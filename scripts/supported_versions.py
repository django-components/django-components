# ruff: noqa: T201, S310
"""
This script manages the info about supported Python and Django versions.

The script fetches the latest supported version information from official sources:
- Python versions from https://devguide.python.org/versions/
- Django versions and compatibility matrix from https://docs.djangoproject.com/

Commands:
    generate: Generates instructions for updating various files (tox.ini, pyproject.toml,
              GitHub Actions, documentation) based on current supported versions

    check:    Compares the current compatibility table in `docs/overview/compatibility.md`
              with the latest official version information. If differences are found,
              creates a GitHub issue to track the needed updates.

Usage:
    python scripts/supported_versions.py generate
    python scripts/supported_versions.py check

    # For GitHub issue creation (check command):
    GITHUB_TOKEN=your_token python scripts/supported_versions.py check

Files updated by this script:
- docs/overview/compatibility.md (compatibility table)
- tox.ini (test environments)
- pyproject.toml (Python classifiers)
- .github/workflows/tests.yml (CI matrix)
- docs/community/development.md (development setup)
"""

import argparse
import json
import os
import re
import sys
import textwrap
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Dict, List, NamedTuple, Tuple
from urllib import request

Version = Tuple[int, ...]
VersionMapping = Dict[Version, List[Version]]


class DjangoVersionChanges(NamedTuple):
    added: List[Version]
    removed: List[Version]


class VersionDifferences(NamedTuple):
    added_python_versions: List[Version]
    removed_python_versions: List[Version]
    changed_django_versions: Dict[Version, DjangoVersionChanges]
    has_changes: bool


######################################
# GET DATA FROM OFFICIAL SOURCES
######################################


HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; django-components version script)"}


def filter_dict(d: Dict, filter_fn: Callable[[Any], bool]) -> Dict:
    return dict(filter(filter_fn, d.items()))


def cut_by_content(content: str, cut_from: str, cut_to: str) -> str:
    return content.split(cut_from)[1].split(cut_to)[0]


def keys_from_content(content: str) -> List[str]:
    return re.findall(r"<td><p>(.*?)</p></td>", content)


def get_python_supported_version(url: str) -> List[Version]:
    req = request.Request(url, headers=HEADERS)
    with request.urlopen(req) as response:
        response_content = response.read()

    content = response_content.decode("utf-8")

    def parse_supported_versions(content: str) -> List[Version]:
        content = cut_by_content(
            content,
            '<section id="supported-versions">',
            "</table>",
        )
        content = cut_by_content(content, "<tbody>", "</tbody>")
        lines = content.split("<tr ")
        versions = [match[0] for line in lines[1:] if (match := re.findall(r"<p>([\d.]+)</p>", line))]
        versions_tuples = [version_to_tuple(version) for version in versions]
        return versions_tuples

    return parse_supported_versions(content)


def get_django_to_python_versions(url: str) -> VersionMapping:
    req = request.Request(url, headers=HEADERS)
    with request.urlopen(req) as response:
        response_content = response.read()

    content = response_content.decode("utf-8")

    def parse_supported_versions(content: str) -> VersionMapping:
        content = cut_by_content(
            content,
            '<span id="what-python-version-can-i-use-with-django">',
            "</table>",
        )
        content = cut_by_content(content, "<tbody>", "</tbody>")

        versions = keys_from_content(content)
        version_dict = dict(zip(versions[::2], versions[1::2]))

        django_to_python = {
            version_to_tuple(python_version): [
                version_to_tuple(version_string)
                for version_string in re.findall(r"(?<!\.)\d+\.\d+(?!\.)", django_versions)
            ]
            for python_version, django_versions in version_dict.items()
        }
        return django_to_python

    return parse_supported_versions(content)


def get_django_supported_versions(url: str) -> List[Tuple[int, ...]]:
    """Extract Django versions from the HTML content, e.g. `5.0` or `4.2`"""
    req = request.Request(url, headers=HEADERS)
    with request.urlopen(req) as response:
        response_content = response.read()

    content = response_content.decode("utf-8")
    content = cut_by_content(
        content,
        "<table class='django-supported-versions'>",
        "</table>",
    )

    rows = re.findall(r"<tr>(.*?)</tr>", content.replace("\n", " "))
    versions: List[Tuple[int, ...]] = []
    # NOTE: Skip first row as that's headers
    for row in rows[1:]:
        data: List[str] = re.findall(r"<td>(.*?)</td>", row)
        # NOTE: First column is version like `5.0` or `4.2 LTS`
        version_with_test = data[0]
        version = version_with_test.split(" ")[0]
        version_tuple = tuple(map(int, version.split(".")))
        versions.append(version_tuple)

    return versions


def get_latest_version(url: str) -> Version:
    req = request.Request(url, headers=HEADERS)
    with request.urlopen(req) as response:
        response_content = response.read()

    content = response_content.decode("utf-8")
    version_string = re.findall(r"The latest official version is (\d+\.\d)", content)[0]
    return version_to_tuple(version_string)


def version_to_tuple(version_string: str) -> Version:
    return tuple(int(num) for num in version_string.split("."))


def build_python_to_django(django_to_python: VersionMapping, latest_version: Version) -> VersionMapping:
    python_to_django: VersionMapping = defaultdict(list)
    for django_version, python_versions in django_to_python.items():
        for python_version in python_versions:
            if django_version <= latest_version:
                python_to_django[python_version].append(django_version)

    python_to_django = dict(python_to_django)
    return python_to_django


def get_python_to_django() -> VersionMapping:
    """Get the Python to Django version mapping as extracted from the websites."""
    active_python = get_python_supported_version("https://devguide.python.org/versions/")
    django_to_python = get_django_to_python_versions("https://docs.djangoproject.com/en/dev/faq/install/")
    django_supported_versions = get_django_supported_versions("https://www.djangoproject.com/download/")
    latest_version = get_latest_version("https://www.djangoproject.com/download/")

    supported_django_to_python = filter_dict(django_to_python, lambda item: item[0] in django_supported_versions)
    python_to_django = build_python_to_django(supported_django_to_python, latest_version)
    # NOTE: Uncomment the below if you want to include only those Python versions
    #       that are still actively supported. Otherwise, we include all Python versions
    #       that are compatible with supported Django versions.
    # python_to_django = filter_dict(python_to_django, lambda item: item[0] in active_python)

    return python_to_django


######################################
# GENERATE COMMAND
######################################


def env_format(version_tuple: Version, divider: str = "") -> str:
    return divider.join(str(num) for num in version_tuple)


def build_tox_envlist(python_to_django: VersionMapping) -> str:
    lines_data = [
        (
            env_format(python_version),
            ",".join(env_format(version) for version in django_versions),
        )
        for python_version, django_versions in python_to_django.items()
    ]
    lines = [f"py{a}-django{{{b}}}" for a, b in lines_data]
    version_lines = "\n".join(version for version in lines)
    return "envlist = \n" + textwrap.indent(version_lines, prefix="  ")


def build_gh_actions_envlist(python_to_django: VersionMapping) -> str:
    lines_data = [
        (
            env_format(python_version, divider="."),
            env_format(python_version),
            ",".join(env_format(version) for version in django_versions),
        )
        for python_version, django_versions in python_to_django.items()
    ]
    lines = [f"{a}: py{b}-django{{{c}}}" for a, b, c in lines_data]
    version_lines = "\n".join(version for version in lines)
    return "python = \n" + textwrap.indent(version_lines, prefix="  ")


def build_deps_envlist(python_to_django: VersionMapping) -> str:
    all_django_versions = set()
    for django_versions in python_to_django.values():
        for django_version in django_versions:
            all_django_versions.add(django_version)

    lines_data = [
        (
            env_format(django_version),
            env_format(django_version, divider="."),
            env_format((django_version[0], django_version[1] + 1), divider="."),
        )
        for django_version in sorted(all_django_versions)
    ]
    lines = [f"django{a}: Django>={b},<{c}" for a, b, c in sorted(lines_data)]
    return "deps = \n" + textwrap.indent("\n".join(lines), prefix="  ")


def build_pypi_classifiers(python_to_django: VersionMapping) -> str:
    classifiers = []

    all_python_versions = python_to_django.keys()
    for python_version in all_python_versions:
        classifiers.append(f'"Programming Language :: Python :: {env_format(python_version, divider=".")}",')

    all_django_versions = set()
    for django_versions in python_to_django.values():
        for django_version in django_versions:
            all_django_versions.add(django_version)

    for django_version in sorted(all_django_versions):
        classifiers.append(f'"Framework :: Django :: {env_format(django_version, divider=".")}",')

    return textwrap.indent("classifiers=[\n", prefix=" " * 4) + textwrap.indent("\n".join(classifiers), prefix=" " * 8)


def build_readme(python_to_django: VersionMapping) -> str:
    print(
        textwrap.dedent(
            """\
                | Python version | Django version           |
                |----------------|--------------------------|
            """.rstrip(),
        ),
    )
    lines_data = [
        (
            env_format(python_version, divider="."),
            ", ".join(env_format(version, divider=".") for version in django_versions),
        )
        for python_version, django_versions in python_to_django.items()
    ]
    lines = [f"| {a: <14} | {b: <24} |" for a, b in lines_data]
    version_lines = "\n".join(version for version in lines)
    return version_lines


def build_pyenv(python_to_django: VersionMapping) -> str:
    lines = []
    all_python_versions = python_to_django.keys()
    for python_version in all_python_versions:
        lines.append(f"pyenv install -s {env_format(python_version, divider='.')}")

    versions_str = " ".join(env_format(version, divider=".") for version in all_python_versions)
    lines.append(f"pyenv local {versions_str}")

    lines.append("tox -p")

    return "\n".join(lines)


def build_ci_python_versions(python_to_django: VersionMapping) -> str:
    # Outputs python-version, like: ['3.8', '3.9', '3.10', '3.11', '3.12']
    lines = [
        f"'{env_format(python_version, divider='.')}'" for python_version, _django_versions in python_to_django.items()
    ]
    lines_formatted = " " * 8 + f"python-version: [{', '.join(lines)}]"
    return lines_formatted


def command_generate() -> None:
    print("🔄 Fetching latest version information...")
    python_to_django = get_python_to_django()

    tox_envlist = build_tox_envlist(python_to_django)
    print("Add this to tox.ini:\n")
    print("[tox]")
    print(tox_envlist)
    print()

    gh_actions_envlist = build_gh_actions_envlist(python_to_django)
    print("[gh-actions]")
    print(gh_actions_envlist)
    print()

    deps_envlist = build_deps_envlist(python_to_django)
    print("[testenv]")
    print(deps_envlist)
    print()
    print()

    print("Add this to pyproject.toml:\n")
    pypi_classifiers = build_pypi_classifiers(python_to_django)
    print(pypi_classifiers)
    print()
    print()

    print("Add this to docs/overview/compatibility.md:\n")
    readme = build_readme(python_to_django)
    print(readme)
    print()
    print()

    print("Add this to docs/community/development.md:\n")
    pyenv = build_pyenv(python_to_django)
    print(pyenv)
    print()
    print()

    print("Add this to tests.yml:\n")
    ci_python_versions = build_ci_python_versions(python_to_django)
    print(ci_python_versions)
    print()
    print()


######################################
# CHECK COMMAND
######################################


def parse_compatibility_markdown(file_path: Path) -> VersionMapping:
    """
    Extract compatibility table from markdown file with following format:

    ```
    | Python version | Django version |
    |----------------|----------------|
    | 3.9            | 4.2            |
    | 3.10           | 4.2, 5.1, 5.2  |
    | 3.11           | 4.2, 5.1, 5.2  |
    | 3.12           | 4.2, 5.1, 5.2  |
    | 3.13           | 5.1, 5.2       |
    ```
    """
    try:
        with file_path.open(encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: Could not find compatibility file at {file_path}")
        sys.exit(1)

    # Find the table section
    lines = content.split("\n")
    table_start = -1
    table_end = -1

    for i, line in enumerate(lines):
        # Search for the table headers line
        # `| Python version | Django version |`
        if re.search(r"\|\s*Python\s+version\s*\|\s*Django\s+version\s*\|", line, re.IGNORECASE):
            table_start = i + 2  # Skip header and separator line
        # Search for the end of the table
        elif table_start != -1 and (line.strip() == "" or not line.startswith("|")):
            table_end = i
            break

    if table_start == -1:
        print("Error: Could not find compatibility table in markdown file")
        sys.exit(1)

    if table_end == -1:
        # If the end of the table is not found, use the last line of the file
        table_end = len(lines)

    # Parse table rows
    # `| 3.10           | 4.2, 5.1, 5.2  |`
    python_to_django: VersionMapping = {}
    for i in range(table_start, table_end):
        # Skip empty and non-table lines
        line = lines[i].strip()
        if not line or not line.startswith("|"):
            continue

        # Split by | and clean up
        parts = [part.strip() for part in line.split("|")[1:-1]]  # Remove empty first/last
        if len(parts) != 2:
            raise ValueError(f"Unexpected table row: {line}")

        python_version_str = parts[0].strip()
        django_versions_str = parts[1].strip()

        try:
            python_version = version_to_tuple(python_version_str)
            django_versions = []
            for version_str in django_versions_str.split(","):
                version_str = version_str.strip()
                if version_str:
                    django_versions.append(version_to_tuple(version_str))

            if django_versions:
                python_to_django[python_version] = django_versions
        except ValueError as e:
            raise ValueError(f"Invalid version string in table row '{line}': {e}") from e

    return python_to_django


def compare_version_mappings(current: VersionMapping, expected: VersionMapping) -> VersionDifferences:
    current_pythons = set(current.keys())
    expected_pythons = set(expected.keys())

    # Find added/removed Python versions
    added_pythons = expected_pythons - current_pythons
    removed_pythons = current_pythons - expected_pythons

    added_python_versions = sorted(added_pythons)
    removed_python_versions = sorted(removed_pythons)

    # Find changed Django versions for existing Python versions
    changed_django_versions = {}
    common_pythons = current_pythons & expected_pythons
    for python_version in common_pythons:
        current_djangos = set(current[python_version])
        expected_djangos = set(expected[python_version])

        if current_djangos != expected_djangos:
            changed_django_versions[python_version] = DjangoVersionChanges(
                added=sorted(expected_djangos - current_djangos),
                removed=sorted(current_djangos - expected_djangos),
            )

    # Check if there are any changes
    has_changes = bool(added_pythons) or bool(removed_pythons) or bool(changed_django_versions)

    return VersionDifferences(
        added_python_versions=added_python_versions,
        removed_python_versions=removed_python_versions,
        changed_django_versions=changed_django_versions,
        has_changes=has_changes,
    )


def command_check(repo_owner: str = "django-components", repo_name: str = "django-components") -> None:
    """Check if supported versions need updating and create GitHub issue if needed"""
    print("🔄 Checking supported versions...")

    # Get current versions from markdown
    compatibility_file = Path("docs/overview/compatibility.md")
    try:
        current_python_to_django = parse_compatibility_markdown(compatibility_file)
        print(f"📖 Parsed current versions from {compatibility_file}")
    except Exception as e:
        print(f"❌ Error parsing compatibility file: {e}")
        sys.exit(1)

    # Get expected versions from official sources
    try:
        expected_python_to_django = get_python_to_django()
        print("🌐 Fetched expected versions from official sources")
    except Exception as e:
        print(f"❌ Error fetching expected versions: {e}")
        sys.exit(1)

    # Compare versions
    differences = compare_version_mappings(current_python_to_django, expected_python_to_django)

    if not differences.has_changes:
        print("✅ Supported versions are up to date!")
        return

    print("⚠️  Supported versions need updating!")

    # Print differences
    if differences.added_python_versions:
        print("➕ Added Python versions:")
        for version in differences.added_python_versions:
            print(f"   - Python {env_format(version, divider='.')}")

    if differences.removed_python_versions:
        print("➖ Removed Python versions:")
        for version in differences.removed_python_versions:
            print(f"   - Python {env_format(version, divider='.')}")

    if differences.changed_django_versions:
        print("🔄 Changed Django version support:")
        for python_version, changes in differences.changed_django_versions.items():
            python_str = env_format(python_version, divider=".")
            print(f"   Python {python_str}:")
            for django_version in changes.added:
                django_str = env_format(django_version, divider=".")
                print(f"     ✅ Added Django {django_str}")
            for django_version in changes.removed:
                django_str = env_format(django_version, divider=".")
                print(f"     ❌ Removed Django {django_str}")

    # Create GitHub issue
    github_token = os.environ.get("GITHUB_TOKEN")

    if not github_token:
        print("\n⚠️  GITHUB_TOKEN environment variable not set.")
        print("Set GITHUB_TOKEN to create GitHub issues automatically.")
        print("Run `python scripts/supported_versions.py generate` to get updated configurations.")
        return

    # Generate issue title and body
    title = create_github_issue_title(differences)
    body = generate_issue_body(differences, current_python_to_django, expected_python_to_django)

    # Check for existing issues
    print("🔍 Checking for existing issues...")
    if check_existing_github_issue(title, repo_owner, repo_name, github_token):
        print("ℹ️  Similar issue already exists. Skipping issue creation.")
        return

    # Create the issue
    print(f"📝 Creating GitHub issue: {title}")
    success = create_github_issue(title, body, repo_owner, repo_name, github_token)

    if not success:
        print("❌ Failed to create GitHub issue")
        sys.exit(1)


######################################
# CHECK COMMAND - GITHUB ISSUE
######################################


def create_github_issue_title(differences: VersionDifferences) -> str:
    """
    Generate a GitHub issue title based on version differences

    We rely on this title to find the issue in the future to avoid duplicates.
    """
    parts = []

    if differences.added_python_versions:
        for version in differences.added_python_versions:
            version_str = env_format(version, divider=".")
            parts.append(f"Add Python {version_str}")

    if differences.removed_python_versions:
        for version in differences.removed_python_versions:
            version_str = env_format(version, divider=".")
            parts.append(f"Remove Python {version_str}")

    # Check for Django version changes
    for python_version, changes in differences.changed_django_versions.items():
        python_str = env_format(python_version, divider=".")
        if changes.added:
            for django_version in changes.added:
                django_str = env_format(django_version, divider=".")
                parts.append(f"Add Django {django_str} for Python {python_str}")
        if changes.removed:
            for django_version in changes.removed:
                django_str = env_format(django_version, divider=".")
                parts.append(f"Remove Django {django_str} for Python {python_str}")

    if not parts:
        return "[maint] Update supported versions"

    # Create a concise title
    if len(parts) == 1:
        return f"[maint] {parts[0]} to supported versions"
    return f"[maint] Update supported versions ({len(parts)} changes)"


def check_existing_github_issue(title: str, repo_owner: str, repo_name: str, token: str) -> bool:
    """Check if a GitHub issue with similar title already exists"""
    # Search for issues with similar titles
    search_url = "https://api.github.com/search/issues"
    params = {
        "q": f'repo:{repo_owner}/{repo_name} is:issue "{title.split(" ")[1]}" "supported versions"'.replace(" ", "%20"),
        "sort": "created",
        "order": "desc",
    }

    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json", **HEADERS}

    try:
        # Build query string manually
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        full_url = f"{search_url}?{query_string}"

        req = request.Request(full_url, headers=headers)
        with request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))

        # Check if any existing issues match our pattern
        for issue in data.get("items", []):
            issue_title = issue["title"].lower()
            if "supported versions" in issue_title and ("[maint]" in issue_title or "maint" in issue_title):
                return True

        return False
    except Exception as e:
        print(f"Warning: Could not check existing issues: {e}")
        return False


def create_github_issue(title: str, body: str, repo_owner: str, repo_name: str, token: str) -> bool:
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues"

    data = {"title": title, "body": body, "labels": ["maintenance", "dependencies"]}

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        **HEADERS,
    }

    try:
        req = request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
        with request.urlopen(req) as response:
            if response.status == 201:
                issue_data = json.loads(response.read().decode("utf-8"))
                print(f"✅ Created GitHub issue: {issue_data['html_url']}")
                return True
            print(f"❌ Failed to create issue. Status: {response.status}")
            return False
    except Exception as e:
        print(f"❌ Error creating GitHub issue: {e}")
        return False


def generate_issue_body(differences: VersionDifferences, current: VersionMapping, expected: VersionMapping) -> str:
    body = "## Supported versions need updating\n\n"
    body += "The supported Python/Django version combinations have changed and need to be updated in the documentation.\n\n"

    if differences.added_python_versions:
        body += "### Added Python versions\n"
        for version in differences.added_python_versions:
            version_str = env_format(version, divider=".")
            body += f"- Python {version_str}\n"
        body += "\n"

    if differences.removed_python_versions:
        body += "### Removed Python versions\n"
        for version in differences.removed_python_versions:
            version_str = env_format(version, divider=".")
            body += f"- Python {version_str}\n"
        body += "\n"

    if differences.changed_django_versions:
        body += "### Changed Django version support\n"
        for python_version, changes in differences.changed_django_versions.items():
            python_str = env_format(python_version, divider=".")
            body += f"**Python {python_str}:**\n"
            if changes.added:
                for django_version in changes.added:
                    django_str = env_format(django_version, divider=".")
                    body += f"- ✅ Added Django {django_str}\n"
            if changes.removed:
                for django_version in changes.removed:
                    django_str = env_format(django_version, divider=".")
                    body += f"- ❌ Removed Django {django_str}\n"
        body += "\n"

    body += "### Expected compatibility table\n\n"
    body += build_readme(expected)
    body += "\n\n"

    body += "### Files to update\n"
    body += "- `docs/overview/compatibility.md`\n"
    body += "- `tox.ini`\n"
    body += "- `pyproject.toml`\n"
    body += "- `.github/workflows/tests.yml`\n\n"

    body += "Run `python scripts/supported_versions.py generate` to get the updated configurations."

    return body


######################################
# MAIN
######################################


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage supported Python/Django version combinations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
            Commands:
              generate    Generate configuration for current supported versions
              check       Check if versions need updating and create GitHub issue

            Environment variables:
              GITHUB_TOKEN    Required for 'check' command to create GitHub issues

            Examples:
              python scripts/supported_versions.py generate
              GITHUB_TOKEN=your_token python scripts/supported_versions.py check
        """),
    )

    parser.add_argument("command", choices=["generate", "check"], help="Command to execute")

    parser.add_argument(
        "--repo-owner", default="django-components", help="GitHub repository owner (default: django-components)"
    )

    parser.add_argument(
        "--repo-name", default="django-components", help="GitHub repository name (default: django-components)"
    )

    return parser


def main() -> None:
    parser = create_parser()
    args = parser.parse_args()

    try:
        if args.command == "generate":
            command_generate()
        elif args.command == "check":
            command_check(args.repo_owner, args.repo_name)
        else:
            parser.error(f"Invalid command: {args.command}")
    except KeyboardInterrupt:
        print("\n❌ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
