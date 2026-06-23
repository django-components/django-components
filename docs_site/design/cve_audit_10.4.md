# CVE audit — frozen Material / plugin bundles (feature 10.4)

**Date:** 2026-06-18 · **Scope:** the JavaScript bundled in / referenced by the
59 historical doc-version snapshots imported from `origin/gh-pages` (feature
6.2), plus the asv benchmark report. **One-off sweep** per Phase 10.4; feeds the
selective-rebuild decision (10.1).

CVE data was verified against NVD, the GitHub Advisory Database, and Snyk (not
from memory). Sources are cited inline.

## TL;DR

- **The live user docs are clean.** Root (`/`, `/docs/`) and the `latest` alias
  are built by the new Django `docs_site` builder, which ships its own JS
  (`site.js`, `search.js`, `pagefind-*`) and **no jQuery and no Material at all**.
  None of the findings below touch the docs a normal visitor reads.
- **Two carriers of old JS remain, both low-real-risk:**
  1. **The asv benchmark report** (`/benchmarks/` *and* a copy inside every
     frozen `/v/<version>/benchmarks/`) loads **jQuery 3.3.1** and **Bootstrap
     3.1.1** from CDNs — both EOL with known XSS CVEs.
  2. **One** frozen version, **`/v/0.92/`** (Material 9.5.16), carries the
     Material search RXSS fixed in 9.5.32. The other 58 versions are 9.5.34+.
- **Verdict: accept the residual risk; no immediate rebuild warranted.** Frozen
  versions are `noindex` + robots-disallowed, byte-frozen by design, and serve
  only static first-party data. Recommendations (SRI on the asv CDN refs; bump
  jQuery if/when convenient) are tracked as follow-ups, not blockers.

## What's bundled / referenced

| Library | Version(s) | Where | Loaded how |
|---|---|---|---|
| jQuery | 3.3.1 | asv report (current + 58 frozen `/v/*/benchmarks/`) | CDN (`code.jquery.com`) |
| Bootstrap | 3.1.1 | asv report | CDN (`jsdelivr`) |
| flot | 0.8.3 (+ flot-orderbars 1.0.0, `jquery.flot.axislabels` local) | asv report | CDN + 1 local file |
| blueimp-md5 | 2.19.0 | asv report | CDN |
| stupidtable | 1.0.1 | asv report | CDN |
| Material for MkDocs | 9.5.16 – 9.7.6 (per version) | frozen `/v/<version>/` | bundled (`bundle.*.min.js`) |
| lunr.js | 2.3.9 (+ language packs) | frozen `/v/*/` search | bundled |
| timeago.js | 4.0.2 | frozen `/v/*/` | bundled |
| pyodide | (markdown-exec loader) | some frozen `/v/*/` | CDN |

## Findings

### 1. asv report — jQuery 3.3.1 (3 CVEs, one CISA-KEV)

| CVE | Severity | Fixed in | Trigger |
|---|---|---|---|
| CVE-2019-11358 | 6.1 | 3.4.0 | prototype pollution via `jQuery.extend(true, …)` over an attacker object with `__proto__` |
| CVE-2020-11022 | 6.1 | 3.5.0 | XSS: untrusted HTML into `.html()`/`.append()` etc. |
| CVE-2020-11023 | 6.1 | 3.5.0 | XSS via untrusted `<option>` HTML. **CISA-KEV (actively exploited).** |

Sources: GHSA-6c3j-c64m-qhgq · GHSA-gxr4-xjj5-5px2 · GHSA-jpcq-cgw6-v4j6.

**Exploitability here: not practical.** All three require *attacker-controlled
input reaching a DOM sink*. The asv report renders only benchmark JSON generated
by our own CI. A targeted check (`location.hash`/`location.search` → `.html()`)
found **no path** where a URL-derived value is injected as HTML — the report uses
`window.location` for hash routing only. So even the KEV CVE is not reachable
with the data we serve.

### 2. asv report — Bootstrap 3.1.1 (EOL, 3 CVEs)

| CVE | Severity | Fixed in | Trigger |
|---|---|---|---|
| CVE-2016-10735 | 6.1 | 3.4.0 | XSS via `data-target` |
| CVE-2018-14042 | 6.1 | 3.4.0 | XSS via tooltip `data-container` |
| CVE-2019-8331 | 6.1 | 3.4.1 | XSS via tooltip/popover `data-template` |

Bootstrap 3.x is end-of-life. All three need an attacker to control a `data-*`
attribute value; static, CI-generated markup gives no such injection point →
not practically exploitable. (CVE-2018-14041 is Bootstrap 4.x only — N/A.)

### 3. Material for MkDocs — search RXSS, only `/v/0.92/`

`SNYK-PYTHON-MKDOCSMATERIAL-7856160` (CVSS 5.1, reflected XSS via a crafted
deep-link into search results), fixed in **9.5.32**. Mapping every version dir to
its bundled Material version, **only `0.92` (9.5.16)** falls in the affected
`<9.5.32` range; `0.96`+ are all 9.5.34 → 9.7.6 and clean. Low impact on an
auth-less docs site, and `/v/0.92/` is the oldest, lowest-traffic snapshot.
(Note: the squidfunk/mkdocs-material project has zero published GitHub
advisories; this is Snyk-only. CVE-2021-40978 is mkdocs *core*, build-time, not
the theme.)

### 4. No actionable CVEs

- **flot 0.8.3 / flot-orderbars 1.0.0** — no direct advisory (risk inherited
  from jQuery); unmaintained.
- **blueimp-md5 2.19.0**, **stupidtable 1.0.1**, **lunr 2.3.9** — no known CVEs.
- **timeago.js 4.0.2** — **clean.** The May 2026 npm supply-chain worm
  compromised 4.1.2 / 4.2.2, *not* 4.0.2, and the frozen snapshots were built
  before that date.
- **pyodide** — no CVEs in pyodide itself (the headline "pyodide" CVEs are
  server-side sandbox-escape bugs in *other* apps that run untrusted Python).
  In-browser, author-written Python in the visitor's own tab is negligible risk.

## Risk assessment

Three factors keep real-world risk low:

1. **No untrusted input reaches the vulnerable code paths.** Every exploitable
   CVE above needs attacker-controlled HTML/attributes at a DOM sink; the asv
   report only renders our own static benchmark JSON, and no URL-derived value
   feeds a jQuery sink (verified).
2. **Blast radius is the benchmark dashboard and frozen archives, not the docs.**
   The live docs use none of these libraries.
3. **Frozen versions are `noindex` + robots-disallowed** (feature 6.12b's
   `seo.write_robots` disallows old `/v/<version>/`), so they're low-traffic and
   out of search.

The larger *posture* concerns are scanner/compliance noise (jQuery 3.3.1 and
Bootstrap 3.1.1 will always be flagged) and **CDN supply-chain integrity** — the
asv report's CDN `<script>`s have no Subresource Integrity (SRI) hashes, so a
tampered CDN asset would run regardless of the "static data" mitigation.

## Decision & recommendations

**Decision: accept the residual risk. No version rebuild is triggered by this
audit.** The frozen tree is byte-frozen by design (we do not rewrite imported
HTML), and nothing here is practically exploitable.

Recommended follow-ups (not blockers; track separately if pursued):

- **asv report (current `/benchmarks/`)** — the one live carrier. Cheapest wins,
  in order: (a) add SRI hashes to the CDN `<script>`/`<link>` refs; (b) bump the
  jQuery CDN ref 3.3.1 → ≥3.5.0 (jQuery 3.x is broadly compatible) and Bootstrap
  → 3.4.1. This is an asv-output post-processing / config task, not a docs-builder
  change, so it's out of scope for 10.4's "audit" deliverable.
- **`/v/0.92/` Material RXSS** — fixable only by a selective rebuild (feature
  10.1) with Material ≥9.5.32. Not worth it for the oldest snapshot unless
  analytics later show meaningful traffic.
- **Re-run this sweep** whenever new versions are imported or asv's bundled libs
  change.
