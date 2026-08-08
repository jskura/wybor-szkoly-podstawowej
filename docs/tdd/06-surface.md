# TDD — the v0 surface (work items 11 and 12)

The Streamlit app (plot check, URL paste, comparable exclusion) and the choropleth
plus gmina table.

Work items: [`18-v0-scope.md`](../18-v0-scope.md) §6 items **11** and **12**.
Requirements: FR-71, FR-67, FR-64, FR-25, FR-29, FR-30, FR-72.
Validation: **V59**, **V51c**, **V45**, **V62**, and V35–V37 applied to the v0
surface. Design: [`21-v0-ui-and-ux.md`](../21-v0-ui-and-ux.md) §3 (U1–U9) and §7
(U10–U14); [`09-ux-specification.md`](../09-ux-specification.md) §1, §3, §4.

---

## 1. Entry criteria (`20` §8)

| # | Criterion | Status |
|---|---|---|
| 1 | PRD requirement or work-plan entry | FR-71, FR-67, FR-25, FR-64; `18` §6 items 11–12 |
| 2 | Validation method exists | V59, V51c, V45, V62, V35–V37 |
| 3 | Verification tier assigned | **Tier A** for every test in this document — see below |
| 4 | Silent-failure detectors named | F7 (stock/flow) → §6; F8 (stale) → §5.8; F9 (price kinds) → §5.2; F1 (units) → §9.3 |
| 5 | Fixtures exist, dated, scrubbed | §11 |
| 6 | Metamorphic properties listed | §12.3 — the surface is not the numeric core, but three relations hold |

**The tier claim, stated precisely.** Whether `142 zł/m²` is a *fair* price is tier D
and unknowable in v0. Whether the number `142` was rendered **with its `n`, its
range, its price type, its price kind and its as-of date, at equal prominence,
outside any hover container** is a property of the output — exactly computable, so
tier A. This document tests only the tier-A half. That is the whole point of §2:
the honesty rules are the part of the surface that *can* be verified, and they are
the part that matters most for a user who cannot check the answer (D63).

## 2. The premise that makes the rest testable

### 2.1 Rendering helpers are pure functions returning a render tree

No test in this document drives a browser, a headless Streamlit session, or a DOM.
Every rendering helper is a pure function from a data payload to an immutable
**render tree**, and the assertions are made about that tree.

```
src/lpc/app/
├── render/            # pure. No streamlit import, no I/O, no clock, no config read
│   ├── contract.py    # RenderNode, Role, Prominence, Disclosure, walkers
│   ├── format.py      # Polish number, date, unit formatting
│   ├── aggregate.py   # render_aggregate_block        (U1)
│   ├── price.py       # render_price                  (U2)
│   ├── flow_stock.py  # render_flow_stock_pair        (U3, U4)
│   ├── absence.py     # render_absence                (U6, U7)
│   ├── state.py       # component state machine       (five states)
│   ├── provenance.py  # render_provenance             (U9)
│   ├── verdict.py     # render_verdict_block          (U5, U14)
│   ├── comparables.py # render_comparable_set         (U14, V51c)
│   ├── uncertainty.py # worded uncertainty, out-of-depth notice  (U10, U11)
│   ├── notes.py       # "what would change the answer"           (U13)
│   ├── export.py      # render_export                 (U12)
│   ├── map_model.py   # build_choropleth_model        (item 12)
│   ├── table.py       # build_gmina_table             (item 12)
│   └── inventory.py   # COMPONENT_REGISTRY — the sweep's source of truth
├── shell/
│   ├── adapter.py     # the ONLY module importing streamlit
│   └── streamlit_app.py
├── intake/
│   ├── url_paste.py   # dispatch by portal
│   └── portals/       # per-portal page parsers, pure
└── feedback/
    └── exclusion.py   # V51c: recompute + log
```

### 2.2 The contract under test

```python
Role       = Literal["aggregate_block", "value", "sample_size", "spread",
                     "price", "price_type_label", "price_kind_label",
                     "flow_window_label", "basis", "unknown", "absence",
                     "staleness", "provenance", "verdict", "comparable_set",
                     "comparable", "uncertainty_note", "out_of_depth_notice",
                     "sensitivity_note", "disclosure_banner", "selector",
                     "map_feature", "legend", "table_row", "fallback_form",
                     "error", "loading"]
Prominence = Literal["primary", "equal", "secondary"]
Disclosure = Literal["always", "expander", "hover"]

@dataclass(frozen=True)
class RenderNode:
    role: Role
    text: str                      # exactly what a user sees, already formatted
    prominence: Prominence
    disclosure: Disclosure
    children: tuple["RenderNode", ...]
    meta: Mapping[str, object]     # provenance, price_type, price_kind, n, basis…
```

Walkers in `contract.py`, each with its own tests: `walk(tree)`,
`nodes_by_role(tree, role)`, `siblings_of(tree, node)`, `ancestors_of(tree, node)`,
`disclosure_chain(tree, node)` (the ordered disclosures of a node's ancestors),
`index_of(tree, node)` (document order), `text_tokens(tree)`.

### 2.3 The gap this premise creates, and its closing test

Pure-tree tests cannot see a shell that receives a node and never draws it. That
gap is closed by one exhaustive mapping test, not by browser automation:

- `test_adapter_handles_every_role_in_the_role_enum()` — parametrized over every
  member of `Role`; asserts `adapter.HANDLERS` has an entry, and that adding a new
  `Role` without a handler fails this test.
- `test_adapter_emits_one_streamlit_call_per_node()` — against a fake `streamlit`
  module recording calls; asserts call count equals `len(list(walk(tree)))` and
  that no node's `text` is absent from the recorded call arguments.
- `test_adapter_preserves_document_order()` — recorded call order equals
  `walk(tree)` order, so U3's "flow first" and U14's "comparables before verdict"
  survive the shell.
- `tests/integration/app/test_app_smoke.py::test_app_builds_every_registered_component_without_streamlit_running()`
  — imports the app module, builds each registered component from fixtures,
  asserts no exception and a non-empty tree for each.

## 3. Ordered red-green sequence

Each step: write the listed tests, watch them fail **for the named reason**, then
implement the minimum that turns them green. No step begins before the previous is
green. Steps 1–3 are infrastructure; every later step consumes them.

| Step | Red (tests written first) | Fails first because | Green (implementation) |
|---|---|---|---|
| 1 | `tests/unit/app/test_render_contract.py` — immutability, walkers, `disclosure_chain`, document order | `contract.py` does not exist | `RenderNode`, `Role`, walkers |
| 2 | `tests/architecture/test_render_purity.py` — §4 | no purity boundary exists | package layout; `adapter.py` isolated |
| 3 | `tests/unit/app/test_format.py` — §8 | no formatters | `format.py` |
| 4 | `tests/unit/app/test_aggregate_block.py` — U1 (§5.1) + the sweep harness `test_no_bare_aggregate_sweep` | `render_aggregate_block` missing; sweep registry empty | `aggregate.py`, `inventory.py` |
| 5 | `tests/unit/app/test_price_labels.py` — U2 (§5.2) | prices render unlabelled | `price.py` |
| 6 | `tests/unit/app/test_flow_stock.py` — U3, U4 (§5.3, §5.4), V45, V62 | no flow/stock pairing, window hardcoded | `flow_stock.py`, config read |
| 7 | `tests/unit/app/test_absence_and_unknown.py` — U6, U7 (§5.6, §5.7) | one shared "brak danych" string | `absence.py` |
| 8 | `tests/unit/app/test_states.py` — §7, V36 | components define fewer than five states | `state.py`, registry states |
| 9 | `tests/unit/app/test_staleness.py`, `test_provenance.py` — U8, U9 (§5.8, §5.9) | age in a page banner; provenance two clicks deep | `provenance.py`, staleness node |
| 10 | `tests/unit/app/test_verdict_block.py` — U5, U14 (§5.5, §5.14) | verdict expanded, rendered above comparables | `verdict.py`, `comparables.py` |
| 11 | `tests/unit/app/test_uncertainty.py` — U10, U11 (§5.10, §5.11) | thin data renders numbers only | `uncertainty.py` |
| 12 | `tests/unit/app/test_sensitivity_notes.py` — U13 (§5.13) | no note derived from unknowns | `notes.py` |
| 13 | `tests/unit/app/test_export.py` — U12 (§5.12) | export strips caveats | `export.py` |
| 14 | `tests/unit/app/test_url_paste.py` + per-portal `tests/unit/app/portals/test_<portal>.py` — §9 | no parsers | `intake/` |
| 15 | `tests/unit/app/test_comparable_exclusion.py`, `test_exclusion_report.py` — §10, V51c | exclusion does not recompute or log | `feedback/exclusion.py` |
| 16 | `tests/unit/app/test_map_model.py`, `test_gmina_table.py` — §6, item 12 | no map model | `map_model.py`, `table.py` |
| 17 | `tests/unit/app/test_terminology_lint.py` — §8.3, V37 | lint absent | `scripts/lint_ui_terms.py` |
| 18 | `tests/unit/app/test_honesty_sweep.py`, `tests/unit/app/test_render_properties.py` — §12 | sweep not parametrized over the full inventory | registry completeness |

**Step 4 is the hinge.** The sweep harness built there is parametrized over
`COMPONENT_REGISTRY × STATES` and re-runs at every later step, so each new
component is subject to U1 the moment it is registered. A component that forgets
to register fails `test_registry_covers_every_render_module_export()` (§12.1).

## 4. Architectural tests (run at step 2, enforced forever)

- `test_no_render_module_imports_streamlit()` — AST scan of `src/lpc/app/render/`;
  the only permitted importer is `shell/adapter.py`.
- `test_render_modules_perform_no_io()` — AST scan forbidding `open`, `requests`,
  `httpx`, `psycopg`, `datetime.now`, `date.today`, `random` in `render/`.
  Clock and config values arrive as arguments, which is what makes staleness (U8)
  and the flow window (U4) testable without freezing time globally.
- `test_every_render_helper_returns_a_render_node()` — signature check over all
  public callables in `render/`.
- `test_render_helpers_are_deterministic()` — each helper called twice on the same
  fixture returns equal trees.
- `test_app_does_not_import_lpc_model()` — the v0 surface shows comparable-based
  numbers only; a `ModelEstimate` would need the `szacunek modelu` marker (`09` §1
  rule 5) and is out of v0 scope. Mirrors V21.

## 5. One test per interaction rule

Every test below names the fixture it runs against (§11) and the observation that
falsifies it. Where a rule is a universal, it is tested twice: once positively on a
representative component, once as a sweep over `COMPONENT_REGISTRY × STATES`.

### 5.1 U1 — no aggregate without `n` and range, at equal prominence

`tests/unit/app/test_aggregate_block.py`

- `test_aggregate_block_contains_value_sample_size_and_spread()` — for
  `AGG_FLOW_N23`: `nodes_by_role(tree, "value")`, `"sample_size"`, `"spread"` each
  return exactly one node, and all three share the same parent
  `aggregate_block` node.
- `test_sample_size_and_spread_have_equal_prominence_to_the_value()` —
  `n.prominence == spread.prominence == value.prominence == "equal"`. Falsified by
  `spread.prominence == "secondary"`.
- `test_n_and_spread_are_not_inside_a_hover_only_container()` — asserts
  `"hover" not in disclosure_chain(tree, n)` and likewise for `spread`. **This is
  the specific assertion V35 names**; falsified by moving the range into a tooltip.
- `test_n_and_spread_are_not_behind_an_expander()` — `"expander" not in
  disclosure_chain(...)`. Only provenance (U9) may sit behind one interaction.
- `test_render_aggregate_block_rejects_a_payload_without_n()` — payload missing `n`
  raises `BareAggregateError`; likewise missing `range`. The violation is
  unrepresentable, matching the API's `Aggregate` type (`14` §2.2).
- `test_spread_kind_follows_n()` — `n >= 5` → `range.kind == "iqr"` and the text
  reads `zakres międzykwartylowy`; `n < 5` → `min_max` and `zakres`. Falsified by
  an IQR label on `n=4`.
- `test_thin_aggregate_still_renders_its_number()` — `AGG_THIN_N4` renders
  `mediana 118` plus `61–240` plus `n = 4`; asserts the string
  `"za mało danych"` does **not** appear in place of the number (D17, rule 6).
- `test_no_bare_aggregate_sweep()` — parametrized over
  `COMPONENT_REGISTRY × STATES`; every node whose `meta` carries a numeric
  aggregate has `sample_size` and `spread` siblings outside hover. The sweep is the
  V35/V59 assertion applied to the surface v0 ships.

### 5.2 U2 — every price shows type **and** kind

`tests/unit/app/test_price_labels.py`

- `test_price_node_carries_type_and_kind_labels()` — parametrized over the six
  combinations; asserts sibling `price_type_label` and `price_kind_label` with
  exact Polish text: `offering→"cena ofertowa"`, `sales→"cena transakcyjna"`,
  `asking→"oferta"`, `auction_start→"cena wywoławcza"`,
  `tender→"cena przetargowa"`.
- `test_render_price_rejects_a_price_without_kind()` — raises
  `UnlabelledPriceError`; and without `price_type` likewise. FR-64, V46.
- `test_price_labels_are_not_hover_only()` — `disclosure_chain` contains no
  `"hover"`.
- `test_aggregate_block_refuses_inputs_spanning_price_kinds()` — a payload whose
  `sources` span `asking` and `auction_start` raises `MixedPriceKindError`. The
  rendering half of F9's detector.
- `test_offering_and_sales_never_share_a_block()` — the two are separate
  `aggregate_block` nodes with distinct `meta["price_type"]`; falsified by one
  block whose children carry both.

### 5.3 U3 — flow and stock both shown, both labelled, flow first

`tests/unit/app/test_flow_stock.py` (V45)

- `test_flow_and_stock_both_rendered()` — both blocks present for
  `AGG_PAIR_FLOW118_STOCK127`.
- `test_flow_block_precedes_stock_block()` — `index_of(flow) < index_of(stock)`
  (D56). Falsified by stock rendering first.
- `test_both_blocks_carry_their_basis_label()` — exact text
  `"Podobne oferty (przepływ, ostatnie 90 dni)"` and
  `"Podobne oferty (stan, wszystkie aktywne)"`.
- `test_neither_renders_without_its_basis()` — a payload with
  `basis=None` raises `UnlabelledAggregateError` (V45's architectural check,
  applied at the render boundary).
- `test_flow_and_stock_are_never_averaged()` — no node's `meta` contains a value
  equal to the mean of the two medians; and `render_flow_stock_pair` exposes no
  combined figure.
- `test_stock_flow_gap_is_shown_as_a_gap_not_reconciled()` — the fixture's
  constructed gap (127 vs 118) appears as two figures, and any commentary node
  describes it (`"stan wyżej niż przepływ"`), never replaces either.

### 5.4 U4 — the flow window appears next to every flow figure

`tests/unit/app/test_flow_stock.py` (V62)

- `test_flow_window_label_is_a_sibling_of_every_flow_figure()` — every node with
  `meta["basis"] == "flow"` has a `flow_window_label` sibling reading
  `"ostatnie 90 dni"`.
- `test_flow_window_is_read_from_config_not_hardcoded()` — with
  `flow_window_days=60` the label reads `"ostatnie 60 dni"` **everywhere** in the
  sweep; falsified by any surviving `90`.
- `test_no_render_module_contains_a_literal_window_length()` — AST scan for the
  integer literals 30/60/90/180 in `render/`; V62's "two call sites, two windows"
  failure caught structurally.
- `test_flow_window_label_appears_in_the_export_and_the_map_legend()` — the label
  travels with the figure into `export.py` and `map_model.py`.

### 5.5 U5 — verdict collapsed until expanded

`tests/unit/app/test_verdict_block.py`

- `test_verdict_block_is_collapsed_by_default()` — the `verdict` node has
  `disclosure == "expander"` and `meta["expanded"] is False`.
- `test_collapsed_verdict_leaks_no_conclusion_text()` — the collapsed node's own
  `text` is exactly `"WERDYKT"`; assert no token from
  `{"powyżej", "poniżej", "w zakresie"}` is reachable without expanding.
- `test_expanded_verdict_is_phrased_relative_to_the_range()` — expanded text
  matches one of the three sanctioned forms and names the range
  (`"Powyżej górnej granicy zakresu przepływu (96–141)"`).
- `test_verdict_never_expresses_a_percentage_off_a_midpoint()` — no `%` character
  and no `"od mediany"` in any verdict node (`05` §5).
- `test_verdict_states_its_basis()` — the basis line carries n, gmina, area band
  and window: `"Podstawa: 23 oferty, ta sama gmina, 1 600–4 800 m², ostatnie 90 dni"`.

### 5.6 U6 — `unknown` renders as explicit Polish text, never blank or dash

`tests/unit/app/test_absence_and_unknown.py`

- `test_unknown_buildability_renders_explicit_polish_text()` — `buildability =
  'unknown'` renders role `unknown` with exactly
  `"brak danych planistycznych — sprawdź w gminie"`. Falsified by `""` or `"—"`.
- `test_no_rendered_text_is_blank_or_a_dash_sweep()` — over
  `COMPONENT_REGISTRY × STATES`, no node's `text` is in
  `{"", " ", "-", "–", "—", "?", "n/a", "N/A", "None", "null", "nan", "NaN", "0"}`
  where its role is not `value`. Catches the Python-repr leak as well as the blank.
- `test_unknown_is_not_styled_as_reassurance()` — the `unknown` node's
  `meta["tone"] == "warning"`, never `"ok"`; and it is not `secondary` prominence.
- `test_unknown_utilities_and_road_access_each_render_their_own_text()` —
  parametrized over `buildability`, `utilities`, `road_access`, `soil_class`; each
  unknown has its own sentence, so three unknowns do not collapse into one.
- `test_unknown_is_never_inferred()` — a payload with `zoning_claim` present and
  `buildability='unknown'` still renders unknown; the advert's claim renders
  separately, labelled `"z ogłoszenia"` (FR-17, `06` §1).

### 5.7 U7 — the four absence reasons are distinguished

`tests/unit/app/test_absence_and_unknown.py`

- `test_four_absence_reasons_render_distinct_text()` — for
  `{not_yet_crawled, no_listings, out_of_scope, too_few_comparables}` the rendered
  texts are pairwise distinct; falsified the moment two share `"Brak danych"`.
- `test_each_absence_reason_states_its_own_next_action()` — each carries an action
  node: not-yet-crawled → `"jeszcze nie zebraliśmy — sprawdź później"`;
  no-listings → `"brak ofert w tej gminie"`; out-of-scope →
  `"poza zasięgiem narzędzia"`; too-few-comparables →
  `"za mało podobnych ofert, żeby porównać"`.
- `test_absence_reasons_render_distinctly_on_the_map_too()` — §6.
- `test_absence_never_renders_as_zero_or_as_a_number()` — no `value` node in any
  absence tree.
- `test_unknown_absence_reason_raises()` — a reason outside the enum raises
  `UnknownAbsenceReasonError` rather than falling back to a generic string. Without
  this, the four collapse back into one the first time a fifth appears.
- `test_absence_reason_enum_matches_the_api_contract()` — the render enum is a
  subset of `14` §2.3's reasons, so the surface cannot invent its own vocabulary.

### 5.8 U8 — stale data shows its age on the number

`tests/unit/app/test_staleness.py` (F8)

- `test_staleness_node_is_a_sibling_of_the_value_not_a_page_banner()` —
  `siblings_of(tree, value)` contains the `staleness` node, and no
  `staleness` node exists at tree root.
- `test_stale_age_text_is_explicit()` — `"dane sprzed 12 dni · ostatnie pobranie
  27.07.2026"` for `as_of` twelve days before the injected `now`.
- `test_fresh_data_renders_no_staleness_node()` — inside the threshold, absent.
- `test_staleness_threshold_is_read_from_config()` — changing the expected crawl
  cadence changes which fixtures are marked.
- `test_every_stale_component_in_the_sweep_marks_its_own_number()` — over
  `COMPONENT_REGISTRY` in the `stale` state.

### 5.9 U9 — every number is one click from source, as-of and method

`tests/unit/app/test_provenance.py`

- `test_every_numeric_node_carries_a_provenance_handle()` — sweep: every `value`
  node's `meta["provenance"]` has non-empty `source`, `as_of`, `method_version`,
  and `n`.
- `test_provenance_is_exactly_one_interaction_away()` — the `provenance` node's
  `disclosure_chain` contains exactly one `"expander"` and no `"hover"`. Falsified
  by provenance nested two expanders deep, and by provenance shown on hover only
  (unreachable on a touch device, and unscreenshotable).
- `test_provenance_lists_every_contributing_source()` — a mixed-source aggregate
  lists all sources, not the first.
- `test_provenance_dates_are_polish_formatted()` — `DD.MM.YYYY` (§8).

### 5.10 U10 — uncertainty stated in words, not only in numbers

`tests/unit/app/test_uncertainty.py`

The rule exists because a range is only legible to someone who already has a prior,
and the user does not have one (D63).

- `test_thin_aggregate_carries_a_worded_uncertainty_note()` — `AGG_THIN_N4`
  produces an `uncertainty_note` reading
  `"Zakres szeroki — mało podobnych ofert"`. Falsified by `n=4` rendering only
  numbers, however correct.
- `test_wide_spread_is_worded_even_when_n_is_large()` — `AGG_WIDE_N40`
  (IQR/median above the configured ratio) also gets a note:
  `"Zakres szeroki — ceny w tej gminie bardzo się różnią"`. A large `n` is not
  evidence of a tight market.
- `test_tight_and_well_supported_aggregate_gets_no_note()` — `AGG_TIGHT_N61`
  produces none; falsified by a note on every aggregate, which would train the user
  to ignore notes.
- `test_uncertainty_note_is_not_hover_only_and_not_secondary()` — disclosure
  `always`, prominence `equal`.
- `test_note_wording_is_selected_from_a_closed_vocabulary()` — the note text is one
  of a fixed, reviewed set; parametrized over (n band × spread band) to assert the
  full mapping, so a new band cannot silently produce an empty string.

### 5.11 U11 — the tool volunteers when it is out of its depth

`tests/unit/app/test_uncertainty.py`

- `test_below_the_comparable_threshold_the_notice_leads()` — with
  `COMP_SET_N3`, the first node in document order is the `out_of_depth_notice`
  reading exactly
  `"za mało danych, żeby ocenić — to jest orientacja, nie wycena"`.
  Falsified by any estimate node preceding it.
- `test_no_confident_band_is_presented_below_the_threshold()` — no `verdict` node
  at `prominence == "primary"`; the estimate still renders (rule 6 — nothing is
  hidden) but demoted beneath the notice with its `n` and range.
- `test_out_of_depth_threshold_is_read_from_config()` — raising the threshold makes
  a previously-confident fixture produce the notice.
- `test_notice_appears_in_the_export_and_in_the_map_panel()` — the admission
  travels with the figure; a screenshot of a thin gmina panel carries it (U12).
- `test_notice_is_absent_when_the_set_is_adequate()` — `COMP_SET_N23`, none.
- `test_silence_is_never_the_thin_data_rendering()` — sweep asserting that every
  component in the `thin` state emits at least one of
  `{uncertainty_note, out_of_depth_notice}`. This is the rule's real content:
  silence would read as confidence.

### 5.12 U12 — never a single unqualified number, in any export or screenshot

`tests/unit/app/test_export.py`

- `test_export_line_containing_a_number_also_contains_n_and_range()` — regex sweep
  over the exported text: every line with a `\d` token either carries `n =` and a
  range, or is a labelled non-aggregate (area, date, count-of-listings with its own
  qualifier).
- `test_export_carries_the_honest_disclosure_verbatim()` — `21` §7.2's paragraph
  appears in full, not a shortened variant.
- `test_export_preserves_price_type_and_kind_on_every_figure()`.
- `test_export_of_a_thin_estimate_leads_with_the_out_of_depth_notice()`.
- `test_copy_to_clipboard_payload_equals_the_export_text()` — one code path, so a
  second, unqualified path cannot appear.

### 5.13 U13 — show what would change the answer

`tests/unit/app/test_sensitivity_notes.py`

- `test_unknown_buildability_produces_its_specific_note()` — exactly
  `"gdyby ta działka miała plan miejscowy, porównania byłyby inne"`.
- `test_notes_are_derived_from_the_subject_s_missing_attributes()` — parametrized:
  unknown road access → `"gdyby dojazd był drogą gminną, a nie służebnością,
  porównania byłyby inne"`; unknown utilities → its own; a fully-known subject →
  **no** note. Falsified by a constant note that appears regardless of the subject.
- `test_each_note_names_a_question_the_user_can_take_to_the_gmina()` — every note
  carries `meta["action"]` naming the office and the document (*wypis i wyrys*).
- `test_notes_are_ordered_by_the_size_of_the_difference_they_would_make()` — the
  attribute whose stratum gap is largest in the fixture is listed first.

### 5.14 U14 — the comparable set is shown before the verdict

`tests/unit/app/test_verdict_block.py`

- `test_comparable_set_precedes_the_verdict_block()` —
  `index_of(comparable_set) < index_of(verdict)`.
- `test_every_comparable_is_listed_with_its_own_price_area_and_distance()` — one
  `comparable` node per member of `COMP_SET_N23`, each with price (type + kind),
  area, gmina, listing date.
- `test_every_comparable_carries_its_nie_pasuje_control()` — each `comparable` node
  has `meta["exclude_control"]` with a stable `comparable_id` (V51c).
- `test_ordering_survives_a_recompute()` — after an exclusion (§10) the ordering
  assertion holds again on the new tree.

## 6. The choropleth and the gmina table (item 12)

`tests/unit/app/test_map_model.py`, `tests/unit/app/test_gmina_table.py`

Same helpers, same honesty rules (`04` §work-item table: item 12 is covered by V59
"same helpers"). The map is where a shortcut is most tempting, because a colour is
a number with its qualifiers stripped off.

- `test_price_type_and_kind_selector_is_always_present()` — the model always
  contains a `selector` node with `disclosure == "always"`; falsified by a selector
  that appears only in a sidebar expander.
- `test_legend_title_states_the_current_price_type_and_kind()` — e.g.
  `"cena ofertowa · oferta · przepływ, ostatnie 90 dni"`.
- `test_map_refuses_features_spanning_price_types()` — mixed input raises
  `MixedPriceTypeError`. "The most dangerous screen in the product" is made
  unrepresentable rather than merely discouraged.
- `test_gmina_below_n5_renders_hatched_and_still_coloured()` — `pattern ==
  "hatch"` **and** `fill is not None` (O13 + rule 6: the hatch says thin, the
  colour is not withheld).
- `test_the_four_absence_reasons_and_thin_have_pairwise_distinct_treatments()` —
  over `{thin, not_yet_crawled, no_listings, out_of_scope, too_few_comparables}`,
  the `(fill, pattern, legend_key)` triples are pairwise distinct. Falsified by
  "no listings" and "not yet crawled" sharing grey.
- `test_every_gmina_label_carries_n_inline()` — label text matches
  `r"^.+ · n = \d+$"`, or the gmina's absence reason.
- `test_gmina_table_row_carries_flow_stock_gus_and_benchmark()` — each with median,
  range, `n`, `as_of`, price type and kind; the GUS row additionally labelled
  `"poziom powiatu, dane kwartalne"`.
- `test_gminas_with_no_data_still_appear_as_rows()` — always show; falsified by a
  table that quietly drops them and makes coverage look complete.
- `test_standard_plot_benchmark_states_its_basis()` — O7's
  `"3 000 m² buildable ≈ X zł"` carries n, range and the assumption, and is
  labelled as derived.
- `test_map_and_table_agree_for_every_gmina()` — the colour bucket of each feature
  equals the bucket implied by that gmina's table median. Two renderings of one
  model cannot disagree.
- `test_clicking_a_gmina_builds_the_panel_with_flow_stock_gus_and_benchmark()` —
  panel model built from the same aggregates; the U1 sweep applies to it.

## 7. Component states — five each, for every data-bearing component

`tests/unit/app/test_states.py` (V36)

`COMPONENT_REGISTRY` in `render/inventory.py` names every data-bearing component:
`plot_check_header`, `verdict_block`, `comparable_set`, `flow_aggregate_block`,
`stock_aggregate_block`, `gus_sales_block`, `standard_plot_benchmark`,
`uncertainty_panel`, `map_feature`, `map_legend`, `gmina_panel`, `gmina_table_row`,
`coverage_row`, `provenance_panel`.

- `test_every_registered_component_defines_all_five_states()` — parametrized over
  `COMPONENT_REGISTRY × {loading, empty, thin, stale, error}`; each builds a
  non-empty tree. A component missing one state fails here, which is V36's
  "enumerating components and failing when any lacks a defined state".
- `test_loading_state_contains_no_value_like_token()` — the loading tree contains
  no digit and no dash; role `loading` only. Falsified by a `0` or `—` skeleton
  that reads as a value.
- `test_empty_state_names_which_of_the_four_reasons_applies()` — §5.7; the empty
  state is never generic.
- `test_thin_state_shows_number_and_min_max_and_n_and_a_worded_note()` — §5.1,
  §5.10 combined; never `"insufficient data"`.
- `test_stale_state_marks_the_number_itself()` — §5.8.
- `test_error_state_names_what_failed_and_what_is_still_trustworthy()` — e.g.
  `"Nie udało się pobrać danych GUS — ceny ofertowe poniżej są aktualne"`.
- `test_a_failed_sales_query_does_not_blank_the_offering_block()` — the partial
  degradation test V36 requires: build the plot check with the GUS source raising;
  assert the flow and stock blocks are intact and complete, and only the sales
  block is in `error`.
- `test_a_failed_map_tile_does_not_blank_the_gmina_table()` — the same property on
  item 12.
- `test_state_is_derived_not_passed()` — the state is computed from the payload
  (`n`, `as_of`, `absent`, exception), so a caller cannot mislabel a thin
  aggregate as normal.

## 8. Polish formatting and terminology (V37)

### 8.1 Numbers, units, dates — `tests/unit/app/test_format.py`

- `test_thousands_separator_is_a_non_breaking_space()` — `format_int(1234567) ==
  "1 234 567"`; asserts the exact codepoint, and that no `","` or `"."`
  appears as a group separator.
- `test_decimal_separator_is_a_comma()` — `format_decimal(118.5) == "118,5"`;
  falsified by `1,234.56` (V37's named falsifier).
- `test_price_unit_is_zl_per_m2_with_a_superscript_two()` —
  `format_ppm2(142) == "142 zł/m²"` with U+00B2; forbidden variants `zl/m2`,
  `PLN/m2`, `zł/m2` are asserted absent from the full sweep.
- `test_area_uses_m2_and_never_ar_or_ha_in_output()` — input may be *ar*/*hektar*
  (§9.3), output is always m² with a space separator: `"3 200 m²"`.
- `test_dates_render_dd_mm_yyyy()` — `date(2026, 8, 1) → "01.08.2026"`; zero-padded.
- `test_quarters_render_as_gus_labels()` — `"GUS 2025Q4"` as `21` §2.1 shows.
- `test_formatting_is_locale_independent()` — same outputs under `C` and `pl_PL`
  locales; no reliance on process locale.
- `test_no_rendered_number_uses_a_dot_decimal_sweep()` — regex over every fixture
  tree's text; catches an unformatted float leaking through a new component.
- `test_rounding_is_explicit_and_never_creates_false_precision()` — zł/m² to whole
  numbers, ratios to one decimal; `format_ppm2(142.4999)` renders `"142 zł/m²"`,
  not `"142,4999"`.

### 8.2 Polish throughout

- `test_no_ui_string_contains_an_english_stopword()` — over all string constants in
  `render/`: `{"median", "range", "price", "unknown", "loading", "error",
  "no data", "sample"}` absent. Code identifiers stay English (D15); user-facing
  text does not.

### 8.3 Terminology lint against the glossary — `scripts/lint_ui_terms.py`

- `test_protected_terms_are_never_loosely_translated()` — for each protected term
  in `12-glossary.md` §4 (*plan ogólny*, *MPZP*, *wypis i wyrys*, *działka*,
  *media*, *droga dojazdowa*, *cena ofertowa*, *cena transakcyjna*), the lint fails
  on the forbidden renderings: `cena ofertowa → "cena rynkowa" | "market price"`,
  `cena transakcyjna → "cena"` unqualified, `droga dojazdowa → "dojazd"` alone,
  `MPZP → "plan"` alone.
- `test_every_domain_term_used_in_the_ui_exists_in_the_glossary()` — the lint
  extracts domain nouns from UI strings and asserts each appears in the glossary's
  Polish column; an invented synonym fails.
- `test_glossary_protected_list_is_read_from_the_document()` — parsed from
  `docs/12-glossary.md`, not duplicated in code, so adding a term to the glossary
  extends the lint automatically.
- `test_lint_flags_a_seeded_violation()` — a fixture module containing
  `"cena rynkowa"` must fail the lint. Without this meta-test the lint could pass
  by doing nothing (the §12.2 principle).

## 9. URL paste (D61, FR-72)

`tests/unit/app/test_url_paste.py`, `tests/unit/app/portals/test_<portal>.py`

Parsing runs against **recorded fixture pages**, never the network; the parser is
pure, per the connector contract (`16` §2 rule 1).

### 9.1 Dispatch

- `test_url_is_routed_to_the_parser_for_its_portal()` — parametrized over portal A
  and portal B URL forms, including query strings and mobile hosts.
- `test_unsupported_portal_is_rejected_by_name()` — raises
  `UnsupportedPortalError`; the tree shows `"Nie obsługujemy tego portalu —
  wpisz powierzchnię i gminę ręcznie"` plus a `fallback_form` node. Never a guess.
- `test_a_non_url_input_is_rejected_without_a_traceback()`.
- `test_paste_is_refused_when_robots_disallows_the_portal()` — the work-item-0 gate
  reaches the surface: an explicit refusal message, no fetch.

### 9.2 Per-portal page parsing

- `test_listing_page_yields_area_price_locality_and_kind()` — per portal, against
  `tests/fixtures/app/listing_pages/<portal>/<id>.html` and its expected JSON:
  `area_m2`, `price_pln`, `price_per_m2`, `locality`, `teryt`,
  `price_type="offering"`, `price_kind="asking"`, `listing_id`, `first_seen`.
- `test_parsed_result_records_parser_version_and_fetched_at()` — so a portal
  layout change is attributable (D61 warns it will happen).
- `test_pasted_page_is_stored_as_a_raw_document_with_its_hash()` — FR-72; the
  re-parse path exists for pasted pages too.
- `test_parse_performs_no_network_io()` — architecture test over
  `intake/portals/`.

### 9.3 Unit conversion at the paste boundary (F1)

- `test_page_stating_ar_converts_to_m2()` — `"12 arów"` → `1200`; falsified by
  `12`.
- `test_page_stating_hektar_converts_to_m2()` — `"0,35 ha"` → `3500`; note the
  comma decimal in the source text.
- `test_implausible_area_is_quarantined_not_rendered()` — an area outside the
  validity band produces an `error` state naming the field, never a zł/m² figure.
  A 100× error is silent and fatal, so the surface refuses rather than displays.

### 9.4 When parsing fails

- `test_total_parse_failure_renders_the_manual_entry_fallback()` — malformed
  fixture: tree contains `fallback_form` and an `error` node naming what could not
  be read; contains **no** `verdict`, no estimate, no zł/m².
- `test_partial_parse_asks_for_the_missing_field_only()` — price found, area not:
  the form is prefilled with what was parsed, the missing field flagged
  `"nie udało się odczytać powierzchni — wpisz ją"`, and no zł/m² is computed from
  a guessed area.
- `test_a_changed_layout_fixture_fails_loudly()` — `<portal>_layout_changed.html`
  must raise `ParseFailure`; falsified by a parser returning a partial record that
  looks complete. This is the fixture that protects against the failure mode D61
  predicts.
- `test_parse_failure_is_logged_with_the_raw_document_hash()` — so the fix is a
  re-parse, not a re-crawl.
- `test_failure_never_degrades_into_the_gmina_average()` — asserts the tree does
  not silently substitute a gmina aggregate for the unparsed plot.

## 10. Comparable exclusion (V51c)

`tests/unit/app/test_comparable_exclusion.py`, `tests/unit/app/test_exclusion_report.py`

Against `COMP_SET_N6_CONSTRUCTED`: six comparables whose median and IQR are known
by hand, one of them (`cmp_hi`) constructed to move the median by a known amount.

- `test_excluding_a_comparable_recomputes_the_estimate()` — after excluding
  `cmp_hi`: `n` drops from 6 to 5, and the median and range equal the hand-computed
  values for the remaining five. Falsified by an estimate that does not move — the
  exact failure V51c names.
- `test_exclusion_is_logged_with_subject_comparable_and_change()` — one log row
  with `subject_id`, `comparable_id`, `excluded_at`, `estimate_before {median, low,
  high, n}`, `estimate_after {…}`, `method_version`. Falsified by a missing row or
  a row without the before/after pair.
- `test_exclusion_is_reversible_and_restores_the_original_estimate()` — undo
  returns the original figures exactly and logs the restore.
- `test_exclusion_never_mutates_the_underlying_listing_or_aggregate()` — the gmina
  aggregate is unchanged after exclusion; the judgement is session-scoped feedback,
  not a data edit.
- `test_recomputed_estimate_still_obeys_u1()` — the new tree passes the §5.1
  assertions; a recompute path is a second rendering path and must not bypass them.
- `test_excluding_down_to_the_threshold_switches_to_the_out_of_depth_notice()` —
  excluding three of six crosses the threshold and U11's notice leads. The interface
  becomes *less* confident as the user removes evidence, which is the behaviour a
  user who cannot price plots needs.
- `test_excluding_every_comparable_renders_the_too_few_comparables_absence()` —
  not a crash, not an empty band.
- `test_exclusion_report_groups_by_attribute()` — V51c(b): a log where five of six
  exclusions have `road_access == "public_main"` produces a report row naming that
  attribute with its count and share of exclusions.
- `test_exclusion_report_is_silent_below_the_pattern_threshold()` — one exclusion
  is noise, not a signal.
- `test_exclusion_report_names_the_selection_rule_it_implicates()` — the report
  points at the comparable-selection rule to revisit, so the feedback loop V51c
  requires ("a pattern of exclusions never feeding back") is closed by an artefact,
  not by intent.

## 11. Fixtures

`tests/fixtures/app/`, all dated and scrubbed of personal data (`20` §8 criterion 5;
FR-22 — no anchor addresses, so gmina Skierniewice and Elbląg-ring gminas appear,
never a street).

| Fixture | Shape | Used by |
|---|---|---|
| `AGG_FLOW_N23` | median 118, IQR 96–141, n=23, offering/asking | §5.1–5.4 |
| `AGG_STOCK_N61` | median 127, IQR 99–168, n=61 | §5.3 |
| `AGG_THIN_N4` | median 118, min–max 61–240, n=4 | §5.1, §5.10, §7 |
| `AGG_WIDE_N40` | large n, IQR/median above the ratio threshold | §5.10 |
| `AGG_TIGHT_N61` | large n, narrow IQR | §5.10 |
| `AGG_SALES_GUS` | mean 104, powiat level, 2025Q4, sales/— | §5.2, §7 |
| `AGG_STALE_12D` | `as_of` 12 days before injected `now` | §5.8 |
| `COMP_SET_N23`, `COMP_SET_N3`, `COMP_SET_N6_CONSTRUCTED` | comparable sets | §5.11, §5.14, §10 |
| `SUBJECT_UNKNOWN_BUILDABILITY` | 3 200 m², gmina Skierniewice, 142 zł/m² | §5.6, §5.13 |
| `MAP_MODEL_TWO_RINGS` | gminas covering thin, all four absence reasons, and well-supported | §6 |
| `listing_pages/<portal>/*.html` + `.expected.json` | recorded pages: m², ar, ha, missing area, changed layout | §9 |
| `dishonest/*.py` | deliberately rule-violating components | §12.2 |

## 12. Sweeps, teeth, and properties

### 12.1 Registry completeness

- `test_registry_covers_every_public_render_helper()` — every public builder in
  `render/` is registered in `COMPONENT_REGISTRY`. Without this, a new component
  ships outside every sweep, which is how the honesty rules would erode.

### 12.2 Proving the sweeps have teeth

Each sweep is paired with a seeded violation in `tests/fixtures/app/dishonest/`
that it **must** flag — a hand-run mutation test for the rendering layer, in the
spirit of V52:

- `test_sweep_flags_an_aggregate_rendered_without_n()`
- `test_sweep_flags_a_range_moved_into_a_hover_container()`
- `test_sweep_flags_a_price_missing_its_kind()`
- `test_sweep_flags_a_blank_where_unknown_belongs()`
- `test_sweep_flags_two_absence_reasons_sharing_one_string()`
- `test_sweep_flags_a_flow_figure_without_its_window()`

A sweep that passes against a deliberately dishonest component is not testing
honesty.

### 12.3 Properties (`tests/unit/app/test_render_properties.py`)

Generated payloads, three relations:

- `test_scaling_every_price_scales_every_rendered_figure_consistently()` — doubling
  prices doubles median, low and high in the rendered text; `n`, labels and notes
  are unchanged.
- `test_adding_an_observation_never_removes_a_qualifier()` — growing `n` may drop a
  thin-data note but never removes `n`, range, price type, kind or window.
- `test_render_is_monotone_in_disclosure()` — no payload produces a tree in which
  `n`, spread, price labels or the out-of-depth notice sit behind a hover or an
  expander.

## 13. Traceability

| Rule / method | Primary test | Falsified by |
|---|---|---|
| U1, V35, V59 | `test_n_and_spread_are_not_inside_a_hover_only_container` | one aggregate rendered bare; a range on hover |
| U2, FR-64, V46 | `test_render_price_rejects_a_price_without_kind` | an auction start price beside an ask, unlabelled |
| U3, V45 | `test_flow_block_precedes_stock_block` | an unlabelled or blended aggregate |
| U4, V62 | `test_flow_window_is_read_from_config_not_hardcoded` | a flow figure with no window; two windows |
| U5 | `test_collapsed_verdict_leaks_no_conclusion_text` | the verdict readable without expanding |
| U6 | `test_no_rendered_text_is_blank_or_a_dash_sweep` | a blank where `unknown` belongs |
| U7 | `test_four_absence_reasons_render_distinct_text` | two reasons sharing "Brak danych" |
| U8, F8 | `test_staleness_node_is_a_sibling_of_the_value_not_a_page_banner` | age in a corner banner |
| U9 | `test_provenance_is_exactly_one_interaction_away` | provenance two clicks deep |
| U10 | `test_thin_aggregate_carries_a_worded_uncertainty_note` | `n=4` shown as numbers only |
| U11 | `test_below_the_comparable_threshold_the_notice_leads` | a confident band on three comparables |
| U12 | `test_export_line_containing_a_number_also_contains_n_and_range` | a screenshot-able bare figure |
| U13 | `test_notes_are_derived_from_the_subject_s_missing_attributes` | a constant, generic caveat |
| U14 | `test_comparable_set_precedes_the_verdict_block` | verdict above the evidence |
| V36 | `test_a_failed_sales_query_does_not_blank_the_offering_block` | one failure blanking unrelated data |
| V37 | `test_protected_terms_are_never_loosely_translated` | *cena ofertowa* as "market price" |
| V51c | `test_exclusion_is_logged_with_subject_comparable_and_change` | exclusion that does not recompute |
| Item 12 | `test_the_four_absence_reasons_and_thin_have_pairwise_distinct_treatments` | "no listings" coloured like "not crawled" |

## 14. Definition of done (`16` §6)

Items 11 and 12 are done when: every test above exists and was written before its
implementation; the sweeps run over the full `COMPONENT_REGISTRY` and flag every
seeded dishonest fixture; the terminology lint reads its protected terms from
`12-glossary.md`; the exclusion log and its report exist with rows produced by a
real exclusion; and `docs/04-validation.md` V59 and V51c can be marked verified
against named tests rather than against a description of intent.
