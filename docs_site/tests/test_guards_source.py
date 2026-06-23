"""Tests for the source-scan guards (run over markdown before rendering)."""

from __future__ import annotations

from pathlib import Path

import pygments_djc  # noqa: F401 -- register djc_py for the lexer-alias test
from apps.docs.build.guards import api_symbols, code_lang, fence_validator, lexer_alias, nav, snippet_path
from apps.docs.build.guards.base import GuardContext, Severity
from apps.docs.build.guards.fence_validator import scan_fences
from apps.docs.reference.discovery.kinds import ReferenceEntry, ReferencePage


def make_ctx(content_dir: Path, **kw: object) -> GuardContext:
    return GuardContext(
        content_dir=content_dir,
        examples_dir=kw.get("examples_dir", content_dir),  # type: ignore[arg-type]
        nav_path=kw.get("nav_path", content_dir / "_nav.yml"),  # type: ignore[arg-type]
        static_dir=kw.get("static_dir", content_dir),  # type: ignore[arg-type]
        site_index=None,
        example_registry={},
    )


def write(content_dir: Path, rel: str, text: str) -> None:
    path = content_dir / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# --- fence scanner ---------------------------------------------------------


def test_scan_fences_closed_and_lang() -> None:
    fences = scan_fences("```python\nx = 1\n```\n")
    assert len(fences) == 1
    assert fences[0].lang == "python"
    assert fences[0].closed is True


def test_scan_fences_unclosed() -> None:
    fences = scan_fences("```python\nx = 1\n")
    assert len(fences) == 1
    assert fences[0].closed is False


def test_scan_fences_nested_longer_run() -> None:
    # A 4-backtick fence containing a 3-backtick block is one fence, not two.
    src = "````markdown\n```python\nx\n```\n````\n"
    fences = scan_fences(src)
    assert len(fences) == 1
    assert fences[0].closed is True


# --- fence_validator -------------------------------------------------------


def test_fence_validator_flags_unclosed(tmp_path: Path) -> None:
    write(tmp_path, "a.md", "intro\n\n```python\nx = 1\n")
    results = list(fence_validator.check(make_ctx(tmp_path)))
    assert len(results) == 1
    assert results[0].severity is Severity.ERROR
    assert results[0].guard == "fence_validator"
    assert results[0].line == 3


# --- lexer_alias -----------------------------------------------------------


def test_lexer_alias_flags_unknown_lang(tmp_path: Path) -> None:
    write(tmp_path, "a.md", "```pythn\nx\n```\n")
    results = list(lexer_alias.check(make_ctx(tmp_path)))
    assert [r.message for r in results] == ["Unknown code-fence language: 'pythn'"]


def test_lexer_alias_accepts_known_and_allowed(tmp_path: Path) -> None:
    write(tmp_path, "a.md", "```python\nx\n```\n\n```djc_py\ny\n```\n\n```text\nz\n```\n")
    assert list(lexer_alias.check(make_ctx(tmp_path))) == []


# --- code_lang -------------------------------------------------------------


def test_code_lang_warns_on_missing_tag(tmp_path: Path) -> None:
    write(tmp_path, "a.md", "```\nplain\n```\n")
    results = list(code_lang.check(make_ctx(tmp_path)))
    assert len(results) == 1
    assert results[0].severity is Severity.WARNING


def test_code_lang_ok_when_tagged(tmp_path: Path) -> None:
    write(tmp_path, "a.md", "```text\nplain\n```\n")
    assert list(code_lang.check(make_ctx(tmp_path))) == []


# --- snippet_path ----------------------------------------------------------


def test_snippet_path_missing(tmp_path: Path) -> None:
    write(tmp_path, "a.md", '--8<-- "does_not_exist.py"\n')
    results = list(snippet_path.check(make_ctx(tmp_path)))
    assert len(results) == 1
    assert results[0].guard == "snippet_path"


def test_snippet_path_resolves_repo_root_only(tmp_path: Path) -> None:
    # Repo-root-relative paths resolve (matches the old mkdocs `base_path: .`)
    write(tmp_path, "a.md", '--8<-- "CHANGELOG.md"\n')
    assert list(snippet_path.check(make_ctx(tmp_path))) == []

    # Source-dir-relative ("sibling") paths deliberately do NOT resolve: on
    # case-insensitive filesystems a root-relative include can otherwise match
    # the including page itself and silently render empty (self-inclusion).
    write(tmp_path, "snippets/inc.py", "x = 1\n")
    write(tmp_path, "b.md", '--8<-- "snippets/inc.py"\n')
    results = list(snippet_path.check(make_ctx(tmp_path)))
    assert len(results) == 1
    assert results[0].source == "b.md"


# --- nav -------------------------------------------------------------------


def test_nav_flags_missing_page_and_orphan(tmp_path: Path) -> None:
    write(tmp_path, "guides/setup/installation.md", "# Install\n")
    write(tmp_path, "orphan.md", "# Orphan\n")
    write(tmp_path, "index.md", "# Home\n")  # omitted from nav by design
    write(
        tmp_path,
        "_nav.yml",
        "sections:\n"
        "  - label: Home\n"
        "    path: /\n"
        "  - label: Guides\n"
        "    items:\n"
        "      - { title: Install, path: /guides/setup/installation/ }\n"
        "      - { title: Gone, path: /guides/missing/ }\n",
    )
    results = list(nav.check(make_ctx(tmp_path)))
    errors = [r for r in results if r.severity is Severity.ERROR]
    warnings = [r for r in results if r.severity is Severity.WARNING]
    assert any("missing" in r.message for r in errors)
    assert any(r.source == "orphan.md" for r in warnings)
    # the page that IS in the nav is not flagged as an orphan
    assert not any("installation" in (r.source or "") for r in warnings)


# --- api_symbols (forward resolve + reverse coverage) ----------------------


def test_api_symbols_clean_against_real_discovery() -> None:
    # Real discovery: every entry resolves and every public export is documented,
    # so the guard is silent. This doubles as a regression test - a new
    # undocumented export, or an entry griffe can't resolve, makes it fail.
    assert list(api_symbols.check(make_ctx(Path()))) == []


def test_api_symbols_forward_errors_on_unresolvable_entry(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    bad = ReferencePage(
        slug="x",
        title="X",
        preface_md="",
        entries=(
            ReferenceEntry(kind="class", dotted_path="django_components.NoSuchSymbol", display_name="NoSuchSymbol"),
        ),
    )
    monkeypatch.setattr(api_symbols, "discover_pages", lambda: (bad,))
    results = list(api_symbols.check(make_ctx(Path())))
    assert any(r.severity is Severity.ERROR and "does not resolve" in r.message for r in results)


def test_api_symbols_reverse_warns_when_export_undocumented(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    # Nothing documented -> every public export is flagged as a coverage warning.
    monkeypatch.setattr(api_symbols, "discover_pages", lambda: ())
    results = list(api_symbols.check(make_ctx(Path())))
    warnings = [r for r in results if r.severity is Severity.WARNING]
    assert any("Component" in r.message for r in warnings)
