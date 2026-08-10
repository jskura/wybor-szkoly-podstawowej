# TDD spec — v0 items 14 & 15: parcels, buildings, the good-neighbour test, and the purchase-restriction badges

The test plan for [`18-v0-scope.md`](../18-v0-scope.md) §6 work items **14**
(parcels + buildings + the WZ *dobre sąsiedztwo* test, 3–4 days) and **15**
(purchase-restriction badges, 1 day + 1 day for the forest badge added by D106).

| | |
|---|---|
| **Requirements** | FR-65, FR-66, **FR-73** (forest badge, D106), **FR-74** (re-verification prompt, D104/D105); constrained by FR-14, FR-17, FR-48, FR-53, FR-54, FR-55 |
| **Validation methods** | V60, V61 (specified in [`19`](../19-legal-and-feasibility.md) §1.3 and §2.3), **V63** (badges never cross), **V64** (re-verification prompt), plus V29 and V31 which this item must not break |
| **Decisions** | D46 (WZ route acceptable), D48 (2000–4000 m²), D50, D51, D55, D58 (mutation testing), **D102** (radius configurable), **D103** (coverage-probe values configurable), **D104/D105** (no expiry, prompt instead), **D106** (forest gets its own badge), O17 (missing building data → `unknown`) |
| **Verification tier** ([`20`](../20-verification-strategy.md) §2) | Parcel resolution and projections: **A**. Building/road/protected-area geometry: **B** (ULDK, EGiB, GDOŚ as independent sources). The composite WZ verdict: **C** — human judgement against orthophotos, and it is the *only* tier-C thing v0 still has, because D63 removed the price verdict's judge. Each badge's legal content: **B** against its own consolidated act |
| **Silent-failure modes touched** ([`20`](../20-verification-strategy.md) §3) | F4 (wrong gmina), plus three new ones registered in §9 below: **F14 unmapped county read as empty countryside**, **F15 superseded legal threshold in shipped copy**, **F16 badge naming the wrong act and the wrong authority** |
| **Status of this document** | Written before any code exists. Nothing in items 14–15 may be implemented until every test named here exists and fails for the right reason |

**Item 15 now carries two badges, not one.** D106 gives forest land its own badge.
Forest sale falls under a different act with a different pre-emption holder, so the
farmland badge would name the wrong law and the wrong authority. The forest badge is
specified in §12. Its legal content is **unverified**, exactly as the farmland one
is (§11).

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
| 1 | PRD requirement or work-plan entry exists | ✅ FR-65, FR-66, FR-73, FR-74; `18` §6 items 14, 15 |
| 2 | Validation method exists | ✅ V60, V61 → `19` §1.3, §2.3; V63, V64 in `04` |
| 3 | Verification tier assigned | ✅ table above |
| 4 | Silent-failure modes have named detectors | ⚠️ **F14, F15 and F16 are new and must be added to `20` §3 before implementation** — detectors specified in §9 |
| 5 | Fixtures exist, dated, scrubbed | ❌ **Blocking.** The 20-parcel hand-labelled set (§8) does not exist yet. It is the first thing to build, and it is manual work, not code |
| 6 | Metamorphic properties listed (numeric core) | ✅ §3.0 (projection), §6.3 (composite) |
| 7 | Legal copy exists for every badge | ❌ **Blocking for §12 only.** `19` carries the farmland copy in §2.2. It carries **no forest section at all**. Doc 19 needs a forest section before R11 is typed |

Three of the seven are not met. Items 14–15 are **not startable** until the
20-parcel label set exists and F14/F15/F16 are registered. That is a finding, not a
formality: without the label set, V60 has no ground truth and the composite verdict
is unfalsifiable.

**The label set does three jobs now, not one.** It is V60's ground truth. D102 also
makes it the arbiter of the shipped good-neighbour radius, and D103 makes it the
arbiter of the coverage-probe values. All three jobs need the same 20 parcels, so
the cost does not rise. The dependency does: a wrong label set now moves a shipped
parameter, not only a test result.

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
src/lpc/legal/regime.py               # register class → regime {agricultural, forest, none}
src/lpc/app/render/feasibility.py     # verdict rendering helpers
src/lpc/app/render/purchase_badge.py  # both badges, one per regime (D106)
src/lpc/app/reverification.py         # once-per-session prompt (D105)
```

Test files:

```
tests/unit/geo/test_projections.py
tests/unit/wz/test_neighbour.py  test_road.py  test_landuse.py
tests/unit/wz/test_protection.py test_composite.py
tests/unit/legal/test_purchasability_badge.py  test_citations.py
tests/unit/legal/test_forest_badge.py      # D106, FR-73
tests/unit/legal/test_badge_regimes.py     # V63 — the two badges never cross
tests/unit/app/test_reverification_prompt.py   # D105, FR-74, V64
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

> **Read this before you set the coverage-probe values (D103).** The control radius
> and the minimum building count decide whether we call a place *genuinely isolated*
> or *not mapped*. Set them wrong and the code produces the exact error the `unknown`
> verdict exists to prevent. A control radius that is too small, or a count that is
> too high, turns a well-mapped quiet area into `unknown` and wastes the feature. A
> count that is too low turns a blank map into `unlikely` and states a fact about the
> world that nobody observed. **The second failure is the one that reaches a user as
> a confident wrong answer.** Both values live in configuration, and the 20-parcel
> labelled set (§8) decides them. §5 carries the tests.

### 1.3 Making it unwritable, not merely untested

A test can be deleted. Following the `unknown_has_no_source` idiom already in
[`15-database-schema.md`](../15-database-schema.md) §7, the rule is also a database
invariant, so a violating row cannot be inserted even by code that never runs a
test. **The tables now exist** — doc 15 carries `parcel_building`,
`building_coverage` and `parcel_wz_feasibility`. This document states what the
invariants must do; doc 15 owns the DDL.

| Constraint | Predicate | States | In doc 15 today |
|---|---|---|---|
| `unlikely_requires_coverage` | `verdict <> 'unlikely' OR coverage_source IS NOT NULL` | O17 | ✅ shipped |
| `unknown_carries_reason_code` | `reason_code IS NOT NULL` on every row | U7 — which kind of unknown | ✅ shipped as `reason_code TEXT NOT NULL`, which is stronger: every verdict carries its reason, not only `unknown` |
| `likely_requires_all_conditions` | `(verdict = 'likely') = (neighbour_found AND shares_road AND land_use_class is non-agricultural AND protection_kind IS NULL)` | §6.2's rule table | ❌ not present; §6.2's tests carry it until it is |

**Pass 1 was wrong about the first one, and the schema is right.** An earlier draft
asked for a biconditional: `(verdict = 'unlikely') = (evidence IS NOT NULL)`. That
forbids a `likely` verdict from recording the coverage evidence it also relied on.
The implication is the correct shape. The test plan found this; the correction lands
here.

`parcel_building` stores the distance as **`distance_mm BIGINT`**, in millimetres.
An `INT` in metres made `30.000` and `30.4` indistinguishable and put the plan's
millimetre tolerances out of reach of any test that reads the database. Every
assertion in §5 that names a distance reads `distance_mm` and divides by 1 000.

**`test_unlikely_without_coverage_evidence_is_rejected_by_the_database`**
(`tests/integration/test_wz_pipeline.py`) attempts the insert and asserts an
`IntegrityError` naming `unlikely_requires_coverage`.

**`test_distance_is_stored_in_millimetres_not_metres`** — writes a building at
30.0004 m, reads back `distance_mm == 30000`, and asserts the column type is not an
integer count of metres. A round trip that loses the millimetre fails.

### 1.4 Mutation testing (D58)

`src/lpc/enrich/wz/composite.py` and `neighbour.py` are in the mutation-testing
set. **Required:** mutants that flip `unknown` → `unlikely`, invert the coverage
check, or weaken `>=` to `>` in the control-radius comparison are all killed.
A surviving mutant in the `unknown`/`unlikely` boundary is a release blocker, not
a metric.

`src/lpc/legal/regime.py` joins the set when R11 lands. **Required:** a mutant that
maps the forest regime to the agricultural one, or that returns a constant regime,
is killed. That mutant is F16 in one line of code.

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
| **R9** | Farmland badge (§10) — item 15 | R1, R4 | Needs the register class, nothing else |
| **R10** | Legal citation check (§11) | R9 | Item 15 does not ship until the thresholds are verified against the consolidated act |
| **R11** | Forest badge (§12) — item 15, added by D106 | R9, R10 | Reuses the register class, the citation record and the regime table. It follows the farmland badge so the crossing tests have both sides to compare |
| **R12** | Re-verification prompt (§13) — FR-74 | R9, R11 | D104 removes the expiry, so the prompt is the only thing left that catches a changed law. It comes last because it needs a badge to trigger on |

R7 before R8 is deliberate: V60's falsification list includes *"any UI rendering
without the disclaimer"*, so the rendering rule is a test, not a review note.

R11 after R10 is also deliberate. The forest badge's act and pre-emption holder come
from the citation record, never from a literal in the render helper. Building the
record first makes the wrong-authority failure (F16) structurally hard rather than
merely tested.

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
different orientation (one baseline predominantly N–S, one E–W). The two
orientations catch a wrong metres-per-degree constant, which is right north–south
and 62 % wrong east–west (test plan §3.3).

**The two orientations do not catch a transposition. I said they did, and I was
wrong.** Swapping `(E, N) → (N, E)` reflects the plane about the line E = N.
Reflections are isometries. If the pipeline transposes *both* points, every pairwise
distance survives exactly, at every orientation and at every scale. A consistently
transposed pipeline passes every distance assertion in this document.

Only an **absolute** assertion catches it. Distance is a relative quantity, so no
number of distance tests can do the job.

| Test | Assertion |
|---|---|
| `test_reprojected_point_matches_the_recorded_4326_coordinates` | Reproject each fixture point from 2180 and compare against the recorded 4326 values, ≤ 1e-7° (about 1 cm). This is the primary absolute check: it pins where the point *is*, not how far it is from another point |
| `test_parcel_falls_inside_its_declared_gmina` | The parcel geometry lies inside the boundary of the gmina its identifier names. A transposed parcel keeps its shape and its size, and lands somewhere else. Containment fails; distance does not |
| `test_ordinate_order_is_easting_first` | The first ordinate of every stored 2180 geometry falls in the easting range for Poland, and the second in the northing range. The two ranges do not overlap, so a transposition is detectable per coordinate |
| `test_distance_is_invariant_under_transposition_and_this_is_why_containment_is_required` | Asserts the invariance **deliberately**, and carries the comment that records why the two tests above cannot be deleted |

The last test looks perverse and matters most. It puts the hole in the obvious
approach into the suite, where the next person meets it before repeating my mistake.

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
| `test_radius_is_read_from_configuration_not_hardcoded` | D102. Mirrors V62's rule for the flow window: one configured value, no per-call-site literal. Static check plus a behavioural check that changing config changes the answer |
| `test_coverage_probe_values_are_read_from_configuration_not_hardcoded` | D103, same shape, for `control_radius_m` and `min_control_buildings` |
| `test_radius_value_appears_in_rendered_reason_string` | `19` §1.2 requires *"w promieniu X m"* — the X must be the X actually used |
| `test_building_on_the_subject_parcel_does_not_count_as_a_neighbour` | The condition is *neighbouring* development |
| `test_egib_preferred_over_osm_when_both_available` | `signal.source == "egib"`, and the confidence recorded with it |
| `test_coverage_record_carries_source_as_of_and_observation_count` | Rule 7 provenance on the evidence itself, not only on the verdict |
| `test_stale_coverage_record_degrades_to_unknown` | A coverage record older than the configured max age cannot support `unlikely` (F8 applied to evidence) |
| `test_building_count_is_reported_alongside_the_signal` | Rule 7 "always show, always flag": the verdict ships with `n` neighbours observed and the radius, never as a bare word |

### 5.1 The three configured parameters, and how the shipped values are chosen

D102 and D103 settle the shape: the good-neighbour radius, the control radius and
the minimum control count are **configuration**, and the 20-parcel labelled set
(§8) arbitrates the values we ship.

| Parameter | Decision | Config key |
|---|---|---|
| Good-neighbour radius | D102 | `wz.good_neighbour_radius_m` |
| Coverage control radius | D103 | `wz.control_radius_m` |
| Minimum buildings in the control radius | D103 | `wz.min_control_buildings` |

**Sensitivity report, not a test:** `scripts/wz_radius_sensitivity.py` reports the
verdict distribution across radii (50/75/100/150/200 m) over both rings, and the
verdict distribution across the coverage-probe grid. The report is the evidence
D102 asks for — the same treatment O27 gave the flow window.

| Test | Assertion |
|---|---|
| `test_shipped_radius_agrees_with_the_labelled_set` | Run the neighbour signal at the configured radius over the 20 labelled parcels. Agreement with the labels is at least as high as at every other radius on the sweep. A radius that loses to a neighbouring value on the sweep fails, and the failure names both values |
| `test_shipped_coverage_probe_values_agree_with_the_labelled_set` | The same test for the probe grid, scored on the 10 isolated parcels. **A wrong value here reproduces the error `unknown` exists to prevent** (§1.2), so the assertion is on the isolated half, where the error appears |
| `test_sensitivity_report_covers_the_shipped_value` | The report's sweep contains the configured value. A value outside the sweep has no evidence behind it and fails |
| `test_configured_values_are_recorded_with_their_evidence` | Each of the three keys carries the report run date and the label-set version that chose it (rule 7 applied to a parameter) |

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
| **F15** | **Copy cites a superseded legal threshold** | The number is plausible, the page looks authoritative, and the law changed under it | (a) thresholds only from the dated citation record (§11); (b) the scheduled consolidated-text change check, which marks the entry stale and degrades the copy rather than shipping stale numbers; (c) the re-verification prompt (§13), which D105 puts in place of an expiry date |
| **F16** | **A badge names the wrong act and the wrong authority** — the farmland badge renders on forest land, or either badge cites the other's act or pre-emption holder | The badge looks exactly as authoritative as a correct one. The user reads a real act name and a real authority, and both are the wrong ones for the land in front of them. Nothing in the page reveals the substitution | (a) the regime is data, from the register class table, never a branch in a render helper (§12.1); (b) the act title and the holder render from the citation record keyed by regime, so a helper cannot name them at all (§12.2); (c) the crossing tests of §12.3, which assert each page contains the other regime's act and holder **nowhere**; (d) Δ assertion `badge_regime_mismatch` over stored `parcel_purchase_restriction` rows |

Δ assertions live in `ops/assertions/` and run in the pipeline, not the test suite
(`16` §4).

---

## 10. R9 — the farmland badge (item 15, FR-66, V61)

`19` §2.2's rules become tests. **File:**
`tests/unit/legal/test_purchasability_badge.py`.

### 10.1 The register-class reference table, keyed by regime

The register classes are **data, not a hardcoded list**:
`config/register_classes.yml`, each row carrying the class symbol, its name, its
**regime**, and the regulation and dated consolidated text it came from.

**D106 replaces the boolean with a regime.** The table used to carry
`is_agricultural: true | false`. A boolean has two states and the product now has
three: farmland, forest, and neither. A boolean cannot say *"restricted, under the
other act"*, so it forces forest into the same cell as a housing plot. The column
becomes `regime ∈ {agricultural, forest, none}`, which matches
`parcel_purchase_restriction.regime` in doc 15 exactly.

| Test | Assertion |
|---|---|
| `test_badge_presence_and_regime_follow_the_table` | Parametrized over **every** row. The rendered badge's regime equals the row's regime, and a row with regime `none` renders no badge. The parametrisation is generated from the table, so a class added later is covered on the day it is added |
| `test_every_agricultural_class_produces_the_farmland_badge` | Every row with regime `agricultural` (R, S, Ł, Ps, Br, Lzr, W, Wsr, and any other such row) |
| `test_no_row_outside_the_agricultural_regime_produces_the_farmland_badge` | Every row with regime `forest` or `none`. **`Ls` is now a `forest` row, not a `none` row** — it still gets no farmland badge, and it now gets a badge of its own (§12) |
| `test_regime_column_accepts_only_the_three_declared_values` | A typo such as `agricutural` fails the table load rather than silently reading as "no regime" |
| `test_register_class_table_rows_all_carry_a_citation` | Symbol, regulation, consolidated-text date. A row without provenance fails |

**Superseded.** An earlier version of this document asserted
`test_no_non_agricultural_class_produces_the_badge` with forest listed among the
rows that get **no badge at all**. D106 makes that assertion wrong. Forest gets no
*farmland* badge and does get a *forest* badge. A test suite that still asserts the
old rule blocks the correct behaviour, so it is replaced, not extended.

### 10.2 The unknown class — neither badge nor reassurance

The subtlest requirement in item 15: silence is not a clean bill of health
(`19` §2.2).

| Test | Assertion |
|---|---|
| `test_unknown_class_produces_no_badge` | `render.badge is None` |
| `test_unknown_class_produces_an_explicit_unknown_statement` | Page contains *"klasa użytku nieznana — nie wiemy, czy obowiązują ograniczenia"* (U6) |
| `test_unknown_class_page_contains_no_reassurance_token` | **Whole-page** scan, not just the badge slot: none of `{"brak ograniczeń", "bez ograniczeń", "można kupić", "nie dotyczy"}` appears anywhere in the rendered output. V61's falsifier is a plot *presented* as unrestricted, and presentation is a property of the page |
| `test_missing_null_and_blank_class_are_all_treated_as_unknown` | `None`, `""`, `"   "`, and an unrecognised symbol all take the unknown path; an unrecognised symbol additionally alarms (FR-49's discipline) |

### 10.3 The farmland badge's other rules

| Test | Assertion |
|---|---|
| `test_badge_is_driven_by_register_class_not_advert_claim` | Advert says *"działka budowlana"*, register says `R` → badge present. Advert says *"rolna"*, register says `B` → badge absent. FR-48/V25 |
| `test_farmland_badge_names_the_holder_recorded_for_its_regime` | The rendered pre-emption line names the holder that the citation record carries for regime `agricultural`. The copy in `19` §2.2 spells KOWR out, so the literal and the record must not drift apart. A mismatch fails and names both values |
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
until checked against the consolidated text. The same holds for every forest claim
in §12, which nobody has checked either.

The record serves **both** regimes. One reader, one schema, two sets of claims,
keyed by regime.

### 11.1 The citation record

`config/legal_citations.yml` — one entry per legal claim made in the UI, each with:
`claim_id`, **`regime`** (`agricultural` or `forest`), `act_title`,
`preemption_holder`, `dziennik_ustaw_reference`, `consolidated_text_id` (ISAP),
`text_as_of`, `value` (the threshold or date), `source_url`, `verified_at`,
`verified_by`, `verification_note`.

| Test | Assertion |
|---|---|
| `test_every_citation_entry_is_complete` | All fields present and non-empty; `verified_at >= text_as_of` |
| `test_every_citation_entry_declares_its_regime` | `regime ∈ {agricultural, forest}`. An entry with no regime cannot be routed to a badge, and an entry with the wrong one is F16 |
| `test_no_legal_threshold_literal_appears_outside_the_citation_record` | **Architecture test** (`tests/architecture/test_legal_literals.py`): scans `src/` for `ha`/`hektar` quantities, act-related dates, act titles and the two pre-emption holder names. The only permitted occurrences are the citation reader and fixtures. This is what makes the other citation tests meaningful — a literal in a template routes around all of them |
| `test_rendered_copy_thresholds_equal_the_citation_record_values` | Every number in either badge's legal copy is traceable to a `claim_id` |
| `test_every_ui_legal_claim_maps_to_a_claim_id` | No legal sentence in either badge lacks a citation |
| `test_stale_citation_degrades_copy_rather_than_shipping_it` | When §11.2's check marks an entry stale, the badge renders without numeric thresholds and with the notary pointer intact — a degraded honest badge, never a confident wrong one |

### 11.1a No expiry date, a prompt instead (D104, D105)

**D104 removes the staleness clock.** An earlier version of this document had
`test_citation_verification_is_not_older_than_the_max_age` fail the build once
`verified_at` passed a configured window, and O30 asked how long the window should
be. There is no good answer. A window that is short enough to catch a real change
fails the build on a quiet law, and a window long enough to be quiet catches
nothing. Worse, the clock measures our own habits, not the law: nothing about the
date we last read the act tells us the act changed.

D105 puts the check where the risk is. **The first time a purchase-restriction badge
appears in a session, the application prompts for re-verification.** No badge, no
prompt, no standing cost. §13 specifies it and carries its tests.

| Test | Assertion |
|---|---|
| `test_citation_record_declares_no_expiry` | The record schema carries no `expires_at`, no `max_age_days` and no equivalent. A reintroduced expiry field fails, so D104 cannot be undone by a quiet config addition |
| `test_verified_at_is_reported_not_enforced` | `verified_at` renders in the prompt (§13) and gates nothing. A stale-looking date never fails the build and never hides a badge |

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
least once for each act and the record reflects it** — no test can substitute for
reading the act. Two badges mean two acts and two separate readings. The forest act
is not a variation of the farmland one, and a single pass over one act verifies
nothing about the other.

---

## 12. R11 — the forest badge (item 15, FR-73, V63, D106)

**New scope.** D106 gives forest land its own badge. **File:**
`tests/unit/legal/test_forest_badge.py`, with the crossing tests in
`tests/unit/legal/test_badge_regimes.py`.

### 12.0 Why a second badge and not a wider first one

Forest sale falls under a **different act** with a **different pre-emption holder**.
The farmland badge names the *ustawa o kształtowaniu ustroju rolnego* and KOWR.
Rendering it on a forest parcel states two facts, and both are wrong: the wrong law
and the wrong authority. That is worse than saying nothing, because the user acts on
it. They telephone the wrong office, or they price in a pre-emption risk that the
wrong body holds.

The alternative — one badge with softer wording that covers both — fails the same
way from the other side. A badge that names no act and no holder tells the user
nothing they can check, and rule 7's *always show, always flag* asks for the
opposite.

So: two badges, two regimes, two citation entries. The register class picks the
regime, and the regime picks everything else.

### 12.1 The regime is data, not a branch

`src/lpc/legal/regime.py` reads `config/register_classes.yml` (§10.1) and returns
the regime. It contains no class symbol as a literal.

| Test | Assertion |
|---|---|
| `test_forest_class_resolves_to_the_forest_regime` | `Ls` → `forest`, read from the table |
| `test_regime_module_contains_no_class_symbol_literal` | **Architecture test.** No `"Ls"`, `"R"` or any other symbol appears in `src/lpc/legal/`. A branch on a symbol is how the wrong regime gets hardcoded and then outlives the table |
| `test_render_helper_receives_a_regime_never_a_class_symbol` | The badge helper's signature takes the regime. It cannot re-derive a regime, so it cannot re-derive it wrongly |

### 12.2 The forest badge's copy — and what does not exist yet

The badge takes the same four-line shape as the farmland one:

```
⚠ Grunt leśny — 3 400 m²
   Możliwe ograniczenia w nabyciu ({act_title})
   Możliwe prawo pierwokupu ({holder})
   → sprawdź u notariusza przed ofertą
```

**`{act_title}` and `{holder}` are not literals. They render from the citation
record entry for regime `forest`.** A render helper physically cannot name KOWR,
because it never holds a holder name at all. That is F16's detector (b), and it is
the difference between a rule that is tested and a rule that is hard to break.

> **This copy is proposed here, not ratified, and doc 19 does not carry it.**
> `19` has §2 for farmland and **no forest section at all**. Entry criterion 7 (§0)
> is therefore unmet for R11. Before R11 is typed, doc 19 needs a forest section
> holding the copy, and the copy needs a decision entry the way `19` §2.2's did.
> The strings below are what this document proposes; the test plan carries their
> hashes so a change to the text shows up as a changed hash rather than a silent
> edit.

| Test | Assertion |
|---|---|
| `test_forest_badge_renders_for_the_forest_regime` | `Ls` → badge present, regime `forest` |
| `test_forest_badge_act_and_holder_come_from_the_citation_record` | Both strings equal the record's values for regime `forest`. Change the record, and the rendered text changes with it |
| `test_forest_badge_states_possibility_never_certainty` | Contains *"Możliwe ograniczenia"* and *"Możliwe prawo pierwokupu"*; contains none of `{"nie możesz kupić", "zakaz nabycia", "na pewno", "wymagana zgoda"}`, matched case-insensitively |
| `test_forest_badge_directs_to_a_notary` | Renders `BADGE_NOTARY_LINE`, the same constant the farmland badge uses. One notary line, shared, because the advice is identical and two copies would drift |
| `test_forest_badge_shows_area_and_its_source` | *"Grunt leśny — 3 400 m²"* with `area_source == "register"` and the parcel's `as_of` (rule 7, V28) |
| `test_forest_badge_is_never_a_filter` | A forest-badged plot appears in an unfiltered result set, and no query predicate references the badge (D51's rule, applied to the second regime) |

### 12.3 The crossing tests — V63, and the reason this section exists

These matter more than the presence tests. A missing badge is a gap. A badge naming
the wrong authority is a false statement that looks authoritative.

| Test | Assertion |
|---|---|
| `test_forest_page_contains_no_farmland_act_or_holder` | **Whole-page** scan: the forest page contains neither the farmland act title nor `KOWR`, anywhere, after HTML tag stripping |
| `test_farmland_page_contains_no_forest_act_or_holder` | The same in the other direction |
| `test_the_two_badges_never_appear_together` | For every register class in the table, the page carries at most one purchase-restriction badge. A parcel has one register class and therefore one regime |
| `test_no_badge_renders_for_the_none_regime` | Rows with regime `none` render neither badge, and no statement about acquisition at all (§10.2's rule, restated for two badges) |
| `test_swapping_the_regime_swaps_the_whole_badge` | Render `Ls` and `R` with the same area and the same `as_of`. The act, the holder and the title line all differ; only the notary line is shared. A helper that varies one field and not the others fails |
| `test_seeded_crossed_badge_is_caught` | A deliberately broken render module, forest badge wired to the agricultural citation entry, makes the suite fail. Without it, the scans above could be vacuous |

### 12.4 The forest badge's legal content is unverified

Exactly as unverified as the farmland one, and stated with the same plainness. The
act title, the pre-emption holder, the scope of the pre-emption and any threshold
are **secondary-source claims that nobody on this project has checked against a
consolidated text.** Doc 15's comment names State Forests as the holder; that is a
starting point for the verification, not the result of one.

Consequence: §11's degraded form is the **only** form the forest badge may render
today. It states that restrictions and a pre-emption right are possible, names the
act and the holder from the record, points at a notary, and makes no numeric claim.

| Test | Assertion |
|---|---|
| `test_forest_claims_are_marked_unverified_in_the_record` | Every forest `claim_id` carries `verified_at: null` and a `verification_note` saying it is unread. A forest entry that claims verification without §11.3 having run fails |
| `test_unverified_forest_citations_render_the_degraded_badge` | The badge renders, keeps all four lines, and contains no digit outside the area figure |
| `test_degraded_forest_badge_is_not_silently_weaker` | The degraded and verified forms are identical except for the threshold sentence. A degraded badge must not also lose its warning |

---

## 13. R12 — the re-verification prompt (FR-74, V64, D104/D105)

**File:** `tests/unit/app/test_reverification_prompt.py`.

D104 leaves the legal content with no expiry. On its own that means nothing ever
tells us the law moved. D105 supplies the missing half: **the first time a
purchase-restriction badge appears in a session, the application prompts to
re-verify.**

The prompt is not a warning to the user about the plot. It is a task addressed to
the operator, shown at the moment the legal content is actually in use.

| Test | Assertion |
|---|---|
| `test_first_badge_in_a_session_shows_the_prompt` | Fresh session, render one badge, exactly one prompt appears |
| `test_second_badge_in_the_same_session_shows_no_prompt` | Render two badges in one session, exactly one prompt. Once per session, not once per badge — a prompt on every badge trains the reader to dismiss it, which is how a real change slips through |
| `test_a_new_session_prompts_again` | The counter lives in session state, not in a module global and not on disk. A second session prompts |
| `test_a_session_with_no_badge_shows_no_prompt` | The whole point of D105: no standing cost. A session that never renders a badge never prompts |
| `test_prompt_names_the_act_and_the_last_verification_date` | V64's third clause. The prompt renders the `act_title` and `verified_at` of the regime that triggered it. A prompt that says only "check the law" names no task |
| `test_prompt_names_the_forest_act_when_a_forest_badge_triggers_it` | Both regimes can trigger the prompt, and the prompt names the one in front of the user |
| `test_prompt_never_blocks_the_badge` | The badge renders whether the prompt is dismissed or not. The prompt is a task, never a gate — a gate would recreate the expiry D104 removed |
| `test_prompt_text_comes_from_one_declared_constant` | The same discipline as the disclaimer (§7): one constant, hash-asserted, no second copy in `src/` |

### 13.1 One open point, raised rather than settled

V64 says *purchase-restriction badge*, not *farmland badge*, so either regime
triggers the prompt. That leaves a residue: a session that shows a farmland badge
first and a forest badge later prompts **only for the farmland act**. The forest
act's verification date never reaches the reader in that session.

Two answers are defensible. Prompt once per session, as V64 says, and accept the
gap. Or prompt once per **regime** per session, at most twice. **I do not know which
you want, and I have not chosen.** The tests above encode V64 as written, once per
session. §14 carries the question.

---

## 14. Assumptions and open questions — flagged, not absorbed

Rule 2 forbids resolving ambiguity by assumption. Batch 21 answered six of the seven
questions this spec raised. The answers and their consequences are recorded first;
the questions that remain follow.

### 14.1 Answered by batch 21

| Was | Question | Answer | Where it lands in this document |
|---|---|---|---|
| **O28** | Good-neighbour radius | **D102** — configuration, with a sensitivity report; the 20-parcel labelled set arbitrates the shipped value | §5.1's parameter table and its four tests; §0 records the label set's new role |
| **O29** | Coverage-probe values | **D103** — configuration, decided by the same labelled set | §1.2's boxed warning and §5.1. Getting these wrong reproduces the exact error `unknown` exists to prevent, so the warning sits next to the first test, not in an appendix |
| **O30** | Citation max age | **D104** — there is no expiry | §11.1a. The build-failing age test is deleted, and `test_citation_record_declares_no_expiry` stops it coming back |
| — | What replaces the expiry? | **D105** — prompt on the first badge in a session | §13, and FR-74 in the PRD |
| **O32** | Missing schema tables | Closed — `parcel_building`, `building_coverage` and `parcel_wz_feasibility` now exist in doc 15 | §1.3, which also corrects pass 1's biconditional to the implication the schema ships, and records `distance_mm` |
| **O33** | Does the badge apply to forest? | **D106** — forest gets **its own** badge, its own act, its own holder, its own verification | §12 in full, F16 in §9, FR-73/V63 |

### 14.2 Still open

| # | Question | Blocks | Provisional treatment |
|---|---|---|---|
| **O31** | **`19` §2.1's legal specifics are unverified.** The 1 ha → 5 ha change and the 30 April 2026 date come from secondary sources that `19` itself says disagree | Item 15 shipping | Treated as unverified throughout §11; no test in this document asserts those values as true |
| **new** | **`19` has no forest section.** D106 needs the act, the holder and the Polish copy written down where the farmland ones live | R11 | §12.2 proposes the copy and marks it unratified. Entry criterion 7 stays unmet until doc 19 carries it |
| **new** | **Do `Lz` and `Lzr` fall under the forest act?** `Lz` is wooded land outside the agricultural register; `Lzr` is wooded land on farmland and is a *użytek rolny* | R11 | The table keeps `Lz` at regime `none` and `Lzr` at `agricultural`. Both are provisional and both are part of §11.3's manual reading of the forest act |
| **new** | **Does the prompt fire once per session, or once per regime per session?** | R12 | §13.1. The tests encode V64 as written: once per session |

---

## 15. Coverage summary

| Requirement / method | Tests |
|---|---|
| **FR-65**, V60 | §1.1–1.4, §5, §6.1–6.3, §7, §8 |
| **FR-66**, V61 | §10.1–10.3, §11 |
| **FR-73**, V63 | §12.1–12.4, §9 (F16) |
| **FR-74**, V64 | §11.1a, §13 |
| **FR-55**, V31 | §3.1–3.5 |
| **FR-53**, V29 | §4 (`test_wz_not_computed_below_parcel_precision`) |
| **FR-17** terminal `unknown` | §1.1, §6.1 (roads, land use, protection), §6.2 absorbing rule |
| **FR-48** register over advert | §6.1, §10.3 |
| **FR-14** parcel over pin | §4 |
| **D102/D103** configured parameters | §5.1 |
| **D104/D105** no expiry, prompt instead | §11.1a, §13 |
| **D106** forest badge | §12 |
| **Rule 7** always show, always flag | §5 (`n` + radius with the signal), §7, §10.3, §12.2 |
| **D58** mutation testing | §1.4 |
