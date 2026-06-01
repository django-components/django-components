# Feature inventory — django-components docs-site rebuild

**Status:** living document
**Date:** 2026-06-01
**Owner:** Juro Oravec
**Related:** [DESIGN_djc_docs_site.md](DESIGN_djc_docs_site.md) (main), spikes 11.5/11.7/11.8/11.9/11.10/11.11/11.12

This file is the **single durable list** of every concrete buildable feature called out across the main design doc and all spike docs. The main design doc carries the **narrative** of each phase; this file carries the **catalogue** so nothing falls off the table when agent context fills.

Rules:
- Every feature lives in exactly one phase.
- When in doubt, defer to a later phase.
- "Critical" means the docs site can't ship without it.
- Effort: **S** ≤1 day, **M** 1-3 days, **L** >3 days.
- Source columns cite which doc speced the feature — pull there for full design.
- Status defaults `pending`; flip to `in_progress` / `done` as PRs land.

If you find a feature missing, **add it to this file**, don't just track it in a todo list — the file is the survival layer.

---

## Phase 0 — Pre-work in `src/django_components/` (before any `docs_site/` code)

Goal: clean source-of-truth before the migration starts. These are codemods in the existing codebase, NOT new features.

| # | ID | Name | Effort | Critical | Source | Status | Notes |
|---|---|---|---|---|---|---|---|
| 0.1 | `codemod-links` | Hand-typed link sweep (`[X](api.md#...)` → `[X][Key]`) | M | ✓ | 11.5 §7.1, §11.4 | **done** (3cb4c531) | 1086 transformations across 72 files. Always-explicit `[X][Key]` form, short keys (no `django_components.` prefix, no module prefix) |
| 0.2 | `codemod-google-sections` | Google-style section alignment (`**Args:**` → `Args:`) | M | ✓ | 11.5 §11.4 | **done** (28cea92d) | 128 mechanical free-form renames + 14 manual structured (Args/Arguments/Raises) bullet → bare-indent restructures |
| 0.3 | `docs-convention-community` | Document docstring convention in `docs/community/development.md` | M | | 11.5 §11.6 | **done** (this commit) | "Writing docstrings" subsection under "Documentation website" |
| 0.4 | `docs-convention-claude` | Add docstring rule to `CLAUDE.md` | S | | 11.5 §11.6 | skipped | `CLAUDE.md` is intentionally local/untracked; spike §11.6 step skipped |

**Out of scope here:** any code under `docs_site/`.

---

## Phase 1 — Foundation: render ONE page end-to-end

Goal: a single page (e.g. `getting_started/index.md`) renders through the 3-pass pipeline to a static file in `docs/v/<version>/`, with full `<head>` metadata. No nav chrome yet; no API reference; no examples.

**Sharp focus:** prove the pipeline, the file layout, and the metadata story. Resist building chrome.

| # | ID | Name | Effort | Critical | Source | Status | Notes |
|---|---|---|---|---|---|---|---|
| 1.1 | `docs-site-django-project` | `docs_site/` Django project scaffold | S | ✓ | main §4.1 | pending | Replaces `sampleproject/` |
| 1.2 | `docs-app-scaffold` | `apps/docs/` with components/, templatetags/, management/commands/ | S | ✓ | main §4.1 | pending | |
| 1.3 | `content-dir-structure` | Move `docs/` → `docs_site/content/` (markdown source) | S | | main §4.1, 11.4.G | pending | `mv` + `rm` of build cruft |
| 1.4 | `examples-dir-moved` | Move `docs/examples/` → `docs_site/examples/` | S | | main §4.1 | pending | First-class location |
| 1.5 | `pygments-djc-loader` | Load `pygments_djc` lexer at command startup | S | ✓ | main §2.1, 11.9 §2.1 | pending | 1 LOC; we own this lib |
| 1.6 | `fence-protection-scanner` | Wrap code regions in `{% verbatim %}` before Django pass | S | ✓ | main §4.7, §11.4.C | pending | ~80 LOC |
| 1.7 | `markdown-pipeline-pass1` | Pass 1: Django template engine on markdown source | S | ✓ | main §4.7, §11.4.C | pending | Auto-loads `docs_extras`, `component_tags` |
| 1.8 | `markdown-pipeline-pass2` | Pass 2: python-markdown + pymdownx → HTML | M | ✓ | main §4.7, §11.4.B | pending | Keep python-markdown, not markdown-it-py |
| 1.9 | `markdown-pipeline-pass3` | Pass 3: wrap in DocPage layout | M | ✓ | main §4.7 | pending | |
| 1.10 | `doc-page-component-mvp` | Minimal `DocPage` component (no nav/sidebar yet) | M | ✓ | main §4.1, 11.11 §2 | pending | Phase 1 = chrome stub; full chrome in Phase 3a |
| 1.11 | `slug-algorithm` | Material-compatible heading slug | S | ✓ | main §4.7, §9.1 | pending | `pymdownx.slugs.slugify(case="lower")` |
| 1.12 | `code-fence-info-string-parser` | Parse fence headers (`djc_py title="…" hl_lines="…"`) | S | | main §4.7 | pending | |
| 1.13 | `include-file-tag` | `{% include_file "path" %}` template tag | S | | main §4.7, §11.4.F | pending | Sugar over snippets |
| 1.14 | `version-tag` | `{% version %}` template tag | S | | main §4.7 | pending | Returns current docs version |
| 1.15 | `image-tag` | `{% image %}` template tag (optional sugar) | S | | main §4.7 | pending | Markdown img also works |
| 1.16 | `pygments-light-stylesheet` | Light-mode Pygments theme CSS | S | | 11.11 §6.3 | pending | Picked during Phase 1 sample |
| 1.17 | `pygments-dark-stylesheet` | Dark-mode Pygments theme CSS | S | | 11.11 §6.3 | pending | |
| 1.18 | `uv-scripts-entrypoints` | Wire `docs-serve` / `docs-build` / `docs-test` in pyproject.toml | S | ✓ | main §4.8 | pending | Source of truth for CLIs |
| 1.19 | `docs-serve-command` | Dev-loop runserver wrapper | S | | main §4.8 | pending | |
| 1.20 | `docs-build-command-mvp` | Build current version to `docs/v/<version>/` (no manifest yet) | M | ✓ | main §4.6, §4.8, 11.7 §3.1, §6 | pending | Versioning manifest in Phase 5b |
| 1.21 | `docs-test-command-mvp` | Post-build link validator (broken anchors fail) | M | ✓ | main §4.8, §9.8 | pending | Hardened in Phase 3b + 5 |
| 1.22 | `front-matter-schema` | Codified front-matter spec (title, description, og_image, …) + validator | S | ✓ | 11.12 §3.B.11 | pending | Foundational for metadata |
| 1.23 | `docpage-head-block` | Unified `<head>` block (title, description, canonical, lang, viewport, favicon, theme-color, robots, alternate) | M | ✓ | 11.12 §4.C.1 | pending | ~100 LOC; central |
| 1.24 | `page-titles` | `<title>` formatting: `<Page Title> - Django-Components` | S | ✓ | 11.12 §2.A.5 | pending | |
| 1.25 | `per-page-descriptions` | Front-matter > first-paragraph > site-level fallback | M | ✓ | 11.12 §2.A.6 | pending | Three-source priority |
| 1.26 | `canonical-urls` | Versioned pages canonical to `/latest/` counterpart | S | ✓ | 11.12 §2.A.1 | pending | Decision: latest is canonical |
| 1.27 | `per-version-noindex` | `noindex,follow` on pages under non-current/non-previous `/v<x>/` | S | | 11.12 §4.C.3 | pending | ~10 LOC in head builder |
| 1.28 | `markdown-companion-urls` | Serve every page also at `…/page.md` (raw markdown) | S | ✓ | 11.12 §3.B.2 | pending | Highest-leverage AI-discovery feature |
| 1.29 | `json-ld-breadcrumbs` | BreadcrumbList JSON-LD on every page | S | | 11.12 §2.A.7 | pending | TechArticle deferred to Phase 5c |
| 1.30 | `placeholder-home-page` | Thin `/` placeholder (replaced in Phase 9) | S | | main §8 | pending | Nav works end-to-end |

**Out of scope here:** API reference (Phase 4), examples (Phase 2), sidebar/header chrome (Phase 3a), search (Phase 5a), versioning manifest (Phase 5b), SEO/AIO polish (Phase 5c).

---

## Phase 2 — `{% example %}` end-to-end (the killer feature)

Goal: one example (suggested: `fragments`) renders interactively in a docs page, with code + page + live-render tabs, with pre-rendered fragments fetched correctly.

**Sharp focus:** prove the live-component + fragment-pre-render trick; resist building all examples.

| # | ID | Name | Effort | Critical | Source | Status | Notes |
|---|---|---|---|---|---|---|---|
| 2.1 | `example-autodiscovery` | Walk `docs_site/examples/` and register Page components | S | ✓ | main §2.4 | pending | Same pattern as sampleproject |
| 2.2 | `docs-example-convention` | `class DocsExample` metadata on Page components | S | | main §4.4a | pending | `fragments = ["alpine", "htmx", "js"]` |
| 2.3 | `fragment-pre-render` | Pre-render every fragment variant to `static/fragments/…` | M | ✓ | main §4.4a | pending | Path-keyed URLs |
| 2.4 | `example-card-component` | `ExampleCard` Django component (tabbed code + render) | M | ✓ | main §4.2 | pending | The centerpiece |
| 2.5 | `example-tag` | `{% example "name" %}` template tag | S | ✓ | main §4.2, §11.4.E | pending | |
| 2.6 | `stable-example-ids-guardrail` | Detect renames of `examples/<name>/` in PR | S | | 11.12 §3.B.5 | pending | Prevents breaking LLM-cached URLs |
| 2.7 | `example-contract-check` | Validate every `{% example %}` has matching dir with `Page` + tests | M | | 11.10 §3.6 | pending | Static + importlib check |

**Out of scope here:** the other examples (those are content port, Phase 3b); all the chrome.

---

## Phase 3a — Theme + core chrome (the page feels like a real docs site)

Goal: a markdown page renders with header + sidebar + right-rail TOC + code blocks + dark mode, on desktop. Mobile and content port deferred.

**Sharp focus:** the visual system. Tokens, layout, typography, code blocks, admonitions.

| # | ID | Name | Effort | Critical | Source | Status | Notes |
|---|---|---|---|---|---|---|---|
| 3a.1 | `design-tokens-css` | OKLCH design-tokens CSS file | S | ✓ | 11.11 §10, §11.1 | pending | Foundation |
| 3a.2 | `light-theme-tokens` | Light-mode token values | S | ✓ | 11.11 §10 | pending | Accent decision deferred to Juro |
| 3a.3 | `dark-theme-tokens` | Dark-mode token values | S | ✓ | 11.11 §10 | pending | |
| 3a.4 | `theme-fouc-prevention` | Inline `<script>` in head reads localStorage before paint | S | ✓ | 11.11 §9.1 | pending | |
| 3a.5 | `inter-font-link` | Inter font (CDN or self-hosted) | S | | 11.11 §10.6 | pending | Self-host if zero-off-origin required |
| 3a.6 | `prose-typography` | Body, headings, links, anchored-heading hover | S | ✓ | 11.11 §5.1-5.3 | pending | CSS-only |
| 3a.7 | `inline-code-styling` | Inline `<code>` styled as accent pills | S | | 11.11 §5.4 | pending | One CSS rule |
| 3a.8 | `code-block-component` | `<pre><code>` with language label + copy button | M | ✓ | 11.11 §6.2-6.3 | pending | Minimal chrome |
| 3a.9 | `tabbed-code-component` | `CodeTabs` (multi-tab fences + example widget tabs + filename) | M | | 11.11 §6.4 | pending | Reusable |
| 3a.10 | `blockquote-styling` | Left-border, muted fg | S | | 11.11 §5.5 | pending | |
| 3a.11 | `table-styling` | Cell borders, header bg, mono first-col auto-detect | S | | 11.11 §5.6 | pending | |
| 3a.12 | `admonition-component` | Note/info/warning with accent border + tinted bg | S | ✓ | 11.11 §5.7 | pending | Get free from pymdownx or wrap |
| 3a.13 | `list-styling` | Standard CommonMark lists | S | | 11.11 §5.8 | pending | |
| 3a.14 | `header-component` | 64px sticky header (logo, top-nav, search trigger, version, theme, GitHub) | M | ✓ | 11.11 §4 | pending | Drives all nav |
| 3a.15 | `sidebar-component` | 280px sticky left sidebar (nested 2-level nav, collapsible groups, active highlight, scroll-into-view) | M | ✓ | 11.11 §3 | pending | Requires nav YAML |
| 3a.16 | `right-toc-component` | 240px sticky right rail (H2/H3 scroll-spy) | M | ✓ | 11.11 §7.1, §2.2 | pending | Hidden < 1024px |
| 3a.17 | `doc-page-layout` | 3-column shell (sidebar / content / TOC), 1280px max-width | M | ✓ | 11.11 §2 | pending | Replaces Phase 1 stub |
| 3a.18 | `theme-toggle-button` | 3-mode cycle (auto / light / dark) wired to localStorage | M | ✓ | 11.11 §4.1, §9 | pending | |
| 3a.19 | `nav-yaml-loader` | Loads + validates single `_nav.yml` | S | ✓ | 11.9 §2.2 | pending | ~80 LOC; replaces awesome-nav |
| 3a.20 | `breadcrumbs-component` | Above-H1 breadcrumb trail | S | | 11.11 §7.2 | pending | From nav tree |
| 3a.21 | `page-nav-component` | Prev/Next cards at bottom | S | | 11.11 §7.3 | pending | From nav order |
| 3a.22 | `site-css` | Bundled prose + components + utilities stylesheet | M | ✓ | 11.11 §5, §6, §11.1 | pending | Incrementally built |
| 3a.23 | `site-js` | Bundled interactivity (search trigger, theme, sidebar persistence, scroll-spy, copy, drawer) | M | ✓ | 11.11 §3.3, §4.1, §7.1, §6.2, §8, §9.1 | pending | Mostly vanilla |

**Out of scope here:** mobile breakpoints (Phase 3b), Pagefind UI (Phase 5a), content port (Phase 3b).

---

## Phase 3b — Mass content port + responsive + content-layer guardrails

Goal: every existing markdown page renders correctly under the new pipeline + chrome, on desktop + mobile. All content-layer guardrails wired into CI.

**Sharp focus:** content fidelity. Resist building anything API-reference- or search-related.

| # | ID | Name | Effort | Critical | Source | Status | Notes |
|---|---|---|---|---|---|---|---|
| 3b.1 | `mobile-drawer` | Full-height left drawer; hamburger toggle | M | ✓ | 11.11 §4.1, §2.2 | pending | < 768px |
| 3b.2 | `mobile-header-actions` | Overflow menu for version + theme + GitHub | S | | 11.11 §4.1 | pending | < 768px |
| 3b.3 | `mobile-toc-details` | `<details>` "On this page" disclosure under H1 | S | | 11.11 §2.2, §7.1 | pending | < 1024px |
| 3b.4 | `responsive-breakpoints` | 4 breakpoints wired flexbox-side | M | ✓ | 11.11 §2.2 | pending | |
| 3b.5 | `release-notes-parser` | Parse CHANGELOG.md → per-release pages + index | S | | 11.9 §2.1 | pending | ~80 LOC port |
| 3b.6 | `people-page-template` | Native Django template (replace mkdocs-macros) | S | | 11.9 §2.7 | pending | Single page |
| 3b.7 | `ai-bot-policy-doc` | New `content/community/ai_bot_policy.md` | S | | 11.12 §3.B.10 | pending | ~30 lines |
| 3b.8 | `template-render-guard` | Catch Django template errors in Pass 1 | S | ✓ | 11.10 §3.1 | pending | Built into Django |
| 3b.9 | `fence-validator` | Detect unclosed fences, malformed snippets, unknown languages | M | ✓ | 11.10 §3.2 | pending | Reuses scanner from 1.6 |
| 3b.10 | `lexer-alias-check` | Validate fence info-strings resolve to Pygments lexer | S | | 11.10 §3.3 | pending | Allowlist for `mermaid` etc. |
| 3b.11 | `snippet-path-check` | Validate `--8<--` targets exist within `base_path` | S | ✓ | 11.10 §3.7 | pending | Config-driven |
| 3b.12 | `internal-link-check` | Walk built HTML, assert every internal `<a href>` resolves | M | ✓ | 11.10 §3.9 | pending | Reuses SiteIndex |
| 3b.13 | `anchor-check` | Every `#anchor` href maps to an `id=` | S | ✓ | 11.10 §3.10 | pending | |
| 3b.14 | `image-asset-check` | `<img src>`, `<script src>`, `<link href>` to local assets exist | S | | 11.10 §3.12 | pending | |
| 3b.15 | `nav-yaml-validity-check` | Content ↔ `_nav.yml` 2-way drift | M | | 11.10 §3.14 | pending | |
| 3b.16 | `html-wellformedness-check` | lxml.html parse with `recover=False` | S | | 11.10 §3.15 | pending | Must run pre-minify |
| 3b.17 | `snapshot-regression-test` | pytest + syrupy on curated 8-page set | M | | 11.10 §3.17 | pending | Starts at 3, grows |
| 3b.18 | `site-index` | Shared post-build HTML walker (~120 LOC) | M | ✓ | 11.10 §6 | pending | Powers all post-build guards |
| 3b.19 | `guardrail-runner-harness` | Orchestrator (~100 LOC) — severity rules, dep order | M | ✓ | 11.10 §6 | pending | Powers docs-build + docs-build-check |
| 3b.20 | `single-h1-guardrail` | Exactly one `<h1>` per page | S | | 11.12 §2.A.8 | pending | |
| 3b.21 | `image-alt-text-guardrail` | Every `<img>` has non-empty `alt` | S | | 11.12 §2.A.9 | pending | Content audit also runs here |
| 3b.22 | `structured-headings-guardrail` | No `##` → `####` jumps | S | | 11.12 §3.B.3 | pending | Supports `.md` companion quality |
| 3b.23 | `code-block-language-tags-guardrail` | Missing language tag = error (with allowlist) | S | | 11.12 §3.B.4 | pending | Extension of 3b.10 |
| 3b.24 | `git-metadata-fetcher` | DIY subprocess `git log` for last-updated + authors | S | | 11.9 §2.3 | pending | ~100 LOC; `fetch-depth: 0` in CI |
| 3b.25 | `content-port-sweep` | Move every existing page; fix `--8<--` paths, links | L | ✓ | main §5 Phase 3 | pending | Mostly mechanical |

**Out of scope here:** API reference (Phase 4), Pagefind (Phase 5a), versioning (Phase 5b), SEO polish (Phase 5c).

---

## Phase 4 — API reference (the big one)

Goal: feature parity with mkdocstrings on the 14 current reference pages, with the discovery → rendering split, dual anchors, full cross-ref resolution.

**Sharp focus:** mkdocstrings replacement. Resist anything that isn't on the reference path.

| # | ID | Name | Effort | Critical | Source | Status | Notes |
|---|---|---|---|---|---|---|---|
| **Discovery layer (Layer 1)** | | | | | | | |
| 4.1 | `discover-kinds-adt` | `ReferencePage` / `ReferenceEntry` types | S | ✓ | 11.5 §5.1, §10 | pending | Located at `docs_site/apps/docs/discovery/kinds.py` |
| 4.2 | `discover-layer` | Discovery orchestrator (Layer 1) | L | ✓ | 11.5 §5.1, §5.3 | pending | Foundation |
| 4.3 | `discover-walk` | Walk script: load griffe with `force_inspection=True` | M | ✓ | 11.5 §5.1, §10 | pending | Metaclass attrs need inspection |
| 4.4 | `discover-page-api` | API page (kinds 1-5: components, fns, decorators, instances, NamedTuples) | M | ✓ | 11.5 §3.1, §10 | pending | |
| 4.5 | `discover-page-exceptions` | Exceptions page (kind 6) | S | ✓ | 11.5 §3.1, §9 | pending | **Proof-of-concept page**; do this first |
| 4.6 | `discover-page-components` | Components page (kind 7: predefined Component subclasses) | M | | 11.5 §3.1, §10 | pending | |
| 4.7 | `discover-page-settings` | Settings page (kind 8: ComponentsSettings fields) | M | | 11.5 §3.1, §10 | pending | Per-field griffe docstrings |
| 4.8 | `discover-page-tag-formatters` | Tag formatters (kinds 9-10) | M | | 11.5 §3.1 | pending | |
| 4.9 | `discover-page-commands` | Management commands (kind 11) | L | ✓ | 11.5 §3.1 | pending | argparse introspection |
| 4.10 | `discover-page-template-tags` | Template tags (kind 12) | M | ✓ | 11.5 §3.1 | pending | `BaseNode._signature` via force_inspection |
| 4.11 | `discover-page-urls` | URL patterns (kind 13) | S | | 11.5 §3.1 | pending | |
| 4.12 | `discover-page-template-vars` | Template vars (kind 14: ComponentVars) | S | | 11.5 §3.1 | pending | |
| 4.13 | `discover-page-testing` | Testing API (kind 15) | S | | 11.5 §3.1 | pending | |
| 4.14 | `discover-page-extension-hooks` | Extension hooks + contexts (kinds 16-17) | M | ✓ | 11.5 §3.1 | pending | Via decorator detection |
| 4.15 | `discover-page-extension-commands` | Extension command API (kind 18) | M | | 11.5 §3.1 | pending | |
| 4.16 | `discover-page-extension-urls` | Extension URL API (kind 19) | M | | 11.5 §3.1 | pending | |
| 4.17 | `discover-page-signals` | Signals placeholder (kind 20) | S | | 11.5 §3.1, §9 | pending | Markdown island for now |
| **Griffe extensions** | | | | | | | |
| 4.18 | `griffe-ext-runtime-bases` | `RuntimeBasesExtension` ported | S | ✓ | 11.5 §8 | pending | One-line config swap |
| 4.19 | `griffe-ext-source-code` | `SourceCodeExtension` ported | S | ✓ | 11.5 §8 | pending | Portable verbatim |
| **Cross-ref + inventory** | | | | | | | |
| 4.20 | `inventory-builder` | Parse stdlib + Django `objects.inv` → name→URL map | M | ✓ | 11.5 §2, §6 | pending | ~100 LOC |
| 4.21 | `signature-crossrefs` | Walk griffe `Expr` trees → resolve `ExprName` → emit links | L | ✓ | 11.5 §2, §6 | pending | 712+ links on api.md alone |
| 4.22 | `inventory-output` | Emit `site/objects.inv` for external linkbacks | M | ✓ | 11.5 §6 | pending | 7034 bytes |
| **Entry renderers (per-kind components)** | | | | | | | |
| 4.23 | `render-ref-class` | `ReferenceClass` (kinds 1-6, 15, 18-19) | L | ✓ | 11.5 §3.2 #1 | pending | Workhorse |
| 4.24 | `render-component-class` | `ReferenceComponentClass` (kind 7) | M | | 11.5 §3.2 #2 | pending | Filters Component base |
| 4.25 | `render-setting` | `ReferenceSetting` (kinds 8, 14) | M | | 11.5 §3.2 #3 | pending | |
| 4.26 | `render-tag-formatter` | `ReferenceTagFormatter` (kind 9) | S | | 11.5 §3.2 #4 | pending | |
| 4.27 | `render-management-command` | `ReferenceManagementCommand` (kind 11) | L | ✓ | 11.5 §3.2 #5 | pending | Most bespoke layout |
| 4.28 | `render-template-tag` | `ReferenceTemplateTag` (kind 12) | M | ✓ | 11.5 §3.2 #6 | pending | |
| 4.29 | `render-url-pattern` | `ReferenceURLPattern` (kind 13) | S | | 11.5 §3.2 #7 | pending | Trivial bullets |
| 4.30 | `render-extension-hook` | `ReferenceExtensionHook` (kind 16) | M | ✓ | 11.5 §3.2 #8 | pending | Custom 'Available data' table |
| 4.31 | `render-hook-context` | `ReferenceHookContext` (kind 17) | M | ✓ | 11.5 §3.2 #9 | pending | 15 contexts |
| 4.32 | `render-signal` | `ReferenceSignal` placeholder (kind 20) | S | | 11.5 §3.2 #10 | pending | No-op |
| 4.33 | `render-instances-list` | `AvailableInstancesList` (kind 10) | S | | 11.5 §3.2 #11 | pending | |
| 4.34 | `render-settings-defaults-panel` | `SettingsDefaultsPanel` companion | M | | 11.5 §3.2 #12 | pending | Page-level |
| **Shared sub-components** | | | | | | | |
| 4.35 | `sub-signature-block` | `SignatureBlock` (lang-aware fenced sig) | S | ✓ | 11.5 §4 | pending | Reused by ~8 entry templates |
| 4.36 | `sub-source-code-link` | `SourceCodeLink` (repo file#L42 link) | S | ✓ | 11.5 §4 | pending | |
| 4.37 | `sub-parameters-table` | `ParametersTable` (name/type/desc rows) | M | ✓ | 11.5 §4 | pending | |
| 4.38 | `sub-docstring-body` | `DocstringBody` (Google sections + md_in_html) | M | ✓ | 11.5 §4 | pending | |
| 4.39 | `sub-admonitions-block` | `AdmonitionsBlock` (`!!! note` in docstrings) | S | | 11.5 §4 | pending | |
| 4.40 | `sub-examples-block` | `ExamplesBlock` (fenced code from `Examples:`) | S | | 11.5 §4 | pending | |
| 4.41 | `sub-cross-ref` | `CrossRef` (bracket refs `[X][]` → URL) | M | ✓ | 11.5 §2, §4, §6 | pending | Merges project + inventories |
| 4.42 | `sub-symbol-type-badge` | `SymbolTypeBadge` (`<span class="doc doc-symbol-X">`) | S | | 11.5 §4, §6 | pending | |
| **Page layouts** | | | | | | | |
| 4.43 | `page-layout-api` | API page layout | M | ✓ | 11.5 §5.2 | pending | |
| 4.44 | `page-layout-exceptions` | Exceptions page layout (POC) | S | ✓ | 11.5 §5.2 | pending | |
| 4.45 | `page-layout-components` | Components page layout | S | | 11.5 §5.2 | pending | |
| 4.46 | `page-layout-settings` | Settings page layout (entries + defaults panel) | M | | 11.5 §5.2 | pending | |
| 4.47 | `page-layout-tag-formatters` | Tag formatters (classes + instances) | M | | 11.5 §5.2 | pending | Fix layout bug §7.6 |
| 4.48 | `page-layout-commands` | Commands (command_tree layout) | M | ✓ | 11.5 §5.2 | pending | |
| 4.49 | `page-layout-template-tags` | Template tags layout | M | ✓ | 11.5 §5.2 | pending | |
| 4.50 | `page-layout-urls` | URL patterns layout | S | | 11.5 §5.2 | pending | |
| 4.51 | `page-layout-template-vars` | Template variables layout | S | | 11.5 §5.2 | pending | |
| 4.52 | `page-layout-testing` | Testing API layout | S | | 11.5 §5.2 | pending | |
| 4.53 | `page-layout-extension-hooks` | Extension hooks + contexts (hooks_plus_objects) | M | ✓ | 11.5 §5.2 | pending | |
| 4.54 | `page-layout-extension-commands` | Extension commands layout | S | | 11.5 §5.2 | pending | |
| 4.55 | `page-layout-extension-urls` | Extension URLs layout | S | | 11.5 §5.2 | pending | |
| 4.56 | `page-layout-signals` | Signals placeholder layout | S | | 11.5 §5.2 | pending | |
| **Tag + glue** | | | | | | | |
| 4.57 | `docstring-tag` | `{% docstring "x.y.z" %}` template tag | S | ✓ | main §4.3, §11.4.E | pending | |
| 4.58 | `anchor-scheme-legacy-compat` | Dual anchors: new `#Component` + legacy `#django_components.Component` | S | ✓ | 11.5 §7.1-7.2 | pending | Preserves 397+578 inbound links |
| 4.59 | `routing-decorator-detection` | `@mark_extension_hook_api` decorator detection | S | ✓ | 11.5 §7.3 | pending | |
| 4.60 | `property-docstring-griffe` | Retire `_extract_property_docstrings` for griffe access | M | ✓ | 11.5 §7.4 | pending | |
| 4.61 | `snapshot-tests-discovery` | Snapshot tests for `ReferencePage[]` | M | | 11.5 §5.3 | pending | |
| 4.62 | `api-symbol-forward-check` | `{% docstring %}` references must resolve | M | ✓ | 11.10 §3.4 | pending | Pass-1 check |
| 4.63 | `api-symbol-reverse-check` | Public API symbols never referenced = warning | M | | 11.10 §3.5 | pending | Upgrades to error in `--strict` |
| 4.64 | `anchor-alias-coverage` | Renamed symbols have legacy aliases | S | | 11.10 §3.11 | pending | Warning severity |
| **Proof-of-concept escalation** | | | | | | | |
| 4.65 | `proof-exceptions-page` | Build exceptions.md end-to-end first | M | ✓ | 11.5 §9 | pending | Validates contract; ~1 day |
| 4.66 | `proof-component-page` | Build Component class entry second | L | ✓ | 11.5 §9 | pending | Exercises shared sub-components |

**Out of scope here:** anything not on the API-reference path.

---

## Phase 5a — Search

Goal: Pagefind-powered search with custom UI feels at least as good as Material's search.

**Sharp focus:** search only. Resist versioning, SEO, social cards in this sub-phase.

| # | ID | Name | Effort | Critical | Source | Status | Notes |
|---|---|---|---|---|---|---|---|
| 5a.1 | `pagefind-integration` | Run `pagefind` CLI post-build; chunked indexes; per-page weights | S | ✓ | main §4.5, §11.1 | pending | |
| 5a.2 | `search-overlay-component` | Centered modal: input + results + keyboard nav (↑↓ Enter Esc) | M | ✓ | 11.11 §8 | pending | |
| 5a.3 | `search-bar-component` | Header trigger that opens overlay | M | ✓ | main §4.5, §11.1.G.5 | pending | |
| 5a.4 | `search-states` | Empty / no-results / error states | S | | 11.11 §8.3 | pending | |
| 5a.5 | `search-v1-features` | `/` `Ctrl+K` `Esc` shortcuts; `?q=` deep link; `?h=` in-page highlight; mobile a11y; delayed spinner | M | ✓ | 11.1.G.2 | pending | |
| 5a.6 | `custom-404-page` | 404 with search bar + common destinations | M | | 11.12 §2.A.12 | pending | |

**Out of scope here:** versioning, SEO, social cards.

---

## Phase 5b — Versioning

Goal: `docs-build` + `docs-build-all` + `version_picker` + `versions.json` flow works end-to-end, with `docs/v/<version>/` committed to `master`.

**Sharp focus:** versioning only.

| # | ID | Name | Effort | Critical | Source | Status | Notes |
|---|---|---|---|---|---|---|---|
| 5b.1 | `verspec-dep` | Add `verspec` dependency | S | ✓ | 11.7 §2.1, §12 | pending | LooseVersion sort |
| 5b.2 | `mike-versions-vendor` | Vendor mike's `Versions` + `VersionInfo` classes | S | ✓ | 11.7 §2.1, §9 | pending | BSD-3 attribution |
| 5b.3 | `mike-redirect-vendor` | Vendor mike's `redirect.html` template | S | ✓ | 11.7 §2.3, §4.4 | pending | 15 lines |
| 5b.4 | `versions-json-schema` | `versions.json` manifest (mike-compatible) | S | ✓ | 11.7 §4 | pending | |
| 5b.5 | `build-info-stamp` | Per-version `_build_info.json` (version, source_sha, builder_version) | S | ✓ | 11.7 §3.3 | pending | Enables idempotent rebuilds |
| 5b.6 | `version-sorter` | Use verspec.LooseVersion; sentinel handling | S | | 11.7 §2.1, §8.1 | pending | |
| 5b.7 | `docs-build-cmd` | Full `docs-build [--version] [--alias]` (replaces MVP from Phase 1) | M | ✓ | 11.7 §3.1, §6 | pending | |
| 5b.8 | `docs-build-all-cmd` | Bootstrap walker (`docs-build-all`) | M | ✓ | 11.7 §3.2, §3.3, §8.1 | pending | Worktree-based |
| 5b.9 | `worktree-orchestration` | Worktree add/remove lifecycle in docs-build-all | S | ✓ | 11.7 §3.2, §8.1 | pending | try/finally + prune |
| 5b.10 | `alias-redirect-materializer` | Materialize `latest/` etc. as redirect HTML | S | ✓ | 11.7 §2.4, §3.1 | pending | |
| 5b.11 | `version-picker-component` | Header dropdown reads versions.json | M | ✓ | main §4.6, 11.7 §5, 11.11 §4.1 | pending | |
| 5b.12 | `docs-versions-toml` | Top-level TOML config | S | | 11.7 §3.2 | pending | |
| 5b.13 | `docs-build-check-cmd` | Inverse CI check: manifest ↔ FS parity | M | | 11.7 §11 | pending | ~150-200 LOC |
| 5b.14 | `versions-manifest-integrity-check` | Manifest ↔ dir 2-way sync guardrail | S | | 11.10 §3.16 | pending | |
| 5b.15 | `cross-version-link-check` | Links from `/v0.X/` to `/v0.Y/` resolve | M | | 11.10 §3.8 | pending | Only with ≥2 versions on disk |
| 5b.16 | `ci-release-docs-workflow` | Rewrite `release-docs.yml` (tag → docs-build → commit → push) | S | ✓ | 11.7 §3.1, §6, §8.2 | pending | |
| 5b.17 | `docs-build-check-command` | Pre-commit CI gate (full build to temp, all guardrails) | M | ✓ | 11.9 §4 | pending | ~80 LOC |

**Out of scope here:** SEO/AIO polish; cutover (Phase 6).

---

## Phase 5c — SEO + AIO + social cards + chrome polish

Goal: every SEO/AIO feature wired. Site is Lighthouse-clean and AI-bot-friendly. Social cards generated.

**Sharp focus:** discoverability + polish only.

| # | ID | Name | Effort | Critical | Source | Status | Notes |
|---|---|---|---|---|---|---|---|
| 5c.1 | `sitemap-xml` | `sitemap.xml` (latest/ URLs + git lastmod + changefreq + priority) | M | | 11.12 §2.A.2 | pending | |
| 5c.2 | `robots-txt` | `robots.txt` (disallow old versions; AI-bot rules; sitemap pointer) | S | | 11.12 §2.A.3 | pending | |
| 5c.3 | `og-image-generation` | OG image PNG per page (via Playwright) | L | | 11.12 §2.A.4, 11.9 §2.4 | pending | |
| 5c.4 | `og-card-template` | Django template for 1200×630 social card | S | | 11.9 §2.4 | pending | |
| 5c.5 | `social-card-generator` | Orchestration (Playwright headless) | L | | 11.9 §2.4 | pending | ~230 LOC total |
| 5c.6 | `social-card-caching` | Hash + sidecar JSON cache | S | | 11.9 §2.4 | pending | |
| 5c.7 | `og-twitter-cards` | Per-page OG + Twitter card `<meta>` | M | | 11.12 §2.A.4 | pending | |
| 5c.8 | `json-ld-techarticle` | TechArticle JSON-LD on content pages | M | | 11.12 §2.A.7 | pending | Skip SoftwareSourceCode / HowTo |
| 5c.9 | `json-ld-validity-guardrail` | Build-time JSON-LD schema validation | S | | 11.12 §2.A.7, §11.10 | pending | |
| 5c.10 | `llms-txt` | `/llms.txt` short index + `/llms-full.txt` concatenation | M | | 11.12 §3.B.1 | pending | High-leverage AI feature |
| 5c.11 | `indexing-manifest` | `meta/indexing.json` (URLs + canonicals + robots directives) | M | | 11.12 §4.C.5 | pending | |
| 5c.12 | `anchor-deprecation-timer` | 12-month timer on legacy anchor aliases | S | | 11.12 §2.A.13, §7.2 | pending | |
| 5c.13 | `lighthouse-ci` | GitHub Actions workflow with Perf/A11y/SEO thresholds | M | | 11.12 §2.A.14 | pending | |
| 5c.14 | `html-minifier` | minify-html post-build pass | S | | 11.9 §2.6 | pending | Rust-based |
| 5c.15 | `html-sanitizer` | bleach/html5lib sanitization pass | S | | main §4.7 | pending | |
| 5c.16 | `edit-on-github-url` | Edit-on-GitHub button per page | S | | main §9.3 | pending | |
| 5c.17 | `redirect-file-emitter` | Static `<meta refresh>` HTML stubs for moved URLs | S | | 11.9 §2.5, main §9.5 | pending | |
| 5c.18 | `redirect-target-check` | Redirect targets resolve in built site | S | | 11.10 §3.13 | pending | |
| 5c.19 | `external-link-check` | Weekly lychee workflow (out-of-band) | S | | 11.10 §3.18 | pending | Not a PR blocker |

**Out of scope here:** cutover (Phase 6).

---

## Phase 6 — Cutover

Goal: GitHub Pages serves from `master/docs/v/`. Old `gh-pages` retained for rollback. Inbound URLs preserved.

**Sharp focus:** cutover and only cutover.

| # | ID | Name | Effort | Critical | Source | Status | Notes |
|---|---|---|---|---|---|---|---|
| 6.1 | `materialize-redirects-script` | Convert `latest/` symlink → redirect HTML files | S | ✓ | 11.8 §6, §7 | pending | ~50 LOC; Windows-compat |
| 6.2 | `import-gh-pages-tree` | One-time mirror of `origin/gh-pages` into `master/docs/v/` (57 versions + dev) | M | ✓ | 11.8 §5.1, §7 | pending | ~30 min execution |
| 6.3 | `docs-build-check-validation` | Validate imported tree before commit | S | ✓ | 11.8 §5.1, §7 | pending | Cutover gate |
| 6.4 | `github-pages-source-switch` | Repo setting: `gh-pages` branch → `master/docs/v/` | S | ✓ | 11.8 §5.1 | pending | Final activation step |
| 6.5 | `gh-pages-branch-deletion` | Delete `gh-pages` branch (deferred 3-6 months) | S | | 11.8 §5.1, §8.2 | pending | Cleanup, not blocker |

---

## Phase 5d — Feature-parity audit (process, not buildables)

Goal: before cutover, decide port/defer/skip for every Material/Zensical feature row not yet replicated. See main doc §8 Phase 5d for the procedure.

No standalone feature rows here; the audit may produce small "port now" tickets which get logged into the appropriate earlier-phase section (typically 3a / 3b / 5c) before cutover.

---

## Phase 7 — Search v2 (post-cutover power-user polish)

Goal: power-user search features.

| # | ID | Name | Effort | Critical | Source | Status | Notes |
|---|---|---|---|---|---|---|---|
| 7.1 | `search-v2-autocomplete` | Inline autocomplete suggestions in the search input | M | | 11.1.G.3 | pending | |
| 7.2 | `search-v2-recent-searches` | Local-stored recent-search history | S | | 11.1.G.3 | pending | |
| 7.3 | `search-v2-filters` | Scoping filters (e.g. API only, examples only) | M | | 11.1.G.3 | pending | |
| 7.4 | `search-v2-typo-recovery` | Fallback scoring borrowing Emil's algorithm (§11.1.C) | M | | 11.1.C, 11.1.G.3 | pending | |

---

## Phase 8 — Search v3 (blocked on analytics target)

| # | ID | Name | Effort | Critical | Source | Status | Notes |
|---|---|---|---|---|---|---|---|
| 8.1 | `search-v3-analytics` | Search-result analytics | M | | 11.1.G.4 | pending | **Blocked.** Choose Plausible / GoatCounter / Cloudflare Worker / self-hosted endpoint first. |

---

## Phase 9 — Landing page (codesign)

Goal: replace the Phase-1 thin scaffold at `/` with the real landing page.

| # | ID | Name | Effort | Critical | Source | Status | Notes |
|---|---|---|---|---|---|---|---|
| 9.1 | `landing-page-component` | Full landing page (no sidebar/TOC; hero, features, CTAs) | M | | 11.11 §4.4 | pending | Codesign — multiple short sessions |

---

## Phase 10+ — Deferred / post-launch maintenance

Tracked so they don't get lost, NOT a checklist for any single agent session.

| # | ID | Name | Effort | Critical | Source | Status | Notes |
|---|---|---|---|---|---|---|---|
| 10.1 | `selective-rebuild-policy` | Rebuild 0.148+ historical versions with new builder | M | | 11.8 §5.2 | pending | Driven by analytics |
| 10.2 | `url-redirect-map-pre-0124` | Manual redirects for pre-0.124 broken URLs | L | | 11.8 §9 | pending | Only if traffic > threshold |
| 10.3 | `version-pruning-policy` | Move pre-0.110 versions to `docs-archive` orphan branch | M | | 11.8 §5.2 | pending | Optional cleanup |
| 10.4 | `cve-bundle-audit` | CVE audit on frozen Material/plugin bundles | M | | 11.8 §8.1 | pending | One-off sweep |
| 10.5 | `docs-versions-toml-per-version-freeze-flag` | Per-version `freeze=true` schema extension | S | | 11.8 §9 | pending | Only if needed |
| 10.6 | `sitemap-strategy` | Sitemap-index aggregating only latest/ | S | | 11.8 §8.2 | pending | Optional |
| 10.7 | `dev-deploy-ci-flow` | Decide whether `dev/` commits or deploys separately | M | | 11.8 §8.1 | pending | Could land earlier if 5b implementation forces it |

---

## Cross-cutting / not phase-bound

| ID | Name | Phase | Notes |
|---|---|---|---|
| `legacy-anchor-alias-mechanism` | Legacy anchor aliases | 4 (rendered) | Lives inside `anchor-scheme-legacy-compat` |

---

## Roll-up

| Phase | Goal | Count | Critical |
|---|---|---|---|
| 0 | Pre-work in `src/` | 4 | 2 |
| 1 | Foundation: 1 page end-to-end | 30 | 21 |
| 2 | `{% example %}` end-to-end | 7 | 4 |
| 3a | Theme + core chrome | 23 | 17 |
| 3b | Mass content port + responsive + content guardrails | 25 | 12 |
| 4 | API reference (mkdocstrings replacement) | 66 | 30 |
| 5a | Search v1 | 6 | 4 |
| 5b | Versioning | 17 | 12 |
| 5c | SEO + AIO + chrome polish | 19 | 0 |
| 5d | Feature-parity audit (process) | 0 | 0 |
| 6 | Cutover | 5 | 4 |
| 7 | Search v2 (post-cutover polish) | 4 | 0 |
| 8 | Search v3 (blocked on analytics target) | 1 | 0 |
| 9 | Landing page (codesign) | 1 | 0 |
| 10+ | Deferred / post-launch maintenance | 7 | 0 |
| **Total** | | **215** | **106** |

If something is missing here, **add it**. This file is the canonical inventory.
