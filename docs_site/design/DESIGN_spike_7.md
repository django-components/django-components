# Spike 11.7 — mike internals + bootstrap-from-tags script

**Status:** spike complete
**Date:** 2026-05-31
**Feeds back into:** [DESIGN_djc_docs_site.md §4.6](DESIGN_djc_docs_site.md) (Versioning)
**Spike question:**
- (a) Can we reuse any of `mike`'s internals (manifest schema, version-picker JS, alias resolution) even though we're persisting versions to `master` rather than `gh-pages`? Did Juro's earlier outreach to the `mike` author get a response?
- (b) Implementing the `docs-build-all` bootstrap command (§4.6): walk `git tag`, check each out in a worktree, run `docs-build` per tag.

---

## 0. TL;DR verdict

**GO.** We have a clear path:

1. **Juro's outreach got a reply.** `jimporter/mike#255` on 2026-01-25 → jimporter responded 2026-01-26. He's "thinking about" a standalone mike but has nothing concrete. He calls the current gh-pages-branch design "a hack" born of 2016 GitHub Pages constraints. Bottom line: no upstream library coming; we extract what we want.

2. **Three pieces of `mike` are worth lifting verbatim:**
    - **`mike/versions.py` (209 LOC)** — the `Versions` and `VersionInfo` classes. Pure Python, no git, no mkdocs. Models exactly our `docs/v/versions.json`. Verified working against our 127 tags in §2.
    - **`mike/themes/*/js/version-select.js` (~50 LOC)** — the algorithm for "read manifest, rewrite URL, swap version." Use as reference for the Django component's JS; not a drop-in (Material has its own selector that mike doesn't replace).
    - **`mike/templates/redirect.html` (15 LOC)** — for aliases like `latest/` that redirect rather than mirror.
   Total reuse: ~270 LOC, all dep-free.

3. **Five pieces of `mike` we replace or skip:**
    - `git_utils.py` (431 LOC) — gh-pages branch plumbing. Skip entirely; we commit to `master`.
    - `mkdocs_utils.py` (139 LOC) and `mkdocs_plugin.py` (80 LOC) — mkdocs adapters. Replaced by our Django components.
    - `commands.py` (322 LOC) — the deploy/delete/alias/list CLI. Useful as a *structural reference* (the contract: read manifest → mutate → write manifest + files → commit) but we rewrite for our two-command model.
    - `jsonpath.py` (146 LOC) — implements `mike props` for arbitrary version-level metadata. We don't need this; if we ever do, lift it then.

4. **`docs-build-all` is a thin shell.** It's `for tag in matched_tags: git worktree add <path> <tag> && uv run --project <path> docs-build && git worktree remove <path>` plus a final manifest-merge step. No new git logic, no new build logic — just orchestration. The hard part is the per-tag idempotency check (don't rebuild `docs/v/0.148/` if it exists and is up to date), which is just a hash/timestamp comparison.

**Biggest risks** to manage during execution:
1. **The `0.139` → `0.139.1` style mixed 2-part/3-part tags.** `verspec.LooseVersion` handles this correctly (verified §2), but downstream URL templating must canonicalize before lookup ("am I `0.139.1` or `0.139`?" is ambiguous if normalized naively).
2. **Aliases must be writable as either symlink, copy, or redirect.** mike supports all three; we should default to **redirect** (smallest disk, plays nicely with `master`-as-deploy-source; symlinks confuse some Windows checkouts and bloat git status).
3. **Older mkdocs-built versions on `gh-pages` (40+ dirs from `0.102` onward) — defer the migration decision until after Phase 7.** The pragmatic call (per Juro): we don't know the final shape of the contract until the new builder has gone through Phase 1-7 end-to-end (scaffold → cutover → search v2). Trying to settle the policy now is premature optimization. The bootstrap walker (§3.2) supports all three migration options (rebuild / freeze / hybrid), so we keep the door open without committing. §11.8 of the main doc captures this deferral.

**Recommended first move:** vendor `mike/versions.py` as `docs_site/apps/docs/_vendor/mike_versions.py` (with attribution), wire `docs-build` (single-version) to write `docs/v/<version>/` and update `docs/v/versions.json` via that class, and prove the round-trip on a scratch branch with three real tags (`0.148.0`, `0.149.0`, `0.150.0`). ~1 day of work. Validates the contract before any `docs-build-all` orchestration.

---

## 1. Juro's outreach to the mike author — verbatim

**[`jimporter/mike` discussion #255 — "mike without mkdocs?"](https://github.com/jimporter/mike/discussions/255)**

> **@JuroOravec, 2026-01-25:**
> Hi, are you thinking of refactoring mike to work also standalone, without mkdocs? Or is there maybe a similar library that does that?

> **@jimporter, 2026-01-26:**
> I am actually thinking about doing this, but nothing definite just yet. I've debated just how useful it would be to have a tool that only stores multiple versions of generated docs in a Git branch, or whether there's a better way to handle this these days. At the time I made this, it was built around the way Github Pages worked at the time, but with the various updates over the years, it's seemed more and more like a hack.
>
> Fundamentally, I consider generated documentation to be a release artifact just like a tarball or a binary executable, and neither of those really belong in your Git repo. However, unlike those cases, multi-version documentation benefits from being able to cross-link to all the versions (via a version selector). This puts documentation in a weird middle ground where some coordination across versions is necessary, and which mike currently relies on Git for.

**What this means for us:**

- **No standalone mike is coming soon.** "Thinking about" is not "in flight." Plan on vendoring.
- **jimporter independently arrived at our concern.** The gh-pages branch is a 2016 hack that has aged badly. The author admits it. Persisting under `docs/v/` on `master` is the saner shape.
- **The one concern jimporter raises against committing generated docs to source — that they're "release artifacts" — we're rejecting deliberately.** Juro's [§4.6 rationale](DESIGN_djc_docs_site.md#46-versioning) is that rebuilding every historical version on every CI run is `O(N versions × build time)` and gets prohibitively slow. Committing the artifact once and reusing it is a deliberate trade against "purity."
- **No standalone library exists either.** We searched; the closest is `mike` itself.

---

## 2. mike's source — what each file does, what we lift

`mike` is small: 12 modules, 1921 LOC total. Inspected via a shallow clone of [`jimporter/mike`](https://github.com/jimporter/mike) at `master`.

| Module | LOC | Purpose | Verdict |
|---|---|---|---|
| `versions.py` | 209 | `Versions` collection, `VersionInfo` model, JSON round-trip, `LooseVersion`-based sort, alias coalescing | **Vendor as-is** |
| `templates/redirect.html` | 15 | `<meta refresh>` + JS `window.location.replace` for alias redirects | **Vendor as-is** |
| `themes/*/js/version-select.js` | ~50 each (mkdocs, readthedocs) | Read `../versions.json`, render `<select>`, redirect on change | **Lift the algorithm**, rewrite for our DOM |
| `jsonpath.py` | 146 | Limited JSONPath used by `mike props get/set` | **Skip** unless we want arbitrary per-version metadata later |
| `commands.py` | 322 | `deploy`/`delete`/`alias`/`set-default`/`list` orchestration | **Reference only.** The deploy contract is informative; the gh-pages coupling makes it not portable |
| `git_utils.py` | 431 | gh-pages branch plumbing: `Commit` context manager, file walking, symlink mode (0o120000), worktree tracking | **Skip entirely.** Our model is "commit to master with `git add docs/v/<version>/`" — Python doesn't need to know git |
| `mkdocs_plugin.py` | 80 | mkdocs `BasePlugin` that injects version-select.js + sets `site_url` per version | **Skip.** Replaced by Django component |
| `mkdocs_utils.py` | 139 | mkdocs config inspection used by `commands.py` | **Skip.** Replaced by our own settings |
| `driver.py` | 480 | CLI argument parsing + `argparse` glue | **Skip.** Replaced by `[project.scripts]` entries |
| `arguments.py` | 42 | Reusable argparse pieces | **Skip** |
| `server.py` | 71 | `mike serve` local preview | **Skip.** Our `uv run docs-serve` is the Django dev server |
| `app_version.py` | 1 | mike's own version constant | **Skip** |

**Reuse total:** ~270 LOC across `versions.py` (209) + `redirect.html` (15) + version-select.js (~50, rewritten). Everything else we walk past.

### 2.1 The `Versions` class — what we get for free

`mike/versions.py` is a self-contained data model. From [versions.py:88-209](https://github.com/jimporter/mike/blob/master/mike/versions.py#L88):

```python
class Versions:
    def __init__(self): self._data = {}

    @classmethod
    def from_json(cls, data): ...       # parse versions.json
    def to_json(self): ...              # serialize to list-of-dicts
    @classmethod
    def loads(cls, data): ...           # str -> Versions
    def dumps(self): ...                # Versions -> str (pretty-printed)
    def __iter__(self): ...             # iterate newest-first (incl. "dev" sentinel)
    def add(self, version, title=None, aliases=[], update_aliases=False): ...
    def update(self, identifier, ...): ...
    def remove(self, identifier): ...
    def difference_update(self, identifiers): ...
```

Dependencies: only [`verspec.loose.LooseVersion`](https://pypi.org/project/verspec/) (which mkdocs ships transitively today). We add `verspec` as an explicit dep when we drop mkdocs and forget about it.

### 2.2 Probe: does it actually handle our tag set?

Ran against representative tags from our 127:

```python
from mike.versions import Versions
v = Versions()
for tag in ['0.124', '0.139', '0.139.1', '0.140.0', '0.141.6', '0.142.0', '0.150.0', '0.102', '0.110', 'dev']:
    v.add(tag, aliases=['latest'] if tag == '0.150.0' else [])

# Iteration order (newest first):
# dev
# 0.150.0  aliases={latest}
# 0.142.0
# 0.141.6
# 0.140.0
# 0.139.1
# 0.139      <-- 2-part sorts below the 3-part 0.139.1, correct
# 0.124
# 0.110
# 0.102
```

The `__iter__` key (versions.py:113-117) treats anything not starting with `\d` as "newer than release" — that's how `dev` floats to the top. We can hijack this for any sentinel we want (`main`, `next`, `unreleased`).

### 2.3 The version-select algorithm — reference, not drop-in

[`mike/themes/mkdocs/js/version-select.js`](https://github.com/jimporter/mike/blob/master/mike/themes/mkdocs/js/version-select.js) is ~50 lines. The core algorithm:

```js
// 1. Compute current version from URL: /.../<version>/<page>
// 2. Fetch ../versions.json (one level up = the manifest)
// 3. Find current version row (by .version OR by .aliases.includes(...))
// 4. Build <select> from all rows (hide ones with properties.hidden)
// 5. On change: window.location.href = ABS_BASE_URL + "../" + value + "/"
```

That's it. Our Django `version_picker` component lifts the algorithm. **Note:** today on `gh-pages` the `0.150.0/js/version-select.js` does NOT exist — Material's `version: provider: mike` integration writes its own selector. So we are replacing Material's selector with our own; we are *not* using mike's JS verbatim. We lift only the algorithm.

### 2.4 Aliases — three mike modes; we pick `redirect`

mike supports three ways to materialize an alias like `latest/` → `0.150.0/`:

| Mode | How | Pros | Cons |
|---|---|---|---|
| `symlink` | Git mode-`120000` symlink blob | Smallest on disk | Confuses Windows checkouts; bloats `git status`; some hosts refuse |
| `copy` | Mirror every file under `latest/` | Universally serves | Doubles disk per alias |
| `redirect` | One HTML file per file with `<meta refresh>` + JS | Tiny on disk; cross-platform | Two requests per visit (initial + redirect) |

**Today on `gh-pages` we use `symlink`** (verified: `latest/` is a mode-120000 blob pointing to `0.150.0`). That works on `gh-pages` because GitHub Pages serves the symlinked content directly.

**Recommendation: switch to `redirect`.** Reasons:
- We're committing the docs site to `master`. Symlinks in `master` are a footgun — Windows clones may see broken files, and "what is `latest/` pointing at?" becomes a git-mode-bit question rather than a docs question.
- The redirect is a tiny HTML file (15 lines, mike's [`templates/redirect.html`](https://github.com/jimporter/mike/blob/master/mike/templates/redirect.html)). One per page-in-`latest/`. Compresses to almost nothing.
- GitHub Pages serves it correctly without any config.

Cost: an extra HTTP request on `latest/whatever` URLs. Negligible.

If disk size becomes a concern later, we add a `copy` mode as an option. Cheap to add then.

---

## 3. The two-command design — concretized

[§4.6](DESIGN_djc_docs_site.md#46-versioning) introduces `docs-build` (single version) and `docs-build-all` (bootstrap). The shapes:

### 3.1 `uv run docs-build` — everyday command

```
$ uv run docs-build [--version=<v>] [--alias=<a>...] [--no-manifest-update]
```

Algorithm:

1. Determine target version. Default: read `version` from [`pyproject.toml`](pyproject.toml). Override via `--version` for previews / dev builds (e.g. `--version=dev`).
2. Determine target directory: `docs/v/<version>/`.
3. Run the existing in-memory build pipeline (Django runserver crawl from §4.7) with `BASE_URL` set to `/v/<version>/`. Write outputs to `docs/v/<version>/`.
4. Load existing `docs/v/versions.json` (or empty if absent) via vendored `Versions`.
5. `versions.add(version, title=..., aliases=[...], update_aliases=True)`.
6. If `--alias=latest` (default for tagged releases), materialize redirect files under `docs/v/latest/`.
7. Write `docs/v/versions.json`.
8. **Stop.** Do not commit. The CI workflow stages and commits.

CI flow (replacement for [`release-docs.yml`](.github/workflows/release-docs.yml)):

```yaml
- run: uv run docs-build --alias=latest
- run: |
    git add docs/v/
    git commit -m "Deploy docs ${REF_NAME}"
    git push origin master
```

Notice what's gone: no `git checkout gh-pages`, no `--update-aliases` flag dance, no `mike set-default`. The pipeline is "build, stage, commit, push." That's it.

### 3.2 `uv run docs-build-all` — bootstrap / disaster recovery

```
$ uv run docs-build-all [--config=docs_versions.toml]
```

Algorithm:

1. Read `docs_versions.toml`:
    ```toml
    [versions]
    pattern = "^v?\\d+\\.\\d+(\\.\\d+)?$"
    include = ["dev"]         # extra sentinels not matched by the regex
    exclude = ["0.102", "0.110"]  # broken / deleted historical tags
    oldest = "0.135"          # don't go below this
    newest = null             # null = no upper bound

    [aliases]
    latest = "0.150.0"        # explicit override; usually derived from newest tag
    ```
2. Enumerate `git tag` matching `pattern`, apply `include`/`exclude`/`oldest`/`newest`.
3. For each tag (newest first, so manifest is incrementally consistent):
    a. **Idempotency check:** if `docs/v/<version>/` exists AND its `_build_info.json` records the same source-tree SHA as the tag, skip.
    b. `git worktree add --detach <tmp> <tag>`.
    c. Run `uv run --project <tmp> docs-build --version=<version> --no-manifest-update` from inside the worktree (writes to `<repo>/docs/v/<version>/` directly).
    d. Write a per-version stamp file `docs/v/<version>/_build_info.json` capturing `{tag, source_sha, built_at, builder_version}`.
    e. `git worktree remove <tmp>`.
4. **Single manifest rewrite** at the end: collect all `docs/v/*/` dirs, build a fresh `Versions`, write `docs/v/versions.json`. This is the only step where the manifest is touched in `docs-build-all` mode.

Why a single rewrite at the end? If steps 3a–3e fail midway, we want the manifest to either reflect the previous successful state OR the new complete state — never a half-state where one row is missing.

### 3.3 The `_build_info.json` stamp file — why it exists

Without a stamp, `docs-build-all` can't know whether `docs/v/0.148/` is from a real `0.148.0` checkout or from a broken half-build that someone committed. The stamp solves that:

```json
{
    "version": "0.148.0",
    "source_sha": "abc123...",
    "source_tag": "0.148.0",
    "built_at": "2026-06-01T12:34:56Z",
    "builder_version": "1.0.0"
}
```

The idempotency check in step 3a compares `stamp.source_sha` against `git rev-parse <tag>^{commit}`. Mismatch → rebuild.

Stamp also documents *which* builder built each version, so when we change the builder we can selectively re-flow old versions (`docs-build-all --rebuild-if-builder-older-than=2.0.0`).

### 3.4 Cost & timing

Per-version build with Django startup + crawl is estimated at 60–120s ([§7 item 6 in main doc](DESIGN_djc_docs_site.md#7-open-questions-to-resolve-before-starting)). With ~40 historical versions to bootstrap, `docs-build-all` is a 40 × ~90s = ~1 hour run. **One time.** Afterward, every release is a single `docs-build` (~90s) + commit + push.

By contrast, "rebuild every version on every release" (the rejected design) would be 1 hour per release.

---

## 4. The `docs/v/versions.json` schema

Lifted verbatim from mike (because we vendor `Versions`):

```json
[
    {"version": "dev", "title": "dev (946395b)", "aliases": []},
    {"version": "0.150.0", "title": "0.150.0", "aliases": ["latest"]},
    {"version": "0.149.0", "title": "0.149.0", "aliases": []},
    {"version": "0.148.0", "title": "0.148.0", "aliases": []}
]
```

The `properties` field (mike's extension point) is omitted by default but the schema supports it:

```json
{"version": "0.150.0", "title": "0.150.0", "aliases": ["latest"], "properties": {"hidden": false, "stability": "stable"}}
```

We'd use `properties.hidden=true` to keep an entry in the manifest (so URLs don't break) but exclude it from the picker. Useful for unreleased dev preview builds.

### 4.1 Schema-compatibility with `mike`

Important property: **our manifest is byte-identical to what mike writes**. That means:
- The Material-for-mkdocs version selector reads it correctly (during the transition window if we keep mkdocs running alongside).
- Any external tool that consumes versions.json (release dashboards, etc.) keeps working.
- We can run `docs-build-all` against the *existing* `gh-pages` manifest to recover state.

### 4.2 What we add: a `current` field

The original mike format doesn't surface "what's the version of the most-recent stable?" — it's inferred from `aliases.includes("latest")`. We can either keep that inference (cheaper) or add an explicit `current` key. Recommendation: keep the inference; one less thing to keep in sync.

---

## 5. The version picker — a Django component sketch

`docs_site/apps/docs/components/version_picker/`:

```python
# component.py
class VersionPicker(Component):
    template = "version_picker.html"

    class Kwargs(NamedTuple):
        current_version: str          # the version the rendered page belongs to
        manifest_url: str = "/docs/v/versions.json"

    def get_template_data(self, args, kwargs, slots, context):
        return {"current": kwargs.current_version, "manifest_url": kwargs.manifest_url}

    # The component's JS reads the manifest at runtime — see Media.js below.
    class Media:
        js = "version_picker.js"
        css = "version_picker.css"
```

```html
<!-- version_picker.html -->
<div class="version-picker" data-version-picker
     data-current="{{ current }}"
     data-manifest="{{ manifest_url }}">
    <select aria-label="Choose docs version">
        <option value="{{ current }}">{{ current }}</option>
    </select>
</div>
```

```js
// version_picker.js — lifted from mike, simplified
document.querySelectorAll("[data-version-picker]").forEach(async (el) => {
    const current = el.dataset.current;
    const manifest = await fetch(el.dataset.manifest).then(r => r.json());
    const select = el.querySelector("select");
    select.innerHTML = "";
    for (const row of manifest) {
        if (row.properties?.hidden && row.version !== current) continue;
        const opt = new Option(row.title, row.version, false, row.version === current);
        select.add(opt);
    }
    select.addEventListener("change", () => {
        // Same logic as mike: redirect to ../<value>/ relative to current page
        const base = window.location.pathname.replace(/\/v\/[^/]+\/.*$/, "/v/");
        window.location.href = base + select.value + "/";
    });
});
```

Total: ~30 lines of JS, no framework dependency.

---

## 6. `docs-build` integration with the rest of the pipeline

`docs-build` is the unit cell. Everything else composes from it.

| Caller | Trigger | Args | Outcome |
|---|---|---|---|
| `release-docs.yml` (CI) on tag push | Push of `v?\d+.\d+.\d+` | `--alias=latest` | `docs/v/<version>/` populated, manifest updated, commit + push to master |
| `release-docs.yml` (CI) on master push | Push to master (no tag) | `--version=dev` | `docs/v/dev/` populated/refreshed, commit + push |
| Developer locally | `uv run docs-build` | (defaults to current pyproject version) | Writes `docs/v/<version>/`. Manifest update. No commit |
| `docs-build-all` | One-off | `--no-manifest-update` per call, single merge at end | Same as developer, but parameterized by `--version=<tag>` |

(**No pre-commit hook.** Per Juro: docs builds are a CI concern, not a per-commit one. Local devs run `uv run docs-serve` for live preview; they don't need a hook that re-renders the static output on every commit.)

This is a clean composition: one core command, multiple thin wrappers.

---

## 7. Migration of the 40+ versions currently on `gh-pages` — DEFERRED to after Phase 7

**Decision (per Juro):** **defer.** We don't pick a migration policy in this spike. We pick it once the new builder is end-to-end alive — through Phase 1 (scaffold) → Phase 2-4 (content) → Phase 5a-d (theming, versioning, search, parity audit) → Phase 6 (cutover) → Phase 7 (search v2). At that point we *know* the final contract: what `{% example %}` and `{% docstring %}` actually expect, how rigorous the directive set is, whether old markdown stays compatible. Trying to settle it now is premature optimization.

**Why deferral works:** the bootstrap walker (§3.2) is option-agnostic. We can pick any of the three approaches below, post-Phase-7, *with no code changes to the walker*:

1. **Rebuild all 40+ with the new builder.** `docs-build-all` walks every tag from `0.102` to `0.150.0`. ~1 hour, one time. Requires old markdown to be compatible with the new directives.
2. **Bring the existing `gh-pages` HTML into `master` as-is.** One commit that copies `gh-pages` subdirs into `docs/v/`. Preserves every URL byte-for-byte. Loses re-buildability of old versions, which is fine — we don't need to rebuild them.
3. **Hybrid.** Option 2 below a chosen threshold (e.g. `< 0.145`), option 1 at/above. The threshold is the line below which we don't promise re-buildability.

The choice depends on data we don't have until Phase 7 wraps:
- How many old docstrings would actually fail the new griffe-based rendering? (Spike 11.5 has the inventory but not the failure rate.)
- Do users still hit old `latest/` URLs we need to honor? (Phase 7 search analytics, if enabled, would tell us.)
- Are there CVE-class issues in the old mkdocs-built HTML (XSS / dependency vulns baked in) that argue for a forced rebuild? (Unknown today.)

**What we DO commit to now**, in this spike: the walker handles all three options without code change. The TOML config sketch is the gate where the choice lands:

```toml
# Deferred. Filled in after Phase 7, not before.
[versions]
oldest_to_rebuild = ???      # "0.145" for hybrid; "0.102" for full rebuild; null for freeze-all
freeze_below_threshold = ??? # true for hybrid/freeze; false for full rebuild
```

**Why this is safe to defer:** until cutover (Phase 6), the old mkdocs site on `gh-pages` is still canonical. The new `docs/v/` on `master` is being filled with new releases (Phase 5b onward), but it doesn't have to contain history yet. At cutover (Phase 6) we point GitHub Pages at `master/docs/v/`. At that point we either (a) have history already in `docs/v/` because we ran `docs-build-all`, or (b) keep serving older versions from a frozen `gh-pages` subtree (DNS / Pages config trick — minor wrinkle, but workable). Either way, Phase 6 doesn't depend on the migration policy being final.

---

## 8. Risks & open items

### 8.1 Risks during execution

1. **`verspec.LooseVersion` semantics on edge tags.** Validated against `0.124`, `0.139`, `0.139.1`, `0.140.0`, etc. (§2.2). One thing not validated: pre-release tags like `0.150.0rc1` if we ever cut one. mike treats these correctly per LooseVersion rules; we'd want a test before introducing the convention.

2. **Symlink → redirect alias migration on first deploy.** The first time `docs-build` runs on master, there's no `docs/v/`. The first run creates everything fresh — no migration needed at that step. The migration is the one-time `gh-pages` → `master/docs/v/` move (handled by §7).

3. **`docs-build-all` worktree cleanup on failure.** If the per-tag build crashes, the worktree dangles. We must `git worktree prune` defensively at the start of each run, and use `try/finally` to remove on error. Tested pattern; not exotic.

4. **The `dev` sentinel.** mike's `__iter__` treats anything not starting with `\d` as "newer than release," so `dev` correctly floats to the top of the manifest. Verified (§2.2). If we add other sentinels (`main`, `next`, `staging`) they all get this treatment, which is fine but worth documenting so contributors don't accidentally make a "release" called `feature-x` and have it pin to top.

5. **The Pygments security pin pressure (§1 of the main doc) interacts here.** Once we drop mkdocs, the version-build step uses our own Pygments. But `docs-build-all` rebuilding old versions would also use our new Pygments — meaning old docs would be rendered with the new lexer. That's a feature (security) not a bug, but we should verify no historical doc relied on a Pygments quirk.

### 8.2 Items deferred to other spikes

- **Older-version migration policy** — §11.8.
- **Per-page redirect from old URLs** (e.g. when a doc moves between versions) — §7 item 5 of the main doc.
- **CI workflow rewrite** — comes after the spike validation; trivial port from current [`release-docs.yml`](.github/workflows/release-docs.yml).
- **Material's `provider: mike` integration removal** — happens at cutover (§6 of the main doc).

### 8.3 Items deferred to implementation

- **Where to put the vendored `Versions` class.** Suggested: `docs_site/apps/docs/_vendor/mike_versions.py` with a NOTICE block citing `jimporter/mike` and the [BSD-3-Clause license](https://github.com/jimporter/mike/blob/master/LICENSE). Same pattern as we use elsewhere.
- **`docs_versions.toml` location** — ~~top-level repo, sibling of `pyproject.toml`~~. **Resolved in implementation:** lives at the **docs-project root, `docs_site/docs_versions.toml`** (sibling of `manage.py`), keeping the docs project self-contained. Read via `settings.VERSIONS_CONFIG`.

---

## 9. Recommended first concrete step

**~1 day of work.** Validates the contract end-to-end on a scratch branch with three real tags.

1. Create `docs_site/apps/docs/_vendor/mike_versions.py` — paste `mike/versions.py` (209 LOC) with attribution header. Add `verspec` to docs deps.
2. Write `docs_site/apps/docs/management/commands/docs_build.py` — the single-version build. For now, it can do anything trivial (e.g. `Hello, version=<v>` index.html) — what matters is the directory writing + manifest update.
3. On a scratch branch:
    ```
    uv run docs-build --version=0.148.0
    uv run docs-build --version=0.149.0
    uv run docs-build --version=0.150.0 --alias=latest
    ```
4. Inspect `docs/v/`:
    - `0.148.0/index.html`, `0.149.0/index.html`, `0.150.0/index.html` present.
    - `latest/index.html` is a redirect to `0.150.0/`.
    - `versions.json` has 3 entries with the right aliases.
5. Open in browser via `python -m http.server`. Verify the version picker (also built in step 2, ~30 lines of JS) reads the manifest and switches between versions.

If steps 1–5 work, the rest of §11.7 is execution. If something falls over — most likely in the redirect-alias materialization or the manifest round-trip — we catch the design issue before sinking weeks into `docs-build-all` orchestration.

---

## 10. Where the code lives

```
docs_site/
    apps/docs/
        _vendor/
            mike_versions.py          # 209 LOC, vendored as-is, BSD-3-Clause attribution
            mike_redirect.html        # 15 LOC, vendored
        components/
            version_picker/
                component.py
                version_picker.html
                version_picker.js     # ~30 LOC, lifted algorithm
                version_picker.css
        management/
            commands/
                docs_build.py         # the single-version build
                docs_build_all.py     # the bootstrap walker
                docs_build_check.py   # CI gate: validates docs/v/ vs manifest
docs_versions.toml                    # top-level
docs/v/                               # the deploy target
    versions.json
    latest/                           # redirects only
    0.150.0/
    0.149.0/
    ...
```

---

## 11. `docs-build-check` — the CI gate

Confirmed in scope for this work (per Juro). `docs-build-check` is the inverse of `docs-build`: it validates that `docs/v/` is internally consistent without rebuilding anything. Runs in CI on every PR that touches `docs/v/` or `docs_versions.toml`, and on every release deploy as a post-commit verification.

**Scope (what it checks):**

1. **Manifest ↔ filesystem.** Every entry in `docs/v/versions.json` has a corresponding `docs/v/<version>/index.html`. Every `docs/v/<version>/` directory has an entry in the manifest. No orphans either way.
2. **Aliases resolve.** Every `aliases: ["latest"]` in the manifest has a `docs/v/latest/` that actually redirects to the named version (in redirect mode: assert the `<meta refresh>` href; in copy mode: assert the index byte-compares; in symlink mode: assert the target).
3. **`_build_info.json` is sane.** Every `docs/v/<version>/_build_info.json` parses, has the required fields, and its `source_sha` matches a real commit. (Doesn't validate the SHA is *the right* commit — that's `docs-build-all`'s problem — only that it's valid git.)
4. **Internal links resolve, across versions.** Walk every generated `.html` in `docs/v/`, parse `<a href>`, assert every internal link (within the same version subtree) resolves to an existing file. Cross-version links are flagged but allowed (the version picker creates them legitimately).
5. **No version dir is half-built.** A `docs/v/<version>/` without an `index.html` or without a `_build_info.json` fails the check. Catches the case where someone interrupted `docs-build-all` mid-tag and committed the partial output.

**Where it runs:**

- **CI gate** on PRs that touch `docs/v/**` or `docs_versions.toml`: fails the PR if any check above fails.
- **CI gate** on the release-deploy workflow, after `docs-build` completes and before `git push`: catches the case where `docs-build` produced an inconsistent state (shouldn't happen, but the guard costs nothing).
- **Local** as `uv run docs-build-check` for devs who want to verify their state.

**Out of scope (intentionally):**

- Content correctness (broken markdown, missing component, etc.) — that's `docs-build`'s job.
- Cross-version content drift (does the v0.150 API page differ unreasonably from v0.149's?) — diff-style policing belongs to `docs-build-all`, not the check command.
- Search index validity — Pagefind has its own validation in Phase 5c.

**Estimated effort:** ~150-200 LOC of Python; one day to implement, half a day to wire into the GitHub Actions workflow. Lands at the same time as `docs-build-all` (since both share the directory-traversal logic).

This is the natural pair to the §11.10 guardrail spike (which is the broader CI-gates story); calling it out here because the existence of `docs-build` and `docs-build-all` *creates* the surface that needs guarding.

---

## 12. License audit — all upstream deps we touch

Juro asked: now that we know `mike` is BSD-3-Clause, what other non-MIT licenses do we pick up across the spike work? Audit run against PyPI metadata and source LICENSE files.

| Package | License | Used by | Vendored or imported? | Attribution required? |
|---|---|---|---|---|
| `mike` (subset) | **BSD-3-Clause** | §11.7 (this spike) | **Vendored** `versions.py` + `redirect.html` | **Yes** — preserve copyright + license text in `_vendor/` |
| `griffe` | **ISC** | §11.5 (API ref) | Imported | Yes (auto via dep) |
| `verspec` | **BSD-2-Clause OR Apache-2.0** (dual) | §11.7 (via `mike/versions.py`) | Imported | Yes (auto via dep) |
| `markdown` (python-markdown) | **BSD-3-Clause** | §11.4 (content pipeline) | Imported | Yes (auto via dep) |
| `pymdown-extensions` | MIT | §11.4 | Imported | Standard MIT |
| `pygments` | **BSD-2-Clause** | §11.4 (syntax highlighting) | Imported | Yes (auto via dep) |
| `pygments_djc` | (we own) | §11.4 | Imported | N/A — we own it |
| `python-frontmatter` | MIT | §11.4 (YAML page metadata) | Imported | Standard MIT |
| `jinja2` | **BSD-3-Clause** | Transitive | Imported | Yes (auto via dep) |
| `pyyaml` | MIT | Transitive | Imported | Standard MIT |
| `pillow` | **MIT-CMU (HPND variant)** | §5b (social cards / OG images) | Imported | Yes — HPND wording, very close to MIT |
| `Pagefind` | MIT | §11.1 / §5c (search) | External CLI tool, output bundled | Standard MIT |
| `mkdocs-redirects`, `mkdocs-include-markdown`, `mkdocs-macros-plugin` | MIT | Currently used; replaced | (dropped at cutover) | N/A |
| `gitpython` | **BSD-3-Clause** | Only if we use it in `docs-build-all`; subprocess `git` is preferred | Maybe imported | Yes if used |

**The whole stack is permissive.** No copyleft (GPL/LGPL/AGPL), no source-available licenses, no proprietary terms.

**Non-MIT items**, all OSI-approved and identical in practical effect for our use case:

- **BSD-2-Clause** — pygments, half of verspec. Identical to MIT for redistribution purposes.
- **BSD-3-Clause** — mike, python-markdown, jinja2, gitpython. Adds a "no endorsement" clause (can't use the author's name to promote derived work). Doesn't constrain us.
- **ISC** — griffe. Same content as 2-clause BSD with different wording.
- **Apache-2.0** — half of verspec (we're free to pick BSD-2-Clause if Apache patent terms ever became an issue; not relevant today).
- **MIT-CMU / HPND** — Pillow. Historical Python imaging license, MIT-equivalent.

**What this means in practice:**

1. **For `pip install`-ed deps, no action needed.** PyPI installs include the LICENSE file; pip-licenses-style tools can produce attribution dumps if we ever ship a binary distribution.
2. **For vendored code** (currently just `mike/versions.py` + `mike/redirect.html`), we **must** keep the upstream copyright notice and license text. Standard pattern: a top-of-file comment block citing the source and license, plus the full LICENSE text in `_vendor/LICENSE-mike.txt` or similar.
3. **For the django-components project itself.** Our own license is **MIT** (see [LICENSE](LICENSE)). Adding permissive-licensed deps doesn't change that — we keep emitting MIT in our package metadata. Vendored BSD-3-Clause code is fine inside an MIT package as long as the BSD notice is preserved (compatibility is one-way: MIT-licensed projects can ship BSD-licensed bundled code; the reverse also works).

**Audit cadence.** Recommend running a license check (`pip-licenses --format=plain` or similar) in CI on dep updates — same way we audit security advisories. Cheap insurance against accidental copyleft creep through a transitive dep update. Tracks naturally with §11.10 guardrails.

---

## 13. Open items deferred to other spikes

- §11.8 — Migration policy for the 40+ existing `gh-pages` versions. **Explicitly deferred to after Phase 7** (§7 above).
- §11.10 — Broader guardrails. `docs-build-check` (§11 above) is one of them but the full §11.10 set is wider (snapshot tests, anchor checks, etc.).
- §11.4 / §11.5 — The `docs-build` step's *content* pipeline (markdown → HTML, API ref renderer). This spike just specifies the directory-and-manifest scaffold around it.
