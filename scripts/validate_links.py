"""
validate_links.py - URL checker and rewriter for the codebase.

This script scans all files in the repository (respecting .gitignore and IGNORED_PATHS),
finds all URLs, validates them (including checking for HTML fragments), and can optionally
rewrite URLs in-place using a configurable mapping.

Features:
- Finds all URLs in code, markdown, and docstrings.
- Validates URLs by making GET requests (with caching and rate limiting).
- Uses BeautifulSoup to check for HTML fragments (e.g., #section) in the target page.
- Outputs a summary table of all issues (invalid, broken, missing fragment, etc).
- Can output the summary table to a file with `-o`/`--output`.
- Can rewrite URLs in-place using URL_REWRITE_MAP (supports both prefix and regex mapping).
- Supports dry-run mode for rewrites with `--dry-run`.

Usage:

    # Validate all links and print summary to stdout
    python scripts/validate_links.py

    # Output summary table to a file
    python scripts/validate_links.py -o link_report.txt

    # Rewrite URLs using URL_REWRITE_MAP (in-place)
    python scripts/validate_links.py --rewrite

    # Show what would be rewritten, but do not write files
    python scripts/validate_links.py --rewrite --dry-run

Configuration:
- IGNORED_PATHS: List of files/dirs to skip (in addition to .gitignore)
- URL_REWRITE_MAP: Dict of {prefix or regex: replacement} for rewriting URLs

See the code for more details and examples.
"""

import argparse
import os
import re
import requests
import sys
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import DefaultDict, Deque, Dict, List, Tuple, Union
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import pathspec

from django_components.util.misc import format_as_ascii_table

# This script relies on .gitignore to know which files to search for URLs,
# and which files to ignore.
#
# If there are files / dirs that you need to ignore, but they are not (or cannot be)
# included in .gitignore, you can add them here.
IGNORED_PATHS = [
    "package-lock.json",
    "package.json",
    "yarn.lock",
    "mdn_complete_page.html",
    "supported_versions.py",
    # Ignore auto-generated files
    "node_modules",
    "node_modules/",
    ".asv/",
    "__snapshots__/",
    "docs/benchmarks/",
    ".git/",
    "*.min.js",
    "*.min.css",
]

# Domains that are not real and should be ignored.
IGNORE_DOMAINS = [
    "127.0.0.1",
    "localhost",
    "0.0.0.0",
    "example.com",
]

# This allows us to rewrite URLs across the codebase.
# - If key is a str, it's a prefix and the value is the new prefix.
# - If key is a re.Pattern, it's a regex and the value is the replacement string.
URL_REWRITE_MAP: Dict[Union[str, re.Pattern], str] = {
    # Example with regex and capture groups
    # re.compile(r"https://github.com/old-org/([^/]+)/"): r"https://github.com/new-org/\1/",
    # Update all Django docs URLs to 5.2
    re.compile(r"https://docs.djangoproject.com/en/([^/]+)/"): "https://docs.djangoproject.com/en/5.2/",
}


REQUEST_TIMEOUT = 8  # seconds
REQUEST_DELAY = 0.5  # seconds between requests


# Simple regex for URLs to scan for
URL_REGEX = re.compile(r'https?://[^\s\'"\)\]]+')

# Detailed regex for URLs to validate
# See https://stackoverflow.com/a/7160778/9788634
URL_VALIDATOR_REGEX = re.compile(
    r"^(?:http|ftp)s?://"  # http:// or https://
    r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"  # domain...
    r"localhost|"  # localhost...
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
    r"(?::\d+)?"  # optional port
    r"(?:/?|[/?]\S+)$",
    re.IGNORECASE,
)


def is_binary_file(filepath: Path) -> bool:
    try:
        with open(filepath, "rb") as f:
            chunk = f.read(1024)
            if b"\0" in chunk:
                return True
    except Exception:
        return True
    return False


def load_gitignore(root: Path) -> pathspec.PathSpec:
    gitignore = root / ".gitignore"
    patterns = []
    if gitignore.exists():
        with open(gitignore) as f:
            patterns = f.read().splitlines()
    # Add additional ignored paths
    patterns += IGNORED_PATHS
    return pathspec.PathSpec.from_lines("gitwildmatch", patterns)


# Recursively find all files not ignored by .gitignore
def find_files(root: Path, spec: pathspec.PathSpec) -> List[Path]:
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Remove ignored dirs in-place
        rel_dir = os.path.relpath(dirpath, root)
        if rel_dir == ".":
            rel_dir = ""
        ignored_dirs = [d for d in dirnames if spec.match_file(os.path.join(rel_dir, d))]
        for d in ignored_dirs:
            dirnames.remove(d)
        for filename in filenames:
            rel_file = os.path.join(rel_dir, filename)
            if not spec.match_file(rel_file):
                files.append(Path(dirpath) / filename)
    return files


# Extract URLs from a file
def extract_urls_from_file(filepath: Path) -> List[Tuple[str, int, str, str]]:
    urls = []
    try:
        with open(filepath, encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f, 1):
                for match in URL_REGEX.finditer(line):
                    url = match.group(0)
                    urls.append((str(filepath), i, line.rstrip(), url))
    except Exception as e:
        print(f"[WARN] Could not read {filepath}: {e}", file=sys.stderr)
    return urls


def get_base_url(url: str) -> str:
    """Return the URL without the fragment."""
    return url.split("#", 1)[0]


def pick_next_url(domains, domain_to_urls, last_request_time):
    """
    Pick the next (domain, url) to fetch, respecting REQUEST_DELAY per domain.
    Returns (domain, url) or None if all are on cooldown or empty.
    """
    now = time.time()
    for domain in domains:
        if not domain_to_urls[domain]:
            continue
        since_last = now - last_request_time[domain]
        if since_last >= REQUEST_DELAY:
            url = domain_to_urls[domain].popleft()
            return domain, url
    return None


def validate_urls(all_urls):
    """
    For each unique base URL, make a GET request (with caching).
    Print progress for each request (including cache hits).
    If a URL is invalid, print a warning and skip fetching.
    Skip URLs whose netloc matches IGNORE_DOMAINS.
    Use round-robin scheduling per domain, with cooldown.
    """
    url_cache: Dict[str, Union[requests.Response, Exception, str]] = {}
    unique_base_urls = sorted(set(get_base_url(url) for _, _, _, url in all_urls))

    # NOTE: Originally we fetched the URLs one after another. But the issue with this was that
    # there is a few large domains like Github, MDN, Djagno docs, etc. And there's a lot of URLs
    # point to them. So we ended up with a lot of 429 errors.
    #
    # The current approach is to group the URLs by domain, and then fetch them in parallel,
    # preferentially fetching from domains with most URLs (if not on cooldown).
    # This way we can spread the load over the domains, and avoid hitting the rate limits.

    # Group URLs by domain
    domain_to_urls: DefaultDict[str, Deque[str]] = defaultdict(deque)
    for url in unique_base_urls:
        parsed = urlparse(url)
        if parsed.hostname and any(parsed.hostname == d for d in IGNORE_DOMAINS):
            url_cache[url] = "SKIPPED"
            continue
        domain_to_urls[parsed.netloc].append(url)

    # Sort domains by number of URLs (descending)
    domains = sorted(domain_to_urls, key=lambda d: -len(domain_to_urls[d]))
    last_request_time = {domain: 0.0 for domain in domains}
    total_urls = sum(len(q) for q in domain_to_urls.values())
    done_count = 0

    print(f"\nValidating {total_urls} unique base URLs (round-robin by domain)...")
    while any(domain_to_urls.values()):
        pick = pick_next_url(domains, domain_to_urls, last_request_time)
        if pick is None:
            # All domains are on cooldown, sleep until the soonest one is ready
            soonest = min(
                (last_request_time[d] + REQUEST_DELAY for d in domains if domain_to_urls[d]),
                default=time.time() + REQUEST_DELAY,
            )
            sleep_time = max(soonest - time.time(), 0.05)
            time.sleep(sleep_time)
            continue
        domain, url = pick

        # Classify and fetch
        if url in url_cache:
            print(f"[done {done_count+1}/{total_urls}] {url} (cache hit)")
            done_count += 1
            continue
        if not URL_VALIDATOR_REGEX.match(url):
            url_cache[url] = "INVALID_URL"
            print(f"[done {done_count+1}/{total_urls}] {url} WARNING: Invalid URL format, not fetched.")
            done_count += 1
            continue

        print(f"[done {done_count+1}/{total_urls}] {url} ...", end=" ")
        try:
            resp = requests.get(
                url, timeout=REQUEST_TIMEOUT, headers={"User-Agent": "django-components-link-checker/0.1"}
            )
            url_cache[url] = resp
            print(f"{resp.status_code}")
        except Exception as err:
            url_cache[url] = err
            print(f"ERROR: {err}")

        last_request_time[domain] = time.time()
        done_count += 1
    return url_cache


def check_fragment_in_html(html: str, fragment: str) -> bool:
    """Return True if id=fragment exists in the HTML."""
    print(f"Checking fragment {fragment} in HTML...")
    soup = BeautifulSoup(html, "html.parser")
    return bool(soup.find(id=fragment))


def rewrite_url(url: str) -> Union[Tuple[None, None], Tuple[str, Union[str, re.Pattern]]]:
    """Return (new_url, mapping_key) if a mapping applies, else (None, None)."""
    for key, repl in URL_REWRITE_MAP.items():
        if isinstance(key, str):
            if url.startswith(key):
                return url.replace(key, repl, 1), key
        elif isinstance(key, re.Pattern):
            if key.search(url):
                return key.sub(repl, url), key
        else:
            raise ValueError(f"Invalid key type: {type(key)}")
    return None, None


def output_summary(errors: List[Tuple[str, int, str, str, str]], output: str):
    # Format the errors into a table
    headers = ["Type", "Details", "File", "URL"]
    data = [
        {"File": file + "#" + str(lineno), "Type": errtype, "URL": url, "Details": details}
        for file, lineno, errtype, url, details in errors
    ]
    table = format_as_ascii_table(data, headers, include_headers=True)

    # Output summary to file if specified
    if output:
        output_path = Path(output)
        output_path.write_text(table + "\n", encoding="utf-8")
    else:
        print(table + "\n")


# TODO: Run this as a test in CI?
# NOTE: At v0.140 there was ~800 URL instances total, ~300 unique URLs, and the script took 4 min.
def main():
    parser = argparse.ArgumentParser(description="Validate links and fragments in the codebase.")
    parser.add_argument(
        "-o", "--output", type=str, help="Output summary table to file (suppress stdout except errors)"
    )
    parser.add_argument("--rewrite", action="store_true", help="Rewrite URLs using URL_REWRITE_MAP and update files")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be changed by --rewrite, but do not write files"
    )
    args = parser.parse_args()

    root = Path(os.getcwd())
    spec = load_gitignore(root)

    files = find_files(root, spec)
    print(f"Scanning {len(files)} files...")

    all_urls: List[Tuple[str, int, str, str]] = []
    for f in files:
        if is_binary_file(f):
            continue
        all_urls.extend(extract_urls_from_file(f))

    # HTTP request and caching step
    url_cache = validate_urls(all_urls)

    # --- URL rewriting logic ---
    if args.rewrite:
        # Group by file for efficient rewriting
        file_to_lines: Dict[str, List[str]] = {}
        for f in files:
            try:
                with open(f, encoding="utf-8", errors="replace") as fh:
                    file_to_lines[str(f)] = fh.readlines()
            except Exception:
                continue

        rewrites = []
        for file, lineno, line, url in all_urls:
            new_url, mapping_key = rewrite_url(url)
            if not new_url or new_url == url:
                continue

            # Rewrite in memory, so we can have dry-run mode
            lines = file_to_lines[file]
            idx = lineno - 1
            old_line = lines[idx]
            new_line = old_line.replace(url, new_url)
            if old_line != new_line:
                lines[idx] = new_line
                rewrites.append((file, lineno, url, new_url, mapping_key))

        # Write back or dry-run
        if args.dry_run:
            for file, lineno, old, new, _ in rewrites:
                print(f"[DRY-RUN] {file}#{lineno}: {old} -> {new}")
        else:
            for file, _, _, _, _ in rewrites:
                # Write only once per file
                lines = file_to_lines[file]
                Path(file).write_text("".join(lines), encoding="utf-8")
            for file, lineno, old, new, _ in rewrites:
                print(f"[REWRITE] {file}#{lineno}: {old} -> {new}")

        return  # After rewriting, skip error reporting

    # --- Categorize the results / errors ---
    errors = []
    for file, lineno, line, url in all_urls:
        base_url = get_base_url(url)
        fragment = url.split("#", 1)[1] if "#" in url else None
        cache_val = url_cache.get(base_url)

        if cache_val == "SKIPPED":
            continue
        elif cache_val == "INVALID_URL":
            errors.append((file, lineno, "INVALID", url, "Invalid URL format"))
            continue
        elif isinstance(cache_val, Exception):
            errors.append((file, lineno, "ERROR", url, str(cache_val)))
            continue
        elif hasattr(cache_val, "status_code") and getattr(cache_val, "status_code", 0) != 200:
            errors.append((file, lineno, "ERROR_HTTP", url, f"Status {getattr(cache_val, 'status_code', '?')}"))
            continue
        elif fragment and hasattr(cache_val, "text"):
            content_type = cache_val.headers.get("Content-Type", "")
            if "html" not in content_type:
                errors.append((file, lineno, "ERROR_FRAGMENT", url, "Not HTML content"))
                continue
            if not check_fragment_in_html(cache_val.text, fragment):
                errors.append((file, lineno, "ERROR_FRAGMENT", url, f"Fragment '#{fragment}' not found"))

    if not errors:
        print("\nAll links and fragments are valid!")
        return

    # Format the errors into a table
    output_summary(errors, args.output)


if __name__ == "__main__":
    main()
