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

For each example's `View.get()`, enumerate the inputs that the example actually uses (e.g. `?type=alpine`, `?type=htmx`, `?type=js`), call it at build time, and write the result to `static/fragments/<example>/<key>.html`. Rewrite `hx-get="/examples/fragments?type=alpine"` to `hx-get="/static/fragments/fragments/alpine.html"` at build time.

This works because **the example author already knows the finite set of inputs** — that's what makes it a doc-able example. We add a tiny convention:

```python
class FragmentsPage(Component):
    class DocsExample:
        # The set of (path, query) pairs to pre-render and emit as static files.
        fragments = [
            ("", {"type": "alpine"}),
            ("", {"type": "htmx"}),
            ("", {"type": "js"}),
        ]
```

The `build_docs` command walks every example's `DocsExample.fragments`, calls the view with a synthetic request, and writes the body to `static/fragments/...html`. A URL rewriter replaces `get_component_url(...)` calls at build time.

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

**Question Juro asked:** is the order "markdown → HTML, then Django templates"? What's the best practice?

**Answer.** The widely-used pattern across Hugo, Eleventy, Jekyll, and 11ty is **shortcodes-first, markdown-second, layout-last**. Concretely, three passes:

```
content/foo.md
    -> [Pass 1] Render markdown source as a Django template (only the page body — no layout yet)
        - Django template tags like {% example "name" %}, {% docstring "django_components.Component" %},
          {% include_file "..." %} expand to markdown snippets and/or block-level HTML
        - This is the only place Django sees the page body
    -> [Pass 2] Markdown to HTML
        - markdown-it-py (CommonMark + extensions: fences, tables, footnotes, anchors, admonitions)
        - With `html=true` so block-level HTML emitted by Pass 1 is passed through untouched
        - Pygments highlights all fenced code blocks (incl. djc_py)
        - Heading slugification + TOC extraction happens here
    -> [Pass 3] Wrap the page HTML inside the DocPage Django component layout
        - DocPage takes {content_html, title, toc, breadcrumbs, edit_url, version} as inputs
        - This is the only place the page chrome (nav, sidebar, footer, dark mode, search bar) is added
    -> sanitize + minify
    -> write to site/<path>.html
```

Why this order:

- **Pass 1 must be first** because `{% example %}` emits the HTML for a tabbed widget that contains rendered components — markdown-it-py must see that HTML as block-level HTML and leave it alone (not parse it as if `<div>` openings were lists, etc.).
- **Pass 1's output must be markdown-compatible**, not arbitrary HTML inline with markdown text. The rule for `{% example %}` is: emit a top-level `<div>...</div>` block separated by blank lines. CommonMark treats that as a raw HTML block and passes it through. Inline tags (`{% ref %}` for cross-references, `{% icon %}`) should emit markdown text or inline HTML.
- **Pass 3 (layout) cannot run before Pass 2** because the layout needs the rendered TOC and heading IDs.

The alternative — "markdown → HTML first, Django templates on the HTML output" — is what we'd have to do if we wanted Django to substitute into a *post-rendered* page. It's harder because we'd be reaching into HTML to find substitution points, and we lose the ability to emit markdown that participates in the parse.

If we discover a `{% example %}` use case where the embedded component output itself contains markdown that needs to be parsed, we'd add a Pass 2.5 (another markdown pass on the component output) — but most likely the embedded output is HTML for a finished widget, so this won't be needed.

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

## 5. Migration plan (incremental, not big-bang)

We don't replace mkdocs in one PR. We run both side-by-side until the new site reaches parity, then cut over.

**Phase 1 — scaffold + one section.** Build `docs_site/` with one section (e.g. `getting_started/`) ported. Markdown → HTML → static output works end-to-end. No interactive examples yet. *Output:* a directory we can `python -m http.server`. *Time estimate:* ~1-2 weeks of focused work.

**Phase 2 — the `{% example %}` tag.** Port [docs/examples/](docs/examples/) and the fragment pre-rendering. Pick fragments as the first real example. Prove that a doc page can embed a real interactive component. *Output:* a live fragments example in the new site. *Time estimate:* ~1 week.

**Phase 3 — the rest of the markdown pages.** Mechanical port of `concepts/`, `guides/`, `community/`, etc. Mostly markdown copy-paste; the tricky bits are the cross-page links and the `mkdocs-macros` people.md page. *Output:* feature-equivalent docs minus API reference. *Time estimate:* ~1-2 weeks.

**Phase 4 — API reference.** Build the griffe → component adapter. Reuse [docs/scripts/extensions.py](docs/scripts/extensions.py) verbatim. *Output:* `reference/*` parity. *Time estimate:* ~1 week.

**Phase 5a — theming.** Light / dark CSS tokens, palette, dark-mode toggle component. Needs to land before search because the search modal is theme-sensitive (input, results, hover, focus rings) — see §11.1.G.1. *Output:* theme tokens consumed by all components built so far. *Time estimate:* ~3-4 days.

**Phase 5b — versioning + social cards.** `docs/v/<version>/` layout per §4.6, `version_picker` component, OG-image generation. Open question (§11.1.G.1): is versioning a hard prerequisite for search v1? Almost certainly no — per-version search is just one Pagefind bundle per version dir — but confirm during implementation. *Output:* multi-version-ready site + social cards. *Time estimate:* ~1 week.

**Phase 5c — search v1.** Pagefind integration, `SearchInput` / `SearchModal` / `SearchResultList` components per §11.1.G.5, plus `?h=` on-page highlight. Includes the delayed-spinner fallback. *Output:* parity with Material's day-to-day search UX. *Time estimate:* ~5-7 days.

**Phase 6 — cutover.** Switch the GitHub Pages deploy from mkdocs to the new build. Delete mkdocs config and dependencies. Leave a redirect for any moved URLs. *Time estimate:* ~2 days.

**Phase 7 — search v2 (post-cutover).** Autocomplete, recent searches, filters/scoping, typo-recovery fallback (borrowing Emil's scoring algo per §11.1.C). *Output:* power-user polish. *Time estimate:* ~3-4 days.

**Phase 8 — search v3 (deferred).** Search-result analytics. **Blocked** on picking an analytics target (Plausible / GoatCounter / Cloudflare Worker / self-hosted endpoint). Separate design decision; park until we know where the data should go.

**Total estimate (Phases 1-6, the actual migration):** ~7-9 weeks of effort. Search v2/v3 add to that whenever we choose to do them. Can all be split across many PRs and many calendar weeks.

A key property of this plan: **at every phase, the old mkdocs site is still the canonical published site.** We do not break docs while we're rebuilding them. We only switch the deploy in Phase 6.

---

## 6. What we lose, what we gain

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

## 7. Open questions to resolve before starting

1. **URL stability.** Material generates anchors as `#some-heading`; we need to match its slug algorithm exactly to avoid breaking inbound links from third-party blog posts. Audit the slug function and replicate it.
2. **Anchor changes from mkdocstrings — we want to DEVIATE.** Today every API symbol is anchored as `reference/api/#django_components.Component`. The dotted import path in the hash is ugly and verbose, and Juro has wanted to drop it for a long time. New scheme: `reference/api/#Component`. Trade-off: this breaks inbound links from blog posts and prior docs versions. Mitigation: in the rendered HTML, emit **both** the new canonical anchor (`<h2 id="Component">`) and a legacy alias for back-compat (`<a name="django_components.Component"></a>`) so old URLs still work. Confirm via spike (§11) whether the alias actually resolves in modern browsers (`<a name>` is deprecated but still honored).
3. **Edit-on-GitHub button URLs.** Each generated page maps back to a source. We control this; needs to be wired into our `doc_page` component.
4. **Themability / dark mode toggle.** Material gives us palette-switching out of the box. We can recreate with one CSS file and a small JS toggle.
5. **Versioned redirects.** When pages move (like [#1355](https://github.com/django-components/django-components/issues/1355)), our redirect map is HTML `<meta http-equiv=refresh>` files. Confirm GitHub Pages serves them with the right Cache-Control.
6. **Build time.** mkdocs build is ~30s today. Django startup + crawl + Pygments will likely be slower; budget ~1-2 minutes. Acceptable for CI.
7. **`pygments_djc` ownership.** Confirmed by Juro — we own it. It stays as a normal dep; no migration concerns here.
8. **mkdocs strict-mode link checking.** We currently run `mkdocs build --strict` in CI to fail on broken links. The new build needs an equivalent step that walks all generated HTML, parses `<a href>`, and asserts every internal link resolves. See "Guardrails" spike in §11.10.
9. **Migrating old docs versions.** Unresolved. Two sub-questions: (a) do we rebuild every historical version from its git tag with the *new* builder (which means historical content has to remain compatible with the new directives), or (b) do we keep the existing mkdocs-built HTML for older versions and only switch the builder for new releases going forward? See spike in §11.8.

---

## 8. First concrete step

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

## 9. Out of scope for this doc

- Internationalization. mkdocs doesn't support it cleanly today either; defer.
- Comments / discussion threads embedded in docs.
- Auto-generated tutorials. We'd rather hand-author and keep them honest.
- The v2/v3 "drop Django dependency" refactor — orthogonal, and the docs site doesn't need it.

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
- **Why.** Search is the most-used feature on docs sites per the [#1515 thread](https://github.com/django-components/django-components/issues/1515). The biggest risk in §6's gains/losses table is "search quality." We need to compare three candidates concretely: Material's Lunr setup, Emil's implementation, and Pagefind.

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

1. **E2E single page working** — at minimum a real markdown page rendering through our `doc_page` component pipeline (the §8 proof of concept). Until the page chrome exists, there's nowhere to put a search bar.
2. **Light / dark theming** — the `SearchModal` is a theme-sensitive surface (input, results, hover states, focus rings). Building it before the theme tokens exist means redoing the CSS once theming lands. Theming first; search after.
3. **Versioning — open question.** Do we need versioning in place before the first search iteration? Per-version search is just "one Pagefind bundle per version directory" (§11.1.G item #19), so probably **no — search v1 can ship pre-versioning**, with the assumption it'll naturally extend to per-version once §4.6's `docs/v/<version>/` layout is live. Confirm during the implementation spike.

**Reorder for the migration plan (§5):** today Phase 5 is "search, versioning, social cards" lumped together. Split it: theming first (in Phase 1 or a dedicated mini-phase), versioning in its own phase, then search v1 as the next phase. Search v2 and v3 come after the initial cutover.

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

### 11.4 Markdown + Django templates pipeline

- **Question.** Can pages remain markdown but with Django template tags embedded? What's the cleanest way to make `{% example %}` and friends work inside markdown without the markdown parser fighting them?
- **Why.** Already partially answered in §4.7 (Hugo-style: shortcodes → markdown → layout). The spike validates the answer end-to-end.
- **Method.**
    1. Pick one real page from `docs/getting_started/` and convert it to the new pipeline.
    2. Verify: heading anchors, code-block highlighting, inline `{% example %}` directives, and a custom `{% docstring %}` directive all render correctly.
    3. Time the per-page render; extrapolate to full-site time.
    4. Validate that `markdown-it-py` (or `python-markdown`) passes through block-level HTML emitted by Django without mangling it.
- **Feeds into.** §4.7, and confirms the order of passes is the one we want.

### 11.5 Griffe reuse + per-API-kind renderers

- **Question.** Validate the assumption that griffe gives us everything we need *minus mkdocstrings*. Then enumerate every API "kind" we currently render and design the component-per-kind set.
- **Why.** This is the biggest piece of new work after the markdown pipeline. If griffe falls short somewhere we expect mkdocstrings to fill in (e.g. cross-references, ambiguity resolution), we need to know.
- **Method.**
    1. List every distinct API kind currently rendered: `class`, `function`, `method`, `property`, `setting`, `cli_command`, `management_command`, `template_tag`, `exception`, `extension_hook`, `dataclass_field`, etc. (audit `docs/scripts/reference.py` and `docs/reference/*.md`).
    2. For each kind, sketch the Django template that renders it. Note shared sub-components (e.g. "signature line", "parameters table", "examples block").
    3. Walk a real griffe `Object` tree for `django_components.Component` and confirm every field we need is reachable.
    4. Identify gaps where mkdocstrings does post-processing we'd need to replicate (cross-reference resolution is the obvious one).
- **Feeds into.** §4.3, §2.2 (the data → renderer split).

### 11.6 Replicating "simple/clean way to define content"

- **Question.** What's the inventory of authoring affordances Material/mkdocs gives us today, and what's the minimum we need to keep contributors happy?
- **Why.** `pymdownx.tabbed`, `admonition`, `details`, `tasklist`, `--8<--` includes, `mkdocs-macros`, code annotations, footnotes — every one of these is a contributor convenience. If the new system feels like a downgrade to authors, we'll regret it.
- **Method.**
    1. Inventory: grep `docs/` for every pymdown / Material directive in use.
    2. For each, decide: (a) supported natively by `markdown-it-py` (or `python-markdown`), (b) trivial Django template tag, (c) drop, (d) reimplement.
    3. Write the shortest possible spec for each — one sentence per directive.
- **Feeds into.** §4.7.

### 11.7 mike internals + bootstrap-from-tags script

- **Question.** Two parts:
    (a) Can we reuse any of `mike`'s internals (manifest schema, version-picker JS, alias resolution) even though we're persisting versions to `master` rather than `gh-pages`? Did Juro's earlier outreach to the `mike` author get a response?
    (b) Implementing the `docs-build-all` bootstrap command (§4.6): walk `git tag`, check each out in a worktree, run `docs-build` per tag.
- **Why.** `docs-build-all` only runs at bootstrap / disaster recovery, but it has to work reliably the few times we do run it. And there's no point reinventing pieces of `mike` that we can lift as small focused modules.
- **Method.**
    1. Read `mike`'s source. Identify modules that could be invoked without the `mkdocs` adapter — manifest writer, version-picker JS, alias resolver.
    2. Check Juro's earlier issue/PR/email thread for any reply from the `mike` author.
    3. Design the `docs-build-all` worktree-walker (the `docs_versions.toml` schema, include/exclude/bounds, idempotency on existing `docs/v/<version>/` dirs).
    4. Verify on a 3-version smoke test (e.g. v0.148, v0.149, v0.150) producing `docs/v/0.148/`, `docs/v/0.149/`, `docs/v/0.150/` on a scratch branch.
- **Feeds into.** §4.6.

### 11.8 Migrating older docs versions

- **Question.** What do we do with `v0.135` through `v0.150` once the new builder is canonical?
- **Why.** Inbound links from blog posts, Stack Overflow, and search engines point to specific historical URLs. We can't break them.
- **Method.** Choose between three options and decide on cost/benefit:
    1. **Rebuild all historical versions with the new builder.** Requires that old markdown content remains compatible with the new directive set (mostly likely, but not guaranteed). Cleanest URL story.
    2. **Freeze old versions; new builder only from v0.151+.** Old versions are served from a frozen mkdocs-built directory committed once. URL prefixes diverge.
    3. **Hybrid:** rebuild only versions of interest (e.g. last 3 stable), freeze older.
- **Feeds into.** §7.9, §4.6.

### 11.9 mkdocs plugin replacement audit

- **Question.** Go plugin-by-plugin through [mkdocs.yml](mkdocs.yml) and confirm a replacement for each.
- **Why.** §2.1 has a high-level table; the spike turns each row into a concrete decision (library / DIY / drop).
- **Method.**
    1. For each plugin: read its current config, list the features we actually use (most plugins have a feature surface bigger than what we exercise).
    2. Pick a replacement library or DIY snippet for each used feature.
    3. Build the proof-of-concept page (§11.4) using the replacements end-to-end.
- **Feeds into.** §2.1, Phase 1 scope.

### 11.10 Guardrails (dead-link detection, broken anchors, schema drift)

- **Question.** What guards does the new build need so CI fails loudly when something breaks?
- **Why.** mkdocs `--strict` mode catches many problems for us. The new build needs equal-or-better guards or we'll regress quality.
- **Method.** Each guardrail is a separate small piece:
    1. **Internal link check.** Walk all generated HTML, parse `<a href>`, assert every internal target resolves.
    2. **Anchor check.** Every `#anchor` in href maps to an `id=` in the destination page.
    3. **API symbol check.** Every `{% docstring "x.y.z" %}` references a symbol that exists in griffe.
    4. **Example-page contract check.** Every `{% example %}` references a directory under `examples/` with a valid `page.py`.
    5. **Cross-version link check.** A link from `/v0.150/foo` should not silently target `/v0.149/foo`.
    6. **Snapshot test.** Snapshot a small set of rendered pages (syrupy) so accidental regressions in the renderer surface in PR review.
- **Feeds into.** §4.8 (build), §7.8.

### 11.11 UI / layout inspiration

- **Question.** What does the actual layout/visual design look like? Reference: `~/repos/agents/safe-ai-factory/web` (flat sidebar, simple and elegant); [Vuese](https://vuese.org/) (nested sidebar variant); [Pagefind docs](https://pagefind.app/).
- **Why.** Material's polish is a real loss in §6. We need a deliberate visual direction before Phase 5 so we're not bikeshedding under time pressure.
- **Method.**
    1. Screenshot the three references' main views (home, content page with sidebar, search overlay, code block, dark mode).
    2. Pull out 5-8 design tokens we want to honor (sidebar width, font stack, code-block padding, link color treatment, table style, etc.).
    3. Decide flat-vs-nested sidebar — likely nested, since our docs have real depth.
    4. Sketch a static HTML mock of a single page before building it as a component.
- **Feeds into.** Phase 5 component design.

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

### 1st iter


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

```
ok, let's now do a deep dive spite on 11.1
```

```
re emil's search - it's not part of this repo. in the mkdocs migration issue, he included link to the website. iirc it was github pages website. so from that you can infer the github URL and source code location
```

```
and how does pagefind compares against lunr feature-wise?
```

```
ok, and for both lunr and pagefind - what features would we need to rebuild ourselves to match (some of) the material search bar UX/features? WHich ones would make sense to reimplement?
```

```
ok, looks good. my conclusion is that:
- let's primarily go with pagefind
- the search bar impl phase should be done after we have the e2e single page working (versioned?), AND after the dark/light themeing is implemented
- during actual implementation, only at that time we should do actual explorations of trying to get pagefind / lunr implemented.
- add another search bar impl phase for the v2 features for the more advanced features.
- one thing I'm just not sure about is the seach-result analytics - we'd need to discuss where to send the data to. So this could be deferred to "v3" (iteration 3) of the search bar feature. (So similar to what you concluded in 11.1.G.1 :) ).
- Tho I think we can still add the `"Searching…" spinner` - just as a fallback.
```
