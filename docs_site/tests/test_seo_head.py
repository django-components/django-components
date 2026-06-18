"""
Tests for the Phase 5c Chunk 1 head metadata + chrome (features 5c.7, 5c.8, 5c.16).

Covers the OG/Twitter card meta tags, the TechArticle JSON-LD, and the
"Edit on GitHub" link emitted by DocPage, plus the edit-URL + git-created
helpers that feed them.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from apps.docs.build.frontmatter import parse_page
from apps.docs.build.paths import edit_url_for
from apps.docs.build.pipeline import _resolve_og_image
from apps.docs.components.doc_page.doc_page import DocPage, _build_breadcrumb_jsonld
from django.conf import settings

CANONICAL = "https://django-components.github.io/django-components/v/1.0.0/docs/concepts/foo/"


def _render(**overrides: object) -> str:
    kwargs: dict[str, object] = {
        "content_html": "<h1>Foo</h1><p>Body.</p>",
        "title": "Foo",
        "description": "A short description.",
        "canonical": CANONICAL,
        "current_path": "docs/concepts/foo",
    }
    kwargs.update(overrides)
    return DocPage.render(kwargs=kwargs)


# -- OG / Twitter cards (5c.7) -------------------------------------------------


def test_og_and_twitter_tags_emitted() -> None:
    # The HTML processor normalizes void elements to <meta .../>, so match the
    # attribute pairs rather than a literal closing bracket.
    html = _render(og_image="https://example.com/card.png")
    assert '<meta property="og:type" content="article"' in html
    assert '<meta property="og:title" content="Foo"' in html
    assert '<meta property="og:description" content="A short description."' in html
    assert f'<meta property="og:url" content="{CANONICAL}"' in html
    assert '<meta property="og:image" content="https://example.com/card.png"' in html
    assert '<meta name="twitter:card" content="summary_large_image"' in html
    assert '<meta name="twitter:image" content="https://example.com/card.png"' in html


def test_resolve_og_image_default_and_overrides() -> None:
    root = str(settings.SITE_URL).rstrip("/")
    # No front-matter image -> interim site default (always absolute, never 404s)
    assert _resolve_og_image("") == f"{root}/static/img/favicon.png"
    # Absolute URLs pass through untouched
    assert _resolve_og_image("https://cdn.example.com/x.png") == "https://cdn.example.com/x.png"
    # Site-root-relative paths are made absolute
    assert _resolve_og_image("/static/img/custom.png") == f"{root}/static/img/custom.png"
    assert _resolve_og_image("img/custom.png") == f"{root}/img/custom.png"


# -- description extraction quality (5c.7) -------------------------------------


def test_description_skips_new_in_version_annotation() -> None:
    # The "_New in version X_" italic note must not become the description;
    # the extractor walks past it to the first real prose paragraph.
    body = "## Heading\n\n_New in version 0.89_\n\nThe real first paragraph of prose.\n"
    assert parse_page(body).description == "The real first paragraph of prose."


def test_description_skips_changed_and_deprecated_annotations() -> None:
    body = "## H\n\n_Changed in version 1.2_\n\n_Deprecated in version 1.3_\n\nActual prose here.\n"
    assert parse_page(body).description == "Actual prose here."


def test_description_uses_first_paragraph_normally() -> None:
    assert parse_page("# Title\n\nPlain intro paragraph.\n").description == "Plain intro paragraph."


def test_frontmatter_description_still_wins() -> None:
    body = "---\ndescription: Explicit.\n---\n## H\n\n_New in version 0.89_\n\nProse.\n"
    assert parse_page(body).description == "Explicit."


def test_description_skips_html_comments_tags_and_snippets() -> None:
    body = '# T\n\n<!-- TODO -->\n\n<img src="x.png">\n\n--8<-- "LICENSE"\n\nThe real prose.\n'
    assert parse_page(body).description == "The real prose."


def test_description_preserves_snake_case_identifiers() -> None:
    # Underscore-stripping must not mangle django_components -> djangocomponents
    assert parse_page("# T\n\nConfigure django_components and my_other_setting.\n").description == (
        "Configure django_components and my_other_setting."
    )


def test_description_strips_images_badges_and_crossrefs() -> None:
    body = "# T\n\n[![badge](img.svg)](https://x) See [Component.render()][Component.render] for details.\n"
    desc = parse_page(body).description
    assert "![" not in desc and "](" not in desc and "][" not in desc
    assert "Component.render()" in desc and "for details." in desc


# -- TechArticle JSON-LD (5c.8) ------------------------------------------------


def _article_block(html: str) -> dict:
    # The second ld+json block is the TechArticle (the first is BreadcrumbList).
    marker = '<script type="application/ld+json">'
    blocks = []
    rest = html
    while marker in rest:
        rest = rest.split(marker, 1)[1]
        payload, rest = rest.split("</script>", 1)
        blocks.append(json.loads(payload))
    return next(b for b in blocks if b.get("@type") == "TechArticle")


def test_techarticle_emitted_on_content_page() -> None:
    created = datetime(2024, 1, 2, tzinfo=timezone.utc)
    modified = datetime(2024, 5, 6, tzinfo=timezone.utc)
    html = _render(created=created, last_updated=modified)
    article = _article_block(html)
    assert article["@context"] == "https://schema.org"
    assert article["headline"] == "Foo"
    assert article["url"] == CANONICAL
    assert article["datePublished"] == created.isoformat()
    assert article["dateModified"] == modified.isoformat()
    assert article["publisher"]["@type"] == "Organization"


def test_techarticle_omits_dates_without_git_history() -> None:
    article = _article_block(_render())
    assert "datePublished" not in article
    assert "dateModified" not in article


def test_techarticle_skipped_on_homepage() -> None:
    html = _render(current_path="", canonical="https://x/")
    assert '"@type": "TechArticle"' not in html


def test_techarticle_skipped_on_community_pages() -> None:
    html = _render(current_path="docs/community/contributing")
    assert '"@type": "TechArticle"' not in html


# -- breadcrumb base-path / version stripping (1.26 / 6.12a) -------------------


def _crumbs(canonical: str) -> list[tuple[str, str]]:
    data = json.loads(_build_breadcrumb_jsonld(canonical, "Leaf"))
    return [(i["name"], i["item"]) for i in data["itemListElement"]]


def test_breadcrumb_strips_site_base_path_for_root_canonical() -> None:
    base = str(settings.SITE_URL).rstrip("/")
    crumbs = _crumbs(f"{base}/docs/concepts/foo/")
    # The GitHub Pages project path must NOT appear as a crumb, and items are root-based.
    assert [c[0] for c in crumbs] == ["Docs", "Concepts", "Leaf"]
    assert crumbs[0][1] == f"{base}/docs/"
    assert crumbs[-1][1] == f"{base}/docs/concepts/foo/"


def test_breadcrumb_strips_version_prefix_for_versioned_canonical() -> None:
    base = str(settings.SITE_URL).rstrip("/")
    crumbs = _crumbs(f"{base}/v/9.9.9/docs/foo/")
    assert [c[0] for c in crumbs] == ["Docs", "Leaf"]
    # Item URLs keep the /v/<version>/ prefix; the prefix is not a crumb itself.
    assert crumbs[0][1] == f"{base}/v/9.9.9/docs/"
    assert all("9.9.9" in url for _, url in crumbs)


def test_breadcrumb_empty_for_root_page() -> None:
    assert _build_breadcrumb_jsonld(str(settings.SITE_URL).rstrip("/") + "/", "Home") == ""


# -- Edit on GitHub (5c.16) ----------------------------------------------------


def test_edit_link_rendered_when_url_present() -> None:
    html = _render(edit_url="https://github.com/x/y/edit/master/docs_site/content/docs/concepts/foo.md")
    assert "Edit this page on GitHub" in html
    assert 'href="https://github.com/x/y/edit/master/docs_site/content/docs/concepts/foo.md"' in html


def test_edit_link_absent_without_url() -> None:
    assert "Edit this page on GitHub" not in _render(edit_url="")


def test_edit_url_for_content_page() -> None:
    src = settings.REPO_ROOT / "docs_site" / "content" / "docs" / "concepts" / "foo.md"
    url = edit_url_for(src)
    repo = str(settings.REPO_URL).strip("/ ")
    assert url == f"{repo}/edit/{settings.SOURCE_CODE_GIT_BRANCH}/docs_site/content/docs/concepts/foo.md"


def test_edit_url_for_generated_page_is_empty(tmp_path: Path) -> None:
    # Generated pages live outside the repo (a temp staging dir) -> no edit link.
    assert edit_url_for(tmp_path / "releases" / "v1.0.0.md") == ""
