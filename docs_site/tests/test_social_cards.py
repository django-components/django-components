"""
Tests for the Phase 5c Chunk 4 social cards (features 5c.3 - 5c.6).

The placement / rewrite / cache / skip logic is tested without a browser by
pre-seeding the content-addressed cache. One e2e test (self-skipping) exercises
the real Playwright screenshot path.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from apps.docs.build.nav import load_nav
from apps.docs.build.pipeline import default_og_image_url
from apps.docs.build.social_cards import (
    _card_hash,
    _section_label,
    _template_version,
    generate_social_cards,
    og_image_rel,
)

DOC_META = '<meta name="generator" content="django-components docs builder">'
SITE = "https://ex.com/base"
NAV = "sections:\n  - label: Concepts\n    items:\n      - { title: Foo, path: /docs/concepts/foo/ }\n"


def _nav_dir(tmp_path: Path) -> Path:
    content = tmp_path / "content"
    content.mkdir(parents=True, exist_ok=True)
    (content / "_nav.yml").write_text(NAV, encoding="utf-8")
    return content


def _write_page(
    output_dir: Path, url: str, *, og_image: str, robots: str = "index,follow", title: str = "Foo"
) -> Path:
    page_dir = output_dir / url.strip("/")
    page_dir.mkdir(parents=True, exist_ok=True)
    head = (
        f"{DOC_META}"
        f'<meta name="robots" content="{robots}">'
        f'<meta property="og:image" content="{og_image}">'
        f'<meta name="twitter:image" content="{og_image}">'
    )
    (page_dir / "index.html").write_text(
        f"<!DOCTYPE html><html><head>{head}</head><body><h1>{title}</h1></body></html>", encoding="utf-8"
    )
    (page_dir / "index.md").write_text(f"---\ntitle: {title}\ndescription: Foo desc.\n---\nBody.\n", encoding="utf-8")
    return page_dir


def _seed_cache(cache_dir: Path, content_dir: Path, *, title: str = "Foo", description: str = "Foo desc.") -> str:
    """Pre-create the cached PNG for the Foo page so no browser is needed."""
    section = _section_label(load_nav(content_dir / "_nav.yml"), "/docs/concepts/foo/")
    digest = _card_hash(_template_version(), title, description, section)
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / f"{digest}.png").write_bytes(b"\x89PNG\r\n\x1a\n-fake")
    return digest


# -- helpers -------------------------------------------------------------------


def test_og_image_rel() -> None:
    assert og_image_rel("/docs/foo/") == "og/docs/foo.png"
    assert og_image_rel("/") == "og/index.png"
    assert og_image_rel("") == "og/index.png"


# -- placement + rewrite (cached, no browser) ----------------------------------


def test_places_cached_card_and_rewrites_og_image(tmp_path: Path) -> None:
    output_dir, content_dir, cache_dir = tmp_path / "site", _nav_dir(tmp_path), tmp_path / "cache"
    default = default_og_image_url()
    page_dir = _write_page(output_dir, "/docs/concepts/foo/", og_image=default)
    _seed_cache(cache_dir, content_dir)

    out = generate_social_cards(output_dir, content_dir, site_url=SITE, cache_dir=cache_dir)

    assert (out.eligible, out.cached, out.rendered, out.placed) == (1, 1, 0, 1)
    assert (output_dir / "og/docs/concepts/foo.png").is_file()
    html = (page_dir / "index.html").read_text()
    # Both og:image and twitter:image now point at the per-page card; default gone.
    assert html.count(f"{SITE}/og/docs/concepts/foo.png") == 2
    assert default not in html


def test_skips_page_with_custom_og_image(tmp_path: Path) -> None:
    output_dir, content_dir, cache_dir = tmp_path / "site", _nav_dir(tmp_path), tmp_path / "cache"
    _write_page(output_dir, "/docs/concepts/foo/", og_image="https://cdn.example.com/custom.png")

    out = generate_social_cards(output_dir, content_dir, site_url=SITE, cache_dir=cache_dir)

    assert out.eligible == 0  # custom image is left untouched
    assert not (output_dir / "og").exists()


def test_skips_noindex_page(tmp_path: Path) -> None:
    output_dir, content_dir, cache_dir = tmp_path / "site", _nav_dir(tmp_path), tmp_path / "cache"
    _write_page(output_dir, "/docs/concepts/foo/", og_image=default_og_image_url(), robots="noindex,follow")

    out = generate_social_cards(output_dir, content_dir, site_url=SITE, cache_dir=cache_dir)
    assert out.eligible == 0


def test_default_image_kept_when_render_unavailable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Empty cache + a forced "no browser" render -> page keeps the default image.
    output_dir, content_dir, cache_dir = tmp_path / "site", _nav_dir(tmp_path), tmp_path / "cache"
    default = default_og_image_url()
    page_dir = _write_page(output_dir, "/docs/concepts/foo/", og_image=default)
    monkeypatch.setattr("apps.docs.build.social_cards._render_cards", lambda *_a, **_k: (0, "chromium-missing"))

    out = generate_social_cards(output_dir, content_dir, site_url=SITE, cache_dir=cache_dir)

    assert out.eligible == 1 and out.placed == 0 and out.skipped_reason == "chromium-missing"
    assert default in (page_dir / "index.html").read_text()  # unchanged, valid default


def test_prunes_unused_cache_entries(tmp_path: Path) -> None:
    output_dir, content_dir, cache_dir = tmp_path / "site", _nav_dir(tmp_path), tmp_path / "cache"
    _write_page(output_dir, "/docs/concepts/foo/", og_image=default_og_image_url())
    _seed_cache(cache_dir, content_dir)
    (cache_dir / "deadbeef.png").write_bytes(b"\x89PNG stale")  # unreferenced

    generate_social_cards(output_dir, content_dir, site_url=SITE, cache_dir=cache_dir)
    assert not (cache_dir / "deadbeef.png").exists()


# -- real render (e2e) ---------------------------------------------------------


@pytest.mark.e2e
def test_real_playwright_render(tmp_path: Path) -> None:
    pytest.importorskip("playwright.sync_api")
    output_dir, content_dir, cache_dir = tmp_path / "site", _nav_dir(tmp_path), tmp_path / "cache"
    _write_page(output_dir, "/docs/concepts/foo/", og_image=default_og_image_url())

    out = generate_social_cards(output_dir, content_dir, site_url=SITE, cache_dir=cache_dir)
    if out.skipped_reason:
        pytest.skip(f"browser unavailable: {out.skipped_reason}")

    png = output_dir / "og/docs/concepts/foo.png"
    assert out.rendered == 1 and out.placed == 1
    assert png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"  # real PNG magic
    assert png.stat().st_size > 5000  # a rendered 1200x630 card, not a stub
