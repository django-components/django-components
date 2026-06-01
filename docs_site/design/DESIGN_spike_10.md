# Spike 11.10 — Guardrails (dead-link detection, broken anchors, schema drift)

**Status:** spike complete
**Date:** 2026-06-01
**Feeds back into:** [DESIGN_djc_docs_site.md §4.7, §4.8, §9, §11.10, Phase plan](DESIGN_djc_docs_site.md)
**Spike question:** What guards does the new build need so CI fails loudly when something breaks? Today's `mkdocs build --strict` is the parity baseline; this spike specifies every check, where it runs, severity, and LOC budget.

This spike is the **terminal authority for build-time correctness checks**. It owns the *internals* of every guardrail. [§11.9 §4](DESIGN_djc_docs_site_spike_11_9.md) owns the CI gate command (`docs-build-check`) that *orchestrates* them.

---

## 0. TL;DR verdict

**GO.** Every check `mkdocs --strict` performs today has a concrete replacement, and we gain seven additional guards that mkdocs can't run (API symbol coverage, example-page contracts, anchor scheme deviation aliases, cross-version drift, snapshot regression, pygments lexer alias validation, HTML well-formedness).

**Total LOC: ~700 across all guards + harness.** Heaviest single piece is the `SiteIndex` (~120 LOC) that every post-build guard reuses; individual guards are 20–80 LOC each.

**Severity model: two levels.**

- **Error** — fail every build. Examples: broken internal link, template syntax error, missing snippet path. Equivalent to today's "non-strict" failures.
- **Warning** — emit a warning; fail only under `--strict`. Examples: unused public-API symbol, redirect target points outside the built site. Equivalent to today's `validation.anchors: warn` behaviour.

`docs-build` emits errors and warnings to stderr but proceeds (so a half-baked Phase-1 bootstrap can still ship). `docs-build-check --strict` (the default in CI per [§11.9 §4](DESIGN_djc_docs_site_spike_11_9.md)) upgrades warnings to errors and exits non-zero.

**Five load-bearing decisions:**

1. **A shared `SiteIndex` walks every built HTML file once and indexes links, anchors, images, scripts, redirects, and headings.** Every post-build guard reads from the index instead of re-parsing. Saves seconds-to-minutes of full-site rebuild time and centralizes the HTML parsing dependency on one library (`lxml.html`, already permissively licensed).

2. **Cross-version link checking is gated by `docs/v/<version>/` provenance.** A link from `/v0.151/foo` to `/v0.150/bar` is allowed only if the target page exists in `docs/v/0.150/` *as committed in `master`*. The check reuses the §4.6 persist-to-master invariant: the previous version is on disk, not behind a server fetch.

3. **The pre-pass code-fence scanner (§11.4.C) gets a validator twin that runs *before* Django template rendering.** It catches `{% verbatim %}`-wrapping mistakes early — a malformed fence is a build-time error before Django even sees the page. Removes a whole class of "Django renders something that looks fine but the original markdown was structurally broken" failures.

4. **Snapshot regression test uses syrupy with a curated 8-page set, not "snapshot everything".** Cluster of pages chosen to exercise every renderer code path: ApiReference, ExampleCard with fragment pre-render, an admonition-heavy page, a `--8<--` heavy page, the people page (Django template bypass), a redirect stub, a 404, the version-picker. Re-snapshot is `pytest --snapshot-update`. ~30 LOC + 8 fixtures.

5. **External link checking is deferred to a weekly out-of-band job, not on PR.** A flaky upstream (Discord invite, PyPI 503) should not block PRs. Spec'd here for completeness in §3.16 but explicitly out of scope for `docs-build-check`. Lychee + GitHub Actions weekly schedule.

**Recommended first concrete step:** during Phase 1, implement the `SiteIndex` + the **template render** + **internal link** + **anchor** guards. These three are the bare minimum to safely ship Phase-1's single-section preview. Everything else lands incrementally as the pipeline grows.

**Biggest open risk:** the snapshot test will produce noisy diffs during the first few weeks of development (renderer is in flux). Mitigation: keep the snapshot set small at first (3 pages), expand to 8 only after the renderer stabilizes (Phase 3+).

---

## 1. What mkdocs `--strict` catches today (the parity baseline)

The current CI gate is:

```yaml
# .github/workflows/release-docs.yml line 175-178
- name: Check docs in pull requests with strict mode
  if: github.event_name == 'pull_request'
  run: |
    CI=false uv run mkdocs build --strict
```

`--strict` upgrades all mkdocs *warnings* to errors. The configuration in [mkdocs.yml](mkdocs.yml) lines 30–35 declares which checks emit warnings:

```yaml
validation:
  omitted_files: warn         # files in docs/ but not referenced in nav
  absolute_links: warn         # /foo/bar instead of ../foo/bar.md
  unrecognized_links: ignore   # ::path:: shorthand we don't use
  anchors: warn                # broken #anchor in href
```

Plus, individual plugins emit their own warnings under `--strict`:

| Source of warning | What it catches | Maps to our guard |
|---|---|---|
| `mkdocs` core | Broken internal link (target page doesn't exist) | §3.2 internal link check |
| `mkdocs` core | `validation.omitted_files` — page on disk not in nav | §3.13 nav YAML check |
| `mkdocs` core | `validation.absolute_links` — `/foo` instead of `../foo.md` | §3.2 internal link check |
| `mkdocs` core | `validation.anchors` — broken `#anchor` | §3.3 anchor check |
| `pymdownx.snippets` (`check_paths: true`) | `--8<--` snippet path doesn't exist | §3.10 snippet path check |
| `mkdocstrings` | Broken `::: x.y.z` reference | §3.4 API symbol forward check |
| `autorefs` | Unresolvable `[X][]` bracket reference | §3.4 (extended) |
| `mkdocs-redirects` | Redirect destination doesn't exist in built site | §3.12 redirect target check |
| Various plugin loaders | Plugin-config schema errors | Build-time fail-fast (covered by Django's settings/URL loading) |

What `--strict` *does not* catch (gaps we close):

- A `djc_py` fence whose content references an undefined component (we make this explicit: §3.5 example contract, §3.11 lexer alias).
- A public API symbol exported from `django_components.__init__` but never documented (§3.6 reverse API check).
- Cross-version drift: a v0.151 page that links into a `/v0.150/` path that's been deleted (§3.8).
- HTML output that's structurally broken (unclosed tag, duplicate `id`) (§3.15).
- Anchor scheme regressions across the §7.2 deviation (§3.3 has explicit alias coverage).
- Snapshot drift: an unrelated renderer change that flips the byte output of every page (§3.9).

These gaps are the reason we're not satisfied with "just `--strict`."

---

## 2. Complete guardrail inventory

Every guard, in dependency order (run-order in §6).

| # | Guard | What it catches | Where it runs | Severity (default) | LOC | Owner |
|---|---|---|---|---|---|---|
| 1 | **Template render** | Django syntax errors, `{% verbatim %}` mismatch, unregistered tag | Pre-pass + Pass 1 of §11.4.C | Error | 30 | §11.4 + this spike |
| 2 | **Fence validator** | Unclosed fence, malformed `--8<--`, fence-language typo | Pre-pass (before Django) | Error | 60 | This spike |
| 3 | **Pygments lexer alias** | `djc_py`/`htmldjango`/`bash`/etc. fence references an unregistered lexer | Pre-pass (after fence scan) | Error | 30 | This spike |
| 4 | **Snippet path** | `--8<--` target file doesn't exist or is outside `base_path` | Build (via `pymdownx.snippets check_paths`) | Error | 0 (config) | §11.6.E |
| 5 | **API symbol forward** | `{% docstring "x.y.z" %}` references a symbol griffe can't resolve | Build (Django template eval) | Error | 40 | §11.5 + this spike |
| 6 | **API symbol reverse** | Public API symbol never appears in any `{% docstring %}` | Pre-build static scan | Warning | 50 | §11.5 + this spike |
| 7 | **Example-page contract** | `{% example "name" %}` references a dir without `component.py` / `page.py` / a `Page` subclass / tests | Pre-build static scan | Error | 50 | This spike |
| 8 | **Internal link** | `<a href>` to non-existent built HTML | Post-build (SiteIndex) | Error | 60 | This spike |
| 9 | **Anchor** | `<a href="page#anchor">` where `anchor` isn't an `id=` on the target page | Post-build (SiteIndex) | Error | 30 | This spike |
| 10 | **Anchor alias coverage** | A renamed §7.2 symbol's legacy alias (`#django_components.X`) is missing | Post-build (SiteIndex) | Warning | 30 | This spike |
| 11 | **Image / asset** | `<img src>` to non-existent file under `static/` | Post-build (SiteIndex) | Error | 30 | This spike |
| 12 | **Redirect target** | Redirect stub points to a URL not built | Post-build (SiteIndex) | Error | 20 | This spike + §11.9 §2.5 |
| 13 | **Nav YAML validity** | Page in `content/` not in `_nav.yml`, or vice-versa | Pre-build | Warning | 50 | This spike + §11.9 §2.2 |
| 14 | **Cross-version link** | Link from `/v0.X/` to `/v0.Y/` whose target doesn't exist on disk | Post-build (multi-version SiteIndex) | Error | 60 | This spike |
| 15 | **HTML well-formedness** | Duplicate `id=`, unclosed tag, invalid attribute that breaks the DOM | Post-build (SiteIndex) | Error | 30 | This spike |
| 16 | **Versions manifest integrity** | `docs/v/versions.json` lists a version dir that doesn't exist (or vice-versa) | Post-build | Error | 20 | This spike + §11.7 |
| 17 | **Snapshot regression** | Curated set of pages differs from committed snapshot | Post-build (pytest + syrupy) | Error (PR review) | 30 + 8 fixtures | This spike |
| 18 | **External link (out-of-band)** | External URLs in docs 404/timeout | Weekly job; not on PR | Warning | 0 (lychee) | This spike (spec'd) |

**Total in `docs-build-check`:** guards 1–17. **Total LOC: ~640 + the shared SiteIndex (~120) = ~760 LOC.**

Guard #18 is in a separate weekly workflow, not the PR gate.

---

## 3. Deep dive — each guard

### 3.1 Template render guard

**What it catches.** Any error Django's template engine raises during Pass 1 of §11.4.C: `TemplateSyntaxError`, `TemplateDoesNotExist`, unregistered tag library, `{% verbatim %}` left unclosed in the pre-pass output.

**Implementation.** Nothing custom — bubble Django's existing exceptions up with the source filename and line number annotated. We already get `TemplateSyntaxError` with line info; we just need to translate "line 47 in inline template" → "line 47 in `content/concepts/foo.md`".

```python
# docs_site/apps/docs/build/guards/template_render.py  ~30 LOC

def render_page(source_md_path: Path, source_text: str) -> str:
    try:
        return _render_pipeline(source_text)
    except TemplateSyntaxError as e:
        raise GuardError(
            guard="template_render",
            source=source_md_path,
            line=getattr(e, "line", None),
            message=str(e),
        ) from e
```

**Severity.** Always error. A page that won't render can't ship.

**Where it runs.** Build itself — there's no separate "guard step." If `docs-build` succeeds, this guard implicitly passed.

**LOC.** ~30, mostly the exception translation layer.

---

### 3.2 Fence validator

**What it catches.** A pre-pass guard that validates the markdown source *before* the §11.4.C fence-protection scanner wraps code regions in `{% verbatim %}`. Fails on:

- Unclosed fenced block (` ``` ` opened, never closed) — would otherwise corrupt the entire downstream pipeline.
- `--8<-- "path"` snippet inside fenced code that uses `~~~` instead of ` ``` ` and lacks blank-line separators.
- A fence info-string with unknown language (paired with §3.3).

This sits *between* the fence scanner and the Django pass. Without it, an unclosed fence causes Pass 1 to render an unbounded `{% verbatim %}` block, which produces a confusing downstream Django error.

**Implementation.** Reuse the fence-state machine from the §11.4.C scanner. After scanning, assert all open fences have a matching close. Emit a clear error citing the line of the unclosed fence opener.

```python
# docs_site/apps/docs/build/guards/fence_validator.py  ~60 LOC

class FenceState(NamedTuple):
    kind: Literal["backtick", "tilde", "indent_4sp"]
    open_line: int

def validate_fences(source: str, source_path: Path) -> Iterator[GuardResult]:
    state: list[FenceState] = []
    for lineno, line in enumerate(source.splitlines(), start=1):
        # ... fence-state machine ...
        pass
    for unclosed in state:
        yield GuardResult.error(
            guard="fence_validator",
            source=source_path,
            line=unclosed.open_line,
            message=f"Unclosed {unclosed.kind} fence (opened at line {unclosed.open_line})",
        )
```

**Severity.** Error.

**Where it runs.** Pre-pass, before any Django rendering. Failing here saves downstream confusion.

**LOC.** ~60 (the state machine).

---

### 3.3 Pygments lexer alias check

**What it catches.** A fence with an info-string that doesn't resolve to a registered Pygments lexer. The Pygments lexer registry contains every alias known to the running interpreter — `python`, `py`, `pycon`, `html`, `djc_py` (registered by [pygments_djc](https://pypi.org/project/pygments-djc/)), `htmldjango`, etc.

A typo like ` ```djcc_py ` won't fail under mkdocs today — Pygments just falls back to the `TextLexer` and you get unstyled output. We want the build to fail.

**Implementation.** Walk all fence info-strings collected by §3.2, look up each against `pygments.lexers.get_lexer_by_name`. If `pygments.util.ClassNotFound`, error.

```python
# docs_site/apps/docs/build/guards/lexer_alias.py  ~30 LOC

from pygments.util import ClassNotFound
from pygments.lexers import get_lexer_by_name

ALLOWED_NON_LEXER_INFOSTRINGS = {"", "text", "plain", "console", "shell-session"}

def check_lexer_aliases(fences: list[Fence]) -> Iterator[GuardResult]:
    for fence in fences:
        lang = fence.info_string.strip().split()[0] if fence.info_string else ""
        if lang in ALLOWED_NON_LEXER_INFOSTRINGS:
            continue
        try:
            get_lexer_by_name(lang)
        except ClassNotFound:
            yield GuardResult.error(
                guard="lexer_alias",
                source=fence.source_path,
                line=fence.open_line,
                message=f"Unknown fence language: {lang!r}",
            )
```

**Severity.** Error.

**Where it runs.** Pre-pass, immediately after §3.2.

**LOC.** ~30.

**Trade-off.** Adds a hard dependency on every fence language being a registered lexer at build time. If a contributor adds ` ```mermaid ` (Mermaid diagram), the guard fails. Mitigation: maintain a small `ALLOWED_NON_LEXER_INFOSTRINGS` set for languages we intentionally pass through to the browser. Three entries today; will grow modestly.

---

### 3.4 API symbol forward check

**What it catches.** `{% docstring "django_components.SomethingThatDoesntExist" %}` where the dotted path can't be resolved by griffe.

**Implementation.** §11.5 owns the griffe symbol lookup (`lookup_symbol(dotted_path)`). The forward guard is a thin wrapper: every `{% docstring %}` invocation in the Pass 1 evaluation path raises a `GuardError` instead of `LookupError` when the symbol's not found, with the source markdown file + line.

This guard runs *during* Pass 1, not as a separate pass. The Django `simple_tag` for `{% docstring %}` either returns rendered HTML or raises with full context.

```python
# docs_site/apps/docs/templatetags/docs_extras.py (excerpt)
@register.simple_tag(takes_context=True)
def docstring(context, dotted_path):
    try:
        symbol_data = lookup_symbol(dotted_path)
    except SymbolNotFound:
        raise GuardError(
            guard="api_symbol_forward",
            source=context["source_md_path"],
            message=f"Unknown API symbol: {dotted_path!r}",
        )
    return ApiReference.render(kwargs={"symbol": symbol_data}, context=context.flatten())
```

**Severity.** Error.

**Where it runs.** Build (Pass 1).

**LOC.** ~40, dominated by error-context plumbing into the Django template engine. The lookup itself is in §11.5.

---

### 3.5 API symbol reverse check

**What it catches.** A public API symbol — anything exported from `django_components/__init__.py` — that's not referenced by any `{% docstring %}` invocation anywhere in `content/`. Catches "we added a new public function but forgot to add it to the docs."

**Implementation.** Pre-build static scan. Walk all `content/**/*.md` for `{% docstring "..." %}` invocations, accumulate the set. Walk griffe's tree of the public surface (the §11.5 Discovery layer already produces this set). Diff: public minus documented = warnings.

```python
# docs_site/apps/docs/build/guards/api_symbol_reverse.py  ~50 LOC

DOCSTRING_RE = re.compile(r'{%\s*docstring\s+["\'](?P<path>[^"\']+)["\']')

def check_api_coverage(content_dir: Path, public_api: set[str]) -> Iterator[GuardResult]:
    documented: set[str] = set()
    for md in content_dir.rglob("*.md"):
        text = md.read_text(encoding="utf-8")
        for m in DOCSTRING_RE.finditer(text):
            documented.add(m.group("path"))

    undocumented = public_api - documented
    for symbol in sorted(undocumented):
        yield GuardResult.warning(
            guard="api_symbol_reverse",
            source=None,
            message=f"Public API symbol {symbol!r} is not referenced by any {{% docstring %}}",
        )

    private_documented = documented - public_api
    for symbol in sorted(private_documented):
        yield GuardResult.warning(
            guard="api_symbol_reverse",
            source=None,
            message=f"{{% docstring %}} references private symbol {symbol!r}; only public API should be documented",
        )
```

**Severity.** Warning by default. Upgrade to error in `--strict` mode (so PR CI fails on coverage gap).

**Where it runs.** Pre-build static scan. Doesn't need a fully built site.

**LOC.** ~50.

**Edge case.** An "implementation detail" public symbol (e.g. a `TypedDict` used as an argument type) might genuinely not deserve its own `{% docstring %}` — its parent does. Mitigation: an opt-out marker in the public-API discovery layer (`__no_docs__ = True` on the symbol's enclosing module, or a `docs_versions.toml` allowlist).

---

### 3.6 Example-page contract check

**What it catches.** `{% example "fragments" %}` referencing a directory that doesn't follow the §2.4 contract:

- Directory exists at `examples/fragments/`.
- `examples/fragments/component.py` exists.
- `examples/fragments/page.py` exists.
- `page.py` defines a `Component` subclass whose name ends in `Page`.
- That class has a nested `View` class.
- At least one `test_example_*.py` exists in the dir (so the example is exercised by the test suite).
- If the example uses fragments (per §4.4a), the `Page.DocsExample.fragments` enumeration exists.

**Implementation.** Static scan + import the `page.py` to introspect its class hierarchy.

```python
# docs_site/apps/docs/build/guards/example_contract.py  ~50 LOC

EXAMPLE_RE = re.compile(r'{%\s*example\s+["\'](?P<name>[^"\']+)["\']')

def check_example_contracts(content_dir: Path, examples_dir: Path) -> Iterator[GuardResult]:
    referenced: set[str] = set()
    for md in content_dir.rglob("*.md"):
        for m in EXAMPLE_RE.finditer(md.read_text(encoding="utf-8")):
            referenced.add(m.group("name"))

    for name in referenced:
        example_dir = examples_dir / name
        for required in ("component.py", "page.py"):
            if not (example_dir / required).exists():
                yield GuardResult.error(
                    guard="example_contract",
                    source=example_dir,
                    message=f"Example {name!r} missing required file: {required}",
                )
                break
        else:
            yield from _check_example_class(example_dir, name)
            if not any(example_dir.glob("test_example_*.py")):
                yield GuardResult.error(
                    guard="example_contract",
                    source=example_dir,
                    message=f"Example {name!r} has no test_example_*.py file",
                )
```

**Severity.** Error. An `{% example %}` that can't render is a build failure.

**Where it runs.** Pre-build static scan + a quick `importlib` introspection of each referenced example's `page.py`.

**LOC.** ~50.

**Edge case.** A page references `{% example %}` but the example dir is intentionally not yet wired (work in progress). Mitigation: scan only `content/**/*.md` that pass the §3.2 fence validator; staged work uses a `{# %example ... #}` comment marker to skip.

---

### 3.7 Snippet path check

**What it catches.** A `--8<-- "path/to/file"` snippet whose target file doesn't exist.

**Implementation.** **No new code.** `pymdownx.snippets` already has `check_paths: true` configured in [mkdocs.yml](mkdocs.yml) line 115 and we keep that config in the new pipeline (§11.4.B). Snippet failures bubble up as Pass 2 markdown errors, which the template render guard (§3.1) catches.

**Severity.** Error (via the underlying pymdownx config).

**Where it runs.** Build (Pass 2).

**LOC.** 0. Config-driven.

---

### 3.8 Cross-version link check

**What it catches.** A link from `/v0.151/foo` to `/v0.150/bar` where `/v0.150/bar` doesn't exist on disk in `docs/v/0.150/`.

This is the load-bearing guard for the §4.6 persist-to-master strategy. Because old versions live on disk in `master`, a link to them is a normal file-exists check — no server round trip needed.

**Implementation.** Post-build pass over the multi-version SiteIndex (§6). For every link whose target starts with `/v<version>/` and points to a different version than the source page's version, assert the target page exists in the on-disk `docs/v/<target_version>/`.

```python
# docs_site/apps/docs/build/guards/cross_version_link.py  ~60 LOC

VERSION_PATH_RE = re.compile(r'^/v(?P<version>[\d.]+)/')

def check_cross_version_links(site_index: SiteIndex, versions_root: Path) -> Iterator[GuardResult]:
    for page in site_index.pages:
        page_version = _version_of(page.url)
        for link in page.links:
            target_version = _version_of(link.target)
            if not target_version or target_version == page_version:
                continue
            target_path = versions_root / f"v{target_version}" / link.target_path
            if not target_path.exists():
                yield GuardResult.error(
                    guard="cross_version_link",
                    source=page.source_md_path,
                    message=f"Link to {link.target!r} (cross-version) — target missing in v{target_version}",
                )
```

**Severity.** Error.

**Where it runs.** Post-build, after every per-version build has completed. Skipped when `docs-build` runs against a single version (the common dev path); always runs in `docs-build-all` and in CI's full build matrix.

**LOC.** ~60.

**Edge case.** The version picker generates intra-site links between versions for the same page (e.g. "see this page in v0.149"). Allowlist: links emitted by the `VersionPicker` component bypass this guard.

---

### 3.9 Internal link check

**What it catches.** Every `<a href="...">` whose target is an internal path that doesn't resolve to a built HTML page.

**Implementation.** Post-build SiteIndex walk. The SiteIndex builds a `set[Path]` of every emitted HTML page. For each link, normalize relative paths against the source page's URL, ignore external URLs (scheme is set), ignore anchors-only (`#foo`), then assert the resolved path is in the built set.

```python
# docs_site/apps/docs/build/guards/internal_link.py  ~60 LOC

def check_internal_links(site_index: SiteIndex) -> Iterator[GuardResult]:
    built_pages = site_index.built_page_paths  # set[PurePosixPath]
    for page in site_index.pages:
        for link in page.links:
            if link.is_external:
                continue
            if link.is_anchor_only:
                continue
            target = page.resolve_link(link.target)
            if target not in built_pages:
                yield GuardResult.error(
                    guard="internal_link",
                    source=page.source_md_path,
                    message=f"Broken internal link: {link.target!r} (resolved to {target!r})",
                )
```

**Severity.** Error.

**Where it runs.** Post-build.

**LOC.** ~60.

---

### 3.10 Anchor check

**What it catches.** `<a href="page#anchor">` where the target page exists but has no `id="anchor"` heading.

**Implementation.** SiteIndex collects `id=` attributes from every `<h1>`–`<h6>` and from every element with an explicit `id=` in the built HTML. Anchor check walks every link with a `#` fragment and asserts the target's anchor set contains the fragment.

```python
# docs_site/apps/docs/build/guards/anchor.py  ~30 LOC

def check_anchors(site_index: SiteIndex) -> Iterator[GuardResult]:
    for page in site_index.pages:
        for link in page.links:
            if not link.anchor:
                continue
            target_page = site_index.get_page(page.resolve_link(link.target_url_only))
            if target_page is None:
                continue   # internal_link guard handles this
            if link.anchor not in target_page.anchors:
                yield GuardResult.error(
                    guard="anchor",
                    source=page.source_md_path,
                    message=f"Broken anchor: {link.target!r} — page has no id={link.anchor!r}",
                )
```

**Severity.** Error.

**Where it runs.** Post-build.

**LOC.** ~30 (shares SiteIndex).

---

### 3.11 Anchor alias coverage

**What it catches.** Per §7.2 of the design doc, the new anchor scheme drops the `django_components.` prefix (so `#django_components.Component` becomes `#Component`). To preserve inbound links, the renderer emits a legacy alias `<a name="django_components.Component"></a>` alongside the canonical `<h2 id="Component">`. This guard verifies the alias is present for every renamed symbol.

**Implementation.** For every `<h*>` heading in an API reference page, check the SiteIndex's `name="..."` set for the corresponding `django_components.<heading-id>` alias.

```python
# docs_site/apps/docs/build/guards/anchor_alias.py  ~30 LOC

def check_alias_coverage(site_index: SiteIndex) -> Iterator[GuardResult]:
    for page in site_index.pages:
        if not page.is_api_reference:
            continue
        for anchor in page.anchors:
            legacy = f"django_components.{anchor}"
            if legacy not in page.name_aliases:
                yield GuardResult.warning(
                    guard="anchor_alias",
                    source=page.source_md_path,
                    message=f"API symbol {anchor!r} missing legacy alias <a name='{legacy}'>",
                )
```

**Severity.** Warning. Aliases are belt-and-braces; a missing one degrades old links to a 200-with-wrong-scroll-position but doesn't break the page.

**Where it runs.** Post-build.

**LOC.** ~30.

---

### 3.12 Image / asset check

**What it catches.** `<img src="...">` whose file doesn't exist under `static/` in the built site. Same for `<script src>` and `<link href>` to local assets.

**Implementation.** SiteIndex collects asset references. For each, normalize to a path under `static/` and check the file exists in the build output.

```python
# docs_site/apps/docs/build/guards/asset.py  ~30 LOC

def check_assets(site_index: SiteIndex, static_root: Path) -> Iterator[GuardResult]:
    for page in site_index.pages:
        for asset in page.assets:
            if asset.is_external:
                continue
            target = static_root / asset.path
            if not target.exists():
                yield GuardResult.error(
                    guard="asset",
                    source=page.source_md_path,
                    message=f"Broken asset: {asset.tag} src={asset.path!r}",
                )
```

**Severity.** Error.

**Where it runs.** Post-build.

**LOC.** ~30.

---

### 3.13 Redirect target check

**What it catches.** A static redirect stub emitted by §11.9 §2.5 whose `<meta http-equiv="refresh" content="...; url=X">` target X doesn't exist in the built site.

**Implementation.** SiteIndex distinguishes redirect-stub pages (a small HTML body, a meta-refresh tag, no real content). For each, check the target URL exists in `built_page_paths`.

```python
# docs_site/apps/docs/build/guards/redirect_target.py  ~20 LOC

def check_redirect_targets(site_index: SiteIndex) -> Iterator[GuardResult]:
    for page in site_index.pages:
        if not page.is_redirect_stub:
            continue
        target = page.redirect_target
        if target not in site_index.built_page_paths:
            yield GuardResult.error(
                guard="redirect_target",
                source=page.source_md_path,
                message=f"Redirect from {page.url!r} points to non-existent {target!r}",
            )
```

**Severity.** Error.

**Where it runs.** Post-build.

**LOC.** ~20.

---

### 3.14 Nav YAML validity check

**What it catches.** Two-way drift between `content/` and `_nav.yml`:

- **Page in `content/` but not referenced in `_nav.yml`** → warning (matches mkdocs `validation.omitted_files: warn`).
- **Entry in `_nav.yml` but page doesn't exist** → error (broken nav entry).

**Implementation.** Pre-build static scan. Load `_nav.yml`, walk `content/`, diff.

```python
# docs_site/apps/docs/build/guards/nav.py  ~50 LOC

def check_nav(nav_yaml_path: Path, content_dir: Path) -> Iterator[GuardResult]:
    nav_pages: set[Path] = _walk_nav_yaml(nav_yaml_path)
    fs_pages: set[Path] = {p for p in content_dir.rglob("*.md")}

    for missing in nav_pages - fs_pages:
        yield GuardResult.error(
            guard="nav",
            source=nav_yaml_path,
            message=f"_nav.yml references non-existent page: {missing}",
        )

    OMIT_FROM_NAV = {Path("README.md"), Path("agent-knowledge/INDEX.md"), ...}
    for omitted in fs_pages - nav_pages - OMIT_FROM_NAV:
        yield GuardResult.warning(
            guard="nav",
            source=omitted,
            message=f"Page exists on disk but is not in _nav.yml: {omitted}",
        )
```

**Severity.** Mixed: broken entry = error; orphan page = warning.

**Where it runs.** Pre-build.

**LOC.** ~50.

---

### 3.15 HTML well-formedness check

**What it catches.** Duplicate `id=` on the same page, unclosed tags that the browser silently auto-closes, invalid characters in attribute values that break the DOM.

**Implementation.** `lxml.html.fromstring(content, parser=lxml.html.HTMLParser(recover=False))` and intercept any `lxml.etree.XMLSyntaxError`. For duplicate `id=`, build a `Counter[str]` over `iter("*")` ids and emit one warning per duplicated id.

```python
# docs_site/apps/docs/build/guards/html_wellformed.py  ~30 LOC

def check_well_formed(site_index: SiteIndex) -> Iterator[GuardResult]:
    for page in site_index.pages:
        # SiteIndex already parsed with recover=False; failures are stored
        if page.parse_error:
            yield GuardResult.error(
                guard="html_wellformed",
                source=page.source_md_path,
                message=f"HTML parse error: {page.parse_error}",
            )
        for id_, count in Counter(e.get("id") for e in page.dom.iter()).items():
            if id_ and count > 1:
                yield GuardResult.error(
                    guard="html_wellformed",
                    source=page.source_md_path,
                    message=f"Duplicate id={id_!r} ({count}× on page)",
                )
```

**Severity.** Error. Duplicate ids in particular break the anchor guard (§3.10) silently because the browser jumps to the first instance.

**Where it runs.** Post-build (during SiteIndex construction; the guard just reports collected failures).

**LOC.** ~30.

---

### 3.16 Versions manifest integrity

**What it catches.** `docs/v/versions.json` lists a version that doesn't have a corresponding `docs/v/<version>/` directory, or vice-versa.

**Implementation.** Post-build, load `docs/v/versions.json`, list `docs/v/v*/`, diff.

```python
# docs_site/apps/docs/build/guards/versions_manifest.py  ~20 LOC

def check_versions_manifest(versions_root: Path) -> Iterator[GuardResult]:
    manifest = json.loads((versions_root / "versions.json").read_text())
    listed = {v["version"] for v in manifest["versions"]}
    on_disk = {p.name.removeprefix("v") for p in versions_root.glob("v*") if p.is_dir()}

    for orphan_manifest in listed - on_disk:
        yield GuardResult.error(
            guard="versions_manifest",
            source=versions_root / "versions.json",
            message=f"versions.json lists v{orphan_manifest} but docs/v/v{orphan_manifest}/ doesn't exist",
        )
    for orphan_disk in on_disk - listed:
        yield GuardResult.error(
            guard="versions_manifest",
            source=versions_root / f"v{orphan_disk}",
            message=f"docs/v/v{orphan_disk}/ exists but is not in versions.json",
        )
```

**Severity.** Error.

**Where it runs.** Post-build (after `docs-build` or `docs-build-all`).

**LOC.** ~20.

---

### 3.17 Snapshot regression test

**What it catches.** Any byte-level change in the rendered HTML for a curated set of pages that isn't acknowledged by the contributor. Catches a renderer change that flips output across many pages — exactly the class of bug a per-page guard misses.

**Implementation.** pytest + syrupy. A pytest test in `tests/test_docs_snapshots.py` renders each fixture page through the new builder and asserts against a committed snapshot. Re-snapshot via `pytest --snapshot-update`.

```python
# tests/test_docs_snapshots.py  ~30 LOC

SNAPSHOT_PAGES = [
    "concepts/fundamentals/component.md",          # ApiReference
    "examples/fragments.md",                       # ExampleCard with fragments
    "getting_started/adding_js_and_css.md",        # admonition-heavy
    "examples/recursion.md",                       # --8<-- heavy
    "community/people.md",                         # Django-template bypass
    "404.md",                                       # 404 page
    "release_notes.md",                            # versioned content
    "reference/components.md",                     # full API reference
]

@pytest.mark.parametrize("page", SNAPSHOT_PAGES)
def test_page_renders_to_snapshot(page, snapshot, docs_builder):
    html = docs_builder.render(page)
    assert html == snapshot(name=page)
```

**Severity.** Error in CI (pytest fails); informational in dev (`pytest -k snapshot` is opt-in).

**Where it runs.** PR test suite, not inside `docs-build-check`. The snapshot diff is visible in code review.

**LOC.** ~30 + 8 snapshot fixture files.

**Edge case.** Renderer is in flux during Phase 1–3; snapshots will churn. Mitigation: start with 3 fixtures, expand to 8 only after Phase 3 stabilizes.

---

### 3.18 External link check (out-of-band)

**What it catches.** External URLs in docs that 404, timeout, or have changed.

**Implementation.** Use [lychee](https://lychee.cli.rs/) (Rust, MIT, ~4MB binary). Already widely used for docs link checking. Run as a separate GitHub Actions workflow on a weekly schedule.

```yaml
# .github/workflows/docs-external-links.yml
name: Docs external link check
on:
  schedule:
    - cron: "0 6 * * 1"   # 06:00 UTC Monday
  workflow_dispatch:
jobs:
  lychee:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: lycheeverse/lychee-action@v2
        with:
          args: --no-progress --exclude-mail content/**/*.md
          fail: true
```

**Severity.** Warning (opens an issue on failure, doesn't fail the build).

**Where it runs.** **Not in `docs-build-check`.** Out-of-band weekly job only. PR CI should never depend on third-party uptime.

**LOC.** 0 (lychee + GitHub Action).

**Justification for separation.** A flaky Discord invite or a momentary PyPI 503 would block PRs if this ran on PR. The whole point of CI guards is determinism. External-link checking is *important* but *should not gate merges*.

---

## 4. Severity model

Three states per guard result: `ERROR`, `WARNING`, `INFO`. The harness collects them all and the exit code depends on mode:

| Mode | Errors → | Warnings → | Info → |
|---|---|---|---|
| `docs-build` (everyday) | Non-zero exit | Print + continue | Print + continue |
| `docs-build --strict` | Non-zero exit | Non-zero exit | Print + continue |
| `docs-build-check` (CI default = strict) | Non-zero exit | Non-zero exit | Print + continue |
| `docs-build-all` (bootstrap) | Print + continue | Print + continue | Print + continue |

**Why `docs-build-all` is permissive.** Bootstrap rebuilds N historical versions from tags. Some old versions may have warnings that the *contemporaneous* mkdocs config didn't catch (because guards are stricter now). We don't want to fail the bootstrap on a 18-month-old warning. The current-version build under `docs-build-check` enforces strictness.

**Why two error-only guards (template_render, fence_validator) have no "warning" mode.** Both produce output that's structurally unusable. There's no graceful degradation.

**Why API symbol reverse defaults to warning.** A newly-added public symbol is reasonably *staged* for docs in a follow-up PR. Hard-failing every PR that adds an export without simultaneously adding `{% docstring %}` would be annoying. Strict CI upgrades it to error.

---

## 5. Where each guard runs

```
┌──────────────────────────────────────────────────────────────────┐
│  Pre-build static scan (no rendering needed)                     │
│  - 3.5 API symbol reverse                                         │
│  - 3.6 Example-page contract                                      │
│  - 3.14 Nav YAML validity                                         │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  Pre-pass (per page, before Django renders)                       │
│  - 3.2 Fence validator                                            │
│  - 3.3 Pygments lexer alias                                       │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  Build (Django template engine — Pass 1 of §11.4.C)               │
│  - 3.1 Template render                                            │
│  - 3.4 API symbol forward                                         │
│  - 3.7 Snippet path (via pymdownx.snippets, runs in Pass 2)       │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  SiteIndex construction (post-build, walk every emitted HTML)     │
│  - 3.15 HTML well-formedness (during parse)                       │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  Post-build guard suite (consumes SiteIndex)                      │
│  - 3.9  Internal link                                             │
│  - 3.10 Anchor                                                    │
│  - 3.11 Anchor alias coverage                                     │
│  - 3.12 Image / asset                                             │
│  - 3.13 Redirect target                                           │
│  - 3.16 Versions manifest integrity                               │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  Multi-version (only when docs/v/ has ≥2 versions)                │
│  - 3.8 Cross-version link                                         │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  PR test suite (pytest, not in docs-build-check)                  │
│  - 3.17 Snapshot regression                                       │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  Out-of-band weekly (separate workflow)                           │
│  - 3.18 External link                                             │
└──────────────────────────────────────────────────────────────────┘
```

---

## 6. The harness — how guards plug together

A `GuardrailRunner` orchestrates the guards and produces a structured report. Each guard is a function with the signature `(context) -> Iterator[GuardResult]`.

```python
# docs_site/apps/docs/build/guards/__init__.py  ~100 LOC

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Iterator

class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

@dataclass(frozen=True)
class GuardResult:
    guard: str                      # "internal_link", "anchor", ...
    severity: Severity
    message: str
    source: Path | None             # source file (markdown or example dir)
    line: int | None = None

    @classmethod
    def error(cls, **kw) -> "GuardResult":
        return cls(severity=Severity.ERROR, **kw)
    @classmethod
    def warning(cls, **kw) -> "GuardResult":
        return cls(severity=Severity.WARNING, **kw)

@dataclass
class GuardContext:
    content_dir: Path
    examples_dir: Path
    build_dir: Path                 # the temp dir docs-build-check writes to
    versions_root: Path             # docs/v/
    site_index: SiteIndex | None    # None during pre-build guards
    public_api: set[str]            # from §11.5 Discovery

GUARDS: list[Callable[[GuardContext], Iterator[GuardResult]]] = [
    nav.check_nav,
    api_symbol_reverse.check_api_coverage,
    example_contract.check_example_contracts,
    # Pre-pass / build-time guards report through GuardError directly;
    # they don't appear in this list (their results are interleaved with the build).
    internal_link.check_internal_links,
    anchor.check_anchors,
    anchor_alias.check_alias_coverage,
    asset.check_assets,
    redirect_target.check_redirect_targets,
    html_wellformed.check_well_formed,
    versions_manifest.check_versions_manifest,
    cross_version_link.check_cross_version_links,
]

def run_guards(ctx: GuardContext, strict: bool = False) -> tuple[int, list[GuardResult]]:
    results: list[GuardResult] = []
    for guard in GUARDS:
        try:
            results.extend(guard(ctx))
        except Exception as e:
            results.append(GuardResult.error(
                guard=guard.__name__,
                source=None,
                message=f"Guard crashed: {type(e).__name__}: {e}",
            ))

    has_error = any(r.severity == Severity.ERROR for r in results)
    has_warning = any(r.severity == Severity.WARNING for r in results)
    if has_error or (strict and has_warning):
        return (1, results)
    return (0, results)
```

The `SiteIndex` is the heaviest piece (~120 LOC):

```python
# docs_site/apps/docs/build/site_index.py  ~120 LOC

@dataclass
class PageRecord:
    url: PurePosixPath              # "/concepts/fundamentals/component"
    source_md_path: Path            # the markdown source file
    dom: lxml.html.HtmlElement
    parse_error: str | None
    anchors: set[str]               # ids of headings
    name_aliases: set[str]          # legacy <a name="..."> elements
    links: list[LinkRef]
    assets: list[AssetRef]
    is_api_reference: bool
    is_redirect_stub: bool
    redirect_target: PurePosixPath | None

class SiteIndex:
    def __init__(self, build_dir: Path, source_dir: Path) -> None:
        self.pages: list[PageRecord] = []
        self.built_page_paths: set[PurePosixPath] = set()
        for html_path in build_dir.rglob("*.html"):
            self.pages.append(self._parse(html_path, source_dir))
            self.built_page_paths.add(PurePosixPath(html_path.relative_to(build_dir)))

    def _parse(self, path: Path, source_dir: Path) -> PageRecord:
        ...  # lxml.html.fromstring, walk <a>, <img>, <h*>, <meta http-equiv=refresh>
```

The harness emits a structured report (per [§11.9 §4](DESIGN_djc_docs_site_spike_11_9.md)):

```
docs-build-check (2026-06-01T12:34:56Z)
  Pre-build:        ✓ nav, api_symbol_reverse, example_contract (3 warnings)
  Build:            ✓ 247 pages rendered
  Post-build:       ✗ internal_link (2 errors), anchor (1 warning)

errors:
  internal_link: content/concepts/foo.md
    broken link: ../bar.md (resolved to /concepts/bar)
  internal_link: content/examples/fragments.md
    broken link: ./missing.gif (resolved to /examples/missing.gif)

warnings:
  api_symbol_reverse:
    public symbol 'django_components.NewThing' is not referenced by any {% docstring %}
  anchor: content/getting_started/index.md
    broken anchor: ../reference/api.md#Render (page has no id='Render')

EXIT 1
```

---

## 7. CI wiring

Already specified in [§11.9 §4](DESIGN_djc_docs_site_spike_11_9.md). The `docs-build-check` PR workflow:

```yaml
# .github/workflows/docs-check.yml
name: Docs check
on:
  pull_request:
    paths:
      - 'src/**'                   # docstring changes need re-render
      - 'content/**'
      - 'docs_site/**'
      - 'examples/**'
      - 'pyproject.toml'
jobs:
  docs-build-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
        with: { fetch-depth: 0 }   # required for §3.14 git metadata
      - uses: astral-sh/setup-uv@v3
      - run: uv sync --group docs
      - run: uv run playwright install chromium
      - run: uv run docs-build-check
```

The weekly external-link workflow (§3.18) is separate and never blocks merges.

A second PR-time test (`pytest tests/test_docs_snapshots.py`) runs alongside `docs-build-check` and produces the syrupy diff visible in code review.

---

## 8. Implementation order

Mapped to the migration phases from [§8 of the design doc](DESIGN_djc_docs_site.md):

**Phase 1 — single-section ports.** Land the three "absolutely required to ship anything" guards:
- §3.1 Template render (free with Django)
- §3.2 Fence validator
- §3.9 Internal link + §3.10 Anchor (one PR — they share the SiteIndex)

Without these, Phase 1 can't validate its own output. With them, we get a credible single-section preview.

**Phase 2 — `{% example %}` lands.** Add:
- §3.6 Example-page contract
- §3.11 Anchor alias coverage (since §7.2 anchor scheme deviation is needed for the rendered API pages)

**Phase 3 — full content port.** Add:
- §3.3 Pygments lexer alias
- §3.4 API symbol forward
- §3.5 API symbol reverse (warning-only at first)
- §3.13 Nav YAML validity
- §3.15 HTML well-formedness

**Phase 4 — API reference lands.** No new guards (§3.4–3.5 already cover this; they just become useful now).

**Phase 5 — search / versioning / social.** Add:
- §3.8 Cross-version link
- §3.12 Image / asset
- §3.13 Redirect target
- §3.16 Versions manifest integrity
- §3.17 Snapshot regression (3 pages first, expand to 8 later)

**Phase 6 — cutover.** Delete the old `mkdocs build --strict` step from `release-docs.yml`. Verify `docs-build-check` is the sole PR gate.

**Out of band (any time):** §3.18 external link weekly workflow.

---

## 9. LOC budget

| Component | LOC |
|---|---|
| `GuardResult` / `GuardContext` / `GuardrailRunner` (the harness) | ~100 |
| `SiteIndex` (the shared post-build walker) | ~120 |
| 3.1 Template render | 30 |
| 3.2 Fence validator | 60 |
| 3.3 Pygments lexer alias | 30 |
| 3.4 API symbol forward | 40 |
| 3.5 API symbol reverse | 50 |
| 3.6 Example-page contract | 50 |
| 3.7 Snippet path | 0 (config) |
| 3.8 Cross-version link | 60 |
| 3.9 Internal link | 60 |
| 3.10 Anchor | 30 |
| 3.11 Anchor alias coverage | 30 |
| 3.12 Image / asset | 30 |
| 3.13 Redirect target | 20 |
| 3.14 Nav YAML validity | 50 |
| 3.15 HTML well-formedness | 30 |
| 3.16 Versions manifest integrity | 20 |
| 3.17 Snapshot regression | 30 + 8 fixture files |
| 3.18 External link (lychee) | 0 (out of repo Python) |
| **Total** | **~840** (Python) |

Single largest item is the harness + SiteIndex (~220 combined), which every post-build guard reuses.

---

## 10. Risks & open items

### 10.1 Risks during execution

- **Snapshot churn during Phases 1–3.** Renderer is in flux; snapshots get regenerated often. Mitigation: small initial set (3 pages), don't add §3.17 to `docs-build-check` until Phase 5.
- **API symbol reverse false positives.** Some genuinely-public-but-not-documented symbols exist (utility `TypedDict`s, internal-ish enums). Mitigation: `__no_docs__ = True` module attribute as opt-out, plus an allowlist in `docs_versions.toml`.
- **Lexer alias guard rejects legitimate non-Pygments fences.** Mermaid, GraphViz, etc. could appear. Mitigation: `ALLOWED_NON_LEXER_INFOSTRINGS` allowlist. Three entries today; will need maintenance.
- **Cross-version check assumes `docs/v/<version>/` is fully built on disk.** During Phase 1–4 we won't have multiple versions yet — guard is a no-op. The guard only becomes meaningful after Phase 5 ships and the first follow-up release lands.
- **HTML well-formedness false positives from minify-html.** `minify-html` (per §11.9 §2.6) is aggressive about closing optional tags. We need to run the well-formedness guard *before* minification (against the pre-minified HTML).

### 10.2 Items deferred to other spikes

- **Accessibility checks** (alt-text presence, contrast, semantic HTML, ARIA correctness). Out of scope for v1; revisit when the visual system stabilizes (§11.11).
- **SEO checks** (canonical URLs, OG tags, robots/sitemap). Covered partly by §11.9 §2.5 (redirects) and the social-card template; full SEO audit is a separate spike if we want it.
- **CSS lint / unused styles.** Out of scope; revisit if the CSS surface grows beyond what humans can review.
- **API symbol cross-reference resolution** ("see [X][]" → /api/X). Owned by §11.5; this spike checks that the resolved URL exists, not the bracket-syntax expansion.
- **Search index validity** (Pagefind index covers every page; no orphans). Owned by §11.1.

### 10.3 Items deferred to implementation

- Exact `_nav.yml` schema and the `OMIT_FROM_NAV` set (§3.14). Resolved during §11.9 §2.2 nav loader implementation.
- Snapshot fixture set finalization (§3.17). Resolved when Phase 3 stabilizes.
- The `ALLOWED_NON_LEXER_INFOSTRINGS` set (§3.3). Resolved as new languages are introduced.
- Whether to allow `--lenient` flag on `docs-build-check` for emergency green CI. Probably not; the right escape hatch is to push fixes, not bypass the gate.

---

## 11. Quick reference

One-line verdict per guard, in run order:

1. **Template render** — error; built into Django; ~30 LOC.
2. **Fence validator** — error; pre-pass; ~60 LOC.
3. **Lexer alias** — error; pre-pass; ~30 LOC.
4. **Snippet path** — error; config-driven (pymdownx.snippets); 0 LOC.
5. **API forward** — error; in Pass 1; ~40 LOC.
6. **API reverse** — warning; pre-build scan; ~50 LOC.
7. **Example contract** — error; pre-build scan + introspect; ~50 LOC.
8. **Internal link** — error; SiteIndex; ~60 LOC.
9. **Anchor** — error; SiteIndex; ~30 LOC.
10. **Anchor alias** — warning; SiteIndex; ~30 LOC.
11. **Image / asset** — error; SiteIndex; ~30 LOC.
12. **Redirect target** — error; SiteIndex; ~20 LOC.
13. **Nav YAML validity** — error/warning; pre-build; ~50 LOC.
14. **Cross-version link** — error; multi-version post-build; ~60 LOC.
15. **HTML well-formedness** — error; SiteIndex parse; ~30 LOC.
16. **Versions manifest** — error; post-build; ~20 LOC.
17. **Snapshot regression** — error in CI; pytest+syrupy; ~30 LOC + fixtures.
18. **External link** — warning; out-of-band weekly; 0 LOC (lychee).

---

## 12. Where this feeds back

- **[§4.7 / §11.4.C](DESIGN_djc_docs_site.md):** the §3.1 + §3.2 + §3.3 guards plug into the pre-pass / Pass 1 of the markdown pipeline.
- **[§4.8](DESIGN_djc_docs_site.md):** `docs-build` keeps emitting warnings to stderr; `docs-build --strict` upgrades to errors. Wires the harness in.
- **[§9 open questions](DESIGN_djc_docs_site.md):** answers §9.8 ("mkdocs strict-mode link checking equivalent") — yes, with the harness specified above.
- **[§11.5](DESIGN_djc_docs_site_spike_11_5.md):** §3.4 forward + §3.5 reverse depend on the Discovery layer exposing the `set[str]` of public-API dotted paths. Confirm during implementation.
- **[§11.7](DESIGN_djc_docs_site_spike_11_7.md):** §3.16 versions-manifest guard reads the schema mike-vendored version of `versions.json`.
- **[§11.9 §4](DESIGN_djc_docs_site_spike_11_9.md):** `docs-build-check` is the harness host. This spike specifies what it runs; §11.9 §4 specifies how it integrates with CI.
- **[§11.11](DESIGN_djc_docs_site.md):** the snapshot fixtures (§3.17) reference the visual layout finalized in §11.11.

---

## 13. What this spike does NOT cover

- The renderer itself (owned by §11.4).
- The Discovery layer that produces `public_api: set[str]` (owned by §11.5).
- The plugin replacements that emit redirects / nav / git metadata (owned by §11.9).
- The CI gate command's orchestration (owned by §11.9 §4).
- The mike vendor of `versions.json` schema (owned by §11.7).
- External-link checking on PR (deliberately punted to weekly out-of-band).
- Accessibility, contrast, SEO checks (deferred; not on v1 critical path).
