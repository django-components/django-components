"""Tests for the shared SiteIndex HTML walker."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from apps.docs.build.site_index import SiteIndex

DOC_META = '<meta name="generator" content="django-components docs builder">'


def _write(build: Path, rel: str, body: str, *, doc_page: bool = True) -> None:
    head = DOC_META if doc_page else ""
    html = f"<!DOCTYPE html><html><head>{head}</head><body>{body}</body></html>"
    path = build / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def test_extracts_links_anchors_assets_headings(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "foo/index.html",
        """
        <h1 id="title">Title</h1>
        <h2 id="sec">Section</h2>
        <a href="/bar/">bar</a>
        <a href="#sec">jump</a>
        <a href="https://example.com">ext</a>
        <a name="legacy"></a>
        <img src="/static/img/a.png" alt="A pic">
        <img src="/static/img/b.png">
        """,
    )
    index = SiteIndex(tmp_path)
    page = index.get_page(PurePosixPath("foo/index.html"))
    assert page is not None
    assert page.is_doc_page is True
    assert page.url == "/foo/"
    assert page.anchors == {"title", "sec"}
    assert page.name_aliases == {"legacy"}
    assert {h.level for h in page.headings} == {1, 2}
    assert page.h1_count == 1
    # one external + one anchor-only + one internal
    targets = {(link.is_external, link.is_anchor_only) for link in page.links}
    assert (True, False) in targets
    assert (False, True) in targets
    # images: one with alt, one without
    assert any(img.alt == "A pic" for img in page.images)
    assert any(img.alt is None for img in page.images)


def test_id_equal_name_anchor_is_not_a_duplicate(tmp_path: Path) -> None:
    # pymdownx line anchors look like this; libxml2 strict mode would flag it,
    # but our id-only Counter must not.
    _write(tmp_path, "p/index.html", '<a id="ln-1" name="ln-1" href="#ln-1"></a><p>ok</p>')
    page = SiteIndex(tmp_path).get_page(PurePosixPath("p/index.html"))
    assert page is not None
    assert page.duplicate_ids == []
    assert page.parse_error is None


def test_real_duplicate_id_is_detected(tmp_path: Path) -> None:
    _write(tmp_path, "p/index.html", '<div id="x"></div><div id="x"></div>')
    page = SiteIndex(tmp_path).get_page(PurePosixPath("p/index.html"))
    assert page is not None
    assert page.duplicate_ids == ["x"]


def test_redirect_stub_detection(tmp_path: Path) -> None:
    html = (
        "<!DOCTYPE html><html><head>"
        '<meta http-equiv="refresh" content="0; url=/new/place/">'
        "</head><body></body></html>"
    )
    (tmp_path / "old").mkdir()
    (tmp_path / "old" / "index.html").write_text(html, encoding="utf-8")
    page = SiteIndex(tmp_path).get_page(PurePosixPath("old/index.html"))
    assert page is not None
    assert page.is_redirect_stub is True
    assert page.redirect_target == "/new/place/"


def test_non_doc_page_when_generator_missing(tmp_path: Path) -> None:
    _write(tmp_path, "demo/index.html", "<h1>Demo</h1>", doc_page=False)
    page = SiteIndex(tmp_path).get_page(PurePosixPath("demo/index.html"))
    assert page is not None
    assert page.is_doc_page is False


def test_resolve_link_clean_urls(tmp_path: Path) -> None:
    _write(tmp_path, "index.html", "home")
    _write(tmp_path, "a/index.html", "a")
    _write(tmp_path, "a/b/index.html", "b")
    index = SiteIndex(tmp_path)

    a = PurePosixPath("a/index.html")
    assert index.resolve_link(a, "/a/b/") == PurePosixPath("a/b/index.html")
    assert index.resolve_link(a, "b/") == PurePosixPath("a/b/index.html")
    assert index.resolve_link(a, "../") == PurePosixPath("index.html")
    assert index.resolve_link(a, "/nope/") is None
