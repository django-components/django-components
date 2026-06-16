"""Tests for the post-build guards (run over the SiteIndex) and the harness."""

from __future__ import annotations

from pathlib import Path

from apps.docs.build import guards as harness
from apps.docs.build.guards import (
    GuardContext,
    GuardResult,
    Severity,
    alt_text,
    anchor,
    anchor_alias,
    asset,
    headings,
    html_wellformed,
    internal_link,
    run_guards,
    single_h1,
)
from apps.docs.build.site_index import SiteIndex
from apps.docs.reference.discovery.kinds import ReferenceEntry, ReferencePage

DOC_META = '<meta name="generator" content="django-components docs builder">'


def write_page(build: Path, rel: str, body: str, *, doc_page: bool = True) -> None:
    head = DOC_META if doc_page else ""
    html = f"<!DOCTYPE html><html><head>{head}</head><body>{body}</body></html>"
    path = build / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def ctx_for(build: Path, *, static_dir: Path | None = None) -> GuardContext:
    return GuardContext(
        content_dir=build,
        examples_dir=build,
        nav_path=build / "_nav.yml",
        static_dir=static_dir or (build / "static"),
        site_index=SiteIndex(build),
        example_registry={},
    )


# --- internal_link ---------------------------------------------------------


def test_internal_link_broken_and_ok(tmp_path: Path) -> None:
    write_page(tmp_path, "a/index.html", '<a href="/b/">b</a><a href="/nope/">x</a>')
    write_page(tmp_path, "b/index.html", "ok")
    results = list(internal_link.check(ctx_for(tmp_path)))
    assert [r.message for r in results] == ["Broken internal link: '/nope/'"]


def test_internal_link_skips_asset_and_external(tmp_path: Path) -> None:
    write_page(tmp_path, "a/index.html", '<a href="/x.png">img</a><a href="https://e.com/">e</a>')
    assert list(internal_link.check(ctx_for(tmp_path))) == []


# --- anchor ----------------------------------------------------------------


def test_anchor_same_page(tmp_path: Path) -> None:
    write_page(tmp_path, "a/index.html", '<h2 id="ok">ok</h2><a href="#ok">y</a><a href="#bad">n</a>')
    results = list(anchor.check(ctx_for(tmp_path)))
    assert len(results) == 1
    assert results[0].severity is Severity.WARNING
    assert "#bad" in results[0].message


def test_anchor_cross_page(tmp_path: Path) -> None:
    write_page(tmp_path, "a/index.html", '<a href="/b/#sec">to b</a>')
    write_page(tmp_path, "b/index.html", '<h2 id="sec">Sec</h2>')
    assert list(anchor.check(ctx_for(tmp_path))) == []


# --- anchor_alias (legacy-anchor coverage) ---------------------------------


def _ref_page(slug: str, *entries: ReferenceEntry) -> ReferencePage:
    return ReferencePage(slug=slug, title=slug.title(), preface_md="", entries=entries)


def test_anchor_alias_ok_when_legacy_anchor_present(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    entry = ReferenceEntry(kind="class", dotted_path="a.b.Thing", display_name="Thing")
    monkeypatch.setattr(anchor_alias, "discover_pages", lambda: (_ref_page("exceptions", entry),))
    # The built page exposes BOTH the canonical and the legacy (dotted-path) anchor.
    write_page(tmp_path, "docs/reference/exceptions/index.html", '<h2 id="Thing"></h2><span id="a.b.Thing"></span>')
    assert list(anchor_alias.check(ctx_for(tmp_path))) == []


def test_anchor_alias_warns_when_legacy_anchor_missing(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    entry = ReferenceEntry(kind="class", dotted_path="a.b.Thing", display_name="Thing")
    monkeypatch.setattr(anchor_alias, "discover_pages", lambda: (_ref_page("exceptions", entry),))
    # Only the canonical anchor is emitted; the legacy alias is gone. (This also
    # exercises the clean-URL page lookup: a wrong path would skip and miss it.)
    write_page(tmp_path, "docs/reference/exceptions/index.html", '<h2 id="Thing"></h2>')
    results = list(anchor_alias.check(ctx_for(tmp_path)))
    assert len(results) == 1
    assert results[0].severity is Severity.WARNING
    assert "a.b.Thing" in results[0].message


def test_anchor_alias_skips_hand_written_kinds(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    # A template tag's legacy anchor equals its canonical anchor (the tag name),
    # so there is no separate alias to require - even though the dotted path (the
    # Node class) appears nowhere on the page.
    entry = ReferenceEntry(kind="template_tag", dotted_path="django_components.slots.FillNode", display_name="fill")
    monkeypatch.setattr(anchor_alias, "discover_pages", lambda: (_ref_page("template_tags", entry),))
    write_page(tmp_path, "docs/reference/template_tags/index.html", '<h2 id="fill"></h2>')
    assert list(anchor_alias.check(ctx_for(tmp_path))) == []


# --- asset -----------------------------------------------------------------


def test_asset_broken_static(tmp_path: Path) -> None:
    static = tmp_path / "static"
    static.mkdir()
    write_page(tmp_path, "a/index.html", '<img src="/static/missing.png" alt="x">')
    results = list(asset.check(ctx_for(tmp_path, static_dir=static)))
    assert any("missing.png" in r.message for r in results)


def test_asset_ok_static(tmp_path: Path) -> None:
    static = tmp_path / "static"
    (static / "img").mkdir(parents=True)
    (static / "img" / "a.png").write_text("x", encoding="utf-8")
    write_page(tmp_path, "a/index.html", '<img src="/static/img/a.png" alt="x">')
    assert list(asset.check(ctx_for(tmp_path, static_dir=static))) == []


# --- single_h1 / alt_text / headings --------------------------------------


def test_single_h1(tmp_path: Path) -> None:
    write_page(tmp_path, "one/index.html", "<h1>A</h1>")
    write_page(tmp_path, "two/index.html", "<h1>A</h1><h1>B</h1>")
    write_page(tmp_path, "zero/index.html", "<h2>A</h2>")
    results = list(single_h1.check(ctx_for(tmp_path)))
    flagged = {r.source for r in results}
    assert "two/index.html" in flagged
    assert "zero/index.html" in flagged
    assert "one/index.html" not in flagged


def test_alt_text(tmp_path: Path) -> None:
    write_page(tmp_path, "a/index.html", '<h1>t</h1><img src="/x.png"><img src="/y.png" alt="y">')
    results = list(alt_text.check(ctx_for(tmp_path)))
    assert len(results) == 1
    assert "/x.png" in results[0].message


def test_headings_jump(tmp_path: Path) -> None:
    write_page(tmp_path, "a/index.html", "<h1>t</h1><h2>s</h2><h4>deep</h4>")
    results = list(headings.check(ctx_for(tmp_path)))
    assert len(results) == 1
    assert "h2 to h4" in results[0].message


def test_content_guards_skip_non_doc_pages(tmp_path: Path) -> None:
    write_page(tmp_path, "demo/index.html", "<h1>A</h1><h1>B</h1>", doc_page=False)
    assert list(single_h1.check(ctx_for(tmp_path))) == []


# --- html_wellformed -------------------------------------------------------


def test_html_wellformed_duplicate_id(tmp_path: Path) -> None:
    write_page(tmp_path, "a/index.html", '<div id="x"></div><span id="x"></span>')
    results = list(html_wellformed.check(ctx_for(tmp_path)))
    assert any("Duplicate id" in r.message for r in results)


# --- harness ---------------------------------------------------------------


def test_run_guards_strict_vs_lenient(tmp_path: Path) -> None:
    # A page with a warning-only issue (missing alt) but no errors.
    write_page(tmp_path, "a/index.html", '<h1>t</h1><img src="/static/x.png">')
    static = tmp_path / "static"
    (static).mkdir()
    (static / "x.png").write_text("x", encoding="utf-8")
    ctx = ctx_for(tmp_path, static_dir=static)

    _, ok_lenient = run_guards(ctx, strict=False)
    results, ok_strict = run_guards(ctx, strict=True)
    assert ok_lenient is True
    assert ok_strict is False
    assert any(r.severity is Severity.WARNING for r in results)


def test_run_guards_reports_crashing_guard(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    def boom(_ctx: GuardContext):  # type: ignore[no-untyped-def]
        raise RuntimeError("kaboom")

    monkeypatch.setattr(harness, "GUARDS", [boom])
    ctx = GuardContext(
        content_dir=Path(),
        examples_dir=Path(),
        nav_path=Path("./_nav.yml"),
        static_dir=Path(),
        site_index=None,
        example_registry={},
    )
    results, ok = run_guards(ctx)
    assert ok is False
    assert any("crashed" in r.message for r in results)
    assert isinstance(results[0], GuardResult)
