"""Tests for the dev-server views (live preview)."""

from __future__ import annotations

from pathlib import Path

from apps.docs.views import _content_asset
from django.conf import settings


def test_content_asset_serves_images_excludes_md_and_blocks_traversal(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(settings, "CONTENT_DIR", tmp_path)
    (tmp_path / "docs" / "images").mkdir(parents=True)
    img = tmp_path / "docs" / "images" / "x.png"
    img.write_bytes(b"\x89PNG")
    (tmp_path / "docs" / "page.md").write_text("# x", encoding="utf-8")

    assert _content_asset("docs/images/x.png") == img.resolve()  # an image -> served
    assert _content_asset("/docs/images/x.png") == img.resolve()  # leading slash tolerated
    assert _content_asset("docs/images/missing.png") is None  # absent -> 404
    assert _content_asset("docs/page.md") is None  # markdown is rendered, not served raw
    assert _content_asset("../../../etc/passwd") is None  # path traversal confined to CONTENT_DIR
