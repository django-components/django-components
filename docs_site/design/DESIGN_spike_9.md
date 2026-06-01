# Spike 11.9 — mkdocs plugin replacement audit

**Status:** spike complete
**Date:** 2026-06-01
**Feeds back into:** [DESIGN_djc_docs_site.md §2.1, §4.6, §4.7, §4.8, §11.10, Phase 1 scope](DESIGN_djc_docs_site.md)
**Spike question:** Go plugin-by-plugin through [mkdocs.yml](mkdocs.yml) and confirm a concrete replacement (library / DIY snippet / drop) for each. Convert §2.1's high-level table into per-plugin verdicts with LOC budgets and risk notes.

This spike is the **terminal authority for plugin dispositions**. Where another spike (§11.1, §11.5, §11.6, §11.7, §11.10) already decided, this spike inherits and cross-links; where no spike has decided yet, this spike decides.

---

## 0. TL;DR verdict

**GO.** Every plugin in [mkdocs.yml](mkdocs.yml) maps to a concrete replacement. No plugin produces a blocker. Total new LOC across the infrastructure plugins covered exclusively by this spike (`social`, `minify`, `redirects`, `gen-files`, `awesome-nav`, `markdown-exec`, `include-markdown`, `mkdocs-macros`, `git-revision-date-localized`, `git-authors`) is **~500–700 LOC**, dominated by one item: social-card generation (~300–400 LOC if we want feature parity with Material's plugin).

**Three load-bearing decisions** drop out:

1. **Social cards: use Playwright + a Django template, not Pillow/cairosvg.** Material's `social` plugin (which we use today) is ~1800 LOC of Pillow + cairosvg + Jinja sandbox + thread-pool composition. Reimplementing that math is undue scope. Playwright (already in dev deps, used for E2E) can screenshot a Django-rendered `OgCard` component to PNG at build time. ~50–100 LOC of orchestration plus a CSS-driven card template. Side benefit: contributors can iterate on card design with normal browser devtools.

2. **`redirects`: emit `<meta http-equiv="refresh">` files into the build output, not a server-side redirect map.** GitHub Pages serves them with the right semantics. ~30 LOC.

3. **`minify`: switch from the mkdocs-minify-plugin's `htmlmin2` to `minify-html` (the Rust-based parser).** htmlmin2 is unmaintained-adjacent (its parent `htmlmin` was abandoned in 2019; htmlmin2 is a community fork) and slow. `minify-html` is well-maintained, ships wheels, and is 10–100× faster. ~10 LOC of glue.

**License audit:**

- All plugins we replace are MIT.
- We're vendoring `mike` (BSD-3 — already audited in §11.7).
- `cairosvg` is LGPL-3.0. **We drop it.** It's only pulled in transitively by Material's `social` plugin. Replacing social-card generation with Playwright removes the LGPL dependency entirely. Bonus.
- `mkdocs-include-markdown-plugin` is Apache-2.0. We drop it (one root-`README.md` use, out of scope).
- Everything else stays MIT/BSD permissive.

**`docs-build-check` CI gate (per Juro's request in §11.7 feedback):** a third CLI entrypoint (alongside `docs-build` and `docs-build-all`) that runs the build + all guardrails (§11.10) but writes nothing to disk. Returns non-zero on any failure. Wired into the GitHub Actions PR check. Designed in §6.

**Biggest open risk:** social-card aesthetic regression. Material's plugin is genuinely well-tuned. A Playwright-rendered card will look different (probably better, since we control the CSS). The risk is the visual delta during the cutover, not the technical feasibility. Mitigation: produce a side-by-side comparison on the proof-of-concept page (§7) and only cut over when the new card is reviewer-approved.

**Recommended first concrete step:** during Phase 1 of the migration, scaffold the `RedirectFile` writer and the `MinifyHtml` post-build step. Both are <50 LOC, validate the build pipeline shape, and are already needed for any internal preview. Social cards land in Phase 5 alongside search and versioning (§5 of the main design doc).

---

## 1. Complete plugin inventory

Every entry from `mkdocs.yml`'s `plugins:` block, in order. The order here mirrors the file so anyone reading [mkdocs.yml](mkdocs.yml) top-to-bottom can find a line below.

| # | mkdocs.yml plugin | Used today | Owner spike | Disposition (this spike's call) | LOC budget |
|---|---|---|---|---|---|
| 1 | `autorefs` | Cross-page Python symbol resolution; consumed by `mkdocstrings` only | **§11.5** | Replaced by §11.5's bracket-cross-ref resolver | 0 new (in §11.5) |
| 2 | `include-markdown` | One use in `docs/README.md` (out of scope) | **§11.6.E** | **Drop.** If we ever need it, Django's `{% include %}` handles it | 0 |
| 3 | `gen-files` | Runs 3 scripts at build start: [setup.py](docs/scripts/setup.py), [reference.py](docs/scripts/reference.py), [gen_release_notes.py](docs/scripts/gen_release_notes.py) | **This spike** + §11.5 | **Replaced by Django management commands** chained into `docs-build`. See §2.1 | ~80 LOC |
| 4 | `awesome-nav` | Nav YAML; 0 `.pages` files actually present in `docs/` (verified §11.6.E) | **§11.6 + this spike** | **Drop the plugin; ship our own nav YAML loader** in the sidebar component. See §2.2 | ~80 LOC |
| 5 | `git-revision-date-localized` | "Last updated" footer per page (CI-only, excludes 4 paths) | **§11.6.C** confirmed; this spike scopes the implementation | DIY via `subprocess.run(["git", "log", -1, "--format=%cI"], path)` + per-file cache. See §2.3 | ~60 LOC |
| 6 | `git-authors` | Author list per page (CI-only, same excludes) | **§11.6.C** + this spike | DIY via `git log --format=%an`, dedup, sort. See §2.3 | ~40 LOC |
| 7 | `markdown-exec` | Configured but **0 `exec="true"` usages in scope** (verified §11.6.E) | **§11.6.E** + this spike | **Drop.** Configured speculatively; nothing relies on it | 0 |
| 8 | `search` | Lunr-style index emitted by Material | **§11.1** | Replaced by Pagefind (or DIY Lunr) per §11.1 | 0 new (in §11.1) |
| 9 | `social` | OG card PNG generator (CI-only); used by Twitter/Facebook embeds | **This spike** | **Replace with Playwright + `OgCard` Django component.** See §2.4 | ~100 LOC orchestration + ~80 LOC template |
| 10 | `mike` | Versioned deploy to `gh-pages` | **§11.7** | Vendor `mike/versions.py` (~270 LOC); replace the rest | 0 new (in §11.7) |
| 11 | `redirects` | URL redirect map (5 entries today) | **This spike** | **Emit static `<meta http-equiv="refresh">` HTML files** at the moved URL paths. GitHub Pages serves them correctly | ~30 LOC |
| 12 | `minify` | `minify_html: true` only | **This spike** | **DIY using `minify-html` (Rust-backed)** as a post-build pass over `site/**.html` | ~20 LOC |
| 13 | `mkdocstrings` | API reference rendering | **§11.5** | Replaced by `griffe` + `ApiReference` Django component per §11.5 | 0 new (in §11.5) |
| 14 | `macros` | Jinja2 rendering, used by 1 page (`docs/community/people.md`) | **§11.6** confirmed; this spike scopes the rewrite | The page becomes a **native Django template page** (bypasses markdown pipeline). See §2.5 | ~40 LOC |

**Plus all `markdown_extensions:` entries** (lines 97–127 of `mkdocs.yml`) are owned by **§11.6** and confirmed there. This spike does not re-audit them.

**Plus all `theme:` features** (lines 37–77 of `mkdocs.yml`) — Material theme UX affordances — are owned by **§11.6.C** + **§11.11** + **§11.1.G.1** (dark/light toggle). This spike does not re-audit them.

### 1.1 Cross-spike ownership cheat sheet

If you arrive at this spike from somewhere else and want to know "is X covered?", here's the map:

| Plugin / capability | Owner spike | Status |
|---|---|---|
| `autorefs` | §11.5 | covered |
| `mkdocstrings` | §11.5 | covered |
| anchor scheme codemod (`#django_components.X` → `#X`) | §11.5 + §11.6.F | covered |
| All `markdown_extensions` (pymdownx.*, admonition, tables, etc.) | §11.6 | covered |
| `mkdocs-macros`, `mkdocs-include-markdown`, `markdown-exec`, `git-*` (decisions) | §11.6.E | covered; this spike scopes the implementations |
| `mike` | §11.7 | covered |
| `search` (incl. index emission) | §11.1 | covered |
| Material `theme.features` (copy button, edit-on-GitHub, etc.) | §11.6.C | covered |
| Dark/light toggle | §11.1.G.1 | covered |
| Material `theme.palette` colors and typography | §11.11 | covered |
| Strict-mode link / anchor / symbol validation | §11.10 | covered |
| Social cards, redirects, minification, gen-files runner, awesome-nav loader, git-* implementation | **this spike** | **decided here** |

---

## 2. Deep dive — plugins this spike owns

### 2.1 `gen-files` — replaced by Django management commands chained into `docs-build`

**What it does today.** [mkdocs.yml](mkdocs.yml) lines 136–140: registers 3 scripts that run before mkdocs starts walking content. Each uses the `mkdocs_gen_files` API to write into a virtual fs that mkdocs merges with `docs_dir/`. Scripts:

- [docs/scripts/setup.py](docs/scripts/setup.py) — 1-liner: imports `pygments_djc` to register the `djc_py` lexer with Pygments.
- [docs/scripts/reference.py](docs/scripts/reference.py) — walks the public API, emits `::: dotted.path` lines into `docs/reference/*.md` for mkdocstrings to render.
- [docs/scripts/gen_release_notes.py](docs/scripts/gen_release_notes.py) — splits `CHANGELOG.md` by `## vX.Y.Z` headers, writes one page per version into `docs/releases/*.md`, builds an index.

**Replacement.** Each of these becomes a step in the `docs-build` management command pipeline. No virtual fs needed — write to a real temp dir, point the markdown pipeline at it. Concretely:

- `setup.py` work: just `import pygments_djc` at module load of the build command. One line.
- `reference.py` work: subsumed by **§11.5's Discovery layer**, which produces the portable Python dict / JSON consumed by `ApiReference` rendering. The `::: dotted.path` emission disappears entirely. See [§11.5 §5.1 of the §11.5 spike file](DESIGN_djc_docs_site_spike_11_5.md).
- `gen_release_notes.py` work: keep ~80% of the existing parsing logic; swap `mkdocs_gen_files.Nav()` writes for plain `pathlib.Path.write_text(...)` calls into the build dir.

**Build pipeline shape:**

```python
class Command(BaseCommand):
    def handle(self, *_, **opts):
        import pygments_djc  # noqa: F401, register djc_py lexer

        build_dir = Path("docs/v") / current_version()
        with TemporaryDirectory() as staging:
            generate_release_notes(staging)        # was gen_release_notes.py
            api_index = discover_api_symbols()     # §11.5 Discovery layer; no .md emission
            crawl_and_render_pages(staging, api_index, build_dir)  # §4.7 markdown pipeline
            emit_redirects(build_dir)              # §2.3
            generate_social_cards(build_dir)       # §2.4
            run_minifier(build_dir)                # §2.2
            update_manifest(build_dir.parent)      # §4.6 + §11.7
```

**Risks.** None significant. `gen-files`' value-add was the virtual fs abstraction over mkdocs' `docs_dir/`. We don't need that abstraction when we control the whole pipeline.

**LOC budget:** ~80 LOC (mostly the release-notes parsing port; the rest is glue).

### 2.2 `awesome-nav` — drop, ship a tiny nav YAML loader

**What it does today.** Plugin that lets contributors override the auto-generated nav by dropping `.pages` files next to markdown. Verified by §11.6.E: **zero `.pages` files exist in `docs/`** — the plugin is configured but does nothing.

**Replacement.** A single nav YAML at `content/_nav.yml` (or similar) that the sidebar component consumes. Schema is small:

```yaml
# content/_nav.yml
- title: Getting started
  children:
    - { title: Installation, page: getting_started/installation.md }
    - { title: Quick start,  page: getting_started/quick_start.md }
- title: Concepts
  children:
    - { title: Fundamentals, page: concepts/fundamentals/index.md, expand: true }
    - ...
```

Loader is ~50 LOC: read YAML, validate each `page:` resolves to an existing markdown file in `content/`, resolve URLs (depth-1 to depth-2, etc.). The sidebar component receives the parsed tree and renders.

**Risks.** Migrating the existing 14-section nav from `mkdocs.yml`'s implicit nav (we don't override today; mkdocs auto-builds it from the `docs/` directory tree) is one careful pass. Most of `docs/` is already organized so the tree mirrors the desired nav. Edge case: `concepts/fundamentals/index.md` vs `concepts/fundamentals/` — must establish the section-index convention (already called out in §11.6.C).

**LOC budget:** ~80 LOC (loader + schema validator).

### 2.3 `git-revision-date-localized` + `git-authors` — DIY subprocess + cache

**What they do today.** Each page gets `last_updated` and `authors` metadata, surfaced in the Material theme footer. Both plugins skip `reference/*`, `changelog.md`, `code_of_conduct.md`, `license.md` (those don't have meaningful "last modified" semantics).

**Replacement.** Single helper module `docs_site/build/git_metadata.py`:

```python
@lru_cache(maxsize=None)
def get_page_metadata(repo_root: Path, page_path: Path) -> PageGitMeta:
    rel = page_path.relative_to(repo_root)
    # last_updated
    last = subprocess.run(
        ["git", "log", "-1", "--format=%cI", "--", str(rel)],
        cwd=repo_root, check=True, capture_output=True, text=True,
    ).stdout.strip()
    # authors (unique, sorted by first-commit order, capped at 5)
    authors_raw = subprocess.run(
        ["git", "log", "--format=%an", "--", str(rel)],
        cwd=repo_root, check=True, capture_output=True, text=True,
    ).stdout.splitlines()
    seen = dict.fromkeys(authors_raw)  # preserves order, dedups
    return PageGitMeta(
        last_updated=datetime.fromisoformat(last),
        authors=list(seen)[:5],
    )
```

`DocPage` reads the result and renders the footer.

**Cache strategy.** `lru_cache` is enough for a single `docs-build` invocation (~50 pages × 2 git calls = 100 calls; trivial). For `docs-build-all` we re-check out tags so the cache is moot.

**Exclusions** (matching today's mkdocs.yml): the helper returns `PageGitMeta(None, [])` for path patterns matching `reference/*`, `changelog.md`, `code_of_conduct.md`, `license.md`. List lives in `docs_site/build/config.py`.

**Risks.**

1. **Worktree builds (§11.7's `docs-build-all`).** When building a historical tag via `git worktree add`, the worktree's `git log` correctly returns history up to that tag — verified by spot-checking. No special handling needed.
2. **Shallow clones in CI.** `actions/checkout@v5` defaults to `fetch-depth: 1`, which breaks `git log`. Mitigation: set `fetch-depth: 0` in the docs-build workflow. Single-line CI change.
3. **Performance.** 50 pages × 2 subprocess calls = ~100 fork+exec on Linux. Linux `git` is fast (~5–10 ms per call); ~1 s total. Acceptable. If we ever hit >500 pages, consolidate into a single `git log --name-only --format=...` parse pass.

**LOC budget:** ~60 LOC (`git-revision-date-localized` equivalent) + ~40 LOC (`git-authors` equivalent), shared helper module.

### 2.4 `social` — Playwright + Django component (the big one)

**What it does today.** [Material's `social` plugin](https://squidfunk.github.io/mkdocs-material/setup/setting-up-social-cards/) generates OG-card PNG images per page (1200×630). Uses Pillow + cairosvg + a Jinja sandbox + a thread pool + a layout system to composite text + icons + background per page. Source: `material/plugins/social/{plugin.py, layout.py, config.py}` — verified by inspection, ~1800 LOC across the three files. Enabled CI-only via `enabled: !ENV [CI, false]`.

**Decision: replace with Playwright + a Django `OgCard` component.**

Rationale:

1. **Material's plugin is sophisticated** (and well-tuned) but is firmly in the "if it breaks, we don't fix it" category — we'd be vendoring 1800 LOC of someone else's font-metric and SVG-composition code, in a domain (typography + image compositing) that's far from our expertise.
2. **Playwright is already a dev dep** (E2E tests). Marginal cost of using it for one more thing is near zero.
3. **CSS authoring beats Python composition.** A 250×250 logo, a title in a system font, a subtitle, and a background image — these are 30 lines of CSS. The contributor who wants to tweak the card design opens the browser, edits CSS, hits reload. That's strictly better DX than `material/plugins/social/layout.py`.
4. **Drops the `cairosvg` LGPL-3.0 dependency entirely.** Material → cairosvg is the only LGPL in our docs stack; removing it cleans up the license story.

#### Architecture

```
content/foo.md
    -> [normal markdown pipeline]
    -> per-page metadata: {title, description, section}
    -> generate_social_cards step:
        for each page:
            html = render_to_string('og_card.html', page_meta)  # Django template
            png  = playwright_screenshot(html, viewport=(1200, 630))
            png.save(build_dir / 'assets' / 'social' / f'{page_slug}.png')
    -> emit <meta property="og:image" content="..."> in each page's <head>
```

**The `OgCard` component / template** is ~80 LOC of CSS + HTML:

```html
{# docs_site/apps/docs/components/og_card/og_card.html #}
<!DOCTYPE html>
<html>
<head><style>
  body { width: 1200px; height: 630px; margin: 0;
         font-family: 'Inter', system-ui;
         background: linear-gradient(135deg, #00897B, #004D40);
         color: white; display: flex; flex-direction: column;
         justify-content: space-between; padding: 64px; box-sizing: border-box; }
  .section { font-size: 28px; opacity: 0.7; text-transform: uppercase; letter-spacing: 0.15em; }
  .title   { font-size: 72px; font-weight: 700; line-height: 1.15; }
  .desc    { font-size: 32px; opacity: 0.85; line-height: 1.4; max-width: 900px; }
  .logo    { font-size: 36px; font-weight: 800; }
</style></head>
<body>
  <div>
    <div class="section">{{ section|default:"Documentation" }}</div>
    <div class="title">{{ title }}</div>
  </div>
  <div>
    <div class="desc">{{ description|default:"" }}</div>
    <div class="logo">django-components</div>
  </div>
</body></html>
```

**The Playwright step** is ~50 LOC:

```python
async def render_card(html: str, out: Path) -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page(viewport={"width": 1200, "height": 630})
        await page.set_content(html, wait_until="networkidle")
        await page.screenshot(path=out, type="png", omit_background=False)
        await browser.close()

async def generate_social_cards(pages: list[PageMeta], build_dir: Path) -> None:
    sem = asyncio.Semaphore(4)  # 4 parallel renders
    async def one(page):
        async with sem:
            html = render_to_string("og_card.html", {"title": page.title, ...})
            await render_card(html, build_dir / "assets/social" / f"{page.slug}.png")
    await asyncio.gather(*(one(p) for p in pages))
```

**Caching.** Same model as Material's plugin: hash `(template_source, page_metadata)`; if hash matches an existing file's recorded hash, skip. Stamp hash in a sidecar JSON. ~20 LOC. Saves rebuild time when only one page changed.

**Performance.** Playwright cold-start is ~1–2 s. Per-page render is ~100–200 ms. For 50 pages, ~30 s first build, ~2–5 s incremental. Acceptable.

#### Open items

- **Card design parity check.** Side-by-side compare a Material-rendered card and our Playwright-rendered card on the proof-of-concept page (§7). Adjust CSS until visually equal-or-better. This is the only real risk in the whole §2.4 plan.
- **Font choice.** Material's plugin ships its own bundled fonts. We use system fonts in the card CSS; if we want a specific brand font, ship the WOFF2 in `static/` and `@font-face` it. Decision deferred to Phase 5.
- **Versioning of cards.** Cards live at `docs/v/<version>/assets/social/<page>.png` — per-version, alongside the page they describe. The image hash makes deduping unnecessary; per-version copies are fine.

**LOC budget:** ~100 LOC orchestration + ~80 LOC template + ~50 LOC caching = ~230 LOC total. Compared to Material's 1800 LOC plugin we're vendoring nothing of, this is favorable.

### 2.5 `redirects` — static `<meta http-equiv="refresh">` files

**What it does today.** [mkdocs.yml](mkdocs.yml) lines 165–172 register 5 redirect mappings, e.g. `'README.md': 'overview/welcome.md'`. The plugin emits a tiny HTML page at the old URL that auto-redirects to the new one.

**Replacement.** Identical idea, ~30 LOC, no plugin needed:

```python
REDIRECTS = {
    "README.md": "overview/welcome.md",
    "release_notes.md": "releases/index.md",
    "concepts/fundamentals/defining_js_css_html_files.md": "concepts/fundamentals/html_js_css_files.md",
    "overview/contributing.md": "community/contributing.md",
    "overview/development.md": "community/development.md",
}

REDIRECT_TEMPLATE = """<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<title>Redirecting...</title>
<link rel="canonical" href="{new_url}">
<meta http-equiv="refresh" content="0; url={new_url}">
<meta name="robots" content="noindex">
</head><body>
<p>This page has moved. <a href="{new_url}">Click here</a> if you are not redirected.</p>
<script>window.location.replace({new_url_json});</script>
</body></html>
"""

def emit_redirects(build_dir: Path) -> None:
    for old_relative, new_relative in REDIRECTS.items():
        # 'README.md' -> 'README/index.html'  (or 'README.html', match Pages convention)
        out = build_dir / old_relative.replace(".md", "/index.html")
        out.parent.mkdir(parents=True, exist_ok=True)
        new_url = "/" + new_relative.replace(".md", "/")  # adjust for site_url prefix
        out.write_text(REDIRECT_TEMPLATE.format(
            new_url=new_url,
            new_url_json=json.dumps(new_url),
        ))
```

**Why both meta-refresh AND `<script>`?** Defense in depth: `<meta refresh>` works without JS (some crawlers, accessibility tools); the JS `replace()` is faster on real browsers and preserves the back-button behavior we want (the old URL is replaced rather than pushed onto history). Material's `mkdocs-redirects` plugin does the same dual-mechanism.

**`<link rel="canonical">`** tells search engines the new URL is the authoritative one — prevents the old URL from getting indexed.

**GitHub Pages compatibility.** Verified by reading the `mkdocs-redirects` source. Pages serves static HTML with `Content-Type: text/html` and respects meta-refresh. No special server config needed.

**`<meta name="robots" content="noindex">`** keeps the redirect stub out of search engines. This is an additional protection on top of the `canonical` link — belt-and-braces because Google docs don't guarantee `canonical` always wins.

**LOC budget:** ~30 LOC.

### 2.6 `minify` — switch to `minify-html`

**What it does today.** `mkdocs-minify-plugin` v0.8.0 only has `minify_html: true` enabled. Uses `htmlmin2` (a community fork of the abandoned `htmlmin`).

**Replacement.** [`minify-html`](https://github.com/wilsonzlin/minify-html), Rust-based, MIT-licensed, ships PyPI wheels for Linux/macOS/Windows. 10–100× faster than htmlmin2 (per its benchmarks) and actively maintained.

```python
import minify_html

def run_minifier(build_dir: Path) -> None:
    cfg = {
        "minify_css": True,
        "minify_js": True,
        "remove_processing_instructions": True,
        "do_not_minify_doctype": True,
        "ensure_spec_compliant_unquoted_attribute_values": True,
        "keep_closing_tags": True,            # safer for HTML5
        "keep_html_and_head_opening_tags": True,
        "keep_spaces_between_attributes": True,
        # Don't touch SVG <text> or <pre><code> — those need exact whitespace.
        # minify-html handles <pre> natively; SVG handling we verify in QA.
    }
    for html_path in build_dir.rglob("*.html"):
        src = html_path.read_text(encoding="utf-8")
        out = minify_html.minify(src, **cfg)
        html_path.write_text(out, encoding="utf-8")
```

**Why not `mkdocs-minify-plugin`?** It's tied to mkdocs (we're dropping that), and its htmlmin2 backend is significantly slower than minify-html. No reason to inherit the choice.

**Why not just skip minification?** GitHub Pages serves with `Content-Encoding: gzip`; minification still meaningfully reduces the *parsed* HTML size (which affects time-to-render in browsers). Gain is modest but cheap.

**Risk.** Aggressive minifiers occasionally break `<pre><code>` whitespace or SVG. Mitigation: the §11.10 guardrails include a snapshot test on a small set of rendered pages — any whitespace regression in `<pre>` blocks would surface immediately. If minify-html ever does break something, the option flags above can be tightened (or we skip minify entirely; 8% size reduction isn't worth chasing).

**LOC budget:** ~20 LOC including the path walk.

### 2.7 `mkdocs-macros` — rewrite as a Django template page (one file)

**What it does today.** [mkdocs.yml](mkdocs.yml) lines 214–225: Jinja2 rendering opt-in for `community/people.md`, with `people.yml` loaded as `people` variable. The page interpolates contributor data into the markdown.

**Replacement.** This one page becomes a **native Django template** instead of markdown. Bypasses the markdown pipeline entirely. The `DocPage` layout still wraps it, so the chrome is identical to other pages.

```python
# docs_site/apps/docs/views.py (or urls.py with TemplateView)
class PeoplePage(TemplateView):
    template_name = "pages/people.html"

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx["people"] = yaml.safe_load(Path("content/community/people.yml").read_text())
        return ctx
```

```html
{# content/community/people.html — a Django template, not markdown #}
{% extends "doc_page.html" %}
{% block title %}People{% endblock %}
{% block content %}
  <h2>Maintainers</h2>
  <ul>
    {% for p in people.maintainers %}
      <li>{{ p.name }} — <a href="{{ p.github }}">{{ p.handle }}</a></li>
    {% endfor %}
  </ul>
  <!-- etc. -->
{% endblock %}
```

**Why not keep it markdown + a `{% people %}` tag?** It would work, but the file is mostly tabular data interpolation — a template fits the shape better than markdown-with-tags. And it's one file. Not worth the indirection.

**Note.** This is also the only file in scope that uses `mkdocs-macros`, so dropping the plugin is a hard zero-cost win once this rewrite lands.

**Risks.** None. The schema of `people.yml` is small and stable.

**LOC budget:** ~40 LOC (view + template).

---

## 3. License audit across all docs deps

Per Juro's §11.7 feedback request. License-by-license:

### 3.1 Licenses in current docs build

| Package | Version | License | Notes |
|---|---|---|---|
| `mkdocs-material` | 9.7.6 | **MIT** | Plugin code we replace; we still use `material` icons until §11.11 design |
| `mkdocs-minify-plugin` | 0.8.0 | **MIT** | Dropped — replaced by `minify-html` |
| `mkdocs-redirects` | 1.2.2 | **MIT** | Dropped — replaced by our static stub generator |
| `mkdocs-gen-files` | 0.6.0 | **MIT** | Dropped — replaced by Django management commands |
| `mkdocs-awesome-nav` | 3.3.0 | **MIT** | Dropped — replaced by our nav YAML loader |
| `mkdocs-include-markdown-plugin` | 7.2.0 | **Apache-2.0** | Dropped — no in-scope usage |
| `mkdocs-macros-plugin` | 1.5.0 | **MIT** | Dropped — one file rewritten as Django template |
| `markdown-exec` | 1.12.1 | **ISC** (verified via PyPI; metadata empty) | Dropped — 0 usages |
| `mkdocstrings` | 1.0.1 | **ISC** (verified via PyPI; metadata empty) | Dropped — replaced by §11.5 ApiReference component |
| `mkdocstrings-python` | 2.0.1 | **ISC** | Dropped |
| `griffe` | 1.15.0 | **ISC** | **Kept** — §11.5 vendor as runtime dep |
| `mike` | 2.1.3 | **BSD-3-Clause** | §11.7 vendors `versions.py` (270 LOC). BSD-3 permits this with attribution |
| `pygments` | 2.19.2 | **BSD-2-Clause** | Kept — drives `djc_py` highlighting |
| `pymdown-extensions` | 10.21.3 | **MIT** | Kept — §11.6 markdown directives |
| `markdown` | 3.10.1 | **BSD-3-Clause** (verified via PyPI; metadata empty) | Kept — markdown rendering |
| `jinja2` | 3.1.6 | **BSD-3-Clause** | Transitive only |
| `cairosvg` | 2.9.0 | **LGPL-3.0-or-later** | **Drop** — only pulled by Material `social` plugin; replacing social with Playwright removes it |
| `pillow` | 12.2.0 | **MIT-CMU** (Pillow's own historical license, MIT-compatible) | Drop unless we want it for OG-image fallback; Playwright covers it |
| `playwright` | 1.57.0 | **Apache-2.0** | **Kept** — used for social cards + existing E2E tests |

### 3.2 Cross-cutting findings

- **One non-permissive license in the stack today: cairosvg (LGPL-3.0).** This spike's social-card replacement removes it. Net effect of the migration: docs deps become permissively-licensed end to end.
- **All other licenses (MIT, BSD-2, BSD-3, ISC, Apache-2.0, MIT-CMU) are permissive** and compatible with django-components' MIT license. No license alert anywhere.
- **Vendoring discipline.** We vendor `mike/versions.py` (§11.7 — BSD-3) and `griffe` patterns (§11.5 — ISC). Both require attribution in the file headers; both spikes already call this out.
- **No copyleft anywhere after the migration.** Even LGPL is gone.

### 3.3 Attribution checklist

When we vendor:

- Top of any file lifted from another project: copy the original copyright line + license declaration.
- New file in `docs_site/apps/docs/_vendor/`: prefix with `_vendor` so reviewers know it's external.
- `pyproject.toml` keeps the original packages as dev-deps for the migration period so the original `LICENSE` text travels with the install. We remove the original packages from `pyproject.toml` only after the migration cuts over and the vendored copy is the only path.

---

## 4. `docs-build-check` — the CI gate command

Per Juro's §11.7 feedback: "we can implement also the `docs-build-check` command - I suppose that could then live in CI as a gate?" — yes, with a specific shape.

### 4.1 What it does

```
uv run docs-build-check         # exit 0 if build is clean; non-zero on any failure
```

- Runs the full `docs-build` pipeline against the working tree.
- Writes output to a temp dir, **not** to `docs/v/<version>/`.
- Discards the temp dir on success.
- Runs every §11.10 guardrail on the temp dir output:
    1. Internal link check
    2. Anchor check
    3. API symbol check
    4. Example-page contract check
    5. Snapshot test (syrupy) for a curated set of pages
    6. Cross-version link check (against the previous committed `docs/v/*`)
- Emits a structured report to stdout.

### 4.2 Why not just run `docs-build`?

`docs-build` writes to `docs/v/<version>/` on disk. That's the right side effect in a release pipeline; the wrong side effect in a PR check. `docs-build-check`:

- Writes nothing (no spurious git diffs).
- Doesn't refresh the `latest/` alias.
- Doesn't update `docs/v/versions.json`.
- Surfaces guardrail failures with non-zero exit; `docs-build` itself is intentionally permissive (it builds even if a link is broken, because Phase-1-bootstrap reality requires being able to ship a partial site).

### 4.3 CI wiring

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
        with: { fetch-depth: 0 }   # required for git-revision metadata (§2.3)
      - uses: astral-sh/setup-uv@v3
      - run: uv sync --group docs
      - run: uv run playwright install chromium  # for social cards
      - run: uv run docs-build-check
```

### 4.4 What does NOT run in `docs-build-check`

- Social-card generation. It's slow (~30 s) and not load-bearing for PR review. Run it only in the release pipeline.
- Minification. Same reason: not load-bearing for correctness.
- The full `docs-build-all` bootstrap. Reserved for explicit re-bootstrap moments.

A separate `--full` flag enables the slow steps when needed:

```
uv run docs-build-check --full   # includes social cards + minification snapshot
```

### 4.5 LOC budget

~80 LOC orchestration + reuses every existing piece. The guardrails themselves are in §11.10 (~300 LOC across all 6 checks).

---

## 5. Implementation order

The plugin replacements don't all land in one PR. Here's the order that gives us a usable system at each step:

**Step 1 — Phase 1 of the migration (single section ported):**
- `gen-files` → Django management command shape (§2.1)
- `awesome-nav` → nav YAML loader (§2.2)
- `redirects` → static stub generator (§2.5)
- `mkdocs-macros` → Django template page (§2.7)

Why first: these are needed before *any* page can render. They unblock §11.4's markdown pipeline and §4.7's three-pass flow.

**Step 2 — Phase 3 onward (the rest of the markdown pages):**
- `git-revision-date-localized` + `git-authors` → DIY subprocess + cache (§2.3)
- `markdown-exec`, `include-markdown` → drop entirely (verified no in-scope use)

**Step 3 — Phase 5 (search, versioning, social cards):**
- `social` → Playwright + Django component (§2.4) — biggest single LOC item, lands when we're confident the rest works
- `minify` → minify-html (§2.6) — last step before cutover

**Step 4 — Phase 6 (cutover):**
- Delete `mkdocs.yml` and all mkdocs deps from `pyproject.toml`.
- Verify `docs-build-check` passes against the new pipeline only (no fallback path).

---

## 6. Where the code lives

```
docs_site/
    apps/
        docs/
            build/
                __init__.py
                commands/
                    docs_build.py            # the `docs-build` management command
                    docs_build_all.py        # the `docs-build-all` orchestrator (§11.7)
                    docs_build_check.py      # the `docs-build-check` CI gate (§4)
                git_metadata.py              # §2.3
                redirects.py                 # §2.5
                minifier.py                  # §2.6
                nav.py                       # §2.2 awesome-nav replacement
                release_notes.py             # §2.1 port of gen_release_notes.py
                social_cards.py              # §2.4
            components/
                og_card/
                    og_card.html             # §2.4
                doc_page/
                    doc_page.html            # the layout wrapper
            _vendor/
                mike_versions.py             # §11.7 vendor
        pages/
            people/                          # §2.7 the one Django-template page
                people.html
                people.py                    # view
content/
    _nav.yml                                 # §2.2
    community/people.yml                     # consumed by people view
    ...
```

---

## 7. Recommended first concrete step

**Spike-validate the redirect + minify pieces during Phase 1.**

Why these two first:

- They're tiny (~50 LOC combined).
- They have **zero dependency on the rest of the build pipeline.** Both run on an already-built `site/` dir.
- They prove the post-build pass shape that social cards (§2.4) will need.
- A failure here would force a rethink of the build dir layout, so getting it wrong cheaply is valuable.

Concretely: in Phase 1, after `docs-build` produces a single-page HTML output, wire up `emit_redirects()` and `run_minifier()` as post-build steps. Verify output by:
1. Hitting the moved URL in a browser, confirming the redirect.
2. Diffing the pre- and post-minify HTML byte count.
3. Visual diff of the rendered page (no whitespace regressions).

If both work end-to-end, we have a credible build pipeline for everything else to plug into.

---

## 8. Risks & open items

### 8.1 Risks during execution

1. **Social-card visual regression.** Mitigation: side-by-side comparison page generated during Phase 5; only cut over when Juro signs off on the look. Fallback: keep Material's `social` plugin running on the old `gh-pages` branch for one release cycle while the new card design stabilizes.
2. **`minify-html` whitespace handling.** Mitigation: §11.10's snapshot test catches regressions. Fallback flags exist in `minify-html` config; aggressive minification is opt-in.
3. **Nav YAML migration drift.** When porting the auto-generated mkdocs nav to our explicit `_nav.yml`, easy to miss a section. Mitigation: a one-time validation script that diffs the old mkdocs sitemap against the new nav; should produce zero entries-only-on-one-side.
4. **Shallow CI clones break git metadata.** Mitigation: `fetch-depth: 0` in CI workflows. Documented as a guardrail in §11.10.

### 8.2 Items deferred to other spikes

- **Sidebar component design** — §11.11.
- **Specific link-checking and anchor-checking logic** — §11.10.
- **Dark/light toggle** — §11.1.G.1.
- **Search index emission** — §11.1.
- **Anchor-scheme codemod** — §11.5 + §11.6.F.
- **Older mkdocs-built versions on `gh-pages`** — §11.8 (and per Juro's §11.7 note, revisited after Phase 7).

### 8.3 Items deferred to implementation

1. **Font choice for OG cards.** Phase 5 design decision.
2. **Caching strategy for social cards.** Sketched in §2.4; refine when we know how often we re-render in the release pipeline.
3. **Whether to remove `pillow` from deps.** It's small and might be useful for one-off image work; decision when we're cleaning up `pyproject.toml` at cutover.
4. **`minify-html` config tuning.** Start with the conservative flag set in §2.6 and relax only after the snapshot tests pass on every page.

---

## 9. Where this feeds back

- **§2.1 of the main design doc** — every row in the build-pipeline plugin table now has a concrete owner spike + verdict. This spike is the source of truth for the rows §11.5, §11.6, §11.7, §11.1, §11.10, §11.11 don't claim.
- **§4.1** — the `docs_site/` layout adds the modules listed in §6 above.
- **§4.6 (versioning)** — `docs-build-all` orchestration step list extends to include `emit_redirects` and `run_minifier` between manifest update and final commit.
- **§4.8 (dev workflow)** — adds `docs-build-check` to the `[project.scripts]` entry points.
- **§5 / Phase plan** — confirms Phase 5 is the right home for `social` + `minify`; Phase 1 must include `gen-files` replacement, nav loader, redirect stub, and the people-page rewrite.
- **§7 (license)** — confirms the migration removes the one LGPL dep (`cairosvg`). All remaining licenses are permissive.
- **§11.10 (guardrails)** — `docs-build-check` is the CI host for every guardrail. §11.10 designs the checks; §11.9 wires them.

---

## 10. Quick reference — every mkdocs plugin, one-line verdict

For a fast skim later:

- `autorefs` → §11.5 bracket-cross-refs
- `include-markdown` → drop (unused in scope)
- `gen-files` → Django management command pipeline (§2.1)
- `awesome-nav` → tiny YAML loader (§2.2)
- `git-revision-date-localized` → subprocess + cache (§2.3)
- `git-authors` → subprocess + cache (§2.3)
- `markdown-exec` → drop (unused in scope)
- `search` → §11.1 Pagefind (or DIY Lunr)
- `social` → Playwright + `OgCard` component (§2.4)
- `mike` → §11.7 vendor `versions.py`
- `redirects` → static `<meta refresh>` stubs (§2.5)
- `minify` → `minify-html` Rust crate via PyPI wheels (§2.6)
- `mkdocstrings` → §11.5 griffe + `ApiReference` component
- `macros` → one Django-template page (§2.7)
