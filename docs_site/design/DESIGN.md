# Design doc: replace mkdocs with a django-components docs site

**Status:** draft / proposal
**Author:** Juro Oravec (with Claude)
**Date:** 2026-05
**Related:** [#1515](https://github.com/django-components/django-components/issues/1515), [#1557](https://github.com/django-components/django-components/issues/1557) (Zensical attempt), [#1355](https://github.com/django-components/django-components/issues/1355) (URL redirects)
**Replaces:** none yet

This document explores what it would take to migrate the published docs site
([django-components.github.io/django-components](https://django-components.github.io/django-components/))
off mkdocs/mkdocstrings/Material and onto a docs site **built with
django-components itself**, so live component examples can be embedded inline
in documentation pages.

> **Implementing? Start with [DESIGN_djc_docs_site_features.md](DESIGN_djc_docs_site_features.md).**
>
> The features file is the **catalogue of every buildable feature** across this doc and all spikes (11.5, 11.7, 11.8, 11.9, 11.10, 11.11, 11.12), with phase assignment, effort, criticality, and source spec. It's the **survival layer** — if a feature isn't in it, it'll get lost when agent context fills. This doc carries the architecture and rationale; the features file carries the work list.

---

## 1. Why we're considering this

Recap of [#1515](https://github.com/django-components/django-components/issues/1515) plus what's happened since:

- Dependabot churn on mkdocs sub-packages is constant. Recent example: [8e711f2c](https://github.com/django-components/django-components/commit/8e711f2c) pinned `Pygments<2.20` because the Material theme's syntax-highlight CSS broke under newer Pygments. The fragility is real, even if each individual fix is small.
- **The Pygments pin is now actively blocking a security upgrade.** A security advisory recommends upgrading Pygments, but mkdocs/Material can't render correctly with the newer version. This forces a choice we shouldn't have to make: stay vulnerable, or break the docs build. The migration removes the conflict entirely because our own renderer doesn't constrain the Pygments version.
- Material-for-mkdocs has been "superseded" by Zensical. [#1557](https://github.com/django-components/django-components/issues/1557) attempted that migration and failed: our existing nav-real-estate template overrides ([docs/overrides/partials/](docs/overrides/partials/)) error out in Zensical.
- Bigger picture: our docs show **code that the reader can't actually run**. Every example under [docs/examples/](docs/examples/) ships a working component (`component.py`, `page.py`, tests, sometimes a GIF), but the visitor sees only a code block and an animated GIF if they're lucky. To actually try the example, they have to clone the repo and run `sampleproject`. We want live components embedded directly in docs.
- A docs site **built with django-components** also doubles as a real-world demo. It replaces the awkward sampleproject vs. docs split: the docs site **is** the showcase.

What we want to keep:
- Docstrings as the source of truth for the API reference.
- Markdown-authored pages (easy to edit, easy to version).
- Search (the single most-used feature according to the [#1515 thread](https://github.com/django-components/django-components/issues/1515)).
- Versioning (`/v0.150/`, `/latest/`).
- Free hosting on GitHub Pages.

---

## 2. What we have today

### 2.1 Build pipeline

The published site is built by `uv run mkdocs build --strict`. Key pieces, all configured in [mkdocs.yml](mkdocs.yml):

| Plugin | What it does | We'd lose / replace with |
|---|---|---|
| `mkdocstrings` + `griffe` | Render Python API docstrings | **Keep griffe**; replace mkdocstrings with our own rendering |
| `mkdocs-gen-files` | Calls [docs/scripts/reference.py](docs/scripts/reference.py) at build time to emit `reference/*.md` | Replace with our own build step |
| `mkdocs-material` | Theme, search, social cards, palette | Replace; biggest UX surface to recreate |
| `pymdownx.snippets` | `--8<-- "path/to/file.py"` inline include | Easy to reimplement as a build-time pass |
| `pymdownx.superfences`, `inlinehilite`, etc. | Code-block features | Replace with `markdown-it-py` or `markdown` + Pygments |
| `pymdownx.tabbed`, `details`, `tasklist` | Markdown extensions | Same |
| `mkdocs-macros` | Jinja2 in `community/people.md` | Native Django templates do this trivially |
| `mkdocs-include-markdown` | `{!file.md!}` includes | Trivial |
| `mike` | Versioned deployment via `gh-pages` branch | Replace with directory-based versioning |
| `redirects` | URL redirect map | Static `<meta http-equiv=refresh>` files |
| `git-revision-date-localized`, `git-authors` | Per-page metadata | Easy to reimplement with `subprocess` + `git log` |
| `social` | OG-image generation | Use Playwright or `Pillow` |
| `minify` | HTML/CSS/JS minification | Use `htmlmin` / `csso` |
| `search` | Lunr-style client search | Replace with [Pagefind](https://pagefind.app/) (or DIY Lunr) |
| `autorefs`, `awesome-nav` | Cross-page link resolution + nav YAML | Reimplement; small scope |

### 2.2 Our custom code

- [docs/scripts/reference.py](docs/scripts/reference.py) — walks `django_components.*`, filters by category (components, exceptions, settings, etc.), and emits `::: dotted.name` lines for mkdocstrings to consume. **Note (per Juro's feedback):** this script today is hard-wired to the mkdocstrings string syntax. In the new design, this work splits in two:
    1. **Discovery** — walk the public API, categorize symbols, produce a portable Python dict / JSON describing what should appear on each reference page (`{kind, dotted_path, members, options}`).
    2. **Rendering** — consumer-specific: today an mkdocstrings adapter would print `::: ...`; in the new world, a Django-template adapter renders an `ApiReference` component per kind.
    The handover contract between (1) and (2) is the data structure, not strings. (1) is reusable across renderers.
- [docs/scripts/extensions.py](docs/scripts/extensions.py) — two `griffe.Extension` subclasses: one rewrites class bases from runtime objects, one appends a "See source code" GitHub link to every docstring.
- [docs/scripts/people.py](docs/scripts/people.py), [docs/scripts/gen_release_notes.py](docs/scripts/gen_release_notes.py) — small generators.
- [docs/overrides/partials/](docs/overrides/partials/) — two Material-theme template overrides (`tabs.html`, `nav-item.html`) for nav layout. These are what blocked the Zensical migration.

**Important:** the griffe layer is genuinely portable. Our extensions don't talk to mkdocs at all; they decorate griffe `Object` nodes. We can reuse them verbatim with a different renderer.

### 2.3 What's in `docs/`

A quick audit of how dynamic the content is today. **Important:** the "First-pass intent" column is a coarse default — every case below needs an example-by-example pass during the migration, not a blanket rule.

| Surface | Count | Today | First-pass intent (not blanket) |
|---|---|---|---|
| `djc_py` / `djc_python` code blocks | ~75 | Static, syntax-highlighted via `pygments_djc` | **Mixed.** Many could become a tabbed `Code / Rendered output` widget when the code is self-contained and runnable. Stays static when it's a snippet, deliberately broken, or shows a code-only concept (e.g. import patterns) |
| `html` code blocks (component output) | ~94 | Static | **Mixed.** Often the rendered output of a preceding `djc_py` block — pair them in a tabbed widget. Otherwise stay static |
| `{% component %}` mentions | ~320 | Almost all inside code blocks | Stay static — these are syntax demonstrations |
| Live-demo GIFs | 3 | tabs, fragments, form_submission | **Replace with real interactive component** |
| Pages using `--8<--` includes | ~10 (all in `docs/examples/`) | Include the example's `.py` file as a code block | Stay as code, but pair with a live render via `{% example %}` |
| `mkdocs-macros` Jinja pages | 1 (`community/people.md`) | Build-time Jinja | Native Django template |
| `mkdocstrings` API ref pages | 14 in `docs/reference/` | Build-time-generated `.md` from Python | Build-time, but our renderer |

The migration is **not** "convert everything that looks like Python into a live runner." Many code blocks are explanatory snippets that aren't designed to render in isolation, and forcing them through a renderer would either fail or produce noise. The default stays static; "live" is an opt-in per code block (e.g. a fence info-string like ` ```djc_py runnable=1 ` or a custom block directive). We'll codify the rule for which code blocks become live during Phase 1.

### 2.4 The examples dir is already a Django app, almost

[docs/examples/](docs/examples/) is set up as **a sibling library to mkdocs** that the sampleproject pulls in at runtime. Every example dir has:

- `component.py` — the example components (already registered)
- `page.py` — a host `Component` with a `class View` and `get_template_data` that drives the demo
- `test_example_*.py` — pytest coverage proving the example renders
- `README.md` — the markdown doc that includes `component.py` and `page.py` via `--8<--` snippet directives
- sometimes `images/*.gif`

[sampleproject/examples/urls.py](sampleproject/examples/urls.py) iterates that directory, dynamically imports each `page.py` via `importlib.util.spec_from_file_location`, finds the first `Component` subclass whose name ends in `Page`, and registers it at `/examples/<example_name>/`. [sampleproject/examples/views.py](sampleproject/examples/views.py) renders an `ExamplesIndexPage` that lists them all.

So the loop "edit example → see live result" already works **in the sampleproject**, but doesn't surface anywhere on the docs site.

---

## 3. The core tension

> Docs are static (GitHub Pages); Django is server-side. How do we reconcile?

You named three options. Let me argue each one's actual feasibility against our current code.

### Option A — Shim Django away

> Render `Component` without a Django request/process, by treating component classes as pure data and using a non-Django template engine.

**Verdict: not viable until v2/v3.**

Reasons:

1. **The template engine is Django's.** `{% component %}`, `{% slot %}`, `{% fill %}`, `{% provide %}`, the tag formatter system, all live as `BaseNode` subclasses inside Django's `django.template.Engine` — see [src/django_components/templatetags/](src/django_components/templatetags/) and [src/django_components/node.py](src/django_components/node.py). To render them you need a live `Engine` instance and a `Context`. There's no second implementation we can hand a Jinja `Environment`.
2. **Component classes have hard imports of `django.*`.** `Component.render_to_response()` returns a `HttpResponse`; `class View` is treated like a Django CBV; `get_component_url` returns reverse-resolved Django URLs; `Media` integrates with Django's static-files system.
3. **Autodiscovery walks INSTALLED_APPS.** [src/django_components/util/loader.py](src/django_components/util/loader.py) and friends.

What would have to change first: a "core" tier of django-components that has no `django.*` imports, with Django glue layered on top. That's a multi-quarter refactor and a v2-or-v3 story. It is the right long-term shape, but it does not unblock the docs work *now*.

### Option B — Pre-render at build time (static-site generator)

> Run Django in CI, crawl every URL, write each response to disk, deploy the directory to GitHub Pages.

**Verdict: this is the path.** It's how [django-distill](https://django-distill.com/) and [django-bakery](https://django-bakery.readthedocs.io/) work, and they have a decade of production use behind them. Our problem space is friendlier than theirs because our "site" is a fixed set of docs URLs, not a CMS with unbounded user content.

The only real questions are:
- **How do we handle fragments / dynamic endpoints?** (see §4.4)
- **Search index** — built once at build time, served as a flat JSON file, queried by Pagefind/Lunr in the browser.
- **Dev-mode parity** — `runserver` for editing, `python manage.py build_docs` to produce the static dir.

### Option C — Run a live Django server in production

> Host the docs on Fly.io / Render / a small VPS.

**Verdict: not worth it for v1.** Loses GitHub Pages' free CDN, adds an oncall surface we don't need, and we'd then have to discuss how to host versioned docs. Keep it on the table as a fallback only if pre-rendering proves to require workarounds we can't stomach.

### Decision

**Option B.** Build a Django app called `docs_site` (or similar), let it use django-components for everything, and bake out static HTML.

---

## 4. Proposed architecture

### 4.0a Repository layout during the migration

Before any new content was written, the existing `docs/` directory was **renamed to `docs_old/`** (one commit, with every config/script/workflow reference repointed so the rename didn't break the build at the time). Keeping mkdocs buildable on the branch indefinitely is **not** a goal — the branch is free to cannibalize it as content is ported (see the §8 branch model). The rename does two things:

1. **Frees up `docs/` for internal docs.** `docs/` now holds **contributor-facing / internal** documentation that is *never* published: `docs/agent-knowledge/` (local, uncommitted) and — at cutover — `docs/devguides/` (implementation deep-dives that were only ever published as a side effect of having nowhere else to put them). A `docs/README.md` points readers to the user docs (at the published URL and in `docs_site/content/`), because a visitor clicking `docs/` reasonably expects user documentation.
2. **Makes the cutover a search.** Every place still wired to the old layout is found with `grep -rn docs_old .`. The big content move and config rewrite happen as one atomic Phase-6 commit, not piecemeal.

Target end-state layout (reached at cutover):

```
docs/                            <-- INTERNAL docs only (agent-knowledge, devguides, README pointer)
docs_old/                        <-- the old mkdocs source; emptied as pages are ported (Phase 3b), fully DELETED by cutover
docs_site/                       <-- the new docs builder (Django project)
    content/                     <-- user-facing markdown (moved from docs_old/ during the Phase 3b content port; see §8 branch model)
    examples/                    <-- runnable examples (moved from docs_old/examples/ during the migration)
    versions/<version>/          <-- committed built version snapshots -> mounted at /v/<version>/
    static/                      <-- css, images, and other static assets
benchmarks/                      <-- benchmark CODE (already here)
    report/                      <-- asv HTML output (relocated from docs_old/benchmarks/); copied
                                     into the build as a static passthrough
site/                            <-- build output (gitignored); the deploy artifact, contains /v/<version>/
```

**Build output and deploy.** The everyday `docs-build` writes to `site/` (gitignored, mirrors mkdocs' `site_dir`). At deploy, CI builds `docs_site` → `site/` (assembling the current version plus the committed `docs_site/versions/*` snapshots into `site/v/*`) and deploys `site/` via GitHub Actions. This supersedes the earlier "commit built HTML to `master/docs/v/` and serve from `/docs`" sketch in §4.6 — versions stay committed (under `docs_site/versions/`, preserving reproducibility/rollback), but the deploy artifact is `site/`, assembled at build time.

**Benchmarks** are a static passthrough: the asv report (currently committed under `docs_old/benchmarks/`) relocates to `benchmarks/report/`, and the builder copies it verbatim into the built site under its mount path (skipping the markdown pipeline — it's already HTML). The builder gains an explicit list of `(source_dir -> mount_path)` passthroughs rather than a magic "serve index.html if present" rule.

### 4.1 Top-level shape

```
docs_site/                       <-- new Django project, replaces sampleproject/
    docs_site/                   <-- settings, urls, asgi
    apps/
        docs/                    <-- handles markdown pages + nav + search
            components/
                page_layout/     <-- the doc-page chrome
                doc_page/        <-- one component per page; renders Markdown
                example_card/    <-- shows code + live render side-by-side
                api_reference/   <-- griffe-driven API page
                search_bar/      <-- client-side search component
                version_picker/
            management/
                commands/
                    build_docs.py
            templatetags/
                docs_extras.py   <-- {% example %}, {% docstring %}, etc.
    content/                     <-- markdown files (this is just today's docs/ minus the build cruft)
        getting_started/
        concepts/
        ...
    examples/                    <-- moved from docs/examples/, now first-class
        fragments/
            component.py
            page.py
            test_example_fragments.py
        ...
    static/
    requirements.txt
```

The markdown files **remain authoring-facing markdown**. The `doc_page` component reads a markdown file at render time and converts it to HTML. Markdown directives like ` ```djc_py ` and `--8<--` are handled by extensions in our own pipeline (the same `pygments_djc` lexer we already use). Custom directives (e.g. `{% example "fragments" %}`) are handled by our own preprocessor before the markdown converter sees them, or as Django template tags after.

### 4.2 The `{% example %}` tag — the killer feature

```django
{% example "fragments" %}
```

Renders to:

```
+------------------------------------------------------------+
| Tab: Component   |   Tab: Page   |   Tab: Live demo        |
+------------------------------------------------------------+
| (selected tab content)                                     |
|                                                            |
+------------------------------------------------------------+
```

- "Component" and "Page" tabs are syntax-highlighted Python from `examples/fragments/component.py` and `page.py`.
- "Live demo" tab inlines the rendered output of the example's `Page` component. This is **the same code we run in tests today**.
- The tab is implemented as one of our own components (`Tabs`) — the docs site dogfoods django-components.

This is the centerpiece of the migration. It only works because we have Django at build time.

### 4.3 API reference

Keep [docs/scripts/extensions.py](docs/scripts/extensions.py) (the griffe extensions). Write a small `griffe → component-input` adapter that produces the same structure our `ApiReference` component expects:

```python
{
    "name": "Component",
    "kind": "class",
    "signature": "...",
    "docstring_html": "...",  # rendered from Google-style
    "bases": [...],
    "members": [...],
    "source_url": "https://github.com/.../component.py#L42",
}
```

This is roughly what mkdocstrings does internally; we just stop at "render to our own component" instead of "render to a Material template."

**Per-kind renderers.** Different API kinds need different layouts (a Django management command page looks nothing like a class page). Each `kind` value (`class`, `function`, `setting`, `cli_command`, `template_tag`, `exception`, etc.) maps to a dedicated Django template or component that takes the dict above as input. Adding a new API kind = new component + new entry in the kind→component map; the discovery layer doesn't change. **Spike needed** to enumerate every kind we currently emit and design the per-kind component set (see §11.5).

### 4.4 Fragments (the trickiest part)

Fragment examples need a server endpoint that returns HTML when clicked. In production-as-static, there's no server. We have three sub-options:

#### 4.4a Pre-render every fragment response to a static file

For each example's `View.get()`, enumerate the inputs that the example actually uses (e.g. alpine / htmx / js variants), call it at build time, and write the result to a static path. Rewrite the in-page `hx-get="..."` URL to point at the static file at build time.

**URL convention: path-keyed, not query-string-keyed.** The fragment variants live at `/examples/fragments/alpine/`, `/examples/fragments/htmx/`, `/examples/fragments/js/` — **not** `/examples/fragments?type=alpine`. Rationale:

- Clean static URLs (a directory per variant, with `index.html` inside).
- Compatible with `django-distill` out of the box, which explicitly rejects query strings (see §11.3 spike findings).
- Cacheable as plain static files without server-side normalization.

This works because **the example author already knows the finite set of inputs** — that's what makes it a doc-able example. We add a tiny convention:

```python
class FragmentsPage(Component):
    class DocsExample:
        # Each entry becomes a sub-URL of the example's page.
        # The view receives the variant as a path parameter.
        fragments = ["alpine", "htmx", "js"]
```

The `build_docs` command walks every example's `DocsExample.fragments`, materializes each variant as a sub-URL of the example's page (`/examples/<name>/<variant>/`), calls the view via Django's test client, and writes the body to `static/fragments/<example>/<variant>/index.html`. A URL rewriter substitutes `get_component_url(...)` calls in the rendered page with the static path at build time.

This covers every fragment example currently in [docs/examples/](docs/examples/) (fragments, form_submission, tabs).

#### 4.4b Embed fragments inline as JS strings

Less clean: each example carries a `<script type="application/json" id="fragments">{...}</script>` map of `{key: html}` and the page's JS reads from there instead of `fetch()`. Faithfully demos client-side templating, but no longer demos the real HTTP round-trip. Reject for v1.

#### 4.4c Pretend fragments are interactive via a Cloudflare worker

Overkill. Reject for v1.

**Decision: 4.4a.**

### 4.5 Search

Use [Pagefind](https://pagefind.app/) — confirmed via the §11.1 spike (2026-05-31). It scans the built static site, builds a chunked content index, and exposes a small JS API. No server. Our current Material/Lunr `search_index.json` is **1.3 MB for ~1,373 heading-level entries**; Pagefind ships a total network payload around **100 kB** for sites our size, lazy-loaded as the user types.

Setup is one CI step (`pagefind --site site/`) after the static build. We wrap Pagefind's JS API in a `SearchBar` Django component (custom UI, not the prebuilt one) so the search affordance is dogfooded like everything else. Per-tag ranking is driven by HTML semantics out of the box (`h1`=7, `h2`=6, …); we can override per-element via `data-pagefind-weight` if a section needs boosting.

Trade-off accepted: no fuzzy/typo tolerance (neither Material's current config nor Pagefind supports it). If user feedback later flags this, mitigations exist (synonym table, query expansion, Fuse.js fallback overlay) — all addressable post-Phase-5.

Alternative considered: write our own Lunr index from a build-time pass (~200 lines of Python). Rejected: pure cost, smaller bundle wouldn't follow, no anchor-level results.

Spike details and full comparison: see §11.1.

### 4.6 Versioning

Drop `mike`. Each release gets its own subdirectory (`/v0.150/`, `/v0.151/`, ...) and a small JSON manifest. A `version_picker` component reads the manifest client-side.

**Key design decision (per Juro): built versions live in `master` under `docs/v/<version>/` and are committed to git.** Do NOT rebuild every historical version on every CI run — that's O(N versions × build time) per release and gets prohibitively slow as N grows. Instead, build a version once, commit the artifact, and the next release only rebuilds itself plus refreshes `latest`.

This gives us:

- Fast CI (each release does one build, not N).
- Reproducibility from a single commit (the whole site is whatever `master` says it is — no separate `gh-pages` branch to drift).
- Trivial rollback (revert the docs commit; no orphaned tag-checkout state).
- Trivial diffing (a docs change shows up as a real diff in `master`, not as a bundle of HTML on a parallel branch).

Trade-off: repo size grows over time. Mitigation: build outputs are minified HTML and gzip well; we can prune very old versions (`v0.13x` and below, say) when they fall off the support window; if it ever becomes painful, switch to `git lfs` for the older `docs/v/*` paths.

#### Two commands, two flows

**1. `uv run docs-build`** — the everyday command.

- Reads the current working-tree state.
- Determines the version from `pyproject.toml` (or a CLI flag for previews).
- Builds the site into `docs/v/<version>/`.
- Updates `docs/v/versions.json` (the manifest the `version_picker` reads).
- Optionally refreshes `docs/v/latest/` (symlink or copy).
- That's it. Commits are a separate step.

This is what runs in CI on every release: tag is cut → `docs-build` → commit `docs/v/<version>/` and the updated manifest → push.

**2. `uv run docs-build-all`** — the one-off bootstrap / disaster-recovery command.

- Walks `git tag` matching a configurable regex (default `^v?\d+\.\d+(\.\d+)?$`).
- For each tag in scope (include/exclude lists, `oldest`/`newest` bounds in `docs_versions.toml`), checks the tag out in a worktree, runs `docs-build` against it, and writes to `docs/v/<version>/` on the current branch.
- Rewrites `docs/v/versions.json` from scratch.

You only run this when:
- bootstrapping the new system (first migration),
- something in the build pipeline changed and we want every version reflowed (rare; usually we only reflow the current version),
- recovering from a corrupted `docs/v/`.

Day-to-day, this command does not run. Only command (1) does.

#### Anchoring on a single commit

A nice consequence: GitHub Pages can deploy `master`'s `docs/v/` directly (no separate `gh-pages` branch, no `mike` machinery). The deploy is "copy `docs/v/` to the site root." This also removes the historical mkdocs/`mike` pattern of force-pushing the built HTML to `gh-pages`, which we've had problems with.

#### Older-versions migration question

Whether `docs-build-all` should rebuild the *historical* versions (v0.135 and below) with the new builder is the open question already captured in §11.8. That spike picks the answer; once chosen, the bootstrap run produces the right set of `docs/v/*` directories and we commit the result.

#### Spike on mike internals

See §11.7 — even though we're persisting to `master`, there are still pieces of `mike`'s logic (manifest schema, version-picker JS, alias resolution) that might be worth reusing.

### 4.7 Markdown processing pipeline

> **Spike done. See §11.4 for the full investigation, including library choice, directive-vs-tag debate, the `--8<--` audit, and a concrete prototype.**

**Question Juro asked:** is the order "markdown → HTML, then Django templates"? What's the best practice?

**Answer.** The widely-used pattern across Hugo, Eleventy, Jekyll, and 11ty is **shortcodes-first, markdown-second, layout-last**. Our shape (revised after the spike): **fence-protection pre-pass → Django template engine → python-markdown → DocPage layout**.

```
content/foo.md
    -> [Pre-pass] Fence-protection scanner (~80 LOC)
        - Walk the source line-by-line
        - Wrap every code region (``` fences, ~~~ fences, 4-space indented, `inline code`) in
          {% verbatim %}...{% endverbatim %}
        - This is Django's official "treat as literal" escape mechanism
    -> [Pass 1] Django template engine (FULL engine, not a narrow expander)
        - {% load docs_extras component_tags %} is auto-injected
        - Any Django tag works in markdown:
            {% component "table" rows=... %}                              <-- djc
            {% example "fragments" %}                                     <-- docs sugar
            {% docstring "django_components.Component" %}                 <-- docs sugar
            {% include_file "path" %}                                     <-- docs sugar
            {% version %}                                          <-- docs sugar
            {% if %}, {% for %}, {% with %}                               <-- core Django
        - Output: markdown body where every tag has expanded to markdown text
          or block-level HTML (separated by blank lines)
        - Inside {% verbatim %} blocks, every {% %} pattern is emitted literally
    -> [Pass 2] python-markdown -> HTML
        - Extensions match today's mkdocs config (pymdownx.highlight, pymdownx.superfences,
          pymdownx.snippets, pymdownx.magiclink, admonition, md_in_html, toc, ...)
        - md_in_html ensures block-level HTML from Pass 1 passes through untouched
        - toc.permalink="¤" with python-markdown's DEFAULT slugify preserves today's anchors
          (NOT pymdownx.slugs.slugify - it produces double hyphens for " / " headings; found in 3b.25)
        - Pygments highlights all fences (incl. djc_py via the pygments_djc lexer we own)
    -> [Pass 3] DocPage layout wrap
        - Render DocPage component with (content_html, title, toc, breadcrumbs, edit_url, version)
        - Only place page chrome (nav, sidebar, footer, dark mode, search bar) is added
    -> sanitize + minify
    -> write to docs/v/<version>/<path>.html
```

Why this order:

- **Pre-pass first** because Django's template engine would otherwise tokenize `{% example %}` *inside* a code fence and execute it. Wrapping every code region in `{% verbatim %}` is Django's official "treat as literal" escape mechanism and removes the problem cleanly.
- **Django (Pass 1) before markdown (Pass 2)** because `{% example %}` emits the HTML for a tabbed widget that contains rendered components — python-markdown must see that HTML as block-level HTML and leave it alone (not parse it as if `<div>` openings were lists, etc.). Pass 1's output is markdown-compatible: top-level `<div>...</div>` blocks separated by blank lines, which `md_in_html` passes through untouched.
- **Pass 3 (layout) cannot run before Pass 2** because the layout needs the rendered TOC and heading IDs.

**Where's the line between "directive" and "Django template tag"?** There is no line. Every tag in markdown is a Django template tag. "Docs sugar" tags (`{% example %}`, `{% docstring %}`, `{% include_file %}`, `{% version %}`, `{% image %}`) are convenience `simple_tag` definitions in `docs_extras.py`. djc tags like `{% component %}` work because Django loads the `django_components` template library like any other Django app. This was the key insight from the spike, in response to Juro's feedback.

**How does a docs tag wire up to a Django component?** Via `simple_tag` implementations that call `Component.render(...)` in Python and return the resulting HTML string. See §11.4.E for the concrete pattern. djc v1/v2 components are not invoked via JSX-style `<ApiReference>` HTML tags — they're invoked via `{% component %}` in templates or `.render()` in Python, and that's the mechanism used here.

Each piece is small and replaceable. None of the pieces is novel.

### 4.8 Dev workflow

The repo is on `uv`, so wire the docs commands as `uv` scripts in `pyproject.toml` rather than a Makefile. This keeps everything in one place and works on Windows / non-make environments out of the box.

```toml
# pyproject.toml
[project.scripts]
docs-serve = "docs_site.cli:serve"
docs-build = "docs_site.cli:build"
docs-test  = "docs_site.cli:test_links"
```

```
uv run docs-serve     # runserver, full Django; edit a .md and hit reload
uv run docs-build     # build_docs management command, output to site/
uv run docs-test      # pytest tests that the build produces no warnings, all links resolve
```

Open to discussion. A thin `Makefile`/`justfile` wrapper that just calls the `uv run` commands is fine if any contributor prefers it; the wrapper adds no logic of its own. The `[project.scripts]` entrypoints are the source of truth.

`runserver` mode and `build_docs` mode share 95% of code. The build step is "for each known URL, GET it and write the response."

---

## 5. What we lose, what we gain

| What we gain | What we lose |
|---|---|
| Live component examples embedded in docs | Material's polish (we have to recreate equivalent CSS) |
| Unblocks the Pygments security upgrade (no more renderer-pinned version) | "Set it up once" Material theme search/social/palette |
| Dogfooding django-components on a real site | Some out-of-the-box plugin features (we replace each piece) |
| Independence from mkdocs dep churn | A few weeks of focused engineering |
| Single source of truth: docs and sampleproject merge | Possibility of bugs in our renderer that mkdocs handled |
| Better story for "show me what this library does" | `mike`'s gh-pages branch convention (we use directories instead) |
| Versioning control we own | |
| Edit-on-GitHub buttons keep working (it's just URLs) | |
| Strict link validation transfers (we own the check) | |
| Anchor scheme is ours — we can drop the `django_components.` prefix from hash links | |

The biggest single risk is **search quality**. Material's search is genuinely well-tuned. Pagefind is the closest off-the-shelf alternative and is good but not as good. If that turns out to be a deal-breaker post-Phase-5, we can fall back to Lunr + a curated stopwords/boost config — still no server needed.

---

## 6. First concrete step

If we want to test the riskiest assumption before committing to the plan, the cheapest experiment is:

**Build a single-page proof of concept.** A management command that:
1. Reads `docs/examples/fragments/README.md`.
2. Renders it through markdown-it-py.
3. Inlines a live render of `FragmentsPage` next to the code blocks.
4. Writes the result to `site/fragments.html`.
5. We open the file in a browser and verify the buttons work, fragments load (from pre-rendered static files), and JS/CSS dependency handling is correct.

If that file works end-to-end in ~2-3 days of effort, the rest is execution. If it doesn't — most likely because the fragment-pre-rendering trick has a subtle issue — we'll catch the deal-breaker before sinking 6 weeks into it.

Recommended next move: **spike the proof of concept**, then come back to this doc to fill in §4.4 with whatever we learned and to lock in the migration plan.

---

## 7. Out of scope for this doc

- Internationalization. mkdocs doesn't support it cleanly today either; defer.
- Comments / discussion threads embedded in docs.
- Auto-generated tutorials. We'd rather hand-author and keep them honest.
- The v2/v3 "drop Django dependency" refactor — orthogonal, and the docs site doesn't need it.

---

## 8. Migration plan (incremental, not big-bang)

We don't replace mkdocs in one PR. We run both side-by-side until the new site reaches parity, then cut over.

> **The catalogue of every buildable feature lives in [DESIGN_djc_docs_site_features.md](DESIGN_djc_docs_site_features.md).** This section carries the **narrative**: what each phase is for, why this order, what's deliberately out of scope. The features file carries the **inventory**: every feature, with phase assignment, effort, criticality, and source spec.
>
> Rule of thumb: when implementing a phase, **read the corresponding section in the features file first** — that's your work list. Then come back here for the framing. Anything that's not in the features file is not in this plan; if something is missing, **add it to the features file** so the next agent picks it up.

### Phase shape

Each phase is **sharply focused**: one mental model, one deliverable. Resist the temptation to bundle "while we're in there" work — the old §8 read like a brief but actually committed each phase to building 20-30 features in parallel. The new shape is finer-grained so the agent doing the work can hold the whole phase in head at once.

### Phase 0 — Pre-work in `src/`

**Goal:** clean source-of-truth before the migration starts. Codemods inside the existing codebase, NOT new features.

**Sharp focus:** sweep `src/django_components/` and `docs/` for the legacy patterns that would block griffe later. Stop when the sweeps land — do not start `docs_site/` yet.

**Key features:** [hand-typed link codemod](DESIGN_djc_docs_site_features.md#phase-0--pre-work-in-srcdjango_components-before-any-docs_site-code), [Google-section codemod](DESIGN_djc_docs_site_features.md#phase-0--pre-work-in-srcdjango_components-before-any-docs_site-code), docstring-convention documentation.

**Estimate:** ~3-4 days.

### Phase 1 — Foundation: render ONE page end-to-end

**Goal:** a single page (e.g. `getting_started/index.md`) renders through the 3-pass pipeline to a static file in `docs/v/<version>/`, with full `<head>` metadata. No nav chrome yet, no API reference, no examples.

**Sharp focus:** the pipeline itself (fence-protect → Django → markdown → DocPage), the file layout, and the metadata story. Resist building chrome.

**Why this scope:** the riskiest piece of the whole migration is "does our 3-pass pipeline produce sensible HTML?" If the answer is no, every later phase shifts. Get to "one good page in a browser" first.

**Out of scope:** API reference (Phase 4), examples (Phase 2), sidebar/header chrome (Phase 3a), search (Phase 5a), versioning manifest (Phase 5b), SEO polish (Phase 5c).

**Estimate:** ~2 weeks.

### Phase 2 — `{% example %}` end-to-end (the killer feature)

**Goal:** one example (suggested: `fragments`) renders interactively in a docs page, with code + page + live-render tabs, with pre-rendered fragments fetched correctly.

**Sharp focus:** prove the live-component + fragment-pre-render trick. Resist building all examples (those are content port, Phase 3b).

**Why this scope:** the second-biggest risk after the pipeline. If `{% example %}` doesn't work or feels bad, the whole "docs site built with django-components" premise weakens.

**Out of scope:** the other examples; chrome; any non-example tag.

**Estimate:** ~1 week.

### Phase 3a — Theme + core chrome

**Goal:** a markdown page renders with header + sidebar + right-rail TOC + code blocks + dark mode, on desktop.

**Sharp focus:** the visual system. Tokens, layout, typography, code blocks, admonitions. No content port yet, no API reference, no mobile.

**Why this scope:** every later phase consumes these primitives. Land them before tons of content moves through. Mobile is split off because it's a separate mental model.

**Out of scope:** mobile breakpoints (3b), content port (3b), Pagefind UI (5a).

**Estimate:** ~1 week.

### Phase 3b — Mass content port + responsive + content-layer guardrails

**Goal:** every existing markdown page renders correctly under the new pipeline + chrome, desktop + mobile. All content-layer guardrails wired into CI.

**Sharp focus:** content fidelity, mobile breakpoints, and the guardrails that protect day-to-day content edits (link check, anchor check, fence validator, snapshot tests).

**Out of scope:** API reference (Phase 4), Pagefind (5a), versioning (5b), SEO polish (5c).

**Estimate:** ~1-2 weeks.

### Phase 4 — API reference (the big one)

**Goal:** feature parity with mkdocstrings on the 14 current reference pages, with the discovery → rendering split, dual anchors, full cross-ref resolution.

**Sharp focus:** mkdocstrings replacement. Resist anything that isn't on the reference path.

**Why this scope:** the largest single piece of new code in the migration (~66 features per inventory). Two sub-deliverables internally: (a) proof-of-concept on `exceptions.md` first to validate the contract, then (b) escalate to one massive `Component` class entry to exercise all sub-components. Only after both proofs land do we generalize to all 14 pages.

**Out of scope:** search, versioning, anything not on the API reference path.

**Estimate:** ~3-4 weeks.

### Phase 5a — Search

**Goal:** Pagefind-powered search with custom UI feels at least as good as Material's search.

**Sharp focus:** search only. Resist versioning, SEO, social cards.

**Why this sub-phase:** depends on theming (Phase 3a) for modal aesthetics. Doesn't depend on versioning — per-version search is just one Pagefind bundle per version dir.

**Estimate:** ~5-7 days.

### Phase 5b — Versioning

**Goal:** `docs-build` + `docs-build-all` + `version_picker` + `versions.json` flow works end-to-end, with `docs/v/<version>/` committed to `master`.

**Sharp focus:** versioning only. The full `docs-build` replaces the Phase-1 MVP build command.

**Estimate:** ~1 week.

### Phase 5c — SEO + AIO + chrome polish

**Goal:** every SEO/AIO feature wired. Site is Lighthouse-clean and AI-bot-friendly. Social cards generated. HTML minified.

**Sharp focus:** discoverability + polish only. Cutover Audit (Phase 5d) is a separate phase because audit is a different mental mode than building.

**Estimate:** ~1 week.

### Phase 5d — Feature-parity audit + selective port

**Goal:** before cutover, hold a deliberate gate. Sit with three columns side by side — (1) our current Material/mkdocs site, (2) Zensical's current feature list (see §11.2 "What we'd give up"), (3) what our new site actually does. For each row, decide one of: **port**, **skip**, **defer**.

**Sharp focus:** auditing, NOT redesigning. The reason this is a separate phase: it's the only realistic moment to catch silent regressions before users see them. Each prior phase optimized for getting the next thing working, not for completeness.

**Concrete steps:**

1. **Build the matrix.** Walk the [Zensical feature inventory](https://zensical.org/compatibility/features/) row by row. For each: "today (Material)", "today (new site)", "user-visible? load-bearing?". Drop trivial rows.
2. **Decide per row.** Port now / defer / skip. Default to *skip* — Phase 3-5c already covered the load-bearing polish.
3. **Implement the port-now set.** Each item should be ≤half a day; if not, re-scope as defer.
4. **Walk the live site cold.** Pretend to be a first-time reader. Compare: home → search a term → land on an API page → navigate to a related concept → toggle dark mode → switch versions. Note anything that feels worse. Fix or file.
5. **File deferred items as a tracked backlog.**

What this phase is NOT: a chance to rethink the design. We do not redesign in Phase 5d. We only port and polish.

**Estimate:** ~4-6 days (the audit itself is 1-2 days; the rest depends on the port-now set).

### Phase 6 — Cutover

**Goal:** merge the migration branch so the new `docs_site` build replaces the old mkdocs site. Inbound URLs preserved.

**Sharp focus:** cutover and only cutover. This is a *comparison + a single merge commit*, not a live deploy switch (see the branch-model invariant above).

**Mechanics:**

1. **Move the remaining content.** Move the user-facing pages still in `docs_old/` into `docs_site/content/` (preserving subtree structure so published URLs don't change), and move any remaining non-content assets (CSS, images, etc.) into their `docs_site/` homes. Move `docs_old/community/devguides/` into the internal `docs/devguides/` (these were never meant to be user-facing). Relocate the benchmark report out of `docs_old/benchmarks/` (see §4.0a).
2. **Find every straggler with one search.** Because the current source was renamed to `docs_old/` up front, `grep -rn docs_old .` lists every place still wired to the old layout — configs, workflows, scripts, docstring links, design docs. Update them all.
3. **Compare locally.** Build the new site and review it page-for-page against the deployed old mkdocs site (visual review + the §11.10 guardrails + link checks).
4. **Delete the old stack.** Remove `docs_old/`, `mkdocs.yml`, and the mkdocs/material/mike dependencies from `pyproject.toml`. Rewrite the docs CI workflow to build `docs_site` → `site/` and deploy `site/`.
5. **One commit, then merge.** Land all of the above as a single cutover commit and merge the branch. The next deploy serves the new site.

Old `gh-pages` is retained for rollback; historical versions are imported per §11.8.

**Estimate:** ~2-3 days.

### Phase 7 — Search v2 (post-cutover polish)

**Goal:** autocomplete, recent searches, filters/scoping, typo-recovery fallback (borrowing Emil's scoring algo per §11.1.C).

**Sharp focus:** search power-user features. Already-working users keep working.

**Estimate:** ~3-4 days.

### Phase 8 — Search v3 (blocked on analytics target)

**Goal:** search-result analytics.

**Blocked** on picking an analytics target (Plausible / GoatCounter / Cloudflare Worker / self-hosted endpoint). Separate design decision; park until we know where the data should go.

### Phase 9 — Landing page (codesign)

**Goal:** build the dedicated landing page at `/` (the marketing-style front door) that §11.11 §4.4 reserved a slot for.

**Explicitly framed as a back-and-forth codesign exercise** between Juro and the agent, not a one-shot spec.

Why a separate phase, post-cutover:
- Juro has a specific vision but it will take iteration to reach (component composition, hero copy, feature framing, code-example choice, visual hierarchy).
- The landing page sits outside `DocPage` chrome and doesn't gate any other phase.
- It can ship to production independently — Phase 6 cuts over with `/` either redirecting to `/docs/` or serving a thin scaffold; Phase 9 replaces that with the real landing.
- Doing it last means the rest of the design system (tokens, typography, `CodeTabs`, `ExampleCard`) is already locked in. The landing page reuses those primitives rather than inventing them.

**Estimate:** hard to predict. Budget ~1-2 weeks of calendar time across multiple short codesign sessions, not dedicated focus blocks.

### Phase 10+ — Deferred / post-launch maintenance

Tracked separately so it doesn't crowd the migration. Items: selective rebuild of newer historical versions, pre-0.124 URL redirect map (driven by analytics), version-pruning policy, CVE audit on frozen Material bundles, per-version freeze flag, sitemap-index, `dev/` deploy flow decision.

See [features file → Phase 7+](DESIGN_djc_docs_site_features.md#phase-7--deferred--post-launch) for the inventory.

### Note on the Phase-1 thin scaffold

Phase 1 ships a *thin* placeholder at `/` so the new top-nav `Docs / Examples / Plugins` structure works end-to-end from day one. The placeholder is ~50 LOC — hero text, three nav links, footer — using the design tokens but no original layout work. Phase 9 replaces this placeholder with the real landing page.

### Total estimate

Phases 0-6 (the actual migration): ~10-12 weeks of focused effort. Search v2/v3 and the landing page (Phases 7-9) add to that whenever we choose to do them. All can be split across many PRs and many calendar weeks.

### Invariant across all phases — the branch model

**The entire migration lives on a single feature branch (`jo-docs-mkdocs-migrate`) and is NOT merged to `master` until it is fully done.** This is the key to a low-drama cutover:

- **`master` keeps serving the old mkdocs site the whole time.** Because the migration branch is never deployed, **there are never two doc sites online at once.** The deployed site is always whatever `master` says — i.e. the old mkdocs site — until the single cutover merge.
- **The branch cannibalizes mkdocs; keeping it buildable locally is NOT a requirement.** We are free to *move and then delete* `docs_old/` content into `docs_site/content/` at any point on the branch — the content port happens during the migration (Phase 3b, feature 3b.25), it is **not** deferred to cutover to "keep mkdocs building." The earlier `docs/` → `docs_old/` rename (see §4.0a) exists to make stragglers greppable (`grep -rn docs_old .`), **not** to oblige us to keep the old build green. Once a page is ported, its `docs_old/` source can be deleted; `docs_old/` is fully gone by cutover.
- **The Phase 6 parity comparison is against the DEPLOYED old site, not a locally-rebuilt mkdocs.** The baseline is the live gh-pages / `master` mkdocs build (it stays online the whole time per the first bullet), so we can dismantle mkdocs on the branch without losing anything to compare against. We do **not** need both builders runnable side-by-side locally.
- **Cutover is a comparison + a single commit, not a deploy switch.** When the new site reaches parity (Phase 6), we review it against the deployed old site (visual + guardrails), then in one commit: delete whatever remains of `docs_old/` and the mkdocs config, wire the new builder into CI, and merge the branch. The next deploy serves the new site.

We do not break the published docs at any point because we never publish the half-built site.

---

## 9. Open questions to resolve before starting

1. **URL stability.** Two intersecting concerns:
    - **(a) Heading anchors.** Material generates anchors as `#some-heading`; we need to match its slug algorithm exactly to avoid breaking inbound links from third-party blog posts. Audit the slug function and replicate it.
    - **(b) `/docs/` path move (decided by §11.11).** Docs content (`/concepts/`, `/reference/`, `/guides/`, `/getting_started/`, `/overview/`, `/upgrading/`, `/community/`, `/releases/`) moves under `/docs/`. `/examples/` and `/plugins/` stay at root. A new landing page lives at `/`. Inbound links handled via the existing redirect machinery (§11.9.2.5) — every old URL gets a `<meta http-equiv="refresh">` redirect file at its old path, auto-generated from the move map in [spike §4.2](DESIGN_djc_docs_site_spike_11_11.md). Internal cross-refs are rewritten by the same codemod pass that handles the §11.5/§11.6.F anchor scheme change.
2. **Anchor changes from mkdocstrings — we want to DEVIATE.** Today every API symbol is anchored as `reference/api/#django_components.Component`. The dotted import path in the hash is ugly and verbose, and Juro has wanted to drop it for a long time. New scheme: `reference/api/#Component`. Trade-off: this breaks inbound links from blog posts and prior docs versions. Mitigation: in the rendered HTML, emit **both** the new canonical anchor (`<h2 id="Component">`) and a legacy alias for back-compat (`<a name="django_components.Component"></a>`) so old URLs still work. Confirm via spike (§11) whether the alias actually resolves in modern browsers (`<a name>` is deprecated but still honored).
3. **Edit-on-GitHub button URLs.** Each generated page maps back to a source. We control this; needs to be wired into our `doc_page` component.
4. **Themability / dark mode toggle.** Material gives us palette-switching out of the box. We can recreate with one CSS file and a small JS toggle.
5. **Versioned redirects.** When pages move (like [#1355](https://github.com/django-components/django-components/issues/1355)), our redirect map is HTML `<meta http-equiv=refresh>` files. Confirm GitHub Pages serves them with the right Cache-Control.
6. **Build time.** mkdocs build is ~30s today. Django startup + crawl + Pygments will likely be slower; budget ~1-2 minutes. Acceptable for CI.
7. **`pygments_djc` ownership.** Confirmed by Juro — we own it. It stays as a normal dep; no migration concerns here.
8. **mkdocs strict-mode link checking.** We currently run `mkdocs build --strict` in CI to fail on broken links. The new build needs an equivalent step that walks all generated HTML, parses `<a href>`, and asserts every internal link resolves. See "Guardrails" spike in §11.10.
9. **Migrating old docs versions.** Unresolved. Two sub-questions: (a) do we rebuild every historical version from its git tag with the *new* builder (which means historical content has to remain compatible with the new directives), or (b) do we keep the existing mkdocs-built HTML for older versions and only switch the builder for new releases going forward? See spike in §11.8.

---

## 10. References

- [#1515 — Move docs to simple markdown-based system?](https://github.com/django-components/django-components/issues/1515) (parent discussion)
- [#1557 — Migrate to Zensical](https://github.com/django-components/django-components/issues/1557) (failed attempt that motivated this)
- [#1355 — URL redirects](https://github.com/django-components/django-components/issues/1355) (one of the original motivators)
- [django-distill](https://django-distill.com/) — prior art for "Django → static site"
- [django-bakery](https://django-bakery.readthedocs.io/) — same problem, different shape
- [Pagefind](https://pagefind.app/) — search index that works without a backend
- [pygments_djc](https://pypi.org/project/pygments-djc/) — lexer we already use for `djc_py` blocks

---

## 11. Spikes to run before / during the work

Captured here so we don't lose them. Each spike has a question, why it matters, the method, and the section of this doc it feeds back into. They're not blockers for starting Phase 1 — most can run in parallel — but each one closes a real uncertainty.

### 11.1 Material-for-mkdocs search internals + Emil's search

**Status:** spike completed 2026-05-31. Recommendation: **Pagefind**. Details below.

- **Question.** How does Material's search actually work end-to-end? Where does it score, what does it index, what makes it feel "snappy"? And what is the search Emil implemented (in a separate branch or repo) — is it usable for us?
- **Why.** Search is the most-used feature on docs sites per the [#1515 thread](https://github.com/django-components/django-components/issues/1515). The biggest risk in §5's gains/losses table is "search quality." We need to compare three candidates concretely: Material's Lunr setup, Emil's implementation, and Pagefind.

#### 11.1.A Findings — Material's search

How it actually works in our current deploy:

- **Engine.** Stock [Lunr.js](https://lunrjs.com), not a fork (confirmed by reading [the worker source](https://github.com/squidfunk/mkdocs-material/blob/master/src/templates/assets/javascripts/integrations/search/worker/main/index.ts) — it imports `lunr` directly).
- **Where it runs.** In a **Web Worker** (`src/templates/assets/javascripts/integrations/search/worker/`). The UI thread is never blocked. This is the source of the "snappy" feel.
- **Index format.** A single JSON file at `site/search/search_index.json`. Our current index measures **1.3 MB uncompressed for 1,373 entries** (one entry per heading, not per page; ~200 pages total).
- **Index schema.** Our config: `{title: boost 1000, text: boost 1, tags: boost 1000000}`, pipeline `[stopWordFilter]` only (no stemming despite Lunr supporting it; we never enabled it). Separator: `[\s\-]+`. Language: `en` only.
- **Tokenizers.** Per-language stemmers loaded dynamically from `assets/javascripts/lunr/` (we ship them all even though we only use `en`). Special tokenizers exist for Japanese (`tinyseg`), Hindi and Thai (`wordcut`) — irrelevant to us.
- **What Material adds on top of stock mkdocs.** Search modal UI, autocomplete suggestions, in-result highlighting, deep-link/shareable query URLs, `data-search-exclude` pragma to omit content, frontmatter-driven page boosting.
- **No fuzzy/typo tolerance** out of the box (Lunr supports `~1` syntax but Material doesn't expose it).

#### 11.1.B Findings — Pagefind

- **Engine.** Custom Rust binary, runs at build time as `pagefind --site site/`. Indexes the built HTML directly — no separate indexer pass to maintain.
- **Bundle size.** Documented as ~100 kB total network payload for typical sites, scaling to under 300 kB for a 10,000-page site. **About 10× smaller than our current Lunr index alone**, before counting Lunr's library JS.
- **Index loading.** Lazy and alphabetically chunked — only the relevant fragment is fetched as the user types, not the whole index up front.
- **Anchor-level sub-results.** First-class. Each page result returns `sub_results[]` with their own `url` (with fragment), `title`, and `excerpt`. This matches our current per-heading granularity exactly without extra work.
- **Ranking.** Quadratic weighting per HTML tag, defaults: `h1=7.0`, `h2=6.0`, `h3=5.0`, `h4=4.0`, `h5=3.0`, `h6=2.0`, everything else `1.0`. Quadratic = weight 2 has ~4× impact, weight 10 has ~100× impact. Customizable per-element via `data-pagefind-weight="N"` attribute on any HTML node.
- **Filters/facets.** Via `data-pagefind-filter` HTML attribute. Useful if we want per-version or per-section filtering later.
- **API surface.** Tiny — `await pagefind.search(query)`, `pagefind.debouncedSearch()` (300ms debounce built in), `pagefind.filters()`, `pagefind.preload()`. We'd build a `SearchBar` Django component that wraps it, or use Pagefind's prebuilt Component UI.
- **Diacritics.** Folded by default (`café` matches `cafe`). Configurable via `exactDiacritics`.
- **No fuzzy/typo tolerance documented.** Same gap as Material.
- **Custom UI is fully supported.** API-first design; the prebuilt Component UI is opt-in, not required.

#### 11.1.C Findings — Emil's search

**Located** at [emilstenstrom/justhtml/docs/assets/search.js](https://github.com/EmilStenstrom/justhtml/blob/main/docs/assets/search.js), live at [emilstenstrom.github.io/justhtml](https://emilstenstrom.github.io/justhtml/). Linked from [#1515](https://github.com/django-components/django-components/issues/1515).

How it works:

- **Zero build step, zero dependencies.** Pure vanilla JS, 9.3 kB unminified. No npm, no Lunr, no Rust binary, nothing to install.
- **Indexing happens in the browser on first page load.** The script fetches the index page (`/`), scrapes every `<a href="*.html">` link, then fetches each linked page, parses it with `DOMParser`, picks the `.markdown-body` element (Jekyll convention) or `<body>`, and extracts a title + body text per page.
- **Cache.** Indexed entries land in `sessionStorage` keyed by a CSS-bust version param. Subsequent searches re-use the cache for the session. New session → re-fetches every page.
- **Normalization.** Lowercase → NFKD → strip diacritics → strip non-alphanumeric.
- **Scoring** (per token, AND semantics — every token must appear in title or body):
    - Title match: `+300`, position boost (earlier=better, up to `+120`), frequency boost (`+15`/occurrence, capped `+60`).
    - Body match: `+100`, position boost (up to `+60`), frequency boost (`+5`/occurrence, capped `+60`).
    - Token-length bonus: `+3` per char, capped `+40`.
- **Phrase bonus.** Full query as a substring: `+250` in title, `+120` in body.
- **UI.** Tiny `<input>` + `<ul>`, inline CSS injected, 50 ms debounce, `<mark>` highlighting. `MAX_RESULTS = 3`.

What's nice about it:

- The scoring function is **actually thoughtful** — token-position, frequency, phrase bonus, length bonus. Better than naive `term in text`.
- Zero dependencies means it'll never bit-rot from a library upgrade.
- For tiny docs sites (justhtml is ~10 pages) it's a perfect fit.

Why it doesn't scale to our docs:

- **First search has to download every page.** For our ~200 pages averaging ~20-50 kB each, that's **a multi-megabyte cold fetch on every new session**, with one `fetch()` per page. Material's `search_index.json` is a single 1.3 MB blob; Pagefind's chunked index is even smaller and only loads slices on demand.
- **No sub-anchor results.** One result per page; we currently give one per heading (1,373 entries) and would want to keep that granularity.
- **`MAX_RESULTS = 3`** is too restrictive for 200+ pages.
- **AND semantics without stemming** is unforgiving — `components` wouldn't match `component`, `fragments` wouldn't match `fragment`. Same gap as Pagefind, but Pagefind has stemming.
- **Hard-coded for Jekyll/`.markdown-body`.** Picks the 2nd `<h1>` because Jekyll page templates put a site-title `<h1>` first. Doesn't generalize.

**Verdict relative to Pagefind:** Emil's approach is the right answer for *justhtml's* constraints (no build infrastructure, GitHub Pages renders markdown directly, ~10 pages). It does not transfer to our constraints (build pipeline exists, ~200 pages, anchor-level granularity expected, users actively rely on search per the [#1515 thread](https://github.com/django-components/django-components/issues/1515)).

**Worth borrowing from it:**

1. The scoring function — token-position-aware + phrase bonus — is a small, testable algorithm that could power a **fallback layer** when Pagefind returns 0 results (i.e. a tiny in-memory index of just page titles + headings used to recover from typos). That's the post-Phase-5 mitigation already noted in §4.5.
2. The cache-by-CSS-version trick is a clean way to invalidate indexed content when the site rebuilds. Pagefind already handles this via its own bundle hashing, but the pattern is good to know.

#### 11.1.D Comparison

| Dimension | Material (Lunr) — today | Pagefind | Emil's justhtml search |
|---|---|---|---|
| **Index size on disk** | 1.3 MB JSON (our build) | ~100 kB total network for typical sites | None (built in-browser) |
| **First-load cost** | Single 1.3 MB fetch | Chunked, only needed slice | **N fetches × page size** (~5-10 MB for our docs) |
| **Subsequent searches** | Instant (worker memory) | Instant (worker memory) | Instant (sessionStorage cache) |
| **Where indexing happens** | mkdocs build (Python) | `pagefind` CLI post-build (Rust) | Runtime, in the user's browser |
| **Where search runs** | Web Worker | Web Worker (via Pagefind's bundle) | Main thread |
| **Anchor-level results** | Yes (one entry per heading) | Yes (`sub_results[]`) | No (one entry per page) |
| **Ranking model** | Manual per-field boosts (we set `tags: 1M`, `title: 1K`) | Quadratic per-tag (h1=7, h2=6, …); customizable via HTML attr | Hand-rolled: position + frequency + phrase bonus, AND tokens |
| **Stemming** | Available but **not enabled** in our config | Built-in | None |
| **Fuzzy/typo tolerance** | Not exposed | Not documented | None |
| **Diacritics folding** | Lunr default (Latin only) | Yes, default on; configurable | Yes (NFKD) |
| **Filters/facets** | No | Yes (HTML-attr driven) | No |
| **Bundle JS** | Lunr + Material's worker (~30+ kB) | Pagefind UI shim (we'd build our own) | **9.3 kB unminified, zero deps** |
| **UI** | Material's modal + suggestions + highlighting + share URL | Prebuilt Component UI **or** our own (we'd use our own) | Inline input + 3-result list |
| **Multi-version search** | One index per version (via `mike`) | Same (one bundle per version directory) | Per-site only |
| **Maintenance burden** | Pinned to mkdocs-material; recent Pygments pin came from this stack | Standalone CLI; can be upgraded independently | None — it's a single file we'd own |
| **Best fit** | Today's mkdocs/Material stack | A real docs site with a build pipeline | A static-markdown site with no build step |

#### 11.1.E Recommendation

**Use Pagefind.** Reasoning:

1. **Bundle size win.** ~10× smaller index. Material's search index is the single biggest non-image asset on our docs site today. Cutting it shrinks first-paint for everyone, especially mobile.
2. **Anchor-level UX preserved for free.** `sub_results[]` maps onto what we have today without a re-architecture.
3. **Ranking is HTML-driven, not config-driven.** We control weights by what we mark up in our `doc_page` and `api_reference` components — no separate YAML to keep in sync.
4. **Build pipeline matches ours.** A single CLI step after the static build. Drops straight into the new `uv run docs-build` flow.
5. **Decoupled lifecycle.** Pagefind is a single binary; upgrades don't fight the rest of the docs stack (unlike Material/mkdocs/Pygments coupling).
6. **Custom UI is the path.** We're building components anyway — wrap Pagefind's JS API in a `SearchBar` component. We get full control over styling and behaviour.

**Caveat: typo tolerance.** Neither Material's current config nor Pagefind offers it. If user feedback later flags this, mitigations exist in order of cost:

- **Curated synonyms file** consumed by our `SearchBar` component (1 day of work).
- **Query expansion** — try the literal query, then a stemmed variant, then known-misspelling rewrites.
- **Fuse.js fallback overlay** when Pagefind returns 0 results — Fuse adds ~20 kB and does fuzzy match against a small in-memory list of page titles.

None of these are blockers for the migration; they're addressable post-Phase-5 if needed.

#### 11.1.E.1 Engine-vs-engine: Pagefind vs Lunr (feature parity)

§11.1.D compares the three *products* as deployed. This sub-section is a narrower question Juro asked: **as search engines**, how do Pagefind and Lunr compare? Useful for understanding what we'd actually be trading away if we kept Lunr-but-ditched-Material.

| Engine feature | Lunr.js | Pagefind |
|---|---|---|
| **Core scoring algorithm** | BM25 | **BM25-aligned** (since [Pagefind v1.1.0](https://github.com/CloudCannon/pagefind/releases/tag/v1.1.0)) |
| **Configurable ranking parameters** | Per-field boosts only | 6 parameters: term frequency, term similarity, page length, term saturation, diacritic similarity, metadata weights |
| **Stemming (en)** | Optional pipeline; **not enabled** in our config | Built-in, on by default |
| **Stop words** | Optional pipeline; we use `stopWordFilter` | Built-in |
| **Diacritics folding** | Latin only, via pipeline | Built-in, on by default; configurable via `exactDiacritics` |
| **Tokenizer** | Whitespace + separator regex; per-language modules | Per-language WebAssembly module; auto-detected from `lang` attr |
| **Languages** | 32+ via `lunr-languages` plugin | 39+ built into the WASM bundle |
| **Index format** | Single JSON blob, `JSON.stringify(idx)` | Chunked binary bundles, alphabetically sliced, lazy-loaded |
| **Index location** | Build-time pre-built (recommended) or browser-built | Build-time only (Rust CLI scans built HTML) |
| **Index granularity** | Per-document (you control "document" — we use one-per-heading) | Per-page **with anchor-level sub-results** baked in (no extra config needed) |
| **Runtime** | Pure JS, runs anywhere; ~8.9 kB min+gz for the core | WebAssembly module, runs in Web Worker by default (`noWorker` to disable) |
| **Web Worker** | DIY (Material wires it up) | Default-on |
| **Custom UI** | Hand-rolled (Lunr is just an engine) | Hand-rolled **or** prebuilt Component UI |
| **Multi-site search** | DIY (merge JSON indexes manually) | First-class: `pagefind.mergeIndex(...)`, `indexWeight`, `mergeFilter`, `language` per index. CORS needed when cross-domain |
| **Filters / facets** | DIY (one index per field, or per-field queries) | First-class via `data-pagefind-filter` HTML attribute |
| **Highlighting in result** | DIY | Built-in (in excerpts) |
| **Excerpt generation** | DIY | Built-in |
| **Debounced API** | DIY | `pagefind.debouncedSearch()` built in (300 ms default) |
| **Append to index** | No (rebuild required) | No (rebuild required) |

#### 11.1.E.2 Query syntax — where Lunr is richer

Lunr's query language is the clearest spec win:

| Operator | Lunr | Pagefind |
|---|---|---|
| Fuzzy match (edit distance) | `foo~1`, `foo~2` | **Not documented** |
| Wildcard / prefix | `foo*`, `*oo`, `f*o` | **Not documented** |
| Per-field query | `title:foo` | Not at query-time (use filters / weights instead) |
| Per-term boost | `foo^10 bar` | Not at query-time (use HTML weights instead) |
| Required term | `+foo` | Not documented |
| Prohibited term | `-baz` | Not documented |
| Phrase query | DIY | Not documented |

The trade-off pattern is: Lunr puts power in the **query syntax**, Pagefind puts it in **build-time HTML annotations** (`data-pagefind-weight`, `data-pagefind-filter`, `data-pagefind-meta`). Pagefind's bet is that docs queries are short keyword queries from people who don't read query-syntax cheat sheets — and on that bet, structuring relevance at indexing time beats hoping users type `foo~1`.

For our audience (Django devs Googling "django component slot fill" and clicking through to our docs), I think Pagefind's bet is correct. We can ship a perfectly good docs search without a single query-syntax token. If someone types `slot`, both engines find pages containing `slots`/`slot`/`Slot` via stemming + case-fold; the better-ranked one wins on a UX axis Pagefind controls more directly.

#### 11.1.E.3 Where Lunr would still win, if we kept it

Three real Lunr-only wins exist:

1. **Fuzzy `~1`/`~2`.** Catches misspellings that Pagefind misses entirely. Recoverable in Pagefind world via the fallback layer mentioned in §4.5.
2. **Wildcard `*`.** Useful for `regis*` matching `registry`/`register`/`registered`. Pagefind's stemmer covers most of these but not all (e.g. `regis*` returns nothing in Pagefind).
3. **Operators visible in URLs.** Lunr queries are simple strings; people can paste `+component -slot` and share it. Pagefind queries are JS calls and don't expose this syntax.

These are real but small. **None changes the overall recommendation** — Pagefind's anchor-level results, chunked bundle, and HTML-driven weighting model still win on aggregate for our use case.

#### 11.1.E.4 If we wanted Lunr-but-not-Material

Just for completeness: yes, this is possible. Lunr is a standalone JS library (~8.9 kB min+gz for the English core, plus ~3-5 kB per extra language). We'd:

1. Build the JSON index in our `build_docs` step using either the JS Lunr or [`lunr-py`](https://github.com/seanlee97/lunr-py) (Python port).
2. Ship `lunr.min.js` and our index in the static output.
3. Build a `SearchBar` component that wires the Lunr API into a Web Worker.

Why we don't: we'd be reinventing what Material gives us today (modal UI, suggestions, highlighting, share URLs) on top of an engine that's strictly less feature-rich than Pagefind for the build-time-static use case. Pagefind already does the work. Lunr is the right choice if we wanted user-facing query syntax (`+foo`, `foo~1`) — see §11.1.E.3 — and that's not a need we have today.

#### 11.1.F Validation step before we lock this in

Before committing, run the original method step #3-#4 hands-on: index our current built site with `pagefind --site site/` (it works against the existing mkdocs output), and compare top-N for the curated queries `{"component", "slot", "fragment", "media", "extension", "registry", "render", "context", "tag"}` against Material's results on the live site. Capture screenshots / a small table for the design doc. ~1-2 hours of work; cheap insurance before we delete the Material/Lunr stack.

- **Feeds into.** §4.5 (final pick), and any synonym/typo fallback decision.

#### 11.1.G UX-feature rebuild matrix (engine-agnostic)

The engine choice gives us *retrieval* — the result list for a query. Everything else around the search bar is UX/UI we'd build ourselves regardless of whether we picked Pagefind or Lunr. This sub-section catalogues every Material search-UX feature, what we'd inherit free from each engine, and which ones we should actually rebuild.

**Legend.** Cost is **S** = a few hours, **M** = ~1 day, **L** = ~2-3 days. "Free (PF)" = Pagefind ships it; "Free (Lunr)" = Lunr ships it; otherwise we DIY.

| # | Material UX feature | What it is | Pagefind | Lunr | Should we rebuild for v1? | Cost |
|---|---|---|---|---|---|---|
| 1 | **Search modal** (overlay input + result list) | The shell of the experience | DIY | DIY | **Yes** — primary interaction | M |
| 2 | **Anchor-level results** | One result per heading, with a fragment URL | Free (PF) — `sub_results[]` | DIY — index per heading | **Yes** — table-stakes for our docs | S (UI only) |
| 3 | **Result excerpts with highlighted terms** | `<mark>`-wrapped matched terms in the snippet | Free (PF) | DIY — ~50 lines (Emil's `makeSnippet`) | **Yes** | S (with PF) / M (with Lunr) |
| 4 | **In-page highlight after click** | Navigate to result, matched terms highlighted on the destination page | DIY — read `?h=` URL param, wrap matches on page load | DIY | **Yes** — explains "why this result" | S |
| 5 | **Deep-linkable / shareable query URL** (`?q=foo`) | URL reflects current query so it's bookmarkable | DIY — trivial JS | DIY | **Yes** — costs almost nothing, big UX win | S |
| 6 | **Keyboard shortcuts** (`/`, `Ctrl+K`, `Esc` to close) | Focus the search input from anywhere | DIY | DIY | **Yes** — table-stakes | S |
| 7 | **Mobile / touch / focus trap / ARIA** | Accessible modal | DIY | DIY | **Yes** — non-negotiable for accessibility | M (proper) |
| 8 | **Per-element exclusion** (`data-search-exclude`) | Mark sections that should never appear in results | Free (PF) — `data-pagefind-ignore` | DIY at index time | **Yes** — just emit the attr from `doc_page` | S |
| 9 | **Per-page boost / weight** | Frontmatter `boost: 2.0` raises a page's ranking | Free (PF, different shape) — wrap page in `data-pagefind-weight="2.0"`; we map frontmatter → HTML attr in `doc_page` | Free (Lunr) at build time | **Yes** — emit from frontmatter | S |
| 10 | **No-results state** | Friendly "no results for X" with a CTA | DIY | DIY | **Yes** — basic empty state | S |
| 11 | **Theme integration (dark mode, palette)** | Search bar styled with the rest of the site | DIY | DIY | **Yes** — part of broader theme work, not search-specific | S (within theme scope) |
| 12 | **Stemming, stopwords, diacritic folding** | "fragments" matches "fragment", "café" matches "cafe" | Free (PF) | Available but **we don't enable today** | **Yes** — turn on with PF; with Lunr we'd opt in via pipeline | Zero (PF) / S (Lunr) |
| 13 | **Debounced input** | Don't search on every keystroke | Free (PF) — `pagefind.debouncedSearch()` (300 ms) | DIY — ~10 lines | **Yes** | Zero (PF) / S (Lunr) |
| 14 | **Autocomplete / token-prefix suggestions** | "comp…" suggests "component", "compose"; Material does this | DIY — maintain side-index of all tokens, prefix lookup | DIY | **Defer to v2.** Nice-to-have but adds an extra index, extra UI state. | M |
| 15 | **Recent searches** | LocalStorage of last N queries shown below input on focus | DIY | DIY | **Defer to v2.** Pleasant but not essential. | S |
| 16 | **Filters / scoping** ("search only `concepts/`", "search only `reference/`") | Restrict by section or page metadata | Free (PF) — `data-pagefind-filter` HTML attr + `pagefind.filters()` API | DIY — separate indexes or per-field query | **Defer to v2.** Useful once docs grow; not blocking for parity. | M (UI) |
| 17 | **Typo-recovery / "did you mean"** | Recover misspellings ("compnent" → "component") | DIY — fallback layer (see §4.5) | Free-ish via `foo~1` fuzzy operator | **Defer to post-Phase-5.** Pull Emil's scoring as the fallback if/when needed. | M (worth it later) |
| 18 | **Search-result analytics** | Track top queries, zero-result queries | DIY — beacon to GH Pages-friendly endpoint, or none | DIY | **Skip v1.** Add only if we discover a need. | M |
| 19 | **Cross-version search** (`/v0.150/` only vs all versions) | Search within a single docs version or across | Free (PF) — separate bundle per version directory; multi-site merge if we want "search all" | DIY — separate index per version | **Yes** for per-version; **defer** cross-version "merge". | S (per-version) / M (merge) |
| 20 | **"Share this query" button** | Click → copy URL to clipboard | DIY — trivial | DIY | **Defer.** Item #5 (deep-link URL) already makes the URL shareable; a dedicated button is icing. | S |

#### 11.1.G.1 Scheduling and prerequisites

Search isn't a standalone phase. It has hard dependencies that have to land first:

1. **E2E single page working** — at minimum a real markdown page rendering through our `doc_page` component pipeline (the §6 proof of concept). Until the page chrome exists, there's nowhere to put a search bar.
2. **Light / dark theming** — the `SearchModal` is a theme-sensitive surface (input, results, hover states, focus rings). Building it before the theme tokens exist means redoing the CSS once theming lands. Theming first; search after.
3. **Versioning — open question.** Do we need versioning in place before the first search iteration? Per-version search is just "one Pagefind bundle per version directory" (§11.1.G item #19), so probably **no — search v1 can ship pre-versioning**, with the assumption it'll naturally extend to per-version once §4.6's `docs/v/<version>/` layout is live. Confirm during the implementation spike.

**Reorder for the migration plan (§8):** today Phase 5 is "search, versioning, social cards" lumped together. Split it: theming first (in Phase 1 or a dedicated mini-phase), versioning in its own phase, then search v1 as the next phase. Search v2 and v3 come after the initial cutover.

#### 11.1.G.2 What gets built when: three iterations

Rolling up the matrix into shippable iterations, each runnable independently:

**Search v1 — core experience (~5-7 days)**

Everything required for parity with Material's day-to-day usefulness. Ships once theming is in place.

- Modal shell, anchor results UI, excerpts with highlighting, in-page highlight after click (`?h=`), deep-link query URL (`?q=`)
- Keyboard shortcuts (`/`, `Ctrl+K`, `Esc`)
- Mobile-friendly modal with focus trap + ARIA
- Per-element exclusion plumbing (`data-pagefind-ignore` emission)
- Per-page boost plumbing (frontmatter → `data-pagefind-weight`)
- No-results state
- Theme integration (assumes light/dark tokens exist)
- Free from Pagefind: stemming, diacritic folding, debounced API, anchor sub-results
- **Delayed "Searching…" fallback** (see G.3 below)

**Search v2 — power-user polish (~3-4 days, post-cutover)**

Adds the affordances that experienced users notice but new users can live without.

- Autocomplete / token-prefix suggestions ("comp…" → "component")
- Recent searches in localStorage
- Filters / scoping ("search only `concepts/`", "search only `reference/`")
- Typo-recovery / "did you mean" — implemented as a fallback layer that runs only when Pagefind returns 0 results. Borrows Emil's scoring algorithm from §11.1.C against a small in-memory index of page titles + headings.
- "Share this query" button (the deep-link URL already makes the query shareable; a dedicated button is icing)

**Search v3 — analytics (deferred, needs upstream decision)**

The unresolved piece: search-result analytics — track top queries, zero-result queries, click-through. Useful for tuning ranking and discovering missing content. **Blocked on:** where does the data go? GitHub Pages has no backend, so we'd need to pick a target (Plausible, GoatCounter, Cloudflare Worker, an internal endpoint we host). This is a separate design decision. Park it as v3.

#### 11.1.G.3 The "Searching…" fallback (kept, with a delay)

Per Juro's call: keep the spinner but **only show it after a threshold**, e.g. 300-500 ms. Most queries return in tens of milliseconds and never need it. The visible cases are slow connections fetching the chunked index for the first time, or unusually large slice fetches. Without a spinner there, the UI just appears frozen; with one, the user knows we're working.

Implementation: a small `setTimeout(showSpinner, 400)` cleared on first result. Net cost: a few lines in `SearchModal`.

#### 11.1.G.4 What we still deliberately don't copy from Material

- **"Search appears in URL anchor" (`#search-results`).** Material puts the search state in the URL hash. Causes weird back-button behavior and conflicts with page anchors. Our `?q=` query param is cleaner.
- **In-result inline "boost" badges (the ⚡ icon).** Cute but adds visual noise and explains an internal implementation detail.

#### 11.1.G.5 Components we'd actually build (search v1)

Concretely, the search v1 work is **three components**:

1. **`SearchInput`** — the input element with keyboard shortcuts and URL state. ~150 lines TS.
2. **`SearchModal`** — focus-trapped overlay containing `SearchInput` + results, with mobile/desktop responsive layout. Includes the delayed-spinner fallback. ~300 lines TS + ~150 lines CSS.
3. **`SearchResultList`** — renders Pagefind `result.sub_results[]`, including excerpts with `<mark>` highlighting and a no-results state. ~200 lines TS.

Plus one cross-cutting bit:

4. **`?h=` highlight on page load** — runs on every doc page, not just search. ~50 lines TS in our `doc_page` component's JS. Reads the URL param, walks the rendered DOM, wraps matches.

**Total estimate:** ~5 days of focused TS/CSS work, mostly UI. The retrieval layer (Pagefind) is configured in one CI step.

#### 11.1.G.6 Implementation-time validation

Per Juro's call: **don't pre-explore Pagefind/Lunr setup during this design phase.** The spike is enough to commit. The actual hands-on validation (the §11.1.F top-N comparison, plus any wiring quirks) happens when search v1 is the active phase. That's where we'd discover, for example, that Pagefind's WebAssembly bundle has a specific CORS requirement on GH Pages, or that `pagefind.search()` returns excerpts in a shape our `SearchResultList` doesn't expect. Catching those during implementation is fine; they're plumbing.

### 11.2 Zensical changes since 2026-01-25

- **Question.** What has Zensical shipped between Juro's previous evaluation on 2026-01-25 and now? Did they make template overrides easier? Did the customization story get less brittle? Any new features we'd gain by moving to it instead of building our own?
- **Why.** Zensical is the official heir to Material. If they've meaningfully closed the customization gap, the build-our-own path becomes harder to justify on engineering ROI. Conversely, if they haven't, we have an even stronger case.
- **Method.**
    1. Read Zensical's CHANGELOG / release notes from 2026-01-25 onward.
    2. Inspect their template-override docs and the equivalent of `docs/overrides/partials/` — does the customization that broke [#1557](https://github.com/django-components/django-components/issues/1557) now work?
    3. Check whether their search, versioning, social cards, and palette features are still present (Material features that Zensical inherited).
    4. Spike a 1-page proof: can we render *one* of our docs pages under Zensical with our custom nav?
- **Feeds into.** §1 (motivation), §3 (the rejected fallback).

#### Findings — 2026-05-31 (resolved by deep-dive)

**Verdict (one line):** Zensical has shipped a lot in 4 months but the gap that blocked us in January is still open: our `tabs.html` override depends on Python introspection that MiniJinja explicitly forbids, the plugin system is still not open to third parties, and Zensical itself is still 0.0.x alpha with no 1.0 ETA. The case for building our own docs site is **stronger**, not weaker.

##### Release velocity since 2026-01-25

24 releases (0.0.20 on 2026-01-29 → 0.0.43 on 2026-05-19). Active, but still self-classifies as "3 - Alpha." First-ever release was 2024-11-25, so the project is ~18 months old. The FAQ states explicitly: **"There's currently no ETA for a 1.0.0 release."** The 0.0.x scheme means the team reserves the right to make breaking changes between any two patch versions.

##### What did get fixed since Jan 25

- **mike works** — via a [squidfunk/mike fork](https://github.com/squidfunk/mike) that targets Zensical. Explicitly framed by the team as a *bridge solution* until native versioning lands "in the coming months." If we go the Zensical route, we'd swap one out-of-tree fork dependency for another.
- **mkdocstrings works (preliminary)** since 0.0.11 — but **no cross-references, no backlinks**. The team says they will "rethink API reference documentation from the ground up in the coming months." Translation: today's integration is throwaway, and our `docs/reference/*` pages would render with degraded link behavior.
- **`mkdocs.yml` config compatibility** is real and confirmed by multiple migration writeups.
- **Theme structure** preserved — the theme is still called `material`, `base.html`/`main.html`/`partials/*` exist, and `custom_dir` overrides work for users with overrides based on Material 9.6.18+.

##### What's still broken or missing

- **Plugin system is not open to third parties.** [122 open backlog issues](https://github.com/zensical/backlog/issues) with zero PRs. Plugin support is being added one at a time by the Zensical team (`mkdocs-glightbox`, `mkdocs-autorefs`, `mkdocs-caption`, `mkdocs-include-markdown`, `markdown-exec` are all open requests). FAQ confirms: "we invite the community to develop modules" only after the system stabilizes.
- **`mkdocs-include-markdown` is unsupported** ([backlog #127](https://github.com/zensical/backlog/issues/127)). We rely on it.
- **`mkdocs-macros` is unsupported.** We use it (1 page today, `community/people.md`).
- **The MiniJinja template engine has a hard rule:** *"there is no Python interpreter available in MiniJinja. This means that it is not possible to call arbitrary Python functions."* This breaks any override that calls methods on Python objects (`.split()`, `.update()`, `.append()`, `__class__.__name__`).

##### Concrete blast radius on our two overrides

I read both override files line-by-line against MiniJinja's constraints:

**[docs/overrides/partials/nav-item.html](docs/overrides/partials/nav-item.html)** (8.8 KB):
- One offending line: `ref.title.split(": ", 1)` is a Python method call. MiniJinja has a `split` *filter* (`ref.title | split(": ")`), so this is a 3-line rewrite, not a blocker.
- Everything else (attribute access on `nav_item`, `loop.index`, `|first`/`|length`/`|safe`/`|tojson`, `{% include %}`, `{% set namespace %}`) is standard Jinja and supported.
- **Verdict:** ports with minor adaptation.

**[docs/overrides/partials/tabs.html](docs/overrides/partials/tabs.html)** (6.9 KB):
- `{% if nav_item.__class__.__name__ == "Page" %}` — direct Python introspection. **MiniJinja blocks this by design.** No `__class__` access.
- `grouped_dict.update({...})` and `group["items"].append(...)` — mutating dict/list via Python methods. MiniJinja is not a Python sandbox; mutation idioms have to be reworked into pure-template accumulation (which is awkward without macros that can return values, which MiniJinja does not have either).
- `parts = nav_item.title.split(': ', 1)` — same method-call issue as nav-item.html.
- `{% import "partials/tabs-item.html" as item with context %}` — depends on Material's `partials/tabs-item.html` still existing under the same name in Zensical. Their docs don't enumerate which partials are preserved verbatim vs. renamed; this would need a `pip install zensical` + actually checking.
- **Verdict:** the file needs a substantial rewrite, possibly to push the grouping logic *out* of the template entirely (into a config-side data prep step) — which is exactly the architectural shift Zensical wants but doesn't yet expose to us. We'd be carrying a more complex override that fights MiniJinja's design.

This is the same class of pain that closed [#1557](https://github.com/django-components/django-components/issues/1557): "the nav-real-estate template overrides error out in Zensical." Five months later, the underlying constraint hasn't moved.

##### Real-world migration reports

Two recent migration writeups corroborate this:

- The [Vidyasagar Machupalli writeup (May 2026)](https://medium.com/vmacwrites/from-mkdocs-1-6-to-zensical-heres-why-i-finally-made-the-move-53b273b49cdd) calls out: *"if your team has a lot of custom theme overrides — custom CSS hooks, template blocks, JavaScript injections — those will need to be rethought."* Their own overrides were minor; ours are not.
- The [Daniel xfuture-blog post](https://xfuture-blog.com/posts/migrate-from-mkdocs-to-zensical/) describes a smooth migration but **does not have any template overrides, plugin dependencies, or versioning**. Their experience does not generalize to us.

The "easy migrations" reported in the wild are projects with vanilla setups. We are not a vanilla setup.

##### What this means for the design doc

- **§1 (motivation):** strengthen the case. Five months and 24 releases later, the same blockers are present. The "wait for Zensical to mature" path is open-ended.
- **§3 Option C (live Django server) → replaced by an implicit Option D (wait for Zensical) — reject.** The risks are: alpha software with no 1.0 ETA, plugin system not yet third-party-friendly, our second-largest override needs a Python-free rewrite, mkdocstrings is "preliminary" and headed for a from-scratch rebuild, mike is a bridge fork.
- **Decision:** continue with Option B (Pre-render with Django at build time). Revisit Zensical only if (a) it ships 1.0, (b) its module system opens to third parties, and (c) mkdocstrings cross-references/backlinks land. Until all three are true, the customization gap is bigger than the build-our-own-docs gap.

##### What we'd give up by building our own instead of going Zensical

The honest opportunity-cost ledger. Three categories, ordered by how much pain each one moves to our column:

**A. Material-class polish we'd have to rebuild ourselves**

These are real features Material/Zensical give us for free that our own renderer has to recreate. This is the bulk of the migration cost.

| Feature | Today via Material | Cost to rebuild |
|---|---|---|
| Palette toggle + auto light/dark mode | Free | One CSS file with `[data-theme]` variants + 20-line JS toggle |
| Custom palettes / colors | Free | CSS variables (we'd own the design tokens) |
| Font + icon + emoji + favicon plumbing | Free | Standard `<link>` + Material-icons / iconify imports |
| Social cards (OG-image generation) | Free | Playwright or Pillow at build time, ~200 lines |
| 30+ markdown extensions (admonitions, tabs, snippets, mermaid, math, footnotes, tasklist, tooltips, grids, annotations, ...) | Free via pymdown | Each extension supported in `markdown-it-py` natively; the few that aren't (e.g. annotations, grids) need custom plugins or a small DIY pass |
| Instant loading / prefetching / instant previews | Free | Each one is a small JS feature (~50-200 lines); we'd cherry-pick which ones matter |
| Sticky tabs / sections / expansion / pruning / breadcrumbs / section-index pages | Free | Navigation rendering is one of our components; logic is ~300 lines |
| Anchor tracking + TOC anchor following + back-to-top | Free | Standard scroll-spy JS, ~100 lines |
| Hide-sidebars + keyboard shortcuts + content-width controls | Free | Mostly CSS + a small JS layer |
| Code-block copy button + line highlight + line numbers | Free | Pygments output + a small JS wrapper |
| Search (Lunr-class) | Free | Pagefind handles this; better-than-Material out of the box |
| Strict mode + link validation | Free | We own this (§11.10 guardrails); strict-than-mkdocs feasible |
| Site-wide 404 page | Free | Static `404.html` |
| Cookie consent / data privacy | Free | One JS modal; rarely needed for a docs site like ours |

**Rough order of magnitude:** category A is *most* of the work in Phases 1-5 of §5. None of these are individually hard; the cost is breadth, not depth. Spread across the 6-8 week estimate.

**B. Zensical roadmap items we'd never get**

These are the genuinely new things Zensical is building that we'd permanently miss out on:

- **Disco search engine** — Rust-based, *"blazing fast"*, with ranking + filtering + aggregation. Likely better than Pagefind once shipped. But: not released yet, no ETA.
- **Module system** — composable, extensible pipeline replacing plugins. Coming first to paid Spark members, eventually opening. Would let us write our docs-site-specific behaviors as Zensical modules instead of as Django code.
- **Component system** — reusable components in templates. Ironically, this is what we're going to build *ourselves* with django-components. We'd be making our own version of what Zensical is building for everyone.
- **Modular navigation** — flexible nav beyond mkdocs' monolithic structure.
- **Native API documentation** — cross-language, replacing mkdocstrings. We'd skip this entirely and keep griffe + our own renderer.
- **Modern theme** — new visual aesthetic alongside classic Material. Same fix-it-ourselves story as polish above.
- **CommonMark via Rust parser** (replacing Python Markdown). We use `markdown-it-py` which is already a CommonMark parser, so we don't really miss this.

**What we actually lose here:** Disco (if it lives up to the hype) and the module ecosystem. Component system is moot (we're building our own). The rest are either fixed-by-our-own-work or things we don't use.

**C. Stuff we don't use today that Zensical ships**

Features we'd theoretically miss but never used in the first place:

| Feature | Used today? | If we wanted later |
|---|---|---|
| Comment system | No | Plug in a third-party widget |
| Blog | No | Same |
| Tags + tag listings + tags in search | No | Could DIY in a small build pass |
| 60+ language i18n | No | We're English-only; out of scope anyway |
| Revisioning (document dates, authors, contributors) | Sort of, via `git-revision-date-localized` + `git-authors` | DIY via `git log`, ~50 lines |
| Site analytics + feedback widget | No | Plug in Plausible/GA + a JS widget |
| Announcement bar | No | One component |

This category is essentially **free** — we don't lose anything we currently use, and if we ever want one of these, each is a small, well-scoped addition.

##### Net assessment

The realistic loss is **category A** (Material-class polish) and **Disco + module system** from category B. We're not losing anything load-bearing for our use case (live component examples — Zensical can't do that anyway without our docs being Django-rendered first). And we're gaining things Zensical can't give us:

- **Live django-components examples** embedded in docs (the killer feature of §4.2).
- **Pygments security upgrade unblocked** (§1).
- **Anchor scheme we control** — `#Component` instead of `#django_components.Component` (§6).
- **Versioning we control** — committed to `master` instead of a `gh-pages` fork (§4.6).
- **No "wait until v1" exposure** — we're not betting our docs on someone else's pre-1.0 alpha.

The opportunity cost is real, but it's the same opportunity cost any custom site has against a turn-key theme. The difference here is that the turn-key theme can't host our killer feature.

##### Sources

- [Zensical homepage](https://zensical.org/)
- [Zensical compatibility / features](https://zensical.org/compatibility/features/)
- [Zensical compatibility / template overrides](https://zensical.org/compatibility/overrides/)
- [Zensical customization docs](https://zensical.org/docs/customization/)
- [Zensical mkdocstrings setup](https://zensical.org/docs/setup/extensions/mkdocstrings/)
- [Zensical versioning docs](https://zensical.org/docs/setup/versioning/)
- [Zensical FAQs](https://zensical.org/docs/community/faqs/)
- [Zensical PyPI release history](https://pypi.org/project/zensical/#history)
- [Zensical GitHub org](https://github.com/zensical)
- [Zensical issues](https://github.com/zensical/zensical/issues)
- [Zensical backlog (plugin requests)](https://github.com/zensical/backlog/issues)
- [squidfunk/mike Zensical-compatible fork](https://github.com/squidfunk/mike)
- [Squidfunk announcement post (2025-11-05)](https://squidfunk.github.io/mkdocs-material/blog/2025/11/05/zensical)
- [Real-world migration: Vidyasagar Machupalli, May 2026](https://medium.com/vmacwrites/from-mkdocs-1-6-to-zensical-heres-why-i-finally-made-the-move-53b273b49cdd)
- [Real-world migration: Daniel xfuture-blog](https://xfuture-blog.com/posts/migrate-from-mkdocs-to-zensical/)

### 11.3 Django → static-site libraries (prior art audit)

- **Question.** Are there existing libraries that already do "run Django, crawl every URL, write to disk"? We named [django-distill](https://django-distill.com/) and [django-bakery](https://django-bakery.readthedocs.io/) — what do they actually look like in 2026? Anything newer?
- **Why.** If a library already implements 80% of the build pipeline, we shouldn't roll our own crawler.
- **Method.**
    1. Read django-distill's README and source — specifically: how does it handle dynamic URL discovery, fragment endpoints, and asset rewriting?
    2. Same for django-bakery.
    3. Search PyPI for "django static site" packages updated within the last 12 months.
    4. For each candidate: does it support our URL patterns (paginated nav, versioned routes, fragments)? Does it fight Django's `Media` / staticfiles?
- **Feeds into.** §4.1 (the build pipeline) and the Phase 1 scope.

#### Spike results (2026-05-31)

**Inventory of what's actually shipping in 2026.**

| Library | Latest | Last release | Approach | Maintained? |
|---|---|---|---|---|
| [django-distill](https://github.com/meeb/django-distill) | 3.2.7 | Aug 2024 | Registration: `distill_path()` replaces `path()`; spoofs requests via test client | Slow but alive |
| [django-bakery](https://github.com/palewire/django-bakery) | 0.13.5 | Mar 2025 | Mixin: subclass `BuildableTemplateView` / `BuildableDetailView` per page; framework walks querysets | Yes — LA Times Data Desk |
| [coltrane](https://github.com/adamghill/coltrane) | 0.40.0 | May 2026 | Filesystem-routed markdown content site, works standalone OR as a third-party Django app | Yes — recent activity |
| [django-render-static](https://pypi.org/project/django-render-static/) | 3.5.2 | Mar 2026 | **Out of scope** — transpiles Python → JS for client side, not URL crawling | n/a |
| [django-static-sites](https://pypi.org/project/django-static-sites/) | low | — | Decorator on existing views | Marginal |
| [django-staticsite](https://pypi.org/project/django-staticsite/) | low | — | Generator for DEBUG and production builds | Marginal |
| [django-jackfrost](https://pypi.org/project/django-jackfrost/) | 0.4.0 | Jul 2015 | Renderer-classes config | **Abandoned** |
| [django-medusa](https://github.com/mtigas/django-medusa) | — | 2014 | TestClient → disk/S3/GAE | **Abandoned** (README points to django-bakery) |

**Deep-dive findings on the three live candidates:**

**django-distill** ([source](https://github.com/meeb/django-distill))
- *URL discovery:* registration-only. You replace `path(...)` with `distill_path(...)` and pass a `distill_func` that yields the parameter dicts to materialize. Under the hood, it uses Django's test client to spoof requests for each URL.
- *Dynamic URLs:* path parameters only. **Query strings are explicitly rejected** ("Querystring parameters do not make sense for static page generation"). This is the most consequential limitation for our §4.4a fragments use case, since today we use `?type=alpine`.
- *Static assets:* requires `collectstatic` first, then copies from `STATIC_ROOT`. Supports `DISTILL_SKIP_STATICFILES_DIRS` and `DISTILL_SKIP_ADMIN_DIRS`.
- *Fragment / partial responses:* not supported. Only GET responses with HTTP 200.
- *Maintenance:* last release Aug 2024, no 2025/2026 releases visible. Mature but slow-moving.
- *Verdict:* the no-query-string limitation is a real obstacle but is fixable by **changing our fragment URL convention from `?type=alpine` to `/alpine/`**, which we'd want for clean static URLs anyway. So the limitation is a forcing function in the right direction.

**django-bakery** ([source](https://github.com/palewire/django-bakery))
- *URL discovery:* mixin opt-in. You subclass `BuildableTemplateView`, `BuildableListView`, `BuildableDetailView`, `BuildableArchiveIndexView`, `Buildable404View`, `BuildableRedirectView`, etc. Each subclass defines a `build_path` attribute and (for Detail views) a queryset that the framework walks, calling `get_absolute_url()` on each object.
- *Heritage:* built and maintained by LA Times Data Desk for newsroom workflows. Heavy on the "build one HTML page per Postgres row" pattern + S3 sync via Celery.
- *Static assets / fragments:* documentation lacks specifics for either; clearly not a focus.
- *Verdict:* overkill for our shape. The mixin layering pays off when your site is model-driven (thousands of detail pages from a DB). Our content is flat markdown files; we don't need the queryset machinery.

**coltrane** ([source](https://github.com/adamghill/coltrane))
- *Shape:* both a standalone framework (`coltrane create` / `coltrane play` / `coltrane record`) **and** a third-party Django app you can integrate into an existing project.
- *Content model:* markdown files with **Django template tags inside the markdown**. Auto-routes URLs from the filesystem (`content/foo/bar.md` → `/foo/bar/`).
- *Pipeline ordering:* docs don't make the markdown↔template ordering explicit. **Spike sub-task** (§11.4): read the source to confirm — this is the same question we already need to answer for our own pipeline (§4.7).
- *What it doesn't have natively:* versioning (mike-style), search, model-driven URLs (it's flat-files focused), fragment pre-rendering, griffe-based API reference.
- *Recent activity:* v0.40.0 May 2026 — most active of the three.
- *Verdict:* **closest fit in spirit**, and ideologically the same shape as our design. But layered on top of an opinionated routing/layout model that may not stretch to our requirements (versioning, custom navigation, API ref pages, fragment pre-rendering). Worth a focused second spike before committing — see "Coltrane follow-up spike" below.

#### Verdict / recommendation

**No existing library cleanly solves the whole problem.** Specifically, none of them handle our fragments use case (query-string-keyed responses) and none have versioning or griffe-based API reference. But two of them give us a meaningful starting point we shouldn't reimplement:

**Primary recommendation: build on django-distill.**
- It's the cheapest, most boring kernel for "crawl Django URLs, write to disk."
- The no-query-string limitation is a forcing function in the right direction — we rewrite our fragment URL convention from `/examples/fragments?type=alpine` to `/examples/fragments/alpine/`, and now we have clean static URLs *and* django-distill works out of the box.
- Layer our own code on top for: markdown processing pipeline (§4.7), API reference (§4.3), versioning (§4.6), search (§4.5).
- Estimated effort saved vs DIY: ~200-300 lines (the URL-iteration + test-client spoofing + asset copying loop).

**Worth a follow-up evaluation before locking in: coltrane.**
- If coltrane's filesystem-routing convention fits our `content/` layout and its markdown+templates pipeline matches §4.7's design, it could replace *both* the django-distill kernel and parts of our markdown pipeline.
- Risk: opinionated about layout. We may end up fighting it for the API-reference, versioning, and fragment-pre-rendering pieces.
- **Coltrane follow-up spike (§11.3a):** read its source for the markdown rendering order; check if its routing accepts external URL patterns (for our `reference/*` and `v/<version>/...` paths); evaluate whether we can swap our own markdown converter into its pipeline.

**Rejected:**
- django-bakery — overkill (mixin layering for model-driven sites we don't have).
- django-medusa, django-jackfrost — abandoned.
- django-render-static — solves a different problem (Python→JS transpilation).
- django-static-sites, django-staticsite — too small / unproven.

**Implication for §4.4 (fragments).** Change the URL scheme from query-string-keyed (`?type=alpine`) to path-keyed (`/alpine/`). This works with django-distill out of the box and gives us cleaner static URLs. Update §4.4a's example to reflect this.

#### §11.3a — coltrane evaluation (results, 2026-05-31)

Source-read spike on coltrane: [`renderer.py`](https://github.com/adamghill/coltrane/blob/main/src/coltrane/renderer.py), [`urls.py`](https://github.com/adamghill/coltrane/blob/main/src/coltrane/urls.py), [`management/commands/build.py`](https://github.com/adamghill/coltrane/blob/main/src/coltrane/management/commands/build.py), and the [`example_integrated/`](https://github.com/adamghill/coltrane/tree/main/example_integrated) project layout. (No `pip install`; pure source reading.)

**Q1: Markdown ↔ Django template ordering.**

Coltrane's order is **markdown → HTML → Django templates on the HTML output**. From `MistuneMarkdownRenderer.render_markdown_text`:

```python
content = self.pre_process_markdown(frontmatter_post.content)
content = self.mistune_markdown(content)         # markdown → HTML
content = unescape(content)
content = self.post_process_html(content)
# ... later, in the parent render_markdown():
content = self.render_html_with_django(html, context, request)  # HTML → Django templates
```

This is **the opposite of the Hugo-style order proposed in §4.7** (shortcodes → markdown → layout).

Coltrane keeps this order working by escaping Django template syntax with placeholder markers before markdown runs and restoring them after. Concretely:
- `{{ var }}` → `DJANGO-TEMPLATE-VARIABLE-BEGIN-var-DJANGO-TEMPLATE-VARIABLE-END` → back to `{{ var }}`
- `{% tag arg %}` → same scheme, plus a `SPACE_REPLACEMENT` sentinel for whitespace inside args.
- Code fences wrapped in `{% verbatim %}` to keep their contents from being templated.
- `replace('"', "'")` on template-tag args — **so you can't use double-quoted args** like our `{% example "fragments" %}`.

That's debt we'd inherit. We'd either fight the escape layer or work around it for every directive we add.

**Q2: Does `coltrane record` walk Django URLs?**

No. The build command (called from `coltrane record`) iterates **content markdown files**, not URL patterns:

```python
for path in get_content_paths(request=self.request):
    future = executor.submit(self._output_markdown_file, path)
```

`sitemap.xml`, `rss.xml`, `collectstatic`, `compress`, and a list of "extra files" (robots.txt, etc.) are handled separately as one-shot writes. Everything else has to be a markdown file under `content/`.

**This is the dealbreaker.** Our docs site has three categories of pages that aren't markdown files:
1. **API reference** — driven by griffe, one component-rendered page per Python symbol (§4.3).
2. **Pre-rendered fragments** — synthesized URLs like `/examples/fragments/alpine/` (§4.4a).
3. **Versioned routes** — `/v/<version>/...` paths whose content comes from other versions' content trees (§4.6).

Coltrane's `record` command would silently skip all of these. We could synthesize pseudo-markdown files for every API symbol and route them through its pipeline, but that's an awkward inversion of control.

**Q3: External URL patterns alongside coltrane.**

Routing-wise, **yes** — coltrane's `urls.py` ends in a catch-all `re_path`, so you wire it in last and your own patterns take precedence:

```python
urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("coltrane.urls")),   # catch-all goes last
]
```

So at runtime (`coltrane play`), our own views work fine. But that doesn't help us at build time, where `coltrane record` only iterates markdown files. The routing freedom is theoretical for the static-export use case.

**Q4: Other observations worth borrowing (not adopting).**

- **Manifest-based incremental builds** in `build.py`: it tracks `(path, mtime, md5)` per content file in `output.json` and skips unchanged files. Genuinely good idea — worth replicating in our own builder.
- **Multi-threaded build** using `ThreadPoolExecutor` with `cpu_count() // 2 - 1` workers by default.
- **`StaticRequest`** pattern: a fake `HttpRequest` subclass used to fool views into rendering at build time. Same trick we'd use ourselves.
- **`{% verbatim %}` wrapping for code fences**: useful defensive idea even if our pipeline order is different.

**Q5: Markdown engine.**

Coltrane uses **mistune**, not markdown-it-py. Mistune is fine but the extension ecosystem is smaller. Not a dealbreaker either way.

#### Verdict on coltrane

**Reject coltrane as the kernel. Stick with django-distill + our own markdown pipeline.**

Two showstoppers:
1. **Pipeline order is markdown-first, not template-first** (§4.7). The escape-and-restore hack to make this work has real constraints (no double-quoted template-tag args, code-fence semantics may not roundtrip cleanly with `djc_py`).
2. **`coltrane record` builds from markdown files, not Django URLs.** Our API reference, fragments, and versioned routes are not markdown files.

What we'd gain by adopting it:
- A filesystem-routed catch-all view (~50 lines of our own code anyway).
- Manifest incremental builds (worth copying as a pattern, not as a dependency).
- Sitemap.xml, rss.xml, collectstatic, compress, django-browser-reload pre-wired (incidental conveniences, low cost to do ourselves).

What we'd lose:
- Control over markdown↔template ordering.
- Ability to render non-markdown URLs without inverting our control flow.
- Choice of markdown library.
- A clean docstring on our own pipeline.

**Borrow, don't adopt.** Take three ideas from coltrane into our own builder:
1. **Manifest-based incremental build** — track per-file mtime/md5 in an `output.json`, skip unchanged content. Big win for dev-mode iteration.
2. **`StaticRequest` fake-HttpRequest** — the same trick django-distill uses; coltrane's version is slightly cleaner to copy.
3. **`{% verbatim %}` wrapping of code fences** — even with our template-first order, we want code blocks not to be templated.

Feeds into: §4.1 (build kernel), §4.7 (pipeline). No further coltrane follow-ups needed.

### 11.4 Markdown + Django templates pipeline

**Status:** spike completed 2026-05-31. Recommendation: **fence-protection pre-pass + full Django template engine + python-markdown + DocPage layout**. Details below.

- **Question.** Can pages remain markdown but with Django template tags embedded? What's the cleanest way to make `{% example %}` and friends — *and arbitrary `{% component %}` calls* — work inside markdown without the markdown parser fighting them?
- **Why.** Already partially answered in §4.7. The spike validates the answer end-to-end and corrects the §4.7 sketch.

#### 11.4.A Findings — what's in the docs today

Sampled three real pages plus the mkdocs config:

- [docs/getting_started/your_first_component.md](docs/getting_started/your_first_component.md) — your-first-component tutorial
- [docs/getting_started/adding_js_and_css.md](docs/getting_started/adding_js_and_css.md) — JS/CSS chapter (admonitions with titles, nested lists with code, multi-language fences)
- [docs/examples/fragments/README.md](docs/examples/fragments/README.md) — example doc that uses `--8<--` snippets

What we found, mapped to the markdown extensions configured in [mkdocs.yml](mkdocs.yml):

| Feature | Syntax in docs today | python-markdown extension |
|---|---|---|
| Code fences with language | ` ```python `, ` ```htmldjango `, ` ```djc_py `, ` ```css `, ` ```js `, ` ```html ` | `pymdownx.highlight` + `pymdownx.superfences` + Pygments (via `pygments_djc` for djc) |
| Code fences with title | ` ```python title="components/calendar/calendar.py" ` | `pymdownx.highlight` |
| Inline code | `` `Component.render()` `` | core |
| File snippets | `--8<-- "docs/examples/fragments/component.py"` (inside a fenced block) | `pymdownx.snippets` |
| Admonitions (typed, optional title) | `!!! note` / `!!! info "Special role of css and js"` | `markdown.extensions.admonition` |
| Cross-page links | `[Component](../reference/api.md#django_components.Component)` | core + `toc` for `#anchor` resolution |
| Nested lists with code blocks | indented 4 spaces inside `1.` | core, but indentation is fragile |
| Images | `![Fragments example](./images/fragments.gif)` | core |
| Auto-link GitHub refs | `#1593`, `@oliverhaas` | `pymdownx.magiclink` (configured for `django-components/django-components`) |
| HTML in markdown | rare in our docs but supported | `md_in_html` |
| Tables, definition lists, footnotes, task lists | configured but rarely used | `tables`, `def_list`, `pymdownx.tasklist` |
| Emoji | configured but rarely used | `pymdownx.emoji` |
| TOC with `¤` permalinks | every page heading | `toc` with `permalink: "¤"` |

The body content is plain CommonMark plus a few well-defined extensions. The extensions are localized: a few admonitions per page, occasional snippets, magic links.

#### 11.4.B Library choice — keep `python-markdown` + `pymdownx.*`

| | `python-markdown` (today) | `markdown-it-py` |
|---|---|---|
| Spec | "loose," historically extended via plugins | CommonMark (strict) |
| Speed | OK | Faster |
| Existing docs compatibility | **Native** — every page is written for `pymdownx.*` syntax | Would require rewriting every admonition, snippet, magic-link, fence-with-title |
| Ecosystem | `pymdownx.*` is the de-facto extension pack; mature, widely used | `mdit-py-plugins` is smaller; admonition has a different syntax (Pandoc `::: note` vs `!!! note`) |
| mkdocs coupling | None at the python-markdown layer | n/a |

**Decision: keep `python-markdown` with the existing `pymdownx.*` extension set.** The speed gain from `markdown-it-py` does not justify rewriting ~100 admonitions, every `--8<--` snippet, and every `title="..."` code fence. None of the `pymdownx.*` extensions depend on mkdocs — they plug into the `markdown` library directly. They keep working unchanged. This reverses the "or markdown-it-py" hedge in §4.7's earlier draft.

#### 11.4.C The pipeline (revision of §4.7)

§4.7's first draft said: "render markdown source as a Django template" (Pass 1), then "markdown to HTML" (Pass 2), then "wrap in layout" (Pass 3). Juro raised a real concern in feedback: **what about arbitrary `{% component "table" rows=... %}` calls in markdown?**

A narrow regex-based whitelist (the previous spike answer) would leave `{% component %}` untouched, so it would survive Pass 1, get carried through python-markdown as text, and end up as literal `{% component %}` in the final HTML — broken.

The fix is conceptually simpler: **wrap every code region in `{% verbatim %}...{% endverbatim %}` in a pre-pass, then run Django's full template engine on the result.** Every Django tag — `{% component %}`, `{% example %}`, `{% docstring %}`, `{% if %}`, `{% for %}` — works uniformly. Code fences are protected because their content is wrapped in `{% verbatim %}`, which is Django's official escape mechanism for "treat what's inside as literal."

Revised four-pass pipeline:

```
content/foo.md
    [Pre-pass] Fence-protection scanner (~50 LOC, Python)
        - Walk the source line-by-line, tracking fence state for:
            - ``` fenced blocks
            - ~~~ fenced blocks
            - 4-space indented code blocks
            - `inline code` spans
        - Wrap each contiguous code region in {% verbatim %}...{% endverbatim %}
        - Output: markdown source where every code region is verbatim-escaped

    [Pass 1] Django template engine renders the body
        - {% load docs_extras component_tags %} is auto-injected
        - Any Django tag works:
            {% component "table" rows=... %}     -> runs the djc renderer
            {% example "fragments" %}            -> custom simple_tag, runs ExampleCard.render(...)
            {% docstring "django_components.Component" %} -> custom simple_tag, runs ApiReference.render(...)
            {% include_file "path" %}            -> custom simple_tag, emits a fenced code block
            {% version %}                 -> custom simple_tag, returns "0.150.0"
            {% if %}, {% for %}, {% with %}      -> just work
        - Output: markdown body with all template tags expanded to either
          markdown text or block-level HTML (separated by blank lines)
        - Inside the {% verbatim %} blocks, every {% %} pattern is emitted literally
          (so doc examples that *show* template tags survive)

    [Pass 2] python-markdown -> HTML
        - Extensions match today's mkdocs config: pymdownx.highlight, pymdownx.superfences,
          pymdownx.snippets, pymdownx.magiclink, pymdownx.details, pymdownx.tabbed,
          pymdownx.tasklist, pymdownx.emoji, pymdownx.inlinehilite, admonition, attr_list,
          codehilite, def_list, tables, md_in_html, toc, abbr
        - md_in_html lets block-level HTML emitted by Pass 1 pass through
        - toc.permalink="¤" preserves today's heading-anchor permalinks
        - Slugify with pymdownx.slugs.slugify(case="lower") to match Material's anchors exactly
        - Output: HTML page body + TOC tree

    [Pass 3] DocPage layout wrap
        - Render DocPage Django component:
            DocPage(content_html, title, toc, breadcrumbs, edit_url, version, version_picker, ...)
        - ONLY place page chrome (nav, sidebar, footer, dark mode, search bar) is added
        - Output: complete HTML page

    [Pass 4] Minify + sanitize + write
        - htmlmin or equivalent
        - write to docs/v/<version>/<path>.html
```

The key shape: **pre-pass protects code, then Django, then markdown, then layout.** There is no "narrow whitelist directive expander" and no special handling for `{% component %}` — Django's template engine handles every tag uniformly.

#### 11.4.D Where's the line between directive and Django template tag?

**There is no line.** Every tag in markdown is just a Django template tag. This was the user's question and is the central insight of the revised design.

- "Docs tags" like `{% example %}`, `{% docstring %}`, `{% include_file %}`, `{% version %}`, `{% image %}` are convenience `simple_tag` definitions registered in `docs_extras.py`. They're sugar for common docs operations.
- djc tags like `{% component "table" %}` are the same tags users use in their own templates. They work in docs unchanged because Django loads the `django_components` template library like any other Django app.
- Core Django tags (`{% if %}`, `{% for %}`, `{% url %}`, `{% with %}`) work too. Useful for cases like "show one section only in the latest version" or looping over a metadata structure.

Authors don't have to memorize a separate "directive" syntax. They write Django template tags in markdown the same way they write them in templates.

#### 11.4.E How a docs tag wires up to a Django component (the `<ApiReference>` clarification)

Juro flagged a confusion in the earlier draft: I described `{% docstring %}` as emitting "an `<ApiReference>` HTML block," which read like JSX-style invocation. **That's not how djc v1/v2 works.** Components are invoked via `{% component "name" %}` in templates, or `.render()` in Python — never as bare HTML tags like `<ApiReference>`.

The correct mechanism for `{% docstring "django_components.Component" %}`:

```python
# docs_site/apps/docs/templatetags/docs_extras.py
from django import template
from docs_site.apps.docs.components.api_reference import ApiReference
from docs_site.apps.docs.griffe_adapter import lookup_symbol  # uses our griffe extensions

register = template.Library()

@register.simple_tag(takes_context=True)
def docstring(context, dotted_path):
    symbol_data = lookup_symbol(dotted_path)  # returns the portable dict from §2.2
    return ApiReference.render(kwargs={"symbol": symbol_data}, context=context.flatten())
```

The `simple_tag` is registered with Django. When the template engine sees `{% docstring "x.Y" %}`, it calls the Python function, which calls `ApiReference.render(...)` (a regular djc Component class), and returns the resulting HTML string. The HTML is substituted into the page where `{% docstring %}` was. No JSX-style tag is ever emitted.

`{% example "fragments" %}` works the same way — a `simple_tag` that calls `ExampleCard.render(name="fragments")` and returns HTML.

This pattern is the bridge from "Django template tag syntax in markdown" to "djc component rendering." It uses entirely existing v1/v2 mechanisms.

#### 11.4.F `--8<--` audit — keep, with two raw-inject pages handled

Juro asked us to audit `--8<--` usage and find any non-fenced cases (raw text injection). Results:

| Use | Where | Inside fenced block? | What to do |
|---|---|---|---|
| `--8<-- "docs/examples/<name>/component.py"` | All `docs/examples/*/README.md` (18 instances) | **Yes** — inside ` ```djc_py ` fences | Keep `pymdownx.snippets` |
| `--8<-- "CODE_OF_CONDUCT.md"` | [docs/community/code_of_conduct.md](docs/community/code_of_conduct.md) | **No** — raw markdown injection | Keep `pymdownx.snippets` (handles both cases) |
| `--8<-- "LICENSE"` | [docs/overview/license.md](docs/overview/license.md) | **No** — raw text injection | Keep `pymdownx.snippets` |

`pymdownx.snippets` handles both fenced and raw injection out of the box — fenced-vs-raw is determined by context (what surrounds the `--8<--` line), not by configuration. We don't need a separate directive for the raw case. The two raw-inject pages keep working as-is.

**Design note on injection-protection:** Juro is right that fenced-injection is safer (the injected content can't be parsed as markdown/template syntax). We can adopt a project convention: "prefer to inject inside a fenced block; document raw injection as the rare exception." `code_of_conduct.md` and `license.md` are the rare exceptions — both inject stable, well-behaved markdown / plain text. No new mechanism needed.

**Decision on `--8<--` vs `{% example %}`** (open question §4 in the earlier spike): **option (1)** — keep `--8<--` for explicit "here is one specific file" inclusions; add `{% example %}` for the high-level "show component + page + live demo tabs" case. They serve different purposes.

#### 11.4.G Per-page validation

I mentally walked each real page through the revised pipeline:

**`your_first_component.md`**: ~15 code fences (each gets verbatim-wrapped by the pre-pass, then highlighted by Pygments in Pass 2), 3 admonitions (handled by `markdown.extensions.admonition` in Pass 2), ~12 cross-page links to `../reference/api.md#django_components.Component`. The `#django_components.Component` anchor becomes `#Component` after the anchor-scheme deviation (§7.2); a post-Pass-2 link-rewriter handles internal links, the legacy alias (§7.2) handles external. Verdict: **zero source changes**.

**`adding_js_and_css.md`**: admonitions with titles, nested ordered lists with indented code, nested admonitions inside list items. All handled by `markdown.extensions.admonition` in Pass 2. Verdict: **zero source changes**.

**`examples/fragments/README.md`**: `--8<-- "docs/examples/fragments/component.py"` inside a `djc_py` fence — handled by `pymdownx.snippets` in Pass 2. Image with relative path — markdown-native. Verdict: **zero source changes**. We can later add `{% example "fragments" %}` to embed the live demo, but the existing content already renders correctly.

#### 11.4.H Concrete prototype

The cheapest follow-up is a ~200-line proof of concept:

```python
# docs_site/apps/docs/management/commands/build_one.py

import re
from pathlib import Path

import markdown
from django.template import Engine, Context
from django.core.management.base import BaseCommand
from pymdownx.slugs import slugify

MD_EXTENSIONS = [
    "abbr", "admonition", "attr_list", "codehilite", "def_list", "tables",
    "md_in_html", "toc",
    "pymdownx.magiclink", "pymdownx.details", "pymdownx.highlight",
    "pymdownx.inlinehilite", "pymdownx.snippets", "pymdownx.tabbed",
    "pymdownx.superfences", "pymdownx.tasklist", "pymdownx.emoji",
]
MD_EXTENSION_CONFIGS = {
    "pymdownx.highlight": {"anchor_linenums": True},
    "pymdownx.snippets": {"check_paths": True, "base_path": "."},
    "pymdownx.tabbed": {"alternate_style": True},
    "pymdownx.tasklist": {"custom_checkbox": True},
    "pymdownx.magiclink": {
        "repo_url_shorthand": True,
        "user": "django-components",
        "repo": "django-components",
    },
    "toc": {"permalink": "¤", "slugify": slugify(case="lower")},
}

FENCE_OPEN_TICK = re.compile(r'^(\s*)```')
FENCE_OPEN_TILDE = re.compile(r'^(\s*)~~~')

def protect_code_fences(md_source: str) -> str:
    """Pre-pass. Wrap every ``` and ~~~ fence in {% verbatim %}...{% endverbatim %}.
    Production version also handles indented code and inline code spans."""
    out = []
    in_fence = False
    fence_char = None
    for line in md_source.splitlines(keepends=True):
        if not in_fence:
            m = FENCE_OPEN_TICK.match(line) or FENCE_OPEN_TILDE.match(line)
            if m:
                fence_char = "```" if "`" in line else "~~~"
                out.append("{% verbatim %}\n")
                out.append(line)
                in_fence = True
                continue
            out.append(line)
        else:
            out.append(line)
            if line.lstrip().startswith(fence_char):
                out.append("{% endverbatim %}\n")
                in_fence = False
    return "".join(out)

def render_django(md_source: str, engine: Engine, ctx: dict) -> str:
    """Pass 1. Run the verbatim-protected source through Django's template engine."""
    template_src = "{% load docs_extras component_tags %}\n" + md_source
    return engine.from_string(template_src).render(Context(ctx))

def md_to_html(md_source: str) -> tuple[str, list]:
    """Pass 2. python-markdown -> HTML + TOC."""
    md = markdown.Markdown(extensions=MD_EXTENSIONS, extension_configs=MD_EXTENSION_CONFIGS)
    html = md.convert(md_source)
    return html, md.toc_tokens

class Command(BaseCommand):
    def handle(self, *args, **opts):
        src = Path("docs/getting_started/your_first_component.md").read_text()
        protected = protect_code_fences(src)
        expanded = render_django(protected, Engine.get_default(),
                                 ctx={"version": "0.150.0"})
        html, toc = md_to_html(expanded)
        # Pass 3: DocPage.render(content_html=html, toc=toc, ...)
        Path("site/test.html").write_text(html)
```

This skeleton is enough to:
1. Prove the fence-protection pre-pass works.
2. Prove arbitrary Django tags in markdown work (including `{% component %}`).
3. Prove `pymdownx.*` extensions render existing pages correctly.
4. Prove `md_in_html` correctly passes through block-level HTML emitted by Pass 1.
5. Time the per-page render (likely <100ms for `your_first_component.md`).

#### 11.4.I Gotchas

1. **Inline code and indented blocks — what the scanner has to handle.** The prototype above only handles ` ``` ` fences. Production pre-pass needs to also escape:
    - **`~~~`-fenced blocks** (also valid in `pymdownx.superfences`) — trivial extension of the fence regex.
    - **Inline code spans** (`` `...` ``) — within a single line, find each backtick-delimited span. The cleanest way to protect a `{% ... %}` pattern inside backticks is to rewrite it to `{% templatetag openblock %}... {% templatetag closeblock %}` only when inside backticks. ~20 LOC.
    - **4-space indented code blocks** — **Juro asked how we'd detect these. Short answer: we essentially don't have to.** A scan of every `.md` file in `docs/` for true standalone 4-space indented code (preceded by a blank line, not inside a list item or admonition) found two non-trivial sources:
        - [docs/community/people.md](docs/community/people.md) — Jinja-template HTML inside `mkdocs-macros` loops. This page becomes a native Django-template page in the new pipeline (see §2.3) and stops being markdown.
        - [docs/reference/*.md](docs/reference/) — mkdocstrings `:::` directives with their `options:` blocks. These are replaced entirely by our `{% docstring %}` mechanism.
        Both cases evaporate during the migration. No other true 4-space indented code blocks exist in our docs today.

    **Decision:** the scanner handles `` ` ``-style fences, `~~~`-style fences, and `` ` `` inline spans. We adopt a **project convention: use fenced blocks for code; raw 4-space indented code is not supported.** A CI guardrail (one regex, run on changed `.md` files) flags any incoming PR that introduces indented code. **If** we ever need to support it, the scanner gains a ~30-line post-process: walk the source, find each contiguous run of `>=4-space-indented` lines preceded by a blank line and NOT preceded (within ~50 lines back) by a list-item or admonition opener, and wrap that run in `{% verbatim %}`. Cheap, but not worth pre-emptively building.

    Total scanner with the cases we DO need: ~80 LOC, well-bounded.

2. **`{% verbatim %}` nesting.** Django supports `{% verbatim somename %}...{% endverbatim somename %}` for nesting. We use a unique name per fence so nested cases (a fence whose content shows the verbatim tag) still work. Edge case but worth supporting.

3. **`--8<--` snippet expansion timing.** `pymdownx.snippets` runs in Pass 2 (after Django). A Pass-1 directive (e.g. `{% include_file %}`) that emits a fenced block with `--8<--` inside it will get further-expanded in Pass 2 — usually desired, occasionally a surprise. Mitigate by documenting the order.

4. **Magic-link expansion.** `pymdownx.magiclink` runs in Pass 2 and rewrites `#1593` → GitHub issue link. If a directive emits text containing `#1593` (or anything resembling a GitHub ref), it will be auto-linked. Mostly desired. Edge case: a directive that emits Python attribute access that happens to look like a ref. None of the planned tags emit such content.

5. **TOC inclusion of directive-emitted headings.** If `{% docstring %}` emits markdown headings (`## Component`), the `toc` extension picks them up. If it emits raw HTML headings, `toc` may or may not, depending on `md_in_html` config. **Recommendation:** have `{% docstring %}` emit markdown headings, not HTML. Simpler, TOC-friendly, slug-controllable.

6. **Slug parity.** Material configures `pymdownx.slugs.slugify(case="lower")`. We use the same in `MD_EXTENSION_CONFIGS["toc"]["slugify"]` so heading anchors match today's exactly. A/B test on one page to confirm before committing to the migration.

7. **Dev-mode reload.** In `runserver` mode, every request to a `.md` URL re-runs the whole pipeline. Fine for dev (~100ms latency). For build mode, cache the markdown→HTML output per content file, keyed on `(source_hash, directive_outputs_hash)`. Directives can change without source changing (e.g. `{% version %}`), so both need to be in the cache key.

8. **Build-time context.** Directives like `{% version %}` depend on the build-time version. The Django render gets a small build context dict at expansion time (version, site_url, edit_base_url). Pure function of (directive args, build context). No HTTP request needed.

#### 11.4.J Conclusions

1. **Architecture works** with one shape correction: the pipeline is **pre-pass + Django template engine + python-markdown + DocPage layout**, not "regex directive expander + ...". The shift was driven by Juro's question about `{% component %}` in markdown.
2. **`python-markdown` stays.** Switching to `markdown-it-py` would force rewriting ~100 admonitions and every snippet; the speed gain doesn't pay back.
3. **Every Django tag works in markdown** — there's no distinction between "directives" and "Django tags." Docs tags (`{% example %}`, `{% docstring %}`, `{% include_file %}`, `{% version %}`, `{% image %}`) are convenience `simple_tag` definitions; djc tags work because Django loads its template library.
4. **`<ApiReference>`-style tags are NOT used.** Components are invoked via `simple_tag` implementations that call `Component.render(...)` in Python. Bridges Django template tag syntax to djc rendering using only v1/v2 mechanisms.
5. **`--8<--` stays for code-block injection.** Two existing raw-inject pages (`code_of_conduct.md`, `license.md`) are handled by the same `pymdownx.snippets` extension. No new directive needed.
6. **Zero source changes** required to existing markdown for it to render under the new pipeline. New tags are additive.
7. **Gotchas are tractable.** The biggest is the fence-protection scanner (~80 LOC, well-bounded).

#### 11.4.K When to build the prototype — Phase 0, before Phase 1

**Juro asked when this gets built.** The prototype is its own micro-phase before Phase 1 of the migration plan (§5):

```
Phase 0 — Pipeline proof of concept  (~2-3 days)   <-- the prototype
Phase 1 — Scaffold + one section     (~1-2 weeks)
Phase 2 — {% example %} tag          (~1 week)
Phase 3 — Rest of markdown pages     (~1-2 weeks)
Phase 4 — API reference              (~1 week)
Phase 5 — Search, versioning, social (~1 week)
Phase 6 — Cutover                    (~2 days)
```

It's not a real "phase" in the project-management sense — it's the executable deliverable that closes the §11.4 spike. The point is to validate the pipeline shape with the cheapest possible code before sinking 1-2 weeks of effort into Phase 1's scaffolding (Django app structure, management command, multi-page build, etc.).

**Phase 0 build:** the ~200-LOC skeleton from §11.4.H. Single management command, one file, throws everything else away. Run against:
- [docs/getting_started/your_first_component.md](docs/getting_started/your_first_component.md) — covers admonitions, multi-language fences, cross-page links, code-fence titles
- [docs/examples/fragments/README.md](docs/examples/fragments/README.md) — covers `--8<--` snippets, images

**Phase 0 success criteria:**
- Output HTML matches the current mkdocs build for `your_first_component.md` modulo class names. Heading anchors are identical (slug-parity A/B test, §11.4.I gotcha 6).
- A small synthetic `{% component %}` call placed inside a test markdown page actually renders to HTML — confirms the "every Django tag works in markdown" claim from §11.4.D.
- Per-page render time recorded, extrapolated to ~200 pages.
- Confirm `md_in_html` passes the Pass-1 block-level HTML through Pass 2 untouched.

**If Phase 0 passes**, §4.7 is locked, the prototype becomes the seed of Phase 1's `docs_site/apps/docs/management/commands/build_docs.py`, and Phase 1 starts.

**If Phase 0 fails** (most likely cause: a markdown extension we configured doesn't compose with `md_in_html` the way we expect, or slug-parity breaks for non-trivial headings), we revise §4.7 before committing engineering effort to Phase 1. The whole prototype is ~200 LOC, so a complete rewrite costs days, not weeks.

The point of Phase 0 is the same as any spike: **shift the riskiest unknown to the cheapest moment.**

### 11.5 Griffe reuse + per-API-kind renderers

- **Status:** **complete** (2026-05-31). Full write-up in [DESIGN_djc_docs_site_spike_11_5.md](DESIGN_djc_docs_site_spike_11_5.md).
- **Verdict:** GO. Griffe gives us every machine-readable fact we need across all 21 distinct API renderings. Five real gaps (cross-refs, runtime-set class attributes, argparse metadata, NamedTuple `_fields`, raw HTML in docstrings) all have known mitigations totalling ~50-200 LOC. Our two existing griffe extensions port verbatim.
- **Key findings:**
    - 21 distinct rendered kinds fold into **12 distinct Django templates** plus a small set of shared sub-components (`SignatureBlock`, `SourceCodeLink`, `ParametersTable`, `DocstringBody`, `CrossRef`, `SymbolTypeBadge`).
    - The Discovery → Rendering contract is a portable `ReferencePage` Python dict (JSON-serializable), validating the §2.2 split.
    - Concrete file layout proposed: per-kind components live under `apps/docs/components/reference/entries/`; the discovery layer is a sibling `apps/docs/discovery/` (not under `components/`), enforcing the §2.2 split by directory placement.
    - **Anchor scheme is leaf-name-only.** `#django_components.component.Component` → `#Component` (the entire dotted path drops, not just the root). Within a single reference page, leaf names are already unique, and the intermediate path is internal detail anyway. The hand-typed `[X](api.md#dotted.path)` form in 397 docstring links gets swept in the same codemod into a resolver-friendly form.
    - **`signature_crossrefs` is load-bearing** (712 auto-linked types on one page). Reimplementing it requires parsing griffe's `Expr` tree per parameter and looking each `ExprName` up against a merged inventory (project symbols + `objects.inv` from Python stdlib and Django).
    - **Docstring format that works in both IDEs and docs builds:** Google-style sections + a **two-syntax model** — single backticks for code/literals/mentions (monospace in both worlds, never linkified, no ambiguity), bracket cross-refs `[X][]` (autorefs-style) when a link is the point. Backticks carry the daily authoring load; cross-refs degrade to plain text in IDE hover (accepted tradeoff for keeping backticks unambiguous). Matches mkdocstrings+autorefs ecosystem syntax, so our `objects.inv` round-trips.
    - **Codemod scope (structural blockers only, per Juro):** ~975 hand-typed `[X](api.md#django_components.Y)` links across `src/` (397) + `docs/` (578) → bracket cross-refs `[X][LeafName]`, no per-link judgment, no downgrades to backticks. Plus ~129 markdown-style `**Args:**` → true Google `Args:`. **Advanced syntaxes in existing docstrings (31 Material admonitions, 1 raw HTML) are NOT swept** — that's a separate later judgment call. The §11.2 convention is the target for new docstrings going forward. Roughly a one-day precursor PR.
    - Thematic grouping for `api.md` is a worthwhile migration opportunity — `ReferencePage` already supports arbitrary entry ordering, so grouping classes by theme (Core / Slots / Registration / Media / Errors) is ~60 min of curation.
    - **`reference.py` (1160 lines)** is rewritten, not refactored — one PR per generator (12 of them).
    - Three mkdocstrings options are dead weight today and can be dropped: `preload_modules`, `summary`, `show_submodules`.
- **First concrete step:** build the Layer 1 + Layer 2 prototype against `exceptions.md` (smallest distinct page, 3 entries, all kind `class`). ~1 day. Validates contract before scaling to 11 more kinds.
- **Feeds into.** §4.3, §2.2 (the data → renderer split), §7.2 (anchor scheme codemod).

### 11.6 Replicating "simple/clean way to define content"

**Status:** spike complete 2026-05-31. Recommendation: **the markdown side is mostly free** because `python-markdown` + `pymdownx.*` (locked in by §11.4.B) covers every directive actually used in `docs/`. The real §11.6 work isn't markdown extensions — it's the **Material theme affordances** (copy button, edit-on-GitHub, page metadata, section-index pages) that authors don't write directives for but that *contributors and readers feel*. Plus formalizing the **new docs-only Django template tags** the migration introduces.

- **Original question.** What's the inventory of authoring affordances Material/mkdocs gives us today, and what's the minimum we need to keep contributors happy?
- **Why.** Every directive and every theme feature is a contributor convenience. If the new system feels like a downgrade to authors, we'll regret it.

#### 11.6.A Reframing — "directives" is the wrong frame

The original spike statement implied the answer is a list of markdown directives. The inventory below shows that's not quite right:

1. Almost everything we use is already free from `python-markdown` + `pymdownx.*` (§11.4.B). The migration doesn't lose those.
2. The features authors *don't* see but contributors and readers *feel* — copy button, edit-on-GitHub, breadcrumbs, dark/light toggle, page metadata — are not markdown directives. They're theme behavior. Material gives them away for free; our renderer must deliberately rebuild each.
3. The migration **introduces new authoring idioms** (`{% example %}`, `{% docstring %}`, `{% include_file %}`, `{% version %}`, `{% component %}`). These count as part of the "simple/clean way to define content" story and need a spec.

So the spike covers three categories: **(B)** markdown directives, **(C)** theme/UX affordances, **(D)** new Django template tags.

#### 11.6.B Markdown-directive inventory (verified counts, 2026-05-31)

Scope: human-authored markdown under `docs/getting_started/`, `docs/concepts/`, `docs/guides/`, `docs/community/`, `docs/overview/`, `docs/upgrading/`, `docs/releases/`, `docs/plugins/`, `docs/examples/*/README.md`, `docs/migrating_from_safer_staticfiles.md`. Auto-generated `docs/reference/` excluded (covered by §11.5).

##### Heavy use — keep

| Directive | Use count | Where | Provides | Verdict |
|---|---|---|---|---|
| Fenced code blocks (info-string includes language) | 633 fences across ~11 languages (most-used: `python` 174, `django` 145, `py` 130, `djc_py` 53, `sh` 33, `html` 26, `bash` 26, `htmldjango` 24, `txt` 17) | All over | `pymdownx.highlight` + `pymdownx.superfences` + Pygments | **Keep** — free from extensions |
| Fenced-block `title="..."` | 39 occurrences | `concepts/`, `examples/`, `guides/` | `pymdownx.highlight` | **Keep** — free |
| Admonitions (`!!! note`, `!!! info`, `!!! warning`) | 80 total: `warning` 32, `info` 28, `note` 18. 7 titled (e.g. `!!! info "Title"`) | All over | `markdown.extensions.admonition` | **Keep** — free |
| Tasklists `- [ ]` / `- [x]` | 59 | `community/`, `concepts/`, `getting_started/` | `pymdownx.tasklist` (config `custom_checkbox: true`) | **Keep** — free |
| `pymdownx.snippets` (`--8<-- "..."`) | 20 (all inside `djc_py` fences in `docs/examples/*/README.md`) | `examples/` | `pymdownx.snippets` | **Keep** — free. Already audited in §11.4.F. Convention: prefer fenced inclusion; raw inclusion documented as the exception (the two raw cases live in `code_of_conduct.md` and `license.md`) |
| Pipe tables | ~36 table rows, 6-8 tables | Scattered | `markdown.extensions.tables` | **Keep** — free |
| Same-page anchor links `[X](#anchor)` | 35 | `concepts/advanced/` mostly | core markdown | **Keep** — free |
| Same-section cross-page links `[X](other.md)` | 59 | `guides/`, `examples/` | core markdown | **Keep** — free |
| Cross-page anchor links `[X](path.md#django_components.Y)` | **773 total in `docs/`, of which 578 target the `#django_components.*` API anchor scheme** | `concepts/` 26 files, `getting_started/` 8, `examples/` 4, `guides/` 3, `overview/` 2, `community/` 2 | core markdown | **Keep — but codemod required.** Same anchor-scheme change as §11.5's 397 in `src/`. See §11.6.F |

##### Configured today but unused — keep enabled, document them

These are currently enabled in `mkdocs.yml` but never used in source. **Decision (per Juro): keep them enabled.** The reason they're unused isn't that we don't need them — it's that contributors (Juro included) didn't know they existed and chronically reached for the affordance they did know about (admonitions). Dropping them codifies the discoverability gap. Keeping them, plus building a "Markdown syntax reference" docs page (§11.6.B.2), surfaces the options.

| Directive | Count | Decision |
|---|---|---|
| `pymdownx.tabbed` (`=== "Tab"`) | 0 today | **Keep** — Juro will want tabs for multi-tool install instructions (pip / uv / poetry), API code examples by language, etc. |
| `pymdownx.details` (`??? note` / `???+ note`) | 0 today | **Keep** — collapsible asides. Juro: "I chronically used notes (admonitions), because I didn't know that expandable details sections were a thing." |
| `pymdownx.inlinehilite` (`` `:python: code` ``) | 0 today | **Keep** — inline syntax highlighting for short snippets where a full fence is overkill |

##### Verified droppable

Only one item really drops:

| Directive | Count | Decision |
|---|---|---|
| `pymdownx.magiclink` (`#1234`, `@user` auto-link) | 0 | **Drop**. Verified: changelog and release-notes pages use *full* GitHub URLs generated by `gen_release_notes.py`, not the magic-link short form. Explicit full URLs are more grep-friendly anyway |

##### Configured but unused — keep (low cost, small surface)

These add nothing if unused but cost nothing to keep enabled. Contributors who reach for them get what they expect:

| Directive | Count | Decision |
|---|---|---|
| `pymdownx.emoji` (`:warning:`) | 0 in scope | **Keep** — costs nothing |
| `attr_list` (`{ #id .class }`) | 0 real (38 false positives are Django template comments `{# ... #}`) | **Keep** — see §11.6.B.3 for what it does |
| `def_list` (term/definition) | 0 | **Keep** — see §11.6.B.3 |
| `abbr` (`*[HTML]: HyperText Markup Language`) | 0 | **Keep** |
| `md_in_html` (`<div markdown=1>...</div>`) explicit | 0 explicit uses | **Keep** — load-bearing for the Pass-1 → Pass-2 handover in §4.7 even though authors don't write it directly |
| `[TOC]` marker | 0 | **Keep** the `toc` extension (heading slugification + anchor generation); the explicit `[TOC]` marker is rarely used but free |
| Frontmatter | 1 file (`docs/README.md`, out of scope) | **Build into the pipeline** — see §11.6.I item 2 for the schema and library choice |

##### Available pymdownx capabilities we haven't enabled yet (catalog)

Juro asked for an enumeration so we know what's reachable when we want a new affordance. The full pymdownx-extensions list is at <https://facelessuser.github.io/pymdown-extensions/>; below is the subset that's plausible for our use case. None are enabled today; all are opt-in.

| Extension | What it does | When we might want it |
|---|---|---|
| `pymdownx.superfences` custom fences | Custom fence languages routed to validators / renderers (e.g. `mermaid`, `vegalite`, custom) | Enable when we add Mermaid (see below) |
| `pymdownx.arithmatex` | LaTeX math via `$inline$` and `$$display$$`, rendered client-side by KaTeX/MathJax | When a real equation appears in docs |
| `pymdownx.tilde` | Strikethrough `~~text~~` (CommonMark/GFM-compatible) and subscript `~sub~` | Cheap to enable; useful for "deprecated" markers |
| `pymdownx.caret` | Superscript `^sup^` and `^^insert^^` | Rarely needed; opt-in |
| `pymdownx.mark` | Highlight `==text==` | "Pay attention to this" emphasis |
| `pymdownx.smartsymbols` | Auto-replace `-->` `<--` `(c)` `(tm)` `1/2` with proper Unicode | Light cosmetic improvement |
| `pymdownx.keys` | Keyboard chords `++ctrl+a++` → styled `<kbd>` | Useful for IDE shortcut tables |
| `pymdownx.critic` | Track-changes-style markup `{++added++}` `{--removed--}` `{~~old~>new~~}` `{>>comment<<}` `{==highlight==}{>>note<<}` | **Promising for "what changed in v0.150"** style release notes; inline diff explanation |
| `pymdownx.blocks.admonition` | Newer block-style admonitions (`/// note`) replacing `!!! note` syntax | Consistency with the `pymdownx.blocks.*` family; transitional |
| `pymdownx.blocks.definition` | Definition lists via `/// define` syntax | Alternative to `def_list` — Juro encountered this form in pymdown docs |
| `pymdownx.blocks.details` | Collapsible blocks via `/// details` | Newer form of `pymdownx.details`; same idea, different syntax |
| `pymdownx.blocks.html` | Block-level HTML wrapper `/// html | div ...` | Cleaner than raw `<div markdown=1>` |
| `pymdownx.blocks.tab` | New block-style tabs `/// tab | Tab Title` | Alternative to `pymdownx.tabbed` |
| `pymdownx.blocks.caption` | Figure captions `/// caption` | Cleaner than raw HTML `<figcaption>` |
| `pymdownx.pathconverter` | Rewrites relative paths in HTML output (absolute ↔ relative) based on a base path | When emitting markdown that references assets from another path context — relevant for `{% include_file %}` |
| `pymdownx.progressbar` | `[=75% "label"]` styled progress bars | Niche; rarely useful for docs |
| `pymdownx.snippets` (already enabled) | `--8<-- "path"` inclusions | Already used in 20 places |

**Mermaid is a separate setup** — it's NOT a pymdownx extension itself. The pattern is: enable `pymdownx.superfences` with a custom fence definition that routes ` ```mermaid ` blocks to a `<pre class="mermaid">` wrapper, then load `mermaid.min.js` on the page. Standard recipe in mkdocs-material docs.

**No CI guardrail.** Earlier draft proposed flagging "dropped" directives in CI; that proposal is rejected because almost nothing actually drops. The healthy invariant is now "all the standard pymdownx affordances work; the Markdown syntax reference page tells you what's available."

#### 11.6.B.2 The "Markdown syntax reference" docs page

A new page in `docs/community/` (or `docs/contributing/`) that lists every authoring syntax available, with a one-line example. Solves the discoverability problem that produced the "I didn't know that was possible" reactions during this spike.

Sections, roughly:

1. **Standard markdown** — bold, italic, lists, blockquote, headings, links, images, fenced code, tables.
2. **Admonitions** — `!!! note` / `!!! info` / `!!! warning` with optional `"Title"`.
3. **Collapsible sections** — `??? note` (closed) / `???+ note` (open).
4. **Tabs** — `=== "Tab Title"` blocks.
5. **Code blocks** — language, `title="..."`, line numbers, line highlighting.
6. **File includes** — `--8<-- "path"` inside a fence (default) or naked (rare exception).
7. **Cross-page links** — `[text](path.md#anchor)` for ordinary links; `[X][]` bracket cross-refs for API symbols.
8. **Docs sugar tags** — `{% example %}`, `{% docstring %}`, `{% include_file %}`, `{% version %}`, `{% image %}`.
9. **Embedded components** — `{% component "name" args... %}` for ad-hoc demos.
10. **Tasklists** — `- [x]` / `- [ ]`.
11. **Available-but-not-enabled** — short note pointing at `mkdocs.yml` for which other pymdownx extensions are reachable (mermaid, math, strikethrough, critic, etc.) and how to enable them in a PR if a real need arises.

This page is also the source of truth for the conventions enforced by §11.10's guardrails (e.g. "raw 4-space indented code is not supported; use fenced blocks").

#### 11.6.B.3 attr_list, def_list, PathConverter — what they do

Brief explanations Juro asked for:

**`attr_list`** (built into python-markdown). Adds HTML attributes to markdown elements via `{ key=value }` syntax. Examples:

```markdown
# My heading { #custom-id .my-class }
[click me](https://example.com){ target=_blank rel=noopener }
![chart](chart.png){ width=400 .figure-tight }
A paragraph with custom CSS class.
{ .callout-warning }
```

Useful when you need a specific anchor ID, want a link to open in a new tab, or want to tag an element with a CSS class for styling. Not currently used in our docs (the 38 grep hits were all Django template comments `{# ... #}`), but small and free.

**`def_list`** (built into python-markdown). Renders definition lists. Two equivalent syntaxes depending on which extension is loaded:

- **`markdown.extensions.def_list`** (the classic):
    ```markdown
    Term
    :   Definition body, indented four spaces.
    ```
- **`pymdownx.blocks.definition`** (newer, block-style):
    ```markdown
    /// define
    Term
    : Definition body.
    ///
    ```

Both produce `<dl><dt>Term</dt><dd>Definition</dd></dl>`. The `/// define` form Juro encountered in pymdownx docs is the second variant. For our purposes either works; pick one when we add the syntax reference page.

**`pymdownx.pathconverter`**. Rewrites relative paths inside the rendered HTML so they resolve correctly from a different base path. Example: a markdown file at `examples/fragments/README.md` references `./images/foo.png`. If we render it into a page served from `/concepts/fragments/`, the path is broken. `pathconverter` rewrites `./images/foo.png` to `../../examples/fragments/images/foo.png` (or to an absolute URL) so links survive the relocation. Most useful when one file is included into another via `--8<--` or `{% include_file %}` and the inclusion crosses directory boundaries. Worth enabling once we hit a real path-rewriting case; pre-emptive enabling is fine since it's a no-op when paths don't move.

#### 11.6.C Material theme affordances — not markdown, but contributor/reader UX

These are what Material gives us by default and what our `DocPage` component (§4.1) has to deliberately rebuild. None of them are markdown directives — they're CSS + JS the theme ships.

| Affordance | Today via Material | What we need to ship | Effort |
|---|---|---|---|
| **Code copy button** | `content.code.copy` Material feature | `~50 LOC JS`: click handler on code blocks, `navigator.clipboard.writeText`, transient "Copied" tooltip | S — half a day |
| **Edit-on-GitHub button** | `content.action.edit` Material feature + `edit_uri` in mkdocs.yml | One slot in `DocPage` component; URL is `f"{REPO_EDIT_URL}/{content_relpath}"`; the `version` context already has the branch | S — trivial |
| **View-source button** | `content.action.view` Material feature | Same shape as edit button; targets `/blob/` instead of `/edit/` | S — trivial |
| **Heading anchor link on hover** | `toc.permalink: "¤"` (configured) | Already handled by `python-markdown` `toc` extension with the same config | Zero |
| **Page metadata: "Last updated" + authors** | `git-revision-date-localized` + `git-authors` (excluded from `reference/*`, `changelog.md`, `code_of_conduct.md`, `license.md`) | `subprocess.run(["git", "log", "-1", "--format=%cs|%an", path])` at build time; cache per content file | S |
| **Section-index pages** (clicking a section in the sidebar opens its index page) | `navigation.indexes` Material feature; used by `docs/plugins/index.md` and `docs/examples/index.md` | The sidebar nav component routes `Section/` to `Section/index.md` if it exists | S — sidebar logic |
| **Breadcrumbs** | Material default | `DocPage` slot rendered from the nav YAML | S |
| **Sticky TOC sidebar** | Material default | CSS `position: sticky` on the right-rail TOC; scroll-spy JS to highlight current heading | S — well-trodden |
| **"Back to top" button** | `navigation.top` Material feature | One JS scroll listener + a button that fades in past a threshold | S |
| **Dark/light theme toggle** | Material palette config (3 modes: auto / light / dark) | CSS variables + JS toggle. **This is the theming prerequisite already called out in §11.1.G.1** | M (lives in its own phase) |
| **Instant page loads / prefetching** | `navigation.instant` + `navigation.instant.progress` Material features | SPA-style routing is non-trivial; **defer** to post-cutover or skip entirely | (deferred) |
| **Heading TOC follow (auto-scroll TOC)** | `toc.follow` Material feature | Scroll-spy JS, same as sticky TOC | S — folds into TOC component |
| **Navigation expand / sections / tabs / tracking** | `navigation.expand`, `navigation.sections`, `navigation.tabs`, `navigation.tracking` Material features | Sidebar component design choices; covered by §11.11 UI spike | M (in §11.11 scope) |
| **Search modal + suggestions + highlighting + share URL** | `search.suggest`, `search.highlight`, `search.share` Material features | Covered by §11.1.G search v1 work | (already scoped) |

**Net.** Everything in this table except dark/light toggle and search is a small, well-bounded JS/CSS task. Total effort across the row: ~3-5 days of focused frontend work. None individually scary; the cost is breadth, not depth.

#### 11.6.D New Django template tags the migration introduces

These are the *new* "simple/clean way to define content" the migration adds on top of markdown. They're not replacing anything in today's docs — they're how authors will compose content in the new world.

Per §11.4.D, every tag in markdown is just a Django template tag. The five canonical "docs sugar" tags:

| Tag | Purpose | Implementation | Spec |
|---|---|---|---|
| `{% example "name" %}` | Embed a code+rendered-output tabbed widget for an `examples/<name>/` directory. Replaces today's static GIFs | `simple_tag` calls `ExampleCard.render(name=...)` returning HTML. See §4.2 | `{% example "fragments" %}` |
| `{% docstring "django_components.Component" %}` | Embed the rendered API reference for a symbol. Replaces today's `::: dotted.path` for one-off mentions outside `reference/*` pages | `simple_tag` calls `lookup_symbol(...)` then `ApiReference.render(...)`. See §11.4.E | `{% docstring "django_components.Component" %}` |
| `{% include_file "path" %}` | Inject a file's contents as a fenced code block (the *safe* form). The unsafe raw form remains as `pymdownx.snippets`' `--8<--` for the two existing exceptions | `simple_tag` reads the file, emits a fenced code block with a language inferred from extension | `{% include_file "docs/examples/fragments/component.py" %}` |
| `{% version %}` | Insert the current package version at build time | `simple_tag` returns the version string from `pyproject.toml` | `{% version %}` |
| `{% component "name" args... %}` | The general djc component invocation — works in markdown because Django loads the `django_components` template library | (Already exists in djc; nothing new to build) | `{% component "table" rows=... %}` |

These five plus arbitrary Django core tags (`{% if %}`, `{% for %}`, `{% with %}`, `{% url %}`) are the full authoring surface. No "directives" — just Django tags.

**One additional tag worth scoping:** `{% image %}` — a thin wrapper around `<img>` that handles responsive variants, alt-text checks, and version-relative paths. Reduces author boilerplate for the 30-ish images we have. Optional for v1.

#### 11.6.E mkdocs plugins audit (the §11.6 piece of §11.9's broader plugin work)

Plugins that affect *authoring* (vs deploy/CI):

| Plugin | Used today | Replacement |
|---|---|---|
| `mkdocs-macros` | 1 page (`docs/community/people.md`) renders Jinja2 with `force_render_paths` opt-in | This page becomes a **native Django template page** — bypasses the markdown pipeline entirely, renders `people.yml` through a Django template. Covered by §11.4 and §2.3 (this is one of the two cases §11.4.I gotcha 1 calls out where 4-space indented code disappears) |
| `mkdocs-include-markdown` | 1 use in `docs/README.md` (out of scope; root README isn't part of the built site) | Drop. If we ever need it, `{% include %}` works |
| `awesome-nav` | Nav YAML — no `.pages` files actually found in `docs/` | Replace with our own nav YAML schema consumed by the sidebar component |
| `autorefs` | Only used by `reference/*` pages (mkdocstrings). 0 hits in human-authored docs | Replaced by §11.5's cross-ref resolver (which fires only on `[X][]` bracket form) |
| `gen-files` | Calls `docs/scripts/{setup,reference,gen_release_notes}.py` | Replaced by Django management commands during `docs-build` |
| `markdown-exec` | Configured but 0 `exec="true"` usage found in scope | Drop |
| `git-revision-date-localized` / `git-authors` | Adds "Last updated"/authors footer per page | Reimplement as build-time subprocess + cache. See §11.6.C |

`mkdocstrings`, `mike`, `redirects`, `minify`, `social`, `search` are tracked by §11.5, §11.7/§4.6, §7.5, §11.10, §11.1, §11.1 respectively. Plugin audit for non-authoring plugins continues in §11.9.

#### 11.6.F Cross-page link codemod scope (extends §11.5)

§11.5 found **397 hand-typed `[X](api.md#django_components.Y)` cross-refs** in `src/` docstrings. This inventory found **578 more** in human-authored `docs/` markdown targeting the same `#django_components.*` anchor scheme:

- 26 files in `docs/concepts/`
- 8 files in `docs/getting_started/`
- 4 files in `docs/examples/`
- 3 files in `docs/guides/`
- 3 files in `docs/templates/`
- 2 files in `docs/overview/`
- 2 files in `docs/community/`

**Total: ~975 cross-refs across `src/` + `docs/`** that the anchor codemod must sweep. The pattern, regex, and sweep logic are the same; the §11.5 spike's plan extends naturally — same codemod, two source roots.

The remaining 195 cross-refs (773 - 578) target non-`django_components.*` anchors (template tag names like `#fill`, settings like `#dirs`, CLI commands). These don't carry the dotted prefix today, so the anchor-scheme change is a no-op for them. **No sweep needed for these 195.**

**Sweep policy** (revised per Juro's clarification, supersedes the earlier "per-link judgment" framing in [§11.4 of the §11.5 spike file](DESIGN_djc_docs_site_spike_11_5.md)): **every hand-typed link converts to bracket cross-ref form `[X][]`, full stop.** Authors wrote them as links because they meant them as links — densely cross-linking every mention of a public API symbol is a deliberate authoring style, not noise to be undone. The codemod is mechanical: extract link text + leaf name, produce `[text][LeafName]` (or `[X][]` when text == leaf name). No per-link interpretation.

The earlier proposal (downgrade some links to backticks based on "is this navigational?") is **rejected**. Backticks remain reserved for cases where the author explicitly chose *not* to link in the first place — the sweep doesn't introduce them.

**Decision:** treat the 578 docs-side links as part of the same precursor PR as §11.5's 397. Both run before the docs-site migration starts so the migration itself stays purely additive.

#### 11.6.G Per-item specs (the kept set)

Shortest possible spec per surviving directive, in case anyone needs to recall syntax later.

- **Code fence:** ` ```<language> [title="..."] ` opens, ` ``` ` closes. Supported languages cover what Pygments knows; we own `djc_py` via `pygments_djc`.
- **Admonition:** `!!! <type>` at column 0, followed by indented body (4 spaces). Optional title: `!!! info "Title"`. Types in use: `note`, `info`, `warning`. Other types render with sensible defaults.
- **Tasklist:** `- [ ]` (unchecked) or `- [x]` (checked) inside a list. Renders with `custom_checkbox: true`.
- **Snippet:** `--8<-- "path/from/repo/root"` inside a fenced code block (default form) or naked (raw injection — used in two pages, document as the exception).
- **Same-page anchor link:** `[text](#anchor)`. Anchor is the auto-slugged heading.
- **Cross-page link:** `[text](relative/path.md)` or `[text](relative/path.md#anchor)`. After the §11.6.F codemod, API anchors use the leaf-name-only scheme.
- **Pipe table:** standard CommonMark/GFM.
- **Image:** `![alt](relative/path.png)`. We may layer `{% image %}` on top for the common `<img>` wrapper.
- **Bold / italic / code / lists / blockquote:** standard markdown.

That's the entire authoring surface for human-written docs. ~10 directives, all standard.

#### 11.6.H Decision matrix (summary)

| What | Decision | Cost |
|---|---|---|
| `pymdownx.snippets`, `pymdownx.highlight`, `pymdownx.superfences`, `pymdownx.tasklist` | **Keep** — load-bearing, all in active use | Zero (already free via §11.4.B) |
| `admonition`, `tables`, `md_in_html`, `toc`, `codehilite` | **Keep** | Zero |
| `pymdownx.tabbed`, `pymdownx.details`, `pymdownx.inlinehilite` | **Keep + document** — Juro wants these available (e.g. tabbed for "pip / uv / poetry" install variants, details for collapsible asides). The reason they're unused today is discoverability, not lack of need. Build a "Markdown syntax reference" docs page (§11.6.B.2) | Zero |
| `pymdownx.magiclink` | **Drop** — verified replaceable with full URLs (no source uses `#1234` shorthand) | Negative — remove from extension list |
| `pymdownx.emoji`, `attr_list`, `def_list`, `abbr` | **Keep** — small, harmless, and individually useful when a contributor reaches for them | Zero |
| Material directive features (buttons, annotations, mermaid, math, keys, critic, mark, smartsymbols, tooltips) | **Available, opt-in** — not enabled today but pymdownx ships them. See the "Available pymdownx capabilities" catalog in §11.6.B so we know what's reachable when we want a new affordance | Zero (until we enable) |
| Code copy button | **DIY rebuild** — high-impact reader UX | S |
| Edit-on-GitHub + view-source buttons | **DIY rebuild** — trivial | S |
| Page metadata (last-updated, authors) | **DIY rebuild** | S |
| Section-index pages | **DIY rebuild** | S |
| Breadcrumbs, sticky TOC, back-to-top, scroll-spy | **DIY rebuild** | S each |
| Dark/light toggle | **DIY rebuild — in its own phase** (§11.1.G.1) | M |
| Instant page loads (SPA routing) | **Defer or skip** — non-trivial, low impact | n/a |
| `mkdocs-macros` (1 page) | **Rewrite as native Django template** | S |
| `mkdocs-include-markdown` (root README only) | **Drop** | Zero |
| `markdown-exec`, `awesome-nav`, `mkdocs-include-markdown` plugin configs | **Drop** from new pipeline | Zero |
| `git-revision-date-localized` / `git-authors` | **Reimplement** as subprocess + cache | S |
| New tags: `{% example %}`, `{% docstring %}`, `{% include_file %}`, `{% version %}`, `{% image %}` | **Build** — additive | M (each is a `simple_tag` calling a Component) |
| Anchor-scheme codemod | **Run as precursor PR before migration** | M (extends §11.5's 397 to ~975 total) |

#### 11.6.I Risks and open items

1. **Discoverability over guardrails.** The earlier draft proposed a CI guardrail flagging "dropped" directives. That guardrail is **dropped** because the §11.6.B revision keeps almost everything enabled. The healthy invariant is now positive: the "Markdown syntax reference" docs page (§11.6.B.2) lists what's available, so contributors find affordances by reading the page rather than learning them by hitting a lint warning. The smaller residual concern — that someone introduces a feature we deliberately decided against (e.g. embedded JS scripts in markdown) — is handled by the link / anchor / schema guardrails in §11.10, not by a markdown-syntax linter.
2. **Frontmatter — we control the schema.** Juro asked who defines the fields. Answer: **we do**. There's no preset schema baked into python-markdown or pymdownx; both leave frontmatter to a separate library. The two relevant libraries:
    - **`python-frontmatter`** — standalone library. Parses YAML / TOML / JSON frontmatter delimited by `---` (or `+++` for TOML). Returns `(metadata: dict, body: str)`. Schema is whatever we define.
    - **`markdown.extensions.meta`** — python-markdown's built-in. Parses simpler `Key: Value` header lines (not YAML). More limited but zero new dependency.
    Recommendation: use `python-frontmatter` (YAML, standard format). Define a small fixed schema in Phase 1: `title` (override H1), `description` (meta description), `hide_toc` (hide right-rail TOC), `redirect_from` (list of old paths), `layout` (override the DocPage layout for the rare custom page), `tags` (reserved for future tag pages). Strict mode: unknown fields fail the build. Today only 1 file uses frontmatter (`docs/README.md`, out of scope), but **scoping frontmatter parsing into Phase 1** is cheap (~50 LOC) and forward-compatible.
3. **Section-index pages.** Two `index.md` files use Material's `navigation.indexes` feature. Make sure the new sidebar component supports the "clickable section header that opens its index page" pattern from day one; it's a small but easy-to-miss UX detail.
4. **Pre-existing inconsistencies.** The 578 cross-refs in `docs/` weren't audited for consistency before. Some may target anchors that don't exist (silent broken links in mkdocs strict mode if `unrecognized_links: warn`). The codemod is a good moment to run the link checker (§11.10) and fix orphans in the same PR.
5. **Advanced syntaxes in `src/` docstrings stay untouched during this migration.** Earlier drafts proposed sweeping Material admonitions (31 in `src/`) into blockquotes and raw HTML into markdown italics for IDE-friendliness. **Rejected per Juro:** that's a judgment call for later, not for the migration codemod. The precursor PR fixes only **structural blockers**: anchor scheme (§11.6.F), the 129 `**Args:**` → true Google `Args:` pseudo-section alignment (§11.5), and any docstring patterns the discovery layer can't parse. Material admonitions, raw HTML, and other docs-build-only constructs in docstrings remain as written until a later, separate decision. The convention recommendation in [§11.2 of the §11.5 spike file](DESIGN_djc_docs_site_spike_11_5.md) (single backticks, bracket cross-refs, prefer-markdown defaults) is the **target state for new docstrings going forward**, not a sweep target for existing ones.

#### 11.6.J Feeds into

- **§4.7** (markdown pipeline) — confirms the locked-in extension set; no changes needed to §4.7 itself.
- **§11.5** (anchor codemod) — scope widens from 397 src/ links to ~975 total (src/ + docs/). Same codemod, two source roots.
- **§11.1.G.1** (theme as a prerequisite for search) — confirmed by the §11.6.C theme-affordance ledger; dark/light toggle lands first, search later.
- **§11.9** (mkdocs plugin audit) — this spike covered the *authoring-facing* plugins; the remaining infrastructure plugins (`gen-files`, `git-*`, `social`, `minify`, `redirects`, `awesome-nav`) are still §11.9's scope.
- **§11.10** (guardrails) — link / anchor / API-symbol / example-page / cross-version / snapshot guards live there. No markdown-syntax linter (§11.6 revision dropped that proposal in favor of the discoverability page §11.6.B.2).
- **§11.11** (UI inspiration) — the sidebar / breadcrumbs / dark-mode design is §11.11's domain; §11.6 only confirms scope.

### 11.7 mike internals + bootstrap-from-tags script

- **Status:** **complete** (2026-05-31). Full write-up in [DESIGN_djc_docs_site_spike_11_7.md](DESIGN_djc_docs_site_spike_11_7.md).
- **Verdict:** GO. Vendor ~270 LOC from `mike` (almost entirely `versions.py`), skip the rest. Two-command shape from §4.6 holds; concretized with idempotency stamps, redirect-mode aliases, and `docs_versions.toml` schema. No upstream standalone `mike` is coming.
- **Key findings:**
    - **Juro's outreach got a reply.** [`jimporter/mike#255`](https://github.com/jimporter/mike/discussions/255), 2026-01-25 → reply 2026-01-26. jimporter is "thinking about" a standalone mike but "nothing definite." He independently agrees the `gh-pages`-branch design is "a hack" from a 2016 GitHub Pages constraint. Bottom line: we vendor, we don't wait.
    - **What we vendor (~270 LOC, dep-free except `verspec`):** `mike/versions.py` (209 LOC — `Versions` + `VersionInfo` classes, JSON round-trip, `LooseVersion`-based sort, alias coalescing — verified against our 127 tags), `mike/templates/redirect.html` (15 LOC, alias redirects), and the *algorithm* (~50 LOC) of `mike/themes/*/js/version-select.js`, rewritten as a Django `version_picker` component.
    - **What we skip:** `git_utils.py` (431 LOC, gh-pages branch plumbing — irrelevant when committing to `master`), `mkdocs_plugin.py`, `mkdocs_utils.py`, `driver.py`, `arguments.py`, `server.py` (mkdocs/CLI adapters), `jsonpath.py` (only used by `mike props`, niche feature we don't need). `commands.py` is reference-only — useful for understanding mike's deploy contract (read manifest → mutate → write files + manifest → commit), but not portable because of gh-pages coupling.
    - **Aliases: switch from `symlink` to `redirect` mode.** mike supports three modes (symlink / copy / redirect). We use `symlink` today on `gh-pages` (verified: `latest/` is a mode-`120000` git symlink blob). With `master` as the deploy source, symlinks become a Windows-clone footgun and a `git status` annoyance. Redirect mode uses mike's 15-line `redirect.html` per page; tiny disk cost, universal compatibility.
    - **`docs-build-all` is a thin orchestrator.** `for tag in matched_tags: git worktree add ... && uv run docs-build --version=<tag> ... && git worktree remove ...` + single manifest-merge at end. Idempotency via a per-version `_build_info.json` stamp that records `{tag, source_sha, built_at, builder_version}` — `docs-build-all` skips dirs whose stamp matches the tag's commit SHA.
    - **`docs_versions.toml` schema:** `pattern` regex, `include`/`exclude` lists, `oldest`/`newest` bounds, optional `aliases` overrides. Default pattern handles both 2-part (`0.124`) and 3-part (`0.139.1`, `0.140.0`) tags — verified.
    - **`docs/v/versions.json` is byte-identical to mike's output.** That means the Material `provider: mike` selector can read our manifest during the transition window, and any third-party tooling that consumes versions.json keeps working.
    - **Cost estimate:** `docs-build` per release is ~90s (one version). `docs-build-all` over the existing 40+ historical versions is a one-time ~1-hour run.
    - **`docs-build-check` confirmed as a CI gate** (per Juro). Validates `docs/v/` ↔ manifest consistency, alias resolution, `_build_info.json` sanity, and intra-version internal links. Runs in PR CI on `docs/v/` touches and on release-deploy as a post-commit guard. ~150-200 LOC; lands with `docs-build-all`.
    - **No pre-commit hook** (per Juro). Docs builds are a CI concern; local devs use `uv run docs-serve` for live preview.
    - **License audit complete** (spike §12). Entire stack is permissive: MIT / BSD-2/3 / ISC / Apache-2.0 / HPND. No copyleft anywhere. Non-MIT deps we pick up: `mike` (BSD-3), `griffe` (ISC), `verspec` (BSD-2 OR Apache-2.0), `python-markdown` (BSD-3), `pygments` (BSD-2), `jinja2` (BSD-3), `pillow` (MIT-CMU). All compatible with our own MIT license. Vendored `mike/versions.py` keeps top-of-file attribution + a `_vendor/LICENSE-mike.txt`. CI license check recommended on dep updates (tracks with §11.10).
- **Risks called out for execution:**
    - Pre-release tags (`0.150.0rc1`) untested; verify before introducing the convention.
    - Worktree cleanup-on-failure must use `try/finally` + a defensive `git worktree prune` at the start of each run.
    - **Older versions migration is explicitly deferred to after Phase 7** (per Juro). We don't pick rebuild / freeze / hybrid until the new builder has gone through end-to-end (scaffold → cutover → search v2). The walker supports all three options without code change; the choice lands as TOML config when we have the data to decide.
- **Recommended first step:** ~1 day. Vendor `versions.py`, write a stub `docs-build` that writes `docs/v/<version>/index.html` + manifest, prove the 3-tag round-trip (`0.148.0`, `0.149.0`, `0.150.0 --alias=latest`) on a scratch branch, open in a browser, confirm the version picker switches versions. If that works the rest is execution.
- **Feeds into.** §4.6 (chosen approach codified), §11.8 (deferred to after Phase 7; the walker is option-agnostic so deferral is safe), §11.10 (`docs-build-check` is one guardrail among many).

### 11.8 Migrating older docs versions

- **Status:** **complete** (2026-05-31). Full write-up in [DESIGN_djc_docs_site_spike_11_8.md](DESIGN_djc_docs_site_spike_11_8.md). Final policy decision is **deferred to after Phase 7** per [§11.7 spike §7](DESIGN_djc_docs_site_spike_11_7.md); this spike's contribution is the data that pre-loads the decision.
- **Recommended default plan:** **freeze + import all** at Phase 6 cutover. One PR copies `origin/gh-pages` → `master/docs/v/`, materializes `latest/` as redirects (not symlinks), and switches GitHub Pages source. After cutover, only new versions land via the new builder. Post-Phase-7, selectively rebuild recent versions if data argues for it.
- **Key findings (data behind the recommendation):**
    - **57 entries** on `gh-pages` today (56 release versions `0.92`-`0.150.0` + `dev`). Manifest skips `0.140.0` and `0.147.0` (releases that were never deployed) — nothing to migrate for those.
    - **The bloat fear was a working-tree artifact.** `gh-pages` working tree is 1.0 GB *expanded*, but the **bare git repo is only 114 MB**. Material's CSS/JS bundle (~5 MB) is byte-identical across versions and deltifies to effectively a single copy. Master `.git` goes from 108 MB → ~220 MB after import. Acceptable.
    - **URL structure has changed twice**, and these are the lines that determine where freeze-vs-rebuild can land:
        - **0.110 → 0.111:** flat (`latest/CHANGELOG/`, `latest/slot_rendering/`) → nested (`latest/concepts/`, `latest/guides/`). Pre-0.111 must be frozen — rebuilding produces different URLs.
        - **0.123 → 0.124:** reference page structure changes from mkdocstrings deep tree (`reference/django_components/Component/`) to per-topic-page model. Modern URL skeleton starts here.
    - **From 0.124 onward URL drift is additive**, not renaming. But within "stable era," each tag's `reference.py` differs from current — rebuilding 0.124 with current `reference.py` produces different pages. To rebuild any historical version, the walker must use that *era's* `reference.py`, which is engineering risk.
    - **If hybrid were chosen**, the realistic cutoff is **0.148.0** (3 versions). Below: freeze. At/above: rebuild possible. Not worth the orchestration for 3 versions — **freeze-all is cheaper**.
    - **Anchor scheme change** (`#django_components.X` → `#X`, per [§11.5 spike §7](DESIGN_djc_docs_site_spike_11_5.md)) is irrelevant for frozen versions (their HTML doesn't change). For any rebuild, the legacy-alias mechanism we'd build for current docs applies uniformly.
    - **`latest/` symlink → redirect-file replacement** at import is a ~50-LOC Python script that lifts mike's [`templates/redirect.html`](https://github.com/jimporter/mike/blob/master/mike/templates/redirect.html) per page.
    - **Org-rename in old sitemaps** (`emilstenstrom.github.io` → `django-components.github.io`, pre-0.139) is not a real problem — GitHub's username-rename redirect keeps inbound URLs alive, and `robots.txt` only advertises `latest/sitemap.xml` anyway.
- **Risks called out for execution:**
    - Master clone size jumps from ~108 MB to ~220 MB `.git`. Document in CONTRIBUTING; `--depth 1` and `--filter=tree:0` work for contributors.
    - **The `dev/` deploy on the new system needs a decision.** Today it's rewritten on every master push — that's a lot of churn if it commits to `master/docs/v/dev/`. Likely answer: build `dev/` without committing to git, or commit as separate orphan. Defer to CI-workflow wiring. **(Resolved in feature 10.7: `dev/` is built fresh into `/v/dev/` on every deploy and added to the served manifest, but never committed - no churn.)**
    - Old Material JS bundles ship with whatever CVEs the era had. Mitigation: optional Phase 7+ sweep to identify and selectively rebuild only versions with critical bundled-JS vulns. **(Done in feature 10.4 - see [`cve_audit_10.4.md`](cve_audit_10.4.md): the asv report's jQuery 3.3.1 / Bootstrap 3.1.1 are the carriers; residual risk accepted, no rebuild triggered.)**
- **Recommended next move:** **none yet.** Execute the import at Phase 6 cutover. Until then, this spike is documentation.
- **Feeds into.** §4.6 (default Phase 6 cutover plan), §11.7 (the walker is option-agnostic; this spike picks the cheap default).

### 11.9 mkdocs plugin replacement audit

- **Status:** **complete** (2026-06-01). Full write-up in [DESIGN_djc_docs_site_spike_11_9.md](DESIGN_djc_docs_site_spike_11_9.md).
- **Verdict:** GO. Every plugin in [mkdocs.yml](mkdocs.yml) maps to a concrete replacement. **Total new LOC across the infrastructure plugins exclusively owned by §11.9** (`social`, `minify`, `redirects`, `gen-files`, `awesome-nav`, `markdown-exec`, `include-markdown`, `mkdocs-macros`, `git-revision-date-localized`, `git-authors`) is **~500–700 LOC**, dominated by social-card generation.
- **Key findings:**
    - **Plugin inventory is exhaustive.** [§11.9 spike §1](DESIGN_djc_docs_site_spike_11_9.md) lists every plugin from [mkdocs.yml](mkdocs.yml) with its owner spike (§11.1, §11.5, §11.6, §11.7, §11.10, or §11.9 itself) and final disposition. No plugin is unaccounted for.
    - **Social cards: replace Material's 1800-LOC plugin with Playwright + a Django `OgCard` component (~230 LOC total).** Playwright is already a dev dep (E2E tests); marginal cost is near zero. CSS-driven card template beats Material's `Pillow + cairosvg + Jinja sandbox + thread-pool composition` stack on both LOC and contributor DX. **Side benefit: drops the only LGPL-3.0 dep in our docs stack (`cairosvg`, pulled transitively by the Material social plugin).**
    - **`redirects`: static `<meta http-equiv="refresh">` HTML stubs at the moved URL paths.** GitHub Pages serves them correctly. Belt-and-braces design (meta refresh + JS replace + canonical link + robots noindex). ~30 LOC.
    - **`minify`: switch from `htmlmin2` (the lib `mkdocs-minify-plugin` uses; community fork of abandoned `htmlmin`) to `minify-html` (Rust-backed, MIT, 10–100× faster, well-maintained).** ~20 LOC.
    - **`gen-files`: replaced by Django management commands chained into `docs-build`.** Three scripts collapse: `setup.py` becomes one import, `reference.py` is subsumed by §11.5's Discovery layer, `gen_release_notes.py` keeps ~80% of its parser but swaps the mkdocs-virtual-fs API for `pathlib.write_text`.
    - **`awesome-nav`: drop the plugin (0 `.pages` files exist), ship a ~50 LOC YAML loader.**
    - **`git-revision-date-localized` + `git-authors`: subprocess `git log` + `lru_cache` per file (~100 LOC combined).** CI workflows need `fetch-depth: 0` instead of the default shallow clone.
    - **`mkdocs-macros` (1 page): rewrite the page as a native Django template** that bypasses the markdown pipeline. ~40 LOC view + template.
    - **`include-markdown`, `markdown-exec`: drop entirely** (verified 0 in-scope usages in §11.6.E).
- **License audit across the full docs stack (per Juro's §11.7 feedback):** with the social-card change, **all docs deps become permissively-licensed.** MIT/BSD-2/BSD-3/ISC/Apache-2.0/MIT-CMU only. The only non-permissive license today (`cairosvg`, LGPL-3.0) is removed transitively by replacing Material's `social` plugin. `mike` (BSD-3) remains vendored per §11.7 with attribution. See [§11.9 spike §3](DESIGN_djc_docs_site_spike_11_9.md).
- **`docs-build-check` CLI gate (per Juro's §11.7 feedback):** third entrypoint alongside `docs-build` and `docs-build-all`. Runs the full build to a temp dir + every §11.10 guardrail, writes nothing to disk, exits non-zero on any failure. Wired into GitHub Actions as a PR check. Skips slow steps (social cards, minify) by default; `--full` flag enables them. ~80 LOC + reuses every existing piece. See [§11.9 spike §4](DESIGN_djc_docs_site_spike_11_9.md).
- **Implementation order is staged by migration phase:** Phase 1 lands `gen-files` / `awesome-nav` / `redirects` / `mkdocs-macros` rewrite (the plugins needed before any page can render). Phase 3 lands `git-*` and drops `markdown-exec` / `include-markdown`. Phase 5 lands `social` + `minify`. Phase 6 deletes `mkdocs.yml`.
- **Recommended first concrete step:** during Phase 1, wire `emit_redirects()` and `run_minifier()` as post-build passes. Both are ~50 LOC combined, zero dependency on the rest of the pipeline, prove the post-build pass shape social cards will reuse. Fail-cheap validation of the build dir layout.
- **Feeds into.** §2.1, §4.1, §4.6, §4.8, §5 / Phase plan, §7 (license), §11.10.

### 11.10 Guardrails (dead-link detection, broken anchors, schema drift)

- **Status:** **complete** (2026-06-01). Full write-up in [DESIGN_djc_docs_site_spike_11_10.md](DESIGN_djc_docs_site_spike_11_10.md).
- **Verdict:** GO. Every check `mkdocs --strict` performs today has a concrete replacement; we gain seven additional guards (API symbol coverage, example-page contracts, anchor alias coverage, cross-version drift, snapshot regression, pygments lexer alias validation, HTML well-formedness) that mkdocs can't run. **Total ~840 LOC** across the harness, `SiteIndex`, and 17 in-build guards. The 18th guard (external links) is deliberately offloaded to a weekly out-of-band workflow to avoid blocking PRs on third-party uptime.
- **Key findings:**
    - **Severity model: two levels (error / warning).** `docs-build` emits both to stderr and proceeds (Phase-1 reality). `docs-build-check --strict` (the CI default) upgrades warnings to errors and exits non-zero. Matches today's `mkdocs --strict` semantics.
    - **A shared `SiteIndex` (~120 LOC) walks every built HTML file once** and exposes links, anchors, images, scripts, redirect stubs, and headings to every post-build guard. Replaces the 5× repeated HTML parsing a naive implementation would do; centralizes the parser dependency on `lxml.html` (already permissively licensed).
    - **The pre-pass code-fence scanner from §11.4.C gets a validator twin (§3.2)** that catches unclosed fences and malformed `--8<--` blocks *before* Django sees the page. Saves a whole class of confusing downstream errors.
    - **Cross-version link checking is a flat file-exists check.** Because the §4.6 strategy persists `docs/v/<version>/` to `master`, a link from `/v0.151/foo` to `/v0.150/bar` is validated by `Path.exists()` on the on-disk version dir. No server lookup, no manifest cross-reference.
    - **API symbol coverage runs both directions** (§3.4 forward = `{% docstring %}` → griffe; §3.5 reverse = public API → `{% docstring %}` coverage). The reverse direction catches new exports added without docs.
    - **Snapshot test starts small (3 pages) and grows to 8.** Reduces churn during Phases 1–3. Re-snapshot via `pytest --snapshot-update`. Lives in `tests/test_docs_snapshots.py`, runs alongside `docs-build-check` not inside it.
    - **External links → lychee in a weekly workflow.** A flaky Discord invite or PyPI 503 should not block PRs. Separate `docs-external-links.yml` workflow on a cron.
- **Implementation order is staged by migration phase:** Phase 1 lands the three minimum-viable guards (template_render, fence_validator, internal_link + anchor sharing one SiteIndex). Phase 2 adds example_contract + anchor_alias. Phase 3 adds the rest of the pre-build/build-time guards. Phase 5 adds cross_version_link, asset, redirect_target, versions_manifest, snapshot. Phase 6 deletes `mkdocs build --strict` from `release-docs.yml`.
- **Recommended first concrete step:** during Phase 1, build the `SiteIndex` + template_render + internal_link + anchor as a single PR. These three guards (with the shared index) are the bare minimum to ship a single-section preview safely.
- **Feeds into.** §4.7 (markdown pipeline pre-pass + Pass 1), §4.8 (build CLI flags), §9.8 (mkdocs strict equivalence), §11.4 (pre-pass), §11.5 (Discovery public-api set), §11.7 (versions.json schema), §11.9 §4 (CI gate host).

### 11.11 UI / layout inspiration

**Status:** spike complete (2026-06-01, revised). See [DESIGN_djc_docs_site_spike_11_11.md](DESIGN_djc_docs_site_spike_11_11.md) for the full deep dive. Headline decisions:

- **Nested sidebar, two levels deep.** Top sections (`Concepts`, `Reference`, etc.) hold either flat items or sub-groups (`fundamentals/`, `advanced/`); never both. Sidebar nav YAML schema in spike §3.2.
- **Top nav names kinds of pages, not docs sections** (revised per Juro). Slots: `logo (→ landing) · Docs · Examples · Plugins · Blog (future) · ⌘K · version · theme · GitHub`. Sidebar handles within-kind nav; top nav handles between-kind.
- **URL move under `/docs/` (NEW).** Content currently at root (`/concepts/`, `/reference/`, `/guides/`, `/getting_started/`, `/overview/`, `/upgrading/`, `/community/`, `/releases/`) moves under `/docs/`. `/examples/` and `/plugins/` stay at root. Inbound links handled via the existing redirect machinery (§11.9.2.5). Full move map in spike §4.2.
- **Landing page at `/` is NEW, deferred to Phase 9 (codesign).** A thin ~50 LOC placeholder ships in Phase 1 so the top-nav taxonomy works end-to-end; the real landing page is its own phase at the end of the migration plan, framed as iterative back-and-forth between Juro and the agent. Lives outside `DocPage` chrome. See spike §4.4 + main doc §8 (Phase 9).
- **Release Notes folds into Docs**, not a top-nav slot.
- **Three-column layout at 1280px outer max.** Sidebar 280px, content max 720px, right TOC 240px. Breakpoint behaviour in spike §2.
- **Light theme is the default; dark theme is a peer.** `auto` mode follows `prefers-color-scheme`. Two complete OKLCH token sets (light + dark), neither derived from the other. Toggle wiring deferred to §11.1.G.1.
- **Code blocks: minimal.** Language label top-right, copy button on hover. No terminal-chrome decoration. 3px left accent border for hierarchy.
- **One unified `CodeTabs` component** serves three authoring affordances: `{% example %}` widget, `pymdownx.tabbed` multi-variant blocks (install variants etc.), and code-fence `title="..."` single-label tabs. One CSS rule, one component, three entry points. Spec in spike §6.4.
- **Eight design tokens** (surfaces, foreground, accent, link, semantic admonitions, typography, spacing, shadows), all OKLCH-defined. Full table in spike §10.
- **Accent colour decision deferred to Juro:** muted teal (continuity with current Material teal) or Django bottle-green (dogfoods the Django brand). Either works; one token swap.
- **Two static HTML mocks** in spike §11: concept page + API reference page. Both render via a single `DocPage` Django chrome component.
- **First concrete step:** Phase 1 ships `DocPage` chrome + a thin ~50 LOC landing placeholder (1-2 days), then content rendering builds on top. The real landing page is Phase 9.

References surveyed: `~/repos/agents/safe-ai-factory/web` (read in full), [VitePress](https://vitepress.dev) (substituting for Vuese, whose domain expired), [Pagefind](https://pagefind.app), and Pydantic's docs (in-repo nav-inspo reference).

**Feeds into.** §4.1 (DocPage + LandingPage chrome), §4.2 (URL stability — the `/docs/` move records here), §5 (sized Material-polish loss), §11.1.G.1 (theme prereq), §11.5 (per-kind component styling envelope), §11.6 (CodeTabs serves pymdownx.tabbed too), §11.6.C (theme-affordance styling), §11.9 (Material palette + redirect machinery handles `/docs/` move), §11.10 (guardrail: every old URL must have a redirect file), Phase 1, Phase 5.

### 11.12 SEO and AIO audit — what features to implement

**Status:** spike complete (2026-06-01). See [DESIGN_djc_docs_site_spike_11_12.md](DESIGN_djc_docs_site_spike_11_12.md) for the full deep dive. Headline decisions:

- **SHIP across the board.** Current site is weaker than people think: prod emits only viewport, site-level description, canonical. No OG, no JSON-LD, no per-page description, no `llms.txt`, no `.md` companion URLs.
- **Three load-bearing additions:** `llms.txt` + `llms-full.txt` (~120 LOC), `.md` companion URLs at every `<path>.md` (~50 LOC, highest-leverage AIO win), per-page description + OG + JSON-LD (`BreadcrumbList` + `TechArticle`) (~80 LOC).
- **Three near-free wins:** per-version `noindex` for `/v0.x/` where `x < latest`, Lighthouse CI on a 5-page sample, custom 404 with embedded Pagefind search.
- **Three deferrals:** `tags.json` template-DSL manifest (post-cutover, coordinated with §11.5), full a11y audit (§11.11 follow-up), real-time SEO monitoring (operational).
- **AI-bot policy: default-allow** (Juro confirmed 2026-06-01). `robots.txt` explicitly allows GPTBot, ClaudeBot, anthropic-ai, Google-Extended, PerplexityBot, CCBot. Codified in `community/ai_bot_policy.md`.
- **Three migration-time gotchas captured:** anchor-migration deprecation timer (12 months) interacts with §7.2; canonical-URL strategy changes (versioned pages canonical to `/latest/`, not self); single-`<h1>` invariant guarded by §11.10.
- **Total surface:** ~880 LOC, of which ~330 must land in Phase 1 (head block, canonical, description, JSON-LD, front-matter, `.md` companion).
- **First concrete step:** Phase 1 unified `DocPage` `<head>` block (~150 LOC) sets the SEO floor; everything else builds on top.

**Feeds into.** §4.1 (DocPage `<head>` block), §4.6 (per-version `noindex`), §7.2 (anchor deprecation timer), §11.9 (sitemap + robots.txt + social cards behaviour scoped), §11.10 (single-h1 + alt-text + JSON-LD + anchor-deprecation + example-rename guardrails), §11.11 (chrome metadata threading), Phase 1, Phase 3 (alt-text + ai_bot_policy.md content), Phase 5.

---

**Original spike framing (preserved for reference):**

- **Question.** What is the full set of SEO (search-engine optimisation) and AIO (AI / LLM optimisation — making content well-formed for retrieval-augmented agents and AI search engines) features the new docs site should ship with? §11.10 §10.2 explicitly deferred this from the guardrails spike; we need to close it before Phase 5 (or before cutover, whichever comes first) so we don't ship the new site weaker than the current Material build.

- **Why.** Three pressures converge here:
    1. **Inbound discovery is how new users find us.** Material's defaults (sitemap, canonical, OG, robots, basic JSON-LD) work well today; if the new site drops any of those silently, we regress organic traffic.
    2. **The migration is the moment to fix the long-standing UX gap with AI search.** Tools like ChatGPT search, Perplexity, Claude, Phind, and Kagi Assistant retrieve docs pages directly. Pages that surface a clean canonical URL, structured headings, machine-readable code-block language tags, and llms.txt land well; pages that don't, don't. We have a one-shot opportunity to design for this rather than retrofit.
    3. **URL stability and the anchor-scheme change (§7.2) interact with search-engine memory.** Old anchors will linger in the index for months; we need a deliberate plan, not just hope.

- **Method.** Inventory + decision per item. Group A is SEO ("classic" search engines); Group B is AIO (LLM consumers); Group C is shared infrastructure that benefits both.

    **Group A — SEO**
    1. **Canonical URLs.** Confirm every page emits `<link rel="canonical">` pointing to `/latest/<path>` for the current version (so old versions don't compete with current). Decide what `/v0.149/` etc. canonicalise to — themselves, or `/latest/`? Material defaults to "self"; reconsider.
    2. **Sitemap.** `sitemap.xml` at site root, `<lastmod>` from git, only `/latest/` entries listed (avoid sitemap-bloat from versioned pages). Materially affects crawl budget.
    3. **`robots.txt`.** Allow `/`, disallow `/v0.x/` for `x < latest` to keep historical versions out of fresh index (but still reachable). Validate against Google's robots tester.
    4. **OG / Twitter cards.** Auto-generated per page (title, description, OG image). Description comes from the page's first paragraph or front-matter `description:`. OG image: per-page social card (continue Material's social plugin behaviour, but using Playwright at build time — see §11.9 §2.4).
    5. **Page titles.** `<title>` is `Page · Section · django-components` (current pattern). Confirm this in the new layout's `<head>` block.
    6. **Meta description.** Same source as OG description. 155 char cap.
    7. **Structured data (JSON-LD).**
        - `SoftwareSourceCode` schema for the project on `/latest/` home, `getting_started/`, and API reference pages.
        - `BreadcrumbList` on all content pages.
        - `Article` / `TechArticle` on concept and guide pages.
        - `HowTo` on the `examples/` pages where it fits.
        - **Question:** does Google still surface JSON-LD on developer docs, or only e-commerce / recipe / event? Verify before investing.
    8. **Heading hierarchy.** Exactly one `<h1>` per page, sequential `<h2>`/`<h3>`. The migration breaks this if `DocPage` chrome inserts an outer `<h1>` while content also opens with `# Heading` → two h1s. Lint this in §11.10 guardrails (file a follow-up to that spike).
    9. **Image alt text.** Every `![](img)` has alt. Currently inconsistent. Guardrail it.
    10. **Internal link density.** Cross-links between concept / reference / examples improve crawl coverage and dwell time. Audit current density; set a soft floor (e.g. each concept page links to ≥1 reference and ≥1 example, where applicable). Manual audit, not automated.
    11. **HTTPS + redirects from www → apex.** GitHub Pages handles HTTPS. Confirm the apex/www redirect chain on the published domain.
    12. **404 page.** Custom 404.html with search box and "did you mean X?" common-typo redirects.
    13. **Anchor migration (§7.2 interaction).** When we drop the `django_components.` prefix from anchors, the old anchors should remain as fallbacks for at least 6-12 months. Decision: emit `<a name="django_components.Component"></a>` aliases (already in §7.2), confirm Google honours both, set a deprecation timer.
    14. **Page speed / Core Web Vitals.** Static HTML with our own minimal CSS / JS should crush this. Confirm via Lighthouse in CI on a sampled set of pages. Budget: LCP < 1.5s on 4G, CLS = 0, INP < 100ms.

    **Group B — AIO (AI / LLM consumers)**
    1. **`llms.txt` at site root.** [Proposed spec by jeremyhoward](https://llmstxt.org/). A markdown index of the docs aimed at LLMs ingesting the site. We auto-generate from the nav YAML. Two variants:
        - `/llms.txt` — short index (titles + URLs + 1-line descriptions).
        - `/llms-full.txt` — concatenation of all content pages as markdown (so a model can ingest the whole site in one fetch). Mistakes here are cheap; the file is a hint, not authoritative.
    2. **`.md` companion URLs.** Every `/path/page/` also serves at `/path/page.md` returning the raw markdown source (with front-matter stripped, includes expanded, but no rendering). Pattern adopted by Stripe docs, Vercel docs, others. Cost is ~one extra file per page in the build; benefit is enormous for LLM ingestion. **Decide whether to ship.**
    3. **Structured headings in markdown source.** The `.md` companion URLs in (2) only pay off if our markdown is well-structured. Audit current `docs/` content for: missing top-level h1, h-tag jumps, code blocks without language tags, unlabelled lists. Tie into §11.10 guardrails.
    4. **Code-block language tags.** Every fence ` ``` ` declares a language. Critical for LLMs interpreting code samples. Already partially enforced via Pygments lexer guard (§11.10 §3.2.3). Extend the check to flag any unlabelled fences as errors.
    5. **Stable code-example IDs.** When an example is referenced (`See the form_submission example`), the URL anchor stays stable across versions. Otherwise LLMs cite anchors that 404 in newer versions. Audit naming.
    6. **Semantic HTML.** `<article>`, `<aside>`, `<nav>` used in `DocPage` chrome (§11.11 §3 already does this). Confirm during Phase 1.
    7. **`<meta name="description">` quality.** LLMs read this when summarising URLs. Auto-generated descriptions from the first paragraph are usually fine; flag pages where the first paragraph is a navigational paragraph or admonition.
    8. **No JS-required content.** Static HTML rendered server-side is already ✓ by the Option-B architecture. Just confirm: nothing critical loads via JS-only `fetch()` (the fragment examples in §4.4 use pre-rendered static files, so they're OK).
    9. **OpenAPI / schema export.** Not applicable (we're a library, not an API surface) — but for the django-components **template-tag DSL**, we could publish a JSON / TOML manifest of every tag's signature, args, kwargs, and slot-fill expectations. AI agents authoring templates would consume this. **Decide whether to ship a `tags.json` at site root.**
    10. **`robots.txt` for AI bots.** Decide: do we allow GPTBot, ClaudeBot, Google-Extended, PerplexityBot? Default-allow is the right call for a docs site that benefits from being well-known; document the policy in `community/`.
    11. **Markdown front-matter consistency.** If a model is fed `/page.md` (per item 2), front-matter (title, description, lastmod) helps it index correctly. Define a small schema and lint it.
    12. **AI-friendly URL conventions.** Lowercase, hyphen-separated, no extensions in URLs. Already mostly true; confirm during the §7.1 slug-algo audit.

    **Group C — Shared infrastructure**
    1. **Build-time fixed `<head>` block.** Single shared block (canonical, OG, JSON-LD, title, description, theme color, favicon, viewport) emitted per page from a centralised template; no per-page handcrafting. Define this in `DocPage` chrome (§4.1).
    2. **Per-page front-matter override.** When a page wants to deviate (custom OG image, custom description, `noindex`), front-matter wins. Define schema.
    3. **Per-version `<head>` differences.** Old versions get `<meta name="robots" content="noindex,follow">` so they don't compete with `/latest/` in search but are still followable. Wire into the versioned build (§4.6).
    4. **Lighthouse CI.** Run on every PR against a sampled set of pages. Block PRs that regress Performance / Accessibility / SEO / Best Practices below thresholds (Performance 95, others 100).
    5. **Search-engine indexing manifest.** A small `meta/indexing.json` enumerating intended-indexable URLs. Used by §11.10 guardrails to confirm we didn't accidentally make a major page `noindex`.

- **Deliverable.** A markdown sub-doc (`DESIGN_djc_docs_site_spike_11_12.md`) listing each item above with a verdict: **Ship / Skip / Defer / Spike further**. For each "Ship", a one-line implementation note pointing at the responsible component or build step.

- **Decisions this spike forces.**
    - Whether to ship `.md` companion URLs (Group B §2). Yes/no with cost estimate.
    - Whether to ship `llms.txt` and `llms-full.txt` (Group B §1). Yes/no.
    - Whether to ship `tags.json` (Group B §9). Yes/no.
    - Whether the AI-bot allow/disallow policy is documented (Group B §10).
    - Canonical-URL strategy for versioned pages (Group A §1).
    - Anchor-migration timeline (Group A §13).

- **Feeds into.** §4.1 (DocPage `<head>` block), §4.6 (per-version `noindex`), §7.2 (anchor migration), §11.9 (which plugins handle social cards / sitemap / robots), §11.10 (additional guardrails — single-h1, alt-text, language-tag).

- **Out of scope.**
    - Comprehensive accessibility audit (deferred to §11.11 follow-up).
    - Multi-language SEO (`hreflang`) — we don't have translated docs.
    - Real-time SEO monitoring (e.g. weekly Search Console audits). Operational concern, not part of this build.

---

## 12. UI / layout inspiration (quick capture)

Three references to honor when designing the visual system:

- **`~/repos/agents/safe-ai-factory/web`** — simple, elegant. Flat sidebar nav. The simplicity is the point. We can extend to nested nav without losing that.
- **[Vuese](https://vuese.org/)** — supports nested sidebar nav. Good reference for how to organize a hierarchy without it feeling heavy.
- **[Pagefind docs site](https://pagefind.app/)** — clean docs UX, good search overlay treatment.

Pull from these in the §11.11 spike; don't try to clone Material's exact aesthetic.

---

## 13. User prompts

### Initial

> let's explore in depth and write a design doc on what it would take to build docs site on top of our django-components.
>
> Biggest unknown for me is that the site is static, and django is server-side rendering. So we'd either need a way to:
> a) shim out Django for djc,
> b) Run Django and pre-render all content,
> c) set up live server with actual django server.
>
> Now, that's partially why I was avoiding / deferring this, because if we were on v2 or v3, it'd be already easier to drop Django dependency, which would make the static-site-generator use case trivial. But we're not there yet.
>
> To assess this, you'll need to explore the code examples in our docs. because while most of the docs examples could be made into static code, things might get trickier around the code examples around HTML fragment support. But I suppose even there the to-be-fetched-later fragments could be pre-rendered too. Check both code examples in docs, as well as the examples pages in the docs, and the live examlples when you run sampleproject.

### 1st feedback

> Agree to go with b) Pre-render with Django at build time. And I like the "Recommended first move" that you proposed. I believe we can do it after we do the additional spikes I ask for below, but the "render one page" as the north star is a good practical framing.
>
> I'll also need you to explore, one-by-one and in-depth (don't do the exploration yet, jsut capture all that needs to be done):
> - how the material-for-mkdocs's search works - whether we can reimplemnet it, or use some 3rd party solution for that. Also check the search that emil has implemented.
> - what changes have been made to zensical since I explored it on 25/01/2026 - and whether there's something else we'd gain moving to that (or whether they made it easier to customize, etc).
> - how we could make the Django server to generate static site. Maybe there's also already a solution for that?
> - can we still use markdown files to define the pages even if we built custom solution? How could we do that? Also, it might have to be not pure markdown, but Django templates, so that we can still insert our components, it then gets rendered by Django into markdown + html, and that untimately to HTML.
> - as for replacing mkdocs with custom solution, I believe we'd reuse griffe. which means we'd only need to rederfine/rebuild how individual kinds of APIs are rendered (eg Django template for the page that renders a CLI command, which then gets used by all CLI commands defined in the project, etc). All of this that I just said needs to be validated.
> - how we could replace other nicities like those mentioned in the "Simple/clean way to define content"
> - how to reimplement the versioning from mike? I believe we could achieve that in similar fashion, where we'd take the git tags from master branch of django-components, filter for some specific pattern (eg `v?\d+.\d+(\d+)?`), with options to manually exclude / include tags or set minimum (oldest) or maximum (latest) tags/commits, and the script would go over our git, and for each version it'd generate the site? maybe a bit differently when scrutinize more deeply, but along similar gist (eg maybe we save to master a special commit with the version-specific build and save it in master, so master would have N versions under `docs/`, eg `docs/v/0.135.0/`, etc). Also in the past I asked the author of the versioning library whether the versioning logic can be used without mike but dunno if I ever got a response, so definitely check that out too. 
> - Also capture that one reason why I want to do this migration is because we're pinning pygments to old version because of mkdocs, but security advisory is asking us to upgrate pygments, so there's a conflict.
> - For an inspiration for the UI, layout, check out `~/repos/agents/safe-ai-factory/web`. It has simpler layout (flat sidebar nav - tho we can make it nested, I see Vuese supports nested sidebar), but I like it's simplicity / elegance. Basically it's similar to Vuese (which is also a good example of how the UI can work.
> - unresolved - how to migrate older docs versions?
> - Also we'll need to go over the mkdocs plugins we use today and consider whether and how to replace them. And the same for guardrails (eg dead link detection) - so that our new website is as safe and fails loudly in CI if something breaks.
>
> regarding your initial design docs and the section 2.2 where you mention how we generate the "::: dotted.name lines for mkdocstrings to consume" - I believe this can be split in two - because in the old docs we hard-code it to the mkdocstring syntax. but we can break that into two:
> 1) generate dict or other Py/JSON object that holds the metadata,
> 2) consumer-specific - converts the Py/JSON object to eg. `::: dotted.name` string.
>
> Basically what I'm trying to say is that you say that the griffe layer is portable, and I'm just pointing out that yes, but the contract for handover should be something portable too, not the mkdocstring strings.
>
> Ah, I just see section 4.3 and the "griffe → component-input adapter " - yes, agree.
>
> regarding 2.3 and "Wants to be live?" - I think we need to be more nuanced and go example by example. eg in the future I can totally imagine that many of the djc_py examples could be instead rendered as a block with tabs that would allow to flick between the static code definition and the rendered output. Ofc, this does not apply to ALL instances of djc_py and html code blocks - eg when we're displaying only a snippet or a deliberately broken code, those cannot be rendered, and so those would remain as static djc_py or html code blocks.
>
> I like the "4.2 The {% example %} tag" 
>
> I also like 4.4a.
>
> re 4.5 - sounds good (btw, pagefind also has nice docs UI).
>
> re 4.6 - agree.
>
> re 4.7 - so the order would be to first convert markdown to HTML and only then expand the Django templates? WHat's the best practice?
>
> re 4.8 - since we're on uv, I wonder whether to wire the CLI commands as uv scripts instead of makefile, open to discussion. but rest looks good.
>
> re "Anchor changes from mkdocstrings." - so here we'll actually want to deviate from mkdocstrings. we'll want to drop the import path from the hashes, so `#django_components.Component` becomes `#Component`. This is something I wanted to do for a year at least, but couldn't figure out if mkdocs supports that or not.
>
> re pygments_djc - I confirm we own that.

### Spike 11.1

> ok, let's now do a deep dive spike on 11.1

> re emil's search - it's not part of this repo. in the mkdocs migration issue, he included link to the website. iirc it was github pages website. so from that you can infer the github URL and source code location

> and how does pagefind compares against lunr feature-wise?

> ok, and for both lunr and pagefind - what features would we need to rebuild ourselves to match (some of) the material search bar UX/features? WHich ones would make sense to reimplement?

> ok, looks good. my conclusion is that:
> - let's primarily go with pagefind
> - the search bar impl phase should be done after we have the e2e single page working (versioned?), AND after the dark/light themeing is implemented
> - during actual implementation, only at that time we should do actual explorations of trying to get pagefind / lunr implemented.
> - add another search bar impl phase for the v2 features for the more advanced features.
> - one thing I'm just not sure about is the seach-result analytics - we'd need to discuss where to send the data to. So this could be deferred to "v3" (iteration 3) of the search bar feature. (So similar to what you concluded in 11.1.G.1 :) ).
> - Tho I think we can still add the `"Searching…" spinner` - just as a fallback.

### Spike 11.2

> ok, let's now do a deep dive spike on 11.2

> ok, please also provide an overview of the features that zensical now ships - what would we lose out on if we decide to roll our own solution?

> loooks good. One more thing on this - after phase 5 (or as 5d?), we should revisit the features and behavior of 1) our old material documentation, 2) the list of zensical features, 3) our new django-based documentaiton, and assess and implement which features we want to port from the old docs / zensical into our new docs.

### Spike 11.3

> ok, let's now do a deep dive spike on 11.3

> ok, go ahead and do the "11.3a — coltrane evaluation"

### Spike 11.4

> ok, let's now do a deep dive spike on 11.4

> please fold the standalone DESIGN_djc_docs_site_spike_11_4.md into the main design doc, the same way as we did with the spikes 11.1-11.3, it was a unapproved deviation that you created this standalone file.
>
> Next, in "3.2 Solution: a directive expander, not a Django template render" - you suggested to convert `{% docstring "<dotted.path>" %}` to `<ApiReference>`. But what does `<ApiReference>` actually mean? is it a web component? or in second pass we replace <ApiReference> again to Djnago syntax so that Django template parser understands it? Or how do we plan to expand/render `<ApiReference>` to final HTML? Something like `<ApiReference>` would work with React, Vue, or DJC v3 (in v3 we switch to HTML-like syntax), but in v1 and v2, DJC components require the Django syntax `{% ... %}`. So how do you plan to wire up the `ExampleCard` *component* to be rendered in the place of a `<ExampleCard>` tag in the HTML?
>
> Next, re "{% include_file '<path>' %}" - I beleive there are use cases where we rely on inserting the text from injected file (`--8<--`) even without the encapsulating fenced code blocks. Or at least in the past we did that with I think overview/welcome page importing README, or sth like that. in such case we'd need `{% include_file "<path>" %}` NOT to wrap the imported string in fenced code block. HOWEVER, I think fenced code block is the BETTER design - it like an injection protection - ensuring that what gets injected is NOT evaluated as markdown/django template. But so in that case we should look for all uses of `--8<--`, and search for those that are NOT injected as literal code, and reassess whether we really need to inject the "raw" string.
>
> ANother thing re 3.2 - So I can imagine that as the entire site will be built on top of Django, we might use otehr custom Django components . AKA we might have things like `{% component "table" %}` in the markdowns. SO how would we handle that? would this survive to pass 3? Or? In such case, where do we draw the line between what is a directive expander and what is django template tag?
>
> re open question in sectino 4. - yes to `Keep --8<-- for explicit "here is one specific file" inclusions. Use {% example %} only for the high-level "show component + page + live demo tabs" case.`

> Nice, the revised design for 11.4 is much better!
>
> re 11.4.C - how are we planning to detect `4-space indented code block`?
>
> And re 11.4.K and 11.4.H - at what stage / phase shoudl we build the prototype?

### Spike 11.5

> ok, let's now do a deep dive spike on 11.5

> One correct re "plan to drop the django_components. prefix" - I don;t want to drop jusrt the root `django_components.` from the anchors, I want to drop the entire path, so only the last part of the path remains as the anchor (usually this corresponds to symbol name) - eg anchor `#django_components.component.Component` would become just `#Component`, because, 1) let's be honest, on respective ref pages (API, commands, django tags, etc), those symbols should be unique, so scoping under the path is not needed, and 2) the path is sometimes internal detail since we have dedicated paths for the public API (eg the general public API is all exported from root `django_component`, etc), so I'd prefer if we can hide the internal path from the docs / users.
> 
> Also, you wrote that "Anchor scheme change breaks 397 handwritten links in src/" - what do you mean by "handwritten links"? Or rather, how would these "handwritten" differ from non-handwritten?
> 
> re "Module-level instances (e.g. django_components.registry)" - where exactly does this happen?
> 
> re "Anchor scheme breaks 397 handwritten links in src/" and the "[X](api.md#django_components.Y)" vs cross-ref -> I suppose we can update them all to use the cross refs instead of md links.
> 
> re "api.md is alphabetically ordered with no thematic grouping." - I like that suggestion of adding thematic grouping!
> 
> re "Both griffe extensions inject raw HTML into docstring values. Our markdown renderer must permit raw HTML (markdown-it-py with html=true does)" - this assessment is outdated, see the latest design docs, we decided to go with python-markdown (or whatever is its name). Check your spike for other such outdated assumptions. (eg for the static site gen item in "Open items deferred to other spikes", we chose django-distill).
> 
> re "Layer 2 prototype: a ReferenceClass Django component that takes one ReferenceEntry, resolves the griffe object, and renders HTML. Wire it into a minimal page layout." and similar - let's also talk amore concretely where the API-kind-specifc templates should / would live.
> 
> Moreover on the topic of links vs cross refs - today, the docstrings are made so the result looks good in the built docs, not necessarily in VSCode or other IDEs. Is there some docstring format that looks well (autoformatted correctly on hints on hover, for example) in all major IDEs? And if so, could we achieve some docstring format that achieves both corect IDE hints rendering, as well as playing nice with the docs building?

> In "11.1 What each IDE renders today" - what is the 3rd entry? because I see 'Inline code \Component``'. Or is it supposed to be a symbol wrapped in double backticks?
>
> Anyway, so my takeaway from 11.1 is:
> - Migrate to Google-style (`Args:`, etc) across the codebase.
> - Migrate to double backticks(?) for inlined code
> 
> re "Backticks around symbol names" and "Write `Component`. IDEs render it as monospace; the docs build runs an implicit-cross-ref resolver pass that turns backticked text into a link when it matches a known project symbol" - not sure I like that - how would we distinguish between `Component` as link vs `Component` as inlined code? Or is teh idea that with single backtick we wrap in links, while in double backticks we don't?
> 
> Also, do python docstirngs support linking to other symbols similarly to I think `@link` in JSDocs?
> 
> re "No Material admonitions. " and "No raw HTML." in 11.2 - I agree with the *idea*, but we'll see in practice whether it makes sense. Right now the nice thing is that we can have rich docs even in reference docs. I'm willing to not adhere to these conventions 100% of the time if the options are a) bland docstrings with only vanilla markdown vs b) rich docstrings with examples vs c) needless duplication just to keep docstrings vanilla and rich examples in separate page.
> 
> Also note that all these conventions that we eventually agree on should be documented (eg in development section of the docs) (and also added to our local claude.md)

> re 11.3 - since backticks would be doing double duty, I think I prefer that we leave backticks are monospace (inline code) and non-linked, and instead leave the cross reffing feature eg `[text][django_components.Component]` for linking.. SO this also changes the item 2. in 11.2.

### Spike 11.6

> ok, let's now do a deep dive spike on 11.6. Note that a lot has changed since last message, so be sure to read up on latest state of the design doc, as well as the surroundnig spike files

> looking through 11.6.B:
> - heavy use items look good
> - re zer- or near zero use, I have some comments:
>   - pymdownx.tabbed -> didn't know that was possible! I did want tabs in the past and WILL want them (eg for multiple package managers). le'ts keep them.
>   - pymdownx.details -> same thing. I chronically used notes (admonitions), because I didn't know that expandable details sections were a thing.
>   - pymdownx.magiclink -> this one I agree can be removed - it's trivial and better to be explicit with the full links.
>   - pymdownx.inlinehilite -> same as the first two, keep and document insrtead of removing.
> 
> So overall I think we should have a reference page to show all the syntaxes that we can use in the markdowns so that those unused features get better visibility, instead of dropping them.
> 
> Ideally we'd also enumarate all available pymdownx plugins, so we'd know when to add them. eg I just saw that the superfence allows for creating mermaid diagrams, or that there's "Arithmatex", or strikethrough, or captions, or keyboard keys, or the "critic" highlight (https://facelessuser.github.io/pymdown-extensions/extensions/critic/) that could be used for inline git-like diffing, etc.
> 
> Some that I genuinely don't know what they do (or couldn't find in the docs) are :
> - attr_list
> - def_list (in docs there's `/// define`)
> - PathConverter
> 
> So with that I'd also drop the CI guardrail that you're proposing. in 11.6.B
> 
> re 11.6.D - I'm thinking changing `{% version %}` to just `{% version %}`, the rest looks good.
> 
> just a note in 11.6.F re "Per-link authoring choice during the sweep" - For a lot of the docs I wrote I included A LOT of manual links eg '[`Component`](../api.md#django_components.component.Component)'. These are meant to be genuine links, NOT just "a backticked mention dressed as a link". My aim indeed is that when we mention specific public API interfaces, to link to them often (as opposed to eg linking only the first instance of the symbol). I'm just mentioning this so that you don't go on a spree undoing all my linking work just because.
> 
> re frontmatter support - how would that look like - would WE control what goes into the frontmatter, or does pymdownx already defines specific fields it recognizes?
> 
> also, re "Default behavior on Material admonitions in docstrings vs in markdown pages." - I said this in another chat but looks like it didn't survive to be noted down in 11.5 / 11.6 - DO NOT sweep-convert existing admonitions to blockquotes for "IDE friendliness". that's something for me to decide later on, but during this work, we should keep the advanced syntaxes in docstrings as they are, and only fix the structural blockers - align on google syntax, fix the links, etc. Please update the other spikes and the main design doc accordingly too.

### Spike 11.7

> ok, let's now do a deep dive spike on 11.7. Note that a lot has changed since last message, so be sure to read up on latest state of the design doc, as well as the surroundnig spike files

> re "Older mkdocs-built versions on gh-pages" - I belive the practical approach is to revisit this once we've built the versioning logic and completed the main build end to end, so we know waht the contract is, eg after phase 7 "search v2"?
> 
> do NOT add precommit hook.
> 
> re 8.3 - I wasn't aware that mike was on BSD 3 - any other deps across all the spikes/upstream deps that have non MIT licenses?
> 
> and re 11 - we can implement also the docs-build-check comand - I suppose tha could then live in CI as a gate?

### Spike 11.9

> ok, let's now do a deep dive spike on 11.9. Note that a lot has changed since last message, so be sure to read up on latest state of the design doc, as well as the surroundnig spike files

### Spike 11.11

> ok, let's now do a deep dive spike on 11.11. Note that a lot has changed since last message, so be sure to read up on latest state of the design doc, as well as the surroundnig spike files

> re "Code blocks" you mentioned "Skip the file-name tab for v1 (we don't author with file-named code blocks today)" - but isn't that what we'd use the pymdownx tabs for?
>
> Q on "4. Top header" - if we move the Overview, Concenpts, etc in the sidebar, then frankly I don't see why it should be duplicated in the top nav? I'd lean that top-level nav would point to genuinely different kinds of pages. Eg like logo would take user to landing page (NEW; differnet from current), Documentation (or just "Docs") would take to section that houses the "Concepts, Reference, Examples, ...", something like Plugins should live in the top too, bc it's different KIND of page, Examples is a mixed case (but could be at top nav), Release notes can be folded inside Docs(?). Thoughts? Also in the future I'd like to have a Blog link there.

> re landing page, let's add that add a separate phase at the end. I have an idea in mind, but it will involve a lot of active back and forth and codesign with the agent
