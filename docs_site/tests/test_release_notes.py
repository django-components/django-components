"""Tests for the CHANGELOG -> release notes parser."""

from __future__ import annotations

import tempfile
from pathlib import Path

from apps.docs.build.release_notes import parse_changelog


def _parse(md: str) -> dict:
    path = Path(tempfile.mkdtemp()) / "CHANGELOG.md"
    path.write_text(md, encoding="utf-8")
    return {r.slug: r for r in parse_changelog(path)}


def test_parse_changelog_reads_long_iso_and_missing_dates() -> None:
    rels = _parse(
        "# Release notes\n\n"
        "## v1.2.0\n\n_2024-09-11_\n\n#### Feat\n\n- x\n\n"  # ISO date
        "## v1.1.0\n\n_05 Jan 2024_\n\n- y\n\n"  # long-form date
        "## v1.0.0\n\n- no date\n"  # no date
    )
    assert rels["v1.2.0"].title == "v1.2.0 (2024-09-11)"  # ISO -> rendered (was silently dropped before)
    assert rels["v1.1.0"].title == "v1.1.0 (2024-01-05)"  # long form -> rendered
    assert rels["v1.0.0"].title == "v1.0.0"  # undated -> bare title
    # The date line is lifted out of the body into the title.
    assert "_2024-09-11_" not in rels["v1.2.0"].body
    assert "_05 Jan 2024_" not in rels["v1.1.0"].body
