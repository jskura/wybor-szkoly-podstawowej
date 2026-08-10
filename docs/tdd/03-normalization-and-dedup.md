# TDD specification — parse/normalize and v0 dedup

Covers **v0 work-plan items 6 and 9** ([`18-v0-scope.md`](../18-v0-scope.md) §6):

| # | Work | Days | Requirements | Validation |
|---|---|---|---|---|
| 6 | Parse + normalize: area units, zł/m², validity bands, quarantine | 1.5 | FR-11, FR-12, FR-48, FR-50, FR-51, FR-64 | V10, V25, V28, V50 |
| 9 | Trivial dedup — exact/near-exact only | 0.5 | FR-13 (weakened), FR-70 | V56, V47 |

This document is the **test plan written before implementation**, per rule 4. It
names every test, pins every expected value, and states the order the tests are
written in. It contains **no implementation code** — only contracts, inputs and
expected outputs.

Silent failures addressed: **F1** (area unit mis-parsed), **F2** (price is for
something else), **F3** (duplicates inflate `n`), **F9** (auction/tender blended
with asking), **F12** (quarantine swallows a class of listing) —
[`20-verification-strategy.md`](../20-verification-strategy.md) §3.

Verification tier: **A** for unit conversion, band arithmetic and exact-match
dedup (an independent correct answer exists); **B** for the register-vs-advert
area cross-check and the per-reason quarantine baseline.

---

## 0. Entry criteria — checked before the first test is written

[`20-verification-strategy.md`](../20-verification-strategy.md) §8, item by item.

| # | Criterion | Status for items 6 and 9 |
|---|---|---|
| 1 | PRD requirement or work-plan entry exists | ✅ FR-11–FR-14, FR-48, FR-51, FR-64, FR-70; work plan 6 and 9 |
| 2 | Validation method exists in `04` | ✅ V10, V25, V28, V47, V50, V56 |
| 3 | Verification tier assigned | ✅ A, with B for the register cross-check — above |
| 4 | Touched silent failures have named detectors | ✅ F1, F2, F3, F9, F12 — mapped in §11 |
| 5 | Fixtures exist, dated, scrubbed | ⛔ **Not yet.** §10 specifies them; they are created as step 0 of the red-green sequence |
| 6 | Metamorphic properties listed (numeric core) | ✅ §7 |
| — | Ambiguities resolved by asking, not assuming (rule 2) | ✅ **All twelve questions are answered** — D78–D88 and D90. §12 lists them. No test in this work item is blocked |

Criterion 5 is work, not a blocker. The rule-2 gate is open: the owner answered
every question this work item raised. §12 states each settled rule with its
D-number. No test carries a `blocked` marker any more.

## 1. The band amendment — read this before copying any constant

FR-12 as amended (O12, closed in [`00-decisions.md`](../00-decisions.md) line 182)
carries the band:

> **area ∈ [300 m², 200 000 m²]**, **price ∈ [1, 100 000] PLN/m²**, and records
> outside it are **flagged and kept visible, never silently dropped**.

**Other documents still show the superseded band.**
[`04-validation.md`](../04-validation.md) V10 states "land area 100–500 000 m²"
and prescribes "boundary values at exactly 100 m² and 500 000 m²". That text is
stale. **The amended band is authoritative**; V10's *structure* (boundary tests,
non-null reason, Δ rate assertion, 200-record manual audit) stands, only its
numbers are superseded.

Two consequences that are themselves tested:

- `test_band_constants_match_amended_fr12` — asserts the band constants equal
  exactly `(Decimal("300"), Decimal("200000"))` and `(Decimal("1"),
  Decimal("100000"))`. This test exists specifically so that a constant copied
  from V10's prose fails immediately rather than quietly discarding 20–50 ha
  farmland, which is the exact outcome O12 was closed to prevent.
- `test_out_of_band_record_is_flagged_not_dropped_and_not_quarantined` — §5.

**Errata to raise separately:** `04-validation.md` V10 should be corrected to the
amended band. It is not corrected as a side effect of this work item; it is a
documentation change with its own commit.

## 2. Contracts under test

Named here so the tests can be written against them before any implementation
exists. Module paths follow [`16-repository-layout.md`](../16-repository-layout.md) §1.

| Module | Callable | Returns |
|---|---|---|
| `lpc.normalize.units` | `parse_area(text, field)` | `AreaParse(m2: Decimal \| None, unit: 'm2'\|'ar'\|'ha'\|None, is_approximate: bool, confidence: 'high'\|'low'\|'unknown', failure: AreaFailure \| None)` |
| `lpc.normalize.units` | `parse_price(text)` | `PriceParse(pln: Decimal \| None, confidence: 'high'\|'low'\|'unknown', failure: PriceFailure \| None)` |
| `lpc.normalize.area_authority` | `resolve_area(register, structured, body, title)` | `ResolvedArea(m2: Decimal, source: 'register'\|'structured'\|'body'\|'title', conflict: bool, candidates: dict[str, Decimal \| None])` |
| `lpc.normalize.bands` | `band_flags(area_m2, price_per_m2)` | `frozenset[Flag]` |
| `lpc.normalize.pipeline` | `normalize(parsed_item, register_area=None)` | `NormalizedListing` **or** `QuarantinedRecord(reason: QuarantineReason, listing_ref: dict)` |
| `lpc.dedup.exact` | `dedup_exact(listings)` | `DedupResult(clusters, n_before, n_after)` |

Four of these fields come from the answered questions.

- `field ∈ {"structured","title","body"}` is a required argument. D86 reads the
  bare `a` abbreviation as ares only in a structured field or title, or in body
  text within 40 characters of an area keyword. The parser cannot apply that rule
  without knowing the field.
- `confidence ∈ {"high","low","unknown"}` records how the value was recovered.
  D80, D83, D86 and D90 all produce a `low` value that still enters the corpus.
- `candidates` keeps every stated area, so the plot page can show the loser
  (§4.3).
- `PriceFailure` gains `NOT_A_TOTAL` and `UNSUPPORTED_CURRENCY`.

Three contract-level rules, each with a test:

1. **Decimal everywhere.** `test_parse_area_returns_decimal_not_float` and
   `test_parse_price_returns_decimal_not_float` — `assert isinstance(result.m2,
   Decimal)`. Binary floats reintroduce the rounding drift that the
   `NUMERIC(12,2)` schema columns exist to avoid.
2. **The normalizer never computes `price_per_m2`.**
   `test_normalized_listing_has_no_price_per_m2_attribute` — the column is
   `GENERATED ALWAYS AS (price_pln / area_m2) STORED`
   ([`15-database-schema.md`](../15-database-schema.md) §5). A Python-side copy
   can drift from its inputs; the database column cannot.
   `assert not hasattr(normalized, "price_per_m2")`.
3. **`parse` is pure** (repo layout §2 rule 2). `test_normalize_performs_no_io` —
   run the whole normalize path with sockets and filesystem writes patched to
   raise; assert it completes.

## 3. Red-green sequence

Written in this order. Each numbered step is: **write the failing test → see it
fail for the stated reason → implement → see it pass.** No step begins before the
previous one is green.

| Step | Test module | What it pins | Why this order |
|---|---|---|---|
| **0** | — | Fixtures recorded, dated, scrubbed (§10) | Entry criterion 5 |
| **1** | `tests/unit/normalize/test_area_units.py` | Every Polish area form → an exact m² value (§4.1) | F1 is the fatal failure; nothing downstream is meaningful until it is right |
| **2** | `tests/property/test_area_equivalence.py` | Cross-unit equivalence, idempotence, round trip (§7.1) | Catches the forms the exhaustive table missed |
| **3** | `tests/unit/normalize/test_price_parse.py` | Polish price forms → exact PLN; placeholders → failure (§4.2) | |
| **4** | `tests/unit/normalize/test_area_authority.py` | register → structured → body → title, `area_source` recorded (§4.3) | Must be green before bands: bands must judge the *resolved* area |
| **5** | `tests/unit/normalize/test_price_per_m2_crosscheck.py` | F2 — advert states total **and** per-m²: agree, or flag; never choose (§4.4) | |
| **6** | `tests/unit/normalize/test_bands.py` | Amended band, inclusive boundaries, flag-not-drop (§5) | |
| **7** | `tests/unit/normalize/test_quarantine.py` | Reason always non-null, closed enum, quarantine ≠ flag (§6) | |
| **8** | `tests/architecture/test_zoning_claim_isolation.py` | V25 — no path writes advert text into `buildability` (§8) | Architectural; independent of steps 1–7 but gates the same commit |
| **9** | `tests/unit/normalize/test_price_kind.py` | FR-64 — asking / auction_start / tender are distinct and never blended (§9) | |
| **10** | `tests/unit/dedup/test_exact_match.py` | Exact duplicates collapse; `duplicate_count`; `n_before`/`n_after` (§13.1) | Work item 9 starts only after 6 is green |
| **11** | `tests/unit/dedup/test_near_duplicates_not_merged.py` | Near-duplicates **stay separate** (§13.2) | The over-merge direction is the one V56 says falsifies v0 dedup |
| **12** | `tests/property/test_dedup_properties.py` | V47 — exact duplicate leaves median and `n` unchanged; permutation; idempotence (§7.2) | |
| **13** | `tests/architecture/test_no_measured_duplicate_rate.py` | No duplicate rate is claimed anywhere (§13.3) | |
| **14** | `tests/unit/ops/test_quarantine_rate_assertion.py` | V50 — per-reason rates, spike alarms (§6.3) | Δ assertion, written last because it consumes the reason enum from step 7 |
| **15** | mutation run over `lpc.normalize` and `lpc.dedup` | The suite has teeth (§14) | Only meaningful once 1–14 are green |

## 4. Parsing — exact-value tests

### 4.1 Area units (`test_area_units.py`, V28, FR-51, F1)

`ar` = 100 m². `hektar` = 10 000 m². `"12a"` = 1200 m². Decimal comma is standard.
Thousands separator is a space — and in real payloads frequently U+00A0 or U+202F,
which a naive `str.strip()` leaves in place.

One parametrized test, `test_parse_area_exact[<case-id>]`, over this table.
Every row asserts `parse_area(text).m2 == Decimal(expected)` **and**
`parse_area(text).unit == expected_unit`.

| Case id | Input | `m2` | `unit` |
|---|---|---|---|
| `m2_plain` | `"1200 m²"` | `1200` | `m2` |
| `m2_thousands_space` | `"1 200 m²"` | `1200` | `m2` |
| `m2_thousands_nbsp` | `"1 200 m²"` | `1200` | `m2` |
| `m2_thousands_narrow_nbsp` | `"1 200 m²"` | `1200` | `m2` |
| `m2_no_space` | `"1200m²"` | `1200` | `m2` |
| `m2_ascii_2` | `"1200 m2"` | `1200` | `m2` |
| `m2_mkw` | `"1200 mkw"` | `1200` | `m2` |
| `m2_m_kw_dotted` | `"1200 m kw."` | `1200` | `m2` |
| `m2_decimal_comma` | `"1 200,50 m²"` | `1200.50` | `m2` |
| `m2_large_valid` | `"150 000 m²"` | `150000` | `m2` |
| `ar_arow` | `"12 arów"` | `1200` | `ar` |
| `ar_arow_no_diacritic` | `"12 arow"` | `1200` | `ar` |
| `ar_ary` | `"12 ary"` | `1200` | `ar` |
| `ar_ara` | `"1,5 ara"` | `150` | `ar` |
| `ar_singular` | `"1 ar"` | `100` | `ar` |
| `ar_abbrev_spaced` | `"12 a"` | `1200` | `ar` |
| `ar_abbrev_glued` | `"12a"` | `1200` | `ar` |
| `ar_abbrev_dotted` | `"12 ar."` | `1200` | `ar` |
| `ar_decimal_comma` | `"12,5 ara"` | `1250` | `ar` |
| `ha_decimal_comma` | `"0,12 ha"` | `1200` | `ha` |
| `ha_half` | `"0,5 ha"` | `5000` | `ha` |
| `ha_one_and_half` | `"1,5 ha"` | `15000` | `ha` |
| `ha_word` | `"2 hektary"` | `20000` | `ha` |
| `ha_word_genitive` | `"5 hektarów"` | `50000` | `ha` |
| `ha_integer` | `"12 ha"` | `120000` | `ha` |
| `ha_above_band` | `"25 ha"` | `250000` | `ha` |
| `m2_below_band` | `"250 m²"` | `250` | `m2` |

Note the last two rows: they parse **successfully** and are then flagged by the
band check (§5). Parsing and band judgement are separate stages, and the tests
keep them separate.

Additional named tests in the same module:

- `test_parse_area_rejects_bare_number_without_unit` — `parse_area("1200")`
  returns `m2 is None`, `failure == AreaFailure.NO_UNIT`. Guessing m² here is the
  single cheapest way to introduce a 100× error on an `ar`-stated plot.
- `test_parse_area_rejects_empty_and_whitespace` — `""`, `"   "`, `"—"` →
  `AreaFailure.ABSENT`.
- `test_parse_area_marks_approximate` — `parse_area("ok. 1200 m²", "body").m2 ==
  Decimal("1200")`, `.is_approximate is True` and `.confidence == "low"` (D83).
- `test_approximate_marker_reaches_the_interface` — D83 also requires the marker
  to reach the interface. The record the app renders carries `is_approximate`, so
  the reader sees that the figure is the seller's estimate.
- `test_parse_area_sums_a_compound` — `parse_area("1 ha 25 a", "structured").m2
  == Decimal("12500")`, `.confidence == "low"` (D90). A first-value rule reads
  this as 10 000 m² and makes the zł/m² figure 25% too high.
- `test_parse_area_quarantines_a_disagreeing_restatement` — `"1200 m² (15 arów)"`
  → `AreaFailure.CONFLICTING_STATEMENTS` (D90). An agreeing restatement,
  `"1200 m² (12 arów)"`, keeps `confidence == "high"`.
- `test_parse_area_quarantines_a_range` — `"1200-1500 m²"` →
  `AreaFailure.NOT_SINGLE_VALUED` (D82). A midpoint invents a number nobody wrote.
- `test_parse_area_dot_separator` — `"1.200 m²"` →
  `AreaFailure.AMBIGUOUS_SEPARATOR` (D79). The one carve-out is a dot followed by
  exactly four digits with the unit `ha`, the parcel register's own format:
  `"1.2500 ha"` → `Decimal("12500")`, `confidence == "low"`.
- `test_bare_a_needs_a_field_or_a_nearby_keyword` — D86. `"12 a"` in a structured
  field or a title parses as 1200 m². The same text in body prose parses only
  within 40 characters of an area keyword. `"Dojazd 12 a nawet 15 minut"` yields
  no area.
- `test_parse_area_unknown_unit_fails_loudly` — `"12 morgów"` →
  `AreaFailure.UNKNOWN_UNIT`, never a silent m² reading.
- `test_ar_and_ha_multipliers_are_exactly_100_and_10000` — asserts the constants
  directly: `AR_IN_M2 == Decimal("100")`, `HA_IN_M2 == Decimal("10000")`. Trivial,
  and it is the assertion a transposed-constant mutant dies on (§14).

**Hand audit, not only unit tests.** V10 and `18` §7 both require it: 20 listings
stated in ar or ha are hand-checked against the rendered zł/m², **zero errors
tolerated**. Script: `scripts/audit_unit_conversion.py`, run at first ingest and
quarterly. A 100× error is silent and fatal; the unit tests only prove the forms
we thought of.

### 4.2 Prices (`test_price_parse.py`)

`test_parse_price_exact[<case-id>]`, asserting `parse_price(text).pln ==
Decimal(expected)`:

| Case id | Input | `pln` |
|---|---|---|
| `plain_zl` | `"250 000 zł"` | `250000` |
| `nbsp_zl` | `"250 000 zł"` | `250000` |
| `pln_suffix` | `"1 250 000 PLN"` | `1250000` |
| `grosze` | `"250 000,50 zł"` | `250000.50` |
| `no_currency` | `"250000"` | `250000` |
| `negotiable_suffix` | `"250 000 zł do negocjacji"` | `250000` |

And the failure cases, `test_parse_price_placeholder_is_not_a_price[<case-id>]`,
each asserting `.pln is None` and the stated failure:

| Input | `failure` |
|---|---|
| `"Zapytaj o cenę"` | `PriceFailure.PLACEHOLDER` |
| `"zapytaj o cenę"` | `PriceFailure.PLACEHOLDER` |
| `"cena do uzgodnienia"` | `PriceFailure.PLACEHOLDER` |
| `"0 zł"` | `PriceFailure.NON_POSITIVE` |
| `""` | `PriceFailure.ABSENT` |

`"0 zł"` is separated from the placeholders deliberately: the schema has
`CHECK (price_pln > 0)`, so a zero would be a constraint violation at insert
time — a crash, not a wrong number. It is caught at normalize time with its own
reason so the failure appears in the quarantine composition (§6.3) instead of in
the run's exception log.

### 4.3 Authority order when advert and register disagree (`test_area_authority.py`)

FR-51 and FR-15: **register → structured field → body → title**, most authoritative
first, with the chosen source recorded in `area_source`
([`15-database-schema.md`](../15-database-schema.md) §5, `CHECK (area_source IN
('register','structured','body','title'))`).

| Test | Inputs | Asserts |
|---|---|---|
| `test_register_wins_over_advert` | register `1450`, structured `1200`, body `1200`, title `1200` | `m2 == Decimal("1450")`, `source == "register"` — the exact V28 conflict case |
| `test_structured_wins_when_no_register` | register `None`, structured `1200`, body `1150`, title `1000` | `m2 == 1200`, `source == "structured"` |
| `test_body_wins_when_no_register_or_structured` | register/structured `None`, body `1150`, title `1000` | `m2 == 1150`, `source == "body"` |
| `test_title_is_last_resort` | only title `1000` | `m2 == 1000`, `source == "title"` |
| `test_no_area_anywhere_yields_no_resolution` | all `None` | raises/returns the `AREA_MISSING` failure → quarantine (§6) |
| `test_advert_never_overrides_register_even_when_more_precise` | register `1450`, structured `1449.87` | `m2 == 1450`, `source == "register"` — precision is not authority |
| `test_conflicting_areas_set_the_conflict_flag` | register `1450`, structured `1200` | `conflict is True` **and** the advert value is retained on the record, not discarded |
| `test_agreeing_areas_do_not_set_the_conflict_flag` | register `1200`, structured `1200` | `conflict is False` |
| `test_conflict_threshold_boundary` | register `1200`, structured `1260.00` and `1260.01` | D81: `conflict` is set when the relative difference is **more than 5%**. `1260.00` is exactly 5% and does not flag; `1260.01` flags |

**The threshold is 5%, not 2%** (D81). The owner chose the looser value. The
consequence is recorded here so a reader sees it: a real register-versus-advert
mismatch below 5% passes unflagged. On a 1200 m² plot that is a gap of up to
60 m².

`test_conflicting_areas_set_the_conflict_flag` carries rule 7: the disagreement is
kept and shown, in the same spirit as the `zoning_claim` / `buildability`
disagreement (`06` §1). We record which source won *and* what the loser said.

### 4.4 Price-for-something-else cross-check (`test_price_per_m2_crosscheck.py`, F2)

Where the advert states **both** a total price and a per-m² price, they are
cross-checked. We **flag mismatches rather than choosing** — F2's detector, stated
verbatim in `20` §3.

| Test | Setup | Asserts |
|---|---|---|
| `test_stated_and_derived_price_per_m2_agree` | total `240000`, area `1200 m²`, advert says `200 zł/m²` | no flag |
| `test_stated_and_derived_price_per_m2_disagree_is_flagged` | total `240000`, area `1200 m²`, advert says `20 000 zł/m²` | `Flag.PRICE_PER_M2_MISMATCH` present, **and** `price_pln == 240000` unchanged — we do not silently switch to the stated figure |
| `test_mismatch_does_not_quarantine` | as above | the record is normalized and visible, not quarantined |

A 100× mismatch here is the same defect as F1 seen from the other side, which is
why the fixture uses exactly 100×.

## 5. Validity bands (`test_bands.py`, FR-12 as amended, V10)

Band: area `[300, 200 000]` m², price `[1, 100 000]` PLN/m², **inclusive**.
Outside → **flagged, kept, visible**. Never dropped. Never quarantined.

| Test | Input | Asserts |
|---|---|---|
| `test_band_constants_match_amended_fr12` | — | `AREA_BAND == (Decimal("300"), Decimal("200000"))`; `PRICE_PER_M2_BAND == (Decimal("1"), Decimal("100000"))` (§1) |
| `test_area_at_lower_boundary_is_in_band` | `300` | `band_flags(...) == frozenset()` |
| `test_area_just_below_lower_boundary_is_flagged` | `299.99` | `Flag.AREA_BELOW_BAND` |
| `test_area_at_upper_boundary_is_in_band` | `200000` | no flag |
| `test_area_just_above_upper_boundary_is_flagged` | `200000.01` | `Flag.AREA_ABOVE_BAND` |
| `test_price_per_m2_at_boundaries_is_in_band` | `1`, `100000` | no flag |
| `test_price_per_m2_below_band_is_flagged` | `0.99` | `Flag.PRICE_BELOW_BAND` |
| `test_price_per_m2_above_band_is_flagged` | `100000.01` | `Flag.PRICE_ABOVE_BAND` |
| `test_out_of_band_record_is_flagged_not_dropped_and_not_quarantined` | 25 ha farmland at `3 zł/m²` | result is a `NormalizedListing`, **not** a `QuarantinedRecord`; `Flag.AREA_ABOVE_BAND` present; the record appears in the emitted rows |
| `test_out_of_band_record_carries_its_flag_to_the_surface` | as above | the flag survives to the record the app renders — an out-of-band figure is never displayed bare |
| `test_out_of_band_record_is_excluded_from_aggregates` | 10 in-band records plus the 25 ha record | the aggregate's `n == 10` (D85) |
| `test_out_of_band_record_stays_in_the_corpus_and_in_dedup` | as above | the record keeps its cluster and appears in the corpus count. D85 excludes it from aggregates only |
| `test_low_confidence_area_enters_aggregates_flagged` | a `low`-confidence area from D80, D83, D86 or D90 | the record is in the aggregate's input set and carries its confidence flag (D87) |
| `test_band_check_reads_the_exact_quotient` | area `3.00`, price `300000.01`; exact quotient `100000.00333…`, stored `100000.00` | `Flag.PRICE_ABOVE_BAND` (D88). The check reads the exact quotient, not the rounded stored value |
| `test_superseded_band_values_are_not_in_band_constants` | — | asserts `Decimal("100")` and `Decimal("500000")` are **not** the area band edges; fails loudly if V10's stale numbers are copied in |

The 25 ha case is the one O12 was closed for. If it is quarantined or dropped, a
whole legitimate segment — rural farmland, the product's subject — disappears, and
that is F12 by another route.

**Flagged, out-of-band and low-confidence are three different states.** D85 keeps
an out-of-band record visible and takes it out of the aggregates. D87 keeps a
low-confidence area in the aggregates and flags it. Both follow rule 7: always
show, always flag.

## 6. Quarantine (`test_quarantine.py`, V10, V50, F12)

### 6.1 What quarantine is, and what it is not

**Quarantined**: the record has **no usable price or area at all** — a
`"zapytaj o cenę"` placeholder, a missing area, an unparseable unit. It cannot
produce a zł/m² figure, so it cannot be a listing.

**Flagged**: the record has a usable price and area that fall outside the validity
band. It is kept and shown with its flag (§5).

Conflating the two is the failure this section exists to prevent — quarantining
out-of-band records would silently amputate farmland from the corpus while the
quarantine rate looked healthy in aggregate.

| Test | Asserts |
|---|---|
| `test_missing_price_is_quarantined_with_reason` | `reason == QuarantineReason.PRICE_MISSING` |
| `test_price_placeholder_is_quarantined_with_reason` | input `"Zapytaj o cenę"` → `reason == PRICE_PLACEHOLDER` |
| `test_missing_area_is_quarantined_with_reason` | `reason == AREA_MISSING` |
| `test_unparseable_area_unit_is_quarantined_with_reason` | `"12 morgów"` → `reason == AREA_UNIT_UNKNOWN` |
| `test_bare_number_area_is_quarantined_not_assumed_m2` | `"1200"` with no unit → `reason == AREA_NO_UNIT` |
| `test_non_positive_price_is_quarantined_with_reason` | `"0 zł"` → `reason == PRICE_NON_POSITIVE` |
| `test_ambiguous_dot_is_quarantined_with_reason` | `"1.200 m²"` → `reason == AREA_AMBIGUOUS_SEPARATOR` (D79) |
| `test_area_range_is_quarantined_with_reason` | `"1200-1500 m²"` → `reason == AREA_NOT_SINGLE_VALUED` (D82) |
| `test_disagreeing_restatement_is_quarantined_with_reason` | `"1200 m² (15 arów)"` → `reason == AREA_CONFLICTING_STATEMENTS` (D90) |
| `test_out_of_band_is_not_quarantined` | the 25 ha case → **not** a `QuarantinedRecord` (mirrors §5, asserted from both sides deliberately) |

D80 parses the magnitude abbreviations, so there is **no**
`PRICE_AMBIGUOUS_MAGNITUDE` reason. A reason that no input can produce is dead
code in a closed enum, and §6.2's `test_every_reason_has_a_producing_fixture`
deletes it.

### 6.2 Reason is structurally guaranteed

| Test | Asserts |
|---|---|
| `test_every_quarantined_record_has_a_non_null_reason` | over **every** fixture in `tests/fixtures/quarantine/`: `record.reason is not None` and `record.reason != ""` |
| `test_quarantine_reason_is_a_member_of_the_closed_enum` | `record.reason in QuarantineReason` — free-text reasons are rejected, because V50's per-reason rates cannot be computed over free text |
| `test_quarantining_without_a_reason_raises` | constructing a `QuarantinedRecord` with `reason=None` raises `ValueError`; the reason is a required constructor argument, not a field set afterwards |
| `test_quarantine_reason_column_is_not_null` (integration) | the DDL for `listing_quarantine.reason` is `NOT NULL` — the schema-level half of the same guarantee ([`15`](../15-database-schema.md) §5) |
| `test_quarantined_record_retains_its_listing_ref` | `listing_ref` carries source, external id and url, so a fixed parser can re-derive the record from `raw_document` (FR-72) |
| `test_quarantined_records_never_reach_aggregates` | a fixture set of 10 records, 3 quarantined → the aggregate's `n == 7` |
| `test_quarantined_count_is_reported_by_the_run` | the run report states 3, so the loss is visible rather than merely absent |

### 6.3 Per-reason rate monitoring (`test_quarantine_rate_assertion.py`, V50, F12)

The Δ assertion, living in `ops/assertions/` and running **inside the pipeline**,
not in the test suite (repo layout §4). What the test suite verifies is the
assertion's own logic, against synthetic rate histories:

| Test | Setup | Asserts |
|---|---|---|
| `test_per_reason_rates_are_computed_separately` | 100 records: 5 `AREA_UNIT_UNKNOWN`, 1 `PRICE_PLACEHOLDER` | the report has a rate per reason, keyed by enum member — not one aggregate number |
| `test_spike_in_one_reason_alarms_even_when_total_is_flat` | baseline 6% split evenly; new run still 6% total but entirely `AREA_UNIT_UNKNOWN` | alarm fires. **This is the F12 test** — a total-only monitor passes this scenario while every hectare-stated plot vanishes |
| `test_stable_rates_do_not_alarm` | rates within the rolling baseline | no alarm |
| `test_new_reason_appearing_alarms` | a reason with no baseline appears at 3% | alarm fires — an unseen reason is upstream drift |
| `test_alarm_blocks_publication` | alarm fired | the pipeline stage returns a blocking result; the coverage page is not refreshed with the run's output ([`11-operations.md`](../11-operations.md) — a failed run is never presented as though it passed) |

Baselines are set from the first runs' actuals, not guessed — the same discipline
as O25 for the LOOCV thresholds.

## 7. Property-based equivalences

`20` §4.2 names three families for parsers and normalization. Written with
Hypothesis over generated inputs, not fixed examples.

### 7.1 Area (`tests/property/test_area_equivalence.py`)

Every call below passes `field="structured"` unless the row says otherwise. D86
makes the field a required argument, so a property test states it too.

| Test | Property |
|---|---|
| `test_cross_unit_equivalence_fixed` | `parse_area("12 arów").m2 == parse_area("1 200 m²").m2 == parse_area("0,12 ha").m2 == Decimal("1200")` — the three unit forms named in `20` §4.2, asserted as one statement |
| `test_ha_ar_ladder_sums_a_compound` | for generated `h` and `a`: `parse_area(f"{h} ha {a} a").m2 == parse_area(f"{h} ha").m2 + parse_area(f"{a} a").m2` — the D90 sum rule as a property, not one example |
| `test_cross_unit_equivalence_generated` | for generated `n` in `[1, 2000]` ares: `parse_area(f"{n} arów").m2 == parse_area(f"{n*100} m²").m2 == parse_area(format_ha(n/100)).m2` |
| `test_ha_ar_m2_ladder` | for generated `h`: `parse_area(f"{h} ha").m2 == 100 * parse_area(f"{h} a").m2` — pins the two multipliers' *ratio*, killing a mutant that scales both |
| `test_decimal_comma_and_thousands_space_are_equivalent` | `parse_area("1 200,50 m²") == parse_area("1200,50 m²")` for generated values |
| `test_nbsp_and_ascii_space_are_equivalent` | generated values with U+0020 / U+00A0 / U+202F separators all parse identically |
| `test_idempotence` | `normalize(normalize(x)) == normalize(x)` for generated parsed items |
| `test_round_trip_canonical_form` | `parse_area(format_area(m2)).m2 == m2` for generated `m2` in `[1, 10**7]` — round trip on the canonical form only, per `20` §4.2 |
| `test_parse_is_total` | no generated string ever raises an unhandled exception: every input yields either a value or a named failure. A crash in the parser stops a crawl; a named failure quarantines one record |

### 7.2 Dedup metamorphic properties (`tests/property/test_dedup_properties.py`, V47)

The two rows of `20` §4.3 that this work item owns, plus determinism:

| Test | Property |
|---|---|
| `test_adding_an_exact_duplicate_leaves_median_unchanged` | median zł/m² before == after, exactly |
| `test_adding_an_exact_duplicate_leaves_n_unchanged` | post-dedup `n` unchanged; `duplicate_count` increments instead |
| `test_dedup_is_order_invariant` | for generated permutations of the same input, `dedup_exact` returns the same clusters and the same canonical record |
| `test_dedup_is_idempotent` | `dedup_exact(dedup_exact(x)) == dedup_exact(x)` |
| `test_scaling_price_and_area_together_leaves_price_per_m2_unchanged` | ×10 on both leaves zł/m² identical — the F1-adjacent metamorphic check, run against the normalize+aggregate path |
| `test_doubling_every_price_doubles_the_median_exactly` | as `20` §4.3 |

The duplicate case is load-bearing for a reason `20` §4.3 states plainly: it tests
that the filter actually filters, which a fixture test can pass while quietly
ignoring its arguments.

## 8. `zoning_claim` never writes buildability (`test_zoning_claim_isolation.py`, V25, FR-48)

Three tests, in ascending strength.

| Test | Kind | Asserts |
|---|---|---|
| `test_mislabelled_advert_retains_both_values` | unit | fixture advert with category *"działka budowlana"* and register/planning data saying agricultural → `zoning_claim == "działka budowlana"` **and** the planning-derived buildability is `agricultural`; both survive; the disagreement flag is set |
| `test_normalized_listing_has_no_buildability_field` | architecture | `listing` has no `buildability` column ([`15`](../15-database-schema.md) §5: it lives only on `parcel_zoning`). `assert "buildability" not in NormalizedListing.__annotations__` |
| `test_extract_module_cannot_write_buildability` | architecture | static import/assignment check: no symbol in `lpc.extract` or `lpc.normalize` assigns to `buildability`, and neither module imports `lpc.enrich.zoning`'s writers (repo layout §3) |
| `test_zero_rows_have_buildability_sourced_from_advert_text` | Δ assertion | count of rows whose buildability provenance is advert text **must be 0** |

`06` §1 calls this the single most important rule in that document: collapsing
`zoning_claim` into `buildability` lets seller marketing set the price expectation,
which inverts the product's purpose. The architectural test is what keeps it true
after the unit test's fixture stops being representative.

## 9. `price_kind` separates asking, auction start and tender (`test_price_kind.py`, FR-64, F9, V46)

`price_kind` is distinct from `price_type`. `price_type ∈ {offering, sales}`
(rule 6). `price_kind ∈ {asking, auction_start, tender}`. An auction starting
price is a statutorily-derived floor; a tender price is a third quantity. **No
aggregate may span kinds.**

| Test | Asserts |
|---|---|
| `test_portal_listing_is_price_kind_asking` | portal fixture → `price_kind == "asking"`, `price_type == "offering"` |
| `test_auction_notice_is_price_kind_auction_start` | bailiff fixture → `price_kind == "auction_start"` |
| `test_kowr_tender_is_price_kind_tender` | KOWR fixture → `price_kind == "tender"` |
| `test_price_kind_is_never_null` | every normalized record has a kind; there is no default that silently absorbs an unrecognised source |
| `test_price_kind_and_price_type_are_independent_fields` | setting one never sets the other; an auction start price is still `price_type == "offering"` |
| `test_asking_median_unchanged_by_adding_auction_rows` | fixture with auction rows priced far below the asking distribution: the asking median is **identical** before and after they are added — the V46 construction |
| `test_aggregation_key_includes_price_kind` | architecture: the grouping key tuple contains `price_kind` |
| `test_no_aggregate_spans_price_kinds` | Δ assertion over the emitted aggregates: every aggregate's input set has exactly one distinct kind |

F9's damage is specific: blended auction floors drag medians down and read as a
market movement. `test_asking_median_unchanged_by_adding_auction_rows` is the test
that would have caught it.

## 10. Fixtures (entry criterion 5)

Recorded, dated, scrubbed of personal data. `tests/fixtures/<source>/`, per repo
layout §1.

| Directory | Contents |
|---|---|
| `fixtures/portal/areas/` | One advert per row of §4.1 — real payload snippets, one file per unit form, including the NBSP and glued-`a` cases |
| `fixtures/portal/prices/` | One per row of §4.2, including all placeholder phrasings |
| `fixtures/portal/conflict/` | One advert whose title, body and structured field disagree on area, plus its register area — drives §4.3 |
| `fixtures/portal/both_prices/` | Adverts stating total **and** per-m² price, one agreeing and one 100× off (§4.4) |
| `fixtures/quarantine/` | One record per `QuarantineReason` member, so §6.2 iterates the whole enum |
| `fixtures/bands/` | The 25 ha farmland record; the 250 m² record; records at exactly 300 and exactly 200 000 |
| `fixtures/dedup/exact/` | Same listing from one source twice; the same plot from two sources with an identical (area, price, gmina, asset_class) key |
| `fixtures/dedup/round/` | The round pairs of §12.1 — one that merges falsely, one separated by `asset_class` |
| `fixtures/dedup/near/` | The five near-miss pairs of §13.2 — **v0 must not merge these**. The `asset_class` pair lives in `dedup/round/` |
| `fixtures/price_kind/` | One portal, one bailiff, one KOWR record with deliberately divergent values |

Every fixture file records its capture date. Seller names, phone numbers and
addresses are scrubbed at capture, not later (FR-23).

## 11. Silent-failure coverage

| # | Failure | Detector in this work item |
|---|---|---|
| F1 | Area unit mis-parsed | §4.1 exhaustive table; §7.1 equivalence properties; §5 band flags; `scripts/audit_unit_conversion.py` over 20 ar/ha listings, zero errors; Δ distribution check for a spike at 100× the mode |
| F2 | Price is for something else | §4.4 cross-check — flag, never choose |
| F3 | Duplicates inflate `n` | §13.1 `n_before` / `n_after` reported side by side; §7.2 median-unchanged property |
| F3 (reverse) | A false merge deflates `n` | §12.1 records the risk D78 accepts; §13.2 asserts the known false merge; the run report carries the caveat. V56's monitoring is the only detector |
| F9 | Auction/tender blended with asking | §9 — distinct kind, aggregation key, unchanged-median test |
| F12 | Quarantine swallows a class | §6.3 per-reason rates; §5's flag-not-quarantine rule keeps out-of-band records in the corpus |

Not addressed here, by design: F4–F8, F10, F11, F13 belong to other work items.

## 12. The settled rules (rule 2)

The owner answered all twelve questions this work item raised. Batches 18 and 19
of [`00-decisions.md`](../00-decisions.md) record them. Nothing here is a
proposal. Nothing here waits for ratification.

| # | Rule | Decision | Governs |
|---|---|---|---|
| O-N1 | A dot in an area string is ambiguous and the record is quarantined. The one carve-out is a dot followed by exactly four digits with the unit `ha`, which is the parcel register's own format | **D79** | `test_parse_area_dot_separator`; plan §1.5 |
| O-N2 | An area range is not single-valued and the record is quarantined | **D82** | `test_parse_area_quarantines_a_range`; plan §1.5 |
| O-N3 | `"250 tys. zł"` and `"1,2 mln zł"` parse, confidence `low` | **D80** | `test_parse_price_abbreviated_magnitude`; plan §2 |
| O-N4 | `conflict` is set when the register and a lower-authority area differ by **more than 5%** | **D81** | `test_conflict_threshold_boundary`; plan §3.2 |
| O-N5 | `"ok. 1200 m²"` parses, marks `is_approximate`, confidence `low`, and the marker reaches the interface | **D83** | `test_parse_area_marks_approximate`; plan §1.4 |
| O-N6 | The cross-source match key is **(area, price, gmina, asset_class)** | **D78** | §13.1, §13.2; plan §5.3 |
| O-N7 | The canonical record is the earliest `first_seen_at`, then the lowest `source_id`, then the lowest `external_id` | **D84** | `test_canonical_record_selection_is_deterministic`; plan §5.2 |
| O-N8 | An out-of-band record stays visible and stays in the corpus. Aggregates exclude it | **D85** | §5; plan §4.3 |
| O-N9 | A compound area **sums**. An agreeing restatement keeps `high` confidence. A disagreeing restatement is quarantined | **D90** | `test_parse_area_sums_a_compound`; plan §1.6 |
| O-N10 | The bare `a` abbreviation reads as ares in a structured field or a title, or in body text within 40 characters of an area keyword | **D86** | `test_bare_a_needs_a_field_or_a_nearby_keyword`; plan §1.3 |
| O-N11 | A low-confidence area enters the aggregates, flagged | **D87** | `test_low_confidence_area_enters_aggregates_flagged` |
| O-N12 | The band check reads the exact quotient, not the stored rounded value | **D88** | `test_band_check_reads_the_exact_quotient`; plan §4.3 |

**D90 supersedes an earlier answer.** Batch 18 first took the first value of a
compound, which read `"1 ha 25 a"` as 10 000 m² instead of 12 500 m². That is a
20% area error and a 25% error in every zł/m² figure derived from it. Batch 19
re-asked and chose the sum. I was wrong to propose the first-value rule.

### 12.1 The residual risk D78 accepts

D78 chose the four-part key over the round-number guard I proposed. The owner
accepted a named cost, and it is written here because a reader of this document
must see it:

> **Two building plots of 1000 m² at 100 000 zł in one gmina still merge.** The
> key cannot tell them apart. The corpus loses one real observation and reports a
> `duplicate_count` of 2 where the truth is two separate plots.

Round areas and round prices are common in this market, so the case is not
hypothetical. §13.2 asserts the merge as a **known false merge**, not as a
success. V56's false-merge monitoring is the only detector for it. The run report
states the accepted risk, so no reader takes the `duplicate_count` as measured
truth.

## 13. Dedup at v0 strength only (FR-70, V56)

v0 dedup is **deliberately weaker** than FR-13. FR-13's matcher — geohash-6, title
shingles, image perceptual hash, hashed seller contact, scored against a
200-listing labelled set — is out of scope (`18` §4 excludes labelled evaluation
sets for extraction and dedup). What v0 ships is exact matching, and the honesty
requirement that comes with it.

### 13.1 Exact matches collapse (`test_exact_match.py`)

**The match key is `(area_m2, price_pln, teryt_gmina, asset_class)`** (D78). It is
a quadruple, not the triple V56 first named. `zoning_claim` and
`seller_contact_hash` are **not** in the key.

| Test | Setup | Asserts |
|---|---|---|
| `test_same_source_same_external_id_is_one_listing` | the same listing ingested twice | one row; `UNIQUE (source_id, external_id)` upserts rather than inserting ([`15`](../15-database-schema.md) §5) |
| `test_cross_source_exact_key_collapses` | two sources, identical `(area_m2, price_pln, teryt_gmina, asset_class)` | one `plot_cluster`, `duplicate_count == 2`, both listings reference it |
| `test_match_key_is_exactly_the_four_named_fields` | — | the key tuple is the four fields of D78, in that order. A fifth field added without a decision fails this test |
| `test_duplicate_count_reflects_cluster_size` | three exact matches | `duplicate_count == 3` |
| `test_canonical_record_selection_is_deterministic` | three exact matches in six different input orders | the same canonical listing every time — earliest `first_seen_at`, then lowest `source_id`, then lowest `external_id` (D84) |
| `test_n_before_and_after_dedup_are_both_reported` | 10 listings, 3 of them one plot | the result carries `n_before == 10` and `n_after == 8`, both surfaced. F3's detector: *more data looks like better data*, so both numbers are shown side by side |
| `test_singleton_gets_duplicate_count_one` | one listing | `duplicate_count == 1`, and it still gets a cluster — no special-casing that later code must remember |

### 13.2 Near-duplicates must **not** merge (`test_near_duplicates_not_merged.py`)

The direction V56 names as falsifying: *a near-duplicate being merged — v0 must
not over-merge*. Each test asserts **two** clusters and `duplicate_count == 1` on
each.

| Test | The pair |
|---|---|
| `test_price_differing_by_two_percent_does_not_merge` | same plot, two agencies, `250 000` vs `255 000 zł` — genuinely the same plot, and v0 correctly **misses** it |
| `test_reworded_title_does_not_merge` | identical area and gmina, different price, reworded title |
| `test_rounded_area_does_not_merge` | `1200 m²` vs `1205 m²` |
| `test_adjacent_plots_same_area_same_street_do_not_merge` | two genuinely different neighbouring plots, identical area, **different prices** |
| `test_same_area_and_price_in_different_gminas_do_not_merge` | identical `(area, price)`, different TERYT |
| `test_differing_asset_class_never_merges` | identical `(area, price, gmina)`, one `land_building` and one `land_agricultural`. D78 added `asset_class` to the key for this pair |

`test_price_differing_by_two_percent_does_not_merge` deserves a comment in the
test file: it asserts a **known miss**, not a success. It is here so that a future
FR-13 matcher flips it deliberately rather than by accident.

**The known false merge (D78).** One pair goes the other way, and it gets its own
test so the loss is recorded rather than discovered later:

| Test | The pair | Asserts |
|---|---|---|
| `test_identical_round_pair_merges_and_is_a_known_false_merge` | two genuinely different building plots, both `1000 m²` at `100 000 zł`, both in one gmina, both `land_building` | **one** cluster, `duplicate_count == 2` — the merge D78 accepts (§12.1) |
| `test_run_report_states_the_accepted_false_merge_risk` | any run | the report carries the caveat: round pairs can merge, and the residual false-merge rate is unknown |

The first test asserts a **wrong answer that the product accepts**. It carries
that sentence verbatim as a comment, in the same form as the known-miss test
above. A later FR-13 matcher flips it deliberately.

### 13.3 No measured duplicate rate may be claimed (`test_no_measured_duplicate_rate.py`)

V56: *the duplicate rate is unknown rather than measured*, and *a claim of a
measured duplicate rate anywhere* falsifies.

| Test | Asserts |
|---|---|
| `test_dedup_result_exposes_no_duplicate_rate` | `DedupResult` has no `duplicate_rate`, `false_merge_rate` or `recall` attribute |
| `test_run_report_states_exact_match_only` | the run report and the coverage-page payload carry the caveat string — dedup is exact-match only, so the residual duplicate rate is **unknown, not measured** |
| `test_ui_surface_carries_the_exact_match_caveat` | the Streamlit surface renders the caveat wherever `n` is shown (FR-71, `21` §U5) |
| `test_no_module_imports_a_dedup_labelled_set` | architecture: nothing under `lpc.dedup` reads `tests/labelled/` — v0 has no such set, and a stub one would manufacture a number |

Also carried over as a manual check from `18` §7: **scan 50 listings for the same
plot twice**. It is an eyeball, it produces no metric, and it is written down as
an eyeball rather than dressed up as a measurement.

## 14. Mutation testing (`20` §4.8, D58)

Run over `lpc.normalize` and `lpc.dedup` once §3 steps 1–14 are green. These are
functions whose bugs are invisible in the output, which is exactly where mutation
testing earns its cost.

Mutants that **must** be killed, listed so the run is checked against intent
rather than only against a surviving-mutant percentage:

| Mutant | Killed by |
|---|---|
| `AR_IN_M2` 100 → 10 | `test_ar_and_ha_multipliers_are_exactly_100_and_10000`, every `ar_*` row of §4.1 |
| `HA_IN_M2` and `AR_IN_M2` swapped | §7.1 `test_ha_ar_m2_ladder` |
| Band comparison `<` → `<=` at either edge | §5 boundary tests at `300` and `200000` |
| Band lower edge 300 → 100 (the superseded value) | `test_superseded_band_values_are_not_in_band_constants` |
| Authority order reversed (title first) | §4.3 `test_register_wins_over_advert` |
| The `register` branch dropped from `resolve_area` | same |
| Quarantine reason defaulted to a constant instead of the failure's own | §6.2 enum-membership and per-reason tests |
| The out-of-band branch routed to quarantine | `test_out_of_band_record_is_flagged_not_dropped_and_not_quarantined` |
| `price_kind` dropped from the aggregation key | §9 `test_aggregation_key_includes_price_kind` |
| Dedup equality loosened to `abs(a - b) < ε` | §13.2 near-duplicate tests |
| `duplicate_count` incremented on the wrong cluster | §13.1 |
| `asset_class` dropped from the match key | §13.2 `test_differing_asset_class_never_merges`; §13.1 `test_match_key_is_exactly_the_four_named_fields` |
| Compound area takes the first value instead of the sum | §4.1 `test_parse_area_sums_a_compound` (D90) |
| Conflict threshold 5% → 2% | §4.3 `test_conflict_threshold_boundary` |
| Band check reads the rounded stored quotient | §5 `test_band_check_reads_the_exact_quotient` (D88) |

A surviving mutant in this list is a missing test, and the test is added before
the work item is called done.

## 15. Traceability

| Requirement | Section | Validation |
|---|---|---|
| FR-11 canonical schema | §2 | V10 |
| FR-12 `price_per_m2`, bands, quarantine | §5, §6 | V10 |
| FR-13 / FR-70 dedup (v0 strength) | §13 | V56, V47 |
| FR-15 registry area not advert area | §4.3 | V28 |
| FR-48 `zoning_claim` ≠ `buildability` | §8 | V25 |
| FR-51 unit normalisation + authority order | §4.1, §4.3 | V28 |
| FR-64 price kind | §9 | V46 |
| FR-72 re-parse from raw payloads | §6.2 (`listing_ref`) | V57 |

## 16. Definition of done

1. Every test in §3 written, seen failing, then passing — in that order.
2. Every test that §12 governs is written. No `blocked` marker remains in
   `tests/unit/normalize` or `tests/unit/dedup`.
3. Fixtures committed, dated, scrubbed.
4. The 20-listing ar/ha hand audit run with **zero** errors (`18` §7).
5. The mutation run in §14 leaves none of the listed mutants alive.
6. The Δ assertions — quarantine reason non-null, per-reason rates, no aggregate
   spanning price kinds, zero advert-sourced buildability — wired into the
   pipeline, not only into the test suite.
7. `04-validation.md` V10's superseded band corrected in its own commit (§1).
