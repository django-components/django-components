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

| Command | What it does |
|---|---|
| `python manage.py docs_serve` | Start the dev server; renders pages live from `content/` |
| `python manage.py build_docs` | Build every `.md` to `<output>/<slug>/index.html` (+ `.md` companions). Defaults to `./site/` |
| `python manage.py docs_test` | Validate internal links and anchors in the build (defaults to `./site/`; `--strict` fails on warnings too) |
| `python manage.py build_one <file> -o <out>` | Render a single page to one HTML file (handy when debugging the pipeline) |

Common options for `build_docs`:

- `--content <dir>` - content directory (default: `content/`)
- `--docs-version <ver>` - version string (default: from `pyproject.toml`)
- `-o, --output <dir>` - output directory (default: `./site/`)
- `--no-companions` - skip `.md` companion file generation

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

## Live examples (`{% example %}`)

The `{% example "name" %}` template tag embeds a tabbed widget in a docs
page showing an example's source code and a live rendered demo (see `DESIGN.md` section 4.2).

Usage in a markdown file:

```markdown
## Fragments example

{% example "fragments" %}
```

This renders three tabs:

- **Component** - syntax-highlighted source from `component.py`
- **Page** - syntax-highlighted source from `page.py`
- **Live demo** - the actual rendered component in an `<iframe srcdoc>`

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
   `fragments` list.
5. Reference it in a markdown page with `{% example "<name>" %}`.
6. Run `python manage.py build_docs` and verify.

## Where to find things

```
docs_site/
    README.md                  <- you are here
    manage.py                  <- Django entrypoint
    design/                    <- design docs + feature inventory
    content/                   <- markdown source pages
        index.md               <- placeholder home page
        test/pipeline_test.md  <- fixture exercising every pipeline feature
        test/example_test.md   <- fixture exercising {% example %} tag
    static/css/                <- Pygments light/dark theme stylesheets
    docs_site/                 <- Django project package
        settings.py            <- settings (REPO_ROOT, SITE_URL, CONTENT_DIR, EXAMPLES_DIR)
        urls.py
        wsgi.py
    apps/docs/                 <- the docs app
        examples.py            <- example autodiscovery + registry
        urls.py / views.py     <- live page serving for the dev server
        build/                 <- pipeline, fence protection, front-matter, links, example pre-rendering
        components/            <- django-components (DocPage, ExampleCard)
        management/commands/   <- build_docs, build_one, docs_test, docs_serve
        templatetags/          <- docs_extras.py ({% example %}, {% version %}, {% include_file %}, {% image %})
```

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

## Status

This is an in-progress migration. See
[`design/DESIGN_features.md`](design/DESIGN_features.md) for the full feature
inventory and current progress. Phases 0-1 (pre-work + foundation) are
complete; Phase 2 (live examples via `{% example %}`) is done for the core
features (guardrails deferred).
