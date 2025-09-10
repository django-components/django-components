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

# ruff: noqa: T201,BLE001,PTH118

import argparse
import os
import re
import sys
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import DefaultDict, Deque, Dict, List, Literal, Optional, Tuple, Union
from urllib.parse import urlparse

import pathspec
import requests
from bs4 import BeautifulSoup

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
    "0.0.0.0",  # noqa: S104
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


@dataclass
class Link:
    file: str
    lineno: int
    url: str
    base_url: str  # The URL without the fragment
    fragment: Optional[str]


@dataclass
class LinkRewrite:
    link: Link
    new_url: str
    mapping_key: Union[str, re.Pattern]


@dataclass
class LinkError:
    link: Link
    error_type: Literal["ERROR_FRAGMENT", "ERROR_HTTP", "ERROR_INVALID", "ERROR_OTHER"]
    error_details: str


FetchedResults = Dict[str, Union[requests.Response, Exception, Literal["SKIPPED", "INVALID_URL"]]]


def is_binary_file(filepath: Path) -> bool:
    try:
        with filepath.open("rb") as f:
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
        with gitignore.open() as f:
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
def extract_links_from_file(filepath: Path) -> List[Link]:
    urls: List[Link] = []
    try:
        with filepath.open(encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f, 1):
                for match in URL_REGEX.finditer(line):
                    url = match.group(0)
                    if "#" in url:
                        base_url, fragment = url.split("#", 1)
                    else:
                        base_url, fragment = url, None
                    urls.append(Link(file=str(filepath), lineno=i, url=url, base_url=base_url, fragment=fragment))
    except Exception as e:
        print(f"[WARN] Could not read {filepath}: {e}", file=sys.stderr)
    return urls


# We validate the links by fetching them, reaching the (potentially 3rd party) servers.
# This can be slow, because servers am have rate limiting policies.
# So we group the URLs by domain - URLs pointing to different domains can be
# fetched in parallel. This way we can spread the load over the domains, and avoid hitting the rate limits.
# This function picks the next URL to fetch, respecting the cooldown.
def pick_next_url(
    domains: List[str],
    domain_to_urls: Dict[str, Deque[str]],
    last_request_time: Dict[str, float],
) -> Optional[Tuple[str, str]]:
    now = time.time()
    for domain in domains:
        if not domain_to_urls[domain]:
            continue
        since_last = now - last_request_time[domain]
        if since_last >= REQUEST_DELAY:
            url = domain_to_urls[domain].popleft()
            return domain, url
    return None


def fetch_urls(links: List[Link]) -> FetchedResults:
    """
    For each unique URL, make a GET request (with caching).
    Print progress for each request (including cache hits).
    If a URL is invalid, print a warning and skip fetching.
    Skip URLs whose netloc matches IGNORE_DOMAINS.
    Use round-robin scheduling per domain, with cooldown.
    """
    all_url_results: FetchedResults = {}
    unique_base_urls = set()
    base_urls_with_fragments = set()
    for link in links:
        unique_base_urls.add(link.base_url)
        if link.fragment:
            base_urls_with_fragments.add(link.base_url)

    base_urls = sorted(unique_base_urls)  # Ensure consistency

    # NOTE: Originally we fetched the URLs one after another. But the issue with this was that
    # there is a few large domains like Github, MDN, Djagno docs, etc. And there's a lot of URLs
    # point to them. So we ended up with a lot of 429 errors.
    #
    # The current approach is to group the URLs by domain, and then fetch them in parallel,
    # preferentially fetching from domains with most URLs (if not on cooldown).
    # This way we can spread the load over the domains, and avoid hitting the rate limits.

    # Group URLs by domain
    domain_to_urls: DefaultDict[str, Deque[str]] = defaultdict(deque)
    for url in base_urls:
        parsed = urlparse(url)
        if parsed.hostname and any(parsed.hostname == d for d in IGNORE_DOMAINS):
            all_url_results[url] = "SKIPPED"
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
        if url in all_url_results:
            print(f"[done {done_count + 1}/{total_urls}] {url} (cache hit)")
            done_count += 1
            continue
        if not URL_VALIDATOR_REGEX.match(url):
            all_url_results[url] = "INVALID_URL"
            print(f"[done {done_count + 1}/{total_urls}] {url} WARNING: Invalid URL format, not fetched.")
            done_count += 1
            continue

        method = "GET" if url in base_urls_with_fragments else "HEAD"
        print(f"[done {done_count + 1}/{total_urls}] {method:<4} {url} ...", end=" ")
        try:
            # If there is at least one URL that specifies a fragment in the URL,
            # we will fetch the full HTML with GET.
            # But if there isn't any, we can simply send HEAD request instead.
            if method == "GET":
                resp = requests.get(
                    url,
                    allow_redirects=True,
                    timeout=REQUEST_TIMEOUT,
                    headers={"User-Agent": "django-components-link-checker/0.1"},
                )
            else:
                resp = requests.head(
                    url,
                    allow_redirects=True,
                    timeout=REQUEST_TIMEOUT,
                    headers={"User-Agent": "django-components-link-checker/0.1"},
                )
            all_url_results[url] = resp
            print(f"{resp.status_code}")
        except Exception as err:
            all_url_results[url] = err
            print(f"ERROR: {err}")

        last_request_time[domain] = time.time()
        done_count += 1
    return all_url_results


def rewrite_links(links: List[Link], files: List[Path], dry_run: bool) -> None:
    # Group by file for efficient rewriting
    file_to_lines: Dict[str, List[str]] = {}
    for filepath in files:
        try:
            with filepath.open(encoding="utf-8", errors="replace") as f:
                file_to_lines[str(filepath)] = f.readlines()
        except Exception as e:
            print(f"[WARN] Could not read {filepath}: {e}", file=sys.stderr)
            continue

    rewrites: List[LinkRewrite] = []
    for link in links:
        new_url, mapping_key = rewrite_url(link.url)
        if not new_url or new_url == link.url or mapping_key is None:
            continue

        # Rewrite in memory, so we can have dry-run mode
        lines = file_to_lines[link.file]
        idx = link.lineno - 1
        old_line = lines[idx]
        new_line = old_line.replace(link.url, new_url)
        if old_line != new_line:
            lines[idx] = new_line
            rewrites.append(LinkRewrite(link=link, new_url=new_url, mapping_key=mapping_key))

    # Write back or dry-run
    if dry_run:
        for rewrite in rewrites:
            print(f"[DRY-RUN] {rewrite.link.file}#{rewrite.link.lineno}: {rewrite.link.url} -> {rewrite.new_url}")
    else:
        for rewrite in rewrites:
            # Write only once per file
            lines = file_to_lines[rewrite.link.file]
            Path(rewrite.link.file).write_text("".join(lines), encoding="utf-8")
            print(f"[REWRITE] {rewrite.link.file}#{rewrite.link.lineno}: {rewrite.link.url} -> {rewrite.new_url}")


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
            raise TypeError(f"Invalid key type: {type(key)}")
    return None, None


def check_links_for_errors(all_urls: List[Link], all_url_results: FetchedResults) -> List[LinkError]:
    errors: List[LinkError] = []
    for link in all_urls:
        cache_val = all_url_results.get(link.base_url)

        if cache_val == "SKIPPED":
            continue

        if cache_val == "INVALID_URL":
            link_error = LinkError(link=link, error_type="ERROR_INVALID", error_details="Invalid URL format")
            errors.append(link_error)
            continue

        if isinstance(cache_val, Exception):
            link_error = LinkError(link=link, error_type="ERROR_OTHER", error_details=str(cache_val))
            errors.append(link_error)
            continue

        if isinstance(cache_val, requests.Response):
            # Error response
            if hasattr(cache_val, "status_code") and getattr(cache_val, "status_code", 0) != 200:
                link_error = LinkError(
                    link=link,
                    error_type="ERROR_HTTP",
                    error_details=f"Status {getattr(cache_val, 'status_code', '?')}",
                )
                errors.append(link_error)
                continue

            # Success response
            if cache_val and hasattr(cache_val, "text") and link.fragment:
                content_type = cache_val.headers.get("Content-Type", "")
                if "html" not in content_type:
                    # The specified URL does NOT point to an HTML page, so the fragment is not valid.
                    link_error = LinkError(link=link, error_type="ERROR_FRAGMENT", error_details="Not HTML content")
                    errors.append(link_error)
                    continue

                fragment_in_html = check_fragment_in_html(cache_val.text, link.fragment)
                if not fragment_in_html:
                    # The specified URL points to an HTML page, but the fragment is not valid.
                    link_error = LinkError(
                        link=link,
                        error_type="ERROR_FRAGMENT",
                        error_details=f"Fragment '#{link.fragment}' not found",
                    )
                    errors.append(link_error)
                    continue

        else:
            raise TypeError(f"Unknown cache value type: {type(cache_val)}")
    return errors


def check_fragment_in_html(html: str, fragment: str) -> bool:
    """Return True if id=fragment exists in the HTML."""
    print(f"Checking fragment {fragment} in HTML...")
    soup = BeautifulSoup(html, "html.parser")
    return bool(soup.find(id=fragment))


def output_summary(errors: List[LinkError], output: Optional[str]) -> None:
    # Format the errors into a table
    headers = ["Type", "Details", "File", "URL"]
    data = [
        {
            "File": link_error.link.file + "#" + str(link_error.link.lineno),
            "Type": link_error.error_type,
            "URL": link_error.link.url,
            "Details": link_error.error_details,
        }
        for link_error in errors
    ]
    table = format_as_ascii_table(data, headers, include_headers=True)

    # Output summary to file if specified
    if output:
        output_path = Path(output)
        output_path.write_text(table + "\n", encoding="utf-8")
    else:
        print(table + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate links and fragments in the codebase.")
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Output summary table to file (suppress stdout except errors)",
    )
    parser.add_argument("--rewrite", action="store_true", help="Rewrite URLs using URL_REWRITE_MAP and update files")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed by --rewrite, but do not write files",
    )
    return parser.parse_args()


# TODO: Run this as a test in CI?
# NOTE: At v0.140 there was ~800 URL instances total, ~300 unique URLs, and the script took 4 min.
def main() -> None:
    args = parse_args()

    # Find all relevant files
    root = Path.cwd()
    spec = load_gitignore(root)

    files = find_files(root, spec)
    print(f"Scanning {len(files)} files...")

    # Find links in those files
    all_links: List[Link] = []
    for filepath in files:
        if is_binary_file(filepath):
            continue
        all_links.extend(extract_links_from_file(filepath))

    # Rewrite links in those files if requested
    if args.rewrite:
        rewrite_links(all_links, files, dry_run=args.dry_run)
        return  # After rewriting, skip error reporting

    # Otherwise proceed to validation of the URLs and fragments
    # by first fetching the HTTP requests.
    all_url_results = fetch_urls(all_links)

    # After everything's fetched, check for errors.
    errors = check_links_for_errors(all_links, all_url_results)
    if not errors:
        print("\nAll links and fragments are valid!")
        return

    # Format the errors into a table
    output_summary(errors, args.output or None)


if __name__ == "__main__":
    main()
