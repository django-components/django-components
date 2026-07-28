# Spike 11.5 — Griffe reuse + per-API-kind renderers

**Status:** spike complete
**Date:** 2026-05-31
**Feeds back into:** [DESIGN_djc_docs_site.md §4.3](DESIGN_djc_docs_site.md) (API reference) and §2.2 (discovery → rendering split)
**Spike question:** Validate that griffe alone (without mkdocstrings) can give us every machine-readable fact our docs need, then enumerate every API "kind" we render today and design the per-kind Django component set.

---

## 0. TL;DR verdict

**GO.** Griffe gives us every machine-readable fact we need across all 21 distinct API renderings in [`docs/reference/`](docs/reference/). The five real gaps (cross-refs, runtime-set class attributes, argparse metadata, NamedTuple `_fields`, raw-HTML-in-docstrings) all have known mitigations costing ~50-200 LOC total. The two existing griffe extensions ([`docs/scripts/extensions.py`](docs/scripts/extensions.py)) port verbatim with a one-line config swap.

**Biggest risks** to manage during execution, in priority order:
1. **Anchor scheme change breaks 397 hand-typed markdown links** in `src/` docstrings — plus **578 more in `docs/` human-authored markdown** per the main doc §11.6.F, for ~975 total. The §7.2 plan is to drop the **entire dotted path** from anchors — `#django_components.component.Component` → `#Component` — not just the root prefix. Within a single reference page, leaf names are already unique, and the intermediate path is internal detail. Needs a codemod, not a flag flip. **Sweep policy (revised per Juro):** every hand-typed `[X](api.md#django_components.Y)` link converts to bracket cross-ref form `[X][LeafName]` (or `[X][]` when text matches the leaf name). No per-link "is this navigational vs a mention?" judgment — authors wrote them as links because they meant them as links; densely cross-linking public API mentions is a deliberate authoring style, not noise. The earlier proposal to downgrade some links to backticks is **rejected**. See §11.4.
2. **`signature_crossrefs` is load-bearing** — we have 712 auto-linked types across one page alone. Reimplementing it requires parsing griffe's `Expr` tree per parameter and looking each `ExprName` up against a merged inventory (project symbols + `objects.inv` from Python stdlib and Django).
3. **`reference.py` is 1160 lines** and inlines per-page mkdocstrings option YAML. Migration means rewriting it to produce a portable data structure that our renderer consumes — the §2.2 split.

**Terminology note.** Throughout this doc, "hand-typed" / "handwritten" links mean the full markdown form `[X](api.md#django_components.Y)` — typed verbatim by the docstring author. They contrast with mkdocstrings' bracket cross-ref form `[X][django_components.Y]`, which the resolver expands at build time. Today the project uses the hand-typed form exclusively (397 hits). Migration converts them to a resolver-friendly form (see §11).

**Recommended first move:** build a one-page proof of the discovery → renderer split for the simplest kind (Exception class), end-to-end. ~1 day of work. Validates the contract before scaling to 11 more kinds.

---

## 1. What griffe gives us (validated by running it)

All facts below verified with `griffe 1.15.0` against `src/django_components/` via probe scripts.

| Need | Reachable? | How |
|---|---|---|
| Symbol kind (`class`/`function`/`attribute`/`module`) | Yes | `obj.kind` |
| File path + line range | Yes | `obj.relative_filepath`, `obj.lineno`, `obj.endlineno` |
| Source code text | Yes | `obj.source` |
| Parameters with annotations + defaults | Yes | `griffe.Parameter` objects; annotations are structured `griffe.Expr` trees, not strings |
| Return annotation | Yes | `griffe.Expr` |
| Decorators (by name) | Yes | `obj.decorators` — list of `griffe.Expr`. Lets us filter by decorator name (e.g. `@mark_extension_hook_api`) |
| Bases | Yes | List of `griffe.Expr`. Caveat: top-level aliases report `bases = []`; must follow `obj.target` first |
| Class members | Yes | `obj.members` dict, ordered by source position |
| Per-field docstrings (NamedTuple fields) | Yes | Field-level docstrings captured correctly for `OnComponentInputContext` and similar |
| Annotation as structured object | Yes | `Expr` subtree (`ExprName`, `ExprBinOp`, `ExprSubscript`, `ExprTuple`) — pretty-printable with refs |
| Class-level literal constants | Yes | `tag = 'component'`, `end_tag = 'endcomponent'`, `allowed_flags = ExprTuple(...)` |
| Google-style docstring sections | Yes when authors used `Args:` / `Returns:` / `Raises:` headings. Markdown-bold `**Args:**` stays as one `text` section (an authoring inconsistency, not a griffe limitation) |
| Cross-package alias resolution | Yes (`alias.target` / `alias.final_target`). Raises `AliasResolutionError` for stdlib imports — wrap walks in `try/except` |

## 2. What griffe doesn't give us — and the mitigations

| Gap | Symptom | Mitigation | Effort |
|---|---|---|---|
| Cross-reference resolution in docstrings | griffe stores `[Component][django_components.Component]` as raw text | Custom resolver: regex over `text` sections of parsed docstrings, look each `[name][path]` up against the loaded `ModulesCollection`, rewrite to anchor URL | ~50 LOC |
| Inventory-based external link resolution | We currently auto-link `Context`, `Any`, `Callable`, etc. to Python stdlib + Django docs via `objects.inv` | Parse `objects.inv` (documented gzipped Sphinx format), build a name→URL map at build time, look up `ExprName`s in signatures against it | ~100 LOC |
| Module-level instances (e.g. `django_components.registry` at [`component_registry.py:630`](src/django_components/component_registry.py#L630): `registry: ComponentRegistry = ComponentRegistry()`) | griffe sees the `ExprCall(ComponentRegistry())`, not the instance | In the renderer, navigate to the class when an attribute's `.value` is an `ExprCall` | Trivial |
| `argparse` argument metadata for management commands | griffe gives source text of `add_arguments`, not the resulting flags/positionals | Keep current runtime-introspection path used by `reference.py` (instantiate command, read parser) | Already done today |
| Metaclass-set attributes (e.g. `ComponentNode._signature` is set by `BaseNodeMeta.__new__`) | Static load shows `_signature` as absent; `allowed_flags` is `ExprTuple([ExprName('COMP_ONLY_FLAG')])` (unresolved) | Use `griffe.load(..., force_inspection=True)`. Confirmed working once Django is configured: `_signature = <Signature (*args, **kwargs) -> str>`, `allowed_flags = ('only',)` resolved | One-line config |
| `_extension_hook_api` marker attribute (set by `@mark_extension_hook_api` decorator) | Not visible as a class member statically | Detect the decorator name in `cls.decorators` instead of reading the marker attribute | Trivial |
| NamedTuple `_fields` | Not a member | `tuple(cls.members.keys())` filtered to `Kind.ATTRIBUTE` | Trivial |
| `AliasResolutionError` mid-walk on stdlib re-exports | Walking some modules raises | Wrap member access in `try/except griffe.AliasResolutionError` | Trivial guard |
| Raw HTML injected into docstrings by our extensions | Both `RuntimeBasesExtension` and `SourceCodeExtension` prepend HTML to `obj.docstring.value` | Our docstring renderer must permit raw HTML (`python-markdown` with the `md_in_html` extension does) | Already in §4.7 plan; lib choice locked in main doc §11.4.B |

## 3. Inventory of API kinds we render today

21 distinct render targets across 14 files in [`docs/reference/`](docs/reference/). Of these, ~12 demand a distinct template. The rest fold into siblings.

### 3.1 Full inventory

| # | Kind | Page | Generator branch | Examples | Distinct template? |
|---|---|---|---|---|---|
| 1 | Class (general public) | [api.md](docs/reference/api.md) | `gen_reference_api` ([`reference.py:77-119`](docs/scripts/reference.py)) | `Component`, `ComponentRegistry`, `Slot` | **Yes** — `ReferenceClass` |
| 2 | Function (module-level) | api.md | same | `autodiscover`, `render_dependencies`, `format_attributes` | Folds into `ReferenceClass` w/ kind tag |
| 3 | Decorator function | api.md | same | `register`, `template_tag` | Folds into `ReferenceClass` |
| 4 | Module-level instance | api.md | same | `registry` | Folds into `ReferenceClass` (navigate to class via `.value`) |
| 5 | NamedTuple type alias | api.md | same | `SlotInput`, `SlotResult`, `ComponentMediaInput` | Folds into `ReferenceClass` |
| 6 | Exception class | [exceptions.md](docs/reference/exceptions.md) | `gen_reference_exceptions` ([`reference.py:155-186`](docs/scripts/reference.py)) | `AlreadyRegistered`, `NotRegistered`, `TagProtectedError` | Folds into `ReferenceClass` |
| 7 | Pre-defined Component class | [components.md](docs/reference/components.md) | `gen_reference_components` ([`reference.py:189-245`](docs/scripts/reference.py)) | `DynamicComponent`, `ErrorFallback` | **Yes** — `ReferenceComponentClass` (hides `Component` base, lists only unique methods) |
| 8 | Setting (NamedTuple field) | [settings.md](docs/reference/settings.md) | `gen_reference_settings` ([`reference.py:248-299`](docs/scripts/reference.py)) | `ComponentsSettings.autodiscover`, `ComponentsSettings.cache` | **Yes** — `ReferenceSetting` (signature without "attr" badge, paired with page-level defaults panel) |
| 9 | Tag formatter class | [tag_formatters.md](docs/reference/tag_formatters.md) | `gen_reference_tagformatters` ([`reference.py:352-415`](docs/scripts/reference.py)) | `ComponentFormatter`, `ShorthandComponentFormatter` | **Yes** — `ReferenceTagFormatter` (naked class card) |
| 10 | Tag formatter instance | tag_formatters.md | same | `component_formatter`, `component_shorthand_formatter` | Folds into a page-level "instance → class" list, not a per-symbol template |
| 11 | Management command (CLI) | [commands.md](docs/reference/commands.md) | `gen_reference_commands` ([`reference.py:437-543`](docs/scripts/reference.py)) | `components`, `components create`, `components ext run`, ... | **Yes** — `ReferenceManagementCommand` (usage block, source link, args table, subcommand links, doc body) |
| 12 | Template tag | [template_tags.md](docs/reference/template_tags.md) | `gen_reference_template_tags` ([`reference.py:546-608`](docs/scripts/reference.py)) | `component`, `fill`, `slot`, `provide`, `html_attrs` | **Yes** — `ReferenceTemplateTag` (`{% tag … %}` signature block from `BaseNode._signature`) |
| 13 | URL pattern | [urls.md](docs/reference/urls.md) | `gen_reference_urls` ([`reference.py:418-435`](docs/scripts/reference.py)) | `components/cache/...` paths | **Yes** — `ReferenceURLPattern` (trivial bullet) |
| 14 | Template variable | [template_variables.md](docs/reference/template_variables.md) | `gen_reference_template_variables` ([`reference.py:611-627`](docs/scripts/reference.py)) | `ComponentVars.args`, `ComponentVars.kwargs`, `ComponentVars.slots` | Folds into `ReferenceSetting` shape |
| 15 | Testing entrypoint | [testing_api.md](docs/reference/testing_api.md) | `gen_reference_testing_api` ([`reference.py:122-152`](docs/scripts/reference.py)) | `django_components.testing.djc_test` | Folds into `ReferenceClass` |
| 16 | Extension hook method | [extension_hooks.md](docs/reference/extension_hooks.md) | `gen_reference_extension_hooks` ([`reference.py:630-719`](docs/scripts/reference.py)) | `ComponentExtension.on_component_class_created`, `on_component_input`, `on_template_loaded` | **Yes** — `ReferenceExtensionHook` (`:::` block + custom "Available data" pipe-table) |
| 17 | Extension hook context (NamedTuple) | extension_hooks.md | same | `OnComponentClassCreatedContext`, `OnComponentRenderedContext`, ... (15 of them) | **Yes** — `ReferenceHookContext` (NamedTuple field listing) |
| 18 | Extension command API object | [extension_commands.md](docs/reference/extension_commands.md) | `gen_reference_extension_commands` ([`reference.py:722-756`](docs/scripts/reference.py)) | `CommandArg`, `CommandArgGroup`, `CommandHandler`, `ComponentCommand` | Folds into `ReferenceClass` |
| 19 | Extension URL API object | [extension_urls.md](docs/reference/extension_urls.md) | `gen_reference_extension_urls` ([`reference.py:759-793`](docs/scripts/reference.py)) | `URLRoute`, `URLRouteHandler` | Folds into `ReferenceClass` |
| 20 | Signal | [signals.md](docs/reference/signals.md) | `gen_reference_signals` ([`reference.py:904-917`](docs/scripts/reference.py)) | `template_rendered` | **Yes** — `ReferenceSignal` (fully hand-authored prose). Until signals are codified in the source, this is a markdown island |
| 21 | CommandArg / subcommand sub-structure | (nested inside #11) | `_format_command_args` ([`reference.py:998-1069`](docs/scripts/reference.py)) | per-arg bullets under `**Options:**` / `**Positional Arguments:**` | Sub-component of #11; reusable as `ArgsTable` |

### 3.2 The 12 distinct templates we'd actually build

1. `ReferenceClass` — covers kinds 1, 2, 3, 4, 5, 6, 15, 18, 19. The workhorse.
2. `ReferenceComponentClass` — kind 7.
3. `ReferenceSetting` — kinds 8, 14.
4. `ReferenceTagFormatter` — kind 9.
5. `ReferenceManagementCommand` — kind 11.
6. `ReferenceTemplateTag` — kind 12.
7. `ReferenceURLPattern` — kind 13.
8. `ReferenceExtensionHook` — kind 16.
9. `ReferenceHookContext` — kind 17.
10. `ReferenceSignal` — kind 20.
11. `AvailableInstancesList` — kind 10 (page-level component, not per-symbol).
12. `SettingsDefaultsPanel` — page-level companion for kind 8.

## 4. Shared sub-components

Common building blocks several templates reuse. Designed once, used everywhere.

| Sub-component | Used by | Inputs | Notes |
|---|---|---|---|
| `SignatureBlock` | All except URL pattern, Signal | `language` (`python`/`django`/`txt`), `signature_html` | Language-aware fenced code block |
| `SourceCodeLink` | All except URL pattern, Signal | `relative_filepath`, `lineno` | Replaces today's `_format_source_code_html` ([`mkdocs_util.py`](docs/scripts/mkdocs_util.py)). The current helper is reused by `reference.py:486,584` for hand-authored pages too — preserve that contract |
| `ParametersTable` | Hook ("Available data"), Command (`**Options:**`), Template tag (`**Args:**`) | List of `{name, type, description}` rows | Today only used for hooks; commands and template tags use loose bullet lists. Migration opportunity to normalize |
| `DocstringBody` | Universal | Parsed `griffe.Docstring` | Renders Google-section blocks. Must permit raw HTML (extensions inject it) |
| `AdmonitionsBlock` | Anywhere docstrings contain `!!! note` | (auto from markdown processor) | Used 31× in `src/`, 115× in `docs/`. We get this for free from pymdownx.details or a custom extension |
| `ExamplesBlock` | Template tags, commands | List of fenced code blocks | Renders `**Example:**` / `### Examples` consistently |
| `CrossRef` | Universal | `name`, `target_path` | Resolves against project symbols + external inventories. Replaces today's hand-coded `](api.md#dotted.path)` links — see §6 below |
| `SymbolTypeBadge` | Headings + TOC | `kind` (`class`/`func`/`attr`/`method`) | Emits `<span class="doc doc-symbol-{kind}">` to keep Material-compatible CSS working, or our own classes |

## 5. The Discovery → Rendering contract (the §2.2 split)

Today: [`reference.py`](docs/scripts/reference.py) walks the public API and emits mkdocstrings strings (`::: dotted.path` plus per-page YAML option blocks). The string syntax is the contract.

Proposed: split into two layers with a portable Python dict as the contract.

### 5.1 Layer 1 — Discovery

Input: nothing (or a config file pointing at the package and version).
Output: a `ReferencePage[]` list, each looking like:

```python
ReferencePage(
    slug="api",
    title="API",
    preface_md="...",          # rendered as markdown
    entries=[
        ReferenceEntry(
            kind="class",
            dotted_path="django_components.Component",
            display_name="Component",
            options={"inherited_members": True, "show_if_no_docstring": True},
            members_filter=None,
        ),
        ReferenceEntry(
            kind="function",
            dotted_path="django_components.autodiscover",
            ...
        ),
        ...
    ],
    layout="repeater",   # or "command_tree" / "hooks_plus_objects" / "settings"
)
```

`kind` is one of the 12 from §3.2; `layout` is one of a small fixed set of page-level layouts (most pages are `repeater`).

This object is JSON-serializable. We can dump it to disk, diff it between versions, snapshot-test it.

### 5.2 Layer 2 — Rendering

Input: a `ReferenceEntry` plus the loaded griffe `ModulesCollection`.
Output: rendered HTML for one entry, ready to be slotted into a page layout.

This layer is the per-kind Django components (§3.2). Each one is a `Component` with a known input shape:

```python
class ReferenceClass(Component):
    class Kwargs(NamedTuple):
        obj: griffe.Class                  # the resolved griffe object
        options: dict                      # rendering options
        cross_refs: CrossRefResolver       # for in-signature + docstring links
        source_link: SourceCodeLink        # built from obj.relative_filepath + obj.lineno
```

The layout pages (`api.md`, `commands.md`, etc.) become Django components that iterate `entries` and dispatch on `kind` to the appropriate per-kind component.

### 5.3 Why this split matters

- **Layer 1 is testable in isolation.** Walks the public API and produces a static structure. Easy to snapshot, easy to assert "the API surface didn't shrink" in CI.
- **Layer 2 is replaceable.** If we ever want a different renderer (Jinja, a static-typed website framework, an LLM-friendly JSON dump), only Layer 2 changes.
- **Removes mkdocstrings from the contract.** Layer 1 today hard-codes mkdocstrings string syntax. Layer 2 today is mkdocstrings + Material templates. Both go away.

## 6. mkdocstrings features we must replicate (or deliberately drop)

From the deep audit of [`mkdocs.yml:175-213`](mkdocs.yml) and rendered output.

### Load-bearing — must replicate

- **`signature_crossrefs`.** 712 auto-linked types on `site/reference/api/index.html` alone. Walk griffe `Expr` per parameter, look each `ExprName` up against the merged inventory.
- **External inventories** (Python stdlib + Django via `objects.inv`). The 712 above includes `Callable`, `Any`, `Context`, `Mapping`, etc. — all resolved via inventory.
- **Inventory output.** We emit `site/objects.inv` (7034 bytes). Other projects can cross-link to us; preserve.
- **Google-style docstring section parsing.** Use `griffe.docstrings.google` directly.
- **Symbol type heading + TOC badges.** `<span class="doc doc-symbol-{class|method|attribute|function}">`. Replicate the markup; ship our own CSS or keep Material-compatible classnames.
- **`group_by_category: true`.** Bucket class members into Attributes / Classes / Functions / Methods. Moderate.
- **`inherited_members: true`** (with per-page overrides). Walk MRO via griffe, de-duplicate overrides. Hard but well-scoped.
- **`merge_init_into_class: true`.** Promote `__init__` params into class signature.
- **`separate_signature: true` + `show_signature_annotations: true`.** Render annotated signatures as separate code blocks below headings.

### Cosmetic — flags we honor

- `docstring_section_style: list`, `unwrap_annotated: true`, `line_length: 140`, `show_root_full_path: false`, `docstring_options.ignore_init_summary: true`, `filters: ["!^_"]`, `show_if_no_docstring: false` (with per-page overrides).

### Safe to drop

- `preload_modules: [mkdocstrings]` — no code references `mkdocstrings.*`. Cargo-cult.
- `summary: true` — produces no output today (verified: no `doc-summary` class anywhere in `site/`).
- `show_submodules: true` — every `:::` targets a class or function, never a bare module. Unused.

### Authoring style cleanup

Mixed-style docstring sections: 43 true `Args:`/`Returns:`/`Raises:` sections vs. 129 markdown `**Args:**` / `**Example:**` / `**Note:**` pseudo-sections in `src/django_components/component.py` alone. A strict parser will silently lose the markdown ones. **Decide one convention before migration**, ideally during the spike for §11.6 (markdown extensions).

## 7. Migration risks (the seams to watch)

In rough priority order:

1. **Anchor scheme breaks 397 hand-typed markdown links in `src/`.** Every docstring writes the full markdown form `[X](api.md#django_components.Y)` instead of using mkdocstrings' bracket cross-refs. Two things change at once: (a) the anchor itself becomes the leaf name only (`#Component` instead of `#django_components.component.Component`), and (b) the hand-typed `[X](api.md#...)` form is replaced with a resolver-friendly form so docstrings stop hardcoding the page+slug. Net effect: all 397 are touched by the codemod, but afterwards the docstrings are decoupled from the docs URL layout. The links are highly regular (`grep -nE '\]\([^)]+\.md#django_components\.' src/django_components/`).
2. **`reference.py` (1160 lines) inlines mkdocstrings option YAML per page.** Each `gen_reference_*` function writes YAML strings. Migration is a rewrite, not a refactor: each generator becomes "produce `ReferenceEntry`s." Plan to do it in one PR per generator, not all at once.
3. **`_extension_*_api` marker attributes are an undocumented contract.** `reference.py:1117-1126` routes classes into sections by checking `getattr(obj, "_extension_hook_api", False)` etc. Set by `@mark_extension_hook_api` and friends. Decorator names are visible to griffe statically — port the predicate to "decorator name in `cls.decorators`?" Don't ship the migration without explicit test coverage for the routing.
4. **The naive property docstring scraper.** `_extract_property_docstrings` ([`reference.py:820-899`](docs/scripts/reference.py)) is hand-rolled line-by-line parsing with documented limits ("no colons in class base definition, 4-space indentation, top-level class"). Single most brittle generation logic on the site — replace with griffe's per-field docstring access during migration.
5. **`signals.md` is a hand-authored stub** ([`reference.py:902-903`](docs/scripts/reference.py) notes "the API of Signals is not yet codified"). Don't try to auto-generate it; treat as a markdown island until signals get codified in source.
6. **`tag_formatters.md` has a layout bug** ([`tag_formatters.md:16-17`](docs/reference/tag_formatters.md)): bullet line and first `:::` directive on adjacent lines with no blank between them. Fix in migration, not in mkdocs.
7. **`ComponentExtension` has no canonical anchor.** `api.md` filters it out via `_is_extension_hook_api` skip ([`reference.py:104`](docs/scripts/reference.py)), while `extension_hooks.md` renders only its `on_*` methods. Cross-refs to the class itself point at a hook-method anchor. Decide canonical home during migration.
8. **`api.md` is alphabetically ordered with no thematic grouping.** `inspect.getmembers` returns sorted names ([`reference.py:94`](docs/scripts/reference.py)). **Migration opportunity (worth doing):** add a thematic grouping layer — `ReferencePage` already allows arbitrary entry ordering, so the Layer 1 generator can emit pre-grouped sections (e.g. "Core components", "Slots & fills", "Registration", "Media & dependencies", "Errors") and let the layout render them as collapsible `<h2>` blocks with their own TOC entries. Roughly 60 minutes of curation work on top of what we already have.
9. **`gen-files` plugin runs `reference.py` as a script.** It does `sys.path` mangling ([`reference.py:60-72`](docs/scripts/reference.py)) to import `extensions.py`. New generator runs as a Django management command; lose the hack but verify nothing relies on it.
10. **Both griffe extensions inject raw HTML into docstring values.** Our markdown renderer must permit raw HTML. The main design doc locked in `python-markdown` + `md_in_html` (see §11.4.B), which preserves block-level HTML when properly fenced. Already in §4.7 plan; verify in proof.
11. **`autorefs` plugin is what turns mkdocstrings' `<autoref>` placeholders into real links.** A custom renderer that emits links directly skips this step — no replacement needed, but our cross-ref resolver has to land at the right point in the pipeline (after docstring rendering, before HTML emission).
12. **Material CSS classes (`doc doc-class-bases`, `doc doc-symbol-*`, `doc doc-contents`) are leaked into our content** by both griffe extensions and mkdocstrings rendering. If we move off Material theme, ship our own CSS for these classes, or rename them and update the extensions in lockstep.

## 8. Validation of our two griffe extensions

Both in [`docs/scripts/extensions.py`](docs/scripts/extensions.py). Verified portable:

- **`RuntimeBasesExtension`** ([`extensions.py:18-34`](docs/scripts/extensions.py)). Uses only `griffe.Class`, `griffe.Docstring`, `import_object`, and `get_import_path`. The mkdocstrings touchpoint is `get_mkdocstrings_plugin_handler_options()` which reads `show_if_no_docstring` — a config read, not a runtime API dependency. **Portable** with a one-line config swap. Prepends `<p class="doc doc-class-bases">Bases: ...</p>` to the docstring value; verified present in `site/reference/api/index.html` for `BaseNode`.
- **`SourceCodeExtension`** ([`extensions.py:37-46`](docs/scripts/extensions.py)). Uses `obj.relative_filepath`, `obj.lineno`, `obj.docstring`. Builds URL from `repo_url` (config) + `relative_filepath`. **Portable.** Same caveat: hardcodes branch `master` ([`extensions.py:9`](docs/scripts/extensions.py)). Note: the helper `_format_source_code_html` is reused by [`reference.py:486,584`](docs/scripts/reference.py) directly for Django commands and template tags — keep that contract.

Both extensions need only griffe + two strings from config (`repo_url`, `show_if_no_docstring`). No mkdocstrings runtime dependency. Both port verbatim.

## 9. Recommended first concrete step

Build a one-page proof of the §5 discovery → renderer split. Specifically:

1. **Pick `exceptions.md`** — smallest distinct page (17 lines, 3 entries, all kind `class`).
2. **Layer 1 prototype:** a script that walks `django_components` for exception classes and produces a `ReferencePage(slug="exceptions", layout="repeater", entries=[...])`. Dump as JSON.
3. **Layer 2 prototype:** a `ReferenceClass` Django component that takes one `ReferenceEntry`, resolves the griffe object, and renders HTML. Wire it into a minimal page layout.
4. **Validate end-to-end:** run the resulting HTML page, diff visually against today's `exceptions.html`. Confirm:
   - Heading anchor scheme works (canonical + legacy alias)
   - `RuntimeBasesExtension` HTML appears
   - Source link points correctly
   - One Google docstring's `Args:` / `Raises:` sections render
   - No mkdocstrings imports in the runtime path

If this works end-to-end in ~1 day, the rest is execution per the §3.2 component list. If it doesn't — most likely because of an HTML-injection-order issue or a griffe API surprise — we catch it before committing to the broader migration.

After Exception works, the next escalation is `Component` itself (one massive class, exercises every shared sub-component). Then move to `ReferenceManagementCommand` since it has the most bespoke layout and is the riskiest mechanically. The other 9 kinds follow in any order.

## 10. Where the per-kind templates live

Now that we know there are ~12 distinct templates (§3.2) and ~8 shared sub-components (§4), here's the concrete file layout fitting the §4.1 top-level shape from the main design doc.

```
docs_site/
    apps/
        docs/
            components/
                page_layout/                  <-- doc-page chrome (header, sidebar, footer)
                doc_page/                     <-- markdown page renderer
                example_card/                 <-- {% example %} live demos
                search_bar/                   <-- client-side search
                version_picker/               <-- mike replacement
                reference/                    <-- ALL of §11.5's work lives here
                    page_layouts/             <-- per-page layouts (one per reference/*.md page)
                        api_page/
                        commands_page/
                        components_page/
                        exceptions_page/
                        extension_commands_page/
                        extension_hooks_page/
                        extension_urls_page/
                        settings_page/
                        signals_page/
                        tag_formatters_page/
                        template_tags_page/
                        template_variables_page/
                        testing_api_page/
                        urls_page/
                    entries/                  <-- per-kind entry renderers (the 12 from §3.2)
                        reference_class/
                        reference_component_class/
                        reference_setting/
                        reference_tag_formatter/
                        reference_management_command/
                        reference_template_tag/
                        reference_url_pattern/
                        reference_extension_hook/
                        reference_hook_context/
                        reference_signal/
                        available_instances_list/
                        settings_defaults_panel/
                    shared/                   <-- §4 sub-components, reusable across entries
                        signature_block/
                        source_code_link/
                        parameters_table/
                        docstring_body/
                        cross_ref/
                        symbol_type_badge/
                        admonitions_block/
                        examples_block/
            discovery/                        <-- Layer 1 from §5
                __init__.py
                walk.py                       <-- walks django_components.*, produces ReferencePage objects
                kinds.py                      <-- ReferencePage / ReferenceEntry NamedTuples
                pages/                        <-- per-page generators (one per reference page)
                    api.py
                    commands.py
                    components.py
                    exceptions.py
                    extension_commands.py
                    extension_hooks.py
                    extension_urls.py
                    settings.py
                    signals.py
                    tag_formatters.py
                    template_tags.py
                    template_variables.py
                    testing_api.py
                    urls.py
            griffe_extensions/                <-- the two extensions, ported verbatim
                __init__.py
                runtime_bases.py
                source_code.py
            management/
                commands/
                    build_docs.py
            templatetags/
                docs_extras.py                <-- {% example %}, {% docstring %}, etc.
```

**Naming convention.** Components follow the django-components default of one directory per component, containing `component.py` (with embedded `template = """..."""` for short ones, or `template.html` + `script.js` + `style.css` for richer ones).

**The 1:1:1 pattern.** `discovery/pages/api.py` produces a `ReferencePage`. The same name shows up as `components/reference/page_layouts/api_page/`. The latter iterates the former's entries and dispatches each on `kind` to a `components/reference/entries/reference_<kind>/`. Three layers, parallel naming, easy to navigate.

**Why a `reference/` subtree under `components/`.** Keeps the reference renderer logically grouped: ~25 components total, all dedicated to API rendering. Without the subtree they'd be intermixed with `page_layout`, `example_card`, `search_bar`, etc., and the navigation cost would compound as we add more.

**Why `discovery/` is a sibling of `components/`, not under it.** The discovery layer doesn't render anything — it walks the public API and produces JSON-serializable data. Putting it under `components/` would confuse the two layers. The §2.2 split is enforced by directory placement.

**Where the griffe extensions live.** Moved from `docs/scripts/extensions.py` into the new Django app at `apps/docs/griffe_extensions/`. They're now importable as regular Python modules instead of being loaded via path manipulation. This also means they get type-checked by mypy under the project's strict-for-`django_components.*` config — which is currently NOT the case for `docs/scripts/*`.

---

## 11. Docstring format that works in both IDEs and the docs build

Today docstrings are optimized for the rendered docs site, not for IDE hover. That's a real cost: contributors writing docstrings can't see what they look like until CI builds the site. And users reading docstrings in their IDE see broken cross-refs, raw HTML, and unrendered admonitions.

Modern IDEs render markdown in hover popups (VSCode + Pylance, since ~2020; PyCharm, since ~2022). That makes "one docstring style that works in both worlds" achievable — with discipline. This spike scoped the convention.

### 11.1 What each IDE renders today

All "Inline code" / backtick examples below mean **single backticks** (the standard markdown form). The double-backtick wrapping in this table source is only because markdown table cells need it to display a literal backtick — when authoring docstrings, use one backtick around the name.

| Construct | VSCode/Pylance hover | PyCharm hover | mkdocstrings build | Recommendation |
|---|---|---|---|---|
| Google-style `Args:` / `Returns:` / `Raises:` | Parsed, rendered as structured sections | Parsed, rendered as structured sections | Parsed via griffe's google parser | **Use universally** |
| Markdown-bold pseudo-sections `**Args:**` | Plain bold text | Plain bold text | Passes through as markdown bold | **Sweep to true Google style** (129 occurrences in `src/django_components/component.py` alone) |
| Inline code with single backticks (e.g. one backtick + `Component` + one backtick) | Rendered as monospace | Rendered as monospace | Rendered as monospace | **Use for code, literals, and symbol mentions where a link isn't needed.** Backticks NEVER linkify — see §11.3 |
| Markdown link with full URL `[X](https://...)` | Clickable | Clickable | Clickable | OK but couples docstring to URL layout |
| Markdown link with relative path `[X](api.md#foo)` | Plain text (broken) | Plain text (broken) | Resolves at build | **Sweep away** — convert the 397 hand-typed links to bracket cross-refs |
| Bracket cross-ref `[X][]` (autorefs) or `[X][leaf.name]` | Plain text (broken) | Plain text (broken) | Resolves at build | **Use when a link is the point.** Accept the IDE-hover degradation as the cost of unambiguous backticks (Juro's call, see §11.3) |
| Raw HTML (`<i>New in version 0.70</i>`) | Plain text (broken) | Plain text (broken) | Renders | **Sweep away by default** — see §11.2 escape hatch |
| Material admonitions `!!! warning` | Plain text (broken) | Plain text (broken) | Renders as styled callout | **Sweep away by default** — see §11.2 escape hatch |
| Markdown bold/italic, headings, lists, code fences | Render fine | Render fine | Render fine | Use freely |

### 11.2 Recommended convention (pragmatic defaults, not absolute rules)

A docstring style that aims to work everywhere by default, with explicit escape hatches when a docstring genuinely needs a docs-build-only feature:

1. **Use Google-style structured sections.** `Args:`, `Returns:`, `Raises:`, `Examples:`, `Note:`, `Warning:`. Indent the body four spaces. Both IDEs and griffe parse these into structured display.
2. **Single backticks for code, literals, and symbol mentions where a link isn't needed.** Single backticks NEVER produce a link in the docs build — they're always rendered as monospace, the same way IDEs render them. This keeps backticks unambiguous (no surprise linkification, no "did the author mean a literal or a reference?" confusion). When a link IS the point of the mention, use the explicit bracket cross-ref form (see point 2a). See §11.3 for the reasoning.
2a. **Bracket cross-refs `[X][]` (or `[X][Y]`) when you want a link.** Don't write `[Component](api.md#Component)`. Write `[Component][]` — the docs build resolves the link text against the project's symbol index and emits the right URL. When the link text differs from the symbol name, use `[text you want shown][Component]`. The IDE shows this as plain text (no link), which is the tradeoff we accept for unambiguous backticks. See §11.3 for the resolver details.
3. **Prefer markdown alternatives to raw HTML and Material admonitions** — most of the time. Replace `<i>New in version X</i>` with `*New in version X.*`. Replace `!!! warning` with `> **Warning:** ...`. Both render reasonably in IDE hover AND in the build.
4. **Escape hatch.** When a docstring genuinely benefits from the Material admonition treatment (a long worked example, a critical-path "this will silently corrupt your data" callout that loses force as a blockquote), keep the `!!! warning` form. The IDE will degrade to plain text but the user still sees the heading and body — they just don't get the colored box. Same for raw HTML if it's load-bearing (e.g. an embedded diagram). **Three legitimate reasons to break the default:** (a) the content is so important that the docs-build callout treatment is a feature, not decoration; (b) duplicating the content out to a separate prose page would be needless overhead for one paragraph; (c) the markdown-only equivalent is significantly worse to read in BOTH the IDE and the build.
5. **External links: use full URLs.** `[Django Context](https://docs.djangoproject.com/.../#django.template.Context)`. IDEs make them clickable. Build passes them through. Acceptable because external links rarely break.
6. **Standard markdown for everything else.** Bold, italic, lists, fenced code blocks all work in both.

The principle: optimize for the common case (markdown that works in both worlds), allow the exception when the value is real. Don't accept duplication just to keep docstrings vanilla, and don't accept bland reference docs just to keep them IDE-friendly.

**Scope of *this* migration vs *later* convention adoption** (per Juro): the convention above is the **target state for new docstrings going forward**. Existing docstrings are NOT swept as part of the docs migration codemod. The 31 existing Material admonitions in `src/` and the 1 raw-HTML occurrence stay put — Juro will decide later, per-occurrence, whether each is load-bearing or habit. The §11.4 codemod fixes only what blocks the structural migration: the anchor scheme and the bold-pseudo Google sections.

### 11.3 The two-syntax model: backticks for code, bracket cross-refs for links

**Juro's decision** (overrides the earlier implicit-backtick proposal): single backticks stay monospace-only, always. They never produce a link, no resolver pass touches them, there's no heuristic and no opt-out marker. Backticks behave the same in IDE hover and in the docs build.

When a link IS the goal, use the explicit bracket cross-ref syntax: `[Component][]` (autorefs-style) or `[link text][Component]` when the visible text differs from the lookup key.

**Why this is the better tradeoff:** the original implicit-backtick proposal made `` `Component` `` ambiguous — author intent (literal? reference?) was no longer obvious from the source, and the resolver had to guess via heuristics. The new model trades a small IDE-hover degradation (cross-refs render as plain text in popups) for full unambiguity in the most common construct (backticks). Authors and readers no longer have to think about whether a given backtick will linkify.

**The trade explicitly:**

| | Single backticks `` `X` `` | Bracket cross-ref `[X][]` |
|---|---|---|
| IDE hover | Monospace | Plain text (no link) |
| Docs build | Monospace | Link to `api.md#X` |
| Author intent | "code / literal / mention" | "link to the X symbol" |
| When to use | Most mentions of code or symbols | Only when the link itself is the point of the mention |

In practice, most current `[Component](api.md#django_components.Component)` links can be answered with either form depending on context. Most prose like "the `Component` class handles rendering" wants backticks (mention, not link); the few links that are doing real navigational work ("see [Component][]'s `render` method for details") become bracket form.

**The resolver.** Smaller and simpler than the implicit-backtick version — only fires on bracket cross-refs:

```python
# After python-markdown converts the docstring,
# but before the HTML is slotted into the page layout:
SYMBOL_INDEX = {
    "Component":                       "api.md#Component",
    "ComponentRegistry":               "api.md#ComponentRegistry",
    "ComponentRegistry.register":      "api.md#ComponentRegistry.register",
    "Slot":                            "api.md#Slot",
    # ... ~200 entries, produced by Layer 1 discovery
    "on_component_input":              "extension_hooks.md#on_component_input",
}

def resolve_crossrefs(html: str, current_page: str) -> str:
    # python-markdown leaves [text][key] as a literal <a href="#key">text</a>
    # (because the ref is undefined). We intercept those and resolve against
    # SYMBOL_INDEX. Bare [text][] expands to [text][text] before this pass.
    def replace(match):
        text, key = match.group(1), match.group(2)
        target = SYMBOL_INDEX.get(key)
        if not target:
            # CI in --strict mode fails on unresolved refs (see §11.10 guardrails)
            warn(f"Unresolved cross-ref [{text}][{key}] in {current_page}")
            return match.group(0)
        url = make_relative(target, current_page)
        return f'<a class="symbol-ref" href="{url}">{text}</a>'
    return re.sub(r'<a href="#([^"]+)">([^<]+)</a>', replace, html)
```

**Ambiguity handling.** Same as before: when the leaf name `register` matches both `django_components.register` (top-level decorator) and `ComponentRegistry.register` (method), the index stores both keys. Author choice resolves it — `[register][]` links to the top-level, `[ComponentRegistry.register][]` to the method.

**What the IDE shows.** A `[Component][]` appears in hover as the literal text `[Component][]`. Not pretty, but not broken — the reader can still tell it's a reference to `Component`, and they have the IDE's "Go to definition" affordance separately. The annoyance is bounded to docstrings that contain *many* cross-refs; in normal prose where most mentions are backticked code, the cost is low.

**Why this matches the Python docs ecosystem.** `[X][]` is mkdocstrings + autorefs' standard form. By using it natively, we keep cross-refs portable — if we ever ship `objects.inv` for other docs sites to link into us (we already do, see §6), the convention round-trips. We're not inventing a private syntax.

**JSDoc `@link` analogue?** Still no. Python docstrings have no IDE-rendered cross-reference syntax. Sphinx roles (`:py:obj:`X``), PEP 727 — none of them render in IDE hover. The bracket form is just as broken in IDEs as Sphinx roles; we're choosing it because it's the ecosystem standard, not because it's IDE-friendly. The IDE-friendly half of the convention is the backtick rule — and that's what carries the daily load.

### 11.4 Codemod scope

**Scope (revised per Juro):** the codemod fixes only **structural blockers**. Advanced syntaxes in docstrings (Material admonitions, raw HTML, etc.) stay as written until a separate later decision.

1. **~975 markdown-link cross-refs** → bracket cross-refs. Find them with `grep -nE '\]\([^)]+\.md#django_components\.'` across `src/django_components/` (397 hits) and `docs/` (578 hits, see main doc §11.6.F). For each: extract the link text and the leaf name (the last dotted segment after `#django_components.`). If they match (the common case), produce `[X][]`. If they differ, produce `[link text][LeafName]`. **No per-link judgment about "navigational vs mention" — every existing link stays a link.** Trivial mechanical Python sweep.
2. **~129 markdown-bold pseudo-sections** in `src/django_components/component.py` and friends → true Google-style. Audited by Agent B: 43 already use true Google style, 129 use `**Args:**`. Slightly less mechanical because the indentation structure changes; ~half a day of manual cleanup with `--snapshot-update` to verify. This is a structural blocker — griffe's Google parser won't pick up the bold-pseudo form.
3. **Material admonitions and raw HTML in `src/` docstrings — NOT touched in this codemod.** Earlier draft proposed sweeping the 31 admonition occurrences into markdown blockquotes and the 1 raw-HTML occurrence into markdown italics for IDE-friendliness. **Rejected per Juro:** that's a judgment call for later. The §11.2 convention (single backticks, bracket cross-refs, prefer-markdown defaults) is the **target state for new docstrings going forward**, not a sweep target for existing ones. The migration's correctness doesn't depend on this sweep — admonitions render fine in both the old and new docs builds.

Total: roughly a one-day cleanup (link sweep + Google-style alignment). Worth doing as a precursor PR before the docs migration so the migration itself is purely additive.

### 11.5 What this gives us

- **Contributors get readable docstrings in their IDE** for the most common case (backticked code and symbol mentions). Cross-refs degrade to plain text in hover — accepted as the cost of unambiguous backticks.
- **Authors no longer guess** whether a given backtick will linkify. Backticks are monospace, full stop. Links are explicit.
- **The docs build is simpler** — the resolver is ~15 LOC, fires only on bracket cross-refs, and uses the same `[X][]` shape mkdocstrings + autorefs uses (we're not inventing private syntax).
- **Docstrings stop coupling to the docs URL layout** — the §7.2 anchor scheme change becomes a one-time event, not a recurring source of broken links.
- **The `objects.inv` we already emit becomes useful in reverse** — other docs sites that adopt our cross-ref form can link back into us with the same syntax we use internally.

This answers Juro's question: *yes, there's a docstring format that does both well, when "both well" means "backticks unambiguous in both, cross-refs explicit and accepted to degrade in IDEs."* Standard Google-style markdown, backticks for mentions, bracket cross-refs for navigation, an opinionated default of "prefer markdown over docs-only constructs," and an explicit escape hatch when a docs-only feature is genuinely worth it.

### 11.6 Where the convention is documented

Once we lock the convention, it has to live in places contributors (human and AI) will actually find:

1. **[docs/community/development.md](docs/community/development.md)** — the canonical "how to contribute" page on the docs site. Add a new section "Writing docstrings" that captures §11.2 (the recommended convention), §11.3 (the cross-ref behavior), and the escape-hatch principle. Link to a worked before/after example.
2. **[CLAUDE.md](CLAUDE.md)** — the operating rules for AI agents (and the de facto onboarding doc for new contributors who read it). Add to the "Code conventions" section: one paragraph naming the rule, with a pointer to `docs/community/development.md` for the full spec. Treat it like the existing "No em dashes" / "Run checks repo-wide" rules — short, prescriptive, with the "why" inline.
3. **Optional: a contrib-mode lint** — a tiny CI check that flags **new occurrences** of patterns the convention discourages (e.g. a fresh `[X](api.md#django_components.Y)` hand-typed link in a PR diff). Catches drift on incoming changes before it lands. Does NOT touch existing docstrings; the convention is forward-looking. Scope-creep for v1; capture as a follow-up.

The codemod PR (§11.4) and the docs/CLAUDE update should land together — same PR if scoped tightly, otherwise back-to-back. Without the docs update, contributors will recreate the old patterns within weeks.

**Reminder on scope.** The codemod itself is narrow (anchor scheme + Google-section alignment). The §11.2 convention is the *target* for new docstrings, communicated via docs and CLAUDE.md. Existing docstrings keep their admonitions, raw HTML, and other advanced syntaxes until a separate later decision.

---

## 12. Open items deferred to other spikes

- **§11.6 (markdown affordances)** — the markdown library + `pymdownx` extension audit (already largely answered in the main doc — `python-markdown` is locked in).
- **§11.10 (guardrails)** — the snapshot-test pattern for the discovery layer's `ReferencePage` output belongs here.
- **§11.11 (UI inspiration)** — the per-kind component visual design (signature block typography, badge colours, table style) belongs here.

**Already resolved by other spikes:**
- **§11.3 (Django→static prior art)** — decided: django-distill is the renderer kernel (see main doc §11.3 spike findings, around line 1010). This spike doesn't depend on the choice but it does mean the per-kind renderers run as ordinary Django views, distill-discovered via `distill_path()` and crawled at build time.

This spike answered the data, pipeline, file-layout, and authoring-convention questions. The visual / build-orchestration questions are out of scope by design.
