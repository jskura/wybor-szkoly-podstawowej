# Test plan — items 14 & 15, pass 2

The typeable detail behind [`../05-feasibility.md`](../05-feasibility.md). Pass 1
gave the sequence (R0–R10) and the shape of each assertion. **This document gives
the literal fixtures, the exhaustive truth table, the numeric tolerances and the
exact strings** — everything a developer needs to open an editor and type the tests
without making a single further decision on their own.

| | |
|---|---|
| **Covers** | `18` §6 items 14, 15 · FR-65, FR-66 · V60, V61 · constrained by V29, V31 |
| **Reads from** | [`19-legal-and-feasibility.md`](../../19-legal-and-feasibility.md) §1–§2, [`15-database-schema.md`](../../15-database-schema.md) §7, [`04-validation.md`](../../04-validation.md) V29/V31/V60/V61, [`00-gap-analysis.md`](../00-gap-analysis.md) A4 |
| **Status** | Written before any code exists. Every number below is either computed here and checkable, or explicitly marked as not yet obtainable |
| **Blocking** | The V60 hand-labelled set (§7) still does not exist. §1's synthetic scene does **not** substitute for it and is not offered as one |

> ### Everything in §1 is synthetic. Nothing in it refers to real land.
>
> All coordinates are round numbers on a fabricated grid origin. All TERYT codes
> begin with **99**, a voivodeship code that does not exist in the TERC register and
> never will, so a synthetic identifier can never collide with a real gmina. All
> parcel identifiers use obręb numbers 900x and gmina codes 9999xx. **No parcel,
> building, road or protected area described below exists.** They are constructed to
> make specific assertions exact, not to resemble anything.
>
> Real geometry appears in exactly two places in items 14–15: the projection
> known-answer pair (§3.4) and the V60 label set (§7). Both are recorded fixtures
> with provenance, and **neither exists yet**.

---

## 1. The synthetic scene — literal geometry

### 1.1 Frame and conventions

| | |
|---|---|
| **CRS** | EPSG:2180 (PUWG 1992). All coordinates below are in metres on that grid |
| **Ordinate order in the fixture** | **easting first**, i.e. `(E, N)` → WKT `POLYGON((E N, …))`. EPSG's own axis order for 2180 is *northing first*; the fixture deliberately uses traditional GIS order because PostGIS and GDAL do, and §1.6 carries the test that pins it |
| **Frame origin** | E 600 000 · N 500 000 — a round point chosen for arithmetic legibility. In the real 2180 grid this is 100 km east of the central meridian, which is what §3 uses to compute the distortion budget |
| **Scene extent** | E 599 000 – 614 000 · N 495 000 – 505 000 |
| **All shapes are axis-aligned rectangles** | So every distance in §1.5 is an exact decimal, computable by hand, and any assertion below can be re-derived with a pocket calculator. A curved or rotated fixture would make the expected values opaque and therefore untrustworthy |
| **Storage form** | `tests/fixtures/synthetic/wz_scene.yml` declares rectangles as `[e_min, e_max, n_min, n_max]`; `tests/fixtures/synthetic/wz_scene.wkt` is the generated golden file. `test_scene_generator_reproduces_the_golden_wkt` asserts byte equality, so the generator and the code under test cannot drift into a shared bug |

Example of the generated form, given in full once so the shape is unambiguous:

```
P1  POLYGON((600000 500000, 600060 500000, 600060 500060, 600000 500060, 600000 500000))
B1  POLYGON((600090 500020, 600100 500020, 600100 500030, 600090 500030, 600090 500020))
```

### 1.2 Synthetic administrative units

Every unit is a vertical strip spanning N 495 000 – 505 000.

| Unit | TERYT | Easting extent | `building_coverage` row | Why it exists |
|---|---|---|---|---|
| **SYNTH-A** | `999901` | 599 000 – 604 500 | `source='egib', has_coverage=true, checked_at=2026-08-01` | The normal, well-mapped case |
| **SYNTH-C** | `999903` | 604 500 – 607 000 | `source='egib', has_coverage=true, checked_at=2026-08-01` | Carries the protected areas |
| **SYNTH-D** | `999904` | 607 000 – 609 000 | `source='egib', has_coverage=true, checked_at=2025-01-01` | **Stale** record — 585 days old at the fixture's build date of 2026-08-08 |
| **SYNTH-B** | `999902` | 609 000 – 612 000 | `source='none', has_coverage=false, checked_at=2026-08-01` | Publishes parcels, **no building layer** — the §1.1 case of pass 1 |
| **SYNTH-E** | `999905` | 612 000 – 614 000 | `source='osm', has_coverage=true, checked_at=2026-08-01` | OSM-only county |

Parcel identifiers follow `07` §1: `TERYT_R.OBRĘB.NUMER`, e.g. `999901_9.9001.1`.

### 1.3 Roads and protected areas

| Object | Geometry (E range · N range) | Attributes |
|---|---|---|
| **R1** — through road | 599 000 – 614 000 · 499 990 – 500 000 | register class `dr`; OSM `highway=residential`; `road_public_status = public_confirmed` (see O-item 4 in §8) |
| **R2** — northern road | 603 800 – 604 300 · 500 165 – 500 175 | register class `dr`; `road_public_status = unknown` |
| **R3** — corner-touch road | 601 000 – 602 000 · 500 060 – 500 070 | Touches P3 at the single point (602 000, 500 060) and nowhere else |
| **SYNTH-PARK** — landscape park | 605 030 – 606 000 · 499 000 – 501 000 | `kind = landscape_park` |
| **SYNTH-OTULINA** — its buffer zone | 604 800 – 605 030 · 499 000 – 501 000 | `kind = landscape_park_buffer` — a *different* regime, not the park |

R1 shares a full 60 m edge with P1, P1N, P2, P2N, P3, P5, P5N, P7, P9, P9N, P11,
P11N, and a 350 m edge with P6. R3 shares **one vertex** with P3 and no edge.

### 1.4 Buildings

All buildings are 10 m × 10 m squares. `n` within the 2 km control radius is
computed in §1.5.

| Id | Geometry (E · N) | Source | Sits on |
|---|---|---|---|
| B1 | 600 090 – 600 100 · 500 020 – 500 030 | egib | P1N |
| B2 | 600 760 – 600 770 · 500 020 – 500 030 | egib | P2N |
| **B2own** | 600 420 – 600 430 · 500 020 – 500 030 | egib | **P2 itself** — the own-building trap |
| B5 | 605 100 – 605 110 · 500 020 – 500 030 | egib | P5N, inside SYNTH-PARK |
| B6 | 602 930 – 602 940 · 500 000 – 500 010 | egib | P6N |
| B7 | 604 020 – 604 030 · 500 105 – 500 115 | egib | P7N |
| B9 | 607 590 – 607 600 · 500 020 – 500 030 | egib | P9N |
| B11 | 612 590 – 612 600 · 500 020 – 500 030 | **osm** | P11N |
| C1…C6 | N 500 500 – 500 510, E 601 000 / 601 050 / 601 100 / 601 150 / 601 200 / 601 250 (each +10 m) | egib | unattached — a hamlet, present only to populate the control radius |

The C-cluster is placed **more than 500 m from every subject parcel and less than
2 km from P1, P2 and P3**. That separation is the whole point: it lets the fixture
prove that *coverage* and *good neighbourhood* are two different questions. A
cluster inside 500 m would let a single radius change flip both at once, and the
tests would stop discriminating.

### 1.5 The subject parcels and their expected verdicts

Configuration assumed throughout: `good_neighbour_radius_m = 100`,
`control_radius_m = 2000`, `min_control_buildings = 5`,
`coverage_max_age_days = 90`, build date 2026-08-08. **All four are unratified**
(O28, O29 in `05` §12) — §1.7 states exactly which expectations move if they change.

| # | Parcel id | Geometry (E · N) | Area | Nearest **neighbour** building | Buildings ≤ 100 m | in 2 km | Road | Land use | Expected verdict |
|---|---|---|---|---|---|---|---|---|---|
| **P1** | `999901_9.9001.1` | 600 000–600 060 · 500 000–500 060 | 3 600 m² | **B1 at 30.000 m** | 1 | 9 | R1, shared edge | `B` | **`likely`** |
| **P2** | `999901_9.9001.3` | 600 400–600 460 · 500 000–500 060 | 3 600 m² | **B1 and B2, both at exactly 300.000 m** | 0 | 8 | R1, shared edge | `B` | **`unlikely`** |
| **P3** | `999901_9.9001.5` | 602 000–602 060 · 500 000–500 060 | 3 600 m² | C6 at 860.930 m | 0 | 11 | R3, **single vertex only** | `R` | **`unlikely`** |
| **P4** | `999902_9.9002.1` | 610 000–610 060 · 500 000–500 060 | 3 600 m² | B9 at 2 400.000 m | 0 | **0** | R1, shared edge | `R` | **`unknown`** / `building_data_unavailable` |
| **P5** | `999903_9.9003.1` | 605 000–605 060 · 500 000–500 060 | 3 600 m² | B5 at 40.000 m | 1 | 2 | R1, shared edge | `B` | **`uncertain`** / `capped_by_protection` |
| **P6** | `999901_9.9001.6` | 603 000–603 350 · 500 000–500 010 | 3 500 m² | B6 at **60.000 m from edge, 235.000 m from centroid** | 1 | 7 | R1, shared 350 m edge | `R` | **`uncertain`** (de-designation) |
| **P7** | `999901_9.9001.8` | 604 000–604 060 · 500 000–500 060 | 3 600 m² | B7 at 45.000 m, **on R2 not R1** | 1 | 3 | R1, shared edge | `B` | **`uncertain`** (different road) |
| **P8** | `999901_9.9001.10` | 604 460–604 520 · 500 200–500 260 | 3 600 m² | B7 at 438.321 m | 0 | 3 | none | `R` | **`unknown`** / `coverage_unproven` |
| **P9** | `999904_9.9004.1` | 607 500–607 560 · 500 000–500 060 | 3 600 m² | B9 at 30.000 m | 1 | 1 | R1, shared edge | `B` | **`uncertain`** / `capped_by_coverage_absent` |
| **P10** | `999901_9.9001.11` | 601 000–601 060 · 503 000–503 060 | 3 600 m² | C1 at 2 490.000 m | 0 | **0** | none | `B` | **`unknown`** / `coverage_unproven` |
| **P11** | `999905_9.9005.1` | 612 500–612 560 · 500 000–500 060 | 3 600 m² | B11 (**osm**) at 30.000 m | 1 | 1 | R1, shared edge | `B` | **`uncertain`** / `capped_by_osm_source` |

Neighbour parcels, carrying the buildings and adjoining the same road unless
stated: P1N `…9001.2` (600 090–600 150), P2N `…9001.4` (600 760–600 820), P5N
`…9003.2` (605 100–605 160), P6N `…9001.7` (602 880–602 940 · N 500 000–500 010),
**P7N `…9001.9` (604 000–604 060 · N 500 105–500 165 — adjoins R2, does not touch
R1)**, P9N `…9004.2` (607 590–607 650), P11N `…9005.2` (612 590–612 650).

**The five parcels the brief names, and what each is for:**

| Brief's case | Parcel | Verdict | The single thing it pins |
|---|---|---|---|
| Building **30 m** away | **P1** | `likely` | The only fixture that reaches the one affirmative cell in §2's 54-row table |
| Building **300 m** away | **P2** | `unlikely` | Buildings *exist and were seen* — 8 within the control radius, 2 at exactly 300 m — and the verdict is still negative, because the good-neighbour radius is 100 m. Distinguishes "no neighbour" from "no data", which is the entire feature. Carries B2own so a naive "any building within radius" implementation reports `present` at 0.000 m and fails |
| **Isolated** | **P3** | `unlikely` | Zero buildings within 500 m, 11 within 2 km. `unlikely` is *earned* here — the map is demonstrably populated nearby |
| Gmina with **no coverage at all** | **P4** | `unknown` | O17. Geometrically indistinguishable from P3 at parcel scale; only the gmina's coverage record separates them. An implementation that reads the two the same way is exactly the F14 failure |
| **Straddles a protected boundary** | **P5** | `uncertain` | Overlaps SYNTH-PARK by **1 800.00 m² (50.00 %)** and SYNTH-OTULINA by **1 800.00 m² (50.00 %)**. Two rows, two distinct `kind` values. Would have been `likely` — B5 is 40 m away, on the same road, non-agricultural — and protection **caps it at `uncertain`, never lowers it to `unlikely`** |

P5 additionally pins `test_landscape_park_and_its_otulina_are_distinguished`: the
two overlaps are equal in area and different in kind, so an implementation that
merges the layers produces one 3 600 m² overlap and fails on both the count and
the kind.

Note that B5 — the developed neighbour — **is itself inside the park**. That is
deliberate: it is the fixture's statement that a protected area does not forbid
building, which is the overreach `19` §1.2 explicitly rules out.

### 1.6 Assertions that come free with this geometry

| Test | Fixture | Exact expected value |
|---|---|---|
| `test_building_within_radius_of_parcel_boundary_counts` | P1/B1 | `distance_m == 30.000 ± 0.001`, `signal == present` |
| `test_distance_measured_from_boundary_not_centroid` | P6/B6 | boundary `60.000`, centroid `235.000`. At radius 100 the two implementations disagree; the centroid one reports `absent` |
| `test_building_on_the_subject_parcel_does_not_count_as_a_neighbour` | P2/B2own | nearest **neighbour** `300.000`, not `0.000` |
| `test_single_vertex_contact_is_not_road_adjacency` | P3/R3 | intersection is a `POINT(602000 500060)`; `road_adjacent == false` |
| `test_parcel_sharing_an_edge_with_a_road_parcel_is_adjacent` | P1/R1 | shared boundary length `60.000 m`; `road_adjacent == true` |
| `test_developed_neighbour_on_a_different_road_does_not_satisfy_the_condition` | P7/B7/R2 | `neighbour == present`, `shares_road == false`, verdict `uncertain` |
| `test_parcel_straddling_gmina_boundary_assigned_by_majority_area_and_flagged` | P8 | 2 400.00 m² in `999901`, 1 200.00 m² in `999903`; assigned `999901`; `boundary_straddle` flag set with both TERYTs and both areas |
| `test_parcel_intersecting_protected_area_is_flagged` | P5 | park 1 800.00 m², otulina 1 800.00 m², fractions 0.5000 each |
| `test_stale_coverage_record_degrades_to_unknown` | P9 | record age 585 d > 90 d → coverage `absent` → verdict capped, `unlikely` unreachable |
| `test_osm_fallback_cannot_produce_likely` | P11 | `source == "osm"`, verdict `uncertain`, never `likely` |
| `test_fixture_ordinates_are_easting_first` | P1 | first ordinate ∈ [599 000, 614 000]; and P1 reprojected to 4326 falls **inside SYNTH-A's polygon** — see §3.5 on why a distance test cannot catch a transposition |

### 1.7 Which expectations move when the unratified parameters move

Only parcels with **no** neighbour depend on `min_control_buildings` (K), because a
neighbour found at all proves the map is populated here (§2.1). That gives a small,
exact sensitivity table — and it is the evidence O29 asks for.

| Parcel | `n` in control radius | Verdict at K≤3 | K=4…8 | K=9…11 | K≥12 |
|---|---|---|---|---|---|
| P2 | 8 | `unlikely` | `unlikely` | `unknown` | `unknown` |
| P3 | 11 | `unlikely` | `unlikely` | `unlikely` | `unknown` |
| P8 | 3 | `unlikely` | `unknown` | `unknown` | `unknown` |
| P10 | 0 | `unknown` | `unknown` | `unknown` | `unknown` |
| P4 | 0 | `unknown` at every K — the gmina record decides before the count is consulted | | | |

Radius sensitivity, for `scripts/wz_radius_sensitivity.py` (`05` §5): **P2 is the
only parcel that flips on radius alone** — `absent` at 50/75/100/150/200 m,
`present` at 350 m and above, because its two neighbours sit at exactly 300.000 m.
P7 flips at radius < 45 m, P6 at < 60 m, P1/P9/P11 at < 30 m. The fixture therefore
covers the whole 50–200 m sweep without any parcel silently changing under it.

---

## 2. The composite truth table

### 2.1 The four axes, and what each value means

| Axis | Values | Determined by |
|---|---|---|
| **neighbour** | `present` · `absent` · `unknown` | A building of any source within `good_neighbour_radius_m` of the parcel *boundary*, excluding buildings on the parcel itself. `unknown` when the layer could not be read at all |
| **shares_road** | `true` · `false` · `unknown` | The parcel is adjacent (shared edge, not vertex) to a road parcel, **and** the neighbouring developed parcel is adjacent to the *same* road parcel. `unknown` when road adjacency itself could not be established |
| **landuse** | `not_required` · `required` · `unknown` | `required` = the register class is a *użytek rolny* and de-designation would be needed (§5.1's table). `unknown` = class missing, blank or unrecognised |
| **coverage** | `present` · `absent` | `present` **iff** the gmina's `building_coverage` row has `has_coverage = true`, is not older than `coverage_max_age_days`, **and** (`neighbour == present` **or** buildings-in-control-radius ≥ K) |

The last clause is the one worth reading twice. **A neighbour actually found proves
coverage a fortiori** — we are holding a building geometry from this place, so the
map is populated here and no count is needed. The control count exists only to
answer the question P3 and P4 pose: *when we found nothing, was there nothing, or
did we not look?* Defining coverage this way keeps the control count out of the
positive branch entirely, where it would otherwise cap perfectly good verdicts in
thinly-built but well-mapped areas.

### 2.2 The table — all 54 combinations

`3 (neighbour) × 3 (shares_road) × 3 (landuse) × 2 (coverage) = 54`. No cell is
omitted, no cell falls through to a default, and `test_no_input_combination_produces_a_verdict_outside_the_table`
enumerates the cross-product and asserts the table's key set is exactly equal to it
— not a superset, not a subset.

**Block 1 — neighbour `present`, coverage `present`** (9 cells)

| # | shares_road | landuse | Verdict | Reason / flag |
|---|---|---|---|---|
| 1 | `true` | `not_required` | **`likely`** | — |
| 2 | `true` | `required` | `uncertain` | `dedesignation_required` |
| 3 | `true` | `unknown` | `uncertain` | `landuse_unknown` |
| 4 | `false` | `not_required` | `uncertain` | `neighbour_on_different_road` |
| 5 | `false` | `required` | `uncertain` | `neighbour_on_different_road`, `dedesignation_required` |
| 6 | `false` | `unknown` | `uncertain` | `neighbour_on_different_road`, `landuse_unknown` |
| 7 | `unknown` | `not_required` | `uncertain` | `road_status_unknown` |
| 8 | `unknown` | `required` | `uncertain` | `road_status_unknown`, `dedesignation_required` |
| 9 | `unknown` | `unknown` | `uncertain` | `road_status_unknown`, `landuse_unknown` |

**Block 2 — neighbour `present`, coverage `absent`** (9 cells)

Reachable only through a stale or negative coverage record contradicted by an
observed building (P9). The observation stands; the *optimism* does not.

| # | shares_road | landuse | Verdict | Reason / flag |
|---|---|---|---|---|
| 10 | `true` | `not_required` | `uncertain` | **`capped_by_coverage_absent`** — the one cell in the table that would be `likely` but is not |
| 11 | `true` | `required` | `uncertain` | `capped_by_coverage_absent`, `dedesignation_required` |
| 12 | `true` | `unknown` | `uncertain` | `capped_by_coverage_absent`, `landuse_unknown` |
| 13 | `false` | `not_required` | `uncertain` | `capped_by_coverage_absent`, `neighbour_on_different_road` |
| 14 | `false` | `required` | `uncertain` | + `dedesignation_required` |
| 15 | `false` | `unknown` | `uncertain` | + `landuse_unknown` |
| 16 | `unknown` | `not_required` | `uncertain` | `capped_by_coverage_absent`, `road_status_unknown` |
| 17 | `unknown` | `required` | `uncertain` | + `dedesignation_required` |
| 18 | `unknown` | `unknown` | `uncertain` | + `landuse_unknown` |

Every cell in this block additionally raises the Δ assertion
`coverage_record_contradicted` (§6 of `05`, F14's detector (b)) — a building was
observed in a unit whose coverage record says otherwise, which is a data-quality
fact about the record, not about the parcel.

**Block 3 — neighbour `absent`, coverage `present`** (9 cells)

| # | shares_road | landuse | Verdict | Reason / flag |
|---|---|---|---|---|
| 19 | `true` | `not_required` | **`unlikely`** | `no_neighbour_within_radius` |
| 20 | `true` | `required` | **`unlikely`** | + `dedesignation_required` |
| 21 | `true` | `unknown` | **`unlikely`** | + `landuse_unknown` |
| 22 | `false` | `not_required` | **`unlikely`** | `no_neighbour_within_radius` |
| 23 | `false` | `required` | **`unlikely`** | + `dedesignation_required` |
| 24 | `false` | `unknown` | **`unlikely`** | + `landuse_unknown` |
| 25 | `unknown` | `not_required` | **`unlikely`** | `no_neighbour_within_radius`, `road_status_unknown` |
| 26 | `unknown` | `required` | **`unlikely`** | + `dedesignation_required` |
| 27 | `unknown` | `unknown` | **`unlikely`** | + `landuse_unknown` |

The whole block is `unlikely` and that is intentional. The good-neighbour condition
has demonstrably failed; the road and land-use axes can only add further obstacles,
never remove this one. Making the verdict depend on them here would be a weighted
score wearing a rule table's clothes, which `test_composite_contains_no_numeric_weights`
exists to forbid. **Every cell in this block requires a coverage evidence row**
(schema `unlikely_requires_coverage`).

**Block 4 — neighbour `absent`, coverage `absent`** (9 cells)

| # | shares_road | landuse | Verdict | Reason code |
|---|---|---|---|---|
| 28–36 | *all nine combinations* | | **`unknown`** | `coverage_unproven` when the record is fresh and positive but the control count is below K (P8, P10); `coverage_record_stale` when the record is too old; `building_data_unavailable` when `has_coverage = false` |

This is the block O17 exists for, and the one the schema constraint makes
unwritable in its wrong form. **`unlikely` appears nowhere in it.**

**Block 5 — neighbour `unknown`, coverage `present`** (9 cells)

| # | shares_road | landuse | Verdict | Reason code |
|---|---|---|---|---|
| 37–45 | *all nine combinations* | | **`unknown`** | `building_query_failed` — the layer exists and is populated, our read of it did not succeed |

**Block 6 — neighbour `unknown`, coverage `absent`** (9 cells)

| # | shares_road | landuse | Verdict | Reason code |
|---|---|---|---|---|
| 46–54 | *all nine combinations* | | **`unknown`** | `building_data_unavailable` — there is no layer to read (P4) |

Blocks 5 and 6 together are `test_unknown_neighbour_signal_is_absorbing`: 18 cells,
one verdict. They carry **different reason codes** because "the map does not exist"
and "the map exists and we failed to read it" call for different operator actions
and different UI sentences (U7). A single `unknown` code across both would pass every
verdict test in pass 1 and still be wrong.

### 2.3 The distribution, and the property worth quoting

| Verdict | Cells | Share |
|---|---|---|
| `likely` | **1** | 1.9 % |
| `uncertain` | 17 | 31.5 % |
| `unlikely` | 9 | 16.7 % |
| `unknown` | 27 | 50.0 % |

`test_likely_occupies_exactly_one_cell_of_fifty_four` is worth writing as an
assertion in its own right. It is the mechanical form of `19` §1.2's rule that the
optimistic answer is the dangerous one: **`likely` requires every single condition
to hold simultaneously, and any one of eight degradations removes it.** If a later
change makes two cells `likely`, this test fails and someone has to say why in
writing.

### 2.4 The modifiers, and the order they apply in

The table above is the whole rule for the four declared axes. Protection, source
and staleness are **caps**, applied outside it.

| # | Modifier | Trigger | Effect |
|---|---|---|---|
| **M0** | staleness | `checked_at` older than `coverage_max_age_days` | Rewrites the `coverage` axis to `absent` **before** the table is consulted |
| **M1** | source | the neighbour signal's `source == "osm"` | Caps the verdict at `uncertain` |
| **M2** | protection | any overlap with a protected area, of any kind, of any fraction > 0 | Caps the verdict at `uncertain` |

On the optimism ordering `likely > uncertain > unlikely`, a **cap** replaces the
verdict with `uncertain` **only if the verdict is `likely`**. It never touches
`unlikely` and never touches `unknown`.

Three consequences, each of which is a test:

| Test | Assertion |
|---|---|
| `test_protected_overlap_alone_never_produces_unlikely` | For all 54 cells, `verdict(cell)` and `verdict(cell) + M2` are either equal or (`likely`, `uncertain`). No pair is (`x`, `unlikely`) |
| `test_caps_commute` | M1 and M2 applied in either order give the same result, for all 54 × 4 combinations. A cap is idempotent and order-free by construction; a `min()` over a scale is not the same as a chain of `if` statements and this is where the difference would show |
| `test_no_modifier_ever_raises_a_verdict` | For all 54 cells and all 8 modifier subsets, the result is never more optimistic than the unmodified cell |

M0 is applied *before* the table and the other two after, and that ordering is
load-bearing: a stale record must be able to turn `unlikely` into `unknown`
(block 3 → block 4), which a post-hoc cap could not do, because caps never touch
`unlikely`. `test_stale_coverage_moves_unlikely_to_unknown_not_to_uncertain` pins it.

### 2.5 The composite's metamorphic properties, stated numerically

| Property | Concrete form over this table |
|---|---|
| Order independence | 54 cells × 4! = 1 296 permutations of signal evaluation order, all giving the same verdict |
| Monotonic in evidence | For each of the 18 `neighbour == unknown` cells, replacing `unknown` with `present` or `absent` never returns to `unknown`: 36 transitions, 36 assertions |
| Coverage removal | For each of the 9 `unlikely` cells, setting coverage to `absent` yields `unknown`: 9 transitions, all to `unknown`, none to `uncertain` or `likely` |
| Non-vacuity companion | A deliberately broken composite that ignores the coverage axis passes the first two properties and fails the third. The suite must contain it, per `00-gap-analysis.md` §E |

---

## 3. The distance tolerance budget, in numbers

### 3.1 Three tiers, not one

V31 as amended gives two tolerances (≤1 m under 1 km, ≤0.1 % at ring scale). That is
one tier short. The synthetic fixture is constructed *in* EPSG:2180, so its
distances are not measurements at all — they are definitions, and asserting them to
±1 m would let a 90 cm arithmetic error through unnoticed.

| Tier | What is compared | Tolerance | Rationale |
|---|---|---|---|
| **S — synthetic** | Distances computed in 2180 against the hand-derived decimal in §1.5 | **±0.001 m (1 mm)** | Pure planar arithmetic. No projection is involved, so the only permissible error is floating point. Every §1.6 assertion is tier S |
| **G — good-neighbour** | The real known-answer pair (§3.4), under 1 km | **≤1.000 m** | V31's contract |
| **G′ — round trip** | 2180 → 4326 → 2180, same points | **≤0.050 m** | A tighter tripwire on the storage round trip alone, where no projection distortion applies and the only error is conversion. It fails first, so the 1 m budget cannot be eaten a centimetre at a time. It must **not** be applied to G's known-answer pair, where 0.21 m of real distortion lives (§3.2) |
| **R — ring** | 25 km grid distance against the ellipsoidal geodesic | **≤0.100 % (25.0 m at 25 km)** | V31 as amended by B2 |

`test_distance_tolerance_budget_is_declared_per_scale` reads these from one table
and raises for any comparison at a scale the table does not cover.

### 3.2 What the projection actually costs, computed

PUWG 1992 is a transverse Mercator on the 19° E meridian with `m0 = 0.9993`. The
point scale factor is `k(y) ≈ 0.9993 · (1 + y² / 2R²)` where `y` is the distance
from the central meridian and `R ≈ 6 381 km`.

| Location | `y` | `k` | Grid error | over 30 m | over 300 m | over 25 km |
|---|---|---|---|---|---|---|
| Central meridian | 0 km | 0.999300 | −0.700 m/km | −21 mm | −0.210 m | −17.50 m |
| **Budy Grabskie ring** | 53–103 km | 0.999334–0.999428 | −0.67 to −0.57 m/km | −20 to −17 mm | −0.201 to −0.172 m | −16.7 to −14.3 m |
| **Elbląg ring** | 1–51 km | 0.999300–0.999331 | −0.700 to −0.669 m/km | −21 to −20 mm | −0.210 to −0.201 m | −17.5 to −16.7 m |
| Scale-true parallel | 239 km | 1.000001 | ~0 | 0 | 0 | 0 |
| Poland's eastern edge | ~353 km | 1.000829 | +0.829 m/km | +25 mm | +0.249 m | +20.7 m |
| **Synthetic frame (§1)** | 99–125 km | 0.999423–0.999490 | −0.577 to −0.510 m/km | −17 to −15 mm | −0.173 to −0.153 m | −14.4 to −12.8 m |

Three things fall out of this table, and each is an assertion:

1. **Both rings sit west of the scale-true parallel, so grid distance is always
   short — never long.** `test_ring_distance_error_is_negative_in_both_rings`
   asserts `grid − geodesic ∈ [−17.6, −14.2] m` at 25 km. A one-sided bound is far
   stronger than `|error| ≤ 25 m`: a **positive** deviation of any magnitude is a
   bug, and the symmetric budget would hide it up to 25 m.
2. **The ring budget has 30–40 % headroom, not 100×.** Worst case in the rings is
   0.070 %, against a 0.100 % budget — 7.5 m of slack over 25 km. This is a tight
   budget and must be asserted against a **geodesic**, never against another grid
   computation, which would agree with itself perfectly and prove nothing.
3. **At 300 m, projection distortion alone consumes 21 % of the 1 m budget.** So
   the good-neighbour tolerance is not dominated by rounding, and the tripwire in
   tier G is set at 0.050 m — below the distortion — precisely so it measures the
   round trip and not the projection.

Worked ring values for the fixture frame, from A = (600 000, 500 000):

| Baseline | Grid distance | Ellipsoidal length | Δ | Δ % |
|---|---|---|---|---|
| N–S to (600 000, 525 000) | 25 000.000 m | 25 014.441 m | **−14.441 m** | **−0.0578 %** |
| E–W to (625 000, 500 000) | 25 000.000 m | 25 013.609 m | **−13.609 m** | **−0.0544 %** |

Both inside 0.1 %; both negative; both different from each other, so a test using
only one orientation would not notice an implementation that ignores `y`.

### 3.3 The degrees-are-wrong control, with expected failure magnitudes

At latitude 51.95° N (the Budy Grabskie ring): **111 267.35 m per degree of
latitude, 68 678.01 m per degree of longitude**.

| Control | Baseline | Correct | Naive result | Absolute error | Ratio |
|---|---|---|---|---|---|
| **C1** raw degrees, N–S | 300 m | 300.000 | **0.00269621** | 299.9973 m | 111 267 : 1 |
| **C2** raw degrees, E–W | 300 m | 300.000 | **0.00436821** | 299.9956 m | 68 678 : 1 |
| **C3** raw degrees, ring | 25 000 m | 25 000.000 | **0.22468406** | 24 999.775 m | 111 267 : 1 |
| **C4** flat 111 320 m/°, E–W | 300 m | 300.000 | **486.269** | **+186.269 m** | 1.62 : 1 |
| **C5** flat 111 320 m/°, ring | 25 000 m | 25 000.000 | **40 522.4** | **+15 522.4 m** | 1.62 : 1 |

Assertions:

```
# C1/C2 — the error is five orders of magnitude, so assert the order, not a bound
assert naive < 0.01
assert abs(naive - expected_m) > 299.0
assert 6.5e4 < expected_m / naive < 1.2e5
assert not within_tolerance(naive, expected_m, tier="G")
```

**C4 and C5 are the controls that matter and pass 1 does not have.** Raw degrees is
off by 10⁵ and dies on contact with any assertion; the bug that actually ships is
"a degree is 111 320 m", which is *right to 0.01 % on a north–south baseline* and
**62 % wrong east–west**. C4 must fail tier G by a factor of 186, and the test says
so:

```
assert abs(c4 - 300.0) > 180.0          # 186 m — 186× the tier-G budget
assert not within_tolerance(c4, 300.0, tier="G")
assert within_tolerance(c4_north_south, 300.0, tier="G")   # and this one passes — that is the trap
```

The last line is the point of the whole control: the naive constant passes a
north–south known-answer test. `05` §3.1's second pair must therefore be
**east–west**, and the test file must say why in a comment, or someone will
"simplify" the two pairs into one.

### 3.4 The real known-answer fixture — does not exist

`tests/fixtures/geo/known_separation.json` is called for by `05` §3.1 and has never
been recorded. It must carry, per pair:

| Field | Notes |
|---|---|
| `point_a_2180`, `point_b_2180` | As published by the source |
| `point_a_4326`, `point_b_4326` | The same points, from the same source, not derived by us |
| `separation_m` | The independently known distance |
| **`separation_kind`** | **`grid` or `geodesic`.** Missing today, and the fixture is unusable without it: at 300 m the two differ by 0.21 m — a fifth of the tier-G budget — and at 25 km by 14 m |
| `orientation` | `north_south` or `east_west`; §3.3 requires at least one of each |
| `source`, `tool`, `tool_version`, `retrieved_at` | Rule 7 provenance |

`test_known_separation_fixture_declares_its_separation_kind` fails the suite while
the field is absent, so the gap cannot be papered over by picking whichever
interpretation makes the test pass.

### 3.5 A transposition cannot be caught by a distance test

`05` §3.1 says two baselines of different orientation mean "a transposed
easting/northing passes neither". **That is not true.** Swapping `(E, N) → (N, E)`
is a reflection about the line E = N, and reflections are isometries: if *both*
points are transposed, every pairwise distance is preserved **exactly**, at every
orientation, at every scale. A consistently transposed pipeline passes every
distance assertion in this document.

What catches it is an **absolute** check, not a relative one:

| Test | Assertion |
|---|---|
| `test_reprojected_point_matches_the_recorded_4326_coordinates` | Compare the reprojected 2180 fixture against the recorded 4326 values, ≤ 1e-7° (≈ 1 cm) |
| `test_parcel_falls_inside_its_declared_gmina` | P1 transposed lands at (500 000, 600 000) — still inside Poland, still a valid coordinate, and **outside SYNTH-A**. Containment is what fails |
| `test_distance_is_invariant_under_transposition_and_this_is_why_containment_is_required` | Asserts the invariance *deliberately*, with the comment that records why the containment test above cannot be deleted |

The third test looks perverse and is the important one: it documents the hole in
the obvious approach, in the suite, where the next person will find it.

---

## 4. The disclaimer test

### 4.1 The strings, exactly

Declared once in `src/lpc/app/render/feasibility.py`. Any second occurrence
anywhere in `src/` fails `test_disclaimer_literal_appears_exactly_once_in_src`.

| Const | String | Chars | UTF-8 bytes | SHA-256 (of the UTF-8 bytes) |
|---|---|---|---|---|
| `WZ_DISCLAIMER` | `wstępna ocena — nie jest to gwarancja wydania WZ` | 48 | 51 | `fa229e39d1be60a4761d4b3997e0063602d99003062ca570b2ce07a15a537d5a` |
| `WZ_UNLIKELY_TEMPLATE` | `brak spełnienia warunku dobrego sąsiedztwa w promieniu {radius} m` | 65 | 67 | `42683c4e1f3d9c712e5529866a461830d5dfb774d9bd55b49acd13285daae88f` |

The two hashes are of the literals as written above, in **NFC**, with U+2014 EM DASH
and U+0020 spaces around it.

Verdict lines, all of which are rendered **in addition to**, never instead of,
`WZ_DISCLAIMER`:

| Verdict / reason | Rendered Polish |
|---|---|
| `likely` | `warunek dobrego sąsiedztwa wygląda na spełniony — budynek w odległości {distance} m, w promieniu {radius} m` |
| `uncertain` | `warunku dobrego sąsiedztwa nie udało się jednoznacznie ocenić` |
| `unlikely` | `brak spełnienia warunku dobrego sąsiedztwa w promieniu {radius} m` |
| `unknown` / `building_data_unavailable` | `brak danych o budynkach w tej gminie — nie wiemy, czy w pobliżu stoją budynki` |
| `unknown` / `coverage_unproven` | `nie potwierdziliśmy, że mapa budynków w tej okolicy jest wypełniona` |
| `unknown` / `coverage_record_stale` | `dane o budynkach dla tej gminy są nieaktualne (sprawdzone {checked_at})` |
| `unknown` / `building_query_failed` | `nie udało się odczytać danych o budynkach` |

Below parcel precision there is **no verdict line and no `wz_feasibility` row at
all** (V29); the page renders `brak dokładnej lokalizacji` and nothing else about
feasibility.

### 4.2 The byte-identity assertion

```python
def test_likely_disclaimer_is_byte_identical_to_unlikely_disclaimer():
    a = render(verdict="likely",   **EVIDENCE).disclaimer
    b = render(verdict="unlikely", **EVIDENCE).disclaimer
    assert a.encode("utf-8") == b.encode("utf-8")          # bytes, not str
    assert hashlib.sha256(a.encode("utf-8")).hexdigest() == WZ_DISCLAIMER_SHA256
    assert a is WZ_DISCLAIMER                              # same object: one constant, not two equal literals
```

Comparing **bytes** rather than strings is the whole point. Two strings that
compare equal under `==` can still differ in encoded form after a normalisation
pass, and two visually identical strings can differ in bytes. Both directions are
tested.

### 4.3 The homoglyph and normalisation guards

The realistic way this rule erodes is not deletion. It is an editor, a copy-paste
from a rendered page, or a well-meaning "typographic fix" that swaps one character.
Each of these produces a string that looks identical and hashes differently:

| Substitution | Result |
|---|---|
| U+2014 EM DASH → U+002D HYPHEN-MINUS | different hash |
| U+2014 → U+2013 EN DASH | different hash |
| U+0020 → U+00A0 NO-BREAK SPACE around the dash | different hash |
| `ę` U+0119 → `e` + U+0328 COMBINING OGONEK (NFD) | different bytes, same rendering |

```python
def test_disclaimer_characters_are_the_declared_ones():
    s = WZ_DISCLAIMER
    assert unicodedata.normalize("NFC", s) == s     # NFC is a fixed point
    assert "—" in s
    assert not any(c in s for c in ("-", "–", " ", "−"))
    assert len(s) == 48 and len(s.encode("utf-8")) == 51
```

### 4.4 The rest of the disclaimer suite

| Test | Assertion |
|---|---|
| `test_every_verdict_renders_with_the_disclaimer` | Parametrized over all four verdicts **and** all four `unknown` reason codes — 7 renders, 7 disclaimers, all byte-identical to `WZ_DISCLAIMER` |
| `test_every_render_helper_in_the_registry_emits_the_disclaimer` | Enumerates the module's exported helpers by introspection. A helper added later fails until it complies |
| `test_likely_is_not_rendered_with_affirmative_styling` | No success colour token, no `✓` (U+2713), and none of `{"można budować", "zgoda", "gwarancja wydania", "spełnia warunki", "bez przeszkód"}` — matched case-insensitively on the whole rendered page |
| `test_unlikely_is_phrased_as_an_observation` | Contains the rendered `WZ_UNLIKELY_TEMPLATE` with `{radius}` substituted by the value actually used; contains none of `{"nie można budować", "odmowa", "nie da się", "niemożliwe"}` |
| `test_radius_in_the_string_equals_the_radius_used` | Render P2 at radius 100 → the string contains `w promieniu 100 m`; re-render at 150 → `150`. A hardcoded `100` in the template passes the first and fails the second |
| `test_disclaimer_is_visible_in_the_collapsed_state` | The collapsed row's text contains `WZ_DISCLAIMER`; not only the expanded panel |
| `test_verdict_renders_with_n_source_and_as_of` | The rendered block contains the neighbour count, the radius, the source (`egib`/`osm`) and the `as_of` date (rule 7) |
| `test_seeded_dishonest_render_tree_is_caught` | A deliberately non-compliant render module — disclaimer removed from `likely` only — makes the suite fail. Without it, the sweep above could be vacuous |

---

## 5. The purchasability badge cases

### 5.1 The register-class table, class by class

`config/register_classes.yml`. **The `agricultural?` column below is drawn from the
EGiB classification of *użytki rolne* and is NOT independently verified.** Per O31
and §6, every row must carry a citation to a dated consolidated text before the
badge ships, and `test_register_class_table_rows_all_carry_a_citation` fails while
any row lacks one. The tests below assert that the **badge follows the table**; they
do not assert that the table is legally correct. That is §6's job.

| Symbol | Name | Agricultural? | Badge | Notes |
|---|---|---|---|---|
| `R` | grunty orne | yes | **yes** | The canonical case |
| `S` | sady | yes | **yes** | |
| `Ł` | łąki trwałe | yes | **yes** | Non-ASCII symbol — see §5.4 |
| `Ps` | pastwiska trwałe | yes | **yes** | |
| `Br` | grunty rolne zabudowane | yes | **yes** | **One character from `B`, opposite verdict** |
| `Wsr` | grunty pod stawami | yes | **yes** | **Two characters from `Ws`, opposite verdict** |
| `W` | grunty pod rowami | yes | **yes** | |
| `Lzr` | grunty zadrzewione i zakrzewione na użytkach rolnych | yes | **yes** | **One character from `Lz`, opposite verdict** |
| `Ls` | lasy | no | **no** | Restricted under the *ustawa o lasach*, a different act with a different pre-emption holder. Must **not** borrow this badge's copy (O33) |
| `Lz` | grunty zadrzewione i zakrzewione | no | **no** | |
| `B` | tereny mieszkaniowe | no | **no** | |
| `Ba` | tereny przemysłowe | no | **no** | |
| `Bi` | inne tereny zabudowane | no | **no** | |
| `Bp` | zurbanizowane tereny niezabudowane | no | **no** | |
| `Bz` | tereny rekreacyjno-wypoczynkowe | no | **no** | |
| `dr` | drogi | no | **no** | Lower-case symbol — see §5.4 |
| `Tk` | tereny kolejowe | no | **no** | |
| `Ti` | inne tereny komunikacyjne | no | **no** | |
| `Tp` | grunty przeznaczone pod budowę dróg i kolei | no | **no** | |
| `Ws` | wody powierzchniowe płynące | no | **no** | |
| `Wp` | wody powierzchniowe stojące | no | **no** | |
| `Wm` | morskie wody wewnętrzne | no | **no** | Relevant to the Elbląg ring |
| `Tr` | tereny różne | no | **no** | |
| `N` | nieużytki | no | **no** | Frequently *assumed* agricultural. It is not, in this table, and the assumption is exactly what the parametrized test catches |

**Three adversarial pairs — `B`/`Br`, `Ws`/`Wsr`, `Lz`/`Lzr` — differ by one or two
characters and fall on opposite sides.** `test_adversarial_class_pairs_do_not_share_a_verdict`
asserts each pair produces different badge presence. A prefix match, a `startswith`,
a case-folded comparison or a truncation bug breaks at least one pair.

Parametrisation is **generated from the table file**, never hand-listed
(`05` §10.1), so a class added later is covered on the day it is added:

```python
@pytest.mark.parametrize("row", load_register_classes())
def test_badge_presence_follows_the_table(row):
    page = render_plot(register_class=row.symbol, area_m2=3400, area_source="register")
    assert (page.badge is not None) == row.is_agricultural
    assert NO_REASSURANCE_TOKEN.search(page.text) is None     # every class, not only unknown
```

### 5.2 The badge copy, exactly

Rendered for every agricultural class, and for no other:

```
⚠ Grunt rolny — 3 400 m²
   Możliwe ograniczenia w nabyciu (ustawa o kształtowaniu ustroju rolnego)
   Możliwe prawo pierwokupu KOWR
   → sprawdź u notariusza przed ofertą
```

| Line | Const | Bytes | SHA-256 |
|---|---|---|---|
| 2 | `BADGE_RESTRICTION_LINE` — `Możliwe ograniczenia w nabyciu (ustawa o kształtowaniu ustroju rolnego)` | 73 | `6dd9a9476cab18c009b6004531c9ca45739d46ffd264d68f0dc1cbf22b1d6c7a` |
| 3 | `BADGE_PREEMPTION_LINE` — `Możliwe prawo pierwokupu KOWR` | 30 | `f20864d3363a915dae82c08bb2dc0e8f436340dfd6f139aec40329520752a73f` |
| 4 | `BADGE_NOTARY_LINE` — `sprawdź u notariusza przed ofertą` | 35 | `796cb396bf0f8f2a7430520e01d408ea0bc9ad122c39d432a86d498edcd82e8d` |

Line 1 is a template: `⚠ Grunt rolny — {area} m²`, with U+26A0 WARNING SIGN, U+2014
EM DASH, and the area formatted by one declared formatter.

> **Defect in pass 1, §10.3.** `test_badge_states_possibility_never_certainty`
> asserts the page contains `"możliwe ograniczenia"` and `"możliwe prawo pierwokupu
> KOWR"` — **lower case**. The copy in `19` §2.2 capitalises both (`Możliwe …`), so
> those assertions fail against the correct copy. Fix: match case-insensitively, or
> assert the exact capitalised constants above. Do not "fix" it by lower-casing the
> copy.

| Test | Assertion |
|---|---|
| `test_badge_contains_all_four_lines` | Each of the three constants present verbatim, plus a line-1 match |
| `test_badge_states_possibility_never_certainty` | Contains the three constants; contains none of `{"nie możesz kupić", "zakaz nabycia", "na pewno", "wymagana zgoda", "nie kupisz"}`, case-insensitively |
| `test_badge_directs_to_a_notary` | `BADGE_NOTARY_LINE` present in **every** badge render, including the degraded one of §6.4 |
| `test_badge_shows_area_and_its_source` | Area from the register, `area_source == "register"`, parcel `as_of` rendered (rule 7, V28) |
| `test_badge_is_driven_by_register_class_not_advert_claim` | Advert `działka budowlana` + register `R` → badge. Advert `rolna` + register `B` → no badge (FR-48, V25) |
| `test_badge_is_never_a_filter` | A badged plot appears in an unfiltered result set; plus an architecture check that no SQL predicate references the badge (D51) |
| `test_badge_renders_at_both_ends_of_the_d48_band` | 2 000 m² and 4 000 m² both badged, with **identical copy** — the band's ends differ in legal consequence but the badge makes no numeric claim, so its text must not vary (§6) |

### 5.3 The unknown class — neither badge nor reassurance

Four inputs take the unknown path: `None`, `""`, `"   "` (three spaces), and any
symbol absent from the table (fixture value `"Xx"`).

| Test | Assertion |
|---|---|
| `test_unknown_class_produces_no_badge` | `page.badge is None` for all four inputs |
| `test_unknown_class_produces_an_explicit_unknown_statement` | Page contains `klasa użytku nieznana — nie wiemy, czy obowiązują ograniczenia` (62 chars, 67 bytes, SHA-256 `44a2cf6f752eef52f84c0768b9ee4311a43381a11389e79a6d41da1ce94186ce`) |
| `test_unrecognised_symbol_additionally_alarms` | `"Xx"` raises the unmapped-value alarm (FR-49); `None`/`""`/`"   "` do not — a missing value is a known state, an unrecognised one is a surprise |
| `test_unknown_class_page_contains_no_reassurance_token` | **Whole-page** scan for `{"brak ograniczeń", "bez ograniczeń", "można kupić", "nie dotyczy", "nieograniczony", "dowolny nabywca"}`, case-insensitive, after HTML tag stripping |

**The scan runs on every class, not only the unknown one.** V61's falsifier is a
plot *presented* as unrestricted, and a known non-agricultural class is just as
capable of being presented that way — `Ls` most of all, because forest **is**
restricted, under a different act we say nothing about. So:

| Test | Assertion |
|---|---|
| `test_no_class_produces_a_reassurance_token` | Parametrized over all 24 table rows plus the four unknown inputs — 28 renders, zero reassurance tokens |
| `test_non_agricultural_class_makes_no_purchasability_statement` | For every non-agricultural row the page contains no sentence about acquisition at all — neither restriction nor permission. Absence of a badge is not a statement, and must not be dressed as one |
| `test_forest_does_not_borrow_the_farmland_copy` | `Ls` page contains none of the three badge constants |

### 5.4 Encoding and formatting traps

| Test | Assertion |
|---|---|
| `test_diacritic_class_symbol_round_trips` | `Ł` (U+0141) survives YAML load, database round trip and render; `L` and `Ł` are different rows |
| `test_class_symbol_matching_is_case_sensitive` | `dr` matches, `DR` and `Dr` do not — they take the unrecognised path and alarm. Case-insensitive matching would collapse `B`/`b` and is exactly how `Br` would come to be treated as `BR` |
| `test_area_is_formatted_with_the_declared_separator` | `3400` renders as `3 400`, never `3400`, `3,400` or `3.400` |

> **Open, must be answered before R9 is written.** The thousands separator in
> `19` §2.2's copy is a space of unknown kind. U+0020 breaks the line between `3`
> and `400`; U+00A0 does not; U+202F narrow no-break space is the Polish
> typographic convention. **Provisional treatment:** one declared constant
> `THOUSANDS_SEP = " "`, asserted by hash like every other literal, with the
> choice recorded in the decision log. The test must reference the constant, so the
> answer can change in one place.

---

## 6. The citation check

### 6.1 What is compared against what

`config/legal_citations.yml`, one entry per legal claim, fields per `05` §11.1.
Four independent comparisons, each with its own failure:

| # | Left side | Right side | Failure |
|---|---|---|---|
| **X1** | Every numeric quantity and date appearing in rendered legal copy | The `value` field of the `claim_id` that copy declares | A number in the copy with no `claim_id`, or a `claim_id` whose `value` differs from what was rendered |
| **X2** | Every `ha` / `hektar` quantity and act-related date literal found by scanning `src/` | The allowlist: the citation reader module and `tests/fixtures/legal/` | A literal anywhere else — a template, a helper, a default argument. **This is the comparison that makes X1 meaningful**; a literal in a template routes around X1 entirely |
| **X3** | `verified_at` of every entry | The **build date**, minus `citation_max_age_days` | Any entry verified longer ago than the window. **Fails the build**, not a warning |
| **X4** | `consolidated_text_id` + `text_as_of` of every entry | The identifier fetched live from ISAP | A changed identifier marks the entry **stale**; it does not guess at the new content |

Two more that need no external input and catch record rot:

| # | Assertion | Failure |
|---|---|---|
| **X5** | `verified_at >= text_as_of` for every entry | An entry verified against a text older than the one it cites — the verification proves nothing about the cited version |
| **X6** | Every `claim_id` in the record is referenced by at least one rendered string, and every rendered legal string references a `claim_id` | Orphan claims (dead law nobody displays) and uncited claims (displayed law nobody verified). Both directions, or the record drifts from the page |

### 6.2 The four claims item 15 makes

| `claim_id` | Value per `19` §2.1 | Status today |
|---|---|---|
| `ukur_consent_threshold_ha` | 5 ha (previously 1 ha) | **unverified** |
| `ukur_threshold_effective_date` | 2026-04-30 | **unverified** |
| `ukur_kowr_preemption_applies` | qualitative — pre-emption may attach regardless of size | **unverified** |
| `ukur_resale_holding_period_years` | referenced but not quantified in `19` | **unverified, and not even stated** |

`19` §2.1 says outright that the law moved in 2026 and secondary sources disagree.
Today's build date is **2026-08-08**, so the claimed change is a little over three
months old and has never been checked against the consolidated text. **Every entry
is `unverified` right now, and that is the state the tests must be written
against** — not the state we hope to be in after someone reads the act.

### 6.3 What fails, concretely

| Trigger | Result |
|---|---|
| `5 ha` appears in a Jinja template | X2 fails: literal outside the allowlist |
| The record says 5 ha, the copy renders 1 ha | X1 fails: rendered value ≠ `claim_id` value |
| `verified_at = 2026-01-15`, max age 90 days, build 2026-08-08 | X3 fails: 205 days > 90. **Build fails** |
| `verified_at = 2026-03-01`, `text_as_of = 2026-04-30` | X5 fails: verified before the text it cites existed |
| ISAP returns a new consolidated-text id | X4 marks stale → §6.4's degradation → operator task |
| A new sentence about pre-emption ships without a `claim_id` | X6 fails: uncited claim |
| `ukur_resale_holding_period_years` present in the record, never rendered | X6 fails: orphan claim |

### 6.4 The degraded badge, which is the badge that ships today

Because all four entries are `unverified`, the **only** badge form item 15 may
currently render is the degraded one. Its test is therefore not a fallback test; it
is the primary test.

| Test | Assertion |
|---|---|
| `test_unverified_citations_render_the_degraded_badge` | With all four entries unverified: the badge renders, contains all three constants of §5.2, contains `BADGE_NOTARY_LINE`, and **contains no digit outside the area figure** |
| `test_degraded_badge_makes_no_threshold_claim` | No occurrence of `ha`, `hektar`, `5 ha`, `1 ha`, or any date other than the parcel's `as_of` |
| `test_degraded_badge_is_not_silently_weaker` | The degraded badge and the verified badge are byte-identical on lines 2–4; only the threshold sentence is absent. A degraded badge must not also lose its warning |
| `test_verified_citations_add_the_threshold_sentence` | Flip the fixture record to verified → one additional sentence appears, and its numbers equal the record's `value` fields |

`test_consolidated_text_identifier_unchanged_since_verification` lives in
`tests/drills/`, is network-permitted, and runs on the scheduled cadence — never in
CI, where it would make the build depend on a government portal's uptime.

### 6.5 The manual step no test replaces

`scripts/verify_legal_citations.md`: open the consolidated text at ISAP, locate the
article, record the threshold, the effective date and the transitional provisions,
set `verified_at` / `verified_by` / `verification_note`. **Item 15 does not ship
until this has been done at least once.** X3 mechanises "on the date shipped"; it
cannot mechanise having read the act.

---

## 7. V60's hand-labelled parcel set — it does not exist

**Stated plainly: `tests/labelled/wz_parcels.yml` has never been produced. Nothing
in §1 substitutes for it.** The synthetic scene tests that the code computes what it
claims to compute; the label set tests that what it computes is true of the world.
Those are different questions and only the second one is V60.

Entry criterion 5 of `20` §8 is unmet until this file exists, so **items 14–15 are
not startable**, and no amount of pass-2 detail changes that.

### 7.1 What it must contain

20 entries — 10 per ring (Budy Grabskie, Elbląg), and within each ring 5 with
obvious built neighbours and 5 clearly isolated.

| Field | Notes |
|---|---|
| `parcel_id` | Full ULDK identifier. Public register data, committable |
| `teryt_gmina`, `ring` | Ring ∈ {`budy_grabskie`, `elblag`} |
| `expected_signal` | `present` or `absent` — **the neighbour signal, not the composite verdict** (§7.4) |
| `nearest_building_distance_band` | `<50` · `50–100` · `100–250` · `>250` m. A band, not a number: an orthophoto cannot support a metre, and a fabricated precision would be worse than none |
| `orthophoto_layer`, `orthophoto_tile_id`, `orthophoto_acquisition_date` | Which imagery, from when. Imagery older than the buildings it should show is the obvious way this ground truth goes wrong |
| `cadastral_map_date` | The parcel boundary's own as-of |
| `inspector`, `inspected_at` | Rule 7 applied to ground truth |
| `justification` | One line, e.g. "two houses with outbuildings on the parcel directly east, both fronting the same road" |
| `draw_seed`, `draw_index` | §7.2 — proof the parcel was drawn, not chosen |
| `building_layer_hidden` | Boolean, must be `true` — §7.3 |

### 7.2 How it is produced — sampling, not picking

1. Enumerate every parcel in each ring's loaded parcel set.
2. Draw with a **recorded seed**, stratified by gmina so one well-mapped gmina
   cannot supply all ten.
3. Inspect drawn parcels in order. Classify each as *obvious neighbours*, *clearly
   isolated*, or **ambiguous — discard**. Record `draws_examined` per polarity.
4. Stop at 5 per polarity per ring.
5. `test_label_set_records_its_sampling_effort` asserts `draws_examined` is present
   and that the discard rate is reported.

The discard rate is the finding, not the overhead. If 60 of 70 drawn parcels are
ambiguous, then "obvious neighbours" and "clearly isolated" describe a small tail of
reality and V60 validates the easy cases only. That must be visible in the file,
not discovered later. A hand-picked set of ten photogenic parcels hides it
completely, which is why picking is forbidden.

### 7.3 Independence — the trap that would make V60 vacuous

**The labeller must inspect the orthophoto with the EGiB building layer switched
off.** If the human looks at the same building layer the code reads, V60 compares
the pipeline against its own input and passes by construction — it would confirm
that we can draw a buffer, not that a house is there. `building_layer_hidden: true`
is recorded per entry and `test_every_label_declares_the_building_layer_was_hidden`
asserts it for all 20.

Same reasoning for **blinding**: labels are recorded and committed *before* the
composite is run against them. The rule is procedural — enforced by requiring the
label file's introducing commit to touch no file under `src/lpc/enrich/wz/` — plus
the `inspected_at` field, and it is stated here so a reviewer can check it.

**Inter-rater agreement:** 6 of the 20 (3 per ring) are labelled independently by a
second inspector. Any disagreement means the criterion "obvious" / "clearly
isolated" is under-specified, and the criterion is rewritten and all 20 relabelled
before the set is used. Recorded in a `second_inspector` block.

**Privacy (V7):** parcel identifiers are public and may be committed; the file must
contain no owner names, no addresses, and no parcel within 500 m of an anchor.
`test_no_labelled_parcel_is_near_an_anchor` reads `config/anchors.yml` at runtime —
never a committed copy — and skips with a clear message when the file is absent.

**Cost:** roughly 20–30 minutes per parcel including the ULDK lookup, the imagery
check and the justification, plus the 6 double-labelled, plus discards — **on the
order of 10–14 hours of one person's attention.** It cannot be produced by tooling,
by an agent, or from any dataset we hold, and budgeting it as an afternoon is the
main way it fails to happen.

### 7.4 What V60 as written cannot validate

An orthophoto shows buildings. It does **not** show road ownership or the register
land-use class. So the label set can validate the **neighbour** axis and nothing
else — one of the four axes in §2's table.

| Axis | Ground truth available from | Status |
|---|---|---|
| neighbour | Orthophoto | ✅ V60, once §7.1 exists |
| shares_road | Register extract + orthophoto | ❌ no method named anywhere |
| landuse | EGiB register extract (tier B against the register itself) | ❌ no method named anywhere |
| coverage | Per-gmina, measurable from the layer directly | ⚠ partially, via the Δ assertions of `05` §9 |

**V60 validates the neighbour signal, not the composite verdict.** `19` §1.3's
falsifier — *"any `likely`/`unlikely` verdict contradicted by the imagery"* — reads
as though it covers the verdict, and it cannot: imagery cannot contradict a
`shares_road` claim. Either V60 is amended to say *signal*, or a second labelled
set carrying road and land-use ground truth is specified. This needs a PRD/
validation decision before R8, and it is not resolved here.

---

## 8. Findings this pass produced

Raised, not absorbed. Each needs an answer before the stage that depends on it.

### 8.1 Schema — `15` §7 cannot store what §2's table computes

The tables added after the gap analysis close A4's headline gap but not its
substance. `parcel_wz_feasibility` holds `verdict`, `neighbour_found`,
`shares_road`, `coverage_source`, `computed_at`.

| # | Gap | Consequence |
|---|---|---|
| 1 | **No `reason_code` column** | The `unknown_carries_reason_code` constraint of `05` §1.3 cannot be written, and blocks 4/5/6 of §2 — 27 of 54 cells — collapse into one indistinguishable `unknown`. §4.1's four `unknown` sentences cannot be selected |
| 2 | **No land-use or protection column** | Two of the table's four axes, plus modifier M2, are not stored. `test_verdict_carries_its_reason_codes_and_evidence` cannot pass; the verdict cannot be re-derived from the row |
| 3 | **`coverage_source TEXT`, not an evidence reference** | Cannot carry `n`, the control radius, the source's `as_of`. Rule 7 requires the verdict to display its `n`, so the number would have to be recomputed at render time from data the row does not point at |
| 4 | **No radius, no nearest-building distance** | `test_radius_value_appears_in_rendered_reason_string` renders a radius the row does not record. Re-rendering an old verdict after a config change silently restates it with the new radius |
| 5 | **`parcel_building.distance_m INT`** | Truncates to whole metres. §1.6's tier-S assertions need 0.001 m; an `INT` makes `30.000` and `30.4` indistinguishable, and the mm tolerance untestable through the database |
| 6 | **`parcel_building` PK includes `geom`** | A refetch with different vertex order or coordinate precision inserts a duplicate building. Needs a source-side building identifier or a normalised geometry hash |
| 7 | **`building_coverage`** allows `source='none'` with `has_coverage=true` | Representable and meaningless. Needs `CHECK ((source = 'none') = (has_coverage = false))` |
| 8 | **`unlikely_requires_coverage` is an implication; `05` §1.3 asks for a biconditional** | Here **the schema is right and pass 1 is wrong**: a `likely` verdict should be free to record its coverage evidence, and the biconditional would forbid it. Pass 1 §1.3's row should be corrected to the implication |

### 8.2 Spec defects found while writing the detail

| # | Where | Defect |
|---|---|---|
| 1 | `05` §3.1 | "A transposed easting/northing passes neither [orientation]" is false — transposition is an isometry and preserves every distance. Only an absolute containment or coordinate check catches it (§3.5) |
| 2 | `05` §3.1 | The known-answer fixture has no `separation_kind` field. Grid and geodesic differ by 0.21 m at 300 m — a fifth of the budget — so the fixture is unusable as specified (§3.4) |
| 3 | `05` §10.3 | `test_badge_states_possibility_never_certainty` asserts lower-case `"możliwe ograniczenia"` against copy that capitalises it. The test as written fails correct copy (§5.2) |
| 4 | `05` §5 | The centroid-trap parcel is described as "60 m from its nearest edge but 190 m from its centroid"; a 3 500 m² parcel giving both exactly is over-constrained. The fixture uses 60.000 m and **235.000 m**, which discriminates more strongly at radius 100 |
| 5 | `19` §1.3 / V60 | Validates the neighbour **signal**; is worded as though it validates the composite **verdict**. Imagery cannot contradict a road or land-use claim (§7.4) |
| 6 | `19` §1 / `05` §6.1 | **EGiB free data gives no ownership, so `road_public_status` is `unknown` for every road in production** — and cell 1, the only `likely` cell in 54, becomes unreachable. Either a documented proxy (register class `dr` + OSM highway class) is ratified as evidence of a public road, or `likely` never ships. §1.3 marks R1 `public_confirmed` purely so the fixture can exercise the cell |

### 8.3 Open questions

Numbers are **not** allocated here — `00-decisions.md` is the only allocator
(`00-gap-analysis.md` §D). Each needs an O-number assigned there.

| Question | Blocks | Provisional treatment in this plan |
|---|---|---|
| Is register class `dr` + OSM highway class acceptable evidence of a **public** road? | The `likely` cell, i.e. all of R3/R6 | Fixture flag `road_public_status`; production consequence stated in §8.2/6 |
| Which **thousands separator** in the badge? U+0020 / U+00A0 / U+202F | R9 | One constant `THOUSANDS_SEP = " "`, hash-asserted (§5.4) |
| Does V60's label set validate the **verdict** or the **signal**, and if the verdict, where does road/land-use ground truth come from? | R8 | Treated as signal-only throughout §7 |
| `citation_max_age_days` — a month or a quarter? (`05` O30) | R10 | 90 days assumed in §6.3's worked example only |
| Is a **50/50** gmina straddle a tie the majority rule cannot resolve? | R1 | P8 is deliberately 40/20 so the tie is not exercised. The tie-break rule is undefined and untested |

---

## 9. What a developer types first

In order, each red before the next is written:

1. `tests/fixtures/synthetic/wz_scene.yml` + the golden `.wkt` + `test_scene_generator_reproduces_the_golden_wkt` — §1.1.
2. `test_missing_building_data_yields_unknown_not_unlikely` against **P4** — `05` §1.1.
3. Its three companions in the same commit, against **P3** (isolated, positive coverage), **P10** (zero in control radius), **P11** (OSM) — `05` §1.2.
4. The tier table and `test_distance_tolerance_budget_is_declared_per_scale` — §3.1.
5. The five degree controls C1–C5 — §3.3.
6. The 54-row table as data, then `test_no_input_combination_produces_a_verdict_outside_the_table` — §2.2.
7. `test_likely_disclaimer_is_byte_identical_to_unlikely_disclaimer` — §4.2.
8. The register-class table and its generated parametrisation — §5.1.
9. X1–X6 — §6.1.

Step 2 stays first for the reason pass 1 gave: it is the test that will be under
pressure when `unknown` looks unhelpful on a screen, and P4 is the fixture that
makes the pressure concrete — geometrically identical to an isolated parcel, and a
different answer.
