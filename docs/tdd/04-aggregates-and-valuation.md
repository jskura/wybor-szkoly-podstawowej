# TDD spec — aggregates and the comparable-set estimator

The numeric core: aggregates by gmina and area band (median, p25/p75, min/max, n,
always with spread, computed as **both stock and flow**) and the comparable-set
estimator that turns them into an estimate.

Covers [`18-v0-scope.md`](../18-v0-scope.md) §6 work item **10**, and the estimator
it feeds in item 11.

- **PRD**: FR-24, FR-25, FR-26, FR-32..FR-38, FR-67, FR-69
- **Validation**: V2, V4, V17–V20, V45, V47, V48, V51, V51c, V62 (and V46, V52 as
  cross-cutting)
- **Method**: [`05-analytics-methodology.md`](../05-analytics-methodology.md) §3, §5, §9
- **Verification**: [`20-verification-strategy.md`](../20-verification-strategy.md)
  §4.3 metamorphic, §4.4 differential, §4.8 mutation, §5 stock vs flow,
  §6.1 leave-one-out cross-validation
- **Rules**: `CLAUDE.md` 3 (TDD), 4 (validation first), 5 (two price types),
  6 (always show, always flag)
- **Decisions applied**: D56, D65, **D66**, **D67**, **D68**, **D69**, **D107**,
  **D108**, **D109**, **D110**, **D113**

This document specifies **tests only**. No implementation code appears here, and
none is written until the test named in each step exists and fails for the stated
reason.

**Where the numbers live.** Pass 2 —
[`plans/04-aggregates-test-plan.md`](./plans/04-aggregates-test-plan.md) — holds every
fixture row, every expected statistic and every LOOCV fold. Pass 2 found eleven
arithmetic defects in this document. All eleven are corrected here, so the two
documents state one value per test. Where a reader wants a value this document does
not give, the plan gives it.

**No parameter in this spec is open.** The valuation parameters are ratified: the
comparable size band is ±50 % (D108), comparable recency is 12 months (D110), the
flow window is 90 days (D107) and the search widens beyond the gmina below three
comparables (D109). The spread threshold lives in configuration (D67).

---

## 1. Entry criteria (`20` §8)

All six must hold before the first test is written. They do.

| # | Criterion | Status |
|---|---|---|
| 1 | PRD requirement or work-plan entry | `18` §6 item 10; FR-24..26, FR-32..38, FR-67, FR-69 |
| 2 | Validation method in `04-validation.md` | V4, V45, V47, V48, V62 (item 10); V17–V20, V51 (estimator) |
| 3 | Verification tier assigned (`20` §2) | Percentile maths and banding: **tier A**. Aggregates over the real corpus: **tier B** (constrained by V16 against GUS). Whether the valuation is *right*: **tier D — not verifiable in v0** |
| 4 | Silent-failure modes touched, each with a named detector | **F3** duplicates inflate n → §5 M4 + V56; **F7** stock vs flow → §7; **F9** price kinds blended → §6.3; **F10** month-boundary → §5 M7; **F11** percentile definition drift → §4 |
| 5 | Fixtures exist, dated, scrubbed | All fixtures in this document are **hand-constructed synthetic**, committed under `tests/fixtures/synthetic/`, with the constructed answer stated in a header comment. No personal data by construction |
| 6 | Metamorphic properties listed | §5, all eight relations from `20` §4.3 |

**Non-goals, so the tests do not drift into them.** v0 excludes the widening
ladder, mix adjustment, size adjustment and the hedonic model (`18` §4).
`widening_step` therefore has exactly one value in v0 — `gmina` — and a subject
with no same-gmina comparables returns an **absence**, never a widened set. The
field exists from the start (FR-35, V19) so the ladder is additive later.

**The widening threshold is three comparables (D109).** The ladder that acts on it
ships after v0. In v0 the number has one visible effect: a set of one or two
comparables still produces an estimate, and `MIN_COMPARABLES_BEFORE_WIDENING`
records why it was not widened. D109 also records the cost plainly. **A median of
three plots is close to noise.** Rule 7 makes that honest rather than strong — the
figure always ships with its `n` and its range, and never as a bare number.

## 2. Surface under test

Names the tests import. Signatures only — no bodies, no behaviour beyond what a
test below pins.

```
src/lpc/metrics/percentiles.py
    percentiles(values) -> Percentiles        # median, p25, p75, min, max, n
src/lpc/metrics/bands.py
    AREA_BANDS                                # ordered, lower-inclusive
    band_for(area_m2) -> AreaBand
src/lpc/metrics/aggregate.py
    Aggregate                                 # frozen dataclass, no defaults
    aggregate(observations, *, as_of, flow_window_days) -> list[Aggregate]
src/lpc/metrics/config.py
    SPREAD_THRESHOLD_N                        # 5  — configuration, not a CHECK (D67)
    FLOW_WINDOW_DAYS                          # 90 — D107
    AREA_BAND_TOLERANCE                       # 0.50 — D108
    RECENCY_MONTHS                            # 12 — D110
    MIN_COMPARABLES_BEFORE_WIDENING           # 3  — D109
src/lpc/valuation/comparables.py
    select_comparables(subject, candidates, *, as_of) -> ComparableSet
src/lpc/valuation/estimator.py
    Estimate                                  # low, median, high, n, basis,
                                              # widening_step, series_kind,
                                              # price_type, price_kind, as_of
    estimate(features, place, price_type, as_of) -> Estimate | Absence
    verdict(observed_ppm2, estimate) -> Literal[below|within|above]
src/lpc/valuation/loocv.py
    run_loocv(corpus, estimator) -> LoocvReport
```

Test modules:

```
tests/unit/metrics/test_percentiles.py
tests/unit/metrics/test_percentiles_differential.py
tests/unit/metrics/test_bands.py
tests/unit/metrics/test_aggregate_grouping.py
tests/unit/metrics/test_spread_switch.py
tests/unit/metrics/test_price_separation.py
tests/unit/metrics/test_stock_vs_flow.py
tests/unit/metrics/test_metamorphic.py
tests/unit/valuation/test_comparable_selection.py
tests/unit/valuation/test_estimator_contract.py
tests/unit/valuation/test_verdict.py
tests/unit/valuation/test_loocv_harness.py
tests/architecture/test_aggregate_labels.py
```

### 2.1 The canonical fixture

`tests/fixtures/synthetic/gmina_a_buildable_offering.py`. One gmina
(`TERYT_GMINA_A`, the rural Skierniewice code fixed by the V30 known-answer
fixture — never a literal in a test module), asset class `budowlana`,
buildability `buildable`, price type `offering`, price kind `asking`, `as_of =
2026-08-08`. The kind is `asking`, the D65 enum member. An earlier version of this
document wrote `ask`, which is not a legal value.

| id | area m² | price PLN | ppm2 | first seen | note |
|---|---|---|---|---|---|
| C1 | 2 000 | 192 000 | **96.00** | 2026-06-20 | |
| C2 | 2 500 | 275 000 | **110.00** | 2026-07-11 | |
| C3 | 3 000 | 378 000 | **126.00** | 2026-07-30 | |
| C4 | 3 600 | 504 000 | **140.00** | 2026-08-04 | |
| C5 | 4 400 | 660 000 | **150.00** | 2025-04-02 | still active — the stale one |

Constructed answers, asserted verbatim throughout. These are the **comparable-set**
figures, over the window `[1500, 4500]`, which admits all five rows:

- over all five (**stock**): median **126.00**, p25 **110.00**, p75 **140.00**,
  min **96.00**, max **150.00**, n **5**, `range_kind = iqr`
- over C1–C4 (**flow**, window **90 days**, D107): median **118.00**,
  p25 **106.50**, p75 **129.50**, min **96.00**, max **140.00**, n **4**,
  `range_kind = min_max`

The same five rows produce **four** `metric_unit_month` rows, because that key
carries the fixed area band and the series kind (D66). Those four rows have
different medians. The plan §1.3 lists them; §7 below states both views.

Decoys, added by individual tests, each of which must leave the estimate exactly
unchanged:

| id | what makes it a decoy | ppm2 |
|---|---|---|
| D1 | area 1 400 m² — below the ±50 % band of a 3 000 m² subject (D108) | 30.00 |
| D2 | area 4 600 m² — above the band (D108) | 400.00 |
| D3 | buildability `agricultural` | 12.00 |
| D4 | buildability `unknown` | 60.00 |
| D5 | `price_type = sales`, `price_kind = transaction` (D68) | 70.00 |
| D6 | observed 2025-01-15 — outside the 12-month recency window (D110) | 400.00 |
| D7 | `price_kind = auction_start` | 40.00 |
| D8 | a different gmina (`TERYT_GMINA_B`) | 400.00 |

---

## 3. The ordered red–green sequence

One test per step. Each step states the pinned value, why the code as it stands
cannot produce it (the red), and the smallest thing that makes it green. No step
is started before the previous one is green.

### Block A — percentiles (tier A)

**A1 · `test_percentiles_of_five_pins_every_statistic`**
Input `[96, 110, 126, 140, 150]`. Asserts `median == 126.00`, `p25 == 110.00`,
`p75 == 140.00`, `min == 96.00`, `max == 150.00`, `n == 5` — five separate
assertions, not one on a tuple, so a failure names the statistic.
*Red*: `percentiles` does not exist. *Green*: sort, index, interpolate.

**A2 · `test_percentiles_of_even_length_interpolates`**
Input `[61, 96, 140, 240]`. Asserts `median == 118.00` (the mean of the two middle
values, not either of them), `p25 == 87.25`, `p75 == 165.00`, `min == 61.00`,
`max == 240.00`.
*Red*: an implementation that returns a middle **element** returns 96 or 140.

**A3 · `test_percentiles_of_one`**
Input `[118]`. Asserts all five statistics `== 118.00` and `n == 1`. A degenerate
range is still a range (V4) — this must not raise, and must not return `None`.

**A4 · `test_percentiles_of_two`**
Input `[100, 200]`. Asserts `median == 150.00`, `p25 == 125.00`, `p75 == 175.00`.

**A5 · `test_percentile_convention_is_linear_r7`**
The canary that pins the convention rather than an implementation accident.
Input `[1, 2, 3, 4]`. Asserts `p25 == 1.75` and `p75 == 3.25`, and asserts
explicitly `p25 != 1.0` (lower), `!= 1.5` (midpoint), `!= 2.0` (nearest/higher).
Asserts `PERCENTILE_METHOD == "linear"`.
*Why*: F11. Percentile conventions differ; picking one silently produces
slightly-wrong ranges forever. This test is the written-down decision.

**A6 · `test_p25_never_exceeds_median_never_exceeds_p75`**
Hypothesis property over `lists(floats(1, 100_000), min_size=1, max_size=500)`.
Asserts `p25 <= median <= p75` and `min <= p25` and `p75 <= max`.
*Why*: partial kill for the p25/p75 swap mutant (V52); A5 is the full kill.

**A7 · `test_percentiles_are_rounded_half_up_to_two_places_on_storage`**
`percentiles` returns unrounded floats; `Aggregate` stores `Decimal` rounded
`ROUND_HALF_UP` to 2 dp, matching `NUMERIC(12,2)`. Two input pairs, because one
cannot separate two different faults:

- `[1.125, 1.125]` asserts `Decimal("1.13")`, not `1.12`. This pins the rounding
  **mode**. 1.125 is exactly representable, so the conversion path cannot affect it.
- `[1.005, 1.005]` asserts `Decimal("1.01")`, not `1.00`. This pins the conversion
  **path**. The code must build the `Decimal` from `str`, because `Decimal(1.005)`
  is `1.00499999…` and `ROUND_HALF_UP` then gives `1.00`.

Asserts the unrounded value is available separately for the differential test in
§4. The `str` conversion is part of the surface contract, not an implementation
choice. See plan §0.4 and §4.3.

### Block B — price per m² and bands

**B1 · `test_price_per_m2_is_price_divided_by_area`**
300 000 PLN over 2 500 m² asserts `120.00`. A single case, because V10 and V28
own unit conversion; this asserts only that the aggregate layer consumes an
already-normalised area and does not re-convert.

**B2 · `test_band_boundaries_are_lower_inclusive`**
Asserts, one per case: `799.99 → "<800"`, `800 → "800-1500"`,
`1499.99 → "800-1500"`, `1500 → "1500-3000"`, `3000 → "3000-10000"`,
`9999.99 → "3000-10000"`, `10000 → ">10000"`.
*Why*: an off-by-one at a band edge moves observations between aggregates
silently. The bands are re-centred by D48 — see §9.

**B3 · `test_every_area_in_the_validity_range_lands_in_exactly_one_band`**
Property test over areas **300..200 000 m²**, the accepted range of FR-12 and V10
after gap-analysis finding B1. Asserts exactly one band matches. *Why*: a gap in
the ladder silently drops a whole size segment.

### Block C — the aggregate object

**C1 · `test_aggregate_cannot_be_constructed_without_n_and_spread`**
Asserts `Aggregate(median_ppm2=...)` alone raises `TypeError`, and that
`fields(Aggregate)` shows no default for `n`, `p25_ppm2`, `p75_ppm2`, `min_ppm2`,
`max_ppm2`, `range_kind`, `as_of`, `source_ids`.
*Why*: V4 and rule 7, made structural. A bare number must be **unconstructible**,
not merely untested. Lives in `tests/architecture/`.

**C2 · `test_aggregate_carries_full_provenance`**
Asserts every returned aggregate has non-null `as_of`, non-empty `source_ids`,
`price_type`, `price_kind`, `series_kind` and `n` (rule 7, V5).

**C3 · `test_aggregate_groups_by_gmina_and_band`**
Fixture: C1–C5 in `TERYT_GMINA_A` plus one 2 000 m² observation at 300.00 ppm2 in
`TERYT_GMINA_B`. Asserts the result has one aggregate per non-empty
(gmina × band × class × buildability × price_type × price_kind × series_kind), that
`TERYT_GMINA_A / "1500-3000"` **stock** has `n == 2` and `median == 103.00`, and
that gmina B's 300.00 appears in no gmina A aggregate.
*Red*: an implementation grouping by gmina only produces one row per gmina.

The members of that band are **C1 (2 000 m², 96.00) and C2 (2 500 m², 110.00)**,
so the median is `(96 + 110) / 2 = 103.00`. Bands are lower-inclusive, so C3 at
exactly 3 000 m² belongs to `3000-10000`. An earlier version of this document named
C2 and C3 and expected 118.00; both halves of that were wrong, and 118.00 is the
flow figure from the comparable-set view. Plan §1.3 lists all four rows.

**C4 · `test_empty_group_produces_no_row_rather_than_a_zero`**
Asserts a (gmina × band) with no observations is **absent** from the result, and
that no aggregate anywhere has `n == 0`, `median == 0` or a null median. Absence
of data is absence, never zero (V13's rule applied here).

### Block D — the spread switch

**D1 · `test_spread_is_min_max_below_the_threshold`**
Fixture `[61, 96, 140, 240]` (n=4). Asserts `range_kind == "min_max"`,
`low == 61.00`, `high == 240.00`, **and** that `p25 == 87.25` / `p75 == 165.00` are
still stored (the schema requires all four percentile columns `NOT NULL`; only the
*displayed* range switches).
This is the `CLAUDE.md` rule-6 example verbatim: `median 118, range 61–240, n=4`.

**D2 · `test_spread_is_iqr_at_and_above_the_threshold`**
Fixture `[61, 96, 140, 150, 240]` (n=5). Asserts `range_kind == "iqr"`,
`median == 140.00`, `low == 96.00`, `high == 150.00`.
*Red*: a `>` instead of `>=` at the threshold gives `min_max` here — this pair (D1,
D2) is the exact-boundary kill for that mutant.

**D3 · `test_spread_switch_reads_the_threshold_from_config`**
Asserts `SPREAD_THRESHOLD_N` is imported at the one place the switch is made, and
that monkeypatching it to 3 makes the n=4 fixture return `iqr`. No call site may
contain a literal 5.
*Why*: **D67 puts the threshold in configuration.** Changing it must stay a
one-line config change, not an audit of every call site — the same discipline V62
imposes on the flow window.

**D4 · `test_the_database_enforces_internal_consistency_and_not_the_threshold`**
The mirror of D3, at the integration layer. Two halves, both from D67:

1. Asserts the schema in [`15-database-schema.md`](../15-database-schema.md) §9
   contains **no** constraint naming the number 5. A row with
   `n = SPREAD_THRESHOLD_N - 1, range_kind = 'iqr'` **inserts**. The application
   layer owns the switch, and D2 is the test that owns it.
2. Asserts the constraints the database does carry reject bad rows:
   `range_bounds_ordered` rejects `p25 > median`, and `flow_states_its_window`
   rejects `series_kind = 'flow'` with a null `flow_window_days`.

*Why*: a threshold frozen in a migration cannot be changed without one. D67 moved
it out. This test stops it moving back in.

**D5 · `test_no_aggregate_is_ever_suppressed`**
Fixture with gminas at n = 1, 3, 4, 5, 10, 100. Asserts all six return a median
(none null, none an "insufficient data" marker), n < 5 carry `min_max`, n >= 5
carry `iqr`, and a full-text scan of the serialized output contains no
`"insufficient"`, `"brak danych"` or `"—"` string. This is V4 (a) verbatim.

A thin aggregate reaching the map renders **faded, with its `n` on the label**
(D113). This spec owns the number and the `n`; [`06-surface.md`](./06-surface.md)
owns the pixels. The two meet at one assertion here: the serialized aggregate
carries `n` as a separate field, so the label can print it.

**D6 · `test_a_source_with_no_spread_gives_range_kind_unavailable`**
A GUS sales aggregate publishes a central value and no spread. Asserts the
aggregate is built, `range_kind == "unavailable"`, `low is None`, `high is None`,
`n` is present, and that nothing raises (D69). Asserts the renderer emits the
explicit text *"Nie znamy rozrzutu — GUS publikuje tylko średnią"*, and that the
`range` field is present rather than dropped.
*Why*: rule 7 says show the absence. Erroring on correct data is not rule 7, and a
missing field is not rule 7 either. Plan §6.5 gives the fixture: median 130.00,
n 37, chosen so no offering figure can leak into it unnoticed.
D6 tests the aggregate and the render. It does not test storage, because such a row
cannot be stored today — see §10 question 7.

### Block E — the estimator contract

**E1 · `test_estimate_returns_all_six_fields_non_null`**
Property test over generated feature bundles against the canonical fixture.
Asserts `low`, `median`, `high`, `n`, `basis`, `widening_step` are all present and
non-null on every return (V17, FR-32).

**E2 · `test_estimate_over_the_canonical_fixture_pins_every_field`**
Subject: 3 000 m², `buildable`, `budowlana`, `offering`, `TERYT_GMINA_A`,
`as_of = 2026-08-08`. Candidates C1–C5. Asserts `n == 5`, `median == 126.00`,
`low == 110.00`, `high == 140.00`, `basis == "gmina"`,
`widening_step == "gmina"`, `range_kind == "iqr"`.

**E3 · `test_area_band_bounds_are_inclusive`**
Subject 3 000 m², so the ±50 % band (D108) is `[1500, 4500]`. Asserts a 1 500.00 m²
candidate is **in**, a 4 500.00 m² candidate is **in**, a 1 499.99 m² candidate is
**out**, a 4 500.01 m² candidate is **out**.

**E4 · `test_no_comparables_returns_an_absence_not_a_number`**
Subject in `TERYT_GMINA_B` with zero same-buildability candidates. Asserts the
return is an `Absence` with a reason, that it is not an `Estimate`, that it carries
no numeric price field at all, and — the load-bearing part — that **no widening
occurred**: gmina A's 126.00 appears nowhere in the result (V18 (b), and `18` §4's
exclusion of the ladder).

**E4b · `test_a_thin_set_still_returns_an_estimate_and_records_why_it_was_not_widened`**
Subject with exactly **two** same-gmina comparables, `[110, 140]`. Asserts an
`Estimate` with `n == 2`, `median == 125.00`, `range_kind == "min_max"`,
`low == 110.00`, `high == 140.00`, and `widening_step == "gmina"`. Asserts the
result records `below_min_comparables == True`, because 2 is under
`MIN_COMPARABLES_BEFORE_WIDENING` (3, D109), and that v0 widens nothing.
*Why*: D109 sets the threshold at three and states the cost — a median of three
plots is close to noise. The answer to that is the `n` and the range beside it, not
suppression.

**E8 · `test_an_observation_outside_the_recency_window_is_excluded`**
Candidates C1–C5 plus **decoy D6** (`observed_at` 2025-01-15, 400.00 ppm2). It passes every
other filter, so recency is the only thing that can exclude it. Asserts `n == 5`,
`median == 126.00`, `max == 150.00`. The leak gives `n == 6`, `median == 133.00`,
`max == 400.00`; both wrong values are asserted against by name. Companion:
monkeypatching `RECENCY_MONTHS` to 24 admits decoy D6 and gives exactly those leak
values, which proves the exclusion is the 12-month rule (D110) and not an accident
of another filter. Plan §6.4.
*Why*: no other test in this document admits decoy D6, so the dropped-recency-filter
mutant had no killer before this one.

**E5 · `test_buildability_is_matched_exactly_and_never_relaxed`**
Candidates C1–C5 plus D3 (`agricultural`, 12.00) and D4 (`unknown`, 60.00).
Asserts the estimate is byte-identical to E2's, and separately that an `unknown`
subject draws only on `unknown` candidates and never on `buildable` ones
(V18, FR-34, D28).

**E6 · `test_verdict_is_relative_to_the_range_not_the_median`**
Against E2's estimate (low 110, high 140): observed `142.00 → "above"`,
`126.00 → "within"`, `100.00 → "below"`, `110.00 → "within"` (inclusive lower
bound), `140.00 → "within"` (inclusive upper bound). Asserts the returned object
carries **no** percentage-deviation-from-median field (FR-38).

**E7 · `test_excluding_a_comparable_recomputes_the_estimate_and_logs_it`**
Excluding C1 (96.00) from E2's set leaves `[110, 126, 140, 150]`. Asserts the
recomputed `median == 133.00`, `n == 4`, `range_kind == "min_max"`,
`low == 110.00`, `high == 150.00`, and that an exclusion log row records the
subject, the excluded comparable and the estimate delta `+7.00` (FR-36, V51c).

---

## 4. Differential testing of percentiles (V48, `20` §4.4)

`tests/unit/metrics/test_percentiles_differential.py`. Reference:
`numpy.percentile(values, [25, 50, 75], method="linear")` and `numpy.median`.
numpy is a **test-only** dependency; an architecture test asserts
`src/lpc/metrics/` does not import it, so the reference stays independent of the
code it checks.

**F1 · `test_matches_numpy_on_random_arrays`**
Hypothesis: `lists(floats(min_value=1, max_value=100_000, allow_nan=False,
allow_infinity=False), min_size=1, max_size=500)`. Asserts
`math.isclose(ours, ref, rel_tol=1e-12, abs_tol=1e-9)` for each of median, p25,
p75, on the **unrounded** values.

**F2 · `test_matches_numpy_on_even_length_arrays`**
Same, with `min_size`/`max_size` constrained to even lengths, and a filter
rejecting odd draws. Called out separately because even-length medians are where
the "middle element" bug lives and a random-length strategy can under-sample it.

**F3 · `test_matches_numpy_under_heavy_ties`**
Hypothesis draws from a five-element pool (`sampled_from([50.0, 100.0, 100.0,
100.0, 250.0])`), lists of length 1..200, so most arrays are mostly ties. Asserts
the same closeness. *Why*: interpolation between two identical values is where
rank-based and interpolating conventions coincide, hiding a definition error that
appears only on distinct values — and vice versa.

**F4 · `test_matches_numpy_at_n_1_2_4_5`**
Explicitly parametrised, not left to Hypothesis:
`[118]`, `[100, 200]`, `[61, 96, 140, 240]`, `[96, 110, 126, 140, 150]`.
Asserts equality with numpy for all three statistics on each. n=1 and n=2 are the
degenerate cases; n=4 and n=5 straddle the spread switch, so a differential failure
there would also be a wrong displayed range.

**F5 · `test_rounded_output_matches_rounded_reference_exactly`**
Asserts `Decimal` equality (not approximate) between our stored 2-dp value and the
reference rounded the same way, over the F1 corpus. Catches a rounding mode
difference that `isclose` would swallow.

**F6 · `test_reference_disagrees_with_a_deliberately_wrong_convention`**
A negative control: a locally defined nearest-rank percentile is asserted to
**differ** from numpy on `[1, 2, 3, 4]`. If this test ever passes vacuously the
differential suite has stopped comparing anything.

---

## 5. The metamorphic suite (V47, `20` §4.3)

`tests/unit/metrics/test_metamorphic.py`. All eight relations, each as an
executable test over the canonical fixture. No oracle is used — these are
relations between outputs, which is exactly why they work where ground truth does
not exist.

**M1 · `test_doubling_every_price_doubles_the_median_exactly`**
Multiply every `price_pln` by 2, leave areas alone. Asserts `median == 252.00`
(was 126.00), `p25 == 220.00`, `p75 == 280.00`, `min == 192.00`, `max == 300.00`,
and `n == 5` unchanged. Exact equality, not approximate — doubling is exact in
binary floating point at these magnitudes.

**M2 · `test_scaling_price_and_area_together_leaves_price_per_m2_unchanged`**
Multiply every `price_pln` **and** every `area_m2` by 10, and scale the subject
with them (3 000 → 30 000 m², window `[15000, 45000]`). Asserts the whole
`Aggregate` is equal to the baseline on every statistic **in the comparable-set
view**, where the window scales with the subject and all five rows stay in.

The `metric_unit_month` view needs a second, separate assertion. The scaled rows
all land in `>10000`, so they collapse from two bands into one. There is no
baseline row to compare against, and the equality above does not hold there.
Assert the collapse instead: one stock row at n 5, median 126.00, and one flow row
at n 4, median 118.00. Plan §M2 gives both tables. An earlier version of this
document asked for equality "on the aggregate for the band the scaled observations
now occupy", which no baseline row supplies.

The trap the test exists for is still there: an implementation that scales one and
not the other passes a naive version of this test.

**M3 · `test_permuting_input_order_changes_nothing`**
Hypothesis `permutations()` over the fixture, 100 examples. Asserts the returned
list of `Aggregate` objects, sorted by key, is equal to the baseline — full
dataclass equality, not just the median. Catches order dependence in grouping,
dedup and tie-breaking.

**M4 · `test_an_exact_duplicate_leaves_the_median_and_n_unchanged`**
Add an exact copy of **C1** (96.00). Asserts, after dedup, `n == 5` and
`median == 126.00`, with `duplicate_count == 2` on C1's cluster (V56).
`test_the_duplicate_property_is_not_vacuous` is its companion: with dedup disabled
the same input gives `n == 6` and `median == 118.00`. C1 is chosen deliberately —
duplicating the middle value would leave the median at 126.00 either way and the
test would pass against a broken dedup.

**M5 · `test_an_out_of_band_observation_leaves_the_estimate_unchanged`**
Add D1 (1 400 m², 30.00) and D2 (4 600 m², 400.00) to the E2 subject's candidate
pool. Asserts the `Estimate` is equal to E2's on all six fields — in particular
`n == 5`, not 7, and `median == 126.00`, not 126.00-by-coincidence: the decoys are
placed on both sides so a filter that drops only one of them still shifts the
median (with only D1: `[30, 96, 110, 126, 140, 150]` → 118.00; with only D2:
`[96, 110, 126, 140, 150, 400]` → 133.00). Both wrong answers are asserted against
by name.

**M6 · `test_a_wrong_buildability_observation_leaves_the_estimate_unchanged`**
Add D3 (`agricultural`, 12.00) and D4 (`unknown`, 60.00). Same equality assertion,
and explicitly `median != 118.00` and `median != 110.00` (the values a leak would
produce). D28's rule, tested as a relation rather than a fixture.

**M7 · `test_shifting_observations_and_the_window_together_gives_the_same_result`**
Shift every `first_seen` and `observed_at` forward by one month **and** shift
`as_of` by one month. Asserts identical output. Includes a month-boundary case:
an observation at `2026-06-30 23:30 Europe/Warsaw` (= `21:30Z`) must land in June,
not July, both before and after the shift (F10).

**M8 · `test_a_far_outlier_moves_the_median_little_and_the_mean_a_lot`**
Add one observation at 5 000.00 ppm2. Asserts `median == 133.00` (a shift of
7.00 from 126.00) while the arithmetic mean moves from 124.40 to 937.00. Asserts
the **published** figure is 133.00 and that 937.00 appears in no field of the
aggregate. Confirms the headline is the median (FR-24 stores `mean` too; this test
pins that it is never the one displayed).

### 5.1 Mutation kills (V52, `20` §4.8)

The mutants to be injected into `metrics/` and `valuation/`, and the test that must
fail for each. A surviving mutant here is a suite defect, not a code defect.

| Mutant | Killed by |
|---|---|
| Swap `p25` and `p75` | A5, D2, E2 |
| `n >= 5` → `n > 5` in the spread switch | D2 |
| Drop the area-band filter | M5, E3 |
| Drop the buildability filter | M6, E5 |
| Drop the price-type filter | §6.1 P1 |
| Drop the price-kind filter | §6.3 P5 |
| Drop the recency filter | **E8** (decoy D6 leaks) — P2 is an architecture test and cannot see a recency leak |
| `median` → `mean` | M8, A1 |
| Flow window → stock set | §7 S1 |
| Skip dedup | M4 |
| Include the held-out listing in LOOCV | §8 L2 |
| `low`/`high` from p25/p75 regardless of n | D1 |
| `range_kind = 'unavailable'` raises instead of storing | D6 |
| Suppress an aggregate below `MIN_COMPARABLES_BEFORE_WIDENING` | E4b |

Plan §7 carries the full table: 24 mutants, each with the exact wrong value it
produces. Use that one when running mutation testing.

---

## 6. Offering and sales never mix (rule 6, V2, V20, FR-8, FR-37)

`tests/unit/metrics/test_price_separation.py`.

### 6.1 Aggregation

**P1 · `test_offering_and_sales_produce_separate_aggregates_and_nothing_between`**
V2's fixture, reused verbatim: one gmina, offering observations all at 200.00
PLN/m² with `price_kind = asking`, sales observations all at 100.00 PLN/m² with
`price_kind = transaction` (D68). Asserts the offering aggregate's
median is `200.00`, the sales aggregate's is `100.00`, and — the assertion that
does the work — that a scan over **every numeric field of every returned
aggregate** finds no value equal to `150.00`, the blended mean.

**P2 · `test_the_aggregation_key_includes_price_type`**
Architecture test: asserts `price_type` is a component of the grouping key, and
that the primary key of `metric_unit_month` is `(teryt_unit, month, asset_class,
buildability, price_type, price_kind, series_kind, area_band, generation)` — the
key D66 extended, quoted from [`15-database-schema.md`](../15-database-schema.md)
§9. `unit_level` is not in the key, because `teryt_unit` determines it.
*Why*: making the separation structural is cheaper than testing for it forever.
Without `area_band`, `series_kind` and `price_kind` in the key, the stock row and
the flow row collide on insert and the second overwrites the first (D66).

### 6.2 No fallback

**P3 · `test_missing_sales_returns_an_absence_and_never_the_offering_figure`**
Fixture area with the canonical offering set and **zero** sales observations.
Asserts:
1. `estimate(..., price_type="sales")` returns an `Absence` whose reason is
   `no_sales_observations`;
2. `126.00`, `110.00`, `140.00`, `96.00`, `150.00` and `5` — every number from the
   offering estimate — appear nowhere in the sales result, recursively over its
   fields;
3. the rendered string is *"brak danych transakcyjnych"* and not a number
   (V20, FR-37, `05` §5).

**P4 · `test_no_code_path_substitutes_one_price_type_for_the_other`**
Architecture test: asserts no function in `metrics/` or `valuation/` takes a
`fallback_price_type` argument or contains a branch assigning a `sales` result
from an `offering` source, by walking the module AST for assignments across the
two literals.

### 6.3 Price kinds (V46, F9 — adjacent, and in the same aggregation key)

**P5 · `test_auction_prices_do_not_move_the_asking_median`**
Add D7 (`auction_start`, 40.00) to the canonical fixture. Asserts the `ask`
aggregate is unchanged (`median == 126.00`, `n == 5`) and that a separate
`auction_start` aggregate exists with `n == 1`, `median == 40.00`,
`range_kind == "min_max"`. An auction starting price is a statutory floor, not an
ask; blending them would drag every median down and look like a market move.

---

## 7. Stock vs flow (`20` §5, V45, V62, FR-67, D56)

`tests/unit/metrics/test_stock_vs_flow.py`. **The flow window is 90 days (D107).**
Every flow figure below states it, and S7 asserts that every flow figure carries it
at run time too.

Fixture: the canonical five, where **C5 is the stale overpriced listing** — first
seen 2025-04-02 (**493 days** before `as_of = 2026-08-08`), still active, 150.00
ppm2 — sitting among four cheaper listings first seen inside the 90-day window.

C5 is deliberately the **maximum** of the set: that is the bias `20` §5 describes,
where the plot that did not sell is still in the pool and the ones that sold have
left it. A fixture whose stale listing was cheap would produce a gap in the wrong
direction and the test would assert the opposite of the real failure mode.
Constructed answers:

**Comparable-set view** (window `[1500, 4500]`, flow window 90 days):

| | set | median | p25 | p75 | min | max | n | range_kind |
|---|---|---|---|---|---|---|---|---|
| **stock** | C1..C5 | **126.00** | 110.00 | 140.00 | 96.00 | 150.00 | 5 | `iqr` |
| **flow** | C1..C4 | **118.00** | 106.50 | 129.50 | 96.00 | 140.00 | 4 | `min_max` |

**`metric_unit_month` view** (the D66 key, fixed area bands):

| band | series | members | median | n | range_kind |
|---|---|---|---|---|---|
| 1500–3000 | stock | C1, C2 | **103.00** | 2 | `min_max` |
| 1500–3000 | flow | C1, C2 | **103.00** | 2 | `min_max` |
| 3000–10000 | stock | C3, C4, C5 | **140.00** | 3 | `min_max` |
| 3000–10000 | flow | C3, C4 | **133.00** | 2 | `min_max` |

The constructed gaps, all three, **stock the higher wherever it differs**:

| view | gap |
|---|---|
| comparable set | `126.00 − 118.00` = **8.00** |
| band 3000–10000 | `140.00 − 133.00` = **7.00** |
| band 1500–3000 | **0.00** — C5 is not in this band |

An earlier version of this document gave 8.00 as a property of "the aggregate". It
is the comparable-set gap. Plan §1.3, §1.4 and §3.1 carry the full tables.

**S1 · `test_the_stale_listing_lifts_the_stock_median_above_the_flow_median`**
Asserts `stock.median_ppm2 == Decimal("126.00")`,
`flow.median_ppm2 == Decimal("118.00")`, and
`stock.median_ppm2 - flow.median_ppm2 == Decimal("8.00")` as an explicit third
assertion, so the constructed relation is pinned and not merely implied by the two
values. Asserts the banded gaps too — **7.00** in `3000-10000` and **0.00** in
`1500-3000` — each naming its view. The 0.00 is not filler: a gap in *both* bands
would mean something other than C5 produces it. Asserts stock and flow both come
back from a single call — neither is optional.

**S2 · `test_both_series_are_labelled_and_neither_is_ever_unlabelled`**
Asserts `stock.series_kind == "stock"` and `flow.series_kind == "flow"`, that
`series_kind` has no default and no `None` member, and (architecture) that no
function in `metrics/` returns a bare `Percentiles` to a caller outside the module
— every value crossing the module boundary is an `Aggregate`, which carries the
label (V45 (c)).

**S3 · `test_flow_is_the_headline`**
Asserts `headline_aggregate(stock, flow) is flow` and that the rendering helper
places the flow figure first with stock explicitly secondary (D56). Asserts the
helper raises if handed only one of the two.

**S4 · `test_stock_and_flow_are_never_averaged`**
Asserts no returned field equals `122.00` (the mean of 126 and 118), and that no
function accepts both aggregates and returns a single number. The mirror of P1's
`150.00` assertion.

**S5 · `test_removing_the_stale_listing_collapses_the_gap`**
Drop C5. Asserts stock and flow are now equal on every statistic
(`median == 118.00` both) and the gap is `0.00`. *Why*: proves S1's gap is caused
by the stale listing and not by an unrelated difference in how the two sets are
built.

**S6 · `test_flow_window_boundary_is_inclusive_and_read_from_config`**
With `as_of = 2026-08-08` and the 90-day window (D107), the boundary is
2026-05-10. Asserts a listing first seen 2026-05-10 is **in** flow, one first seen
2026-05-09 is **out**, and that monkeypatching `FLOW_WINDOW_DAYS` to 30 moves C1
(2026-06-20) out of flow — giving `flow.n == 3` and `flow.median == 126.00`
(`[110, 126, 140]`). No call site contains a literal 90 (V62 (a)). D107 fixes the
value; the constant still lives in configuration, so the sensitivity report can
vary it.

**S7 · `test_every_flow_figure_carries_its_window_length`**
Asserts the serialized flow aggregate carries `flow_window_days == 90` and that the
rendering helper emits it next to the number (V62 (b), D107). A flow figure with no
stated window is meaningless. This is the run-time half of "state the window beside
every flow figure"; the prose half is this document.

**S8 · `test_window_sensitivity_report_covers_thirty_sixty_ninety_and_one_eighty`**
Asserts `flow_sensitivity(fixture)` returns flow medians at 30/60/90/180 days
(V62 (c)). The window itself is settled at 90 days (D107), so this report is now
evidence kept on the record, not an input to a pending choice. It still runs,
because a later change of window must be argued from measurements.

The canonical five cannot pin it: they give only two distinct medians across the
four windows (30 d → 126.00; 60/90/180 d → 118.00). S8 uses its own multi-month
fixture, `gmina_a_window_sensitivity.py`, with four distinct monotone medians —
**140.00 / 100.00 / 80.00 / 60.00** at 30 / 60 / 90 / 180 days. Plan §3.3 gives the
nine rows. An earlier version of this document named a fixture that did not exist.

---

## 8. The LOOCV harness (FR-69, V51, `20` §6.1)

`tests/unit/valuation/test_loocv_harness.py`.

### 8.1 What it computes

`run_loocv(corpus, estimator) -> LoocvReport` holds out each listing in turn,
rebuilds its comparable set from the remainder, estimates, and compares to the
listing's actual asking price per m². Reported per run:

| Field | Definition pinned by the tests |
|---|---|
| `n_total` | listings in the corpus |
| `n_estimable` | folds where the estimator returned an `Estimate` (n ≥ 1) rather than an `Absence` |
| `coverage` | `n_estimable / n_total` |
| `hit_rate` | share of **estimable** folds where `low <= actual <= high`, inclusive |
| `median_ape` | median over estimable folds of `abs(actual - estimate.median) / actual` |
| `tail_over_2x` | share of estimable folds where `max(actual/est.median, est.median/actual) > 2.0`, **strictly** greater |
| `by_area_band` | every metric above, broken down by the subject's band |
| `widening_profile` | folds per widening step — in v0 always `{"gmina": n_estimable}` |

`coverage` uses `n_total` as denominator; every other metric uses `n_estimable`.
The report carries both counts so the two denominators can never be confused by a
reader.

### 8.2 How the harness is tested itself

The harness is code that judges code, so it needs its own known answers. Each test
below uses a **stub estimator** and a synthetic corpus whose metrics are computed
by hand in the fixture header.

**L1 · `test_metrics_are_exact_against_a_stub_estimator`**
Corpus of 12 listings. One sits alone in `TERYT_GMINA_C` with no comparables, so
its fold returns an `Absence`. The other 11 have actual ppm2
`[60, 90, 100, 110, 120, 130, 140, 150, 160, 240, 480]`, and the stub returns
`low=100, median=120, high=140` for every fold. Asserts, each on its own line:

- `n_total == 12`, `n_estimable == 11`
- `coverage == Fraction(11, 12)`
- `hit_rate == Fraction(5, 11)` — the five inside `[100, 140]`: 100, 110, 120,
  130, 140, with both endpoints inside, pinning inclusivity
- `median_ape == 0.20` exactly — the 11 APEs sort to
  `[0, .0769, .0909, .1429, .20, .20, .25, .3333, .50, .75, 1.00]` and the sixth is
  `0.20`
- `tail_over_2x == Fraction(1, 11)` — only 480 (ratio 4.0). **60 and 240 both give
  a ratio of exactly 2.0 and must not count**, which pins the strict inequality
  with two boundary cases rather than one

**L2 · `test_the_held_out_listing_never_enters_its_own_comparable_set`**
The load-bearing test. Corpus: C1–C5 plus X at 5 000.00 ppm2, real estimator.
Asserts that in X's fold `n == 5`, `median == 126.00`, `low == 110.00`,
`high == 140.00`, and explicitly `median != 133.00` — the value leakage would
produce. Asserts that in C3's fold the set is `[96, 110, 140, 150, 5000]` giving
`median == 140.00`, `p25 == 110.00`, `p75 == 150.00`, `n == 5` — so the harness is
shown to remove exactly one listing, not the wrong one and not two.

**L3 · `test_hit_rate_is_one_for_a_perfect_estimator`**
Stub returning `low = median = high = actual`. Asserts `hit_rate == 1.0`,
`median_ape == 0.0`, `tail_over_2x == 0.0`.

**L4 · `test_hit_rate_is_zero_and_tail_is_one_for_an_absurd_estimator`**
Stub returning `low = median = high = 0.01` for every fold. Asserts
`hit_rate == 0.0` and `tail_over_2x == 1.0`. L3 and L4 together catch an inverted
comparison, which L1 alone would not — a flipped `<=` can still produce a
plausible-looking middling hit rate.

**L5 · `test_unestimable_folds_count_in_coverage_only`**
Extends L1's corpus with three more comparable-less listings whose actual prices
are absurd (`[1.0, 9999.0, 5.0]`). Asserts `coverage == Fraction(11, 15)` while
`hit_rate`, `median_ape` and `tail_over_2x` are **unchanged** from L1. *Why*: an
implementation that silently scores unestimable folds as misses makes the hit rate
depend on data thinness rather than on the estimator.

**L6 · `test_report_is_deterministic`**
Two runs over the same corpus produce equal reports, including `by_area_band`
ordering. Asserts no RNG is seeded inside the harness and no set iteration reaches
the output. LOOCV is a regression gate (O25); a report that wobbles cannot be one.

**L7 · `test_by_area_band_breakdown_isolates_size_correlated_error`**
Corpus of nine listings in three gminas, one per band, all exact except the
`>10000` pool. Asserts the overall `median_ape == 0` while
`by_area_band[">10000"].median_ape == Fraction(1, 4)` and that band's `hit_rate`
is `Fraction(2, 3)` against an overall `Fraction(8, 9)`. Plan §5.7 gives the nine
rows and every fold.

*Why*: this breakdown is the evidence O6 requires before any size adjustment ships
(`05` §4) — the aggregate number would hide exactly the signal the decision needs.
An overall median APE of exactly 0 beside a band at 1/4 shows that as starkly as a
number can.

An earlier version of this document asked for `median_ape == 1.0` in that band. A
leave-one-out **median** estimator reaches an APE of 1.0 only when the estimate is
exactly twice the actual, which cannot hold for most folds drawn from one pool. The
target was unreachable, so the test could never have gone green.

**L8 · `test_regression_against_a_recorded_baseline_fails_and_absence_of_baseline_reports`**
Two cases. With a committed baseline fixture, a report whose `hit_rate` falls
materially below it makes the CI check **fail**. With no baseline present, the
check **reports and passes**, writing the actuals. This is O25's procedure —
thresholds are set from the first run, never guessed — made executable.

**L9 · `test_loocv_reruns_when_comparable_logic_changes`**
Asserts the CI job's trigger set includes `metrics/`, `valuation/comparables.py`,
`valuation/estimator.py` and `metrics/config.py`, so a change to the band
tolerance, the recency window or the spread threshold cannot land without the
harness re-running (V51 "re-run on any change to comparable selection, banding or
aggregation").

### 8.3 What LOOCV does not establish — asserted, not merely written down

**L10 · `test_report_carries_its_own_limitation`**
Asserts `LoocvReport.limitation` is non-empty and states that the harness proves
consistency of *asking-price* prediction, not that asking prices are fair; and
that the rendering helper prints it alongside the metrics. A uniformly overpriced
corpus scores perfectly here. Price **level** is constrained only by V16 against
GUS, and neither check is tier D.

---

## 9. Parameters carried by this spec, and where they live

Every parameter is ratified. Each is still pinned by a test that reads it from
`metrics/config.py` rather than from a literal, so a later change stays a config
change plus a fixture update.

| Parameter | Value | Settled by | Tests that hold its expected values |
|---|---|---|---|
| Spread switch threshold | `n = 5`, in configuration | **D67** | D1, D2, D3, D4, F4 |
| Area band tolerance | ±50 % | **D108** | E3, M5 |
| Recency window | 12 months | **D110** | E2, E8 |
| Minimum comparables before widening | 3 | **D109** | E4b |
| Area bands | `<800 / 800–1500 / 1500–3000 / 3000–10000 / >10000` m² | D48 | B2, B3, C3, L7 |
| Flow window | 90 days | **D107** | S1, S5, S6, S7, S8 |

Two of these carry a consequence worth naming rather than burying.

**The n = 5 switch decides how a thin gmina reads.** Below it the spread shows as
min–max, at and above it as an IQR. D67 moved the number out of the database, so
the config constant and the UI are the only two places that hold it. D3 and D4
enforce that split.

**Three comparables is a thin basis and D109 says so.** The median of three plots is
close to noise. This spec never suppresses such a figure and never dresses it up:
it ships with `n`, with its range, and — on the map — faded with the count on the
label (D113).

## 10. The two questions still open (rule 2)

Five of the seven questions this document has carried are answered. Two are not, and
neither blocks work item 10.

| # | Question | Status |
|---|---|---|
| 1 | Median APE denominator | **Closed by gap-analysis B4** — the estimate **median**, in `20` §6.1 and `05` §9 alike. §8 uses it throughout |
| 2 | `metric_unit_month` primary key | **Closed by D66** — the key gains `area_band`, `series_kind` and `price_kind`. P2 asserts the extended key; the migration is a precondition of Block C |
| 3 | Field name for stock and flow | **Closed by D66** — `series_kind`, in the schema, the API and the UI |
| 4 | Flow window length | **Closed by D107** — 90 days, stated beside every flow figure |
| 6 | `price_kind` for a sales row | **Closed by D68** — `transaction` |
| 5 | Rounding point | **Open.** See below |
| 7 | Storage of a `range_kind = 'unavailable'` row | **Open, new.** See below |

**5 · Rounding point.** This spec rounds once, on storage, `ROUND_HALF_UP` to 2 dp
through `str` (A7). If the API rounds a second time, `stock − flow == 8.00` in S1
becomes fixture-dependent and can read 7.99. The question is not what this document
does, which is settled; it is whether
[`06-surface.md`](./06-surface.md) adds a second rounding boundary. That document
owns the answer.

**7 · Storage of a D69 row.** `metric_unit_month` declares `p25_ppm2`, `p75_ppm2`,
`min_ppm2` and `max_ppm2` as `NOT NULL` (`15` §9). A row with
`range_kind = 'unavailable'` has none of them, so it cannot be written as the schema
stands. D69 settles the shape and the copy; it does not settle the columns. D6 tests
the shape and does not touch storage. Two ratified decisions disagree here, and the
schema change is the owner's to take.

**No test in this document is blocked.** Work item 10 can start.

---

## 11. Definition of done for work item 10

Per [`16-repository-layout.md`](../16-repository-layout.md) §6, all of:

1. Blocks A–E, §4, §5, §6, §7 green, each written before its implementation and
   observed failing first.
2. §8's harness green, and a first LOOCV run over the real corpus recorded as the
   baseline (O25).
3. Mutation run over `metrics/` and `valuation/` with **zero survivors** from
   §5.1's table (V52).
4. Every aggregate reaching the surface carries `n`, spread, `price_type`,
   `price_kind`, `series_kind`, `as_of` and `source_ids` — enforced by C1, C2 and
   S2, which are architecture tests rather than conventions.
5. Every flow figure states its window, 90 days (D107) — enforced by S7.
6. The `metric_unit_month` migration of D66 applied before Block C runs.
7. §10's remaining question, the rounding point, answered by `06-surface.md`
   before the API ships. It does not block this work item.
