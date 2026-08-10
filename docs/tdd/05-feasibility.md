# TDD spec — v0 items 14 & 15: parcels, buildings, the good-neighbour test, and the purchasability badge

The test plan for [`18-v0-scope.md`](../18-v0-scope.md) §6 work items **14**
(parcels + buildings + the WZ *dobre sąsiedztwo* test, 3–4 days) and **15**
(farmland purchasability badge, 1 day).

| | |
|---|---|
| **Requirements** | FR-65, FR-66; constrained by FR-14, FR-17, FR-48, FR-53, FR-54, FR-55 |
| **Validation methods** | V60, V61 (specified in [`19`](../19-legal-and-feasibility.md) §1.3 and §2.3), plus V29 and V31 which this item must not break |
| **Decisions** | D46 (WZ route acceptable), D48 (2000–4000 m²), D50, D51, D55, D58 (mutation testing), O17 (missing building data → `unknown`) |
| **Verification tier** ([`20`](../20-verification-strategy.md) §2) | Parcel resolution and projections: **A**. Building/road/protected-area geometry: **B** (ULDK, EGiB, GDOŚ as independent sources). The composite WZ verdict: **C** — human judgement against orthophotos, and it is the *only* tier-C thing v0 still has, because D63 removed the price verdict's judge. The badge's legal content: **B** against the consolidated act |
| **Silent-failure modes touched** ([`20`](../20-verification-strategy.md) §3) | F4 (wrong gmina), plus two new ones registered in §9 below: **F14 unmapped county read as empty countryside**, **F15 superseded legal threshold in shipped copy** |
| **Status of this document** | Written before any code exists. Nothing in items 14–15 may be implemented until every test named here exists and fails for the right reason |

Rule 4 ordering is the spine of this document: **PRD entry → validation method →
failing test → implementation → passing test.** Steps 1 and 2 are already done
(FR-65/FR-66 in [`02-prd.md`](../02-prd.md), V60/V61 in
[`04-validation.md`](../04-validation.md) pointing at
[`19-legal-and-feasibility.md`](../19-legal-and-feasibility.md)). This document is
step 3 and nothing beyond it.

---

## 0. Entry criteria — checked before the first test is written

[`20-verification-strategy.md`](../20-verification-strategy.md) §8 gates the TDD
cycle. Status per criterion:

| # | Criterion | Status |
|---|---|---|
| 1 | PRD requirement or work-plan entry exists | ✅ FR-65, FR-66; `18` §6 items 14, 15 |
| 2 | Validation method exists | ✅ V60, V61 → `19` §1.3, §2.3 |
| 3 | Verification tier assigned | ✅ table above |
| 4 | Silent-failure modes have named detectors | ⚠️ **F14 and F15 are new and must be added to `20` §3 before implementation** — detectors specified in §9 |
| 5 | Fixtures exist, dated, scrubbed | ❌ **Blocking.** The 20-parcel hand-labelled set (§8) does not exist yet. It is the first thing to build, and it is manual work, not code |
| 6 | Metamorphic properties listed (numeric core) | ✅ §3.0 (projection), §6.3 (composite) |

Two of the six are not met. Items 14–15 are **not startable** until the 20-parcel
label set exists and F14/F15 are registered. That is a finding, not a formality:
without the label set, V60 has no ground truth and the composite verdict is
unfalsifiable.

### 0.1 Module map

Test names below refer to these modules, per
[`16-repository-layout.md`](../16-repository-layout.md) §1. None of them exist yet.

```
src/lpc/geo/projections.py            # distance/area kernel — EPSG:2180 compute, 4326 store
src/lpc/ingest/official/uldk.py       # parcel identifier → geometry (pure parse)
src/lpc/ingest/official/egib_buildings.py
src/lpc/ingest/official/osm_buildings.py
src/lpc/ingest/official/gdos.py       # protected areas
src/lpc/enrich/wz/neighbour.py        # developed-neighbour signal
src/lpc/enrich/wz/road.py             # road adjacency + shared-road test
src/lpc/enrich/wz/landuse.py          # register class → de-designation need
src/lpc/enrich/wz/protection.py       # protected-area overlap
src/lpc/enrich/wz/composite.py        # the rule table producing wz_feasibility
src/lpc/enrich/coverage.py            # building_coverage — the F14 detector
src/lpc/legal/citations.py            # dated legal citation record reader
src/lpc/app/render/feasibility.py     # verdict + badge rendering helpers
```

Test files:

```
tests/unit/geo/test_projections.py
tests/unit/wz/test_neighbour.py  test_road.py  test_landuse.py
tests/unit/wz/test_protection.py test_composite.py
tests/unit/legal/test_purchasability_badge.py  test_citations.py
tests/integration/test_uldk_resolution.py  test_wz_pipeline.py
tests/architecture/test_wz_boundaries.py   test_legal_literals.py
tests/labelled/test_wz_known_answers.py    # V60's 10+10 parcels
tests/fixtures/{uldk,egib,osm,gdos,legal}/ # recorded, dated, scrubbed
```

---

## 1. The first test — missing building data yields `unknown`, never `unlikely`

This is written **before every other test in this document**, before the ULDK
client, before the projection kernel, before anything. It is the test the whole
item exists to satisfy, and it is the one that will be under pressure later when
`unknown` looks unhelpful in the UI and someone is tempted to "default sensibly".

> **The claim under test.** Absence of observed buildings in a poorly-mapped county
> is absence of *data*, not absence of *neighbours* (O17, `19` §1.2). A verdict of
> `unlikely` is an assertion about the world. We may only make it when we hold
> positive evidence that the world was actually looked at.

### 1.1 `test_missing_building_data_yields_unknown_not_unlikely`

**File:** `tests/unit/wz/test_neighbour.py` — first test in the file, first test
written for items 14–15.

**Fixture:** `tests/fixtures/egib/county_without_buildings/` — a recorded EGiB WFS
response for a county that publishes parcels but **no** building layer, paired with
a parcel geometry from ULDK inside that county, and an OSM extract for the same
bbox containing zero building ways.

**Contract under test** (signature only — the seam, not the implementation):

```
neighbour_signal(parcel, buildings, coverage) -> NeighbourSignal
    where NeighbourSignal.value ∈ {present, absent, unknown}
```

**Assertions:**

```
assert signal.value == "unknown"
assert signal.value != "absent"
assert composite.verdict == "unknown"
assert composite.verdict != "unlikely"
assert composite.reason_code == "building_data_unavailable"
assert composite.coverage_evidence is None
```

**Red:** fails at import — `src/lpc/enrich/wz/` does not exist. That is the correct
first failure. It must **not** be made to pass by stubbing a constant.

**Green:** the minimum is a `neighbour_signal` that consults a coverage record
before it consults geometry, and returns `unknown` when the coverage record does
not attest that buildings are published and observed for the unit in question.

**Why the reason code is asserted.** `unknown` from *no data* and `unknown` from
*not applicable* are different facts (U7). Without a distinguishing code the UI
cannot say which, and both collapse into an unactionable shrug.

### 1.2 Its three companion tests, in the same commit

A degenerate implementation that returns `unknown` unconditionally passes §1.1.
These three make it non-degenerate. They are written together with §1.1 and none
of the four may be committed alone.

| Test | Assertion | Guards against |
|---|---|---|
| `test_isolated_parcel_with_positive_coverage_is_unlikely` | `verdict == "unlikely"` and `coverage_evidence.buildings_in_control_radius >= config.min_control_buildings` | The always-`unknown` implementation. This is the test that gives §1.1 its teeth |
| `test_zero_buildings_in_control_radius_is_unknown_even_when_source_is_configured` | `verdict == "unknown"`, `reason_code == "coverage_unproven"` | Trusting a county's *presence* in a config list as evidence its tiles are actually populated. A configured source that returns nothing is indistinguishable from an empty landscape unless the map is demonstrably populated nearby |
| `test_osm_fallback_is_marked_lower_confidence_and_cannot_produce_likely` | `signal.source == "osm"` implies `verdict != "likely"`; verdict is at most `uncertain` | An OSM-only county producing an optimistic answer off a hobby-mapped dataset (`19` §1.1 rates OSM "weaker") |

### 1.3 Making it unwritable, not merely untested

A test can be deleted. Following the `unknown_has_no_source` idiom already in
[`15-database-schema.md`](../15-database-schema.md) §7, the rule is also a database
invariant, so a violating row cannot be inserted even by code that never runs a
test. DDL belongs in doc 15; the required invariants are:

| Constraint name | Predicate | States |
|---|---|---|
| `unlikely_requires_coverage_evidence` | `(verdict = 'unlikely') = (coverage_evidence_id IS NOT NULL)` | O17, in the schema |
| `unknown_carries_reason_code` | `(verdict = 'unknown') = (reason_code IS NOT NULL)` | U7 — which kind of unknown |
| `likely_requires_all_conditions` | `(verdict = 'likely') = (neighbour_present AND road_established AND same_road AND NOT needs_dedesignation)` | §6.2's rule table, in the schema |

**`test_unlikely_without_coverage_evidence_is_rejected_by_the_database`**
(`tests/integration/test_wz_pipeline.py`) attempts the insert and asserts an
`IntegrityError` naming `unlikely_requires_coverage_evidence`.

### 1.4 Mutation testing (D58)

`src/lpc/enrich/wz/composite.py` and `neighbour.py` are in the mutation-testing
set. **Required:** mutants that flip `unknown` → `unlikely`, invert the coverage
check, or weaken `>=` to `>` in the control-radius comparison are all killed.
A surviving mutant in the `unknown`/`unlikely` boundary is a release blocker, not
a metric.

---

## 2. Ordering of the whole sequence

Each stage is red before the next stage is written. The order is chosen so that
every stage's failure mode is visible before anything depends on it.

| Stage | What | Depends on | Why here |
|---|---|---|---|
| **R0** | Projection kernel (§3) | — | Every later metre-based assertion is meaningless if metres are wrong. It comes before the data it measures |
| **R1** | ULDK parcel resolution (§4) | R0 | Without a true boundary there is nothing to measure from. §5–§7 all take a parcel geometry |
| **R2** | Building proximity + coverage (§5) | R0, R1 | Written first in *test* order (§1), implemented here in *code* order |
| **R3** | Road adjacency and the shared-road condition (§6.1) | R1, R2 | The WZ condition is a neighbour *on the same public road*; needs both |
| **R4** | Land-use class and de-designation (§6.1) | R1 | Register-only, independent of geometry |
| **R5** | Protected-area overlap (§6.1) | R0, R1 | Caps the verdict; must not be able to produce `unlikely` alone |
| **R6** | Composite rule table (§6.2–6.3) | R2–R5 | Combines only signals that already have tests |
| **R7** | Rendering and disclaimers (§7) | R6 | The verdict cannot reach a screen before the disclaimer test exists |
| **R8** | V60 known-answer set, 10 parcels × 2 rings (§8) | R0–R7 | The acceptance gate for item 14 |
| **R9** | Purchasability badge (§10) — item 15 | R1, R4 | Needs the register class, nothing else |
| **R10** | Legal citation check (§11) | R9 | Item 15 does not ship until the thresholds are verified against the consolidated act |

R7 before R8 is deliberate: V60's falsification list includes *"any UI rendering
without the disclaimer"*, so the rendering rule is a test, not a review note.

---

## 3. R0 — projection correctness (V31, FR-55)

Compute in **EPSG:2180** (PUWG 1992), store in **EPSG:4326**, every geometry
column carries an explicit SRID ([`07`](../07-geocoding.md) §5).

### 3.1 The known-answer test

**`test_known_separation_short_baseline_within_one_metre`**

**Fixture:** `tests/fixtures/geo/known_separation.json` — two points ~300 m apart
near Budy Grabskie, recorded with: coordinates in EPSG:2180 (as published),
coordinates in EPSG:4326, `separation_m` from an independent authority, the tool
and version that produced it, and `retrieved_at`. Provenance is part of the
fixture; an unattributed constant is not ground truth.

```
assert abs(distance_m(a, b) - fixture.separation_m) <= 1.0
```

**`test_known_separation_second_pair_independent_of_the_first`** — a second pair,
different orientation (one baseline predominantly N–S, one E–W), so a transposed
easting/northing passes neither.

### 3.2 The test that computing in degrees would fail it

**`test_degree_space_distance_fails_the_known_answer`**

Asserts the naive computation is *rejected by the same assertion*, so the guard
cannot be neutralised by widening a tolerance:

```
naive = euclidean_in_degrees(a_4326, b_4326)        # ≈ 0.0035, not 300
assert abs(naive - fixture.separation_m) > 100.0    # off by ~10^5
assert not within_tolerance(naive, fixture.separation_m, tol_m=1.0)
```

**`test_distance_helper_rejects_geographic_srid_input`** — calling the metre
kernel with a 4326 geometry raises rather than silently returning degrees.
A wrong number that looks like a number is F1's lesson applied to geometry.

### 3.3 Storage and SRID

- **`test_uldk_geometry_reprojected_once_and_original_retained`** — ULDK's native
  2180 geometry is stored as 4326, the 2180 original is retained, and
  `ST_SRID(geom) == 4326` while `ST_SRID(geom_native) == 2180` (`07` §5).
- **`test_no_geometry_column_lacks_declared_srid`**
  (`tests/architecture/`) — introspects the catalogue; any geometry column with
  SRID 0 fails. Covers tables that do not exist yet, so it keeps holding.
- **`test_round_trip_2180_4326_2180_within_one_centimetre`** — reprojection is not
  quietly lossy.

### 3.4 The tolerance honesty test — a finding, not a formality

V31 says "within 1 m". **PUWG 1992 is a transverse Mercator with a scale factor of
0.9993 on the central meridian; its length distortion reaches roughly ±0.7–0.9 m
per kilometre across Poland.** A 1 m tolerance is therefore achievable at
good-neighbour scale (tens to hundreds of metres) and *not* achievable at ring
scale (25 km, where distortion alone is ~20 m). Silently widening the tolerance
later would hide a real error class behind a real limitation.

- **`test_ring_scale_distance_agrees_with_geodesic_within_documented_budget`** —
  a ~25 km baseline, asserted against the ellipsoidal geodesic within the
  **documented** budget (0.1%), not within 1 m.
- **`test_distance_tolerance_budget_is_declared_per_scale`** — the tolerances are
  read from a single declared table, and the helper refuses a comparison at a
  scale the table does not cover. Prevents "1 m" being quietly redefined.
- **All good-neighbour radii are ≤ 500 m by construction**, so §5's assertions live
  in the regime where 1 m holds.

### 3.5 Metamorphic properties (numeric core, `20` §4.3)

| Property | Test |
|---|---|
| Translation invariance | `test_distance_invariant_under_common_translation` — shifting both points by the same vector changes the distance by < 1 mm |
| Symmetry | `test_distance_is_symmetric` |
| Triangle inequality | `test_distance_satisfies_triangle_inequality` on random triples |
| Area scaling | `test_area_scales_quadratically_under_uniform_scaling` |
| Unit sanity | `test_registry_area_matches_computed_geometry_area_within_tolerance` — ULDK geometry area vs EGiB `registry_area_m2`; a disagreement beyond tolerance flags rather than picks (F2's discipline) |

---

## 4. R1 — parcel resolution via ULDK (FR-14, FR-53)

`19` §1 is only computable for a parcel we actually hold the boundary of.

| Test | Assertion |
|---|---|
| `test_parcel_identifier_pattern_is_parsed` | `146509_8.0201.12/3` → parts `(teryt=146509, R=8, obreb=0201, number=12/3)`; malformed inputs return `None`, never a partial guess (`07` §1) |
| `test_uldk_response_parsed_to_multipolygon_2180` | Pure parse against a recorded fixture; no network in the unit layer (`16` §2 rule 2) |
| `test_uldk_lookup_failure_yields_no_parcel_not_an_empty_geometry` | A 404/empty ULDK response produces absence, not a zero-area polygon that would silently pass downstream area checks |
| `test_parcel_geometry_beats_portal_pin` | FR-14 / `07` §2.1 — pin never overrides parcel |
| `test_wz_not_computed_below_parcel_precision` | For `location_precision ∈ {address, pin, locality, gmina, none}` **no `wz_feasibility` row exists at all** — not `unknown`. Absent ≠ unknown (U7, V29) |
| `test_pin_precision_listing_renders_brak_dokladnej_lokalizacji` | The UI states the location is imprecise rather than showing a feasibility verdict it cannot support (V29) |
| `test_parcel_straddling_gmina_boundary_assigned_by_majority_area_and_flagged` | `07` §4, cross-check with V30 — the gmina drives the comparable set and the badge's legal context |
| `test_registry_area_overrides_advert_area` | V28's conflict rule, re-asserted at the parcel seam: `area_source == "register"` |

**Red for the whole stage:** no `uldk` module. **Green:** a pure parser plus a
thin fetch behind `ingest/http.py`.

---

## 5. R2 — building proximity and the coverage record

§1 already fixed the important half. This stage completes the signal.

| Test | Assertion |
|---|---|
| `test_building_within_radius_of_parcel_boundary_counts` | A building 40 m from the boundary is `present` at radius 100 m |
| `test_distance_measured_from_boundary_not_centroid` | An elongated 3 500 m² parcel with a building 60 m from its nearest edge but 190 m from its centroid is `present` at radius 100 m. A centroid implementation fails |
| `test_radius_is_read_from_configuration_not_hardcoded` | Mirrors V62's rule for the flow window: one configured value, no per-call-site literal. Static check plus a behavioural check that changing config changes the answer |
| `test_radius_value_appears_in_rendered_reason_string` | `19` §1.2 requires *"w promieniu X m"* — the X must be the X actually used |
| `test_building_on_the_subject_parcel_does_not_count_as_a_neighbour` | The condition is *neighbouring* development |
| `test_egib_preferred_over_osm_when_both_available` | `signal.source == "egib"`, and the confidence recorded with it |
| `test_coverage_record_carries_source_as_of_and_observation_count` | Rule 7 provenance on the evidence itself, not only on the verdict |
| `test_stale_coverage_record_degrades_to_unknown` | A coverage record older than the configured max age cannot support `unlikely` (F8 applied to evidence) |
| `test_building_count_is_reported_alongside_the_signal` | Rule 7 "always show, always flag": the verdict ships with `n` neighbours observed and the radius, never as a bare word |

**Sensitivity report, not a test:** `scripts/wz_radius_sensitivity.py` reports the
verdict distribution across radii (50/75/100/150/200 m) over both rings, so the
radius is chosen on evidence rather than guessed — the same treatment O27 gave the
flow window. The chosen value needs a decision-log entry before item 14 ships
(§12, O28).

---

## 6. R3–R6 — the remaining conditions and the composite

### 6.1 The three other signals

**Road adjacency** (`tests/unit/wz/test_road.py`):

| Test | Assertion |
|---|---|
| `test_parcel_sharing_an_edge_with_a_road_parcel_is_adjacent` | Register class `dr`, shared edge, not a single touching vertex |
| `test_single_vertex_contact_is_not_road_adjacency` | Corner-touching is not access |
| `test_road_parcel_of_unknown_ownership_yields_unknown_public_status` | EGiB free data does not give ownership. `public = unknown`, **never** `no access` — the same O17 discipline applied to roads |
| `test_developed_neighbour_on_a_different_road_does_not_satisfy_the_condition` | The WZ condition is a developed neighbour *accessible from the same public road* (`19` §1) |
| `test_shared_road_cannot_be_evaluated_without_road_adjacency` | Signal is `unknown`, and this can only lower the verdict to `uncertain`/`unknown`, never to `unlikely` |
| `test_osm_highway_class_maps_explicitly_and_alarms_on_unmapped_value` | FR-49's discipline: an unmapped classification alarms rather than defaulting |

**Land-use class** (`tests/unit/wz/test_landuse.py`):

| Test | Assertion |
|---|---|
| `test_agricultural_class_flags_dedesignation_requirement` | Parametrized over the register classes in the reference table (§10.1) |
| `test_non_agricultural_class_does_not_flag_dedesignation` | |
| `test_unknown_class_yields_unknown_not_no_requirement` | FR-17 again: silence is not a clean bill of health |
| `test_landuse_never_sourced_from_advert_text` | FR-48 / V25 — an architecture test that `extract` cannot write the register class |
| `test_soil_class_i_to_iii_recorded_as_a_constraint` | FR-18; feeds the badge context and the WZ caveat |

**Protected-area overlap** (`tests/unit/wz/test_protection.py`):

| Test | Assertion |
|---|---|
| `test_parcel_intersecting_natura_2000_is_flagged` | Computed in 2180 (R0), partial overlap counts |
| `test_landscape_park_and_its_otulina_are_distinguished` | Bolimowski PK ring around Budy Grabskie — the buffer zone is a different regime from the park |
| `test_protected_overlap_alone_never_produces_unlikely` | It caps the verdict at `uncertain`. Protection changes the procedure; it does not forbid building, and claiming otherwise is exactly the overreach `19` §1.2 forbids |
| `test_missing_gdos_layer_yields_unknown_overlap_not_absent_overlap` | O17, third application |

### 6.2 The composite rule table (`test_composite.py`)

`wz_feasibility ∈ {likely, uncertain, unlikely, unknown}`. It is a **rule table**,
not a score.

| Test | Assertion |
|---|---|
| `test_unknown_neighbour_signal_is_absorbing` | Any input with `neighbour == unknown` → `unknown`, whatever the other three say. FR-17's terminal `unknown` |
| `test_likely_requires_every_condition_simultaneously` | `likely` only when: neighbour `present` (EGiB source), road adjacency established, neighbour on the same road, no de-designation requirement, no protected overlap. Removing any one drops it to `uncertain` — parametrized over all five removals |
| `test_unlikely_requires_positive_coverage_and_zero_neighbours` | The §1.1 rule restated at the composite seam |
| `test_no_input_combination_produces_a_verdict_outside_the_table` | Exhaustive enumeration of the signal cross-product; every cell has a declared verdict and no cell falls through to a default |
| `test_composite_contains_no_numeric_weights` | Static check: no float literals, no summation of signals. A weighted score would let two weak positives outvote a missing-data `unknown` |
| `test_verdict_carries_its_reason_codes_and_evidence` | Every verdict ships with the signals that produced it, their sources and `as_of` (rule 7) |

### 6.3 Metamorphic properties of the composite

- **`test_verdict_is_independent_of_signal_evaluation_order`** — permuting the
  order of the four signals never changes the verdict.
- **`test_adding_evidence_never_makes_the_verdict_less_certain`** — going from
  `unknown` building data to observed buildings never returns to `unknown`;
  monotonicity in evidence.
- **`test_removing_coverage_evidence_always_moves_unlikely_to_unknown`** — the
  inverse direction, and the property F14's detector leans on.

---

## 7. R7 — rendering: `likely` is the dangerous answer

`19` §1.2, restated because it is the rule most likely to erode: **`likely` never
appears without the same disclaimer as `unlikely`.** The optimistic answer is the
one that would make someone spend money, so it carries the heaviest warning, not
the lightest.

**File:** `tests/unit/app/test_feasibility_render.py`.

| Test | Assertion |
|---|---|
| `test_every_verdict_renders_with_the_disclaimer` | Parametrized over **all four** values including `likely`: output contains *"wstępna ocena — nie jest to gwarancja wydania WZ"* |
| `test_likely_disclaimer_is_byte_identical_to_unlikely_disclaimer` | `render(likely).disclaimer == render(unlikely).disclaimer`. Not "similar", not "also present" — identical, so no one can soften one of them later |
| `test_likely_is_not_rendered_with_affirmative_styling` | No success colour, no ✓, no token from the forbidden set `{"można budować", "zgoda", "gwarancja", "spełnia warunki"}` |
| `test_unlikely_is_phrased_as_an_observation` | Contains *"brak spełnienia warunku dobrego sąsiedztwa w promieniu {radius} m"*; contains none of `{"nie można budować", "odmowa", "nie da się"}` |
| `test_unknown_renders_as_explicit_text_never_blank` | U6; and the reason code is rendered so the user learns *which* unknown |
| `test_disclaimer_is_visible_in_the_collapsed_state` | U5 collapses the verdict; the collapsed row is often all that is read, so the disclaimer sits at the collapsed level, not behind the expander |
| `test_every_render_helper_in_the_registry_emits_the_disclaimer` | **Structural.** Enumerates the module's exported render helpers rather than a hand-listed set, so a helper added in six months fails until it complies. This is the test that makes the rule durable |
| `test_verdict_renders_with_n_source_and_as_of` | Rule 7 — the verdict is an aggregate of evidence and is shown like one |

---

## 8. R8 — V60's known-answer acceptance gate

**File:** `tests/labelled/test_wz_known_answers.py`.
**Label set:** `tests/labelled/wz_parcels.yml` — **10 parcels per ring, 20 total**;
per ring 5 with obvious built neighbours and 5 clearly isolated. Each entry:
parcel identifier, ring, `expected_signal`, the orthophoto tile and date inspected,
the inspector, the inspection date, and a one-line justification. Scrubbed of
anything personal.

| Test | Assertion |
|---|---|
| `test_computed_signal_matches_orthophoto_label_for_every_parcel` | Exact match on all 20. A disagreement fails; it is never downgraded to a warning |
| `test_no_labelled_parcel_with_missing_building_data_is_unlikely` | V60's headline falsifier, run over the real set rather than a fixture |
| `test_all_five_isolated_parcels_per_ring_are_unlikely` | The counterweight — an implementation that answers `unknown` everywhere fails here even though it passes the test above |
| `test_label_set_covers_both_rings_and_both_polarities` | 5/5 per ring; a drifted or truncated label file fails loudly |
| `test_every_label_records_its_orthophoto_date_and_inspector` | Ground truth without provenance is not ground truth |

**Item 14 is not done until all five pass.** Per `16` §6, plus: tests were written
first (this document is the evidence), and the Δ assertions in §9 pass against
real data for both rings.

---

## 9. New silent-failure detectors (to be added to `20` §3)

| # | Silent failure | Why invisible | Detector |
|---|---|---|---|
| **F14** | **An unmapped county reads as empty countryside** — zero buildings returned, verdict `unlikely` | The verdict looks decisive and specific; nothing in the output reveals the map was blank | (a) coverage record required for `unlikely`, enforced by schema constraint (§1.3); (b) **Δ assertion `unlikely_rate_by_county`** — a county whose `unlikely` rate exceeds the ring's by a wide margin alarms; (c) `unknown` rate reported per county on the coverage view (`21` §2.3), so poor mapping shows up as poor mapping |
| **F15** | **Copy cites a superseded legal threshold** | The number is plausible, the page looks authoritative, and the law changed under it | (a) thresholds only from the dated citation record (§11); (b) citation-age test failing the build; (c) scheduled consolidated-text change check that degrades the copy rather than shipping stale numbers |

Δ assertions live in `ops/assertions/` and run in the pipeline, not the test suite
(`16` §4).

---

## 10. R9 — the purchasability badge (item 15, FR-66, V61)

`19` §2.2's rules become tests. **File:**
`tests/unit/legal/test_purchasability_badge.py`.

### 10.1 The register-class reference table

The set of agricultural register classes is **data, not a hardcoded list**:
`config/register_classes.yml`, each row carrying the class symbol, its name, whether
it is a *użytek rolny*, and the regulation and dated consolidated text it came from.

| Test | Assertion |
|---|---|
| `test_every_agricultural_class_produces_the_badge` | Parametrized over **every** row where `is_agricultural` is true (R, S, Ł, Ps, Br, Lzr, W/Wsr, and any other row the table carries). No cherry-picked subset — the parametrisation is generated from the table, so a class added later is automatically covered |
| `test_no_non_agricultural_class_produces_the_badge` | Parametrized over every non-agricultural row, forest (Ls) explicitly among them — forest is restricted under a *different* act and must not borrow this badge's copy |
| `test_register_class_table_rows_all_carry_a_citation` | Symbol, regulation, consolidated-text date. A row without provenance fails |

### 10.2 The unknown class — neither badge nor reassurance

The subtlest requirement in item 15: silence is not a clean bill of health
(`19` §2.2).

| Test | Assertion |
|---|---|
| `test_unknown_class_produces_no_badge` | `render.badge is None` |
| `test_unknown_class_produces_an_explicit_unknown_statement` | Page contains *"klasa użytku nieznana — nie wiemy, czy obowiązują ograniczenia"* (U6) |
| `test_unknown_class_page_contains_no_reassurance_token` | **Whole-page** scan, not just the badge slot: none of `{"brak ograniczeń", "bez ograniczeń", "można kupić", "nie dotyczy"}` appears anywhere in the rendered output. V61's falsifier is a plot *presented* as unrestricted, and presentation is a property of the page |
| `test_missing_null_and_blank_class_are_all_treated_as_unknown` | `None`, `""`, `"   "`, and an unrecognised symbol all take the unknown path; an unrecognised symbol additionally alarms (FR-49's discipline) |

### 10.3 The badge's other rules

| Test | Assertion |
|---|---|
| `test_badge_is_driven_by_register_class_not_advert_claim` | Advert says *"działka budowlana"*, register says `R` → badge present. Advert says *"rolna"*, register says `B` → badge absent. FR-48/V25 |
| `test_badge_states_possibility_never_certainty` | Contains *"możliwe ograniczenia"* and *"możliwe prawo pierwokupu KOWR"*; contains none of `{"nie możesz kupić", "zakaz nabycia", "na pewno", "wymagana zgoda"}` — the determination is the notary's |
| `test_badge_directs_to_a_notary` | Contains *"sprawdź u notariusza przed ofertą"* |
| `test_badge_is_never_a_filter` | A badged plot appears in an unfiltered result set (D51 chose the badge over exclusion); plus an architecture check that no query predicate references the badge |
| `test_badge_shows_area_and_its_source` | *"Grunt rolny — 3 400 m²"* with `area_source == "register"` and the parcel's `as_of` (rule 7, V28) |
| `test_badge_thresholds_come_from_the_citation_record` | No numeric threshold is constructed in the render helper (§11) |
| `test_badge_renders_at_both_ends_of_the_d48_band` | 2 000 m² and 4 000 m² — the sizes that straddle the line `19` §2.1 flags. Both are badged; the *copy* about thresholds comes from §11, not from a rule of thumb baked into code |

---

## 11. R10 — the citation check (V61's second half, F15)

> *"These specifics must be verified against the current consolidated act before the
> badge ships — the law moved in 2026 and secondary sources disagree. That
> verification is part of the work item, not an afterthought."* (`19` §2.1)

The 5 ha / 1 ha threshold and the 30 April 2026 effective date named in `19` §2.1
are **currently unverified secondary-source claims**. They must not reach a screen
until checked against the consolidated text.

### 11.1 The citation record

`config/legal_citations.yml` — one entry per legal claim made in the UI, each with:
`claim_id`, `act_title`, `dziennik_ustaw_reference`, `consolidated_text_id` (ISAP),
`text_as_of`, `value` (the threshold or date), `source_url`, `verified_at`,
`verified_by`, `verification_note`.

| Test | Assertion |
|---|---|
| `test_every_citation_entry_is_complete` | All fields present and non-empty; `verified_at >= text_as_of` |
| `test_no_legal_threshold_literal_appears_outside_the_citation_record` | **Architecture test** (`tests/architecture/test_legal_literals.py`): scans `src/` for `ha`/`hektar` quantities and act-related dates; the only permitted occurrences are the citation reader and fixtures. This is what makes the other citation tests meaningful — a literal in a template routes around all of them |
| `test_rendered_copy_thresholds_equal_the_citation_record_values` | Every number in the badge's legal copy is traceable to a `claim_id` |
| `test_citation_verification_is_not_older_than_the_max_age` | `verified_at` within the configured window of the **build date**. This is the mechanical form of *"on the date shipped"*: an unverified-for-too-long citation **fails the build**, so the badge cannot ship stale |
| `test_citation_older_than_max_age_degrades_copy_rather_than_shipping_it` | When the record is stale, the badge renders without numeric thresholds and with the notary pointer intact — a degraded honest badge, never a confident wrong one |
| `test_every_ui_legal_claim_maps_to_a_claim_id` | No legal sentence in the badge lacks a citation |

### 11.2 The scheduled external check (not CI)

**`test_consolidated_text_identifier_unchanged_since_verification`** —
`tests/drills/`, scheduled per `04-validation.md` §"Every pipeline run"/scheduled
cadence, network-permitted. Fetches the ISAP consolidated-text identifier for the
act and compares with `consolidated_text_id` + `text_as_of`. A change does not
guess at the new content: it marks the entry stale, which trips §11.1's degradation
path and raises an operator task. **Rule 5's "runs on a schedule, not once", applied
to law rather than data.**

### 11.3 The manual verification procedure

Recorded in `scripts/verify_legal_citations.md` (a written check, per rule 5's
allowance): open the consolidated text at ISAP, locate the article, record the
threshold, the effective date and the transitional provisions, and update
`verified_at`/`verified_by`. **Item 15 is not done until this has been performed at
least once and the record reflects it** — no test can substitute for reading the act.

---

## 12. Assumptions and open questions — flagged, not absorbed

Rule 2 forbids resolving ambiguity by assumption. These arose while writing this
spec and are **unresolved**; each needs an answer (and a decision-log entry) before
the stage that depends on it. They are listed here rather than silently defaulted.

| # | Question | Blocks | Provisional treatment |
|---|---|---|---|
| **O28** | **Good-neighbour radius.** `19` §1 says "within a radius" without a value | R2, and every §5 assertion | Configuration-driven with a sensitivity report (§5); the shipped value needs ratification, like O27's flow window |
| **O29** | **Control-radius and minimum-count parameters** for the coverage probe (proposed ~2 km / ≥K buildings) | R2, F14's detector | Configuration-driven; the 20-parcel set (§8) is the arbiter of whether the values separate "isolated" from "unmapped" |
| **O30** | **Citation max age** — how stale may a legal verification be before the build fails? (a quarter? a month?) | R10 | Configuration-driven; must be short enough that a 2026-style change is caught |
| **O31** | **`19` §2.1's legal specifics are unverified.** The 1 ha → 5 ha change and the 30 April 2026 date come from secondary sources that `19` itself says disagree | Item 15 shipping | Treated as unverified throughout §11; no test in this document asserts those values as true |
| **O32** | **Doc 15 has no tables for buildings, coverage or `wz_feasibility`.** `parcel_zoning`, `parcel_constraint`, `parcel_nature` exist; items 14–15 need `parcel_building`, `building_coverage` and `parcel_wz_feasibility` | R2 onwards | §1.3 states the required invariants; the DDL belongs in [`15-database-schema.md`](../15-database-schema.md) and should be added there before R2 |
| **O33** | **Does the badge apply to forest (`Ls`)?** Forest sale is restricted under the *ustawa o lasach*, a different act with a different pre-emption holder (State Forests, not KOWR) | R9 | §10.1 tests assert forest gets **no** farmland badge. Whether it deserves its *own* badge is out of scope for item 15 and needs a PRD entry if wanted |

---

## 13. Coverage summary

| Requirement / method | Tests |
|---|---|
| **FR-65**, V60 | §1.1–1.4, §5, §6.1–6.3, §7, §8 |
| **FR-66**, V61 | §10.1–10.3, §11 |
| **FR-55**, V31 | §3.1–3.5 |
| **FR-53**, V29 | §4 (`test_wz_not_computed_below_parcel_precision`) |
| **FR-17** terminal `unknown` | §1.1, §6.1 (roads, land use, protection), §6.2 absorbing rule |
| **FR-48** register over advert | §6.1, §10.3 |
| **FR-14** parcel over pin | §4 |
| **Rule 7** always show, always flag | §5 (`n` + radius with the signal), §7, §10.3 |
| **D58** mutation testing | §1.4 |
