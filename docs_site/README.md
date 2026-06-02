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
   `{% include_file %}`, and other tags
3. **python-markdown + pymdownx** - converts the expanded markdown to HTML
   (syntax highlighting, admonitions, tabs, TOC, etc.)
4. **DocPage layout** - wraps the content in a full HTML page with `<head>`
   metadata ([`components/doc_page/`](apps/docs/components/doc_page/))

## Where to find things

```
docs_site/
├── README.md                  <- you are here
├── manage.py                  <- Django entrypoint
├── design/                    <- design docs + feature inventory
├── content/                   <- markdown source pages
│   ├── index.md               <- placeholder home page
│   └── test/pipeline_test.md  <- fixture exercising every pipeline feature
├── static/css/                <- Pygments light/dark theme stylesheets
├── docs_site/                 <- Django project package
│   ├── settings.py            <- settings + shared constants (REPO_ROOT, SITE_URL, CONTENT_DIR)
│   ├── urls.py
│   └── wsgi.py
└── apps/docs/                 <- the docs app
    ├── urls.py / views.py     <- live page serving for the dev server
    ├── build/                 <- pipeline, fence protection, front-matter, URL<->path mapping
    ├── components/            <- django-components (DocPage, ...)
    ├── management/commands/   <- build_docs, build_one, docs_test, docs_serve
    └── templatetags/          <- docs_extras.py ({% version %}, {% include_file %}, {% image %})
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
inventory and current progress. Phase 1 (foundation: render one page
end-to-end) is nearly complete.
