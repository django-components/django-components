import pathlib
import re
from datetime import datetime

import mkdocs_gen_files
from mkdocs_gen_files import Nav

# Project root, relative to this script
ROOT = pathlib.Path(__file__).parent.parent.parent


def generate_release_notes() -> None:
    """
    Reads CHANGELOG.md, splits it into per-version pages,
    and generates an index page with links to all versions.
    """
    changelog_path = ROOT / "CHANGELOG.md"
    releases_dir = pathlib.Path("releases")

    # Create the output directory if it doesn't exist
    (ROOT / "docs" / releases_dir).mkdir(parents=True, exist_ok=True)

    with changelog_path.open("r", encoding="utf-8") as f:
        changelog_content = f.read()

    # Split the changelog by version headers (e.g., "## vX.Y.Z")
    # The regex uses a positive lookahead (?=...) to keep the delimiter in the split part.
    versions_raw = re.split(r"(?=^##\s+)", changelog_content, flags=re.MULTILINE)

    # The navigation object for the release notes section
    release_nav = Nav()

    # The first item is the main title '# Release notes\n\n', so we skip it.
    for version_chunk in versions_raw[1:]:
        # The first line is the version header, e.g., "## v0.142.0"
        header_line, body = version_chunk.strip().split("\n", 1)

        # Individual releases may contain the date of release, e.g.
        # ```md
        # ## 🚨📢 v0.100
        # _11 Sep 2024_
        # ```
        #
        # We want to extract the date, and move it from the body to the title.
        date_str = None

        # Check for date in format '_DD Mon YYYY_', e.g. "_11 Sep 2024_"
        date_match = re.search(r"_(\d{1,2}\s+\w{3}\s+\d{4})_", body)
        if date_match:
            date_str = date_match.group(1)
            body = body.replace(date_str, "").strip()

        # Extract the full title from the header, e.g., "🚨📢 v0.140.0"
        version_title_full = header_line.replace("##", "").strip()

        # Get a clean version string for the filename, e.g., "v0.140.0",
        # By removing any emojis, whitespace, and other non-alphanumeric characters.
        version_string_clean, _ = re.subn(r"[^a-zA-Z0-9.-_]", "", version_title_full)
        if not version_string_clean.startswith("v"):
            version_string_clean = "v" + version_string_clean

        # Prepare title for navigation, e.g. "v0.140.0 (2024-09-11)"
        nav_title = version_title_full
        if date_str:
            parsed_date = datetime.strptime(date_str, "%d %b %Y")  # noqa: DTZ007
            formatted_date = parsed_date.strftime("%Y-%m-%d")
            nav_title += f" ({formatted_date})"

        # Generate file name like `v0.140.0.md`
        filename = f"{version_string_clean}.md"
        page_path = releases_dir / filename

        # Create the content for the individual release page
        # We use the full title from the changelog for the page's H1
        page_content = f"# {nav_title}\n\n{body}"

        # Write the individual release page file
        with mkdocs_gen_files.open(page_path.as_posix(), "w", encoding="utf-8") as f:
            f.write(page_content)

        # Add this page to our navigation structure
        release_nav[nav_title] = page_path.as_posix()

    # Generate the index page that lists all releases
    index_path = releases_dir / "index.md"
    with mkdocs_gen_files.open(index_path.as_posix(), "w", encoding="utf-8") as f:
        f.write("# Release Notes\n\n")
        f.write("Here you can find the release notes for all versions of Django-Components.\n\n")

        # Manually build the list with correct relative links
        for nav_item in release_nav.items():
            if nav_item.title and nav_item.filename:
                # nav_item.filename is like 'releases/v0.123.md'. We need just 'v0.123.md'.
                relative_filename = pathlib.Path(nav_item.filename).name
                f.write(f"* [{nav_item.title}]({relative_filename})\n")

    # Generate the .nav.yml file for ordering in the sidebar
    nav_yml_path = releases_dir / ".nav.yml"
    with mkdocs_gen_files.open(nav_yml_path.as_posix(), "w", encoding="utf-8") as f:
        f.write("nav:\n")
        f.write("  - index.md\n")
        for nav_item in release_nav.items():
            if nav_item.filename:
                relative_filename = pathlib.Path(nav_item.filename).name
                f.write(f"  - {relative_filename}\n")


# Run the script
generate_release_notes()
