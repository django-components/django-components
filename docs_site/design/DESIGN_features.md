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
| 0.3 | `docs-convention-community` | Document docstring convention in `docs/community/development.md` | M | | 11.5 §11.6 | **done** (14554db7) | "Writing docstrings" subsection under "Documentation website" |
| 0.4 | `docs-convention-claude` | Add docstring rule to `CLAUDE.md` | S | | 11.5 §11.6 | **done (local-only)** | `CLAUDE.md` is intentionally untracked, so the edit stays local and is not committed. The rule itself is written and active for AI agents that load CLAUDE.md. |

**Out of scope here:** any code under `docs_site/`.

---

## Phase 1 — Foundation: render ONE page end-to-end

Goal: a single page (e.g. `getting_started/index.md`) renders through the 3-pass pipeline to a static file in `docs/v/<version>/`, with full `<head>` metadata. No nav chrome yet; no API reference; no examples.

**Sharp focus:** prove the pipeline, the file layout, and the metadata story. Resist building chrome.

| # | ID | Name | Effort | Critical | Source | Status | Notes |
|---|---|---|---|---|---|---|---|
| 1.0a | `docs-old-rename` | Rename `docs/` → `docs_old/`; repoint every config/script/workflow so old mkdocs still builds locally; free `docs/` for internal docs (agent-knowledge + README pointer) | M | ✓ | main §4.0a | **done** | `git mv`; updated mkdocs.yml, pyproject (testpaths/ruff), asv.conf.json, sampleproject `EXAMPLES_DIR`, scripts, workflows, example snippet paths. Verified: mkdocs builds (only the known Phase-0 autorefs warnings), pytest collects examples. Internal `docs/` now holds `agent-knowledge/` (local) + `README.md` |
| 1.1 | `docs-site-django-project` | `docs_site/` Django project scaffold | S | ✓ | main §4.1 | **done** | settings, urls, wsgi, manage.py |
| 1.2 | `docs-app-scaffold` | `apps/docs/` with components/, templatetags/, management/commands/ | S | ✓ | main §4.1 | **done** | Includes `docs_extras.py` with `{% version %}` tag |
| 1.3 | `content-dir-structure` | Move user-facing pages → `docs_site/content/` (markdown source) | S | | main §4.0a, §4.1, 11.4.G | **moved to Phase 3b** (3b.25) | The content move IS the Phase 3b content-port sweep. (Originally parked for Phase 6 to "keep mkdocs building on the branch" - but the branch cannibalizes mkdocs and Phase 6 compares against the *deployed* old site, so the move can happen now. See main §8 branch model.) Source was renamed `docs/` → `docs_old/` first (see 1.0a) |
| 1.4 | `examples-dir-moved` | Move examples → `docs_site/examples/` | S | | main §4.1 | **moved to Phase 6** (6.8) | Examples stay at `docs_old/examples/` until cutover. (Not a "keep mkdocs building" constraint - it's just that nothing forces the examples move earlier; the `{% example %}` tag reads `EXAMPLES_DIR`, which can point at `docs_old/examples/` meanwhile. Can be pulled into the migration if convenient.) |
| 1.5 | `pygments-djc-loader` | Load `pygments_djc` lexer at command startup | S | ✓ | main §2.1, 11.9 §2.1 | **done** | `import pygments_djc` at the top of the build commands (`build_docs`, etc.) |
| 1.6 | `fence-protection-scanner` | Wrap code regions in `{% verbatim %}` before Django pass | S | ✓ | main §4.7, §11.4.C | **done** | `fence_protection.py` ~100 LOC; handles fenced blocks + inline code spans |
| 1.7 | `markdown-pipeline-pass1` | Pass 1: Django template engine on markdown source | S | ✓ | main §4.7, §11.4.C | **done** | Auto-loads `docs_extras`, `component_tags` |
| 1.8 | `markdown-pipeline-pass2` | Pass 2: python-markdown + pymdownx → HTML | M | ✓ | main §4.7, §11.4.B | **done** | All pymdownx extensions configured; snippet base_path includes repo root |
| 1.9 | `markdown-pipeline-pass3` | Pass 3: wrap in DocPage layout | M | ✓ | main §4.7 | **done** | `_pass3_layout` calls `DocPage.render()` |
| 1.10 | `doc-page-component-mvp` | Minimal `DocPage` component (no nav/sidebar yet) | M | ✓ | main §4.1, 11.11 §2 | **done** | `doc_page.py` with full `<head>` block, design tokens, prose CSS; full chrome in Phase 3a |
| 1.11 | `slug-algorithm` | Material-compatible heading slug | S | ✓ | main §4.7, §9.1 | **done** | **Corrected during 3b.25:** the old site used python-markdown's DEFAULT toc slugify (mkdocs.yml set only `permalink`), NOT `pymdownx.slugs.slugify` - the latter keeps whitespace runs as double hyphens (`default-js--css-locations`) and broke every inbound anchor. Pipeline now uses the default slugify |
| 1.12 | `code-fence-info-string-parser` | Parse fence headers (`djc_py title="…" hl_lines="…"`) | S | | main §4.7 | **done** | Handled natively by `pymdownx.highlight`; verified `title=` renders as `<span class="filename">` |
| 1.13 | `include-file-tag` | `{% include_file "path" %}` template tag | S | | main §4.7, §11.4.F | **done** | In `docs_extras.py`; infers language from extension |
| 1.14 | `version-tag` | `{% version %}` template tag | S | | main §4.7 | **done** | `docs_extras.py`; verified expanding to `0.150.1` |
| 1.15 | `image-tag` | `{% image %}` template tag (optional sugar) | S | | main §4.7 | **done** | In `docs_extras.py`; supports `alt`, `width`, `css_class` attrs |
| 1.16 | `pygments-light-stylesheet` | Light-mode Pygments theme CSS | S | | 11.11 §6.3 | **done** | `static/css/pygments-light.css` (default theme, ~5KB) |
| 1.17 | `pygments-dark-stylesheet` | Dark-mode Pygments theme CSS | S | | 11.11 §6.3 | **done** | `static/css/pygments-dark.css` (monokai theme, ~5KB) |
| 1.18 | `uv-scripts-entrypoints` | Wire `docs-serve` / `docs-build` / `docs-test` | S | ✓ | main §4.8 | **done** | Django management commands (`docs_serve`, `build_docs`, ...), documented in `development.md`, run from `docs_site/`. (`docs_test` was later culled - its validation is in `docs_build_check`; the mgmt-command set was trimmed 9 → 6: `build_one`/`docs_test`/`docs_preview` removed, `docs_preview` folded into `docs_serve_built --versions`) |
| 1.19 | `docs-serve-command` | Dev-loop runserver wrapper | S | | main §4.8 | **done** | `docs_serve` wraps `runserver`; live `serve_page` view renders `content/*.md` on the fly via the same pipeline; URL<->path mapping shared with build in `build/paths.py` |
| 1.20 | `docs-build-command-mvp` | Build current version to `docs/v/<version>/` (no manifest yet) | M | ✓ | main §4.6, §4.8, 11.7 §3.1, §6 | **done** | `build_docs` command; renders all .md in a content dir to `output/`; versioning manifest in Phase 5b |
| 1.21 | `docs-test-command-mvp` | Post-build link validator (broken anchors fail) | M | ✓ | main §4.8, §9.8 | **done** (command later culled) | Was the `docs_test` command (walked HTML, checked internal links + anchors, `--strict`). The validation now lives in the guard harness (`internal_link`/`anchor` guards) run by `docs_build_check`; the standalone `docs_test` command was removed in the mgmt-command cull as redundant |
| 1.22 | `front-matter-schema` | Codified front-matter spec (title, description, og_image, …) + validator | S | ✓ | 11.12 §3.B.11 | **done** | `frontmatter.py`; YAML front-matter with 6 known fields; strict mode rejects unknowns |
| 1.23 | `docpage-head-block` | Unified `<head>` block (title, description, canonical, lang, viewport, favicon, theme-color, robots, alternate) | M | ✓ | 11.12 §4.C.1 | **done** | In DocPage component template; emits title, description, canonical, robots, generator |
| 1.24 | `page-titles` | `<title>` formatting: `<Page Title> - Django-Components` | S | ✓ | 11.12 §2.A.5 | **done** | Front-matter > H1 > site name fallback |
| 1.25 | `per-page-descriptions` | Front-matter > first-paragraph > site-level fallback | M | ✓ | 11.12 §2.A.6 | **done** | Fence-aware H1 extraction; paragraph extractor strips markdown formatting, caps at 155 chars |
| 1.26 | `canonical-urls` | Versioned pages canonical to `/latest/` counterpart | S | ✓ | 11.12 §2.A.1 | **partial** | **5c (6.12 part a) fixed the live-site anti-pattern:** the root/deployed build now canonicals to the root (latest) URL (`build_site(versioned_canonical=False)`), so the page users actually see no longer canonicals *away* to a versioned URL. og:url, breadcrumb JSON-LD, and indexing.json all realigned to root; the breadcrumb builder now strips the site base-path explicitly (no longer keys off the `/v/` marker). **Still pending (6.12 part b, Phase 6):** old `/v/<ver>/` snapshots still self-canonical (the proper canonical→latest + noindex-if-absent mapping needs the multi-version manifest) |
| 1.27 | `per-version-noindex` | `noindex,follow` on pages under non-current/non-previous `/v<x>/` | S | | 11.12 §4.C.3 | **done** | DocPage emits `noindex,follow` when front-matter `noindex: true`; version-based logic deferred to Phase 5b |
| 1.28 | `markdown-companion-urls` | Serve every page also at `…/page.md` (raw markdown) | S | ✓ | 11.12 §3.B.2 | **done** | `build_docs` emits `index.md` companion with title/url/description front-matter + expanded markdown. **Chunk 3 fix:** `pipeline.expand_snippets` now resolves pymdownx `--8<--` file includes in the companion (they're a Pass-2 feature, previously left literal), so the `.md` matches the rendered page (e.g. License/Code of Conduct show their text, not the directive) |
| 1.29 | `json-ld-breadcrumbs` | BreadcrumbList JSON-LD on every page | S | | 11.12 §2.A.7 | **done** | Generated from canonical URL path in DocPage; TechArticle deferred to Phase 5c |
| 1.30 | `placeholder-home-page` | Thin `/` placeholder (replaced in Phase 9) | S | | main §8 | **done** | `content/index.md` with title, description, GitHub link |
| 1.31 | `internal-md-link-rewriting` | Rewrite internal `[X](foo/bar.md)` links to clean URLs (`use_directory_urls`-style) so they resolve under the `page.md` -> `/page/` scheme | M | ✓ | main §4.7, §9.1a, 3b.25 | **done** | `build/links.py`; post-Pass-2 HTML rewrite. Resolves `.md` relative to source, maps to clean URL, computes relative href with `../` nesting; preserves anchors; leaves clean URLs + external links untouched. `.md` companion link rewriting (spike 11.12) deferred |

**Out of scope here:** API reference (Phase 4), examples (Phase 2), sidebar/header chrome (Phase 3a), search (Phase 5a), versioning manifest (Phase 5b), SEO/AIO polish (Phase 5c).

---

## Phase 2 — `{% example %}` end-to-end (the killer feature)

Goal: one example (suggested: `fragments`) renders interactively in a docs page, with code + page + live-render tabs, with pre-rendered fragments fetched correctly.

**Sharp focus:** prove the live-component + fragment-pre-render trick; resist building all examples.

| # | ID | Name | Effort | Critical | Source | Status | Notes |
|---|---|---|---|---|---|---|---|
| 2.1 | `example-autodiscovery` | Walk `docs_old/examples/` and register Page components | S | ✓ | main §2.4 | **done** | `apps/docs/examples.py`; walks EXAMPLES_DIR, imports component.py + page.py, finds *Page class; cached registry |
| 2.2 | `docs-example-convention` | `class DocsExample` metadata on Page components | S | | main §4.4a | **done** | Added to FragmentsPage: `fragments = {"alpine": {"type": "alpine"}, ...}` (name -> query params dict) |
| 2.3 | `fragment-pre-render` | Pre-render every fragment variant to `output/examples/…` | M | ✓ | main §4.4a | **done** | `build/examples.py`; uses `Component.as_view()` + RequestFactory; `get_component_url()` outputs rewritten to static paths via string replacement |
| 2.4 | `example-card-component` | `ExampleCard` Django component (tabbed code + render) | M | ✓ | main §4.2 | **done** | CSS radio-button tabs; Pygments-highlighted code; iframe srcdoc for live demo; `get_component_url()` string replacement for fragments |
| 2.5 | `example-tag` | `{% example "name" %}` template tag | S | ✓ | main §4.2, §11.4.E | **done** | `simple_tag` in docs_extras.py; calls ExampleCard.render(); lstrips output for markdown block-level parsing |
| 2.6 | `stable-example-ids-guardrail` | Detect renames of `examples/<name>/` in PR | S | | 11.12 §3.B.5 | **dropped** | Overly prescriptive - freezing example names via a guardrail isn't useful |
| 2.7 | `example-contract-check` | Validate every `{% example %}` has matching dir with `Page` + tests | M | | 11.10 §3.6 | **done** | `build/guards/example_contract.py` (migrated from `build/guards.py` into the unified harness in Phase 3b); validates component.py, page.py, *Page class, View, test file; runs as a harness guard |

**Out of scope here:** the other examples (those are content port, Phase 3b); all the chrome.

---

## Phase 3a — Theme + core chrome (the page feels like a real docs site)

Goal: a markdown page renders with header + sidebar + right-rail TOC + code blocks + dark mode, on desktop. Mobile and content port deferred.

**Sharp focus:** the visual system. Tokens, layout, typography, code blocks, admonitions.

| # | ID | Name | Effort | Critical | Source | Status | Notes |
|---|---|---|---|---|---|---|---|
| 3a.1 | `design-tokens-css` | OKLCH design-tokens CSS file | S | ✓ | 11.11 §10, §11.1 | **done** | `static/css/tokens.css`; OKLCH values with @font-face for self-hosted Inter |
| 3a.2 | `light-theme-tokens` | Light-mode token values | S | ✓ | 11.11 §10 | **done** | Teal accent (Option A per Juro) |
| 3a.3 | `dark-theme-tokens` | Dark-mode token values | S | ✓ | 11.11 §10 | **done** | `[data-theme="dark"]` + `@media (prefers-color-scheme: dark)` auto fallback |
| 3a.4 | `theme-fouc-prevention` | Inline `<script>` in head reads localStorage before paint | S | ✓ | 11.11 §9.1 | **done** | Reads `djc-theme` from localStorage, sets `data-theme` attr |
| 3a.5 | `inter-font-link` | Inter font (CDN or self-hosted) | S | | 11.11 §10.6 | **done** | Self-hosted: `static/fonts/InterVariable.woff2` (variable font, 344KB, all weights) |
| 3a.6 | `prose-typography` | Body, headings, links, anchored-heading hover | S | ✓ | 11.11 §5.1-5.3 | **done** | `static/css/site.css`; `.prose` class with heading borders, anchor hover |
| 3a.7 | `inline-code-styling` | Inline `<code>` styled as accent pills | S | | 11.11 §5.4 | **done** | Accent-colored pill via `var(--c-accent)` + `var(--c-accent-dim)` |
| 3a.8 | `code-block-component` | `<pre><code>` with language label + copy button | M | ✓ | 11.11 §6.2-6.3 | **done** | JS-driven: detects language from code class, injects label + copy button on hover; checkmark feedback on copy |
| 3a.9 | `tabbed-code-component` | `CodeTabs` (multi-tab fences + example widget tabs + filename) | M | | 11.11 §6.4 | pending | Deferred: pymdownx.tabbed already provides tab switching; unified CodeTabs component built when needed in Phase 3b/4 |
| 3a.10 | `blockquote-styling` | Left-border, muted fg | S | | 11.11 §5.5 | **done** | CSS-only in `site.css` |
| 3a.11 | `table-styling` | Cell borders, header bg, mono first-col auto-detect | S | | 11.11 §5.6 | **done** | CSS-only in `site.css`; overflow-x wrapper |
| 3a.12 | `admonition-component` | Note/info/warning with accent border + tinted bg | S | ✓ | 11.11 §5.7 | **done** | CSS-only in `site.css`; note/info/warning/danger variants via pymdownx classes |
| 3a.13 | `list-styling` | Standard CommonMark lists | S | | 11.11 §5.8 | **done** | CSS-only in `site.css`; includes task-list and definition-list styling |
| 3a.14 | `header-component` | 64px sticky header (logo, top-nav, search trigger, version, theme, GitHub) | M | ✓ | 11.11 §4 | **done** | Sticky header with backdrop-blur; Docs/Examples nav; theme toggle, version badge, GitHub link |
| 3a.15 | `sidebar-component` | 280px sticky left sidebar (nested 2-level nav, collapsible groups, active highlight, scroll-into-view) | M | ✓ | 11.11 §3 | **done** | 280px sticky sidebar from _nav.yml; collapsible groups with localStorage persistence; active highlight + scroll-into-view |
| 3a.16 | `right-toc-component` | 240px sticky right rail (H2/H3 scroll-spy) | M | ✓ | 11.11 §7.1, §2.2 | **done** | 240px sticky; H2/H3 from toc_tokens; IntersectionObserver scroll-spy; hidden <1024px |
| 3a.17 | `doc-page-layout` | 3-column shell (sidebar / content / TOC), 1280px max-width | M | ✓ | 11.11 §2 | **done** | Replaces Phase 1 stub; 3-column flexbox; responsive breakpoints at 768px and 1024px |
| 3a.18 | `theme-toggle-button` | 3-mode cycle (auto / light / dark) wired to localStorage | M | ✓ | 11.11 §4.1, §9 | **done** | Sun/moon SVG icons; auto->light->dark->auto cycle; wired in site.js |
| 3a.19 | `nav-yaml-loader` | Loads + validates single `_nav.yml` | S | ✓ | 11.9 §2.2 | **done** | `build/nav.py` ~130 LOC; NavTree/NavSection/NavGroup/NavItem types; flat_pages, breadcrumbs, prev/next, active state |
| 3a.20 | `breadcrumbs-component` | Above-H1 breadcrumb trail | S | | 11.11 §7.2 | **done** | Generated from nav tree; rendered above H1 in content area |
| 3a.21 | `page-nav-component` | Prev/Next cards at bottom | S | | 11.11 §7.3 | **done** | Card-style prev/next with hover border glow; derived from nav order |
| 3a.22 | `site-css` | Bundled prose + components + utilities stylesheet | M | ✓ | 11.11 §5, §6, §11.1 | **done** | `site.css`: prose typography + layout chrome (header, sidebar, TOC, breadcrumbs, page-nav, footer) |
| 3a.23 | `site-js` | Bundled interactivity (search trigger, theme, sidebar persistence, scroll-spy, copy, drawer) | M | ✓ | 11.11 §3.3, §4.1, §7.1, §6.2, §8, §9.1 | **done** | `site.js`: theme toggle, sidebar collapse/persist, TOC scroll-spy, code block lang label + copy button. Search trigger wired in Phase 5a; mobile drawer in Phase 3b |

**Out of scope here:** mobile breakpoints (Phase 3b), Pagefind UI (Phase 5a), content port (Phase 3b).

---

## Phase 3b — Mass content port + responsive + content-layer guardrails

Goal: every existing markdown page renders correctly under the new pipeline + chrome, on desktop + mobile. All content-layer guardrails wired into CI.

**Sharp focus:** content fidelity. Resist building anything API-reference- or search-related.

| # | ID | Name | Effort | Critical | Source | Status | Notes |
|---|---|---|---|---|---|---|---|
| 3b.1 | `mobile-drawer` | Full-height left drawer; hamburger toggle | M | ✓ | 11.11 §4.1, §2.2 | **done** | The sidebar element becomes the off-canvas drawer (<768px); hamburger in header, overlay/Esc close, body scroll-lock, drawer-only top-nav links block |
| 3b.2 | `mobile-header-actions` | Overflow menu for version + theme + GitHub | S | | 11.11 §4.1 | **done** | `.djc-overflow` kebab menu; theme picker reuses the same `data-theme-value` hooks (text buttons), outside-click + Esc close |
| 3b.3 | `mobile-toc-details` | `<details>` "On this page" disclosure under H1 | S | | 11.11 §2.2, §7.1 | **done** | `.djc-toc-mobile` above the article, same toc_items as the right rail; shown <1024px |
| 3b.4 | `responsive-breakpoints` | 4 breakpoints wired flexbox-side | M | ✓ | 11.11 §2.2 | **done** | `--page-gutter` var (24/32/48px) on header + layout; tier rules per spike §2.2 (TOC <1024 -> details, sidebar <768 -> drawer) |
| 3b.5 | `release-notes-parser` | Parse CHANGELOG.md → per-release pages + index | S | | 11.9 §2.1 | **done** | `build/release_notes.py`; pages generated into a temp staging dir at build time and rendered through the normal loop; dev server serves /releases/ from an mtime-cached staging dir; index uses clean URLs. Also added a generated /examples/ index page so the chrome's Examples link resolves (closed a pre-existing internal_link error class); nav entry for /releases/ comes with the 3b.25 content port |
| 3b.6 | `people-page-template` | Native Django template (replace mkdocs-macros) | S | | 11.9 §2.7 | **done** | **Deviation from spike:** markdown page + `{% people %}` tag + `UserGrid` component instead of a TemplateView - Pass 1 already runs Django tags in markdown, so a special-cased template page would be more indirection, not less. `people.yml` moved to `content/community/`; updater script repointed |
| 3b.7 | `ai-bot-policy-doc` | New `content/community/ai_bot_policy.md` | S | | 11.12 §3.B.10 | **done** | Default-allow policy text per spike; in nav under Community |
| 3b.8 | `template-render-guard` | Catch Django template errors in Pass 1 | S | ✓ | 11.10 §3.1 | **done** | `builder.build_site` captures per-page render failures as `template_render` ERRORs instead of aborting; folded into the report by `docs_build_check` |
| 3b.9 | `fence-validator` | Detect unclosed fences, malformed snippets, unknown languages | M | ✓ | 11.10 §3.2 | **done** | `guards/fence_validator.py` - `scan_fences()` is the shared primitive (unclosed=ERROR); unknown langs split into 3b.10, missing snippet paths into 3b.11 |
| 3b.10 | `lexer-alias-check` | Validate fence info-strings resolve to Pygments lexer | S | | 11.10 §3.3 | **done** | `guards/lexer_alias.py`; `ALLOWED_NON_LEXER_LANGS` allowlist (text/console/mermaid...) |
| 3b.11 | `snippet-path-check` | Validate `--8<--` targets exist within `base_path` | S | ✓ | 11.10 §3.7 | **done** | `guards/snippet_path.py` - static pre-scan (single + block `--8<--` forms), resolves vs source dir then repo root |
| 3b.12 | `internal-link-check` | Walk built HTML, assert every internal `<a href>` resolves | M | ✓ | 11.10 §3.9 | **done** | `guards/internal_link.py` via `SiteIndex.resolve_link` (clean-URL aware); skips asset-looking hrefs |
| 3b.13 | `anchor-check` | Every `#anchor` href maps to an `id=` | S | ✓ | 11.10 §3.10 | **done** | `guards/anchor.py`; WARNING (matches mkdocs `validation.anchors: warn`, fails under `--strict`) |
| 3b.14 | `image-asset-check` | `<img src>`, `<script src>`, `<link href>` to local assets exist | S | | 11.10 §3.12 | **done** | `guards/asset.py`; `/static/` resolved via Django staticfiles **finders** (sees package static like djc JS); doc-pages only |
| 3b.15 | `nav-yaml-validity-check` | Content ↔ `_nav.yml` 2-way drift | M | | 11.10 §3.14 | **done** | `guards/nav.py`; missing target=ERROR, orphan page=WARNING; `OMIT_FROM_NAV` for index/404 |
| 3b.16 | `html-wellformedness-check` | lxml.html parse + duplicate-id detection | S | | 11.10 §3.15 | **done** | `guards/html_wellformed.py`. **Deviation:** dropped `recover=False` - libxml2 strict mode treats `<a id=X name=X>` (pymdownx line anchors) as a duplicate ID, a false positive on nearly every page. Real dup IDs caught precisely by an `id=`-only Counter in `SiteIndex` |
| 3b.17 | `snapshot-regression-test` | pytest + syrupy on curated set | M | | 11.10 §3.17 | **done (scaffold)** | `tests/test_render_snapshot.py`, 3 fixtures, snapshots **content** HTML (`wrap_in_layout=False`) so chrome/version don't churn. Standalone pytest - NOT wired into `docs_build_check` until renderer settles (Phase 5), per spike |
| 3b.18 | `site-index` | Shared post-build HTML walker (~120 LOC) | M | ✓ | 11.10 §6 | **done** | `build/site_index.py` - parses each page once; exposes links/anchors/assets/images/headings/redirect/dup-ids |
| 3b.19 | `guardrail-runner-harness` | Orchestrator (~100 LOC) — severity rules, dep order | M | ✓ | 11.10 §6 | **done** | `build/guards/__init__.py` (`run_guards`, `format_report`); a crashing guard is itself an ERROR. Driven by `docs_build_check` (the build-to-temp CI gate) |
| 3b.20 | `single-h1-guardrail` | Exactly one `<h1>` per page | S | | 11.12 §2.A.8 | **done** | `guards/single_h1.py`; WARNING; doc-pages only (skips example demos / redirect stubs) |
| 3b.21 | `image-alt-text-guardrail` | Every `<img>` has non-empty `alt` | S | | 11.12 §2.A.9 | **done** | `guards/alt_text.py`; WARNING; doc-pages only |
| 3b.22 | `structured-headings-guardrail` | No `##` → `####` jumps | S | | 11.12 §3.B.3 | **done** | `guards/headings.py`; WARNING; flags level jumps > +1; generated `releases/*` pages exempt (frozen CHANGELOG history) |
| 3b.23 | `code-block-language-tags-guardrail` | Missing language tag = warning (with allowlist) | S | | 11.12 §3.B.4 | **done** | `guards/code_lang.py`; source-scan over `scan_fences`; empty info-string=WARNING (suggest ```text) |
| 3b.24 | `git-metadata-fetcher` | DIY subprocess `git log` for last-updated + authors | S | | 11.9 §2.3 | **done** | `build/git_metadata.py` - one cached `git log --follow` call per page (date + authors combined); exclusions per old mkdocs config + `releases/*`; rendered in the DocPage footer. CI workflow needs `fetch-depth: 0` (lands with 5b.16) |
| 3b.25 | `content-port-sweep` | Move every existing page `docs_old/` → `docs_site/content/` (move + delete source); fix `--8<--` paths, links | L | ✓ | main §5 Phase 3 | **done** | 50 pages + 10 images ported. **Landed the §11.11 §4.2 URL taxonomy directly** (per Juro): content lives at `content/docs/<section>/`, `/plugins/` at root; old `welcome.md` became the `/docs/` hub (README.md include wrapper deleted). The 14 API-reference pages are interim stubs (anchor sections for inbound `#component` etc. links) until Phase 4. Port surfaced + fixed: slug algorithm was wrong (see 1.11), snippet base-path self-inclusion on macOS (now repo-root-only, matching old mkdocs), asset guard resolved relative srcs against build root instead of page dir. Pages without H1 get one injected from the nav title (Material parity); heading-level jumps and untagged fences fixed in content. Known interim gap: ~640 `[X][Key]` autorefs render literally until Phase 4 cross-ref resolution. `docs_old/` now holds only examples/, devguides/, benchmarks/, reference+templates (Phase 4), scripts/css/overrides (Phase 6) |

**Out of scope here:** API reference (Phase 4), Pagefind (Phase 5a), versioning (Phase 5b), SEO polish (Phase 5c).

---

## Phase 4 — API reference (the big one)

Goal: feature parity with mkdocstrings on the 14 current reference pages, with the discovery → rendering split, dual anchors, full cross-ref resolution.

**Sharp focus:** mkdocstrings replacement. Resist anything that isn't on the reference path.

| # | ID | Name | Effort | Critical | Source | Status | Notes |
|---|---|---|---|---|---|---|---|
| **Discovery layer (Layer 1)** | | | | | | | |
| 4.1 | `discover-kinds-adt` | `ReferencePage` / `ReferenceEntry` types | S | ✓ | 11.5 §5.1, §10 | **done** | Located at `docs_site/apps/docs/discovery/kinds.py` |
| 4.2 | `discover-layer` | Discovery orchestrator (Layer 1) | L | ✓ | 11.5 §5.1, §5.3 | **done** | Foundation |
| 4.3 | `discover-walk` | Walk script: load griffe with `force_inspection=True` | M | ✓ | 11.5 §5.1, §10 | **done** | via static analysis; force_inspection deferred to the template-tags page (`BaseNode._signature`) |
| 4.4 | `discover-page-api` | API page (kinds 1-5: components, fns, decorators, instances, NamedTuples) | M | ✓ | 11.5 §3.1, §10 | **done** | |
| 4.5 | `discover-page-exceptions` | Exceptions page (kind 6) | S | ✓ | 11.5 §3.1, §9 | **done** | **Proof-of-concept page**; do this first |
| 4.6 | `discover-page-components` | Components page (kind 7: predefined Component subclasses) | M | | 11.5 §3.1, §10 | **done** | predefined Component subclasses from django_components.components |
| 4.7 | `discover-page-settings` | Settings page (kind 8: ComponentsSettings fields) | M | | 11.5 §3.1, §10 | **done** | ComponentsSettings fields |
| 4.8 | `discover-page-tag-formatters` | Tag formatters (kinds 9-10) | M | | 11.5 §3.1 | **done** | TagFormatterABC subclasses (classes) + instances (marker predicates) |
| 4.9 | `discover-page-commands` | Management commands (kind 11) | L | ✓ | 11.5 §3.1 | **done** | argparse introspection via setup_parser_from_command; legacy startcomponent/upgradecomponent excluded (TODO_v1) |
| 4.10 | `discover-page-template-tags` | Template tags (kind 12) | M | ✓ | 11.5 §3.1 | **done** | BaseNode subclasses from templatetags/*; runtime `_signature` (no force_inspection needed) |
| 4.11 | `discover-page-urls` | URL patterns (kind 13) | S | | 11.5 §3.1 | done | |
| 4.12 | `discover-page-template-vars` | Template vars (kind 14: ComponentVars) | S | | 11.5 §3.1 | **done** | ComponentVars fields |
| 4.13 | `discover-page-testing` | Testing API (kind 15) | S | | 11.5 §3.1 | done | |
| 4.14 | `discover-page-extension-hooks` | Extension hooks + contexts (kinds 16-17) | M | ✓ | 11.5 §3.1 | **done** | ComponentExtension on_* methods + marker-detected context classes |
| 4.15 | `discover-page-extension-commands` | Extension command API (kind 18) | M | | 11.5 §3.1 | done | |
| 4.16 | `discover-page-extension-urls` | Extension URL API (kind 19) | M | | 11.5 §3.1 | done | |
| 4.17 | `discover-page-signals` | Signals placeholder (kind 20) | S | | 11.5 §3.1, §9 | done | Markdown island for now |
| **Griffe extensions** | | | | | | | |
| 4.18 | `griffe-ext-runtime-bases` | `RuntimeBasesExtension` ported | S | ✓ | 11.5 §8 | **done** | One-line config swap |
| 4.19 | `griffe-ext-source-code` | `SourceCodeExtension` ported | S | ✓ | 11.5 §8 | **done** | Portable verbatim |
| **Cross-ref + inventory** | | | | | | | |
| 4.20 | `inventory-builder` | Parse stdlib + Django `objects.inv` → name→URL map | M | ✓ | 11.5 §2, §6 | **done** | ~100 LOC |
| 4.21 | `signature-crossrefs` | Walk griffe `Expr` trees → resolve `ExprName` → emit links | L | ✓ | 11.5 §2, §6 | **done** | 712+ links on api.md alone |
| 4.22 | `inventory-output` | Emit `site/objects.inv` for external linkbacks | M | ✓ | 11.5 §6 | **done** | 7034 bytes |
| **Entry renderers (per-kind components)** | | | | | | | |
| 4.23 | `render-ref-class` | `ReferenceClass` (kinds 1-6, 15, 18-19) | L | ✓ | 11.5 §3.2 #1 | **done** | Workhorse |
| 4.24 | `render-component-class` | `ReferenceComponentClass` (kind 7) | M | | 11.5 §3.2 #2 | **done** | ReferenceComponentClass: heading + docstring + own members (no class signature; griffe .members is own-only) |
| 4.25 | `render-setting` | `ReferenceSetting` (kinds 8, 14) | M | | 11.5 §3.2 #3 | **done** | ReferenceSetting: name + type + docstring, no badge (shared by settings + template vars) |
| 4.26 | `render-tag-formatter` | `ReferenceTagFormatter` (kind 9) | S | | 11.5 §3.2 #4 | **done** | ReferenceTagFormatter: naked class card (heading + docstring; no signature/members/badge) |
| 4.27 | `render-management-command` | `ReferenceManagementCommand` (kind 11) | L | ✓ | 11.5 §3.2 #5 | **done** | ReferenceManagementCommand: usage + arg sections + subcommand links + source |
| 4.28 | `render-template-tag` | `ReferenceTemplateTag` (kind 12) | M | ✓ | 11.5 §3.2 #6 | **done** | ReferenceTemplateTag: `{% tag %}` block from _signature/tag/end_tag/allowed_flags + docstring + source |
| 4.29 | `render-url-pattern` | `ReferenceURLPattern` (kind 13) | S | | 11.5 §3.2 #7 | done | Trivial bullets |
| 4.30 | `render-extension-hook` | `ReferenceExtensionHook` (kind 16) | M | ✓ | 11.5 §3.2 #8 | **done** | ReferenceExtensionHook: signature + docstring + Available-data table from ctx |
| 4.31 | `render-hook-context` | `ReferenceHookContext` (kind 17) | M | ✓ | 11.5 §3.2 #9 | **done** | ReferenceHookContext: docstring + fields table (griffe per-field docstrings) |
| 4.32 | `render-signal` | `ReferenceSignal` placeholder (kind 20) | S | | 11.5 §3.2 #10 | done | No-op |
| 4.33 | `render-instances-list` | `AvailableInstancesList` (kind 10) | S | | 11.5 §3.2 #11 | **done** | AvailableInstancesList = instance->class same-page links in the preface |
| 4.34 | `render-settings-defaults-panel` | `SettingsDefaultsPanel` companion | M | | 11.5 §3.2 #12 | **done** | defaults panel = cleaned `--snippet:defaults--` code block in the page preface |
| **Shared sub-components** | | | | | | | |
| 4.35 | `sub-signature-block` | `SignatureBlock` (lang-aware fenced sig) | S | ✓ | 11.5 §4 | **done** | Reused by ~8 entry templates |
| 4.36 | `sub-source-code-link` | `SourceCodeLink` (repo file#L42 link) | S | ✓ | 11.5 §4 | **done** | source link via `SourceCodeExtension` (`format_source_code_html`) |
| 4.37 | `sub-parameters-table` | `ParametersTable` (name/type/desc rows) | M | ✓ | 11.5 §4 | **done** | |
| 4.38 | `sub-docstring-body` | `DocstringBody` (Google sections + md_in_html) | M | ✓ | 11.5 §4 | **done** | |
| 4.39 | `sub-admonitions-block` | `AdmonitionsBlock` (`!!! note` in docstrings) | S | | 11.5 §4 | **done** | |
| 4.40 | `sub-examples-block` | `ExamplesBlock` (fenced code from `Examples:`) | S | | 11.5 §4 | **done** | |
| 4.41 | `sub-cross-ref` | `CrossRef` (bracket refs `[X][]` → URL) | M | ✓ | 11.5 §2, §4, §6 | **done** | Merges project + inventories |
| 4.42 | `sub-symbol-type-badge` | `SymbolTypeBadge` (`<span class="doc doc-symbol-X">`) | S | | 11.5 §4, §6 | **done** | |
| **Page layouts** | | | | | | | |
| 4.43 | `page-layout-api` | API page layout | M | ✓ | 11.5 §5.2 | **done** | page = generated md + `{% docstring %}` per entry (repeater layout; no dedicated component) |
| 4.44 | `page-layout-exceptions` | Exceptions page layout (POC) | S | ✓ | 11.5 §5.2 | **done** | same generated-md repeater approach as api |
| 4.45 | `page-layout-components` | Components page layout | S | | 11.5 §5.2 | **done** | components layout = per-class cards (ReferenceComponentClass) |
| 4.46 | `page-layout-settings` | Settings page layout (entries + defaults panel) | M | | 11.5 §5.2 | **done** | settings layout = defaults panel (preface) + per-field entries |
| 4.47 | `page-layout-tag-formatters` | Tag formatters (classes + instances) | M | | 11.5 §5.2 | **done** | instances list (preface) + class-card entries; §7.6 blank-line bug avoided |
| 4.48 | `page-layout-commands` | Commands (command_tree layout) | M | ✓ | 11.5 §5.2 | **done** | command_tree = generated md + `{% docstring %}` per command (depth-first walk) |
| 4.49 | `page-layout-template-tags` | Template tags layout | M | ✓ | 11.5 §5.2 | **done** | single anchor (the tag name); shared runtime.py helper (with commands) |
| 4.50 | `page-layout-urls` | URL patterns layout | S | | 11.5 §5.2 | done | |
| 4.51 | `page-layout-template-vars` | Template variables layout | S | | 11.5 §5.2 | **done** | template-vars layout = per-field entries (ReferenceSetting) |
| 4.52 | `page-layout-testing` | Testing API layout | S | | 11.5 §5.2 | done | |
| 4.53 | `page-layout-extension-hooks` | Extension hooks + contexts (hooks_plus_objects) | M | ✓ | 11.5 §5.2 | **done** | hooks_plus_objects: `## Hooks` / `## Objects` sections in the generated page |
| 4.54 | `page-layout-extension-commands` | Extension commands layout | S | | 11.5 §5.2 | done | |
| 4.55 | `page-layout-extension-urls` | Extension URLs layout | S | | 11.5 §5.2 | done | |
| 4.56 | `page-layout-signals` | Signals placeholder layout | S | | 11.5 §5.2 | done | |
| **Tag + glue** | | | | | | | |
| 4.57 | `docstring-tag` | `{% docstring "x.y.z" %}` template tag | S | ✓ | main §4.3, §11.4.E | **done** | |
| 4.58 | `anchor-scheme-legacy-compat` | Dual anchors: new `#Component` + legacy `#django_components.Component` | S | ✓ | 11.5 §7.1-7.2 | **done** | Preserves 397+578 inbound links |
| 4.59 | `routing-decorator-detection` | `@mark_extension_hook_api` decorator detection | S | ✓ | 11.5 §7.3 | **done** | via the runtime `_extension_hook_api` marker (set by @mark_extension_hook_api) |
| 4.60 | `property-docstring-griffe` | Retire `_extract_property_docstrings` for griffe access | M | ✓ | 11.5 §7.4 | **done** | griffe per-field docstring access throughout; old `_extract_property_docstrings` not ported |
| 4.61 | `snapshot-tests-discovery` | Snapshot tests for `ReferencePage[]` | M | | 11.5 §5.3 | **done** | |
| 4.62 | `api-symbol-forward-check` | `{% docstring %}` references must resolve | M | ✓ | 11.10 §3.4 | **done** | Pass-1 check |
| 4.63 | `api-symbol-reverse-check` | Public API symbols never referenced = warning | M | | 11.10 §3.5 | **done** | Upgrades to error in `--strict` |
| 4.64 | `anchor-alias-coverage` | Renamed symbols have legacy aliases | S | | 11.10 §3.11 | **done** | Warning severity |
| **Proof-of-concept escalation** | | | | | | | |
| 4.65 | `proof-exceptions-page` | Build exceptions.md end-to-end first | M | ✓ | 11.5 §9 | **done** | Validates contract; ~1 day |
| 4.66 | `proof-component-page` | Build Component class entry second | L | ✓ | 11.5 §9 | **done** | Exercises shared sub-components |
| **Post-Phase-4 enhancements** | | | | | | | |
| 4.67 | `toc-member-nav` | Collapsible per-member TOC on reference pages (Option C) | M | | - | **done** | Class members lifted into the right rail with class/attr/meth badges; scroll-spy auto-expands the active class, a caret pins one open. The page H1 is unwrapped from the rail (every page). Touches `toc.py` + `doc_page` + `site.css`/`site.js`; builds on 3a.16 and the Chunk-A TOC merge |

**Out of scope here:** anything not on the API-reference path.

### Chunk execution plan

Phase 4 is executed in **vertical chunks, not horizontally by layer**: build the
discovery -> rendering contract once, prove it end-to-end on the smallest page
(exceptions), escalate to the hardest class (Component/api) to exercise every
shared sub-component, then generalise to the remaining pages (mostly execution on
the proven toolkit), and finish with the reference-specific guards. This follows
spike 11.5 §9.

Every per-page chunk shares the same shape: a discovery generator
(`discovery/pages/<x>.py`) + any new per-kind renderer
(`components/reference/entries/`) + wire into
`discovery/registry.py::discover_pages()` + delete the
`content/docs/reference/<x>.md` stub + add the URL to the nav guard's
`GENERATED_NAV_URLS`.

| Chunk | Scope | Features | Status |
|---|---|---|---|
| **0 — Foundation** | griffe dep, `kinds` ADT, walker, 2 griffe extensions, discovery orchestrator | P4.0, 4.1-4.3, 4.18-4.19 | **done** |
| **A — Exceptions proof** | exceptions discovery, `ReferenceClass` v1, `{% docstring %}` tag, dual anchors, DocstringBody/SymbolTypeBadge, generated-page build hook + TOC merge + CSS | 4.5, 4.23, 4.35-4.36, 4.38-4.39, 4.42, 4.44, 4.57-4.58, 4.65 | **done** |
| **B — Component/api proof** | api discovery, inventory (parse + emit `objects.inv`), signature cross-refs, ParametersTable, ExamplesBlock, CrossRef, members + group_by_category, `ReferenceClass` v2 | 4.4, 4.20-4.22, 4.37, 4.40-4.41, 4.43, 4.60, 4.66 | **done** |
| **C — Commands** | argparse introspection; `ReferenceManagementCommand` (most bespoke layout). Do next per §9. | 4.9, 4.27, 4.48 | **done** |
| **D — Extension hooks** | `ReferenceExtensionHook` (Available-data table) + `ReferenceHookContext` (15 contexts); `@mark_extension_hook_api` decorator detection | 4.14, 4.30-4.31, 4.53, 4.59 | **done** |
| **E — Template tags** | `ReferenceTemplateTag`. `BaseNode._signature` is metaclass-set; resolved via **runtime introspection** of the live class (no force_inspection needed - the walker stays static). | 4.10, 4.28, 4.49 | **done** |
| **F — Settings + Template vars** | `ReferenceSetting` + `SettingsDefaultsPanel` | 4.7, 4.12, 4.25, 4.34, 4.46, 4.51 | **done** |
| **G — Tag formatters** | `ReferenceTagFormatter` + `AvailableInstancesList` | 4.8, 4.26, 4.33, 4.47 | **done** |
| **H — Components page** | `ReferenceComponentClass` (hides `Component` base) | 4.6, 4.24, 4.45 | **done** |
| **I — Fold-in / trivial pages** | testing / ext-commands / ext-urls reuse `ReferenceClass`; `ReferenceURLPattern` (trivial), `ReferenceSignal` (markdown island) | 4.13/4.52, 4.15/4.54, 4.16/4.55, 4.11/4.29/4.50, 4.17/4.32/4.56 | done |
| **J — Hardening** | discovery snapshot tests; api-symbol forward/reverse checks + anchor-alias coverage (the reference-content link validation) | 4.61-4.64 | **done** |

**Non-feature fixes that landed alongside the proofs** (not catalogue rows, but
load-bearing): per-symbol render resilience (one unintrospectable symbol degrades
to a minimal entry instead of failing the page); the static-analysis loader
decision (resolves the full submodule tree - `force_inspection` silently missed
the extension submodules); a stale-docstring-link codemod in `src/` (21 bare
`[x](#tag)` and stale-anchor links -> bracket cross-refs / corrected anchors);
and context-aware docstring heading demotion. The last two let the `anchor` and
`headings` guards run on reference pages with **no exemption** (only the
pre-existing `releases/*` headings exemption remains).

---

## Phase 5a — Search

Goal: Pagefind-powered search with custom UI feels at least as good as Material's search.

**Sharp focus:** search only. Resist versioning, SEO, social cards in this sub-phase.

| # | ID | Name | Effort | Critical | Source | Status | Notes |
|---|---|---|---|---|---|---|---|
| 5a.1 | `pagefind-integration` | Run `pagefind` CLI post-build; chunked indexes; per-page weights | S | ✓ | main §4.5, §11.1 | **done** | `pagefind[bin]` dep; `build/pagefind.py::run_pagefind` shells `python -m pagefind --site <out>` after `build_site` in `build_docs` (skippable via `--no-search`; NOT run in `docs_build_check`). Scoping is whitelist-based: `data-pagefind-body` on `<article>` (excludes all chrome, no per-element `data-pagefind-ignore` needed); `boost:` front-matter -> `data-pagefind-weight` (omitted when 1.0). Anchor sub-results come free from headings. Tests in `test_pagefind.py` |
| 5a.2 | `search-overlay-component` | Centered modal: input + results + keyboard nav (↑↓ Enter Esc) | M | ✓ | 11.11 §8 | **done** | `SearchModal` component (markup-only; behavior in `static/js/search.js`). Lazy `import()` of Pagefind on first open; debounced search; anchor-level results from `sub_results` with `<mark>` excerpts; ↑↓/Enter/Esc nav within the modal. Verified end-to-end in headless Chromium (query "component" -> 36 rows, 159 marks). Esc/backdrop close |
| 5a.3 | `search-bar-component` | Header trigger that opens overlay | M | ✓ | main §4.5, §11.1.G.5 | **done** | `.djc-search-trigger` button inline in DocPage header (`data-search-open`), `Search… ⌘K`; shrinks to icon-only <768px. (Static ⌘K hint; per-platform label + global shortcut to open are Chunk 3 / 5a.5) |
| 5a.4 | `search-states` | Empty / no-results / error states | S | | 11.11 §8.3 | **done** | Empty = 5 popular-page quick links (validated by `internal_link` guard); no-results message; error state falls back to a Google `site:` link (also the dev-server path, where no index exists) |
| 5a.5 | `search-v1-features` | `/` `Ctrl+K` `Esc` shortcuts; `?q=` deep link; `?h=` in-page highlight; mobile a11y; delayed spinner | M | ✓ | 11.1.G.2 | **done** | Global `/` + `Ctrl/Cmd+K` open (per-platform ⌘/Ctrl label), Esc close. `?q=` mirrors the live query into the URL (cleared on close) and opens pre-filled on load. `?h=` highlights matched terms in the destination article (result links carry it); runs on every page via search.js. Focus trapped in the open dialog + restored to the opener; `aria-expanded`/`aria-controls`/`role=dialog`. Delayed (400ms) spinner. Committed Playwright E2E (`test_search_e2e.py`, marked `e2e`, self-skips without a browser) drives all of this against a real index |
| 5a.6 | `custom-404-page` | 404 with search bar + common destinations | M | | 11.12 §2.A.12 | **done** | `NotFoundPage` component (message + "Search the documentation" button wired to the shared modal + 4 popular destinations + issue link, all absolute URLs). `builder.generate_not_found` wraps it in DocPage chrome and writes `404.html` at the site root (served by GitHub Pages on any 404). Marked noindex + `searchable=False` (new DocPage kwarg -> omits `data-pagefind-body`, so it's not in the Pagefind index). Validated by all guards in `docs_build_check`; covered by `test_not_found.py` + an E2E case |

**Out of scope here:** versioning, SEO, social cards.

---

## Phase 5b — Versioning

Goal: `docs-build` + `docs-build-all` + `version_picker` + `versions.json` flow works end-to-end, with `docs_site/versions/<version>/` committed to `master` (the target moved from `docs/v/` to `docs_site/versions/` per main §4.0a; the spike still says `docs/v/`).

**Sharp focus:** versioning only.

| # | ID | Name | Effort | Critical | Source | Status | Notes |
|---|---|---|---|---|---|---|---|
| 5b.1 | `verspec-dep` | Add `verspec` dependency | S | ✓ | 11.7 §2.1, §12 | **done** | Direct dep in the `docs` group (was transitive via mike/mkdocs); comment marks it as surviving the Phase-6 mkdocs/mike removal |
| 5b.2 | `mike-versions-vendor` | Vendor mike's `Versions` + `VersionInfo` classes | S | ✓ | 11.7 §2.1, §9 | **done** | `_vendor/mike_versions.py` + `LICENSE-mike.txt` (BSD-3, © Jim Porter). Dropped the unused jsonpath `props` methods; `_vendor` excluded from ruff/mypy so it stays verbatim |
| 5b.3 | `mike-redirect-vendor` | Vendor mike's `redirect.html` template | S | ✓ | 11.7 §2.3, §4.4 | **done** | `_vendor/mike_redirect.html`; rendered via `versioning.render_redirect` |
| 5b.4 | `versions-json-schema` | `versions.json` manifest (mike-compatible) | S | ✓ | 11.7 §4 | **done** | Byte-compatible with mike (list of {version,title,aliases}); read/written by `build/versioning.py` |
| 5b.5 | `build-info-stamp` | Per-version `_build_info.json` (version, source_sha, builder_version) | S | ✓ | 11.7 §3.3 | **done** | `versioning.write_build_info`; `DOCS_BUILDER_VERSION=1.0.0`; powers the docs-build-all idempotency check |
| 5b.6 | `version-sorter` | Use verspec.LooseVersion; sentinel handling | S | | 11.7 §2.1, §8.1 | **done** | Via the vendored `Versions.__iter__` (dev/non-digit sentinels sort above releases) + `bootstrap._lv` for tag bounds |
| 5b.7 | `docs-build-cmd` | Full `docs-build [--version] [--alias]` (replaces MVP from Phase 1) | M | ✓ | 11.7 §3.1, §6 | **done** | Extended `build_docs`: preview mode (→site/) vs version mode (→`docs_site/versions/<v>/` + manifest + stamp + aliases). Added `--alias`, `--no-manifest-update`, `--title` |
| 5b.8 | `docs-build-all-cmd` | Bootstrap walker (`docs-build-all`) | M | ✓ | 11.7 §3.2, §3.3, §8.1 | **done** | `docs_build_all` command + testable `build/bootstrap.py` core (config, tag select, idempotency, orchestration). `--dry-run`. Skips tags whose checkout predates the builder (historical migration deferred, spike §7) |
| 5b.9 | `worktree-orchestration` | Worktree add/remove lifecycle in docs-build-all | S | ✓ | 11.7 §3.2, §8.1 | **done** | `git worktree prune` at start; add `--detach`; remove `--force` in a `finally` + rmtree. Verified clean (no dangling) against a real tag |
| 5b.10 | `alias-redirect-materializer` | Materialize `latest/` etc. as redirect HTML | S | ✓ | 11.7 §2.4, §3.1 | **done** | `versioning.materialize_alias`; per-page redirect stubs, relative href correct at every nesting depth; clears stale stubs when an alias moves |
| 5b.11 | `version-picker-component` | Header dropdown reads versions.json | M | ✓ | main §4.6, 11.7 §5, 11.11 §4.1 | **done** | `VersionPicker` component (replaces the static badge); behavior in `site.js`, base-path-agnostic `/v/<version>/` derivation. Browser round-trip verified. Switches to version home (preserve-page is a Phase-7 enhancement) |
| 5b.12 | `docs-versions-toml` | Top-level TOML config | S | | 11.7 §3.2 | **done** | `docs_site/docs_versions.toml` (at the docs-project root, not the repo root as the spike sketched; read via `settings.VERSIONS_CONFIG`). Keys: pattern/include/exclude/oldest/newest/latest; `oldest=0.150.0` as a safe floor while migration is deferred |
| 5b.13 | `docs-build-check-cmd` | Inverse CI check: manifest ↔ FS parity | M | | 11.7 §11 | **done** | Folded into the guard harness (per Juro): `guards/versions_manifest.py` + `docs_versions_check` command. Resolves the name collision with 5b.17 |
| 5b.14 | `versions-manifest-integrity-check` | Manifest ↔ dir 2-way sync guardrail | S | | 11.10 §3.16 | **done** | Same `versions_manifest` guard: orphans, half-built dirs, alias resolution, build-info sanity |
| 5b.15 | `cross-version-link-check` | Links from `/v0.X/` to `/v0.Y/` resolve | M | | 11.10 §3.8 | **done** | `guards/cross_version_link.py`; reuses the SiteIndex parser + clean-URL `resolve_link` (the same machinery as internal_link) over one index of the whole versions tree, so cross-version links resolve like a browser would. Skips absolute + non-page-asset links (explicit suffix allowlist so version dirs like `0.150.0/` aren't mis-skipped) |
| 5b.16 | `ci-release-docs-workflow` | Rewrite `release-docs.yml` (tag → docs-build → commit → push) | S | ✓ | 11.7 §3.1, §6, §8.2 | **done** | New build→`docs_versions_check`→commit→push flow on master (no gh-pages/mike); `dev` committed on master push, `[skip ci]` breaks the loop. Dormant until cutover; Pages deploy assembly is Phase 6 (6.4) |
| 5b.17 | `docs-build-check-command` | Pre-commit CI gate (full build to temp, all guardrails) | M | ✓ | 11.9 §4 | **done** | Command already existed (`docs_build_check`, cites 11.9 §4). 5b **wired it into PR CI**: `tests.yml`'s `test_docs` job now runs `docs_build_check` + `docs_versions_check` (replacing the branch's broken `mkdocs build`), with `fetch-depth: 0` for the git-metadata footer |

**Out of scope here:** SEO/AIO polish; cutover (Phase 6).

### Chunk execution

Phase 5b was built in four vertical chunks (mirroring spike §9's "prove the
manifest+build contract first"), each verified and reviewed before the next:

| Chunk | Scope | Features |
|---|---|---|
| **1 — Manifest + single-version build** | vendor mike `Versions`/redirect, `verspec`, `_build_info.json`, `build_docs` version mode + alias materializer | 5b.1-5b.7, 5b.10 |
| **2 — version_picker** | header dropdown reading `versions.json` (markup + site.js) | 5b.11 |
| **3 — docs-build-all** | `docs_versions.toml`, bootstrap core, worktree walker | 5b.8, 5b.9, 5b.12 |
| **4 — Guards + CI** | `versions_manifest` + `cross_version_link` guards via `docs_versions_check`; `release-docs.yml` rewrite | 5b.13-5b.17 |

**Deferred / dormant by design** (not gaps): `docs-build-all` skips every tag
today because no released tag yet contains the builder (the historical-version
migration is the spike §7 decision, post-Phase-7); the rewritten
`release-docs.yml` doesn't run until the branch merges at cutover, and its Pages
**deploy** (assembling `site/` from the committed `versions/*`) is Phase 6 (6.4).

---

## Phase 5c — SEO + AIO + social cards + chrome polish

Goal: every SEO/AIO feature wired. Site is Lighthouse-clean and AI-bot-friendly. Social cards generated.

**Sharp focus:** discoverability + polish only.

| # | ID | Name | Effort | Critical | Source | Status | Notes |
|---|---|---|---|---|---|---|---|
| 5c.1 | `sitemap-xml` | `sitemap.xml` (latest/ URLs + git lastmod + changefreq + priority) | M | | 11.12 §2.A.2 | **done** (Chunk 2) | `build/seo.py::write_sitemap`; lists root (latest) URLs for indexable doc pages (skips noindex + redirect stubs), `<lastmod>` from git per source (via `url_to_md`+`get_page_git_meta`), `<priority>` by section (1.0 home / 0.8 getting-started / 0.6 concepts·reference·guides·overview / 0.4 community·releases). Emitted by `build_docs` for the current-version build (preview mode) only |
| 5c.2 | `robots-txt` | `robots.txt` (disallow old versions; AI-bot rules; sitemap pointer) | S | | 11.12 §2.A.3 | **done** (Chunk 2) | `build/seo.py::write_robots`; `User-agent: *` allow-all + auto-generated `Disallow: /v/<version>/` for every version except the 2 newest releases + `latest` (read from `versions.json`; none yet, so dormant) + sitemap pointer + explicit AI-bot allow stanzas (GPTBot/ClaudeBot/anthropic-ai/Google-Extended/PerplexityBot/CCBot). Uses the actual `/v/<version>/` scheme, not the spike's `/v0.x/` |
| 5c.3 | `og-image-generation` | OG image PNG per page (via Playwright) | L | | 11.12 §2.A.4, 11.9 §2.4 | **done** (Chunk 4) | `build/social_cards.py` post-build step: rewrites each indexable page's `og:image`/`twitter:image` from the default to its generated `/og/<path>.png`. Render-time keeps the valid favicon default (`pipeline.default_og_image_url`), so the swap only happens where a card exists - degrades cleanly to the default if Playwright/Chromium is absent (no 404s). Skips noindex + custom-`og_image` pages. **Deploy note:** the Phase-6 root-build CI (6.4) needs `playwright install chromium` for cards to actually generate |
| 5c.4 | `og-card-template` | Django template for 1200×630 social card | S | | 11.9 §2.4 | **done** (Chunk 4) | `components/og_card/` - a Component rendering a standalone, fully self-contained 1200×630 HTML doc (inline CSS, system fonts, inline SVG mark; brand dark/teal). Screenshotted via `set_content` (no server/network) |
| 5c.5 | `social-card-generator` | Orchestration (Playwright headless) | L | | 11.9 §2.4 | **done** (Chunk 4) | Sync Playwright (matches the e2e test pattern); one reused page, `set_content`+`screenshot` per card into the cache. Wired into `build_docs` (current-version build only; `--no-social-cards` opt-out). Full build ~16s cold / ~4.5s fully-cached |
| 5c.6 | `social-card-caching` | Hash + sidecar JSON cache | S | | 11.9 §2.4 | **done** (Chunk 4) | **Deviation:** content-addressed cache (`<hash>.png` in gitignored `docs_site/.cache/og/`) instead of a sidecar JSON - the hash (template+title+description+section) IS the filename, so it's equivalent + simpler. Survives `build_site` wiping the output; a fully-cached build launches no browser. Unused entries pruned each run |
| 5c.7 | `og-twitter-cards` | Per-page OG + Twitter card `<meta>` | M | | 11.12 §2.A.4 | **done** (Chunk 1) | OG (`type=article`, site_name, title, description, url, image) + Twitter (`summary_large_image`) in DocPage head. `og:image` resolved to an absolute URL by `pipeline._resolve_og_image` (front-matter `og_image` > interim site default = favicon.png; per-page generated cards land in Chunk 4) |
| 5c.8 | `json-ld-techarticle` | TechArticle JSON-LD on content pages | M | | 11.12 §2.A.7 | **done** (Chunk 1) | `_build_article_jsonld` in DocPage; emitted on content pages, skips homepage (`current_path==""`) + `docs/community/*`. `datePublished`/`dateModified` from new `PageGitMeta.created` (first commit) + `last_updated`; omitted on pages with no git history. Skips SoftwareSourceCode / HowTo per spike |
| 5c.9 | `json-ld-validity-guardrail` | Build-time JSON-LD schema validation | S | | 11.12 §2.A.7, §11.10 | **done** (Chunk 1) | `guards/json_ld.py` (registered in `GUARDS`); validates every `<script type=ld+json>` block parses + has `@context`/`@type`/per-type required keys (malformed=ERROR, missing recommended=WARNING). `SiteIndex.PageRecord.jsonld_blocks` feeds it. **Surfaced + fixed a latent bug**: Django auto-escaped the JSON-LD (`&quot;`), which browsers don't decode inside `<script>` - the *existing* breadcrumb JSON-LD was invalid too. Both now use script-safe `_jsonld_dumps` + `\|safe` |
| 5c.10 | `llms-txt` | `/llms.txt` short index + `/llms-full.txt` concatenation | M | | 11.12 §3.B.1 | **done** (Chunk 3) | `build/llms.py`; both built from the nav tree + the `.md` companions (title/description/expanded-body via `parse_page`). `llms.txt` = nav-ordered `## Section` index with per-item descriptions, standalone hubs → `## Optional`; `llms-full.txt` = `flat_pages()`-ordered concatenation with `# Title` + Source headers (front-matter stripped). `<link rel="alternate" type="text/markdown" href="/llms.txt">` added to the DocPage head; asset guard skips the generated root files. Root-build only (like SEO); `--no-llms` opt-out. **Two source fixes folded in:** (1) `pipeline.expand_snippets` resolves `--8<--` file includes in the companion/llms-full (Pass-2 feature, previously left literal - so License/CoC now show their text, not the directive; also fixes feature 1.28); (2) Mechanism-3 sweep of the description extractor (`frontmatter.py`) - skips raw HTML / comments / `--8<--` directives, drops images + badge-links, resolves `[X][Key]` cross-refs, preserves `snake_case` (was mangling `django_components`→`djangocomponents`) - which also fixes the live `<meta description>`/og:description on License, Code of Conduct, Typing, Welcome, etc. |
| 5c.11 | `indexing-manifest` | `meta/indexing.json` (URLs + canonicals + robots directives) | M | | 11.12 §4.C.5 | **done** (Chunk 2) | `build/seo.py::write_indexing_manifest`; `{generated_at, version, pages:[{url, canonical, robots}]}` over every built doc page (incl. noindex ones, for the audit). The §11.10 guardrail consumer is tautological here (the manifest is generated *from* the built SiteIndex), so it's omitted. For the current-version build, `canonical` now equals `url` (both root) after 6.12 part a; only old `/v/<ver>/` snapshots still self-canonical (6.12 part b, Phase 6). `SiteIndex.PageRecord` extended with `robots`+`canonical` to feed this |
| 5c.12 | `anchor-deprecation-timer` | 12-month timer on legacy anchor aliases | S | | 11.12 §2.A.13, §7.2 | **done** (Chunk 6) | `guards/anchor_deprecation.py` + `settings.ANCHOR_ALIAS_DEPRECATION_DATE` (None = dormant; set to cutover+12mo at cutover). After the date, the guard fails any content *source* still linking via the long-form `#django_components.X` anchor (fence- + inline-code-aware, so the docstring-guide literals at development.md:573/609 aren't flagged), forcing internal migration before aliases are removed. **Deliberately NOT auto-expiring the emitted aliases** (a one-way breaking change → stays a manual step, not a time bomb that would also break the `anchor_alias` guard). Today there are 0 real long-form usages, so it starts green |
| 5c.13 | `lighthouse-ci` | GitHub Actions workflow with Perf/A11y/SEO thresholds | M | | 11.12 §2.A.14 | **done** (Chunk 6) | `.github/workflows/maint-docs-lighthouse.yml` + `.github/lighthouserc.json` (4 content pages; the iframe-demo example dropped). Builds + assembles `/static` via collectstatic. **Ran locally (lhci + Playwright Chrome) and fixed the real issues it surfaced**, lifting the site from a11y 0.86-0.91 to **0.95-1.0, SEO 100, best-practices 100**: removed `anchor_linenums` (thousands of empty code-line `<a>`s → "links without a name"); darkened `--c-fg-subtle` + `--c-link` + added `--c-code-text` for WCAG AA contrast; underlined in-prose + `doc-type` links; made 6 generic "[here]/[Learn more]" links descriptive (incl. 2 public-API docstrings). Gates: SEO+BP=1.0, **a11y>=0.95**, perf warn. **Residual a11y (→1.0) = Pygments syntax-token contrast (code comments/keywords) + type-links in signature blocks: a code-theme retune, tracked follow-up.** First CI run may still need threshold confirmation |
| 5c.14 | `html-minifier` | minify-html post-build pass | S | | 11.9 §2.6 | **done** (Chunk 5) | `build/minify.py::minify_site`; `minify-html` (Rust, MIT) added to the `docs` dep group (replaces `mkdocs-minify-plugin`). Final pass in `build_docs`, all modes; `--no-minify` opt-out; lazy+guarded import (degrades to no-op). Conservative config (lib defaults keep doctype/`<pre>`/attr spacing; we add keep-closing-tags + minify_css; **minify_js OFF so JSON-LD is never touched**). Verified: code fences, SVG, JSON-LD, redirect stubs all preserved; **~47% smaller** (the spike's ~8% estimate was for htmlmin2). v0.18 kwargs differ from the spike's snippet |
| 5c.15 | `html-sanitizer` | bleach/html5lib sanitization pass | S | | main §4.7 | **won't-do** (by design, per Juro) | The §4.7 "sanitize" was an aspirational sketch, NOT a ported plugin (the §11.9 plugin audit owns minify/redirects/social but lists no sanitizer - there was nothing to port). A full-page bleach pass would strip the site's own `<script>` (FOUC, site.js/search.js), JSON-LD, inline SVG, and example `<iframe srcdoc>` demos; and there is **no untrusted-input XSS sink** (all rendered content - markdown, docstrings, CHANGELOG, examples - is maintainer-committed). A sanitizer defends against untrusted input that doesn't exist here, so it's all breakage risk, no value. Rationale noted in `build_docs` so it isn't re-added |
| 5c.16 | `edit-on-github-url` | Edit-on-GitHub button per page | S | | main §9.3 | **done** (Chunk 1) | `paths.edit_url_for` builds `{REPO_URL}/edit/{branch}/{repo-rel-path}`; only real content pages get a link (generated pages render from a temp staging dir outside the repo, so `relative_to()` raises → no link). Rendered in the DocPage footer; threaded via build + dev-server context for parity |
| 5c.17 | `redirect-file-emitter` | Static `<meta refresh>` HTML stubs for moved URLs | S | | 11.9 §2.5, main §9.5 | **done** (Chunk 5) | `build/redirects.py`; the 5 mkdocs-redirects entries remapped onto the `/docs/` taxonomy. Triple mechanism (meta-refresh + `location.replace` + canonical) + `noindex`. Refresh/JS hrefs are **relative** (base-path-safe via `os.path.relpath`), canonical absolute. Emitted in `build_site` (every build) so the guard validates them. Wholesale pre-migration URL preservation stays Phase 6 (6.1) |
| 5c.18 | `redirect-target-check` | Redirect targets resolve in built site | S | | 11.10 §3.13 | **done** (Chunk 5) | `guards/redirect_target.py` (registered in `GUARDS`, runs in `docs_build_check`); for every `is_redirect_stub` page, resolves `redirect_target` via `SiteIndex.resolve_link` (ERROR if it 404s / is empty; external targets skipped). Generic - covers any future redirect stub, not just the 5c.17 set |
| 5c.19 | `external-link-check` | Weekly lychee workflow (out-of-band) | S | | 11.10 §3.18 | **done** (Chunk 6) | `.github/workflows/maint-docs-external-links.yml`; weekly cron + dispatch (not a PR blocker). Builds the site, runs `lycheeverse/lychee-action` over the built HTML for outbound http(s) links only (relative/internal links + our own not-yet-live domain excluded; the internal_link/anchor guards already cover on-site links per PR). A broken external link reddens the scheduled run. **Ran locally and fixed a real bug it surfaced:** `--root-dir` is required or lychee errors on every root-relative internal link (`/docs/...`) in local-file mode (13.5k false errors → 6 real external ones, mostly bot-block 403s) |

**Out of scope here:** cutover (Phase 6).

### Chunk execution plan

Phase 5c is executed in **6 vertical chunks**, grouped by where each feature
hooks into the build (in-pipeline head metadata vs post-build emitters vs
out-of-band CI), ordered so shared plumbing and low-risk metadata land first,
the heaviest new infra (Playwright) is isolated, and the CI gates land last
(once the site is clean enough to pass them). Mirrors the Phase 4 / 5b approach.

| Chunk | Scope | Features | Status |
|---|---|---|---|
| **1 — Head metadata & chrome** | OG/Twitter tags, TechArticle JSON-LD + validity guard, edit-on-GitHub. Establishes per-page metadata plumbing (source path, og_image, git `created`). `og:image` uses interim site default (Playwright swap is Chunk 4) | 5c.7, 5c.8, 5c.9, 5c.16 | **done** |
| **2 — Crawl & index files** | sitemap.xml, robots.txt, indexing.json - post-build root emitters sharing one `build/seo.py` (one SiteIndex pass + the `versions.json` manifest). Generated by `build_docs` for the current-version build (preview mode) (= the deployed site root); per-version snapshots + canonical→latest alignment deferred to Phase 6 (6.4) per Juro. `--no-seo` opt-out | 5c.1, 5c.2, 5c.11 | **done** |
| **3 — llms.txt** | `/llms.txt` + `/llms-full.txt` (`build/llms.py`, reuses `.md` companions + nav); `<link rel=alternate type=text/markdown>` head tag; description-extractor hardening (HTML/snippet/image/cross-ref/snake_case) | 5c.10 | **done** |
| **4 — Social cards** | OgCard component + sync-Playwright generator + content-addressed cache; post-build rewrite of `og:image` default → per-page PNG. Degrades gracefully without a browser (keeps default). Deploy CI (6.4) needs `playwright install chromium` | 5c.4, 5c.5, 5c.6, 5c.3 | **done** |
| **5 — Redirects + final HTML passes** | redirect emitter (in build_site) + target-check guard; minify final pass (after all HTML written). Sanitizer (5c.15) **dropped by design** - the specced full-page bleach would break the site's own JS/JSON-LD/SVG and there's no untrusted-input XSS sink | 5c.17, 5c.18, 5c.14 (+5c.15 dropped) | **done** |
| **6 — Out-of-band CI** | anchor-deprecation guard + date setting (dormant until cutover, auto-expiry declined); Lighthouse workflow + lhci config (static assembled via collectstatic); weekly lychee external-link workflow. Workflows need first-run CI validation (can't run lhci/lychee locally); build steps de-risked locally | 5c.12, 5c.13, 5c.19 | **done** |

---

## Phase 6 — Cutover

Goal: merge the migration branch so the new `docs_site` build replaces the old mkdocs site. One atomic commit; never two sites deployed at once (see main §8 branch-model invariant). Inbound URLs preserved.

**Sharp focus:** cutover and only cutover. This is a comparison + a single merge commit, not a live deploy switch.

| # | ID | Name | Effort | Critical | Source | Status | Notes |
|---|---|---|---|---|---|---|---|
| 6.1 | `materialize-redirects-script` | Convert `latest/` symlink → redirect HTML files | S | ✓ | 11.8 §6, §7 | pending | ~50 LOC; Windows-compat |
| 6.2 | `import-gh-pages-tree` | One-time mirror of `origin/gh-pages` into `docs_site/versions/` (57 versions + dev) | M | ✓ | 11.8 §5.1, §7 | pending | ~30 min execution. Target changed from `docs/v/` to `docs_site/versions/` per main §4.0a |
| 6.3 | `docs-build-check-validation` | Validate imported tree before commit | S | ✓ | 11.8 §5.1, §7 | pending | Cutover gate |
| 6.4 | `ci-deploy-site-via-actions` | Rewrite docs CI: build `docs_site` → `site/` (current + `docs_site/versions/*`), deploy `site/` via GitHub Actions | M | ✓ | main §4.0a, §4.6 | pending | Supersedes "switch Pages source to master/docs/v/". **Static-assembly piece already built:** `builder.collect_static()` copies `/static` into the output via the staticfiles *finders*. `build_docs` runs it **by default** for the current-version build (`--no-collectstatic` to skip); it's skipped for per-version snapshots so they don't each duplicate static (the deploy mounts one shared `/static` at the root). The Lighthouse workflow (5c.13) uses the same assembly. Note: must copy from finders, not override `settings.STATIC_ROOT` + `collectstatic` (the storage caches its dest mid-build) |
| 6.5 | `gh-pages-branch-deletion` | Delete `gh-pages` branch (deferred 3-6 months) | S | | 11.8 §5.1, §8.2 | pending | Cleanup, not blocker |
| 6.6 | `cutover-docs-cleanup` | Delete `docs_old/` + `mkdocs.yml`; remove mkdocs/material/mike deps from pyproject.toml; `grep -rn docs_old .` and update every straggler | M | ✓ | main §4.0a, §6 | pending | The `docs_old` rename makes this a search. **Also grep `master/docs/`**: absolute GitHub URLs (README image, CHANGELOG link, mkdocs `edit_uri`) still say `docs/` and won't be caught by the `docs_old` grep |
| 6.7 | `content-move-to-content-dir` | Move user-facing pages `docs_old/` → `docs_site/content/` (preserve subtree structure so URLs are stable) + remaining assets (css, images) into `docs_site/static/` | L | ✓ | main §4.0a, §4.1, 11.11 §4.2 | **folded into 3b.25** | The page move now happens during the Phase 3b content port (3b.25), not at cutover - the "keep mkdocs building" rationale no longer applies (branch cannibalizes mkdocs; Phase 6 compares against the *deployed* old site, see main §8). What remains for Phase 6 here: sweep up any *remaining* assets (css, images) and verify nothing user-facing is still left in `docs_old/` before deleting it |
| 6.8 | `examples-move` | Move `docs_old/examples/` → `docs_site/examples/`; update pytest `testpaths`, ruff override, sampleproject `EXAMPLES_DIR` | M | ✓ | main §4.0a, §4.1 | pending | Was Phase-1 feature 1.4 |
| 6.9 | `devguides-move` | Move `docs_old/community/devguides/` → internal `docs/devguides/` (was never meant to be user-facing) | S | | main §4.0a | pending | Pair with 6.10 review |
| 6.10 | `devguides-relevance-review` | Review each devguide article for whether it's still relevant/accurate before keeping it as internal docs | S | | main §4.0a | pending | Content audit |
| 6.11 | `benchmark-report-relocation` | Relocate asv report `docs_old/benchmarks/` → `benchmarks/report/`; add static-passthrough copy into the build; update `asv.conf.json` `html_dir`, `release-docs.yml`, `benchmarks/README.md` | M | | main §4.0a | pending | Static passthrough, not "serve index.html if present" |
| 6.12 | `canonical-latest-alignment` | Implement the §2.A.1 canonical strategy properly: pages canonical to their `/latest/` (root) counterpart, not self-referential versioned URLs; pages absent from latest canonical to self + `noindex,follow`; `/latest/` (root) canonical to itself | M | ✓ | 11.12 §2.A.1 | **part a done (5c) / part b pending** | **(a) DONE in 5c:** current-version build → root canonical (`build_site(versioned_canonical=...)`), fixing the live anti-pattern §2.A.1 warns against + realigning og:url / breadcrumb / sitemap / indexing.json to root; breadcrumb builder now base-path-aware. **(b) pending (Phase 6):** old `/v/<ver>/` snapshots → `/latest/` counterpart + `noindex,follow` when absent from latest - needs the multi-version manifest (which pages exist in latest), only available at assembly. Pairs with 1.27's deferred per-version noindex |

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

| Phase | Goal | Count | Critical | Status |
|---|---|---|---|---|
| 0 | Pre-work in `src/` | 4 | 2 | **4/4 done** (0.4 is local-only edit to untracked CLAUDE.md) |
| 1 | Foundation: 1 page end-to-end | 30 | 23 | **29/30 done** (1.26 `canonical-urls` reopened as **partial** - ships versioned self-canonical, not the §2.A.1 `/latest/` strategy → tracked as 6.12; content move 1.3 → 3b.25; examples move 1.4 → 6.8) |
| 2 | `{% example %}` end-to-end | 7 | 4 | **6/7 done** (2.6 dropped) |
| 3a | Theme + core chrome | 23 | 17 | **22/23 done** (3a.9 CodeTabs deferred to when needed) |
| 3b | Mass content port + responsive + content guardrails | 25 | 12 | **25/25 done** (Phase 3b complete) |
| 4 | API reference (mkdocstrings replacement) | 67 | 30 | **67/67 done** (Chunks 0/A-J complete: all 14 reference pages + the reference guards; plus 4.67, the collapsible per-member TOC) |
| 5a | Search v1 | 6 | 4 | pending |
| 5b | Versioning | 17 | 12 | **17/17 done** (target moved to `docs_site/versions/` per §4.0a; 5b.13 folded into the guard harness; historical bootstrap + Pages deploy deferred to post-Phase-7 / Phase 6 by design) |
| 5c | SEO + AIO + chrome polish | 19 | 0 | **18/19 done, 1 dropped** — COMPLETE (Ch1: 5c.7/8/9/16; Ch2: 5c.1/2/11; Ch3: 5c.10; Ch4: 5c.3/4/5/6; Ch5: 5c.14/17/18 + 5c.15 dropped; Ch6: 5c.12/13/19) |
| 5d | Feature-parity audit (process) | 0 | 0 | pending |
| 6 | Cutover | 12 | 8 | pending (6.12 `canonical-latest-alignment` added - the real §2.A.1 canonical strategy 1.26 only partially shipped) |
| 7 | Search v2 (post-cutover polish) | 4 | 0 | pending |
| 8 | Search v3 (blocked on analytics target) | 1 | 0 | pending |
| 9 | Landing page (codesign) | 1 | 0 | pending |
| 10+ | Deferred / post-launch maintenance | 7 | 0 | pending |
| **Total** | | **223** | **112** | **188/223 done** (phases 0-4 + 5b + **5c complete**: 18 done + 5c.15 dropped; 1.26 reopened as partial → 6.12) |

### Phase 0 closed

Phase 0 landed across four commits on `jo-docs-mkdocs-migrate`:

- [`3cb4c531`](https://github.com/django-components/django-components/commit/3cb4c531) — link codemod (Phase 0.1)
- [`28cea92d`](https://github.com/django-components/django-components/commit/28cea92d) — Google-section sweep (Phase 0.2)
- [`14554db7`](https://github.com/django-components/django-components/commit/14554db7) — "Writing docstrings" convention (Phase 0.3)
- [`51ae0cae`](https://github.com/django-components/django-components/commit/51ae0cae) — Examples-block normalization (Phase 0.5; the §11.4 follow-up flagged in `ee8cd3ec`)

P0.4 (CLAUDE.md docstring rule) is "done (local-only)": the file is intentionally untracked, so the edit stays on disk and is not committed. The rule is active for any AI agent that loads CLAUDE.md.

If something is missing here, **add it**. This file is the canonical inventory.
