# docs_site

The django-components documentation site. A Django project that uses
django-components to render markdown pages into static HTML, pre-rendered
at build time and deployed to GitHub Pages.

This replaces the previous mkdocs/Material setup. The full design and migration
plan live in [`design/`](design/) (start with `DESIGN.md` and
`DESIGN_features.md`).

## Quick start

All commands run from inside this directory:

```sh
cd docs_site
```

While editing, run the dev server for live preview. It renders each page on the
fly through the same pipeline as the build, so you just edit a markdown file and
reload:

```sh
uv run python manage.py docs_serve   # open http://127.0.0.1:8000/
```

To produce the full static site, build it and validate the links:

```sh
uv run python manage.py build_docs   # -> ./site/ (gitignored)
uv run python manage.py docs_test    # validate links/anchors in ./site/
```

## Commands

All run from `docs_site/` as `uv run python manage.py <command>`.

**Author & preview:**

| Command | What it does |
|---|---|
| `docs_serve` | Dev server; renders pages live from `content/` (no search index) |
| `docs_serve_built` | Build the full site (incl. Pagefind search + collected `/static/`) and serve it like production; `--no-build` reuses `./site/` |
| `build_one <file> -o <out>` | Render a single page to one HTML file (handy when debugging the pipeline) |

**Build & validate:**

| Command | What it does |
|---|---|
| `build_docs` | Build every `.md` to `<output>/<slug>/index.html` (+ `.md` companions + Pagefind index). Defaults to `./site/` |
| `docs_test` | Validate internal links + anchors in a build (`--strict` fails on warnings too) |
| `docs_build_check` | CI gate: build to a temp dir and run the full guardrail suite (links, anchors, fences, nav drift, ...) in strict mode |

**Versioning** (see [Versioning](#versioning)):

| Command | What it does |
|---|---|
| `build_docs --docs-version X --alias latest` | Build a committed version snapshot into `versions/X/` + update the manifest + the `latest` redirect |
| `docs_build_all` | Bootstrap/rebuild every version selected by `docs_versions.toml` (a git worktree per tag); `--dry-run` to preview |
| `docs_versions_check` | Validate the committed `versions/` tree (manifest <-> filesystem, aliases, cross-version links) |
| `docs_preview` | Build a few fake versions locally and serve them, to test the version picker (latest / dev / specific) |

Common `build_docs` options:

- `--content <dir>` - content directory (default: `content/`)
- `--docs-version <ver>` - version label (default: from `pyproject.toml`); switches to "version mode" (writes `versions/<ver>/` + manifest)
- `--alias <name>` - alias (e.g. `latest`) pointed at this version; materialized as redirect stubs
- `-o, --output <dir>` - output directory (default: `./site/`, or `versions/<ver>/` in version mode)
- `--title <text>` - manifest display title (e.g. `dev (a1b2c3d)`)
- `--no-manifest-update` - don't rewrite `versions.json` (used by `docs_build_all`)
- `--no-companions` / `--no-search` - skip `.md` companions / the Pagefind index

## The rendering pipeline

Each markdown file is rendered through four passes
([`apps/docs/build/pipeline.py`](apps/docs/build/pipeline.py)):

1. **Fence protection** - wraps code blocks in `{% verbatim %}` so Django
   doesn't execute template tags inside code examples
   ([`fence_protection.py`](apps/docs/build/fence_protection.py))
2. **Django template engine** - expands `{% version %}`, `{% component %}`,
   `{% example %}`, `{% include_file %}`, and other tags
3. **python-markdown + pymdownx** - converts the expanded markdown to HTML
   (syntax highlighting, admonitions, tabs, TOC, etc.)
4. **DocPage layout** - wraps the content in a full HTML page with `<head>`
   metadata ([`components/doc_page/`](apps/docs/components/doc_page/))

Tags that emit block-level HTML (like `{% example %}`) run in step 2.
Their output must start at column 0 (no leading whitespace) so
python-markdown in step 3 treats it as block-level HTML rather than a
code block.

## Sidebar navigation (`_nav.yml`)

The left sidebar is driven by [`content/_nav.yml`](content/_nav.yml).
The loader lives at [`apps/docs/build/nav.py`](apps/docs/build/nav.py).

### Schema

A section has EITHER `items` (1-level flat list) OR `groups` (2-level
with collapsible sub-groups), never both. Section labels can optionally
be links via `path`.

```yaml
sections:
  - label: Overview
    path: /overview/   # optional: makes the section label clickable

  # 1-level: flat list of pages
  - label: Getting Started
    items:
      - { title: Installation, path: /getting_started/installation/ }
      - { title: Quick start,  path: /getting_started/quick_start/ }

  # 2-level: collapsible sub-groups
  - label: Concepts
    groups:
      - label: Fundamentals
        items:
          - { title: Render API, path: /concepts/fundamentals/render_api/ }
          - { title: Component defaults, path: /concepts/fundamentals/component_defaults/ }
      - label: Advanced
        items:
          - { title: Hooks, path: /concepts/advanced/hooks/ }
```

### Behavior

- **Active highlighting**: the sidebar auto-highlights the current page
  based on URL matching.
- **Collapsible groups**: sub-groups start collapsed unless the current
  page is inside them. Collapse state is saved to `localStorage`.
- **Breadcrumbs**: generated from the nav tree by walking up from the
  current page (section > group > page).
- **Prev/next navigation**: computed from the document order in the nav.

### Caveats

- Paths in `_nav.yml` must match the clean URL slug for the page. For
  `content/foo/bar.md` the path is `/foo/bar/`. For
  `content/foo/index.md` the path is `/foo/`.
- If a path doesn't match any content file, the sidebar link will be a
  dead link (no build-time validation yet; that's Phase 3b feature
  `nav-yaml-validity-check`).
- A section cannot have both `items` and `groups`. The nav loader does
  not enforce this at build time yet, but the sidebar will render incorrectly.

## Template tags

Custom template tags available in markdown files via the Django template
engine (Pass 1). Defined in
[`apps/docs/templatetags/docs_extras.py`](apps/docs/templatetags/docs_extras.py).

### `{% example "name" %}`

Embeds a tabbed widget showing an example's source code and live demo.

```markdown
{% example "fragments" %}
```

Renders three tabs:
- **Live demo** - the actual rendered component in an `<iframe>`
- **Component** - syntax-highlighted source from `component.py`
- **Page** - syntax-highlighted source from `page.py`

**Caveats:**
- The example name must match a directory under `EXAMPLES_DIR`
  (currently `docs_old/examples/`) with a `component.py` and `page.py`.
- The tag output goes through `_lstrip_outside_pre()` to strip Django
  template indentation while preserving code indentation inside `<pre>`
  blocks.

### `{% version %}`

Outputs the current django-components version string (e.g. `0.151.0`).

```markdown
Install version {% version %}
```

### `{% include_file "path" %}`

Includes a file as a fenced code block. Language is inferred from the
file extension unless explicitly set.

```markdown
{% include_file "docs_old/examples/fragments/component.py" %}
{% include_file "some/config" language="toml" %}
```

**Caveats:**
- The path is relative to the working directory (the repo root when
  running from `docs_site/`), not to the content file.

### `{% image "src" %}`

Renders an `<img>` tag with optional attributes.

```markdown
{% image "/static/screenshot.png" alt="Example" width="400" css_class="bordered" %}
```

## Tabbed content (pymdownx.tabbed)

Multi-tab code blocks work via `pymdownx.tabbed` (alternate style).
Tab switching is handled by `site.js`, not CSS-only.

```markdown
=== "uv"
    ```bash
    uv pip install django-components
    ```

=== "pip"
    ```bash
    pip install django-components
    ```
```

**Behavior:**
- Tabs can contain mixed content (text + code blocks), not just code.

**Caveats:**
- The `===` tab syntax must be flush-left in the markdown source (no
  leading indentation).
- Each tab's content must be indented 4 spaces under its `===` header.

## Code blocks

Fenced code blocks support language labels and copy buttons
(injected by `site.js` at page load).

```markdown
```python
class MyComponent(Component):
    pass
`` `

```python title="components/calendar.py"
class Calendar(Component):
    pass
`` `
```

**Features:**
- **Language label**: auto-detected from the fence info string, shown
  top-right in muted text.
- **Copy button**: appears on hover (top-right), copies code to
  clipboard, shows a checkmark for 1.5s.
- **Filename tab**: `title="filename.py"` renders as a monospace tab
  header above the code block (via `pymdownx.highlight`).

## Theme (dark / light / auto)

Three theme modes via the header picker buttons:
- **Light** (sun icon): forces light theme
- **System** (monitor icon): follows OS `prefers-color-scheme`
- **Dark** (moon icon): forces dark theme

The active mode is highlighted with accent color. Choice is persisted
in `localStorage` under the key `djc-theme`.

A FOUC (Flash of unstyled content) prevention `<script>` in `<head>` reads the stored value and
sets `data-theme` on `<html>` before the first paint.

## Resizable sidebars

The dividers between sidebar/content and content/TOC are draggable.
A 4x2 dot grid grip is visible at the viewport center. Widths are
clamped to 160-500px and persisted in `localStorage`.

## Examples

### How it works

The wiring has three layers:

1. **Autodiscovery** ([`apps/docs/examples.py`](apps/docs/examples.py))
   walks `EXAMPLES_DIR` (currently `docs_old/examples/`), imports each
   example's `component.py` and `page.py`, finds the `*Page` Component
   subclass, and caches a registry of `ExampleInfo` objects.

2. **`{% example %}` tag**
   ([`apps/docs/templatetags/docs_extras.py`](apps/docs/templatetags/docs_extras.py))
   looks up the example in the registry and calls
   `ExampleCard.render(kwargs={"name": ..., "info": ...})`.

3. **ExampleCard component**
   ([`apps/docs/components/example_card/`](apps/docs/components/example_card/))
   reads the source files, highlights them with Pygments, renders the live
   demo via `Component.as_view()`, and assembles the tabbed widget.

### Example directory layout

Each example lives in its own directory under `docs_old/examples/`:

```
docs_old/examples/fragments/
    component.py              <- the components being demonstrated
    page.py                   <- a *Page Component that renders the demo
    test_example_fragments.py <- pytest tests proving the example works
    README.md                 <- the mkdocs-era writeup (--8<-- includes)
    images/                   <- screenshots/GIFs (optional)
```

Required conventions:

- `component.py` must exist and define at least one registered Component.
- `page.py` must define a Component subclass whose name ends in `Page`
  (e.g. `FragmentsPage`, `TabsPage`).
- The Page class must have a nested `class View` with at least a `get()`
  method so it can be rendered via `Component.as_view()`.

### Fragment examples

Some examples (like `fragments`) use AJAX to load HTML fragments on button
click. On a live Django server this works via `get_component_url()`, but
on the static GitHub Pages site there's no server.

The solution: **pre-render each fragment variant at build time** and use a
**JS fetch interceptor** to redirect requests to the static files.

To declare fragment variants, add a `DocsExample` inner class to the Page.
The `fragments` dict maps each variant name (used to construct the static
file path) to the query params dict that the live server expects:

```python
class FragmentsPage(Component):
    class DocsExample:
        fragments = {
            "alpine": {"type": "alpine"},
            "htmx": {"type": "htmx"},
            "js": {"type": "js"},
        }
    ...
```

At build time, `build_docs` calls each variant through `as_view()` with the
query params from the dict and writes the responses to static files:

```
site/examples/fragments/index.html          <- full page
site/examples/fragments/alpine/index.html   <- alpine fragment response
site/examples/fragments/htmx/index.html     <- htmx fragment response
site/examples/fragments/js/index.html       <- js fragment response
```

The ExampleCard then rewrites the rendered demo HTML by replacing each
`get_component_url()` output with the corresponding static file path.
It calls `get_component_url(PageCls, query={"type": "alpine"})` to get
the exact URL string that appears in the HTML, and replaces it with
`/examples/fragments/alpine/`. This is a direct string replacement -
no JS interceptor or runtime patching needed.

### Adding a new example

1. Create `docs_old/examples/<name>/component.py` with your component(s).
2. Create `docs_old/examples/<name>/page.py` with a `*Page` Component
   that has `class View` with `def get(self, request)`.
3. Add a test file `test_example_<name>.py`.
4. If the example uses fragments, add `class DocsExample` with a
   `fragments` dict.
5. Reference it in a markdown page with `{% example "<name>" %}`.
6. Run `python manage.py build_docs` and verify.

## Front-matter

Markdown pages may declare optional YAML front-matter
([`apps/docs/build/frontmatter.py`](apps/docs/build/frontmatter.py)):

```yaml
---
title: Page Title              # overrides the first # H1
description: One-line summary   # meta description (falls back to first paragraph)
og_image: /path/to/image.png
noindex: false
canonical: https://...
tags: [example, advanced]
---
```

All fields are optional. With no front-matter, the title comes from the first
`# H1` and the description from the first paragraph.

## Versioning

Built versions live in `docs_site/versions/<version>/` (committed to the repo),
with a sibling `versions.json` manifest and `latest/` redirect stubs. The header
version picker reads `versions.json` client-side. There is no `gh-pages` branch
and no `mike` dependency - only mike's manifest data model is vendored, under
[`apps/docs/_vendor/`](apps/docs/_vendor/).

- **Build one version** (what CI runs on a release tag):
  `build_docs --docs-version 0.151.0 --alias latest`. On a push to `master` it
  builds `dev` instead. The snapshot, manifest, and `latest/` redirects all land
  under `versions/`.
- **Bootstrap / rebuild many** (one-off): `docs_build_all` walks the tags
  selected by [`docs_versions.toml`](docs_versions.toml), checks each out in a
  worktree, and builds it. Tags that predate the docs builder are skipped -
  rebuilding historical versions is a deferred decision.
- **Validate** the committed tree with `docs_versions_check` (manifest <->
  filesystem parity, alias redirects, cross-version links). It also runs in CI.
- **Preview locally** with `docs_preview`: it fakes a few versions from the
  current content and serves them, so you can click through the picker without
  needing real historical builds.

The deploy artifact is `site/` (gitignored), assembled at build time from the
current build plus the committed `versions/*` snapshots, mounted at `/v/<version>/`.

## Where to find things

```
docs_site/
    README.md                  <- you are here
    manage.py                  <- Django entrypoint
    docs_versions.toml         <- which git tags docs_build_all rebuilds
    design/                    <- design docs + feature inventory
    content/                   <- markdown source pages
        _nav.yml               <- sidebar navigation tree
        index.md               <- placeholder home page
        docs/                  <- published pages (concepts, reference, community, ...)
    versions/<version>/        <- committed built version snapshots + versions.json
                                  (created when bootstrapped; not present yet)
    static/
        css/tokens.css         <- OKLCH design tokens (light + dark themes)
        css/site.css           <- prose typography, layout chrome, components
        css/pygments-*.css     <- syntax highlighting (light + dark)
        fonts/InterVariable.woff2  <- self-hosted Inter variable font
        js/site.js             <- theme toggle, sidebar, TOC scroll-spy, version
                                  picker, tab switching, code copy, resize handles
        js/search.js           <- Pagefind-backed search modal
    docs_site/                 <- Django project package
        settings.py            <- settings (REPO_ROOT, SITE_URL, CONTENT_DIR,
                                  EXAMPLES_DIR, VERSIONS_DIR, VERSIONS_CONFIG, SITE_DIR)
        urls.py / wsgi.py
    apps/docs/                 <- the docs app
        examples.py            <- example autodiscovery + registry
        discovery/             <- API-reference discovery (griffe-driven)
        urls.py / views.py     <- live page serving for the dev server
        build/                 <- pipeline, fence protection, front-matter, links,
                                  nav loader, versioning, bootstrap, guards/
        components/            <- django-components (DocPage, ExampleCard,
                                  version_picker, search_modal, reference, ...)
        management/commands/   <- docs_serve, docs_serve_built, build_docs,
                                  build_one, docs_test, docs_build_check,
                                  docs_build_all, docs_versions_check, docs_preview
        templatetags/          <- docs_extras.py ({% example %}, {% version %},
                                  {% docstring %}, {% include_file %}, {% image %})
        _vendor/               <- vendored mike Versions model (BSD-3)
```

## Status

In-progress migration; see
[`design/DESIGN_features.md`](design/DESIGN_features.md) for the full inventory.
Done: Phases 0-2 (foundation, examples), 3a-3b (theme, chrome, content port,
guardrails), 4 (API reference), 5a (search), 5b (versioning). Next: 5c
(SEO + social cards), then Phase 6 cutover.
