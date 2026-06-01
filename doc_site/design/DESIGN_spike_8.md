# Spike 11.8 — Migrating older docs versions

**Status:** spike complete (decision deferred per [§11.7 spike §7](DESIGN_djc_docs_site_spike_11_7.md))
**Date:** 2026-05-31
**Feeds back into:** [DESIGN_djc_docs_site.md §11.8](DESIGN_djc_docs_site.md), [§4.6 Versioning](DESIGN_djc_docs_site.md), and [§5 Migration plan](DESIGN_djc_docs_site.md) (Phase 6 cutover + Phase 7+)
**Spike question:** What do we do with the 40+ historical `gh-pages` doc versions when the new builder is canonical? Inbound links from blog posts, Stack Overflow, search engines must not break.

---

## 0. TL;DR verdict

**RECOMMEND: Freeze-all-and-import** (option 2 from the original three). One commit at cutover imports every existing `gh-pages` version dir into `master/docs/v/` as immutable artifacts. New versions land via the new builder from then on.

**Why this is the right answer despite earlier hesitation:**

1. **The gh-pages bare repo is only 114 MB** — the "1 GB" working-tree size was an artifact of Material's CSS/JS being decompressed 57 times. The packed git data deltifies extremely well because every version shares ~95% of its bundled assets. **Master gains ~100-150 MB of objects**, not a gigabyte.
2. **URL structure changed twice** (post-0.110 layout overhaul, post-0.124 reference restructure). For pre-0.124 versions, **rebuilding would produce different URLs** — i.e. rebuilding *guarantees* breakage that freezing avoids.
3. **Anchor scheme is changing** ([§11.5 spike §7](DESIGN_djc_docs_site_spike_11_5.md)) — `#django_components.Component` → `#Component`. If we rebuild any old version, its inbound `#django_components.X` links break unless we emit legacy aliases. Freezing skips this work entirely.
4. **Decision is reversible.** The walker from [§11.7 spike §3.2](DESIGN_djc_docs_site_spike_11_7.md) is option-agnostic. After Phase 7 we can selectively rebuild any subset; freezing at cutover is just the cheap default.

**Per Juro's earlier note** ([§11.7 spike §7](DESIGN_djc_docs_site_spike_11_7.md)): the final policy is deferred until **after Phase 7**. This spike's contribution is to (a) inventory the actual state, (b) quantify what each option costs, and (c) pre-load the decision so post-Phase-7 picks from data instead of intuition.

**Biggest risks** to manage at execution:
1. **Material assets shared across version dirs.** When we import, git deltification works *if* paths match. We must import the **tree** verbatim — no path rewriting in flight — or we lose the deduplication and bloat balloons.
2. **The org rename from `emilstenstrom.github.io` → `django-components.github.io`** persists in old `sitemap.xml` and any `<link rel="canonical">` tags. GitHub's redirect-on-rename keeps inbound URLs alive, but we should audit whether frozen sitemaps cause SEO weirdness (we likely just want to add a top-level sitemap-index that points only at `latest/`).
3. **Old Material JS bundles ship with whatever CVEs the era's Material had.** Freezing means we don't patch them. Mitigation: if any frozen JS has a known vuln, add a Content-Security-Policy meta tag in a tiny patcher step (or rebuild *just* the affected versions later).

**Recommended next move:** **don't do anything in this spike's window.** Just commit the inventory below to the design doc, run the actual freeze at Phase 6 (cutover), and revisit selectively at Phase 7+.

---

## 1. The state of `gh-pages` today

Audited against the live `origin/gh-pages` branch.

### 1.1 Inventory

- **57 entries** in `versions.json` (56 release versions + `dev`).
- **Oldest version:** `0.92`. **Newest:** `0.150.0` (aliased as `latest`).
- **Branch history:** 457 commits, going back to a `dev` deploy of commit `36b8fcf` with MkDocs 1.5.3 + mike 2.0.0.
- **Bare repo size:** **114 MB** (vs. 1.0 GB working-tree expansion — the 9× ratio comes from Material assets repeating across versions, which git deltifies near-perfectly).
- **Working-tree size by era:**
    | Era | Versions | Avg per-version disk | Notes |
    |---|---|---|---|
    | 0.92 - 0.110 | 5 | ~7 MB | Pre-Material flat structure, monolithic `index.html` |
    | 0.111 - 0.123 | 13 | ~8 MB | Concepts/Guides era; mkdocstrings auto-tree for reference |
    | 0.124 - 0.134 | 11 | ~10 MB | Modern URL skeleton starts; reference uses per-page model |
    | 0.135 - 0.146 | 12 | ~30 MB | API ref expands (`testing_api`, `extension_hooks`, etc.) |
    | 0.148.0 - 0.150.0 | 3 | ~40 MB | Current era — full reference + benchmarks |

### 1.2 What's missing (per the manifest)

Three release tags exist in git but NOT in `gh-pages`:
- `0.140.0` — manifest jumps `0.139.1` → `0.140.1` (likely a release that was retracted)
- `0.147.0` — manifest jumps `0.146.0` → `0.148.0`

For these, we don't need to do anything — they were never deployed in the first place, so no URLs point at them.

### 1.3 What's at the root of gh-pages

```
versions.json                       # 57-entry manifest
index.html                          # redirect to latest/
robots.txt                          # sitemap: latest/sitemap.xml
.nojekyll
404.html (in each version dir)
{version}/                          # 57 dirs
latest/                             # mode-120000 symlink to 0.150.0
dev/                                # current master HEAD deploy
```

The root `index.html` is a meta-refresh + JS redirect to `latest/`. Same as mike's [`templates/redirect.html`](https://github.com/jimporter/mike/blob/master/mike/templates/redirect.html). The `robots.txt` only advertises `latest/sitemap.xml`, so SEO crawlers don't index every historical version.

### 1.4 Probe: URL drift between eras

Comparing sitemap URLs across versions surfaces three breakpoints:

| Era | URL examples | Drift from current |
|---|---|---|
| **0.92 - 0.110** | `latest/CHANGELOG/`, `latest/slot_rendering/`, `latest/devguides/dependency_mgmt/` | **Massive.** Flat structure, no nesting. `index.html` of `0.92` is a literal 1,149-line monolithic page. Inbound URLs to `slot_rendering/` no longer have an equivalent path in modern docs. |
| **0.111 - 0.123** | `latest/concepts/...`, `latest/devguides/...`, `latest/reference/django_components/...` | **Significant.** "concepts/" introduced but reference uses mkdocstrings' deep tree (`reference/django_components/...`). Modern reference is flat (`reference/settings/`, etc.). |
| **0.124 - 0.150.0** | `latest/concepts/...`, `latest/getting_started/...`, `latest/reference/settings/` | **Negligible.** Top-level URL skeleton unchanged from 0.124 onward. Minor additions inside `reference/` (`testing_api/` lands at 0.135, etc.) but those are additive, not renames. |

### 1.5 The org rename in old sitemaps

Sitemaps in old versions reference different hostnames:

- **0.92 - 0.124:** `https://emilstenstrom.github.io/django-components/latest/...`
- **0.139 - 0.150.0:** `https://django-components.github.io/django-components/latest/...`

GitHub's username-rename keeps `emilstenstrom.github.io` redirecting to `django-components.github.io` forever, so inbound URLs from the old host still resolve. But search engines see two distinct sitemap origins for the same content. Likely already self-resolved in search index by now; the rename happened years ago.

### 1.6 The hand-typed `#django_components.X` anchors

Per [§11.5 spike](DESIGN_djc_docs_site_spike_11_5.md), 397 hand-typed markdown links in current `src/` docstrings use the dotted-path anchor form (`api.md#django_components.Component`). The new builder anchors as `#Component` (dotted path dropped) and emits a legacy alias for back-compat.

For **frozen** old versions, this isn't relevant — their HTML is what it is; we never rerender. Their anchors stay `#django_components.Component`. Visitors of old versions get the old behavior. Fine.

For **rebuilt** old versions, the same legacy-alias mechanism we built for the current version would apply. Cost is uniform across versions, so this isn't a freeze-vs-rebuild discriminator.

---

## 2. What "preserve URLs" actually means

Defining the contract before evaluating options:

1. **Every URL currently resolvable on `gh-pages` must keep resolving after cutover**, byte-identical or semantically equivalent (a meta-refresh redirect to the same content is acceptable; a 404 is not).
2. **`latest/` continues to point at the newest stable** (currently 0.150.0; soon whatever ships next).
3. **`dev/` continues to point at the newest master commit's docs** (built on every master push).
4. **The version picker (per [§11.7 spike §5](DESIGN_djc_docs_site_spike_11_7.md)) lists every version that exists** — frozen or rebuilt makes no difference at the manifest level.
5. **Inbound links to specific anchors** (`#django_components.Component` inside an old version) keep resolving because the anchor was emitted by the old build and we're not touching the HTML.

We do NOT promise:
- That re-crawling search engines see byte-identical HTML for old versions (we control `latest/` only).
- That old in-page JS keeps working in modern browsers (rare-but-possible: deprecated APIs in old Material bundles).
- That CVEs in old bundled JS get patched in-place (mitigations below).

---

## 3. The three options, with concrete numbers

| Option | What happens at cutover | Disk delta to master | Engineering risk | URL guarantee |
|---|---|---|---|---|
| **1. Rebuild all** | `docs-build-all` walks every tag, produces fresh `docs/v/<v>/` | ~150 MB (compressible, less deltification because new HTML differs from old) | **High.** Pre-0.124 URLs *cannot* survive (different layout). Old markdown directives may not survive the new builder. Anchor scheme changes for all. | **Broken** for pre-0.124 versions |
| **2. Freeze + import all** | One commit copies `origin/gh-pages` tree → `master/docs/v/`. Future versions land via new builder | **~100-150 MB** (bare-repo size; deltification kicks in because we import the exact tree mike produced) | **Low.** No re-rendering; just a file copy + path remap (gh-pages root → `docs/v/`) | **Preserved** byte-for-byte for everything |
| **3. Hybrid** | Freeze pre-cutoff + rebuild post-cutoff. Cutoff is e.g. `0.135` | ~80-100 MB freeze + ~80 MB rebuild = ~180 MB | **Medium.** Cutoff line needs justification. Rebuild risk for `≥cutoff` is real — old markdown may not survive new directives | **Mostly preserved** with some rebuilt anchor changes |

**The killer fact from §1:** the bare gh-pages repo is **only 114 MB**. The freeze option's bloat fear was based on the 1 GB working-tree number, which was misleading. Material's CSS/JS bundle is ~5 MB and identical across versions; git deltifies it across 57 dirs to effectively a single copy.

This collapses Option 2's main downside.

---

## 4. The two real breakpoints

Already in §1.4 but worth restating because they drive any "hybrid" line:

### Breakpoint A — at 0.110 → 0.111

URL structure changes from flat (`/CHANGELOG/`, `/slot_rendering/`) to nested (`/concepts/`, `/devguides/`). Rebuilding 0.92-0.110 with the new builder produces fundamentally different URLs that don't match what any inbound link expects. **These must be frozen**, no exceptions.

### Breakpoint B — at 0.123 → 0.124

Reference page structure changes from mkdocstrings' deep tree (`reference/django_components/Component/`) to the per-topic-page model we have today (`reference/settings/`, `reference/template_tags/`, etc.). Top-level URL skeleton (`concepts/`, `guides/`) is now stable.

### What's actually stable

From 0.124 onward, URL drift is **additive** (new reference pages added, old ones not renamed). A rebuild of 0.124+ with the new builder produces *mostly* the same URLs, with these caveats:
- **Anchors change** (`#django_components.X` → `#X`), mitigated by emitting legacy aliases.
- **`reference/template_tags/`, `reference/middlewares/`, `reference/exceptions/`** existed at 0.124 but not at 0.150.0. If we rebuild 0.124 using *current* `reference.py`, those pages don't get generated and the URLs 404.

So even within "stable era," rebuild requires running the *era's own* `reference.py` config, not the current one. That's possible — `docs-build-all` checks out the tag — but it means we have to keep the *old* `reference.py` runnable under the *new* builder, which is engineering risk.

### Verdict for hybrid cutoff

If we ever do hybrid, cutoff would land at **0.148.0** (the earliest version where current `reference.py` matches what we'd produce). Below 0.148 → freeze. At/above → rebuild possible.

But that's only 3 versions (0.148, 0.149, 0.150) — barely worth the orchestration. **Freeze-all is cheaper.**

---

## 5. Recommendation

### 5.1 Default plan for Phase 6 cutover

**Freeze + import all.** One PR at Phase 6 cutover:

1. Add `docs/v/` to master.
2. `git read-tree origin/gh-pages` into `docs/v/` (or `git checkout origin/gh-pages -- .` into a scratch worktree, then copy).
3. Verify the resulting tree:
    - `docs/v/versions.json` matches `origin/gh-pages:versions.json`
    - Every version dir present
    - `docs/v/latest/` is a symlink OR (preferred — see §6 below) replaced with redirect files pointing at `docs/v/0.150.0/`
    - `docs/v/dev/` either copied as-is OR omitted and rebuilt on the next master push
4. Commit. Disk delta should land at ~100-150 MB of packed objects.
5. Switch GitHub Pages source to `master/docs/v/` (via Actions workflow or repo settings).
6. Delete the `gh-pages` branch *after* a few weeks of confirmed working deploy.

### 5.2 Post-Phase-7 follow-up

After Phase 7 (search v2), revisit:

- **Should we rebuild any frozen version?** Probably yes for `0.148+`, where old markdown is most compatible with new directives and the anchor-scheme benefit is real. Use search analytics (if enabled in Phase 7) to decide which versions get the most traffic.
- **Should we prune very-old versions?** `0.92-0.110` (5 dirs, ~35 MB) are pre-Material monolithic pages. Almost no inbound traffic. Could be moved to a `docs-archive` orphan branch and removed from `latest/sitemap.xml` advertising. **Don't prune in Phase 6** — frozen-and-kept is the lowest-risk default.

---

## 6. Aliases — symlink vs redirect on master

Already covered in [§11.7 spike §2.4](DESIGN_djc_docs_site_spike_11_7.md): on `master/docs/v/`, switch from `symlink` (current gh-pages mode) to `redirect`. The import step must materialize redirects:

- gh-pages has `latest/` as a mode-`120000` git symlink. When we import the tree into `master/docs/v/`, git would faithfully preserve the symlink — but that's the Windows-clone footgun [§11.7 §2.4] specifically warns against.
- **Import step replaces the symlink with redirect HTML files.** For every `latest/<path>` URL that existed before, write a tiny redirect HTML pointing at `0.150.0/<path>`. ~15 lines per page × pages = ~5 MB extra. Marginal.

This is a small custom step in the import, not a separate phase.

---

## 7. Migration mechanics — the actual commands

A scratch transcript of what cutover looks like, assuming `freeze + import all`:

```sh
# In a worktree, on a branch off master:
git worktree add /tmp/djc-cutover -b docs-cutover origin/master
cd /tmp/djc-cutover

# Pull gh-pages into a sibling worktree
git worktree add /tmp/djc-ghpages-import origin/gh-pages

# Mirror the tree, omitting the symlink (we materialize it next)
mkdir -p docs/v
rsync -a --exclude=latest /tmp/djc-ghpages-import/ docs/v/

# Materialize latest/ as redirects (Python script — ~50 LOC, lifted from mike/templates/redirect.html)
python scripts/materialize_redirects.py docs/v/0.150.0 docs/v/latest

# Validate
python -m docs_site.management.docs_build_check  # the spike-11.7 gate

# Cleanup gh-pages worktree
git worktree remove /tmp/djc-ghpages-import

# Stage + commit
cd docs/v
git add .
cd ../..
git commit -m "Import historical docs versions from gh-pages into master/docs/v/

One-time cutover commit per DESIGN_djc_docs_site_spike_11_8.md.
Freezes 56 release versions (0.92 - 0.150.0) and dev/.
latest/ symlink replaced with redirect HTML.
"

# Final: switch Pages source to master/docs/v/ (GitHub repo setting, not code)
```

**Estimated time:** ~30 min for the commands (most of it is the rsync and `docs-build-check` run). Plus a PR review.

---

## 8. Risks & open items

### 8.1 Risks at execution

1. **Master clone size jumps.** Today: 108 MB `.git`. After import: ~220 MB. Fresh contributors see a slower initial clone. Mitigations:
    - `git clone --depth 1` works fine and skips history; size ~50 MB.
    - `git clone --filter=tree:0` (partial clone) works for tooling that doesn't need history.
    - Document the size in the CONTRIBUTING guide. New contributors shouldn't be surprised.

2. **Old Material JS bundles are not auditable for CVEs.** Frozen versions ship whatever Material+plugins shipped at the time. Mitigation: a Phase 7+ scan (`npm audit`-style equivalent for the bundled JS in each `docs/v/<version>/assets/`) can identify any version that needs a re-render *specifically* to update bundled JS. Probably best handled as a separate one-time sweep, not a recurring concern.

3. **The org-rename sitemap entries in pre-0.139 versions** point at `emilstenstrom.github.io`. GitHub still redirects, but a paranoid SEO audit might prefer fresh `sitemap.xml` files. Cheapest mitigation: don't advertise old sitemaps in `robots.txt` (we already don't — `robots.txt` only points at `latest/sitemap.xml`).

4. **The `dev/` deploy on the new system.** Today `dev/` is rewritten on every master push. After cutover, the new builder's `docs-build` writes `docs/v/dev/` — which means **every master push creates a commit in `master/docs/v/dev/`** with the new HTML output. That's a lot of churn in git. Mitigations:
    - Use `docs-build --version=dev --no-commit` and have CI push only the dev dir as a separate orphaned commit.
    - Or: don't commit `dev/` at all; build and deploy it directly without writing to git. (Diverges from "single source = master" property but only for `dev`, which is ephemeral anyway.)
    - **Spike-level decision: defer.** The dev-deploy flow is small enough to revisit when wiring the CI workflow.

### 8.2 Open items deferred

- **Sitemap strategy post-cutover.** The freeze keeps old sitemaps in place, advertising old URLs. Likely fine; do a search-engine recrawl sanity check during Phase 6. (Trivial to also write a unified `sitemap-index.xml` at root that just aggregates `latest/sitemap.xml` if we want.)
- **Whether to remove the `gh-pages` branch after Phase 6.** Recommendation: keep it for ~3-6 months as a recovery option, then delete. Tracked as a post-cutover follow-up.
- **Selective rebuild policy** post-Phase-7 — covered in §5.2.

---

## 9. The "what changes the answer" table

Decision is deferred per [§11.7 spike §7](DESIGN_djc_docs_site_spike_11_7.md); this table captures the data that would push us off the default recommendation.

| If we discover... | Then... |
|---|---|
| Master clone size grows much more than ~150 MB (bad deltification, e.g. because rsync didn't preserve mode bits and every blob is unique) | Reconsider — either use `git lfs` for `docs/v/`, or keep `gh-pages` alive as the archive and only put new versions on master |
| Inbound traffic to pre-0.124 versions is non-trivial (e.g. >1% of all docs traffic per Phase 7 analytics) | Add a Phase 7+ task to rewrite the affected old pages' meta-refresh to point at the *closest* modern page (manual curation) |
| Old Material JS bundles have known critical CVEs | Sweep-rebuild affected versions specifically. Walker supports this without code change |
| Pre-Phase-6 markdown directives in some 0.148+ versions don't survive the new builder | Either pin those versions to "freeze" individually (per-version `freeze=true` in `docs_versions.toml`) or skip rebuild for them |
| GitHub Pages stops supporting redirects-from-flat-HTML | Switch `latest/` materialization mode to `copy` (mike supports it; small disk cost increase) |

---

## 10. Recommended next move

**None for now.** This spike's contribution is the inventory + the data behind the recommendation. The actual execution lands at Phase 6 (the cutover PR), which is weeks of project work away.

What we get to **today**:

- Update [main doc §11.8](DESIGN_djc_docs_site.md) status to "complete; deferred to Phase 6/7+ per spike."
- Pre-bake the migration approach (`freeze + import all`) as the default so the Phase 6 PR doesn't have to relitigate it from scratch.
- Confirm to ourselves that the bloat fear was a working-tree artifact, not a real `.git` cost.

---

## 11. Open items deferred to other spikes / phases

- [Phase 6 PR] Execute the import (§7 commands).
- [Phase 7+] Selective rebuild of recent versions if analytics or maintenance argues for it (§5.2).
- [§11.10 spike] `docs-build-check` extended with cross-version validation rules (per [§11.7 spike §11](DESIGN_djc_docs_site_spike_11_7.md)).
