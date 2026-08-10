# Test plan — aggregates and the comparable-set estimator (pass 2)

Pass 2 of [`04-aggregates-and-valuation.md`](../04-aggregates-and-valuation.md).
Pass 1 gave the red–green sequence; this document gives the **numbers a developer
types straight in**. Every fixture row, every transformed fixture, every expected
statistic and every LOOCV fold below was computed by hand and re-checked against an
independent R-7 percentile implementation.

Nothing here is approximate. If a value in this document disagrees with what the
code produces, one of them is wrong and the disagreement is the finding.

Reads with: [`00-decisions.md`](../../00-decisions.md) batches 15, 20 and 21;
[`00-gap-analysis.md`](../00-gap-analysis.md);
[`05-analytics-methodology.md`](../../05-analytics-methodology.md) §3, §5, §9;
[`20-verification-strategy.md`](../../20-verification-strategy.md) §4.3, §4.4, §4.8, §5, §6.1;
[`04-validation.md`](../../04-validation.md) V2, V4, V45, V47, V48, V51, V62.

**Every parameter below is ratified.** No value in this plan is provisional.

| Decision | What it settles |
|---|---|
| **D66** | `metric_unit_month` is keyed by `area_band`, `series_kind` and `price_kind` as well. Stock and flow are separate rows |
| **D67** | The n=5 spread threshold lives in configuration. The database enforces internal consistency only |
| **D68** | `price_kind` gains `transaction`, so a sales row has a legal kind |
| **D69** | `range_kind` gains `unavailable`, for a source that publishes a central value and no spread |
| **D107** | The flow window is **90 days**. Every flow figure states it |
| **D108** | The comparable size band is **±50 %** |
| **D109** | The search widens beyond the gmina below **three** comparables |
| **D110** | Comparable recency is **12 months** |
| **D113** | A thin map tile renders **faded**, with the count on the label |

**§9 lists eleven arithmetic and definitional defects this pass found in pass 1.**
Pass 1 now carries the corrected values in place, so the two documents state one
value per test. §9 remains as the record of what was wrong and why.

---

## 0. Conventions every number below depends on

Fix these first; nothing else is well-defined without them.

### 0.1 The percentile function — R-7, "linear"

For sorted `x[0..n-1]` and quantile `q`:

```
h        = (n - 1) * q
lo       = floor(h)
hi       = min(lo + 1, n - 1)
result   = x[lo] + (h - lo) * (x[hi] - x[lo])
n == 1   → result = x[0]     (all five statistics equal, never an error)
```

This is `numpy.percentile(..., method="linear")`, R's `type=7`, and the default in
both. `PERCENTILE_METHOD == "linear"` is asserted as a literal so the choice is a
written-down decision rather than an implementation accident (A5, F11).

The index arithmetic used throughout, spelled out once:

| n | p25 | median | p75 |
|---|---|---|---|
| 1 | `x[0]` | `x[0]` | `x[0]` |
| 2 | `x0 + 0.25·(x1−x0)` | `x0 + 0.50·(x1−x0)` | `x0 + 0.75·(x1−x0)` |
| 3 | `x0 + 0.50·(x1−x0)` | `x[1]` | `x1 + 0.50·(x2−x1)` |
| 4 | `x0 + 0.75·(x1−x0)` | `x1 + 0.50·(x2−x1)` | `x2 + 0.25·(x3−x2)` |
| 5 | `x[1]` | `x[2]` | `x[3]` |
| 6 | `x1 + 0.25·(x2−x1)` | `x2 + 0.50·(x3−x2)` | `x3 + 0.75·(x4−x3)` |
| 7 | `x1 + 0.50·(x2−x1)` | `x[3]` | `x4 + 0.50·(x5−x4)` |

### 0.2 Two different area mechanisms, never conflated

Pass 1 uses one word ("band") for two different things. They give different
answers on the same fixture and both are needed.

| | **Fixed area band** | **Comparable window** |
|---|---|---|
| Used by | `metric_unit_month` rows (D66 key) | `select_comparables` |
| Definition | `<800 / 800–1500 / 1500–3000 / 3000–10000 / >10000` m², lower-inclusive | `[0.5 · subject_area, 1.5 · subject_area]`, **both ends inclusive** |
| Constant | `AREA_BANDS` (D48) | `AREA_BAND_TOLERANCE = 0.50` (**D108**) |
| On the canonical fixture | **two** bands, four rows (see §1.3) | **one** set of five (see §1.4) |

Wherever a number below could belong to either, the view is named.

### 0.2b The widening threshold — three comparables (D109)

`MIN_COMPARABLES_BEFORE_WIDENING = 3`. The ladder it drives ships after v0, so in
v0 the constant has one visible effect: a set of one or two comparables still
returns an `Estimate`, flagged `below_min_comparables`, and nothing widens.

D109 records the cost in the owner's own terms. **The median of three plots is close
to noise.** Rule 7 answers that with the `n` and the range beside every figure, and
D113 answers it on the map with a faded tile carrying the count on its label. Nothing
here suppresses a thin figure. §1.6's `SPREAD_N1` and `SPREAD_N3` are the fixtures.

### 0.3 Recency filters `observed_at`; flow filters `first_seen`

This is the whole stock/flow mechanism and it is why C5 (first seen 493 days before
`as_of`) is inside the 12-month recency window while being outside the 90-day flow
window. Getting these two columns crossed produces a fixture that cannot be
satisfied.

- **Recency** (`RECENCY_MONTHS = 12`, **D110**): `observed_at >= as_of − 12 months`.
  Cutoff for `as_of = 2026-08-08` is **2025-08-08**.
- **Flow** (`FLOW_WINDOW_DAYS = 90`, **D107**): `first_seen >= as_of − 90 days`.
  Cutoff for `as_of = 2026-08-08` is **2026-05-10**, inclusive. State the window
  beside every flow figure — in this document, in the API and in the UI.
- **Stock**: `active == True` at `as_of`, subject to recency.

Verified day counts from `as_of = 2026-08-08`: 30 d → 2026-07-09, 60 d → 2026-06-09,
90 d → 2026-05-10, 180 d → 2026-02-09.

### 0.4 Rounding — one boundary, and a float trap

Storage rounds `ROUND_HALF_UP` to 2 dp (`NUMERIC(12,2)`); `percentiles()` returns
unrounded for the differential test. **The conversion must go through `str`, not
through the binary float**, or `ROUND_HALF_UP` silently becomes truncation:

```python
Decimal(1.005).quantize(Decimal("0.01"), ROUND_HALF_UP)     # Decimal('1.00')  ← wrong
Decimal("1.005").quantize(Decimal("0.01"), ROUND_HALF_UP)   # Decimal('1.01')  ← required
```

because `1.005` as a double is `1.00499999999999989…`. Pass 1's A7 asserts `1.01`
from input `[1.005, 1.005]` and will fail against a correct-looking implementation
for this reason alone. See §9 defect **P1-3**.

`1.125` and `0.125` are exactly representable and discriminate rounding **mode**
without the float trap: HALF_UP gives `1.13` / `0.13`, HALF_EVEN gives `1.12` /
`0.12`. Use both pairs — one pins the mode, one pins the conversion path.

### 0.5 Inclusivity and tie-breaking, stated once

| Rule | Pinned by |
|---|---|
| Area bands are **lower-inclusive**: `[lower, upper)` | B2 |
| The comparable window is **closed at both ends**: `[0.5a, 1.5a]` | E3 |
| The flow window is **closed at its old end**: `first_seen >= cutoff` | S6 |
| The spread switch is `n >= SPREAD_THRESHOLD_N` → `iqr`, read from config (D67) | D1/D2, D3, D4 |
| A source with no spread gives `range_kind = 'unavailable'`, never an error (D69) | D6 (§6.5) |
| Below `MIN_COMPARABLES_BEFORE_WIDENING = 3` the estimate still ships (D109) | E4b |
| A hit is `low <= actual <= high` — **both bounds inclusive** | K3, K6, B1, B2 (§7) |
| The tail is `ratio > 2` — **strictly** greater; `ratio == 2` is not a tail | K1, K8 (§7) |
| Ratios and rates are computed as `Fraction`, never float | §7.4 |
| Ties among equal ppm2 values must not affect output; sort is on value only | M3 |

---

## 1. The canonical fixture, literally

`tests/fixtures/synthetic/gmina_a_buildable_offering.py`.

Constants: `as_of = 2026-08-08`, `teryt = TERYT_GMINA_A` (the rural Skierniewice code
from the V30 known-answer fixture — imported, never a literal in a test module),
`asset_class = budowlana`, `unit_level = gmina`, `month = 2026-08`.

### 1.1 The five rows

| id | gmina | area m² | price PLN | **ppm2** | first_seen | observed_at | active | buildability | price_type | price_kind |
|---|---|---|---|---|---|---|---|---|---|---|
| C1 | A | 2 000 | 192 000 | **96.00** | 2026-06-20 | 2026-08-08 | yes | buildable | offering | asking |
| C2 | A | 2 500 | 275 000 | **110.00** | 2026-07-11 | 2026-08-08 | yes | buildable | offering | asking |
| C3 | A | 3 000 | 378 000 | **126.00** | 2026-07-30 | 2026-08-08 | yes | buildable | offering | asking |
| C4 | A | 3 600 | 504 000 | **140.00** | 2026-08-04 | 2026-08-08 | yes | buildable | offering | asking |
| C5 | A | 4 400 | 660 000 | **150.00** | 2025-04-02 | 2026-08-08 | yes | buildable | offering | asking |

Every `price ÷ area` is exact: 192000/2000 = 96, 275000/2500 = 110, 378000/3000 = 126,
504000/3600 = 140, 660000/4400 = 150. No repeating decimal enters the fixture, so
every downstream statistic is exact in `Decimal` and in binary float alike.

**C5 is the stale overpriced listing** and it is deliberately the **maximum** of the
set — that is the direction of the stock/flow bias described in `20` §5. It was first
seen **493 days** before `as_of` (see §9 defect **P1-2**), which puts it outside every
flow window in this document while remaining inside the 12-month recency window
(D110) on `observed_at`.

`price_kind` is **`asking`**, matching the enum `{asking, auction_start, tender,
transaction}` — D65 plus D68. See §9 defect **P1-4**.

### 1.2 Membership of each filter, per row

The table a developer checks a filter against without re-deriving anything.

| id | area band | in comparable window of a 3 000 m² subject `[1500, 4500]` | in flow (cutoff 2026-05-10) | in recency (cutoff 2025-08-08) |
|---|---|---|---|---|
| C1 | 1500–3000 | yes (2 000) | yes (2026-06-20) | yes |
| C2 | 1500–3000 | yes (2 500) | yes (2026-07-11) | yes |
| C3 | 3000–10000 | yes (3 000) | yes (2026-07-30) | yes |
| C4 | 3000–10000 | yes (3 600) | yes (2026-08-04) | yes |
| C5 | 3000–10000 | yes (4 400 ≤ 4 500) | **no** (2025-04-02) | yes (`observed_at` 2026-08-08) |

C5 at 4 400 m² sits 100 m² inside the window's upper edge — deliberately close, so an
implementation that computes `1.5 · area` in the wrong direction or rounds the bound
drops it and the estimate falls to n=4, median 118.00.

### 1.3 Expected `metric_unit_month` rows — the D66-keyed view

Key (D66): `(teryt_unit, month, asset_class, buildability, price_type, price_kind,
series_kind, area_band, generation)`, exactly as `15` §9 states it. `unit_level` is
not in the key, because `teryt_unit` determines it. Four rows, not one:

| area_band | series_kind | members | n | **median** | p25 | p75 | min | max | range_kind | displayed low | displayed high |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1500–3000 | stock | C1, C2 | 2 | **103.00** | 99.50 | 106.50 | 96.00 | 110.00 | `min_max` | 96.00 | 110.00 |
| 1500–3000 | flow | C1, C2 | 2 | **103.00** | 99.50 | 106.50 | 96.00 | 110.00 | `min_max` | 96.00 | 110.00 |
| 3000–10000 | stock | C3, C4, C5 | 3 | **140.00** | 133.00 | 145.00 | 126.00 | 150.00 | `min_max` | 126.00 | 150.00 |
| 3000–10000 | flow | C3, C4 | 2 | **133.00** | 129.50 | 136.50 | 126.00 | 140.00 | `min_max` | 126.00 | 140.00 |

All four percentile columns are stored `NOT NULL` even where `range_kind` is
`min_max` — only the **displayed** range switches (D1).

**Banded stock − flow gap in `3000–10000` = 140.00 − 133.00 = 7.00.**

### 1.4 Expected comparable-set aggregate — the estimator view

Subject: 3 000 m², `buildable`, `budowlana`, `offering`, `asking`, `TERYT_GMINA_A`,
`as_of = 2026-08-08`. Window `[1500, 4500]` admits all five.

| set | members | n | **median** | p25 | p75 | min | max | range_kind | low | high |
|---|---|---|---|---|---|---|---|---|---|---|
| stock | C1–C5 | 5 | **126.00** | 110.00 | 140.00 | 96.00 | 150.00 | `iqr` | 110.00 | 140.00 |
| flow | C1–C4 | 4 | **118.00** | 106.50 | 129.50 | 96.00 | 140.00 | `min_max` | 96.00 | 140.00 |

**Comparable-set stock − flow gap = 126.00 − 118.00 = 8.00.**
Arithmetic mean of C1–C5 = 622 / 5 = **124.40** (needed by M8; never displayed).

The 8.00 gap is the **estimator-view** gap. The D66-keyed rows give **7.00** in the
`3000–10000` band and **0.00** in `1500–3000`. S1 asserts all three, naming which is
which. Pass 1 now says the same. See §9 defect **P1-5**.

### 1.5 The decoys, literally

Every decoy is in `TERYT_GMINA_A`, `budowlana`, `active`, `observed_at = 2026-08-08`
and `first_seen = 2026-07-01` unless the row says otherwise.

| id | area m² | price PLN | ppm2 | buildability | price_type | price_kind | what makes it a decoy |
|---|---|---|---|---|---|---|---|
| D1 | 1 400 | 42 000 | **30.00** | buildable | offering | asking | 1 400 < 1 500 — below the window |
| D2 | 4 600 | 1 840 000 | **400.00** | buildable | offering | asking | 4 600 > 4 500 — above the window |
| D3 | 3 000 | 36 000 | **12.00** | agricultural | offering | asking | wrong buildability |
| D4 | 3 000 | 180 000 | **60.00** | unknown | offering | asking | wrong buildability |
| D5 | 3 000 | 210 000 | **70.00** | buildable | **sales** | **transaction** (D68) | wrong price type |
| D6 | 3 000 | 1 200 000 | **400.00** | buildable | offering | asking | `first_seen` 2024-12-10, `observed_at` **2025-01-15**, inactive — outside recency |
| D7 | 3 000 | 120 000 | **40.00** | buildable | offering | **auction_start** | wrong price kind |
| D8 | 3 000 | 1 200 000 | **400.00** | buildable | offering | asking | gmina **B** |

**What each decoy does if its filter leaks.** Every one is individually visible in
the median, which is why single-decoy tests are worth writing:

| leaking decoy | resulting set | n | median |
|---|---|---|---|
| D1 | `[30, 96, 110, 126, 140, 150]` | 6 | **118.00** |
| D2 | `[96, 110, 126, 140, 150, 400]` | 6 | **133.00** |
| D3 | `[12, 96, 110, 126, 140, 150]` | 6 | **118.00** |
| D4 | `[60, 96, 110, 126, 140, 150]` | 6 | **118.00** |
| D5 | `[70, 96, 110, 126, 140, 150]` | 6 | **118.00** |
| D6 | `[96, 110, 126, 140, 150, 400]` | 6 | **133.00** |
| D7 | `[40, 96, 110, 126, 140, 150]` | 6 | **118.00** |
| D8 | `[96, 110, 126, 140, 150, 400]` | 6 | **133.00** |
| **D1 and D2 together** | `[30, 96, 110, 126, 140, 150, 400]` | **7** | **126.00** ← unchanged |

The last row is the trap and the reason M5 puts decoys on **both** sides. A
symmetric leak leaves the median at 126.00 exactly. `n == 5`, `min == 96.00` and
`max == 150.00` are the load-bearing assertions there, not the median.

### 1.6 Reference fixtures used by the spread switch

| name | values | n | p25 | median | p75 | min | max | range_kind | low | high |
|---|---|---|---|---|---|---|---|---|---|---|
| `SPREAD_N1` | `[118]` | 1 | 118.00 | 118.00 | 118.00 | 118.00 | 118.00 | `min_max` | 118.00 | 118.00 |
| `SPREAD_N3` | `[96, 126, 150]` | 3 | 111.00 | 126.00 | 138.00 | 96.00 | 150.00 | `min_max` | 96.00 | 150.00 |
| `SPREAD_N4` | `[61, 96, 140, 240]` | 4 | 87.25 | **118.00** | 165.00 | 61.00 | 240.00 | `min_max` | **61.00** | **240.00** |
| `SPREAD_N5` | `[61, 96, 140, 150, 240]` | 5 | **96.00** | **140.00** | **150.00** | 61.00 | 240.00 | `iqr` | **96.00** | **150.00** |
| `SPREAD_N10` | `[10,20,…,100]` | 10 | 32.50 | 55.00 | 77.50 | 10.00 | 100.00 | `iqr` | 32.50 | 77.50 |
| `SPREAD_N100` | `[1, 2, …, 100]` | 100 | 25.75 | 50.50 | 75.25 | 1.00 | 100.00 | `iqr` | 25.75 | 75.25 |

| `SPREAD_GUS` | central 130.00, **no spread published** | 37 | — | 130.00 | — | — | — | `unavailable` | `None` | `None` |

`SPREAD_N4` is `CLAUDE.md` rule 7's own example: *median 118, range 61–240, n=4*.
`SPREAD_N4` / `SPREAD_N5` are the exact-boundary pair for the `>=`→`>` mutant, and
`SPREAD_N1`…`SPREAD_N100` are D5's no-suppression fixture. `SPREAD_N3` is also the
D109 case: three comparables, shown with `n` and a 96.00–150.00 range, never as a
bare 126.00.

`SPREAD_GUS` is the D69 case and it is the odd one. §6.5 gives it in full.

---

## 2. Metamorphic relations — transformed fixture, expected output, non-vacuity

`tests/unit/metrics/test_metamorphic.py`. Each relation below gives: the exact
transform, the exact expected output, and a **companion test that proves the
relation can fail**. Every companion uses `pytest.raises(AssertionError)` around the
relation's own assertion block, run against a deliberately broken stub or a disabled
filter — so the companion fails if the relation has become vacuous.

Baseline throughout is §1.4's estimator view unless stated: n=5, median 126.00,
p25 110.00, p75 140.00, min 96.00, max 150.00.

### M1 · Doubling every price doubles the median exactly

**Transform.** `price_pln × 2`, areas untouched.

| id | area m² | price PLN | ppm2 |
|---|---|---|---|
| C1 | 2 000 | 384 000 | 192.00 |
| C2 | 2 500 | 550 000 | 220.00 |
| C3 | 3 000 | 756 000 | 252.00 |
| C4 | 3 600 | 1 008 000 | 280.00 |
| C5 | 4 400 | 1 320 000 | 300.00 |

**Expected.** n **5** (unchanged), median **252.00**, p25 **220.00**, p75 **280.00**,
min **192.00**, max **300.00**, `range_kind` `iqr`. Exact equality, not `isclose` —
doubling is exact in binary at these magnitudes. Area bands are unchanged, so the
D66 rows are the §1.3 rows with every figure doubled.

**Non-vacuity · `test_m1_is_not_vacuous`.** Run M1's assertion block against a stub
whose ppm2 ignores price entirely (`ppm2 = area_m2 / 100`): baseline
`[20.00, 25.00, 30.00, 36.00, 44.00]` median **30.00**, and the transform leaves it at
**30.00**. Assert the block raises. Without this, a price-blind implementation that
happened to return a constant would satisfy nothing and still look tested.

### M2 · Scaling price and area together leaves ppm2 unchanged

**Transform.** `price_pln × 10` **and** `area_m2 × 10`.

| id | area m² | price PLN | ppm2 | fixed band |
|---|---|---|---|---|
| C1 | 20 000 | 1 920 000 | 96.00 | >10000 |
| C2 | 25 000 | 2 750 000 | 110.00 | >10000 |
| C3 | 30 000 | 3 780 000 | 126.00 | >10000 |
| C4 | 36 000 | 5 040 000 | 140.00 | >10000 |
| C5 | 44 000 | 6 600 000 | 150.00 | >10000 |

**Expected — estimator view (the assertion that holds exactly).** Scale the subject
too: 3 000 → 30 000 m², window `[15000, 45000]`, which admits all five. The
`Aggregate` is equal to the §1.4 baseline on **every** field: n 5, median 126.00,
p25 110.00, p75 140.00, min 96.00, max 150.00, `iqr`.

**Expected — D66-keyed view.** All five collapse into the single `>10000` band:
one stock row with n 5, median 126.00, p25 110.00, p75 140.00, min 96.00, max 150.00,
`iqr`; one flow row (C1–C4) with n 4, median 118.00, p25 106.50, p75 129.50, min
96.00, max 140.00, `min_max`. This is **not** equal to the §1.3 baseline, which has
four rows across two bands. Pass 1's instruction to assert on "the aggregate for the
band the scaled observations now occupy" only works because the *scaled* set is
single-band; the *baseline* is not. Assert the equality in the estimator view and
assert the band collapse separately. See §9 defect **P1-7**.

**Non-vacuity · `test_m2_is_not_vacuous`.** Apply a price-only ×10 to the real
implementation: ppm2 becomes `[960, 1100, 1260, 1400, 1500]`, median **1260.00**.
Assert M2's equality block raises. This is the genuine trap pass 1 names: an
implementation that scales one and not the other passes a one-sided test.

### M3 · Permuting input order changes nothing

**Transform.** Hypothesis `permutations()` over C1–C5, 100 examples, plus one
hard-coded permutation so the test is reproducible without Hypothesis:
`[C4, C1, C5, C2, C3]` → ppm2 `[140.00, 96.00, 150.00, 110.00, 126.00]`.

**Expected.** The returned `list[Aggregate]`, sorted by key, is equal to the baseline
by full dataclass equality — every field, not just the median.

**Non-vacuity · `test_m3_is_not_vacuous`.** Stub `unsorted_middle` returning
`values[len(values) // 2]` from the **un-sorted** list. On the hard-coded permutation
above it returns `values[2]` = **150.00** ≠ 126.00. Assert M3's equality raises for
that permutation. (Chosen deliberately: the reversed permutation
`[150, 140, 126, 110, 96]` returns 126.00 and would let the companion pass
vacuously.)

### M4 · An exact duplicate leaves the median and n unchanged

**Transform.** Append `C1'`, a byte-exact copy of C1 — same source URL, same
2 000 m², same 192 000 PLN, same 2026-06-20 — so dedup must cluster it.

**Expected, dedup on.** n **5**, median **126.00**, p25 110.00, p75 140.00,
min 96.00, max 150.00; `duplicate_count == 2` on C1's cluster (V56); `n_raw == 6`
reported alongside `n == 5` (F3's before/after detector).

**Non-vacuity · `test_m4_is_not_vacuous`.** Same input, `dedup=False`. Set becomes
`[96, 96, 110, 126, 140, 150]`: n **6**, median **118.00**, p25 **99.50**,
p75 **136.50**, min 96.00, max 150.00. Assert exactly these, and that M4's block
raises.

C1 is the deliberate choice. Duplicating C3 (the median) gives
`[96, 110, 126, 126, 140, 150]` → median 126.00 whether dedup works or not, and the
test would pass against broken dedup.

### M5 · An out-of-band observation leaves the estimate unchanged

**Transform.** Add **D1** (1 400 m², 30.00) **and** **D2** (4 600 m², 400.00) to the
E2 subject's candidate pool.

**Expected.** Equal to the §1.4 baseline on all six estimate fields:
n **5**, median **126.00**, low **110.00**, high **140.00**, min **96.00**,
max **150.00**, `basis == "gmina"`, `widening_step == "gmina"`.

Assert **against** all three wrong answers by name:

| leak | n | median | p25 | p75 | min | max |
|---|---|---|---|---|---|---|
| D1 only | 6 | 118.00 | 99.50 | 136.50 | 30.00 | 150.00 |
| D2 only | 6 | 133.00 | 114.00 | 147.50 | 96.00 | 400.00 |
| **both** | **7** | **126.00** | 103.00 | 145.00 | 30.00 | 400.00 |

**Non-vacuity · `test_m5_is_not_vacuous`.** Monkeypatch `AREA_BAND_TOLERANCE` to
`10.00` (± 1000 %, window `[0, 33000]`) so both decoys are admitted. Assert the
result is n **7**, min **30.00**, max **400.00**, median **126.00** — and that M5's
`n == 5` assertion raises while a median-only assertion would still pass. This
companion proves two things at once: that the decoys are reachable candidates (so
M5 is not passing because they were dropped by some earlier filter), and that the
median alone cannot kill the dropped-band-filter mutant.

### M6 · A wrong-buildability observation leaves the estimate unchanged

**Transform.** Add **D3** (`agricultural`, 12.00) and **D4** (`unknown`, 60.00), both
3 000 m², both in-gmina, both in-window, both in-recency.

**Expected.** Equal to baseline: n **5**, median **126.00**, low 110.00, high 140.00.
Assert explicitly `median != 118.00` (either single leak) and `median != 110.00`
(both leaking).

| leak | set | n | median | p25 | p75 |
|---|---|---|---|---|---|
| D3 only | `[12, 96, 110, 126, 140, 150]` | 6 | 118.00 | 99.50 | 136.50 |
| D4 only | `[60, 96, 110, 126, 140, 150]` | 6 | 118.00 | 99.50 | 136.50 |
| both | `[12, 60, 96, 110, 126, 140, 150]` | 7 | **110.00** | 78.00 | 133.00 |

**Non-vacuity · `test_m6_is_not_vacuous`.** Run the *mirror* subject: buildability
`unknown`, everything else identical, candidates C1–C5 (all `buildable`) plus D4
(`unknown`). Expected: n **1**, median **60.00**, `range_kind` `min_max`,
low = high = **60.00** — and explicitly **not** 126.00. D28's rule is symmetric and
this is the direction a one-way filter gets wrong.

### M7 · Shifting observations and the window together gives the same result

**Transform.** `first_seen`, `observed_at` and `as_of` all shifted forward by one
calendar month.

| id | first_seen → | observed_at → | in flow? |
|---|---|---|---|
| C1 | 2026-07-20 | 2026-09-08 | yes |
| C2 | 2026-08-11 | 2026-09-08 | yes |
| C3 | 2026-08-30 | 2026-09-08 | yes |
| C4 | 2026-09-04 | 2026-09-08 | yes |
| C5 | 2025-05-02 | 2026-09-08 | no |

`as_of` 2026-08-08 → **2026-09-08**; flow cutoff 2026-05-10 → **2026-06-10**.

**Expected.** Output identical to baseline: stock n 5 median 126.00, flow n 4 median
118.00, gap 8.00; D66 rows as §1.3 with `month` 2026-08 → 2026-09.

**Margins, so the reviewer can see the invariance is real and not luck.** A calendar
month is 30 or 31 days while the window is a fixed 90 days, so exact invariance holds
only if no observation crosses the cutoff. C1 is the closest: 41 days inside before
the shift, 40 days inside after. C5 is 403 days outside before and 404 after. No row
is within a month of a boundary in either direction.

**Month-boundary case (F10), as a separate two-row fixture** — adding it to the
canonical five would move the medians:

| id | first_seen (Europe/Warsaw) | stored UTC | expected month bucket | ppm2 |
|---|---|---|---|---|
| Z1 | 2026-06-30 23:30 | 2026-06-30 21:30Z | **2026-06** | 100.00 |
| Z2 | 2026-07-01 00:30 | 2026-06-30 22:30Z | **2026-07** | 200.00 |

Expected: `2026-06` has n 1 median **100.00**; `2026-07` has n 1 median **200.00**.
A UTC-bucketing implementation puts both in June: n 2, median **150.00**, and July
absent. Assert `150.00` appears nowhere. Shift both by one month and assert the same
result in `2026-07` / `2026-08`.

**Non-vacuity · `test_m7_is_not_vacuous`.** Shift the observations by one month but
`as_of` by **three** months, to 2026-11-08 (flow cutoff **2026-08-10**). Then C1
(2026-07-20) drops out and flow becomes `[110, 126, 140]`: n **3**, median
**126.00**, p25 111.00, p75 138.00, min 110.00, max 140.00, `min_max`. Assert M7's
equality block raises. Both dates remain in the past relative to `as_of`, so the
companion is a legal input, not a malformed one.

### M8 · A far outlier moves the median little and the mean a lot

**Transform.** Add **O1**: 3 000 m², 15 000 000 PLN → ppm2 **5 000.00**, gmina A,
buildable, offering, asking, `first_seen` 2026-07-15, `observed_at` 2026-08-08.
In-gmina, in-window, in-recency, in-kind — it passes every filter, by design.

**Expected.** Set `[96, 110, 126, 140, 150, 5000]`: n **6**, median **133.00**
(a shift of **7.00** from 126.00), p25 **114.00**, p75 **147.50**, min **96.00**,
max **5000.00**, `range_kind` `iqr`.

Arithmetic mean moves from **124.40** to **937.00** — a shift of 812.60, or 116× the
median's shift. Assert the **published** figure is `133.00` and that `937.00` appears
in no displayed field.

**Non-vacuity · `test_m8_is_not_vacuous`.** Two parts:
1. Assert `aggregate.mean_ppm2 == Decimal("937.00")`. This proves the outlier
   actually entered the set — without it, a filter that silently dropped O1 would
   give median 126.00 and the "median moved little" claim would be trivially true.
2. Run M8's `published == 133.00` assertion against a stub whose headline is the
   mean; it returns 937.00 and the block must raise.

---

## 3. Stock versus flow — the constructed gap

`tests/unit/metrics/test_stock_vs_flow.py`. Fixture: the canonical five of §1.1,
unchanged. `as_of = 2026-08-08`, `FLOW_WINDOW_DAYS = 90` (**D107**), **flow cutoff
2026-05-10 (inclusive)**.

Every flow figure in this section is a **90-day** figure and every assertion on one
also asserts `flow_window_days == 90` (S7). A flow median without its window says
nothing.

### 3.1 The two medians

| view | series | members | n | **median** | p25 | p75 | min | max | range_kind |
|---|---|---|---|---|---|---|---|---|---|
| estimator (window `[1500,4500]`) | **stock** | C1–C5 | 5 | **126.00** | 110.00 | 140.00 | 96.00 | 150.00 | `iqr` |
| estimator | **flow** | C1–C4 | 4 | **118.00** | 106.50 | 129.50 | 96.00 | 140.00 | `min_max` |
| D66 row, band `1500–3000` | stock | C1, C2 | 2 | 103.00 | 99.50 | 106.50 | 96.00 | 110.00 | `min_max` |
| D66 row, band `1500–3000` | flow | C1, C2 | 2 | 103.00 | 99.50 | 106.50 | 96.00 | 110.00 | `min_max` |
| D66 row, band `3000–10000` | stock | C3, C4, C5 | 3 | **140.00** | 133.00 | 145.00 | 126.00 | 150.00 | `min_max` |
| D66 row, band `3000–10000` | flow | C3, C4 | 2 | **133.00** | 129.50 | 136.50 | 126.00 | 140.00 | `min_max` |

**Constructed gaps, all three asserted explicitly:**

- estimator view: `126.00 − 118.00 = ` **8.00**, stock the higher
- band `3000–10000`: `140.00 − 133.00 = ` **7.00**, stock the higher
- band `1500–3000`: **0.00** — C5 is not in this band, so there is nothing to bias it

The third is not filler. A gap that appeared in *both* bands would mean something
other than C5 is producing it.

**Never-averaged values to assert absent** (S4): `122.00` (mean of 126 and 118),
`136.50` (mean of 140 and 133), and `110.50` in the banded 1500–3000 case.

### 3.2 Window boundary (S6)

| listing first seen | 90-day window (cutoff 2026-05-10) |
|---|---|
| 2026-05-11 | in |
| **2026-05-10** | **in** — the cutoff itself is inclusive |
| **2026-05-09** | **out** |

Monkeypatching `FLOW_WINDOW_DAYS`:

| window | cutoff | flow members | n | median | p25 | p75 | min | max | range_kind |
|---|---|---|---|---|---|---|---|---|---|
| 30 | 2026-07-09 | C2, C3, C4 | 3 | **126.00** | 111.00 | 138.00 | 110.00 | 140.00 | `min_max` |
| 60 | 2026-06-09 | C1–C4 | 4 | 118.00 | 106.50 | 129.50 | 96.00 | 140.00 | `min_max` |
| 90 | 2026-05-10 | C1–C4 | 4 | 118.00 | 106.50 | 129.50 | 96.00 | 140.00 | `min_max` |
| 180 | 2026-02-09 | C1–C4 | 4 | 118.00 | 106.50 | 129.50 | 96.00 | 140.00 | `min_max` |

No call site contains a literal `90` (V62 (a)). D107 fixes the value; the constant
stays in configuration so the sensitivity report of §3.3 can vary it.

### 3.3 The sensitivity fixture (S8) — a separate, multi-month set

The window is settled at 90 days (D107), so this report is evidence kept on the
record rather than an input to a pending choice. It still runs, because a later
change of window must be argued from measurements.

The canonical five give only **two** distinct medians across 30/60/90/180 days, so
they cannot exercise the report. S8 needs its own fixture (§9 defect **P1-8**).

`tests/fixtures/synthetic/gmina_a_window_sensitivity.py`. All rows: gmina A,
**3 000 m²**, buildable, budowlana, offering, asking, active, `observed_at`
2026-08-08, `as_of` 2026-08-08. One fixed band (`3000–10000`), so window length is
the only variable.

| id | first_seen | price PLN | ppm2 |
|---|---|---|---|
| W1 | 2026-08-01 | 300 000 | 100.00 |
| W2 | 2026-07-20 | 420 000 | 140.00 |
| W3 | 2026-07-10 | 540 000 | 180.00 |
| W4 | 2026-06-20 | 180 000 | 60.00 |
| W5 | 2026-06-15 | 240 000 | 80.00 |
| W6 | 2026-05-20 | 120 000 | 40.00 |
| W7 | 2026-05-15 | 60 000 | 20.00 |
| W8 | 2026-03-01 | 30 000 | 10.00 |
| W9 | 2026-02-15 | 36 000 | 12.00 |

`flow_sensitivity(fixture)` expected output — four distinct, monotone medians:

| window | cutoff | members | values | n | **median** | p25 | p75 | min | max | range_kind |
|---|---|---|---|---|---|---|---|---|---|---|
| **30** | 2026-07-09 | W1–W3 | `[100, 140, 180]` | 3 | **140.00** | 120.00 | 160.00 | 100.00 | 180.00 | `min_max` |
| **60** | 2026-06-09 | W1–W5 | `[60, 80, 100, 140, 180]` | 5 | **100.00** | 80.00 | 140.00 | 60.00 | 180.00 | `iqr` |
| **90** | 2026-05-10 | W1–W7 | `[20, 40, 60, 80, 100, 140, 180]` | 7 | **80.00** | 50.00 | 120.00 | 20.00 | 180.00 | `iqr` |
| **180** | 2026-02-09 | W1–W9 | `[10, 12, 20, 40, 60, 80, 100, 140, 180]` | 9 | **60.00** | 20.00 | 100.00 | 10.00 | 180.00 | `iqr` |

W3 (2026-07-10) sits one day inside the 30-day cutoff and W7 (2026-05-15) five days
inside the 90-day cutoff, so each window's edge is exercised by a real row. Stock over
all nine equals the 180-day row (every listing is active), giving a stock−flow gap of
**20.00** at a 90-day window.

### 3.4 Removing the stale listing collapses the gap (S5)

Drop C5. Estimator view: stock and flow are both C1–C4 → n 4, median **118.00**,
p25 106.50, p75 129.50, min 96.00, max 140.00, `min_max`, gap **0.00**. Banded view:
`3000–10000` stock and flow both `{C3, C4}` → median **133.00**, gap **0.00**;
`1500–3000` unchanged at 103.00. This proves the §3.1 gap is caused by C5 and not by
a structural difference in how the two sets are assembled.

---

## 4. Differential test parameter set (V48, `20` §4.4)

`tests/unit/metrics/test_percentiles_differential.py`. Reference:
`numpy.percentile(values, [25, 50, 75], method="linear")` and `numpy.median`. numpy is
test-only; an architecture test asserts `src/lpc/metrics/` never imports it.

### 4.1 The explicit parameter table (F4, extended)

Every row was computed by hand with §0.1 and confirmed against R-7. Comparison is on
**unrounded** values, `math.isclose(rel_tol=1e-12, abs_tol=1e-9)`.

| # | array | n | why it is in the set | p25 | median | p75 | min | max |
|---|---|---|---|---|---|---|---|---|
| 1 | `[118]` | 1 | degenerate; must not raise, must not return `None` | 118.0 | 118.0 | 118.0 | 118.0 | 118.0 |
| 2 | `[100, 200]` | 2 | **even**; smallest interpolating case | **125.0** | **150.0** | **175.0** | 100.0 | 200.0 |
| 3 | `[96, 126, 150]` | 3 | odd, median is an element | 111.0 | 126.0 | 138.0 | 96.0 | 150.0 |
| 4 | `[61, 96, 140, 240]` | 4 | **even**; straddles the spread switch from below | **87.25** | **118.0** | **165.0** | 61.0 | 240.0 |
| 5 | `[96, 110, 126, 140, 150]` | 5 | straddles the spread switch from above; the canonical set | **110.0** | **126.0** | **140.0** | 96.0 | 150.0 |
| 6 | `[96, 110, 126, 140, 150, 5000]` | 6 | **even** with a far outlier (M8's set) | **114.0** | **133.0** | **147.5** | 96.0 | 5000.0 |
| 7 | `[1, 2, 3, 4]` | 4 | the convention canary (A5) | **1.75** | **2.5** | **3.25** | 1.0 | 4.0 |
| 8 | `[100, 100, 100, 100]` | 4 | **all ties**; every statistic degenerate | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| 9 | `[50, 100, 100, 100, 250]` | 5 | **heavy ties** at n=5 | **100.0** | **100.0** | **100.0** | 50.0 | 250.0 |
| 10 | `[50, 100, 100, 250]` | 4 | **ties straddling both quartiles**, even length | **87.5** | **100.0** | **137.5** | 50.0 | 250.0 |
| 11 | `[61, 96, 140, 150, 240]` | 5 | the D2 spread-switch fixture | 96.0 | 140.0 | 150.0 | 61.0 | 240.0 |
| 12 | `[10,20,30,40,50,60,70,80,90,100]` | 10 | **even**, n=10 | 32.5 | 55.0 | 77.5 | 10.0 | 100.0 |
| 13 | `[1, 2, …, 100]` | 100 | large, even, interpolating at all three quantiles | **25.75** | **50.5** | **75.25** | 1.0 | 100.0 |

Row 9 is worth its own assertion beyond the differential: at n=5 the switch chooses
`iqr`, so the **displayed** range is `100.00–100.00` on data that spans 50–250. That
is correct behaviour under `05` §3 and rule 7 requires min–max to remain stored and
reachable. Assert both — a zero-width IQR next to a stored 50–250 min–max.

### 4.2 The Hypothesis strategies

| test | strategy | assertion |
|---|---|---|
| **F1** | `lists(floats(1, 100_000, allow_nan=False, allow_infinity=False), min_size=1, max_size=500)` | `isclose` on median, p25, p75 |
| **F2** | as F1, `.filter(lambda xs: len(xs) % 2 == 0)`, `min_size=2` | same — even-length medians are where the "middle element" bug lives and random lengths under-sample them |
| **F3** | `lists(sampled_from([50.0, 100.0, 100.0, 100.0, 250.0]), min_size=1, max_size=200)` | same — interpolation between identical values makes rank-based and interpolating conventions coincide, hiding a definition error that appears only on distinct values |
| **F5** | the F1 corpus | `Decimal` **equality**, not `isclose`, between our stored 2-dp value and the reference rounded the same way — catches a rounding-mode difference `isclose` swallows |

### 4.3 Rounding, pinned to exact inputs (A7, F5)

| input | unrounded | stored (HALF_UP, via `str`) | HALF_EVEN would give | `Decimal(float)` would give |
|---|---|---|---|---|
| `[1.125, 1.125]` | 1.125 | **1.13** | 1.12 | 1.13 (exactly representable) |
| `[0.125, 0.125]` | 0.125 | **0.13** | 0.12 | 0.13 (exactly representable) |
| `[1.005, 1.005]` | 1.005 | **1.01** | 1.00 | **1.00** ← the float trap |
| `[2.675, 2.675]` | 2.675 | **2.68** | 2.67 | **2.67** ← the float trap |

The first two pin the rounding **mode**; the last two pin the conversion **path**.
A test using only `1.005` cannot distinguish "wrong mode" from "wrong path".

### 4.4 The negative control (F6)

On `[1, 2, 3, 4]`, every other convention gives a different answer. Assert our
`linear` result **differs** from each:

| convention | p25 | p75 |
|---|---|---|
| **linear (ours)** | **1.75** | **3.25** |
| lower | 1.0 | 3.0 |
| higher | 2.0 | 4.0 |
| midpoint | 1.5 | 3.5 |
| nearest | 2.0 | 3.0 |
| inverted_cdf (nearest-rank) | 1.0 | 3.0 |

A5 asserts `p25 == 1.75` **and** `p25 not in (1.0, 1.5, 2.0)`. F6 asserts a locally
defined nearest-rank implementation *disagrees* with numpy on this array — if F6 ever
passes vacuously, the differential suite has stopped comparing anything.

---

## 5. LOOCV worked example (FR-69, V51, `20` §6.1)

`tests/unit/valuation/test_loocv_harness.py`. This section is the real-estimator
worked example: every fold, hand-computed, with the metrics derived from it.

### 5.1 The corpus — 12 listings

All: `budowlana`, `buildable`, `offering`, `asking`, active, `first_seen` 2026-07-01,
`observed_at` 2026-08-08, `as_of` 2026-08-08. Every listing therefore passes recency
and flow; the only filters that bind are gmina and the ±50 % window.

| id | gmina | area m² | price PLN | **actual ppm2** | fixed band |
|---|---|---|---|---|---|
| K1 | A | 3 000 | 180 000 | **60** | 3000–10000 |
| K2 | A | 3 000 | 300 000 | **100** | 3000–10000 |
| K3 | A | 3 000 | 330 000 | **110** | 3000–10000 |
| K4 | A | 2 800 | 336 000 | **120** | 1500–3000 |
| K5 | A | 3 200 | 384 000 | **120** | 3000–10000 |
| K6 | A | 3 000 | 390 000 | **130** | 3000–10000 |
| K7 | A | 3 000 | 420 000 | **140** | 3000–10000 |
| K8 | A | 3 000 | 720 000 | **240** | 3000–10000 |
| B1 | B | 3 000 | 300 000 | **100** | 3000–10000 |
| B2 | B | 3 100 | 310 000 | **100** | 3000–10000 |
| B3 | B | 2 900 | 1 450 000 | **500** | 1500–3000 |
| X1 | C | 3 000 | 1 440 000 | **480** | 3000–10000 |

Construction notes, each load-bearing:

- **Areas are spread so that every gmina-A listing is inside every other's window.**
  Windows: 2 800 → `[1400, 4200]`; 3 000 → `[1500, 4500]`; 3 200 → `[1600, 4800]`. All
  areas (2 800…3 200) sit inside all three. So each fold's comparable set is exactly
  "the other seven in the same gmina" — the harness's *removal* behaviour is the only
  thing under test, not the window.
- **K4 and K5 carry the same ppm2 (120) at different areas.** Identical price *and*
  area would trip dedup and entangle two work items. Different areas keep them
  distinct listings with a genuine tie in ppm2, which is what M3's order-independence
  needs to matter here.
- **X1 is alone in gmina C** and therefore returns an `Absence` — the fold that makes
  coverage < 1.
- **Gmina B is a three-listing pool** that produces the >2× tails and exercises the
  `n < 5` → `min_max` branch *inside* LOOCV, which the gmina-A folds (all n=7) never
  reach.

### 5.2 Every fold, in full

`n = 7` in every gmina-A fold, so `range_kind = iqr` and `(low, high) = (p25, p75)`.
`n = 2` in every gmina-B fold, so `range_kind = min_max` and `(low, high) = (min, max)`.

| fold | actual | comparable set (sorted ppm2) | n | p25 | **median** | p75 | **low** | **high** | hit? | APE | ratio | tail? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **K1** | 60 | `[100, 110, 120, 120, 130, 140, 240]` | 7 | 115.00 | **120.00** | 135.00 | 115.00 | 135.00 | no (below) | **1** = 1.000000 | **2** | **no** † |
| **K2** | 100 | `[60, 110, 120, 120, 130, 140, 240]` | 7 | 115.00 | **120.00** | 135.00 | 115.00 | 135.00 | no (below) | **1/5** = 0.200000 | 6/5 | no |
| **K3** | 110 | `[60, 100, 120, 120, 130, 140, 240]` | 7 | 110.00 | **120.00** | 135.00 | **110.00** | 135.00 | **yes — `actual == low`** | **1/11** = 0.090909 | 12/11 | no |
| **K4** | 120 | `[60, 100, 110, 120, 130, 140, 240]` | 7 | 105.00 | **120.00** | 135.00 | 105.00 | 135.00 | yes | **0** | 1 | no |
| **K5** | 120 | `[60, 100, 110, 120, 130, 140, 240]` | 7 | 105.00 | **120.00** | 135.00 | 105.00 | 135.00 | yes | **0** | 1 | no |
| **K6** | 130 | `[60, 100, 110, 120, 120, 140, 240]` | 7 | 105.00 | **120.00** | 130.00 | 105.00 | **130.00** | **yes — `actual == high`** | **1/13** = 0.076923 | 13/12 | no |
| **K7** | 140 | `[60, 100, 110, 120, 120, 130, 240]` | 7 | 105.00 | **120.00** | 125.00 | 105.00 | 125.00 | no (above) | **1/7** = 0.142857 | 7/6 | no |
| **K8** | 240 | `[60, 100, 110, 120, 120, 130, 140]` | 7 | 105.00 | **120.00** | 125.00 | 105.00 | 125.00 | no (above) | **1/2** = 0.500000 | **2** | **no** † |
| **B1** | 100 | `[100, 500]` | 2 | 200.00 | **300.00** | 400.00 | **100.00** | 500.00 | **yes — `actual == low`** | **2** = 2.000000 | 3 | **yes** |
| **B2** | 100 | `[100, 500]` | 2 | 200.00 | **300.00** | 400.00 | **100.00** | 500.00 | **yes — `actual == low`** | **2** = 2.000000 | 3 | **yes** |
| **B3** | 500 | `[100, 100]` | 2 | 100.00 | **100.00** | 100.00 | 100.00 | 100.00 | no (above) | **4/5** = 0.800000 | 5 | **yes** |
| **X1** | 480 | *(none — alone in gmina C)* | — | — | **`Absence`** | — | — | — | *not estimable* | — | — | — |

† K1 and K8 sit **exactly** on the twofold threshold: `120/60 = 2` and `240/120 = 2`.
Under `ratio > 2` neither counts. Under `ratio >= 2` both would, and `tail_over_2x`
would read `5/11` instead of `3/11`.

Two further shapes worth naming rather than leaving to be rediscovered:

- **B1 and B2 are hits with an APE of 2.0.** The range `100–500` is so wide it
  contains the actual while the median is 3× off. Hit rate and error measure
  different things and this corpus proves it in one row.
- **B3's range is degenerate: `100.00–100.00` at n=2.** Both comparables are 100.00,
  so min = max. That is a legitimate rule-6 output (n and spread both shown, spread
  happens to be zero) and the harness must not treat a zero-width range as an error.

### 5.3 The metrics, computed by hand

**Denominators.** `coverage` divides by `n_total`; every other metric divides by
`n_estimable`. The report carries both counts so a reader cannot confuse them.

```
n_total      = 12
n_estimable  = 11                      (X1 returned an Absence)
coverage     = Fraction(11, 12)        ≈ 0.916667
```

**Hit rate.** Hits are K3, K4, K5, K6, B1, B2 — six of eleven. Note that **four of
the six are boundary hits** (`actual == low` three times, `actual == high` once), so
flipping to a strict comparison drops the figure to 2/11.

```
hit_rate     = Fraction(6, 11)         ≈ 0.545455
```

**Median APE.** The eleven APEs, sorted, as exact fractions:

```
0,  0,  1/13,  1/11,  1/7,  1/5,  1/2,  4/5,  1,  2,  2
0.000000  0.000000  0.076923  0.090909  0.142857  0.200000  0.500000  0.800000  1.000000  2.000000  2.000000
                                                  ^^^^^^^^ 6th of 11
median_ape   = Fraction(1, 5)          = 0.200000 exactly
```

n = 11 is odd, so the median is an element and no interpolation is involved — but the
harness must still call the **same** `percentiles()` function (h = 10 · 0.5 = 5 →
`x[5]`), not `statistics.median` on a private path. §5.4 has the even-length case
where the two diverge.

**Tail.** Ratios > 2 strictly: B1 (3), B2 (3), B3 (5). K1 and K8 are exactly 2 and
excluded.

```
tail_over_2x = Fraction(3, 11)         ≈ 0.272727
```

**`by_area_band`.** Band is the **subject's** fixed band, per §0.2.

| band | folds | n_total | n_estimable | coverage | hit_rate | median_ape | tail_over_2x |
|---|---|---|---|---|---|---|---|
| `1500–3000` | K4, B3 | 2 | 2 | **1** | **1/2** | **2/5** = 0.400000 | **1/2** |
| `3000–10000` | K1, K2, K3, K5, K6, K7, K8, B1, B2, *X1* | 10 | 9 | **9/10** | **5/9** | **1/5** = 0.200000 | **2/9** |

The `1500–3000` median APE is the only **even-length** median in this example — two
values `[0, 4/5]`, so `h = 1 · 0.5 = 0.5` and the result is `0 + 0.5 · 4/5 = 2/5`.
An implementation using a "middle element" median returns `0` or `4/5` here. This is
the assertion that stops the harness quietly using a second percentile convention.

Cross-checks the test asserts explicitly, so a band-assignment bug cannot hide:
`2 + 9 = 11 = n_estimable`; `2 + 10 = 12 = n_total`; `1 + 5 = 6` hits; `1 + 2 = 3` tails.

**`widening_profile`** = `{"gmina": 11}`. v0 has exactly one widening step, and a
subject with no same-gmina comparables returns an `Absence` rather than a widened set
(`18` §4). X1 contributes to no step.

### 5.4 The tie-breaking and boundary rules this example pins

| # | Rule | Pinned by | Value if the rule flips |
|---|---|---|---|
| 1 | A hit is `low <= actual <= high`, **both bounds inclusive** | K3 (`== low`), K6 (`== high`), B1, B2 (`== low`) | `hit_rate` 6/11 → **2/11** |
| 2 | The tail is `ratio > 2`, **strictly**; `ratio == 2` is not a tail | K1 (120/60), K8 (240/120) — one on each side of the median | `tail_over_2x` 3/11 → **5/11** |
| 3 | The ratio is `max(actual/median, median/actual)`, so over- and under-estimates are symmetric | K1 and K8 both yield exactly 2 from opposite directions | an asymmetric definition gives 1/11 or 2/11 |
| 4 | `coverage` divides by `n_total`; everything else by `n_estimable` | X1 | `coverage` 11/12 → **1** |
| 5 | Metrics are exact `Fraction`s, never floats | all | `Fraction(1,3)` vs `0.3333333333333333` at a threshold comparison |
| 6 | The median APE uses the same R-7 `percentiles()` as everything else | `1500–3000` band (even length, 2/5) | **0** or **4/5** |
| 7 | Equal ppm2 values are interchangeable; sort is on value only | K4 and K5, both 120 — their folds must return **identical** ranges | a stable-sort dependency makes the two folds differ |

**Why float never touches the threshold.** Every ratio in this corpus is a ratio of
small integers, and `120/60` and `240/120` are exactly representable as doubles — so
`== 2.0` is unambiguous here. That is a property of this fixture, not of the code.
The harness computes ratios as `Fraction(actual_numerator, median_numerator)` from the
stored `Decimal`s so the rule holds for corpora where it is not.

### 5.5 The leakage test (L2) — the load-bearing one

Corpus: C1–C5 (§1.1) plus **X** at 3 000 m², 15 000 000 PLN → **5 000.00** ppm2, same
gmina, buildability, price type and kind, `first_seen` 2026-07-15.

| fold | correct comparable set | n | p25 | **median** | p75 | what leakage would give |
|---|---|---|---|---|---|---|
| **X** | `[96, 110, 126, 140, 150]` | **5** | 110.00 | **126.00** | 140.00 | `[96,110,126,140,150,5000]` → n **6**, median **133.00** |
| **C3** | `[96, 110, 140, 150, 5000]` | **5** | 110.00 | **140.00** | 150.00 | removing the wrong row, or two rows, changes all three |

Assert `median != 133.00` in X's fold by name. C3's fold proves the harness removes
**exactly one** listing — not the wrong one, and not two.

**Leakage inside §5.2's corpus** is quieter and worth stating so nobody relies on the
median there: fold K1 with the held-out listing left in gives
`[60, 100, 110, 120, 120, 130, 140, 240]`, n **8**, p25 **107.50**, median **120.00**,
p75 **132.50**. The median is *unchanged*. Only `n == 7` and `low == 115.00` kill that
mutant in this corpus, which is why L2 keeps its own 5 000-ppm2 fixture.

### 5.6 The stub-estimator harness tests (L1, L3, L4, L5)

Kept from pass 1 and re-verified. Corpus of 12: eleven estimable with actuals
`[60, 90, 100, 110, 120, 130, 140, 150, 160, 240, 480]` and one alone in `TERYT_GMINA_C`;
the stub returns `low=100, median=120, high=140` for every fold.

- `n_total == 12`, `n_estimable == 11`, `coverage == Fraction(11, 12)`
- `hit_rate == Fraction(5, 11)` — 100, 110, 120, 130, 140; **both endpoints inside**
- APEs sorted as exact fractions: `0, 1/13, 1/11, 1/7, 1/5, 1/5, 1/4, 1/3, 1/2, 3/4, 1` →
  `[0, 0.076923, 0.090909, 0.142857, 0.200000, 0.200000, 0.250000, 0.333333, 0.500000, 0.750000, 1.000000]`,
  6th of 11 = **0.200000**, so `median_ape == Fraction(1, 5)`
- `tail_over_2x == Fraction(1, 11)` — only 480 (ratio 4). **60 gives exactly 2 and 240
  gives exactly 2**; neither counts

| test | stub | expected |
|---|---|---|
| **L3** | `low = median = high = actual` | `hit_rate == 1`, `median_ape == 0`, `tail_over_2x == 0` |
| **L4** | `low = median = high = 0.01` for every fold | `hit_rate == 0`, `tail_over_2x == 1` |
| **L5** | L1's corpus plus three more comparable-less listings at actuals `[1.0, 9999.0, 5.0]` | `coverage == Fraction(11, 15)`; `hit_rate`, `median_ape`, `tail_over_2x` **byte-identical to L1** |

L3 and L4 together catch an inverted comparison that L1 alone cannot — a flipped `<=`
still yields a plausible middling hit rate on L1's corpus.

### 5.7 The band-breakdown fixture (L7)

`by_area_band` exists to expose size-correlated error that the aggregate hides
(`05` §4, O6). An earlier version of pass 1 asked for
`by_area_band[">10000"].median_ape == 1.0`, which a leave-one-out **median**
estimator cannot produce for a majority of folds in any band — see §9 defect
**P1-9**. The realisable construction below produces a starker contrast and is
exact. Pass 1 now states these values.

Three gminas, each a self-contained pool, all `budowlana`/`buildable`/`offering`/`asking`:

| id | gmina | area m² | ppm2 | band |
|---|---|---|---|---|
| E1, E2, E3 | E | 2 000 / 2 200 / 2 400 | 100.00 each | `1500–3000` |
| F1, F2, F3 | F | 4 000 / 4 400 / 4 800 | 100.00 each | `3000–10000` |
| G1 | G | 20 000 | **60.00** | `>10000` |
| G2 | G | 22 000 | **120.00** | `>10000` |
| G3 | G | 24 000 | **120.00** | `>10000` |

Folds:

| fold | comparables | n | median | low | high | hit? | APE |
|---|---|---|---|---|---|---|---|
| E1/E2/E3 | `[100, 100]` | 2 | 100.00 | 100.00 | 100.00 | yes | **0** |
| F1/F2/F3 | `[100, 100]` | 2 | 100.00 | 100.00 | 100.00 | yes | **0** |
| **G1** (actual 60) | `[120, 120]` | 2 | **120.00** | 120.00 | 120.00 | no | **1** = 1.000000 |
| **G2** (actual 120) | `[60, 120]` | 2 | **90.00** | 60.00 | 120.00 | yes | **1/4** = 0.250000 |
| **G3** (actual 120) | `[60, 120]` | 2 | **90.00** | 60.00 | 120.00 | yes | **1/4** = 0.250000 |

Expected report:

```
overall  : n_estimable 9, hit_rate 8/9, median_ape 0        (sorted: 0,0,0,0,0,0,1/4,1/4,1 → 5th = 0)
1500-3000: median_ape 0,     hit_rate 1
3000-10000: median_ape 0,    hit_rate 1
>10000   : median_ape 1/4,   hit_rate 2/3
```

**The overall `median_ape` is exactly 0 while one whole band is at 1/4 and misses a
third of its folds.** The aggregate hides the signal completely, which is L7's entire
point — and it is a cleaner demonstration than pass 1's unattainable 1.0.

---

## 6. Price separation and price kinds — exact fixtures

### 6.1 P1 · offering and sales, nothing between (V2, rule 6)

`tests/unit/metrics/test_price_separation.py`. One gmina (A), one band
(`1500–3000`), so the only axis in play is `price_type`.

| id | area m² | price PLN | ppm2 | price_type | price_kind |
|---|---|---|---|---|---|
| O1..O5 | 1 600 / 1 700 / 1 800 / 1 900 / 2 000 | 320 000 / 340 000 / 360 000 / 380 000 / 400 000 | **200.00** each | offering | asking |
| S1..S5 | 2 100 / 2 200 / 2 300 / 2 400 / 2 500 | 210 000 / 220 000 / 230 000 / 240 000 / 250 000 | **100.00** each | sales | **transaction** (D68) |

**Expected — two rows, nothing between:**

| price_type | n | median | p25 | p75 | min | max | range_kind |
|---|---|---|---|---|---|---|---|
| offering | 5 | **200.00** | 200.00 | 200.00 | 200.00 | 200.00 | `iqr` |
| sales | 5 | **100.00** | 100.00 | 100.00 | 100.00 | 100.00 | `iqr` |

**The blended value to assert absent.** If the price-type filter is dropped the ten
merge into `[100, 100, 100, 100, 100, 200, 200, 200, 200, 200]`: n **10**,
p25 **100.00**, median **150.00**, p75 **200.00**. The assertion that does the work is
a scan over **every numeric field of every returned aggregate** finding no value equal
to `150.00`. Both aggregates are deliberately zero-width (`200.00–200.00` and
`100.00–100.00`) so `150.00` cannot arise by coincidence from either.

### 6.2 P3 · missing sales returns an absence

Fixture: the §1.1 canonical offering set, **zero** sales rows. `estimate(...,
price_type="sales")` must return an `Absence` with `reason == "no_sales_observations"`.
Assert, recursively over every field of the returned object, that none of
**126.00**, **110.00**, **140.00**, **96.00**, **150.00** or **5** appears. Rendered
string is *"brak danych transakcyjnych"* (V20, FR-37, `05` §5).

### 6.3 P5 · auction prices do not move the asking median (V46, F9)

Add **D7** (§1.5): 3 000 m², 120 000 PLN, **40.00** ppm2, `price_kind = auction_start`.

| price_kind | members | n | median | p25 | p75 | min | max | range_kind | low | high |
|---|---|---|---|---|---|---|---|---|---|---|
| `asking` | C1–C5 | **5** | **126.00** | 110.00 | 140.00 | 96.00 | 150.00 | `iqr` | 110.00 | 140.00 |
| `auction_start` | D7 | **1** | **40.00** | 40.00 | 40.00 | 40.00 | 40.00 | `min_max` | 40.00 | 40.00 |

Blended (mutant) value: `[40, 96, 110, 126, 140, 150]` → n **6**, median **118.00**,
p25 99.50, p75 136.50, min 40.00. Assert `median != 118.00` and `min != 40.00` on the
`asking` row. An auction starting price is a statutory floor, not an ask; blending
drags every median down and reads as a market move.

### 6.4 E8 · the recency window (new — see §9 defect **P1-10**)

`tests/unit/valuation/test_comparable_selection.py`. Recency is 12 months (D110).

An earlier mutation table sent the dropped-recency-filter mutant to "§6.1 P2", which
is the architecture test for the grouping key and cannot detect a recency leak. Pass
1 now names E8. The test:

**`test_an_observation_outside_the_recency_window_is_excluded`.** Candidates C1–C5
plus **decoy D6** (`observed_at` 2025-01-15, ppm2 400.00, in-gmina, in-window, in-kind,
in-buildability — recency is the *only* filter that excludes it). Expected: n **5**,
median **126.00**, max **150.00**. Leak value: `[96, 110, 126, 140, 150, 400]` → n
**6**, median **133.00**, max **400.00**. Companion: monkeypatch `RECENCY_MONTHS` to
`24` (cutoff 2024-08-08) and assert decoy D6 **is** admitted, giving exactly n 6 and median
133.00 — proving the exclusion is the recency rule and not an accident of some other
filter.

### 6.5 Test D6 · a source that publishes no spread (D69)

`tests/unit/metrics/test_spread_switch.py`, fixture
`synthetic/gus_sales_no_spread.py`. GUS publishes a central value for a gmina and no
percentiles. Rule 7 says show the absence. D69 gives it a name.

| field | value |
|---|---|
| `price_type` | `sales` |
| `price_kind` | `transaction` (D68) |
| `median_ppm2` | **130.00** |
| `n` | **37** |
| `range_kind` | **`unavailable`** |
| displayed `low` / `high` | **`None`** / **`None`** |
| rendered text | *"Nie znamy rozrzutu — GUS publikuje tylko średnią"* |

Three assertions, each killing a different wrong behaviour:

1. Building the aggregate **does not raise**. An error on correct data is the failure
   D69 exists to stop.
2. The `range` field is **present** with `kind == "unavailable"`, not dropped. A
   missing field reads as a bug in the reader, not as an absent spread at the source.
3. The rendered output contains the explicit sentence. A blank, a dash or `"—"` fails
   — the same scan D5 runs.

The 130.00 is deliberately **not** any value in §1.1, so a figure leaking from the
offering fixture is visible.

**This was a real gap, and it is closed.** The four spread columns were declared
`NOT NULL`, so the row D69 exists to allow could never be written. `15` §9 and
migration `0002` now make them nullable, guarded by
`spread_present_unless_unavailable`: a spread may be absent only when the source
publishes none, and then it must be absent completely. Nullability cannot be used
to skip rule 7. `test_a_central_value_with_no_spread_is_storable` asserts the row
stores.

---

## 7. Mutation-testing table (V52, `20` §4.8)

Every mutant, the fixture it is run against, the **exact wrong value** it produces,
and the single test that must fail. A mutant with no exact wrong value listed is a
mutant nobody has actually reasoned about.

| # | Mutant | Fixture | Value the mutant produces | **Killed by** | Also fails |
|---|---|---|---|---|---|
| 1 | Swap `p25` and `p75` | `[1, 2, 3, 4]` | p25 **3.25**, p75 **1.75** | **A5** | D2, E2, A6, F1 |
| 2 | `n >= SPREAD_THRESHOLD_N` → `n > …` | `SPREAD_N5` | `range_kind` `min_max`, low **61.00**, high **240.00** | **D2** | E2 (low 96.00, high 150.00) |
| 3 | Drop the area-band filter | §1.4 + D1 + D2 | n **7**, min **30.00**, max **400.00**, median **126.00** (unchanged) | **M5** *(via `n == 5`)* | E3; **not** a median assertion |
| 4 | Drop the buildability filter | §1.4 + D3 + D4 | n **7**, median **110.00** | **M6** | E5 |
| 5 | Drop the price-type filter | §6.1 | n **10**, median **150.00** | **P1** | — |
| 6 | Drop the price-kind filter | §6.3 | n **6**, median **118.00**, min **40.00** | **P5** | — |
| 7 | Drop the recency filter | §6.4 | n **6**, median **133.00**, max **400.00** | **E8** *(new)* | — |
| 8 | `median` → `mean` | `[96,110,126,140,150]` | **124.40** | **A1** | M8 (**937.00**) |
| 9 | Flow window ignored → flow = stock | §3.1 | flow median **126.00**, n **5**, gap **0.00** | **S1** | S6 (30-day case reads 126.00 at n **5**, not n **3**). **Not S5** — S5 already expects a 0.00 gap, so it survives this mutant |
| 10 | Skip dedup | §M4 | n **6**, median **118.00** | **M4** | — |
| 11 | Held-out listing left in its own set | §5.5 X fold | n **6**, median **133.00** | **L2** | §5.2 K1 fold (n **8**, low **107.50**) |
| 12 | `low`/`high` from p25/p75 regardless of n | `SPREAD_N4` | low **87.25**, high **165.00** | **D1** | §3.1's displayed low/high (flow reads 106.50 / 129.50 instead of 96.00 / 140.00); §5.2's B folds (B1 reads 200.00 / 400.00 instead of 100.00 / 500.00, turning three hits into misses) |
| 13 | Band boundary `>=` → `>` in `band_for` | `area = 1500` | `"800-1500"` instead of `"1500-3000"` | **B2** | C3, B3 (a gap opens at every edge) |
| 14 | `ROUND_HALF_UP` → `ROUND_HALF_EVEN` | `[1.125, 1.125]` | **1.12** | **A7** | F5 |
| 15 | `Decimal(str(x))` → `Decimal(x)` on storage | `[1.005, 1.005]` | **1.00** | **A7** | F5 |
| 16 | `percentile method` `"linear"` → `"midpoint"` | `[1, 2, 3, 4]` | p25 **1.5**, p75 **3.5** | **A5** | F1, F4 |
| 17 | Flow cutoff `>=` → `>` | listing at `first_seen = 2026-05-10` | excluded; flow n **3**, median **126.00** | **S6** | S1 (gap becomes 8.00 → different n) |
| 18 | LOOCV hit `low <= a <= high` → `low < a < high` | §5.2 | `hit_rate` **2/11** | **§5.3** | L1 (**3/11**) |
| 19 | LOOCV tail `> 2` → `>= 2` | §5.2 | `tail_over_2x` **5/11** | **§5.3** | L1 (**3/11**) |
| 20 | LOOCV `coverage` denominator `n_total` → `n_estimable` | §5.2 | `coverage` **1** | **§5.3** | L5 (**1** instead of 11/15) |
| 21 | `median_ape` uses "middle element" not R-7 | §5.3 `1500–3000` band | **0** or **4/5** instead of **2/5** | **§5.3 `by_area_band`** | L1 unaffected (odd n) |
| 22 | Month bucketing in UTC, not Europe/Warsaw | §M7 Z1/Z2 | June n **2**, median **150.00**; July **absent** | **M7** | — |
| 23 | Aggregate suppressed when `n < SPREAD_THRESHOLD_N` | `SPREAD_N1`…`SPREAD_N4` | `None` / `"brak danych"` | **D5** | C4 |
| 24 | `Absence` replaced by the nearest gmina's estimate | §E4 / §5.2 X1 | **126.00** appears in gmina B's result | **E4** | §5.3 (`coverage` **1**) |
| 25 | `range_kind = 'unavailable'` raises instead of storing | §6.5 | exception, no aggregate | **D6** | — |
| 26 | `range` field dropped when there is no spread | §6.5 | `range` absent from the payload | **D6** | D5's no-suppression scan |
| 27 | The n=5 threshold restored as a database CHECK | `SPREAD_N4` insert with `range_kind='iqr'` | the insert is rejected | **D4** | — |
| 28 | Suppress the estimate below `MIN_COMPARABLES_BEFORE_WIDENING` | two comparables `[110, 140]` | `Absence` instead of median **125.00** | **E4b** | D5 |

Mutants 25 to 28 come from the batch 15, 20 and 21 decisions and have no killer in
the pass-1 suite as first written. D6, D4 and E4b are the tests that add one.

Mutants 3, 11 and 21 are the ones that survive an obvious-looking suite:
**3 and 11 leave the median unchanged**, and **21 is invisible at odd n**. Each is
killed only by an `n`, a bound, or an even-length assertion. If the mutation run shows
survivors, they will be these three.

---

## 8. Fixture manifest

Files, and the constructed answer each carries in its header comment (`20` §8
criterion 5).

| File | Rows | Header states |
|---|---|---|
| `synthetic/gmina_a_buildable_offering.py` | C1–C5 | §1.3 four D66 rows and §1.4 both estimator views |
| `synthetic/gmina_a_decoys.py` | D1–D8 | §1.5's leak table — every decoy's individual effect |
| `synthetic/spread_switch.py` | `SPREAD_N1/3/4/5/10/100` | §1.6 |
| `synthetic/gus_sales_no_spread.py` | `SPREAD_GUS` | §6.5 — median 130.00, n 37, `range_kind` `unavailable` |
| `synthetic/thin_comparable_set.py` | two rows at 110.00 and 140.00 | §0.2b — E4b's median **125.00**, `min_max`, `below_min_comparables` |
| `synthetic/gmina_a_window_sensitivity.py` | W1–W9 | §3.3's four windows |
| `synthetic/month_boundary.py` | Z1, Z2 | §M7 — June 100.00, July 200.00, never 150.00 |
| `synthetic/price_separation.py` | O1–O5, S1–S5 | §6.1 — 200.00, 100.00, never 150.00 |
| `synthetic/loocv_worked_example.py` | K1–K8, B1–B3, X1 | §5.2's full fold table and §5.3's metrics |
| `synthetic/loocv_stub_corpus.py` | 12 rows | §5.6's L1 metrics |
| `synthetic/loocv_band_breakdown.py` | E1–E3, F1–F3, G1–G3 | §5.7 |
| `synthetic/percentile_reference.py` | rows 1–13 of §4.1 | each array's three statistics |

All are hand-constructed synthetic, contain no personal data by construction, and
carry `as_of = 2026-08-08`.

---

## 9. Defects this pass found in pass 1

Pass 2 is where the arithmetic gets checked. Eleven findings; **P1-1, P1-2 and P1-4
changed values that pass 1 stated verbatim**, and P1-6 was a schema gap.

**All eleven are now corrected in pass 1 itself.** The two documents state one value
per test. This table stays as the record of what was wrong, so a later reader can see
why a number changed rather than guess.

| # | Where | Defect | Correction |
|---|---|---|---|
| **P1-1** | §3 block C, test **C3** | Asserts `TERYT_GMINA_A / "1500-3000"` has `n == 2` from **C2 (2 500 m²) and C3 (3 000 m²)**, median 118.00. Bands are lower-inclusive, so C3 at exactly 3 000 m² belongs to `3000–10000`, and C1 at 2 000 m² also belongs to `1500–3000`. The stated membership is wrong in **both** directions | The band holds **C1 and C2**: n **2**, median **103.00**, p25 99.50, p75 106.50, min 96.00, max 110.00. See §1.3. The 118.00 in that test is the *flow estimator* figure, imported from §2.1 by mistake |
| **P1-2** | §7 preamble | C5 is "first seen 2025-04-02 (**494 days** before `as_of = 2026-08-08`)" | **493 days.** 2025 day-of-year 92 → 273 days remaining in 2025; 2026-08-08 is day 220; 273 + 220 = 493 |
| **P1-3** | §3 block A, test **A7** | Asserts input `[1.005, 1.005]` stores `Decimal("1.01")`. True only if the conversion goes through `str`; `Decimal(1.005)` is `1.00499999…` and `ROUND_HALF_UP` gives `1.00` | Keep the assertion, add the required conversion path to the surface contract, and add `[1.125, 1.125] → 1.13` to separate "wrong mode" from "wrong path". §0.4, §4.3 |
| **P1-4** | §2.1 and throughout | Uses `price_kind = "ask"`. D65 defines the enum as `{asking, auction_start, tender}` | **`asking`** everywhere |
| **P1-5** | §2.1, §7 | The 8.00 stock−flow gap is presented as a property of "the aggregate". It is the **comparable-set** gap. The D66-keyed rows give **7.00** in `3000–10000` and **0.00** in `1500–3000` | S1 asserts all three, each naming its view. §1.3, §1.4, §3.1 |
| **P1-6** | §2.1, D5 decoy; D65 | **`price_kind` was `NOT NULL` with enum `{asking, auction_start, tender}` — all three are `price_type = 'offering'`. A sales row had no valid `price_kind`.** D5 and §6.1's S1–S5 could not be written as stated | **Closed by D68.** `price_kind` gains `transaction`, pinned by a CHECK on the `transaction` table. D5 and S1–S5 carry it. Nothing is blocked |
| **P1-7** | §5, **M2** | "the assertion is made on the aggregate for the band the scaled observations now occupy" — the *scaled* set is single-band (`>10000`) but the *baseline* spans two bands, so there is no baseline row to compare against | Assert full equality in the **estimator** view with the subject scaled too; assert the band collapse separately. §M2 |
| **P1-8** | §7, **S8** | "Pinned against a multi-month fixture with known medians per window" — no such fixture is given, and the canonical five yield only two distinct medians (30 d → 126.00; 60/90/180 d → 118.00), which cannot exercise the report | New fixture in §3.3: four distinct monotone medians **140 / 100 / 80 / 60**. The window itself is now settled at 90 days by **D107** |
| **P1-9** | §8, **L7** | Asserts `by_area_band[">10000"].median_ape == 1.0`. A leave-one-out **median** estimator produces APE 1.0 only when the estimate is exactly twice the actual, which cannot hold for a majority of folds drawn from one pool | Replaced with an exact, realisable contrast in §5.7: overall `median_ape` **0**, `>10000` **1/4**, hit rate `2/3` in that band. The contrast is what L7 needs |
| **P1-10** | §5.1 mutation table | "Drop the recency filter → killed by §6.1 P2". P2 is the architecture test for the grouping key and cannot see a recency leak; §9's table likewise sends it to E2 and P4, neither of which admits decoy D6 | New test **E8** in §6.4, with its non-vacuity companion |
| **P1-11** | §3 block B, test **B3** | Property test ranges over "areas 100..500 000 m² (V10's accepted band)". Gap analysis **B1** amended FR-12 and V10 to **300 – 200 000 m²** | Range over **300 – 200 000 m²** |

### Questions after this pass

Pass 1 carried five. Five are closed. Two remain, and neither blocks work item 10.

| # | Status |
|---|---|
| 1 · Median APE denominator | **Closed by gap analysis B4** — the estimate **median**, in both documents. Used throughout §5 |
| 2 · `metric_unit_month` primary key | **Closed by D66** — extended with `area_band`, `series_kind`, `price_kind`. §1.3 is written against the extended key; the migration remains a precondition of Block C |
| 3 · Field name for stock and flow | **Closed by D66** — `series_kind`, in the schema, the API and the UI |
| 4 · Flow window length | **Closed by D107** — 90 days. §3.3 keeps the sensitivity evidence on the record |
| **6 · `price_kind` for sales rows** | **Closed by D68** — `transaction`. See P1-6 |
| 5 · Rounding point | **Open.** This plan rounds once, on storage (§0.4). If the API rounds again, `stock − flow == 8.00` becomes fixture-dependent. `06-surface.md` owns the answer |
| **7 · Storage of a D69 row** | **Closed.** The four spread columns are nullable, guarded by `spread_present_unless_unavailable`, so an `unavailable` row stores and every other combination stays unwritable. Both `15` §9 and migration `0002` carry it |

Question 7 is a contradiction between two ratified decisions, not a preference. I
found it while writing §6.5 and I am recording it rather than choosing an answer.
Making the four columns nullable and adding a CHECK tying nullability to
`range_kind = 'unavailable'` would resolve it, and that is a schema decision the
owner takes, not this document.
