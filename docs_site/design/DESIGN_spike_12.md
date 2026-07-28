# Spike 11.12 — SEO and AIO audit

**Status:** spike complete
**Date:** 2026-06-01
**Feeds back into:** [DESIGN_djc_docs_site.md §4.1, §4.6, §7.2, §11.9, §11.10, Phase 1 + Phase 5](DESIGN_djc_docs_site.md)
**Spike question:** What is the complete set of SEO (classic search-engine) and AIO (AI / LLM consumer) features the new docs site should ship with? §11.10 §10.2 deferred this; we need a decision before cutover so the new site is not weaker on discovery than the current Material build.

This spike is the **terminal authority for SEO/AIO dispositions** on the new docs site. Where another spike already decided (§11.9 social cards, §11.10 single-h1 guardrail, §7.2 anchors, §4.6 versioning), this spike inherits and cross-links; where no spike has decided, this spike decides.

---

## 0. TL;DR verdict

**SHIP across the board, with three load-bearing additions over what Material gives us today.**

Current site is weaker than people think: in production, every page emits only `viewport`, the site-level `description`, and `canonical`. **No OG cards, no Twitter cards, no JSON-LD, no per-page description, no `llms.txt`, no `.md` companion URLs, no AI-bot policy.** The migration is the moment to fix that.

**Three load-bearing additions** (all small, all high-leverage):

1. **Ship `llms.txt` + `llms-full.txt`.** Auto-generated from the nav YAML and the page index. ~120 LOC. Sets us up to land well in ChatGPT / Claude / Perplexity / Phind / Kagi search. Cost is trivial; benefit is meaningful and growing month over month.
2. **Ship `.md` companion URLs.** Every `/path/page/` also serves at `/path/page.md` — raw markdown with front-matter stripped, includes expanded, no rendering. Pattern adopted by Stripe, Vercel, Next.js docs, Tailwind docs. **~50 LOC** in our case (we already have the markdown; just write it next to each `index.html`). Highest leverage AI-discovery feature we can ship.
3. **Per-page description, OG, JSON-LD.** The `DocPage` chrome already owns the `<head>` block (§11.11 §3). Threading per-page description and JSON-LD `TechArticle` / `BreadcrumbList` into it costs ~80 LOC and dramatically improves how search engines surface us.

**Three near-free wins** courtesy of the new architecture:

- **Per-version `noindex` on `/v0.x/` for `x < latest`.** Stops historical versions diluting search rank against `/latest/`. One line in `DocPage`.
- **Lighthouse CI on a sampled page set.** Block PRs that regress Performance / Accessibility / SEO / Best Practices below thresholds. ~60 LOC workflow + sample list. Aligns with §11.10's guardrail philosophy.
- **Auto-generated 404 page with search.** Inherit from `DocPage`, embed the Pagefind search bar (§11.1). Trivial.

**Three deferrals (with reasons):**

- **`tags.json` (template-tag DSL manifest for AI agents authoring Django-components templates).** Worth shipping but **defer to post-cutover.** Requires close coordination with §11.5 (per-API-kind discovery) to share the same data source. Lower priority than ships above.
- **Comprehensive a11y audit.** Belongs to §11.11 follow-up (already deferred). We add the *minimum* a11y posture (alt text linting, single-h1) here; full audit later.
- **Real-time SEO monitoring (Search Console alerting).** Operational concern; out of scope.

**One decision resolved:**

- **AI-bot policy: default-allow** (Juro confirmed 2026-06-01). GPTBot, ClaudeBot, anthropic-ai, Google-Extended, PerplexityBot, CCBot, and other major AI training and search crawlers are allowed in `robots.txt`. Documented in `community/ai_bot_policy.md` so the stance is explicit, reviewable, and revisable.

**Three things that bite the migration if we're not careful:**

1. **Anchor migration (§7.2) interacts with this spike.** The new short anchor scheme (`#Component` vs. `#django_components.Component`) breaks inbound links from search indexes for ~6-12 months. We emit aliases (already decided in §7.2); this spike adds the deprecation timer and a guardrail check (§11.10 follow-up).
2. **Canonical URLs for versioned pages.** Material's default has every page canonical-to-itself, including `/v0.149/foo/` canonical to `/v0.149/foo/`. That competes with `/latest/foo/`. **Recommendation: versioned pages canonical to `/latest/` for the *current* counterpart; `noindex` if the page no longer exists in latest.** New behaviour, not parity.
3. **Single `<h1>` per page.** Markdown source starts with `# Heading`, but `DocPage` chrome inserts the page title in `<header>` (§11.11 §3). If both render as `<h1>`, we have two — bad for SEO and a11y. Resolution: chrome uses `<header><h1>...</h1></header>` and content's first `#` becomes a `<h1>` only if the page has no front-matter title; otherwise it shifts to `<h2>` or is dropped. Codified in §11.10 guardrails.

**Total new code surface** across this spike: **~400–500 LOC**, distributed across `DocPage` head block (~100), JSON-LD generator (~80), `llms.txt` + `llms-full.txt` builders (~120), `.md` companion writer (~50), Lighthouse CI workflow (~60), AI-bot policy file (~30 lines), and guardrail extensions (~50).

**Recommended first concrete step:** in Phase 1, ship the unified `DocPage` `<head>` block with viewport + canonical + per-page description + per-version `noindex` wiring. That's <150 LOC and lands the SEO floor; everything else builds on top.

---

## 1. Current state — what Material gives us today

Verified from the local `site/` build and from production (`curl https://django-components.github.io/django-components/latest/overview/welcome/`).

### 1.1 What is in the `<head>` today

Every page emits exactly this SEO-relevant set:

```html
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="A way to create simple reusable template components in Django.">
<link rel="canonical" href="https://django-components.github.io/django-components/latest/overview/welcome/">
<meta name="generator" content="mkdocs-1.6.1, mkdocs-material-9.7.6">
<title>Welcome to Django Components - Django-Components</title>
<meta name="google-site-verification" content="vQA3d50F2ByQxG0eB6b0YoPnYW9gZo8xnd6HKhCyuys">
```

That is the entire SEO surface. Note in particular:

- **`description` is site-level, not per-page.** Every URL gets the same string. Search-engine snippets default to the meta description when present and trustworthy — so every page snippet today reads identically until Google decides to synthesise from body content. We are leaving snippet quality on the table.
- **No `og:*`, no `twitter:*`.** Sharing the URL on Slack, Discord, Bluesky, X, or LinkedIn produces an ugly unfurl with no image and no description.
- **No `<meta name="robots">`.** Every page is implicitly `index, follow`, including all historical versions. They compete with `/latest/` in search.
- **No JSON-LD.** No `TechArticle`, no `BreadcrumbList`, no `SoftwareSourceCode`. Search-engine entity understanding has to be inferred entirely from body text.
- **No `theme-color`.** Browsers can't tint the URL bar to match the site.

### 1.2 What's at the site root

- **`/sitemap.xml`** ✓ Auto-generated. Lists every page with `<lastmod>` from build time. No `<priority>`, no `<changefreq>`. Adequate but minimal.
- **`/robots.txt`** ✓ Auto-served by GitHub Pages — minimal, allows everything, points at sitemap. We do not control it from mkdocs.
- **`/sitemap.xml.gz`** ✓ Also emitted by mkdocs.
- **`/objects.inv`** ✓ mkdocstrings cross-ref inventory. **Useful for AIO** as a structured symbol map; we should preserve an equivalent.
- **`/llms.txt`** ✗ 404.
- **`/.well-known/`** ✗ Not present.
- **`<path>/page.md`** ✗ Not emitted; raw markdown not addressable at all.

### 1.3 What the `social` plugin actually does today

Worth a closer look because the §11.9 verdict already replaced this plugin (Playwright + Django-rendered `OgCard`). The current behaviour:

- **Enabled only on CI** (`enabled: !ENV [CI, false]`). Local builds get no OG cards at all.
- **Generates PNG only.** Does NOT inject `<meta property="og:image">` into the page head by default unless the social plugin's `meta` feature is enabled. We do not have that feature enabled.
- **In production today the OG image PNGs exist on disk** at `assets/images/social/<slug>.png` but **no `<meta>` tags reference them.** Verified by curl. Social unfurls today therefore use whatever Twitter/Facebook scrape from the body or fall back to the favicon.

That is a latent quality bug in the current site. Migrating to our own `OgCard` + explicit `<meta property="og:image">` wiring closes it.

### 1.4 Front-matter usage in current docs

- **Exactly one file uses front-matter:** [docs/README.md](docs/README.md) sets `title: Welcome to Django Components`. Everything else gets a title derived from the first `# Heading`.
- **No page sets a per-page `description:`** anywhere.
- **No page sets a custom OG image or social card.**

The migration adds a front-matter schema (§5.2 below). Adoption is opt-in per page; the defaults handle the unannotated 99%.

### 1.5 Anchor scheme today

All API symbols anchored as `#django_components.Component`, `#django_components.Component.render`, etc. — the full dotted path. §7.2 of the main doc commits to shortening these to `#Component`, `#Component.render` while emitting legacy aliases.

This spike adds the SEO consequence: emit a deprecation timer on the alias so it stops appearing in fresh search-index crawls after the deprecation window (recommended: 12 months).

---

## 2. Group A — SEO (classic search engines)

### 2.A.1 Canonical URLs

**Verdict: SHIP — but change the strategy from Material's default.**

**Why.** Material today emits `<link rel="canonical" href="self">` on every page, including every historical version. That means `/v0.148/foo/`, `/v0.149/foo/`, `/v0.150/foo/`, and `/latest/foo/` all advertise themselves as canonical. Search engines then have to choose, and they sometimes choose the older versions because they accumulated more links. This is a known anti-pattern for versioned docs.

**How.** The `DocPage` chrome decides the canonical URL by walking three rules:

1. If the page exists in `/latest/`, the canonical URL is the `/latest/` counterpart. Versioned URLs (`/v0.148/foo/`) canonical to `/latest/foo/`.
2. If the page does NOT exist in `/latest/` (the symbol was removed, the page was renamed and not redirected), the canonical URL is the page itself, AND the page emits `<meta name="robots" content="noindex,follow">` so it stops competing in fresh indexes.
3. `/latest/` itself is always canonical to itself.

Implementation: the build's manifest already knows which pages exist in each version (§4.6). Computing the canonical at `DocPage` render time is a dict lookup.

**LOC.** ~30. Lives in `DocPage` and consumes a `version_manifest` injected by the build.

**Owner.** This spike (decision), §4.1 (implementation).

### 2.A.2 Sitemap

**Verdict: SHIP, upgrade scope.**

**Why.** Current `sitemap.xml` only lists pages with `<loc>` and `<lastmod>` from build time. We can do better in three ways:
1. **`<lastmod>` should come from `git log -1 --format=%cI`** for the source markdown, not the build date. Build date changes every CI run even if the content didn't.
2. **Only `/latest/` URLs in the sitemap.** Historical versions get `noindex`'d (§2.A.1) so they should not appear in the sitemap either, which is what Google recommends.
3. **`<changefreq>` and `<priority>` are widely ignored by Google** (their own docs say so since 2015), but `<priority>` is still useful for Bing/Yandex. Set sensibly: `1.0` for `/latest/`, `0.8` for getting-started, `0.6` for concepts/reference, `0.4` for community.

**How.** Build-time pass after `docs-build` finishes. Walk the rendered page set, group by URL prefix, look up git lastmod per source file, write XML.

**LOC.** ~80. New file `apps/docs/sitemap.py`. Re-uses git-walk helper from §11.6.C.

**Owner.** This spike + §11.9 (which already noted sitemap as a replaceable plugin).

### 2.A.3 robots.txt

**Verdict: SHIP — explicit, not GitHub-Pages-default.**

**Why.** GitHub Pages serves a minimal default robots.txt for us today. We want to control it for three reasons: (a) point at our own sitemap path, (b) disallow `/v0.x/` for `x < latest`, (c) make our AI-bot policy explicit and reviewable (§2.B.10).

**How.** Static file at `apps/docs/static/robots.txt`. Content:

```
User-agent: *
Allow: /
Disallow: /v0.135/
Disallow: /v0.136/
...
Disallow: /v0.149/
# /v0.150/ and /latest/ allowed
Sitemap: https://django-components.github.io/django-components/sitemap.xml

# AI bots — explicit allow (see /community/ai_bot_policy/)
User-agent: GPTBot
Allow: /
User-agent: ClaudeBot
Allow: /
User-agent: anthropic-ai
Allow: /
User-agent: Google-Extended
Allow: /
User-agent: PerplexityBot
Allow: /
User-agent: CCBot
Allow: /
```

The `Disallow: /v0.x/` list is auto-generated at build time from the version manifest (every version except `latest` and the most recent N — let's say N=2 — gets disallowed). That way the file stays in sync with releases.

**LOC.** ~40 (generator + static template).

**Owner.** This spike + §4.6 (manifest source).

**Note on the AI-bot section.** The block above is the default-allow stance. Decision needed from Juro before cutover — see §6 for the table.

### 2.A.4 OG / Twitter cards

**Verdict: SHIP — full per-page metadata + Playwright-generated image (§11.9 already decided the image piece).**

**Why.** §11.9 decided we generate OG PNGs via Playwright screenshotting a Django-rendered `OgCard`. That gets us images. **But we also need the `<meta>` tags pointing at them.** Without the tags, social-media unfurls have nothing to grab. Today's prod site has the PNGs but no tags — a latent quality bug we close as part of the migration.

**How.** `DocPage` `<head>` block emits, per page:

```html
<meta property="og:type" content="article">
<meta property="og:title" content="{{ page.title }}">
<meta property="og:description" content="{{ page.description }}">
<meta property="og:url" content="{{ page.canonical_url }}">
<meta property="og:image" content="{{ page.og_image_url }}">
<meta property="og:site_name" content="Django Components">
<meta property="og:locale" content="en_US">

<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{{ page.title }}">
<meta name="twitter:description" content="{{ page.description }}">
<meta name="twitter:image" content="{{ page.og_image_url }}">
```

Description sources from front-matter `description:` if set, otherwise the first paragraph of body content (stripped to 155 chars at a word boundary). OG image points at the per-page PNG generated in §11.9.

**LOC.** ~40 in `DocPage` template; ~30 in a `extract_description` helper (with proper paragraph detection — skips admonitions, `_New in version_` lines, navigational notes).

**Owner.** This spike (tag wiring) + §11.9 (image generation).

### 2.A.5 Page titles

**Verdict: SHIP — formalise current pattern.**

**Why.** Current pattern is `<Page Title> - Django-Components`. Works fine. The migration just needs to keep it deliberate, not accidental.

**How.** `DocPage` builds the `<title>` from `{{ page.title }} - {{ site.name }}`. Page title comes from front-matter `title:` if set, otherwise the first `# Heading` of the markdown source. The homepage uses just `{{ site.name }}` (no prefix).

**Caveat.** The separator is `-` not `·` or `|` because Google explicitly recommends `-` and historically rewrites others (it doesn't anymore, but parity with intent is cheap).

**LOC.** ~10 in `DocPage`.

**Owner.** This spike + §11.11 (which already specifies the chrome).

### 2.A.6 Meta description (per-page)

**Verdict: SHIP — biggest snippet-quality win.**

**Why.** Today every page has the same site-level description. Search-result snippets are therefore identical until Google synthesises body text. Per-page descriptions are the cheapest SEO win we have.

**How.** Three-source priority for the description:

1. Front-matter `description:` (authored).
2. First non-trivial paragraph (extracted, 155-char cap at word boundary). "Non-trivial" excludes:
   - Admonitions (`!!! note`, `> **Note**`).
   - `_New in version X.Y_` lines.
   - Single-link or single-image-only paragraphs.
   - Tables.
3. Fall back to the site-level description.

The extractor lives in the markdown preprocessing pipeline (§4.7) and runs once per page during build.

**LOC.** ~50 for the extractor with edge-case handling.

**Owner.** This spike + §4.7.

**Audit note.** Once the extractor is shipped, run it across all current pages and **commit the extracted descriptions back into front-matter** for the top-50 most-trafficked pages. That way the description is reviewable and editable, not regenerated on every build.

### 2.A.7 Structured data (JSON-LD)

**Verdict: SHIP — `BreadcrumbList` + `TechArticle`; SKIP `SoftwareSourceCode` and `HowTo`.**

**Why.**

- **`BreadcrumbList`** — high value, low cost, displayed in Google search results as the breadcrumb trail above the snippet. Every page gets one.
- **`TechArticle`** — appropriate type for technical documentation pages. Helps Google understand "this is documentation about X" entity-wise. Modest value; effectively free once we have the data.
- **`SoftwareSourceCode`** on `/latest/` home and getting-started: **skip.** Google rarely renders this for docs sites; the schema fits libraries like a glove but the visible payoff is invisible. Reconsider only if §11.12 follow-up data shows it's actually rendered.
- **`HowTo`**: **skip.** Documented as deprecated by Google for non-recipe use; recent guidance recommends not using `HowTo` for general technical content. Was on the original spike list as a maybe; skip after verification.

**How.** `DocPage` emits `BreadcrumbList` always, derived from the nav YAML (every page knows its parent chain from §11.11 §3.5). Emits `TechArticle` on content pages (not on the homepage or community pages — they get different types or none).

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    {"@type": "ListItem", "position": 1, "name": "Concepts", "item": ".../latest/concepts/"},
    {"@type": "ListItem", "position": 2, "name": "Fundamentals", "item": ".../latest/concepts/fundamentals/"},
    {"@type": "ListItem", "position": 3, "name": "Components in Templates"}
  ]
}
</script>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Components in Templates",
  "description": "{{ page.description }}",
  "datePublished": "{{ page.first_published }}",
  "dateModified": "{{ page.last_modified }}",
  "author": {"@type": "Organization", "name": "django-components contributors"},
  "publisher": {"@type": "Organization", "name": "django-components", "url": "..."}
}
</script>
```

`first_published` and `last_modified` come from the `git log` lookups (§11.9 §2.3, §11.6.C).

**LOC.** ~80 across `DocPage` + a `jsonld.py` builder.

**Owner.** This spike.

**Validation.** Google's Rich Results Test (`rich-results-test.google.com`) accepts JSON-LD strings via URL. Wire it into the Lighthouse CI sample (§2.C.4) so we catch malformed JSON-LD in PRs.

### 2.A.8 Heading hierarchy (one `<h1>` per page)

**Verdict: SHIP — codify via §11.10 guardrail.**

**Why.** SEO and a11y both insist on exactly one `<h1>`. The migration risks producing two: `DocPage` chrome wraps the page title in `<header><h1>...</h1></header>`, and the markdown source typically starts with `# Heading`. Both rendered = two `<h1>`.

**How.** Three-part resolution:

1. **Chrome's `<h1>` is canonical.** It uses `{{ page.title }}` (front-matter or first `# Heading`).
2. **Markdown's first `# Heading` is consumed by the title extractor and removed from the body.** Same behaviour mkdocs has today.
3. **Markdown headings `##` and below render normally.** The single-h1 invariant holds.
4. **A guardrail in §11.10 §3** asserts each page emits exactly one `<h1>`. Fails the build if violated.

**LOC.** ~10 markdown preprocessor change + ~15 guardrail check. Add to §11.10 §3.

**Owner.** This spike (decision); §4.7 (preprocessor); §11.10 (guardrail).

### 2.A.9 Image alt text

**Verdict: SHIP — guardrail-enforced, content-audited.**

**Why.** SEO and a11y. Today's docs are inconsistent (some images lack alt, some have placeholder alt). Cleaning this up has compounding benefit: better a11y, better image search, and LLMs reading `.md` companion URLs (§2.B.2) get usable image descriptions.

**How.**

- **Guardrail (§11.10 §3 extension):** every `<img>` in the rendered HTML must have a non-empty `alt`. Build fails otherwise.
- **One-time audit pass during Phase 3** (rest of markdown pages migration): grep for images, fill in alt text where missing.
- **For diagrams generated by tools** (no current usage, but possible future): the source authoring tag carries an `alt=` attribute that flows through.

**LOC.** ~15 guardrail + audit-pass content edits.

**Owner.** This spike (decision); §11.10 (guardrail); Phase 3 (content).

### 2.A.10 Internal link density

**Verdict: SKIP automation; manual audit pass.**

**Why.** "Each concept page links to ≥1 reference and ≥1 example" is a soft quality bar — automating it would either rubber-stamp the status quo or generate noise. The migration is already producing the cleanest version of every page (Phase 3 rewrites them); use that opportunity to audit linking by eye.

**How.** During the Phase 3 mechanical port, the reviewer (likely Juro) eyeballs each section's link density. No tooling.

**LOC.** 0.

**Owner.** Phase 3 reviewer.

### 2.A.11 HTTPS + www → apex redirect

**Verdict: SHIP, but it's free.**

**Why.** GitHub Pages handles HTTPS by default. We don't have a `www.` apex — our domain is `django-components.github.io/django-components/`, so there's no www redirect to manage.

**How.** Nothing required; just verify with curl during cutover.

**LOC.** 0.

**Owner.** Cutover checklist.

### 2.A.12 404 page

**Verdict: SHIP — custom 404 with search box.**

**Why.** A useful 404 keeps visitors who hit broken inbound links. Material gives us a generic 404. Ours can do better by embedding the Pagefind search bar (§11.1) and a "common destinations" list.

**How.** `404.html` is generated by rendering a `NotFoundPage` Django component using the `DocPage` chrome. It has:

- A clear "Page not found" headline.
- The Pagefind search bar pre-mounted, ready to query.
- A list of top destinations: `/latest/getting_started/`, `/latest/concepts/`, `/latest/reference/`.
- A link to file an issue if a recently-existed page is missing.

The page is published as `/404.html` at site root; GitHub Pages serves it automatically on any 404 within the deployed path.

**LOC.** ~80 (Django component + integration).

**Owner.** This spike + §11.1 (search component).

### 2.A.13 Anchor migration interaction with §7.2

**Verdict: SHIP — already decided in §7.2; this spike adds the deprecation timer and a guardrail.**

**Why.** §7.2 commits to dropping the `django_components.` prefix from API anchors and emitting legacy aliases. The SEO consequence: search engines may keep the old anchors in their index for months. We need to make sure aliases keep working long enough for the index to refresh, but not forever (an alias that lingers indefinitely is a maintenance liability).

**How.**

- **Aliases emit for 12 months** from the date the new anchor scheme ships.
- **Each alias gets a comment in the rendered HTML** with the deprecation date, so future maintainers see when to remove.
- **A guardrail (§11.10 follow-up)** flags any markdown page that still uses the long-form anchor in its source after a configurable date.

**LOC.** ~30 for the alias emitter + ~20 for the guardrail.

**Owner.** §7.2 + §11.10 + this spike (timer).

### 2.A.14 Page speed / Core Web Vitals

**Verdict: SHIP — Lighthouse CI on sample pages.**

**Why.** Static HTML with our own minimal CSS and JS should crush this. We just need to *prove* it and stop regressions in PRs.

**How.** GitHub Actions workflow that, on every PR touching `docs/`, builds the site, serves it locally, and runs Lighthouse against a 5-page sample (homepage, getting-started, a concept page, a reference page, the fragments example). Asserts thresholds:

- Performance ≥ 95
- Accessibility = 100
- Best Practices = 100
- SEO = 100

PRs that drop below get a failing check. The workflow uses `lhci/cli` with a small `lighthouserc.json` in the repo root.

**Budget targets** (informational, not hard thresholds): LCP < 1.5s, CLS = 0, INP < 100ms. With a fully static site and zero external requests, all three are trivial to hit.

**LOC.** ~60 workflow + ~30 sample config.

**Owner.** This spike + Phase 5.

---

## 3. Group B — AIO (AI / LLM consumers)

### 3.B.1 `llms.txt` + `llms-full.txt`

**Verdict: SHIP both.**

**Why.** [`llms.txt`](https://llmstxt.org/) is a proposed convention (Jeremy Howard, late 2024) for sites publishing a markdown index aimed at LLMs. Adoption is accelerating across docs sites in 2025-2026 (Pydantic, Cloudflare, Vercel, Stripe, Anthropic). It's a one-shot fetch that gives an AI agent the site's table of contents and per-section pointers.

Cost is genuinely small (~120 LOC), benefit grows month over month as more retrieval pipelines key off the convention. Skipping this would be leaving a free win on the table.

**How.** Two files generated at build time from the nav YAML and page index:

**`/llms.txt`** — short index. ~80 lines for our site:

```
# Django Components

> A way to create simple reusable template components in Django.

## Getting started

- [Installation](https://django-components.github.io/django-components/latest/getting_started/installation/): Install django-components and set up your first project.
- [Your first component](https://django-components.github.io/django-components/latest/getting_started/your_first_component/): Write your first reusable component.
- [Adding slots](https://django-components.github.io/django-components/latest/getting_started/adding_slots/): Parameterize templates with named slots.
...

## Concepts

- [Component fundamentals](https://django-components.github.io/django-components/latest/concepts/fundamentals/component/): The Component class lifecycle and rendering pipeline.
- [Render API](https://django-components.github.io/django-components/latest/concepts/fundamentals/render_api/): get_template_data, get_js_data, get_css_data.
...

## API reference

- [Component](https://django-components.github.io/django-components/latest/reference/api/#Component): The Component base class.
- [Slot](https://django-components.github.io/django-components/latest/reference/api/#Slot): Named template slot.
...

## Optional

- [Migration from safer-staticfiles](https://django-components.github.io/django-components/latest/migrating_from_safer_staticfiles/)
- [Release notes](https://django-components.github.io/django-components/latest/releases/)
```

The per-page description comes from §2.A.6's extractor. The "Optional" section follows the llms.txt convention (lower-priority links).

**`/llms-full.txt`** — full content concatenation. Every content page's raw markdown (front-matter stripped, includes expanded, `{% example %}` tags expanded into static code + a "Live demo at <URL>" line, snippet directives expanded) joined with section headers. Lets a model ingest the whole site in one fetch. ~2-3MB depending on site growth — fine.

**LOC.** ~120 across `llms_txt.py` (generator), `llms_full_txt.py` (concatenator + directive expander), and `DocPage` `<head>` `<link rel="alternate">` pointers.

**Owner.** This spike.

**Discoverability.** Add `<link rel="alternate" type="text/markdown" href="/llms.txt" title="LLM index">` to every page's `<head>`.

### 3.B.2 `.md` companion URLs

**Verdict: SHIP — highest-leverage AI-discovery feature.**

**Why.** Every `/path/page/` also serves at `/path/page.md` — raw markdown source (front-matter stripped, includes expanded, no rendering). Adopted by Stripe docs, Vercel docs, Next.js docs, Tailwind docs, Cloudflare docs in 2025. LLM-based retrieval picks up the `.md` URL when present and uses it as canonical source rather than reverse-engineering markdown from HTML.

Our case is even simpler than most: we already author in markdown. We just write it next to the rendered HTML.

**How.** During `docs-build`, for each page rendered to `site/<path>/index.html`, also emit:

- `site/<path>.md` — the post-preprocessor markdown:
  - Front-matter stripped (or kept minimal — `title` and `description` only).
  - `--8<--` snippet includes expanded.
  - `{% example "name" %}` tags expanded into a tabbed code block + a "Live demo: <URL>" line at the end.
  - `{% docstring "x.y" %}` tags expanded inline so the model sees the docstring content, not a directive.
  - All other custom Django tags resolved to text or static markdown.
  - Internal `[text](relative.md)` links rewritten to absolute URLs of the `/path/page.md` form (so an agent following links stays in markdown space).
  - Block-level HTML emitted by the §4.7 Django preprocessor passed through unchanged.

A header is prepended:

```markdown
---
title: Components in Templates
url: https://django-components.github.io/django-components/latest/concepts/fundamentals/components_in_templates/
last_modified: 2026-05-12
---

# Components in Templates

(rest of markdown)
```

`DocPage` adds `<link rel="alternate" type="text/markdown" href="<page>.md">` to the rendered HTML so the `.md` version is discoverable from the HTML.

**LOC.** ~50 if we tap into the §4.7 pipeline cleanly. The .md output is essentially the pipeline stopping after the Django-template pass and before the markdown-to-HTML pass.

**Owner.** This spike + §4.7 pipeline.

**Edge case: pages with live demos.** The `{% example %}` widget can't be rendered into pure markdown. Resolution: expand to a tabbed code block (component code + page code) plus a one-line "Live demo at <full URL>" pointer. The agent gets the static code without losing access to the live thing.

### 3.B.3 Structured headings in markdown source

**Verdict: SHIP as guardrail.**

**Why.** The `.md` companion URLs in §3.B.2 only pay off if our markdown source is well-structured. Sequential heading levels (no `## → #### jumps`), one `<h1>` per page, every section labelled.

**How.** §11.10 guardrail extension that checks the rendered HTML's heading sequence and the markdown source's heading levels are well-formed. Already partially scoped — this spike just confirms it's wanted.

**LOC.** ~30 in §11.10.

**Owner.** §11.10 (extension).

### 3.B.4 Code-block language tags

**Verdict: SHIP — enforce; existing §11.10 lexer guard partially does this.**

**Why.** LLMs use the fence language to interpret code (otherwise they guess from content). §11.10 §3.2.3 already flags unlabelled fences via the Pygments lexer guard. Extend the existing guard to *error* (not warn) on missing language tags.

**How.** Tighten the §11.10 lexer guard's behaviour: missing language = build failure. Add `ALLOWED_NON_LEXER_INFOSTRINGS` (per §11.10) to whitelist `mermaid`, `graphviz`, etc.

**LOC.** ~5 (change warn→error in the existing guard).

**Owner.** §11.10 (existing).

### 3.B.5 Stable code-example IDs across versions

**Verdict: SHIP as guardrail.**

**Why.** When an example is referenced ("see the form_submission example"), the URL anchor should stay stable across versions. Otherwise LLMs that cached a URL in an older index hand users 404s on new releases.

**How.**

- Example directory names (`docs/examples/<name>/`) are the source of truth. Renaming an example = breaking change; treat as such.
- A guardrail flags renames of `docs/examples/<name>` directories in PRs (compares against `master`). Forces a review where reviewer either approves the rename (and lands a redirect) or keeps the old name.

**LOC.** ~20 guardrail.

**Owner.** §11.10 (extension).

### 3.B.6 Semantic HTML

**Verdict: SHIP — already in §11.11.**

**Why.** §11.11 §3 specifies the `DocPage` chrome uses `<article>`, `<aside>`, `<nav>` and other semantic elements. LLMs and screen readers both benefit. Nothing additional here.

**LOC.** 0 (covered).

**Owner.** §11.11.

### 3.B.7 Meta description quality (LLM consumption)

**Verdict: SHIP — same as §2.A.6.**

**Why.** Same feature; AIO is a second consumer of the same metadata. The extractor in §2.A.6 handles both.

**LOC.** 0 (covered).

**Owner.** §2.A.6.

### 3.B.8 No JS-required content

**Verdict: SHIP — already a property of the architecture.**

**Why.** Option B (pre-render at build time) means the rendered HTML is the content. The fragment examples in §4.4 use pre-rendered static files; the live demos use post-load JS to *enhance* the static markup but don't *require* it for content visibility. Already done.

**Audit step:** during Phase 2 (`{% example %}` migration), verify that with JS disabled in the browser, the static code tabs are visible (even if the live-demo tab loses interactivity). If JS-off rendering loses content, fix.

**LOC.** 0 (architecture) + audit.

**Owner.** Phase 2.

### 3.B.9 `tags.json` — template-tag DSL manifest

**Verdict: DEFER to post-cutover.**

**Why.** We're a library; for our library's own templating DSL (`{% component %}`, `{% slot %}`, `{% fill %}`, `{% provide %}`, etc.), we could publish a JSON manifest at site root listing every tag with its signature, args, kwargs, and slot-fill expectations. AI agents authoring django-components templates would consume this directly.

This is genuinely valuable but it's not on the critical migration path:

- The data source overlaps heavily with §11.5 (per-API-kind discovery). We should ship `tags.json` from the same discovery pass that drives the per-API-kind reference rendering, not as a parallel pipeline.
- §11.5's data structure (`{kind, dotted_path, members, options}`) doesn't yet model template-tag DSL specifics (slot fills, named slots, conditional kwargs).
- Cutover does not regress on this — `tags.json` doesn't exist today either.

**How (when we get to it).** Add a `template_tag` kind to §11.5's discovery. Emit `tags.json` as a build artifact at site root. Document the schema. Land in a follow-up after Phase 6.

**LOC.** ~100 deferred.

**Owner.** Follow-up after cutover; coordinate with §11.5.

### 3.B.10 robots.txt for AI bots

**Verdict: SHIP — default-allow (confirmed by Juro 2026-06-01).**

**Why.** A docs site benefits from being well-known and well-cited. AI consumers are a growing channel for organic discovery and inbound traffic. Blocking them defaults to no inclusion in the indexes that LLMs build from.

**How.** Explicit `User-agent:` blocks in `robots.txt` (§2.A.3). Document the policy in `community/ai_bot_policy.md`:

```markdown
# AI / LLM bot policy

We allow the major AI training and search crawlers to index this documentation:

- GPTBot (OpenAI)
- ClaudeBot (Anthropic)
- anthropic-ai (Anthropic — legacy)
- Google-Extended (Google AI training)
- PerplexityBot (Perplexity search)
- CCBot (Common Crawl — feeds many models)

Reason: this is a community-maintained library, and the more discoverable our docs are
to AI-based search and AI-based authoring tools, the easier it is for users to find us
and write components correctly the first time.

If you maintain a downstream tool that relies on django-components and want to verify
your bot is allowed, see /robots.txt. We update the allow-list on a rolling basis as
new well-behaved crawlers appear.

To request that a specific bot be added or removed, file an issue.
```

**LOC.** ~30 (policy doc) + already covered by §2.A.3 robots.txt.

**Owner.** This spike (decision made) + Phase 3 (policy doc).

### 3.B.11 Markdown front-matter consistency

**Verdict: SHIP — front-matter schema codified.**

**Why.** Once `.md` companion URLs ship (§3.B.2), front-matter quality affects how LLMs index our content. Today only one file uses front-matter — adoption is opt-in but consistent.

**How.** Front-matter schema:

```yaml
---
title: Components in Templates       # str, optional (defaults to first # Heading)
description: ...                     # str, optional (defaults to first-paragraph extract)
og_image: /assets/.../custom.png     # str, optional (defaults to auto-generated OG card)
noindex: false                       # bool, optional (defaults: true for v0.x where x < latest)
canonical: null                      # str, optional (defaults: rule from §2.A.1)
tags: [migration, advanced]          # list[str], optional (taxonomy; informs llms.txt grouping)
first_published: 2026-05-12          # date, optional (defaults: git-log oldest commit)
---
```

A guardrail (§11.10) validates the schema: unknown keys = build error; type mismatches = build error.

**LOC.** ~40 (schema + validator).

**Owner.** This spike + §11.10.

### 3.B.12 AI-friendly URL conventions

**Verdict: SHIP — already mostly true.**

**Why.** Lowercase, hyphen-separated, no extensions. Current docs already follow this with one exception: the `?` and `&` in fragment-example URLs (`/examples/fragments/?type=alpine`). §4.4 already specifies these become path-based static URLs at build time (`/static/fragments/.../alpine.html`), so the issue evaporates.

**How.** Confirm during the §7.1 slug-algo audit that slugification preserves these properties.

**LOC.** 0 (covered).

**Owner.** §7.1.

---

## 4. Group C — Shared infrastructure

### 4.C.1 Unified `<head>` block in `DocPage`

**Verdict: SHIP — central to everything else in this spike.**

**Why.** Single source of truth for canonical, OG, JSON-LD, title, description, theme-color, favicon, viewport, robots, alternate, lang. No per-page handcrafting — pages override via front-matter.

**How.** A single Django template block in `DocPage` (§4.1, §11.11 §3). Takes a `head_meta` dict assembled by the build:

```python
{
    "title": "...",
    "description": "...",
    "canonical": "...",
    "og": {"image": "...", "type": "article", ...},
    "twitter": {"image": "...", "card": "summary_large_image"},
    "jsonld": [{"@type": "BreadcrumbList", ...}, {"@type": "TechArticle", ...}],
    "alternate": [{"rel": "alternate", "type": "text/markdown", "href": "...md"}, ...],
    "robots": "index,follow",  # or "noindex,follow" for old versions
    "theme_color": "#0d9488",
    "lang": "en",
}
```

The dict is assembled by `apps/docs/head.py` from front-matter + defaults + version-manifest lookups.

**LOC.** ~100 across the template + builder.

**Owner.** This spike + §4.1 + §11.11.

### 4.C.2 Per-page front-matter override

**Verdict: SHIP — codified in §3.B.11.**

**Why.** Default behaviour handles 99%; the 1% that needs custom metadata gets it from front-matter. Already scoped above.

**LOC.** 0 (covered in §3.B.11).

### 4.C.3 Per-version `<head>` differences

**Verdict: SHIP — `noindex` on old versions.**

**Why.** Old version URLs accumulate inbound links over time. If they all stay indexed, search engines spread rank across many copies of the same content. Marking them `noindex` (while keeping `follow` so the internal nav still gets discovered) concentrates rank on `/latest/` while keeping old versions reachable for users who land there directly.

**How.** Build-time rule: any page under `/v<version>/` where `<version>` is not the most recent N (recommended N=2 — current + one prior) emits `<meta name="robots" content="noindex,follow">`. The version manifest (§4.6) drives the decision.

**LOC.** ~10 in §4.C.1's head builder.

**Owner.** This spike + §4.6.

### 4.C.4 Lighthouse CI

**Verdict: SHIP — covered in §2.A.14.**

**LOC.** 0 (covered).

### 4.C.5 Search-engine indexing manifest

**Verdict: SHIP — small build artifact.**

**Why.** A file at `meta/indexing.json` enumerates "URLs we intend to be indexed" and their canonical equivalents. Used by §11.10 guardrails to confirm we didn't accidentally `noindex` a major page. Also useful as a diff artifact when a release adds or removes pages.

**How.** Generated at build time. Schema:

```json
{
  "generated_at": "2026-06-01",
  "version": "0.150",
  "pages": [
    {"url": ".../latest/", "canonical": ".../latest/", "robots": "index,follow"},
    {"url": ".../latest/getting_started/installation/", "canonical": "...", "robots": "index,follow"},
    {"url": ".../v0.149/getting_started/installation/", "canonical": ".../latest/.../installation/", "robots": "noindex,follow"},
    ...
  ]
}
```

The §11.10 single-h1 guardrail extension also validates: every entry with `robots: index,follow` corresponds to a built HTML page that exists and has well-formed metadata.

**LOC.** ~50 generator + ~30 guardrail consumer.

**Owner.** This spike + §11.10.

---

## 5. Implementation surface (code map)

Where each piece lands in the new repo structure (from §4.1 of the main doc):

| Component | File(s) | LOC | Phase |
|---|---|---|---|
| `DocPage` `<head>` block | `apps/docs/components/doc_page/template.html` | ~60 | Phase 1 |
| Head-meta builder | `apps/docs/head.py` | ~100 | Phase 1 |
| Description extractor | `apps/docs/seo/description.py` | ~50 | Phase 1 |
| Canonical-URL rule | `apps/docs/seo/canonical.py` | ~30 | Phase 1 |
| JSON-LD builder | `apps/docs/seo/jsonld.py` | ~80 | Phase 1 |
| Sitemap generator | `apps/docs/seo/sitemap.py` | ~80 | Phase 5 |
| robots.txt template | `apps/docs/static/robots.txt.tmpl` + `apps/docs/seo/robots.py` | ~40 | Phase 5 |
| `OgCard` Django component | `apps/docs/components/og_card/` | (§11.9) | Phase 5 |
| `llms.txt` generator | `apps/docs/aio/llms_txt.py` | ~80 | Phase 5 |
| `llms-full.txt` generator | `apps/docs/aio/llms_full_txt.py` | ~40 | Phase 5 |
| `.md` companion writer | `apps/docs/aio/md_companion.py` | ~50 | Phase 1 (cheap; needed for testing) |
| Lighthouse CI workflow | `.github/workflows/docs-lighthouse.yml` + `lighthouserc.json` | ~90 | Phase 5 |
| AI-bot policy doc | `content/community/ai_bot_policy.md` | ~30 lines | Phase 3 |
| Front-matter schema validator | `apps/docs/frontmatter.py` | ~40 | Phase 1 (cheap, needed for testing) |
| Indexing manifest generator | `apps/docs/seo/indexing_manifest.py` | ~50 | Phase 5 |
| Single-h1 guardrail | extends §11.10 §3 | ~15 | Phase 5 |
| Alt-text guardrail | extends §11.10 §3 | ~15 | Phase 5 |
| JSON-LD validity guardrail | extends §11.10 §3 | ~30 | Phase 5 |
| Anchor-deprecation guardrail | extends §11.10 §3 | ~20 | post-cutover |
| Example-rename guardrail | extends §11.10 §3 | ~20 | Phase 5 |

**Subtotals:**

- Phase 1 (foundational, ships with first content): ~330 LOC
- Phase 5 (SEO/AIO polish before cutover): ~430 LOC
- Post-cutover (`tags.json` + deprecation timer): ~120 LOC

**Total new SEO/AIO surface: ~880 LOC**, of which ~330 must land in Phase 1 (the head block, canonical, description, JSON-LD, front-matter, `.md` companion).

---

## 6. Decisions log

| Decision | Resolution | Date | Owner |
|---|---|---|---|
| AI-bot allow/deny policy | **Default-allow.** GPTBot, ClaudeBot, anthropic-ai, Google-Extended, PerplexityBot, CCBot, and other major AI training and search crawlers allowed in `robots.txt`. Matches the project's permissive-OSS posture and maximises discovery in a growing channel. Codified in `community/ai_bot_policy.md`. | 2026-06-01 | Juro |
| Canonical URL strategy for versioned pages | Versioned pages canonical to `/latest/` counterpart; `noindex,follow` if the page no longer exists in `/latest/`. (Change from Material default of canonical-to-self.) | 2026-06-01 | Spike |
| Anchor-alias deprecation window | 12 months from new anchor scheme shipping (interacts with §7.2). | 2026-06-01 | Spike |
| Old-versions `noindex` threshold | All `/v0.x/` except current and one prior emit `<meta name="robots" content="noindex,follow">`. | 2026-06-01 | Spike |
| `tags.json` template-DSL manifest | Defer to post-cutover; coordinate with §11.5 discovery. | 2026-06-01 | Spike |

---

## 7. Phase placement

Mapping each piece to the migration phases (from §5 of the main doc):

**Phase 1 — scaffold + one section.** The `DocPage` `<head>` block, head-meta builder, description extractor, canonical-URL rule, JSON-LD builder, `.md` companion writer, front-matter schema. **All of these need to land in Phase 1** so subsequent phases test against a real SEO floor, not a placeholder.

**Phase 2 — `{% example %}` tag.** No new SEO surface; verify `.md` companion writer handles the `{% example %}` expansion correctly.

**Phase 3 — rest of markdown pages.** Content-side work: alt-text audit, internal-link density audit, ai_bot_policy.md written.

**Phase 4 — API reference.** Reference pages get JSON-LD `TechArticle` like content pages. Per-kind components (§11.5) inherit the `DocPage` head block.

**Phase 5 — search, versioning, social.** Sitemap, robots.txt, OG/Twitter cards in head, `llms.txt`, `llms-full.txt`, Lighthouse CI workflow, indexing manifest, custom 404 page, single-h1 guardrail, alt-text guardrail, JSON-LD validity guardrail, example-rename guardrail.

**Phase 6 — cutover.** Verify HTTPS + apex redirect. Run final Lighthouse audit. Run anchor-alias check on a sample inbound-link set.

**Post-cutover.** `tags.json`, anchor-deprecation timer, deprecation guardrail.

---

## 8. Risks and open questions

### 8.1 Risks

- **Per-page description quality on long-tail pages.** The extractor in §2.A.6 has to handle weird content shapes gracefully (pages that open with a definition list, a code block, a table). Edge cases will surface during the Phase 3 audit; if more than a few dozen pages need hand-authored descriptions, the LOC budget grows. Mitigation: extractor falls back to the site-level description (never worse than today).

- **JSON-LD rejection by Google's parser.** Malformed JSON-LD can break rich-result eligibility on the entire site. Mitigation: §11.10 guardrail asserts the JSON parses and validates against the `BreadcrumbList`/`TechArticle` JSON schema before build succeeds.

- **`.md` companion URLs doubling site size.** ~2x file count, ~1.5x total bytes (markdown is smaller than rendered HTML). Acceptable; static-site hosting is free. Worth monitoring after Phase 5 lands.

- **`llms-full.txt` becoming stale or too large.** It's a concatenation; if the docs grow 10x, it becomes a 30MB file. Mitigation: skip the largest reference pages (mkdocstrings dumps), include only concept/guide/example content. Re-evaluate every release.

- **AI-bot allow-list maintenance.** New AI crawlers appear quarterly. Without maintenance, the explicit allow-list in robots.txt grows stale. Mitigation: a quarterly issue on a calendar to review the list.

### 8.2 Open questions (resolvable during implementation)

- **Should `og:image` fall back to a site-level default** if a per-page card hasn't been generated yet (Phase 1 ships before Phase 5 OG card generation)? Recommendation: yes, ship a single hand-designed `og-default.png` in static for Phase 1, swap to per-page in Phase 5.
- **Should the indexing manifest be committed to git** or be a CI artifact only? Recommendation: CI artifact, surfaced as a PR comment diff. Avoids merge conflicts.
- **`google-site-verification` token migration.** Current site has a verification token in the head. Carry it over to the new build verbatim during cutover.

### 8.3 Items explicitly deferred

- **Comprehensive accessibility audit.** Out of scope; revisit when the visual system stabilizes (§11.11 follow-up).
- **Real-time SEO monitoring (Search Console alerts).** Operational concern; not part of the build pipeline.
- **Internationalization / `hreflang`.** We don't have translated docs.
- **Mobile-app deep links / iOS App Search.** Not applicable for a library docs site.

---

## 9. Cross-references

- **§4.1 (DocPage chrome)** — owns the `<head>` block this spike specifies.
- **§4.6 (versioning)** — supplies the version manifest that drives canonical-URL rule and per-version `noindex`.
- **§4.7 (markdown pipeline)** — owns front-matter parsing and the `.md` companion-emission hook.
- **§7.1 (URL stability / slug algo)** — depends on this spike's anchor-deprecation timeline.
- **§7.2 (anchor migration)** — already decided; this spike adds the timer and guardrail.
- **§11.1 (search)** — Pagefind search bar embedded in the custom 404 page.
- **§11.5 (per-API-kind discovery)** — `tags.json` (deferred) reuses this data source.
- **§11.6 (content directives)** — `.md` companion writer consumes the directive-expansion pipeline.
- **§11.9 (plugin replacements)** — sitemap and robots.txt replacement already-decided plugins; this spike scopes their behaviour.
- **§11.10 (guardrails)** — owns the single-h1, alt-text, JSON-LD validity, example-rename, anchor-deprecation guardrails this spike adds.
- **§11.11 (UI/layout)** — `DocPage` chrome lives here; this spike threads metadata through it.

---

## 10. References

- [llms.txt proposal — llmstxt.org](https://llmstxt.org/) — short and full index conventions.
- [Schema.org TechArticle](https://schema.org/TechArticle), [BreadcrumbList](https://schema.org/BreadcrumbList).
- [Google Search Central — JSON-LD guidelines](https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data).
- [Stripe Docs `.md` companion URL pattern](https://docs.stripe.com/) — append `.md` to any page URL.
- [Vercel Docs `.md` companion](https://vercel.com/docs) — same pattern.
- [Anthropic Docs llms.txt](https://docs.anthropic.com/llms.txt) — example llms.txt in the wild.
- [Cloudflare Docs llms.txt](https://developers.cloudflare.com/llms.txt) — another example.
- [Google Search Central — Robots meta and X-Robots-Tag](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag).
- [Lighthouse CI](https://github.com/GoogleChrome/lighthouse-ci) — CI integration.
- [Pagefind](https://pagefind.app/) — search index used in the custom 404.
- [Common Crawl robots.txt allow-list](https://commoncrawl.org/faq) — bot identification.
- [OpenAI GPTBot user agent](https://platform.openai.com/docs/gptbot) — opt-out / opt-in instructions.
- [Anthropic ClaudeBot user agent](https://www.anthropic.com/news/bot-disclosure) — opt-out instructions.
