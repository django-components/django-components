# Spike 11.11 — UI / layout inspiration

**Status:** spike complete
**Date:** 2026-06-01
**Feeds back into:** [DESIGN_djc_docs_site.md §4.1, §5, §11.1.G.1, §11.5 (per-kind visual design), §11.6.C, Phase 5 component design](DESIGN_djc_docs_site.md)
**Spike question:** What does the actual layout/visual design look like? Pull a deliberate visual direction from the three references the user named (safe-ai-factory/web, Vuese, Pagefind), decide flat-vs-nested sidebar, lock in 5-8 design tokens, sketch a static HTML mock of a single page.

This spike is the **terminal authority for visual direction**. Where another spike (§11.1, §11.5, §11.6, §11.9) deferred a visual decision to "the §11.11 UI spike", it gets decided here. Where this spike commits to a token value, downstream component work in Phase 5 takes that value as given.

---

## 0. TL;DR verdict

**GO.** A coherent visual direction lands cleanly using one outer reference (`~/repos/agents/safe-ai-factory/web`'s OKLCH + Tailwind + sectioned-sidebar shape) plus one nav-hierarchy reference (VitePress: nested sidebar with uppercase group headers and a right-rail "On this page" TOC). No reference is copied wholesale; we mix the two.

**Five load-bearing decisions** drop out:

1. **Sidebar is nested, two levels deep.** Top-level sections (Concepts, Reference, etc.) become collapsible groups containing pages or sub-sections (`concepts/fundamentals/`, `concepts/advanced/`). A third level is allowed but rendered as additional indent inside the same group, not a new collapsible. The current Material "top tabs + sidebar" two-dimensional nav is dropped; everything fits in the sidebar. Validated against our content depth (§1.3).

2. **Top nav names *kinds of artifact*, not docs sections.** The earlier draft listed `Concepts / Reference / Examples` in the top nav alongside the same sections in the sidebar — duplicate scaffolding. Replaced (per Juro's feedback) with: `logo (→ landing) · Docs · Examples · Plugins · Blog (future) · ⌘K · version · theme · GitHub`. Sidebar handles within-kind nav; top nav handles between-kind. Implies a URL change: docs content moves under `/docs/` (full impact in §4.2). A new landing page lives at `/` (out of spec for this spike but the slot is reserved — see §4.4).

3. **Three-column layout, 1280px outer max.** Left sidebar 280px, content 720px max, right TOC 240px. Total content viewport is 1240px with breathing-room padding to a 1280px outer constraint. Breakpoint behaviour in §2.

4. **Light theme is the default; dark theme is a peer.** Material today defaults to "auto via `prefers-color-scheme`"; we keep that. But the docs ship a full hand-tuned light theme and a full hand-tuned dark theme (the two `theme.palette` entries today get translated to our OKLCH token sets). No automatic dark mode generated from light (Material does that and it looks washed out in places). Toggle lives in the top nav. **This spike does not implement the toggle**, only specifies it; the toggle's wiring is §11.1.G.1.

5. **Code blocks: minimal, language label top-right, copy on hover. NO terminal chrome.** safe-ai-factory's macOS traffic-light treatment is distinctive but reads as "playful" — wrong tone for a library docs site that needs to convey precision. We borrow the typography, padding, and copy-button placement but skip the chrome. A subtle 3px left-border accent in the section-color of the surrounding heading is enough hierarchy without busy decoration.

**Accent colour decision deferred to Juro (one of two presented in §10.3).** Default proposal: **muted teal** (continuity with the current Material teal palette so existing screenshots and inbound links don't feel jarring). Alternative: **Django bottle-green** (`oklch(45% 0.12 155)` — dogfoods the Django brand). Both work; neither is load-bearing for any other decision in this spike.

**Per-kind component visuals (the §11.5 carry-over):** signature line in a bordered callout with a `class` / `function` / `setting` / `cli` badge top-right, parameters as a clean GFM table with name column in mono, source link as a subtle "→ source" link top-right of each symbol entry, anchored heading exposes `#` on hover. Specified in §6.

**Mock pages.** Two static HTML sketches in §11: a typical concept page (`render_api.md` shape) and an API reference page (`reference/components.md` shape). Both render at 1280px in a single column-flexbox layout. Skeletal CSS uses our token system.

**Biggest open risk.** **Visual brand collision with the current site.** The new docs site looks distinctly different from the current Material site. During the staged rollout (per §8 of the main doc), the live site and the preview will diverge visually, which will read as "the project changed its branding". Mitigation: stage the rollout to a `next.django-components.github.io` subdomain (or a `/preview/` path) so reviewers compare deliberately, not by surprise, and the cutover commit is a single moment. Concrete mitigation steps in §13.

**Recommended first concrete step.** During Phase 1 of the migration, build the layout shell (the three-column flexbox + header + sidebar + content stub + right TOC) as **one** Django component (`DocPage`) on top of the design tokens in §10. No content rendering, no per-kind components yet — just the chrome. This is a 1-2 day task that proves the layout direction holds before any markdown is rendered. See §11.4.

---

## 1. References surveyed (concrete observations)

### 1.1 `~/repos/agents/safe-ai-factory/web` (Next.js + Tailwind + MDX)

Read in full from [src/components/](file:///Users/mac/repos/agents/safe-ai-factory/web/src/components/). The pattern is mature and consistent. What I'm taking from it:

| Element | Observation | Adopt? |
|---|---|---|
| Outer layout | `max-w-[1400px] mx-auto flex min-h-[calc(100vh-4rem)]` — three logical zones (header, sidebar, content) | **Yes**, slightly narrower at 1280px to match our content density |
| Sidebar | `w-64` (256px), `border-r border-border`, `sticky top-16`, `overflow-y-auto`. Items are small block links, padded `px-3 py-1.5`, `text-sm` (then `text-xs` on `md:`) | **Yes**, but widened to 280px (we have longer page titles) and items stay at `text-sm` (deeper depth → readability matters more than density) |
| Section labels | `text-xs font-mono uppercase tracking-widest text-fg-subtle mt-6 mb-2 px-3` — very restrained label-of-labels | **Yes — verbatim styling.** This is one of the most distinctive moves and it works |
| Active link | `text-accent bg-accent-dim font-medium` (accent text + 10% tinted accent bg) | **Yes** |
| Top nav | `fixed top-0 h-16 border-b border-border bg-bg/80 backdrop-blur-md`. Logo left, links centre-right, CTA right | **Yes** structure; we replace the CTA with the search trigger |
| Mobile drawer | Sliding left drawer with backdrop overlay, opens on hamburger click | **Yes — same pattern** |
| Code blocks | macOS traffic-light header + dark surface-3 chrome + lang label centred top + copy button top-right | **No.** Too decorative. Borrow padding, lang label idea, copy button position only |
| Typography | `prose prose-sm prose-invert`, headings `font-bold tracking-tight`, body `text-fg-muted`, links `text-link no-underline hover:underline` | **Yes** for the structure; we own the colour tokens |
| Inline code | `.prose :not(pre) > code { color: accent; background: accent-dim; padding: 0.1em 0.35em; border-radius: 0.2em; font-weight: 500 }` | **Yes — verbatim styling.** Inline code as a colored pill reads as a "term" |
| Colours | OKLCH variables, all tokens in `globals.css`, consumed by Tailwind via `bg-bg`, `text-accent`, etc. | **Yes — same architecture.** OKLCH gives us perceptually uniform light/dark adjustment |
| Nav JSON | `{ product, sections: [{ type, label, items: [{ slug, title, path }] }] }`. Flat groups, no nesting beyond section→item | **Adopt the shape**, extend with optional `groups` for our 2-level nesting (see §3.2) |

What I'm **not** taking: the dark-only theme (we ship both), the gold accent (we pick our own), the right-rail TOC (safe-ai-factory has no TOC; we need one), and the playful code-block chrome.

### 1.2 VitePress (https://vitepress.dev)

Live web fetch summarized in this section. The reference for *nested sidebar* and *right-rail TOC*, which safe-ai-factory doesn't have.

| Element | Observation | Adopt? |
|---|---|---|
| Sidebar nesting | Section headers in uppercase, regular-weight links below, always-expanded (no per-section collapse). Active item highlighted | **Yes** — uppercase section headers (matches safe-ai-factory exactly), but we add per-section collapse for the long groups (`concepts/advanced/` has 13 items; expanding them by default eats the entire viewport) |
| Top header | Logo + product name far left, primary links (`Guide`, `Reference`), then version picker, search trigger with ⌘K hint, theme toggle, GitHub icon | **Yes — adopt almost verbatim.** Drop the language switcher (no i18n; §7 of main doc is explicit) |
| Search trigger | A button that displays "Search… ⌘K" inline in the header. Click or ⌘K opens the modal | **Yes** |
| Right-rail TOC | "On this page" heading, list of H2/H3 from the current page, scroll-spy with active heading | **Yes** |
| Code blocks | Language label top-right (small, monospace, muted), copy button on hover top-right, no chrome border, optional file-name tab on top | **Yes** for the language label + copy treatment. Skip the file-name tab for v1 (we don't author with file-named code blocks today) |
| Dark mode toggle | "Appearance" toggle in header, three modes (auto / light / dark) | **Yes** — same 3-mode toggle (matches what Material does today, preserves user expectation) |
| Typography | Sans body, mono code, generous line height, comfortable max-width on prose | **Yes** philosophically; specific tokens in §10 |

What I'm **not** taking: the version selector as a separate dropdown next to the logo (we use the sidebar footer for version picking — less clutter at the top). The exact accent (VitePress uses a soft blue that reads "Vue-ish"; we pick our own).

### 1.3 Pagefind docs (https://pagefind.app)

WebFetch was light on visual specifics (the homepage is mostly marketing copy). Pulling from the **Pagefind UI component** (which is what we'd actually integrate per §11.1), not the website:

- **Search overlay shape.** ⌘K opens a modal centred on screen, ~600px wide, with the search input at the top and result list below. Each result shows page title + breadcrumb + matched snippet with the query highlighted. Keyboard-navigable (↑/↓ to move, Enter to open, Esc to close).
- **Default styling is "neutral and dark".** Configurable via CSS variables. We override to match our token system.
- **One thing to honor:** the result snippet uses a small inline `<mark>` to show the match. We keep that.

The Pagefind site itself uses a clean centred-content layout, no docs sidebar (it's a small site). Not a useful nav reference; only a search-UX reference.

### 1.4 Bonus reference — Pydantic docs (https://docs.pydantic.dev/latest)

[docs/.nav.yml](docs/.nav.yml) line 1 calls Pydantic out as the in-repo "nav content inspo" reference. I checked it for hierarchy:

- Top header is a single horizontal bar.
- Sidebar is nested with collapsible sections (`Concepts`, `API Documentation`, `Internals`, etc.).
- Per-page right TOC.
- Material under the hood (same theme we use today) but with significant override CSS.

Not a separate visual direction — same Material theme — but a useful sanity check that "nested sidebar + right TOC" is the well-trodden pattern for Python library docs. Confirms §3's decision.

---

## 2. Layout system

### 2.1 The geometry

```
+----------------------------------------------------------------------------+ <- 1280px outer max
| Top header (sticky, 64px high, backdrop-blur, border-b)                   |
+-------------+--------------------------------------+----------------------+
|             |                                      |                      |
|  Sidebar    |  Content article                     |  Right TOC          |
|  280px      |  max 720px (60-70 ch)               |  240px              |
|  sticky     |  centred in column                   |  sticky             |
|             |                                      |  scroll-spy          |
|             |                                      |                      |
+-------------+--------------------------------------+----------------------+
|             |  Footer (in-flow, not sticky)        |                      |
+-------------+--------------------------------------+----------------------+
```

Numbers:

| Dimension | Value | Reason |
|---|---|---|
| Outer max | 1280px | Comfortable on 1440 / 1920 / 2560 displays. Slightly tighter than safe-ai-factory's 1400 because our content is denser (more code blocks per page) and we want shorter lines |
| Header height | 64px (`h-16`) | Matches safe-ai-factory; gives room for the search trigger to feel clickable |
| Sidebar width | 280px | Wider than safe-ai-factory's 256 because our group labels are longer ("Documentation: API Reference" etc., though we drop the "Documentation:" prefix in §3) |
| Content max | 720px | ~70ch at 16px body. CommonMark and prose research both land at 65-75ch as the readable max |
| Right TOC | 240px | Enough for headings up to ~30 chars wrapped on two lines |
| Inner gutter | 32px between sidebar and content; 48px between content and right TOC | Asymmetric — sidebar is structural, right TOC is auxiliary, so it gets more whitespace |
| Page side padding | 24px on mobile, 32px on tablet, 48px on desktop | Standard Tailwind progression |

### 2.2 Breakpoints

| Viewport | Behaviour |
|---|---|
| `< 768px` | Sidebar hidden, hamburger in header opens drawer. Right TOC hidden; render as a `<details>` popover under the H1 ("On this page →") |
| `768px – 1024px` | Sidebar visible (collapsible). Right TOC hidden; `<details>` popover |
| `1024px – 1280px` | Sidebar visible. Right TOC visible. Content flexes to fill available space, max still 720px |
| `>= 1280px` | Fully laid out at the geometry in §2.1, centred |

The "no right TOC under 1024" rule is a deliberate trade-off: the TOC is a power-user feature, mobile readers scroll. Avoids a cramped 4-column layout on iPads.

### 2.3 Outer body / page chrome

- `body { background: var(--c-bg); color: var(--c-fg); }`
- Top header is `position: fixed` so it stays visible when the content scrolls. Backdrop-blur on the bg gives the "translucent over scrolled content" feel that VitePress and safe-ai-factory both use.
- Sidebar and right TOC are `position: sticky; top: 64px; height: calc(100vh - 64px); overflow-y: auto`. They don't scroll the page; they scroll independently.
- Footer is in-flow at the bottom of the content column, not sticky. (Material's `navigation.footer` next/prev-page navigation lives at the bottom of the content area, not in the right TOC.)

---

## 3. Sidebar

### 3.1 Nested vs flat — the decision

**Nested, two levels of structural nesting.** Validated against our actual content depth ([docs/](docs/) inventory in §1.3 of the main doc and re-verified here):

```
docs/
├── overview/                    <- top-level group (no sub-sections)
├── getting_started/             <- 8 flat pages
├── concepts/
│   ├── fundamentals/            <- 7 pages
│   └── advanced/                <- 13 pages
├── reference/                   <- 14 flat pages
├── guides/
│   ├── setup/                   <- 2 pages
│   └── other/                   <- 1 page
├── examples/                    <- 10 example dirs + index
├── plugins/                     <- 1 page (catalog)
├── community/
│   └── devguides/               <- 3 deep-dives
└── releases/                    <- 1 generated page
```

Three depth-classes appear:
- **1 level** (e.g. `getting_started/`, `reference/`) — top group → page
- **2 levels** (e.g. `concepts/fundamentals/`, `community/devguides/`) — top group → sub-group → page
- We do not have 3-level structural nesting today; nothing breaks that rule.

The sidebar renders both 1-level and 2-level cases as **the same visual hierarchy with one extra indent**:

```
CONCEPTS
  Fundamentals
    Render API
    Component defaults
    Single-file components
    ...
  Advanced
    Hooks
    Provide / inject
    Extensions
    ...

REFERENCE
  Components
  Settings
  Commands
  ...
```

Top-level groups in `tracking-widest uppercase` (the safe-ai-factory move). Sub-groups in regular weight, slightly larger text than items, padded left to indicate nesting. Items get 16px additional left padding inside a sub-group.

### 3.2 Sidebar nav data shape

Adopted from safe-ai-factory with one extension. We add an optional `groups` field next to `items`:

```yaml
# docs/.nav.yml (new schema, replaces the awesome-nav .nav.yml)
sections:
  - label: Overview
    path: /overview/
    items:
      - { title: What is django-components?, path: /overview/welcome/ }
      - { title: Comparison, path: /overview/comparison/ }
      ...

  - label: Concepts
    groups:
      - label: Fundamentals
        items:
          - { title: Render API, path: /concepts/fundamentals/render_api/ }
          - { title: Component defaults, path: /concepts/fundamentals/component_defaults/ }
          ...
      - label: Advanced
        items:
          - { title: Hooks, path: /concepts/advanced/hooks/ }
          ...
```

A section has **either** `items` (1 level) **or** `groups` (2 levels), never both. Asserted at build time by the guardrails in §11.10.

This schema is parsed once at build time and frozen as JSON in the sidebar component's input. The §11.9 spike already owns the nav loader implementation (~80 LOC, see [DESIGN_djc_docs_site_spike_11_9.md §2.2](DESIGN_djc_docs_site_spike_11_9.md)).

### 3.3 Collapse / expand affordances

| Pattern | Decision | Reason |
|---|---|---|
| Top-level sections (Concepts, Reference, …) | **Always expanded.** No collapse | They're the orientation labels; collapsing them defeats the point |
| Sub-groups within a section (Fundamentals, Advanced) | **Collapsible.** Closed by default unless the current page is inside | Avoids the 20-page wall-of-text in `concepts/` when reader is in `getting_started/` |
| Within a section but no sub-groups | **Always expanded** (it's just a flat list) | Same as 1-level case |

Collapse-state persists in `localStorage` keyed by section label. Restoring on next visit makes the sidebar feel personal without being magical.

Collapse caret: small `▾` / `▸` glyph, 12px, muted color, on the right of the sub-group label. Click target is the whole label row.

### 3.4 Active state, current-page, current-section

- **Active page:** accent text + accent-dim background. Matches safe-ai-factory exactly: `text-accent bg-accent-dim font-medium`.
- **Containing section / sub-group:** label stays in its default muted color but bolded slightly (`font-semibold` instead of `font-medium`).
- **Scroll-into-view on page load** if the active item is below the fold. JS one-liner: `activeItem.scrollIntoView({ block: "nearest" })`.

### 3.5 Section-index pages

`overview/index.md`, `examples/index.md`, `plugins/index.md` exist today as landing pages for their section. Material's `navigation.indexes` makes the section label clickable. We adopt the same: section labels render as `<a>` if a matching `index.md` exists, otherwise as `<span>`.

Pre-existing in our content: 3 sections have index pages. Confirmed by file inventory above.

---

## 4. Top header

### 4.0 Per Juro's feedback: top nav should distinguish *kinds of pages*, not duplicate sidebar sections

Earlier draft listed `Concepts / Reference / Examples` in the top nav alongside the same sections in the sidebar. That's duplicate scaffolding. Replaced with a taxonomy where the top nav names the **kinds of artifact** the site hosts; the sidebar handles within-kind navigation.

### 4.1 The new structure

```
+--------------------------------------------------------------------------------------+
| [logo] django-components   Docs  Examples  Plugins  Blog       [Search ⌘K] v0.150 ☼ [GH] |
+--------------------------------------------------------------------------------------+
```

| Slot | Content | Notes |
|---|---|---|
| Logo + wordmark | SVG icon + "django-components" wordmark in `font-bold tracking-tight` | Wordmark links to **`/`** (landing page, not docs home — see §4.4) |
| `Docs` | Primary nav link to `/docs/` (the docs hub) | Houses everything that's currently under `concepts/`, `reference/`, `guides/`, `getting_started/`, `overview/`, `upgrading/`, `community/`, `releases/`. See §4.3 for the URL impact |
| `Examples` | Primary nav link to `/examples/` | A gallery of runnable demos. Kept top-level because it's a different *kind* of artifact (runnable code) and a different navigation flow (card gallery, not sidebar tree) |
| `Plugins` | Primary nav link to `/plugins/` | The community plugin catalog. Different *kind* of page from docs — it's a third-party-extension discovery surface |
| `Blog` | Primary nav link to `/blog/` | **Future** (not in v1). Stub the route or hide the link until first post; per Juro the slot is reserved |
| Search trigger | Button with text `"Search…"` and a keyboard-hint pill `⌘K` | Opens Pagefind modal. Wired in §8 |
| Version picker | Dropdown showing current version, opens to a list of all built versions (`docs/v/*` per §4.6) | Anchored top-right; populated client-side from `versions.json` |
| Theme toggle | Sun / moon / auto icon button | 3-state cycle. Implementation lives in §11.1.G.1 |
| GitHub link | Icon-only `<a>` to the repo | Right edge |

The principle: a top-nav link should lead to a *meaningfully different navigation context*. `Docs` and `Examples` have different sidebar trees; `Plugins` has no sidebar (it's a catalog page); the landing page has no sidebar at all. That's why each one earns a top-nav slot.

Mobile (<768px):
- Logo + wordmark visible
- Search trigger shrinks to icon-only
- Hamburger replaces the primary nav (opens a single drawer combining the top-nav links plus the contextual sidebar for the current section)
- Version picker, theme toggle, GitHub icon collapse into a single overflow menu (kebab icon)

### 4.2 URL taxonomy (the implication)

This re-grouping means the URL structure changes. The current docs live at the root (`/concepts/`, `/reference/`, etc.); the proposed structure puts them under `/docs/`:

| URL today | URL proposed | Notes |
|---|---|---|
| `/` | `/` | Currently shows the docs landing; proposed: a NEW marketing-style landing page (see §4.4). Existing `/` content moves to `/docs/` |
| `/getting_started/...` | `/docs/getting_started/...` | |
| `/overview/...` | `/docs/overview/...` | |
| `/concepts/...` | `/docs/concepts/...` | |
| `/reference/...` | `/docs/reference/...` | |
| `/guides/...` | `/docs/guides/...` | |
| `/upgrading/...` | `/docs/upgrading/...` | |
| `/community/...` | `/docs/community/...` | |
| `/releases/...` | `/docs/releases/...` | Renamed to `Release notes` in sidebar but URL keeps `/releases/`. **Per Juro: folded into Docs**, not a top-nav slot |
| `/examples/...` | `/examples/...` | Unchanged |
| `/plugins/...` | `/plugins/...` | Unchanged |
| `(new)` | `/blog/...` | Future |

**Cost.** ~8 directories of pages get a `/docs/` URL prefix. Inbound links to specific pages break. Mitigation:
1. The `<meta http-equiv="refresh">` redirect machinery from §11.9.2.5 already plans for moved URLs ([#1355](https://github.com/django-components/django-components/issues/1355) precedent). Every old URL gets a redirect file at its old path.
2. Generate redirects automatically by inverting the move map above.
3. The anchor codemod (§11.6.F) already touches every internal cross-ref; same codemod pass updates `/concepts/foo.md` → `/docs/concepts/foo.md`.
4. This URL change is a **deliberate part of the new structure**, called out in the CHANGELOG and the migration announcement.

**Alternative considered:** keep URLs flat (`/concepts/`, `/reference/`, etc.) and have `Docs` link to `/concepts/` or a `/docs/` hub page that just lists the sections. Simpler migration. **Rejected** because the mental model the user is articulating (top nav = kinds of pages, sidebar = within-kind nav) is structurally cleaner, and the URL change is bounded and one-time.

This decision spans §11.11 (visual nav structure) and the main doc's §4.1 / §11.10 / §11.6.F (URL stability, redirects, codemod). Cross-link added in §14.

### 4.3 Why `Release notes` is not a top-nav slot

The user proposed folding Release notes under Docs. Concur:

- Reading release notes is a "between two versions, what changed?" task — it lives next to the rest of the documentation, not as a peer to the marketing/examples/plugin surfaces.
- It's already generated by [docs/scripts/gen_release_notes.py](docs/scripts/gen_release_notes.py) as a docs-pipeline artifact.
- Top-nav real estate is precious; promoting Release notes to a slot would crowd out future kinds (Blog, eventually).

Sidebar treatment: Release notes is the bottom-most section in the Docs sidebar, after Community.

### 4.4 The landing page (NEW; logo destination — deferred to Phase 9 codesign)

Today `/` redirects to `/getting_started/installation/` (or shows `docs/README.md`). The proposed structure introduces a **dedicated landing page** at `/`:

- Logo links to it
- The site's "front door" for visitors who arrive without context
- Lives outside `DocPage` chrome — uses its own `LandingPage` Django component with a stripped layout (no sidebar, no right TOC, full-width sections)

**Scope decision (revised per Juro):** the landing page is **its own phase at the end of the migration plan** (Phase 9 in main doc §8). Why:

- It's explicitly framed as a codesign exercise between Juro and the agent, not a one-shot spec. Juro has a vision but it'll take iteration to reach
- The landing page doesn't gate any other phase. It can ship independently of the cutover
- Building it last means the design system (tokens, typography, components) is already locked in and battle-tested. The landing page reuses primitives rather than inventing them
- Doing it last avoids letting "what does the front page say?" politics block the actual docs migration

**For Phase 1 through Phase 8:** a thin placeholder lives at `/` so the new top-nav taxonomy works end-to-end:

```
+----------------------------------------------+
|        django-components                     |
|        A modular UI library for Django       |
|                                              |
|        [ Read the docs → ]                   |
|                                              |
|        Docs · Examples · Plugins · GitHub    |
+----------------------------------------------+
```

~50 LOC of HTML, uses the design tokens from §10 but no original layout work. Phase 9 replaces this scaffold with the real landing page.

**This spike does not pre-spec the Phase-9 content.** Things like hero copy, feature framing, code-example choice, visual hierarchy, motion design — all of that is the Phase 9 codesign session's job. What this spike commits to:

- The slot exists (`/` is the landing page, not docs home)
- The landing page lives outside `DocPage` chrome
- The landing page is one Django component (`LandingPage`), composing the same primitives the rest of the site uses (typography tokens, code-block treatment, `CodeTabs` if needed, button styles)
- The landing page reuses the top header (logo + Docs/Examples/Plugins links + GitHub) so navigation between the landing and the docs is consistent

Phase 9 fills in the rest.

### 4.5 Sticky behaviour

- `position: fixed; top: 0; left: 0; right: 0; z-index: 50`
- Backdrop blur on the bg: `bg-bg/80 backdrop-blur-md` so content scrolling beneath is faintly visible
- Border-bottom in `--c-border` for definition without weight

### 4.6 What the header is NOT

- No language switcher (no i18n; §7 of main doc)
- No "Star on GitHub" CTA badge; just the icon
- No social icons cluster; just GitHub
- No announcement banner (§13 risks: we may want this later, but not in v1)

---

## 5. Content article — typography & prose

### 5.1 Body typography

| Property | Value | Reason |
|---|---|---|
| Font stack | `Inter`, then `system-ui`, then `-apple-system`, `Segoe UI`, `Roboto`, sans-serif | Inter has excellent screen rendering at 14-18px; system-ui fallback |
| Body size | `16px` | Standard prose readability |
| Body line height | `1.65` | Material default is ~1.6; we err slightly looser because our pages have dense Python code |
| Body color | `var(--c-fg-muted)` (not `--c-fg`) | Headings carry the visual weight; body sits visually lower. Matches safe-ai-factory |
| Max line length | `~70ch` (720px content / 16px ≈ 45em) | At the upper edge of readable; tightens to 65ch on narrower viewports via natural reflow |

### 5.2 Headings

| Level | Size | Weight | Margin-top | Special |
|---|---|---|---|---|
| H1 | `2.25rem` (36px) | `bold` | 0 (first element) | Sets the page title; only one per page |
| H2 | `1.75rem` (28px) | `bold` | `3rem` | `border-top: 1px solid var(--c-border-subtle); padding-top: 1.5rem` — matches today's [docs/css/style.css](docs/css/style.css). The horizontal rule between top-level concepts is one of the few things our current docs do really well |
| H3 | `1.25rem` (20px) | `semibold` | `2rem` | Same border-top treatment, lighter |
| H4 | `1.05rem` (17px) | `semibold` | `1.5rem` | No border |
| H5 / H6 | `0.95rem` (15px) | `semibold` | `1rem` | Rare; same as body otherwise |

Each heading is anchored. The anchor `#` glyph is hidden by default and fades in on `:hover` of the heading row — VitePress and safe-ai-factory both do this. One CSS rule does it all:

```css
.prose h2 { position: relative; }
.prose h2 .anchor { opacity: 0; transition: opacity .15s; }
.prose h2:hover .anchor { opacity: 1; }
```

### 5.3 Links

- Default: `var(--c-link)`, no underline
- Hover: `var(--c-link-hover)`, underline
- Visited: same as default (no purple visited state — too noisy in a docs context)
- External links get a tiny `↗` glyph after the text (CSS `::after`)
- Internal links to API symbols are styled the same as regular links; the API anchor scheme (§7.2 of main doc — drop `django_components.` prefix) is separate from the visual styling

### 5.4 Inline code

Adopted **verbatim** from safe-ai-factory:

```css
.prose :not(pre) > code {
  color: var(--c-accent);
  background: var(--c-accent-dim);  /* 10% accent tint */
  padding: 0.1em 0.35em;
  border-radius: 0.2em;
  font-weight: 500;
}
```

Inline code reads as "this is a term" — the accent pill makes it impossible to miss. Important for a library docs site where 60% of paragraphs reference a symbol or template tag.

### 5.5 Blockquotes

- `border-left: 3px solid var(--c-link)`, `padding-left: 1rem`, `color: var(--c-fg-muted)`
- Used sparingly in our current content; mostly for "quoted from issue X" or pull-quotes

### 5.6 Tables

| Property | Value |
|---|---|
| Border | 1px subtle border on each cell |
| Header | `bg: --c-surface-2`, `font-weight: 600` |
| Row padding | `padding: 0.5rem 0.75rem` |
| Mono columns | First column auto-detected as mono if it contains only `<code>` entries (one CSS-selectors rule) |
| Overflow | `overflow-x: auto` on the table wrapper so wide tables scroll horizontally on mobile |

Materially the same as Pydantic's tables. Not novel; just done right.

### 5.7 Admonitions

We have three types in use (note, info, warning). Visual treatment:

```
+------------------------------------------+
| ◯ NOTE                                   |
| body text in fg-muted                    |
+------------------------------------------+
```

- Left accent border in the type-color (note: blue, info: teal-ish, warning: amber)
- Pale tinted background in the same hue at ~6% opacity
- Type label in small uppercase mono, no icon for v1 (skip icon font dependency)
- No title bar; the label sits inline above the body

Compact, no box-shadow, no rounded corners. Material's admonitions are decorative; ours are signal.

### 5.8 Lists

Standard CommonMark. No custom bullet glyphs. `padding-left: 1.5rem`. Nested lists indent further, `padding-left: 1.5rem` per level.

---

## 6. Code blocks (the most distinctive content surface)

### 6.1 The decision

**Minimal treatment. Language label top-right, copy button on hover top-right, optional 3px left accent border. No terminal chrome.**

```
+------------------------------------------------------------+
|                                       djc_py     [ copy ]  |
|                                                            |
|   class MyComponent(Component):                            |
|       template = """                                       |
|           <div>...</div>                                   |
|       """                                                  |
|                                                            |
+------------------------------------------------------------+
```

### 6.2 Specification

- `<pre>` element: `background: var(--c-surface-2)`, `padding: 1rem 1.25rem`, `border-radius: 0.5rem`, `border-left: 3px solid var(--c-link-dim)`, `overflow-x: auto`
- Inner `<code>`: `font-family: ui-monospace, 'JetBrains Mono', 'Fira Code', 'Cascadia Code', Menlo, monospace`, `font-size: 0.875em` (relative to body), `line-height: 1.6`
- Language label: positioned `absolute; top: 0.5rem; right: 0.75rem`, `font-size: 0.65rem`, `text-transform: uppercase`, `letter-spacing: 0.08em`, `color: var(--c-fg-subtle)`
- Copy button: positioned `absolute; top: 0.25rem; right: 0.5rem`, hidden by default (`opacity: 0`), fades in on `:hover` of the `<pre>`. Click copies, transient checkmark for 1.5s.

### 6.3 Syntax highlighting

- Pygments at build time (already in our pipeline per §4.7). We own `pygments_djc` for our DSL.
- Two themes generated and shipped: light (e.g. `monokai-light`/`tango`) and dark (e.g. `one-dark`/`zenburn`). One stylesheet for each, included via CSS `@media (prefers-color-scheme)` blocks (plus an explicit override class for the manual toggle).
- §11.9 spike confirmed we already emit Pygments CSS at build time; no new tooling needed.

### 6.4 Tabbed code blocks (one visual spec, three use cases)

Per Juro's feedback: the earlier draft introduced the `{% example %}` widget's tab strip *and* deferred "file-name tab" treatment as a separate v1-skip item. That's two patterns when we need one. **Unified spec below covers all three use cases with the same visual treatment.**

The three things that all render through the same tab-strip-on-top-of-a-code-area visual:

| Use case | Source | Tab labels |
|---|---|---|
| **`{% example %}` widget** | A directory under `examples/<name>/` | `Component`, `Page`, `Demo` (or whatever the example exposes) |
| **`pymdownx.tabbed` multi-variant blocks** | `=== "uv"` / `=== "pip"` / `=== "poetry"` markdown sources | Whatever the markdown author names them. The canonical use case Juro called out is install variants |
| **Single file-name label on a code block** | A code fence with a `title=` info-string: ` ```python title="component.py" ` | One "tab" that's purely a label, no click interaction |

The third row is the case I previously mislabelled "skip for v1". It's not a separate feature — **it's a degenerate single-tab block.** A code fence with `title="component.py"` renders the same way as a one-tab pymdownx block.

#### 6.4a The unified visual

```
+------------------------------------------------------------+
| [ Component | Page | Demo ]                       djc_py   |  <-- multi-tab (clickable)
|------------------------------------------------------------|
| (active tab content)                                       |
+------------------------------------------------------------+

+------------------------------------------------------------+
| [ component.py ]                                  python   |  <-- single-tab (label only)
|------------------------------------------------------------|
| ...code...                                                 |
+------------------------------------------------------------+
```

- Tab strip: row of buttons / labels at top, `gap: 0.5rem`, padded `padding: 0.5rem 0.75rem`
- Active tab: `border-bottom: 2px solid var(--c-accent)`, `font-weight: 500`, `color: var(--c-fg)`
- Inactive tab: `color: var(--c-fg-muted)`, no underline, hover brightens to `var(--c-fg)`
- Single-tab degenerate case: render the same chrome but the tab is not interactive (no hover, no click). Visually equivalent to a "file label chip"
- Active tab content area styled the same as a regular `<pre>` (§6.2)
- Language label and copy button remain top-right, unchanged from §6.2 — they apply to *the active tab's content*
- `{% example %}` "Demo" tab: inlines the rendered component output (no `<pre>` chrome — it stands as itself)

#### 6.4b Implementation reuse

One Django component, `CodeTabs`, handles all three cases:

- Input: a list of `{label, language, content_html, is_interactive}` items
- If `len(items) == 1` and not interactive → render the single-tab variant (label only)
- If `len(items) >= 1` and interactive → render the multi-tab variant (click handlers)
- `ExampleCard` (the `{% example %}` widget) composes `CodeTabs` with `is_interactive=True`
- `pymdownx.tabbed` markdown blocks compose `CodeTabs` via a custom markdown-it-py renderer
- A code fence with `title="…"` info-string compiles to a single-item `CodeTabs` with `is_interactive=False`

This means **one tab styling rule** in the CSS, **one component to test**, and **three authoring surfaces** that all look consistent.

#### 6.4c The pymdownx.tabbed coverage Juro flagged

The canonical use cases from §11.6.D (kept in scope by §11.6):

```markdown
=== "uv"
    ```bash
    uv pip install django-components
    ```

=== "pip"
    ```bash
    pip install django-components
    ```

=== "poetry"
    ```bash
    poetry add django-components
    ```
```

renders as a 3-tab `CodeTabs` with `is_interactive=True`, default tab = first. Tab selection persists in `localStorage` keyed by the tab labels (so a reader who picks `uv` once gets `uv` shown across the site — Material does this; we keep the pattern).

### 6.5 What we explicitly skip in v1

- Line numbers (visual noise, low value)
- Per-line highlighting (`{% highlight %}` patterns) — rare in our content
- Code annotations (Material's `# (1)` markers) — handled by markdown extensions in §11.6 if reintroduced; not visual-direction work

---

## 7. Right-rail TOC + breadcrumbs

### 7.1 Right-rail "On this page"

```
On this page
------------
  Overview
  Getting started
    Step 1
    Step 2
  Common patterns
  Troubleshooting
```

- Heading: `On this page` in `text-xs uppercase tracking-widest text-fg-subtle`
- Items: small block links, `text-sm`, `text-fg-muted` default, `text-accent font-medium` when scroll-spy says it's active
- H2s flush left, H3s indented `1rem`; H4+ not shown
- Scroll-spy: IntersectionObserver on the `<h2>` and `<h3>` elements in the article. The first heading currently within the top 30% of the viewport is "active"
- Sticky positioning: same as sidebar (`top: 64px`)
- Hidden under 1024px breakpoint (folded into `<details>` under the H1)

### 7.2 Breadcrumbs

Placed just above the H1, full-width across the content column:

```
Concepts  /  Fundamentals  /  Render API
```

- `text-sm text-fg-subtle`
- Each segment is a link to that level (section → sub-group → page)
- Separator `/` in `text-fg-subtle`
- Active (current) segment is not a link, slightly stronger color (`text-fg-muted`)

Generated from the sidebar nav tree by walking up from the current page.

### 7.3 Footer page-nav (prev / next)

At the bottom of the content article, two cards side-by-side:

```
+----------------------+   +----------------------+
| ← Previous           |   |           Next →     |
| Component defaults   |   | Single-file components|
+----------------------+   +----------------------+
```

- `display: flex; gap: 1rem; margin-top: 4rem`
- Border 1px subtle, `padding: 1rem 1.25rem`, `border-radius: 0.5rem`
- Hover: border lights up to `var(--c-link)` (the `border-glow` pattern from safe-ai-factory)
- Generated from the nav order (next-page / previous-page in the same sub-group; falls back to next sub-group)

---

## 8. Search overlay UX (Pagefind integration)

§11.1 owns the search index + Pagefind decision. This spike specifies the **visual surface only**.

### 8.1 Trigger

- Header search button described in §4
- Keyboard shortcut: `⌘K` (Mac) / `Ctrl+K` (Win/Linux)
- `/` alone also opens the modal (GitHub / VitePress convention)

### 8.2 Modal layout

```
+-------------------------------------------------------+
| [🔍] Search...                                   [Esc]|
+-------------------------------------------------------+
| Getting Started                                       |
|   Installation                                        |
|     ...how to <mark>install</mark> django-components..|
|                                                       |
| Concepts > Advanced                                   |
|   Component caching                                   |
|     ...the <mark>cache</mark> tag is loaded via...    |
|                                                       |
| ...                                                   |
+-------------------------------------------------------+
| ↑↓ navigate · ↵ select · esc close                    |
+-------------------------------------------------------+
```

- Centred, `width: min(600px, calc(100vw - 2rem))`, `max-height: 80vh`
- Backdrop: `background: rgba(0, 0, 0, 0.5)`, click-to-dismiss
- Input at top, `padding: 1rem`, `font-size: 1rem`, border-bottom subtle
- Results: each is a link, padded `0.75rem 1rem`, hover/keyboard-active has accent-dim background
- Result hierarchy shown: small breadcrumb above the result title, snippet below the title with `<mark>` highlighting matched terms
- Keyboard help footer at the bottom, `text-xs text-fg-subtle`

### 8.3 Empty / no-results / error states

- Empty (no input yet): show 5 most-common pages as "quick links" (Material does this; nice touch)
- No results: `No results for "{query}". Try a different term?` in `text-fg-muted`
- Error (Pagefind failed to load): fall back to a Google site:django-components.github.io link

### 8.4 Pagefind customization

Pagefind exposes a small CSS API. We override:

```css
:root {
  --pagefind-ui-primary: var(--c-accent);
  --pagefind-ui-text: var(--c-fg);
  --pagefind-ui-background: var(--c-surface);
  --pagefind-ui-border: var(--c-border);
  --pagefind-ui-tag: var(--c-link);
  --pagefind-ui-font: var(--font-sans);
  --pagefind-ui-border-radius: 0.5rem;
}
```

This is all that's needed to make Pagefind feel native. Confirmed against the Pagefind UI customization docs.

---

## 9. Light / dark / auto theming

### 9.1 What this spike commits to

- **Three modes:** auto (default — follows `prefers-color-scheme`), light, dark
- **Toggle** in the top header (§4), cycles auto → light → dark → auto
- **Two complete token sets** (light + dark), not one auto-derived from the other
- **Persisted** in `localStorage`, restored on page load before first paint (inline `<script>` in `<head>` to prevent FOUC)
- **All design tokens** (§10) are defined twice, once under `:root` for light and once under `[data-theme="dark"]` for dark; the `auto` mode applies dark tokens inside a `@media (prefers-color-scheme: dark)` block

### 9.2 What this spike defers

- The actual JS toggle implementation, FOUC-prevention `<script>` block placement, and `<html data-theme>` attribute switching are **owned by §11.1.G.1** (which calls dark/light toggle a prerequisite for search work)
- The specific Pygments themes selected for syntax highlighting are picked in Phase 1 by sampling 3 candidates each side and picking by feel

### 9.3 Sanity rules

- Body text contrast ratio against bg ≥ 7:1 in both modes (WCAG AAA for body text)
- Muted text against bg ≥ 4.5:1 (WCAG AA)
- Link colour distinguishable from body without relying solely on colour (we have the underline-on-hover; for inline links amid prose, the colour difference is the primary cue but we accept the accessibility hit because every link is followable by Tab anyway). Concretely: the link colour is chosen with ≥3:1 contrast against the body colour, not just the bg.

---

## 10. Design tokens (the canonical set)

The user asked for 5-8 tokens. Here are eight, organized as a token *system* (each token has light and dark values). All values are OKLCH, following safe-ai-factory's convention. Hex equivalents in comments are approximate, for sanity-checking.

### 10.1 Surface tokens (background hierarchy)

| Token | Light value | Dark value | Used for |
|---|---|---|---|
| `--c-bg` | `oklch(99% 0.003 250)` ≈ `#fbfcfd` | `oklch(15% 0.008 250)` ≈ `#0f1117` | Page background |
| `--c-surface` | `oklch(97% 0.005 250)` ≈ `#f1f4f7` | `oklch(18% 0.01 250)` ≈ `#161924` | Cards, modal panels |
| `--c-surface-2` | `oklch(95% 0.006 250)` ≈ `#e9edf2` | `oklch(21% 0.01 250)` ≈ `#1c1f2b` | `<pre>` background, inline-code bg fallback, table header |
| `--c-surface-3` | `oklch(92% 0.008 250)` ≈ `#dee3eb` | `oklch(25% 0.01 250)` ≈ `#23273a` | Deepest surface, used sparingly |

Slight blue tint (`0.003-0.01` chroma at hue `250`) avoids pure-grey, gives the UI a subtle "cool" temperature. Same as safe-ai-factory's iron-blue.

### 10.2 Foreground & border tokens

| Token | Light | Dark | Used for |
|---|---|---|---|
| `--c-fg` | `oklch(20% 0.01 250)` ≈ `#1d2030` | `oklch(94% 0.005 80)` ≈ `#f0ecdf` | Primary text (headings, strong) |
| `--c-fg-muted` | `oklch(40% 0.01 250)` ≈ `#525b6e` | `oklch(70% 0.008 80)` ≈ `#b3aa9a` | Body text |
| `--c-fg-subtle` | `oklch(55% 0.01 250)` ≈ `#797f8c` | `oklch(50% 0.008 80)` ≈ `#7a7264` | Labels, captions, breadcrumb separators |
| `--c-border` | `oklch(88% 0.005 250)` ≈ `#d0d5db` | `oklch(32% 0.01 250)` ≈ `#2d3043` | Default 1px borders |
| `--c-border-subtle` | `oklch(92% 0.005 250)` ≈ `#dde2e7` | `oklch(28% 0.01 250)` ≈ `#272a3b` | Subtle dividers |

### 10.3 Accent tokens (the brand colour — DECISION DEFERRED to Juro)

**Option A — muted teal** (continuity with current Material teal palette):

| Token | Light | Dark |
|---|---|---|
| `--c-accent` | `oklch(55% 0.13 195)` ≈ `#0d8a8a` | `oklch(72% 0.13 195)` ≈ `#3eb4b4` |
| `--c-accent-hover` | `oklch(48% 0.13 195)` ≈ `#0a7474` | `oklch(78% 0.13 195)` ≈ `#5cc8c8` |
| `--c-accent-dim` | `oklch(55% 0.13 195 / 10%)` | `oklch(72% 0.13 195 / 12%)` |

**Option B — Django bottle-green** (dogfoods the Django brand, ~`#0C4B33`-aligned):

| Token | Light | Dark |
|---|---|---|
| `--c-accent` | `oklch(40% 0.12 155)` ≈ `#0c5b3a` | `oklch(68% 0.13 155)` ≈ `#4eaa7c` |
| `--c-accent-hover` | `oklch(34% 0.12 155)` ≈ `#08482e` | `oklch(74% 0.13 155)` ≈ `#69c197` |
| `--c-accent-dim` | `oklch(40% 0.12 155 / 10%)` | `oklch(68% 0.13 155 / 12%)` |

Either works against the §10.1/§10.2 tokens at WCAG AA. Juro's call.

### 10.4 Link / secondary tokens

| Token | Light | Dark |
|---|---|---|
| `--c-link` | `oklch(55% 0.15 245)` ≈ `#3870c5` | `oklch(72% 0.13 245)` ≈ `#7aaae0` |
| `--c-link-hover` | `oklch(48% 0.15 245)` ≈ `#2a5da8` | `oklch(78% 0.13 245)` ≈ `#94c0eb` |
| `--c-link-dim` | `oklch(55% 0.15 245 / 10%)` | `oklch(72% 0.13 245 / 12%)` |

Steel-blue link complement, intentionally distinct from the accent so the two roles (action / link) don't collide. Safe-ai-factory's split.

### 10.5 Semantic admonition tokens

| Token | Hue | Used for |
|---|---|---|
| `--c-note` | 245 (blue) | `!!! note` admonitions |
| `--c-info` | 175 (teal-cyan) | `!!! info` admonitions |
| `--c-warning` | 70 (amber) | `!!! warning` admonitions |
| `--c-danger` | 25 (red) | Reserved for future, not used today |

Each follows the same pattern: `oklch(L C H)` for the accent line/text, `oklch(L C H / 8%)` for the tinted background.

### 10.6 Typography tokens

| Token | Value |
|---|---|
| `--font-sans` | `Inter, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif` |
| `--font-mono` | `ui-monospace, 'JetBrains Mono', 'Fira Code', 'Cascadia Code', Menlo, monospace` |

Two stacks. We don't ship Inter as a hosted font; we add a `<link>` tag for `https://rsms.me/inter/inter.css` (CDN, ~50ms cold). If we later want offline-first, we self-host (~80KB woff2).

### 10.7 Spacing & radius tokens

Standard Tailwind scale, no custom tokens. Border-radius commonly used:
- `0.2rem` for inline code pill
- `0.375rem` for buttons
- `0.5rem` for cards, code blocks, modals

### 10.8 Shadow tokens

Used sparingly:

| Token | Value |
|---|---|
| `--shadow-modal` | `0 25px 50px -12px oklch(0% 0 0 / 25%)` |
| `--shadow-card-hover` | `0 4px 12px oklch(0% 0 0 / 8%)` |

That's it. No floating shadow on regular content; the docs are flat.

---

## 11. Static HTML mock — two page types

The user asked for "a static HTML mock of a single page before building it as a component". Here are skeletal mocks for the two page shapes the docs serve. Both use the same `DocPage` outer layout; they differ in the `<main>` content.

These mocks **are not the implementation** — they're a visual contract. Phase 5 implementation is the §11.5 per-kind components plus a `DocPage` layout component that composes the chrome.

### 11.1 Page type A — concept / guide page

File: `docs/concepts/fundamentals/render_api.md` (one of our densest pages)

```html
<!DOCTYPE html>
<html lang="en" data-theme="auto">
<head>
  <meta charset="utf-8">
  <title>Render API · django-components</title>
  <!-- inline script: read localStorage theme, set data-theme before first paint -->
  <script>
    (function() {
      var t = localStorage.getItem('theme') || 'auto';
      if (t !== 'auto') document.documentElement.setAttribute('data-theme', t);
    })();
  </script>
  <link rel="stylesheet" href="/static/tokens.css">
  <link rel="stylesheet" href="/static/site.css">
  <link rel="stylesheet" href="/static/pygments-light.css" media="(prefers-color-scheme: light)">
  <link rel="stylesheet" href="/static/pygments-dark.css" media="(prefers-color-scheme: dark)">
</head>
<body>

  <!-- TOP HEADER -->
  <header class="djc-header">
    <div class="djc-header__inner">
      <a class="djc-logo" href="/">
        <svg class="djc-logo__icon">…</svg>
        <span class="djc-logo__wordmark">django-components</span>
      </a>
      <nav class="djc-header__nav">
        <a href="/docs/">Docs</a>
        <a href="/examples/">Examples</a>
        <a href="/plugins/">Plugins</a>
        <!-- Blog: hidden until first post lands -->
        <!-- <a href="/blog/">Blog</a> -->
      </nav>
      <div class="djc-header__actions">
        <button class="djc-search-trigger">
          <span>Search…</span>
          <kbd>⌘K</kbd>
        </button>
        <div class="djc-version-picker">v0.150 ▾</div>
        <button class="djc-theme-toggle" aria-label="Toggle theme">☼</button>
        <a class="djc-gh" href="https://github.com/django-components/django-components" aria-label="GitHub"><svg>…</svg></a>
      </div>
    </div>
  </header>

  <!-- LAYOUT -->
  <div class="djc-layout">

    <!-- LEFT SIDEBAR -->
    <aside class="djc-sidebar">
      <nav>
        <div class="djc-sidebar__section">
          <div class="djc-sidebar__label">Concepts</div>
          <div class="djc-sidebar__group" data-open="true">
            <button class="djc-sidebar__group-label">Fundamentals ▾</button>
            <ul class="djc-sidebar__items">
              <li><a class="is-active" href="/docs/concepts/fundamentals/render_api/">Render API</a></li>
              <li><a href="/docs/concepts/fundamentals/component_defaults/">Component defaults</a></li>
              <li><a href="/docs/concepts/fundamentals/single_file_components/">Single-file components</a></li>
              ...
            </ul>
          </div>
          <div class="djc-sidebar__group" data-open="false">
            <button class="djc-sidebar__group-label">Advanced ▸</button>
            <ul class="djc-sidebar__items" hidden>…</ul>
          </div>
        </div>
        <div class="djc-sidebar__section">
          <div class="djc-sidebar__label">Reference</div>
          <ul class="djc-sidebar__items">
            <li><a href="/docs/reference/components/">Components</a></li>
            ...
          </ul>
        </div>
        …
      </nav>
    </aside>

    <!-- CONTENT -->
    <main class="djc-content">
      <nav class="djc-breadcrumbs">
        <a href="/docs/">Docs</a> /
        <a href="/docs/concepts/">Concepts</a> /
        <a href="/docs/concepts/fundamentals/">Fundamentals</a> /
        <span>Render API</span>
      </nav>

      <article class="prose">
        <h1>Render API</h1>

        <p>The Render API gives you the methods Component uses to produce HTML…</p>

        <h2 id="get_template_data">
          <a class="anchor" href="#get_template_data">#</a>
          get_template_data
        </h2>
        <p>Called once per render. Returns the dict that becomes the template context…</p>

        <pre><code class="djc-code djc_py">…syntax-highlighted python…</code></pre>

        <!-- ADMONITION -->
        <aside class="djc-admonition djc-admonition--note">
          <div class="djc-admonition__label">NOTE</div>
          <p>This method runs even on cache hits. Don't put expensive…</p>
        </aside>

        …
      </article>

      <nav class="djc-page-nav">
        <a class="djc-page-nav__prev" href="/docs/concepts/fundamentals/component_defaults/">
          ← Previous<br>
          <strong>Component defaults</strong>
        </a>
        <a class="djc-page-nav__next" href="/docs/concepts/fundamentals/single_file_components/">
          Next →<br>
          <strong>Single-file components</strong>
        </a>
      </nav>
    </main>

    <!-- RIGHT TOC -->
    <aside class="djc-toc">
      <div class="djc-toc__label">On this page</div>
      <ul>
        <li><a class="is-active" href="#get_template_data">get_template_data</a></li>
        <li><a href="#get_js_data">get_js_data</a></li>
        <li><a href="#get_css_data">get_css_data</a></li>
        ...
      </ul>
    </aside>
  </div>

  <!-- PAGEFIND modal (hidden by default; opens on ⌘K) -->
  <div class="djc-search-modal" hidden>…</div>

  <script src="/_pagefind/pagefind-ui.js"></script>
  <script src="/static/site.js"></script>
</body>
</html>
```

Annotated styling note for any element prefixed `djc-`: classes are flat (BEM-style) so the corresponding Django component template owns them 1:1. No descendant-selector creep into element styling.

### 11.2 Page type B — API reference page

Same chrome (header, sidebar, right TOC); the `<article>` content shape differs.

```html
<article class="prose">
  <h1>Components</h1>

  <p>Every public component class in <code>django_components</code> lives on this page. Use ⌘K to jump to a specific symbol.</p>

  <!-- SYMBOL ENTRY -->
  <section class="djc-symbol" id="Component">
    <header class="djc-symbol__header">
      <span class="djc-symbol__badge djc-symbol__badge--class">class</span>
      <h2 class="djc-symbol__title">
        <a class="anchor" href="#Component">#</a>
        Component
      </h2>
      <a class="djc-symbol__source" href="https://github.com/.../component.py#L42">→ source</a>
    </header>

    <div class="djc-symbol__signature">
      <pre><code class="djc-code python">class Component(metaclass=ComponentMeta):
    ...</code></pre>
    </div>

    <div class="djc-symbol__bases">
      <span class="djc-symbol__bases-label">Bases:</span>
      <code>object</code>
    </div>

    <div class="djc-symbol__docstring prose">
      <p>The base class every component inherits from…</p>
    </div>

    <h3>Parameters</h3>
    <table class="djc-params">
      <thead>
        <tr><th>Name</th><th>Type</th><th>Description</th></tr>
      </thead>
      <tbody>
        <tr>
          <td><code>args</code></td>
          <td><code>tuple</code></td>
          <td>Positional arguments…</td>
        </tr>
        ...
      </tbody>
    </table>

    <h3>Methods</h3>
    <!-- nested .djc-symbol blocks for each method -->
    <section class="djc-symbol djc-symbol--nested" id="Component.render">
      <header class="djc-symbol__header">
        <span class="djc-symbol__badge djc-symbol__badge--method">method</span>
        <h3 class="djc-symbol__title">
          <a class="anchor" href="#Component.render">#</a>
          render
        </h3>
        <a class="djc-symbol__source" href="…">→ source</a>
      </header>
      …
    </section>
  </section>

  <!-- NEXT SYMBOL -->
  <section class="djc-symbol" id="ComponentRegistry">…</section>
</article>
```

Key visual treatments unique to API reference pages:

- `djc-symbol`: a vertically-stacked block with `padding: 1.5rem 0; border-top: 1px solid var(--c-border-subtle)` separating sibling symbols
- `djc-symbol__badge`: small uppercase pill on the left, `font-size: 0.7rem`, color-coded by kind (`--c-link` for class, `--c-accent` for method, `--c-warning` for setting, etc.)
- `djc-symbol__source`: subtle link in `text-xs text-fg-subtle`, hover brightens
- `djc-symbol--nested`: indented `1.5rem` to show containment within a class
- `djc-params`: standard table; the first column auto-styles as mono code

### 11.3 What the mocks deliberately omit

- Logo SVG content (placeholder)
- The Pagefind modal full markup (Pagefind UI emits this — we only style it)
- The version-picker dropdown menu markup (a `<details><summary>` pattern; trivial)
- All actual content; the mocks are about structure
- Per-component CSS — that's Phase 5 work

### 11.4 First concrete implementation step

During Phase 1 of the migration:

1. Build the `DocPage` Django component with **just the chrome** — header, sidebar (statically populated from a hard-coded JSON for now), content slot, right-TOC slot, footer page-nav
2. Render one fake content page through it, verifying the layout at 1280px / 1024px / 768px / 375px
3. Ship the design tokens (§10) as `static/tokens.css`
4. Ship a minimal `site.css` with the prose styles (§5) and code-block styles (§6)
5. Confirm with Juro that the visual direction reads correctly before any markdown rendering work begins

Estimated effort: 1-2 days for one developer. Cheapest way to lock in the direction before Phase 1's markdown work commits to specific component shapes.

---

## 12. Out of scope for this spike

- Specific brand asset (logo SVG, favicon, social-card template) — those are art-direction work, separate from layout/component design
- Pages outside the docs (the project marketing homepage, if there is one — currently there isn't; `/` is just the docs landing)
- Tutorial pages with interactive scrub-through code (not in our content today; not in the migration scope)
- The `Tabs` component used for pip / uv / poetry install variants in §11.6.D — its visual treatment is "render the same way as the `{% example %}` widget's tab strip" (§6.4); no separate spec needed
- Animation / motion design — the only motion we ship is the 150ms fade-in of copy buttons and anchor `#` glyphs on hover. No page-transition animation
- Print stylesheet — defer; nobody prints library docs

---

## 13. Risks & open items

### 13.1 Risks during execution

1. **Visual brand collision during the rollout.** The new site looks distinctly different from the current Material one. Some readers will read the change as "the project rebranded". Mitigation: stage on `next.django-components.github.io` (or a `/preview/` path under the existing site) so the diff is intentional. Cutover is a single commit. Phase 6 of the main doc handles this.
2. **URL move under `/docs/` (§4.2) breaks every inbound link to docs pages.** Bounded but real cost: ~8 directory prefixes (`getting_started`, `concepts`, `reference`, etc.) plus their children. Mitigation: (a) auto-generate `<meta http-equiv="refresh">` redirect files at every old URL from the inversion of the move map; (b) extend the §11.6.F anchor codemod to also rewrite internal `/concepts/foo.md` → `/docs/concepts/foo.md` in the same precursor PR; (c) call the URL change out in the release announcement so blog authors with links can update at their leisure. The redirect machinery from §11.9.2.5 already covers the GitHub Pages serving semantics.
3. **Landing page scope creep.** Introducing a dedicated landing page at `/` is structurally clean but visually demanding (hero, feature cards, code example, footer). **Mitigation in place:** the landing page is its own phase at the *end* of the migration plan (Phase 9 in main doc §8), explicitly framed as a codesign exercise. Phases 1-8 ship a thin placeholder (~50 LOC, see §4.4) so the top-nav taxonomy works end-to-end. Phase 9 replaces the placeholder via iteration with Juro. The risk this controls: landing-page bikeshedding stealing focus from the docs migration's core work.
4. **Pygments theme picks are subjective.** Two Pygments stylesheets (light + dark) will be picked by feel during Phase 1. The risk is one looks great and the other looks washed out. Mitigation: sample three candidates each, pick by comparison against a representative dense Python page (`render_api.md`).
5. **OKLCH browser support.** OKLCH is supported in Chromium 111+, Safari 16.4+, Firefox 113+ (all 2023). For older browsers, we fall back to the hex values inline. Spike on this in Phase 1 by checking analytics for browser versions; if <0.5% of readers are on pre-OKLCH browsers, ship without fallback.
6. **Inter font CDN dependency.** Adding `https://rsms.me/inter/inter.css` adds a single off-origin request. If we want zero off-origin requests (some readers in restricted networks), self-host. Decision is one line of HTML.
7. **Accent colour choice may be re-litigated.** §10.3 defers between teal and Django-green. If neither lands well in Juro's review, we may iterate on a third option. Low-blast-radius — it's one token swap.

### 13.2 Items deferred to other spikes

- **Dark / light toggle JS implementation** — §11.1.G.1
- **Per-kind component visual templates (the API reference layouts)** — §11.5 already owns the per-kind component set; this spike specifies the styling but the implementation belongs there
- **Search modal full implementation** — §11.1 (Pagefind integration + index emission)
- **Theme affordances ledger (copy button, edit-on-GitHub button, scroll-spy, back-to-top, breadcrumbs, sticky TOC)** — §11.6.C confirmed scope; this spike specifies the visual treatment
- **Nav YAML loader implementation** — §11.9.2.2 (we extend the schema in §3.2 of this spike)
- **Sidebar component build** — Phase 5 component design

### 13.3 Items deferred to implementation

- Picking the specific Pygments themes (light + dark) — sample during Phase 1
- Final wordmark / logo art — separate brand work
- Whether to ship Inter via CDN or self-host — pick before Phase 1 deploys publicly
- Whether the version picker is a `<details>` element or a custom dropdown — Phase 5 decision, low stakes either way
- Exact icon set for the theme toggle — we sketched sun / moon / auto; could be Lucide, Material Symbols, or hand-rolled SVG

---

## 14. Where this feeds back

- **§4.1** (top-level shape) — the `components/page_layout/` Django component named there is the `DocPage` outer chrome specified in §11. A separate `LandingPage` component at `/` is introduced (see §4.4); `DocPage` is no longer the only top-level layout
- **§4.2** (URL stability) — the URL move under `/docs/` (§4.2 of this spike) is a deliberate structural change. Update §4.2 of the main doc to record it. The §11.6.F codemod scope grows by one more rewrite (relative docs paths gain `/docs/` prefix); the §11.9.2.5 redirect machinery handles inbound links
- **§5** (what we lose, what we gain) — the "Material's polish" loss is now concretely sized: a coherent set of tokens + components matching VitePress / safe-ai-factory quality, not a bespoke design system from scratch
- **§11.1.G.1** (search prerequisite) — confirms the visual direction the dark/light toggle ships into
- **§11.5** (per-kind renderers) — provides the visual envelope (badge, signature callout, parameter table style) for the components §11.5 implements
- **§11.6** (markdown directives + pymdownx.tabbed) — the unified `CodeTabs` component in §6.4 is the visual surface for *all three* tab-shaped affordances: `{% example %}`, `pymdownx.tabbed` blocks (install variants etc.), and code-fence `title="..."` labels. One component, one CSS rule, three authoring entry points
- **§11.6.C** (theme-affordances ledger) — confirms scope; this spike supplies the styling for every row in that ledger
- **§11.9** (plugin audit) — the Material `theme.palette` colors and typography slot is now decided here. The redirect machinery decision (§11.9.2.5) gains a major reusable consumer: the URL move per §4.2 generates ~hundreds of redirect files via the same writer
- **§11.10** (guardrails) — gains an additional CI check: every URL listed in the §4.2 move map must have a redirect file at its old path. Trivial to assert, prevents the URL change from leaking broken links
- **Phase 1** (main doc §8) — the first concrete step is "ship `DocPage` chrome at 1-2 days of effort" (§11.4 of this spike). The thin landing-page scaffold (§4.4) lands in the same phase
- **Phase 5** (search, versioning, social cards) — the social-card template (§11.9.2.4) is rendered through the same token system; cards inherit the brand by reusing `--c-bg`, `--c-fg`, `--c-accent`
