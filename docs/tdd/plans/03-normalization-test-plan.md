# Test plan — parse/normalize and v0 dedup (pass 2 detail)

Pass 2, step 5 of the standard workflow ([`CLAUDE.md`](../../../CLAUDE.md) rule 8),
for [`03-normalization-and-dedup.md`](../03-normalization-and-dedup.md).

Pass 1 named the tests and fixed their order. **This document is the data**: every
input string, every expected value, every expected failure, every fixture row and
the CI wiring that runs them. A developer should be able to type the tables in
without a further decision. Every question this plan raised is answered, so no
table holds a proposal (rule 2).

Read with, not instead of, the pass-1 spec: the red-green order (§3 there), the
contracts (§2 there) and the mutation list (§14 there) are not repeated here.

---

## 0. The decisions this plan carries

The pass-1 spec left eight open questions, **O-N1..O-N8**. Writing the concrete
data surfaced four more. The owner answered all twelve. Batches 18 and 19 of
[`00-decisions.md`](../../00-decisions.md) record them.

**No row in this plan is a proposal, and no row waits for ratification.** Every
table below states a decided value.

| # | Settled rule | Decision | Where the data lives |
|---|---|---|---|
| O-N1 | A dot in an area string quarantines the record as `area_ambiguous_separator`. **One carve-out:** a dot followed by **exactly four digits** with the unit `ha` (`"1.2500 ha"`, the register's own format) reads as a decimal point, confidence `low` | **D79** | §1.5 |
| O-N2 | An area range quarantines the record as `area_not_single_valued` | **D82** | §1.5 |
| O-N3 | `"250 tys. zł"` and `"1,2 mln zł"` parse the multiplier, confidence `low` | **D80** | §2 |
| O-N4 | `conflict` is set at a relative difference of **more than 5%**, against any lower-authority source | **D81** | §3.2 |
| O-N5 | `"ok. 1200 m²"` parses, `is_approximate=True`, confidence `low`, and the marker reaches the interface | **D83** | §1.4 |
| O-N6 | The cross-source match key is **`(area_m2, price_pln, teryt_gmina, asset_class)`**. There is **no** round-number guard | **D78** | §5.3 |
| O-N7 | The canonical record is the earliest `first_seen_at`, then the lowest `source_id`, then the lowest `external_id` | **D84** | §5.2 |
| O-N8 | An out-of-band record stays in the corpus and on the plot page, with its flag. Aggregates exclude it | **D85** | §4.3 row B9 |
| O-N9 | A compound area **sums**, confidence `low`. An agreeing restatement keeps confidence `high`. A disagreeing restatement quarantines as `area_conflicting_statements` | **D90** | §1.6 |
| O-N10 | `12a` / `12 a` reads as ares in a structured field or a title, or in body text within 40 characters of an area keyword (`powierzchnia`, `pow.`, `działka`, `grunt`). Otherwise there is no area | **D86** | §1.3 |
| O-N11 | A low-confidence area enters the aggregates, flagged, with the same "always show, always flag" treatment as a thin `n` (rule 7) | **D87** | §4.5 |
| O-N12 | The band check reads the **exact `Decimal` quotient**, not the `NUMERIC(12,2)` value the generated column stores | **D88** | §4.3 row B12 |

**Two answers changed the numbers I had proposed.**

- D81 set the conflict threshold at 5%, not the 2% I proposed. §3.2's boundary
  rows are recomputed against 1260.00 and 1260.01.
- D90 supersedes an earlier answer that took the first value of a compound. That
  rule read `"1 ha 25 a"` as 10 000 m² instead of 12 500 m² — a 20% area error and
  a 25% error in every zł/m² figure taken from it. I was wrong to propose it.

D78 rejected the round-number guard I proposed and accepted a named cost. §5.3
records the cost and asserts it as a test.

`@pytest.mark.blocked("O-Nn")` stays as a mechanism, and its gate stays in CI:

- `test_every_blocked_marker_names_an_open_question` — the string in each `blocked`
  marker must match an entry in `00-decisions.md` **that has no recorded answer**.
  This is rule 2 made mechanical rather than remembered.

That gate now requires **zero** `blocked` markers under `tests/unit/normalize` and
`tests/unit/dedup`. Every question this work item raised has a recorded answer, so
any surviving marker fails CI.

---

## 1. `parse_area` — the complete parametrised table

**Contract extension.** Pass 1 gave `AreaParse(m2, unit, is_approximate, failure)`.
This plan adds `confidence: Literal["high","low","unknown"]`, using the vocabulary
already fixed in [`06-taxonomy-and-extraction.md`](../../06-taxonomy-and-extraction.md)
§3.1 for every other extracted attribute. It is stored in the existing
`listing.attr_confidence` JSONB under key `area_m2`
([`15-database-schema.md`](../../15-database-schema.md) §5) — no schema change.

Confidence is decided by *how* the value was recovered, never by how plausible it
looks:

- **`high`** — a supported unit token appears explicitly and adjacent to the number.
- **`low`** — the value was recovered through an ambiguous or lossy route: the bare
  `a` abbreviation, an approximation marker, an additive compound, a magnitude
  abbreviation, a dot resolved by D79's carve-out, or a value taken from the title.
- **`unknown`** — no value. Every failure row is `unknown`.

Inputs are given as **Python literals with explicit escapes**. The pass-1 table
printed U+00A0 and U+202F as literal characters, which are invisible in a diff and
get normalised away by editors — this is the form to type.

### 1.1 Square metres

`test_parse_area_exact[<case-id>]` asserts all four of `m2`, `unit`, `confidence`,
`failure is None`.

| Case id | Input (Python literal) | `m2` | `unit` | conf |
|---|---|---|---|---|
| `m2_plain` | `"1200 m²"` | `1200` | `m2` | high |
| `m2_thousands_space` | `"1 200 m²"` | `1200` | `m2` | high |
| `m2_thousands_nbsp` | `"1\u00a0200 m²"` | `1200` | `m2` | high |
| `m2_thousands_narrow_nbsp` | `"1\u202f200 m²"` | `1200` | `m2` | high |
| `m2_thousands_thin_space` | `"1\u2009200 m²"` | `1200` | `m2` | high |
| `m2_no_space` | `"1200m²"` | `1200` | `m2` | high |
| `m2_ascii_2` | `"1200 m2"` | `1200` | `m2` | high |
| `m2_ascii_caret` | `"1200 m^2"` | `1200` | `m2` | high |
| `m2_upper` | `"1200 M2"` | `1200` | `m2` | high |
| `m2_mkw` | `"1200 mkw"` | `1200` | `m2` | high |
| `m2_mkw_dotted` | `"1200 mkw."` | `1200` | `m2` | high |
| `m2_m_kw_dotted` | `"1200 m kw."` | `1200` | `m2` | high |
| `m2_words` | `"1200 metrów kwadratowych"` | `1200` | `m2` | high |
| `m2_words_no_diacritic` | `"1200 metrow kwadratowych"` | `1200` | `m2` | high |
| `m2_decimal_comma` | `"1 200,50 m²"` | `1200.50` | `m2` | high |
| `m2_decimal_comma_nbsp` | `"1\u00a0200,50 m²"` | `1200.50` | `m2` | high |
| `m2_decimal_comma_no_thousands` | `"1200,50 m²"` | `1200.50` | `m2` | high |
| `m2_trailing_zero_kept` | `"1200,00 m²"` | `1200.00` | `m2` | high |
| `m2_large_valid` | `"150 000 m²"` | `150000` | `m2` | high |
| `m2_two_groups_nbsp` | `"1\u00a0250\u00a0000 m²"` | `1250000` | `m2` | high |
| `m2_label_prefix` | `"Powierzchnia: 1200 m²"` | `1200` | `m2` | high |
| `m2_label_abbrev` | `"pow. 1 200 m²"` | `1200` | `m2` | high |
| `m2_with_price_in_string` | `"Sprzedam działkę 1200 m² za 250 000 zł"` | `1200` | `m2` | high |
| `m2_below_band` | `"250 m²"` | `250` | `m2` | high |
| `m2_at_lower_band` | `"300 m²"` | `300` | `m2` | high |

`m2_with_price_in_string` is not decoration. A parser that scans for the largest
number in the body returns `250000` here, and a 208× area error is the same defect
as F1 wearing a different hat.

`m2_trailing_zero_kept` pins that the `Decimal` is not normalised to `1200` — the
column is `NUMERIC(12,2)` and the scale is part of the value.

### 1.2 Ares

| Case id | Input | `m2` | `unit` | conf |
|---|---|---|---|---|
| `ar_arow` | `"12 arów"` | `1200` | `ar` | high |
| `ar_arow_no_diacritic` | `"12 arow"` | `1200` | `ar` | high |
| `ar_ary` | `"12 ary"` | `1200` | `ar` | high |
| `ar_ara` | `"1,5 ara"` | `150` | `ar` | high |
| `ar_singular` | `"1 ar"` | `100` | `ar` | high |
| `ar_dotted` | `"12 ar."` | `1200` | `ar` | high |
| `ar_decimal_comma` | `"12,5 ara"` | `1250` | `ar` | high |
| `ar_nbsp` | `"12\u00a0arów"` | `1200` | `ar` | high |
| `ar_upper` | `"12 ARÓW"` | `1200` | `ar` | high |
| `ar_fraction_small` | `"0,5 ara"` | `50` | `ar` | high |
| `ar_three_digit` | `"120 arów"` | `12000` | `ar` | high |

### 1.3 The `a` abbreviation — the ambiguous form

`a` alone is also the Polish conjunction *and/but*, so this form carries
confidence `low` even when it parses. **D86 fixes when it parses at all:** in a
structured field or a title always, in body text only within **40 characters** of
an area keyword (`powierzchnia`, `pow.`, `działka`, `grunt`).

| Case id | Input | Field | `m2` | `unit` | conf |
|---|---|---|---|---|---|
| `ar_abbrev_spaced` | `"12 a"` | structured | `1200` | `ar` | low |
| `ar_abbrev_glued` | `"12a"` | structured | `1200` | `ar` | low |
| `ar_abbrev_glued_decimal` | `"12,5a"` | structured | `1250` | `ar` | low |
| `ar_abbrev_title` | `"Działka 12a Radzymin"` | title | `1200` | `ar` | low |
| `ar_abbrev_body_near_keyword` | `"Ładna działka 12 a, media w drodze"` | body | `1200` | `ar` | low |
| `ar_abbrev_body_prose` | `"Dojazd 12 a nawet 15 minut do centrum"` | body | `None` | `None` | unknown |
| `ar_abbrev_body_far_from_keyword` | `"Powierzchnia opisana niżej. " + 60 chars + "12 a"` | body | `None` | `None` | unknown |

The last two rows carry the D86 rule from both sides. `ar_abbrev_body_prose` has
no area keyword at all. `ar_abbrev_body_far_from_keyword` has one, 60 characters
away, which is outside the 40-character window.

- `test_bare_a_window_is_exactly_forty_characters` — one input places the keyword
  40 characters before the number and parses; one places it 41 characters before
  and does not. The window is a named constant, `BARE_A_KEYWORD_WINDOW == 40`.
- `test_bare_a_keyword_list_is_the_decided_list` — the lexicon is exactly
  `powierzchnia`, `pow.`, `działka`, `grunt` (D86). Adding a keyword changes what
  parses and needs its own decision.

`parse_area` therefore takes the field it is parsing: `parse_area(text, field)` with
`field ∈ {"structured","title","body"}`. **This is a contract change from pass 1**,
and D86 settles it: without the field the parser cannot apply the rule.

- `test_parse_area_field_argument_is_required` — calling `parse_area(text)` without
  a field is a `TypeError`, not a defaulted `"body"`. A default here silently picks
  the most permissive reading for the least trustworthy text.

### 1.4 Hectares, and approximation markers

| Case id | Input | `m2` | `unit` | conf |
|---|---|---|---|---|
| `ha_decimal_comma` | `"0,12 ha"` | `1200` | `ha` | high |
| `ha_half` | `"0,5 ha"` | `5000` | `ha` | high |
| `ha_one_and_half` | `"1,5 ha"` | `15000` | `ha` | high |
| `ha_integer` | `"12 ha"` | `120000` | `ha` | high |
| `ha_one` | `"1 ha"` | `10000` | `ha` | high |
| `ha_word` | `"2 hektary"` | `20000` | `ha` | high |
| `ha_word_genitive` | `"5 hektarów"` | `50000` | `ha` | high |
| `ha_word_singular` | `"1 hektar"` | `10000` | `ha` | high |
| `ha_register_four_dp` | `"0,2500 ha"` | `2500` | `ha` | high |
| `ha_register_four_dp_large` | `"1,0374 ha"` | `10374` | `ha` | high |
| `ha_above_band` | `"25 ha"` | `250000` | `ha` | high |
| `ha_at_upper_band` | `"20 ha"` | `200000` | `ha` | high |
| `approx_ok_m2` | `"ok. 1200 m²"` | `1200` | `m2` | low |
| `approx_okolo_ar` | `"około 12 arów"` | `1200` | `ar` | low |
| `approx_tilde` | `"~1200 m²"` | `1200` | `m2` | low |
| `approx_ca` | `"ca 0,12 ha"` | `1200` | `ha` | low |

Every `approx_*` row also asserts `is_approximate is True`; every other row in §1
asserts `is_approximate is False`, which is the half a reviewer forgets.

D83 requires more than the parse. The marker must reach the interface:

- `test_is_approximate_survives_normalization` — the `NormalizedListing` built from
  `approx_ok_m2` carries `is_approximate is True`.
- `test_is_approximate_reaches_the_render_tree` — the record the app renders
  carries the marker, so the reader sees that the area is the seller's estimate
  and not a measured figure. An approximate area is never displayed bare (rule 7).

`ha_register_four_dp` matters more than it looks: the parcel register states area in
hectares to four decimal places, so this is the *register* branch's own format, and
it is the input to §3's authority resolution.

### 1.5 Separator and range forms — settled

**The dot (D79).** A dot in an area string quarantines the record. The single
carve-out is a dot followed by **exactly four digits** with the unit `ha`. That is
the parcel register's own format, and it has one reading. Everything else has two
readings 1000× apart, so ambiguity loses.

| Case id | Input | `m2` | `unit` | conf | `failure` |
|---|---|---|---|---|---|
| `dot_1200_m2` | `"1.200 m²"` | `None` | `None` | unknown | `AMBIGUOUS_SEPARATOR` |
| `dot_0_12_ha` | `"0.12 ha"` | `None` | `None` | unknown | `AMBIGUOUS_SEPARATOR` |
| `dot_12_5_ara` | `"12.5 ara"` | `None` | `None` | unknown | `AMBIGUOUS_SEPARATOR` |
| `dot_1_250_000_m2` | `"1.250.000 m²"` | `None` | `None` | unknown | `AMBIGUOUS_SEPARATOR` |
| `dot_1_2500_ha` | `"1.2500 ha"` | `12500` | `ha` | low | — |
| `dot_0_2500_ha` | `"0.2500 ha"` | `2500` | `ha` | low | — |
| `dot_three_digit_ha` | `"1.250 ha"` | `None` | `None` | unknown | `AMBIGUOUS_SEPARATOR` |
| `dot_five_digit_ha` | `"1.25000 ha"` | `None` | `None` | unknown | `AMBIGUOUS_SEPARATOR` |
| `dot_four_digit_m2` | `"1.2500 m²"` | `None` | `None` | unknown | `AMBIGUOUS_SEPARATOR` |

The last three rows pin both edges of the carve-out. Three digits fail, five
digits fail, and four digits with a unit other than `ha` fail. A carve-out written
loosely swallows the whole ambiguous class it was carved out of.

- `test_dot_carve_out_requires_four_digits_and_ha` — asserts the three edge rows
  together, so a widened carve-out fails in one place.
- `test_dot_carve_out_confidence_is_low` — `"1.2500 ha"` parses at `low`, never
  `high`. The route is a carve-out, not an explicit unambiguous token.

**The range (D82).** An area range is not single-valued. The record is
quarantined. A midpoint invents a number nobody wrote, and a lower bound reports a
plot smaller than the one on sale.

| Case id | Input | `m2` | conf | `failure` |
|---|---|---|---|---|
| `range_hyphen` | `"1200-1500 m²"` | `None` | unknown | `NOT_SINGLE_VALUED` |
| `range_en_dash` | `"1200–1500 m²"` | `None` | unknown | `NOT_SINGLE_VALUED` |
| `range_words` | `"od 1200 do 1500 m²"` | `None` | unknown | `NOT_SINGLE_VALUED` |
| `range_od` | `"od 1200 m²"` | `None` | unknown | `NOT_SINGLE_VALUED` |

`range_hyphen` has a trap worth a comment in the test file: `"1200-1500"` reads as
a range to a human and as two numbers to a regex. The parser must never return
`1200` *and* `1500` as two separate parses of one field.

- `test_range_returns_one_failure_not_two_values` — asserts a single `AreaParse`
  with `NOT_SINGLE_VALUED`, not a list.

### 1.6 Compound and restated forms — settled by D90

D90 fixes three rules, and they are three different rules:

1. **A compound sums.** `"1 ha 25 a"` is 10 000 + 2 500 = 12 500 m².
2. **An agreeing restatement keeps full confidence.** Two statements of one area
   that match are corroboration, not ambiguity, so confidence stays `high`.
3. **A disagreeing restatement quarantines.**

| Case id | Input | `m2` | `unit` | conf |
|---|---|---|---|---|
| `compound_ha_ar` | `"1 ha 25 a"` | `12500` | `ha` | low |
| `compound_ha_ar_m2` | `"1 ha 25 a 30 m²"` | `12530` | `ha` | low |
| `compound_ar_m2` | `"12 a 30 m²"` | `1230` | `ar` | low |
| `restated_agreeing` | `"1200 m² (12 arów)"` | `1200` | `m2` | high |
| `restated_agreeing_reverse` | `"12 arów (1200 m²)"` | `1200` | `ar` | high |
| `restated_disagreeing` | `"1200 m² (15 arów)"` | fail `CONFLICTING_STATEMENTS` | — | unknown |
| `restated_disagreeing_100x` | `"1200 m² (12 ha)"` | fail `CONFLICTING_STATEMENTS` | — | unknown |

**D90 supersedes the first answer, which took the first value.** Under that rule
`"1 ha 25 a"` read as 10 000 m². The area was 20% low and every zł/m² figure taken
from it was 25% high. The sum is the arithmetic the register itself uses.

- `test_compound_sums_rather_than_taking_the_first_value` — `"1 ha 25 a"` asserts
  `Decimal("12500")` and, in the same test, asserts the value is **not**
  `Decimal("10000")`. The superseded reading is named so it cannot come back
  quietly.
- `test_compound_unit_is_the_largest_unit_present` — `unit == "ha"` for
  `compound_ha_ar`. The unit records how the advert stated the area; `m2` carries
  the value.
- `test_agreeing_restatement_keeps_high_confidence` — `restated_agreeing` asserts
  `confidence == "high"`. A restatement that agrees is evidence, so it must not be
  demoted to `low` alongside the compound rows.

**A compound and a restatement must not be confused.** `"1 ha 25 a"` sums to
12 500 m². `"1200 m² (12 arów)"` is one area stated twice and equals 1200 m², not
2400 m².

- `test_restatement_is_not_summed` — `restated_agreeing` asserts `1200`, never
  `2400`. This is the mirror of the test above and kills the mutant that sums
  every multi-unit string.

`restated_disagreeing_100x` is the F1 signature seen inside a single field. It must
never resolve to either value by preference order — the field disagrees with itself
and there is no authority to break the tie.

### 1.7 Text that must **not** parse

`test_parse_area_failure[<case-id>]` asserts `m2 is None`, `unit is None`,
`confidence == "unknown"` and the exact failure member.

| Case id | Input | `failure` |
|---|---|---|
| `bare_number` | `"1200"` | `NO_UNIT` |
| `bare_decimal` | `"1200,50"` | `NO_UNIT` |
| `empty` | `""` | `ABSENT` |
| `whitespace` | `"   "` | `ABSENT` |
| `nbsp_only` | `"\u00a0\u00a0"` | `ABSENT` |
| `em_dash` | `"—"` | `ABSENT` |
| `hyphen` | `"-"` | `ABSENT` |
| `brak_danych` | `"brak danych"` | `ABSENT` |
| `nie_podano` | `"nie podano"` | `ABSENT` |
| `unit_without_number` | `"m²"` | `NO_VALUE` |
| `unit_without_number_ar` | `"arów"` | `NO_VALUE` |
| `unknown_unit_morgi` | `"12 morgów"` | `UNKNOWN_UNIT` |
| `unknown_unit_morg` | `"12 mórg"` | `UNKNOWN_UNIT` |
| `unknown_unit_akr` | `"3 akry"` | `UNKNOWN_UNIT` |
| `unknown_unit_sqft` | `"12000 sq ft"` | `UNKNOWN_UNIT` |
| `zero_m2` | `"0 m²"` | `NON_POSITIVE` |
| `zero_ha` | `"0,00 ha"` | `NON_POSITIVE` |
| `negative_m2` | `"-500 m²"` | `NON_POSITIVE` |
| `price_only` | `"250 000 zł"` | `ABSENT` |
| `price_per_m2_only` | `"200 zł/m²"` | `ABSENT` |
| `phone_number` | `"tel. 601 200 300"` | `ABSENT` |
| `phone_number_grouped` | `"kontakt: 601-200-300"` | `ABSENT` |
| `postcode` | `"05-200 Wołomin"` | `ABSENT` |
| `year` | `"rok budowy 1998"` | `ABSENT` |
| `rooms` | `"3 pokoje"` | `ABSENT` |
| `distance_km` | `"1200 m od jeziora"` | `ABSENT` |
| `plot_number` | `"działka nr 1200/3"` | `ABSENT` |
| `price_placeholder_in_area_field` | `"Zapytaj o cenę"` | `ABSENT` |
| `category_text` | `"działka budowlana"` | `ABSENT` |
| `html_entity_noise` | `"&nbsp;"` | `ABSENT` |

Two of these carry the real weight:

- **`price_per_m2_only`** — `"200 zł/m²"` contains the token `m²`. A unit-token
  search finds it and returns `200 m²`, and the resulting listing looks entirely
  ordinary. The `zł/` prefix must veto the match.
- **`distance_km`** — `"1200 m od jeziora"` contains `m` followed by a space. If
  the `m²` pattern is written loosely enough to accept `"1200 m"`, every
  distance-to-something phrase in every body becomes an area.
- **`plot_number`** — `1200/3` is a parcel identifier, not `400 m²`.

The failure-to-reason mapping is §6.

### 1.8 Named tests beyond the table

| Test | Asserts |
|---|---|
| `test_parse_area_returns_decimal_not_float` | `isinstance(r.m2, Decimal)` for every §1.1–1.6 row — parametrised over the same table, so a new row gets the check free |
| `test_ar_and_ha_multipliers_are_exactly_100_and_10000` | `AR_IN_M2 == Decimal("100")`, `HA_IN_M2 == Decimal("10000")` |
| `test_parse_area_never_returns_a_value_with_a_failure` | for every row: exactly one of `m2` and `failure` is `None` — the states cannot both be populated |
| `test_confidence_is_unknown_iff_parse_failed` | `(r.confidence == "unknown") == (r.m2 is None)` over the whole table |
| `test_no_case_id_is_duplicated` | the parametrisation ids are unique — a duplicated id silently drops a case from the run |
| `test_every_supported_unit_token_has_a_case` | every token in `UNIT_LEXICON` appears in at least one §1.1–1.4 row; adding a token without a case fails |
| `test_every_unknown_unit_token_has_a_case` | same for `UNSUPPORTED_UNIT_LEXICON` (morga, akr, sq ft …) |

The last two are the guard against the table going stale: the lexicon and the test
table are kept in sync mechanically rather than by review.

---

## 2. `parse_price` — the complete parametrised table

`test_parse_price_exact[<case-id>]` asserts `pln`, `confidence`, `failure is None`.

| Case id | Input | `pln` | conf |
|---|---|---|---|
| `plain_zl` | `"250 000 zł"` | `250000` | high |
| `nbsp_zl` | `"250\u00a0000 zł"` | `250000` | high |
| `narrow_nbsp_zl` | `"250\u202f000 zł"` | `250000` | high |
| `zl_no_diacritic` | `"250 000 zl"` | `250000` | high |
| `pln_suffix` | `"1 250 000 PLN"` | `1250000` | high |
| `pln_lower` | `"1 250 000 pln"` | `1250000` | high |
| `grosze` | `"250 000,50 zł"` | `250000.50` | high |
| `grosze_dot` | `"250 000.50 zł"` | `250000.50` | high |
| `no_currency` | `"250000"` | `250000` | low |
| `negotiable_suffix` | `"250 000 zł do negocjacji"` | `250000` | high |
| `negotiable_abbrev` | `"250 000 zł (do neg.)"` | `250000` | high |
| `label_prefix` | `"Cena: 250 000 zł"` | `250000` | high |
| `glued` | `"250000zł"` | `250000` | high |
| `tys` | `"250 tys. zł"` | `250000` | low |
| `tys_no_dot` | `"250 tys zł"` | `250000` | low |
| `mln` | `"1,2 mln zł"` | `1200000` | low |
| `mln_word` | `"1,2 miliona zł"` | `1200000` | low |

D80 parses the magnitude abbreviations at confidence `low`. They are frequent and
unambiguous, and quarantining them drops a whole segment of the corpus (F12).

- `test_magnitude_multipliers_are_named_constants` — `TYS_MULTIPLIER ==
  Decimal("1000")`, `MLN_MULTIPLIER == Decimal("1000000")`.
- `test_magnitude_abbreviation_is_never_high_confidence` — every `tys`/`mln` row
  parses at `low`. The multiplier is inferred from an abbreviation, not read from
  the digits.

`no_currency` is confidence `low` deliberately: a bare number in a price field is
almost certainly PLN and there is no other plausible currency in this corpus, but
"almost certainly" is `low`, not `high`. Contrast `bare_number` in §1.7, which
**fails** — because there a bare number has two readings 100× apart, and here it
has one.

`grosze_dot` accepts a dot as the decimal separator for prices even though D79
treats a dot in an *area* as ambiguous. The asymmetry is intentional and tested:

- `test_price_dot_and_area_dot_are_treated_differently` — documents that a price is
  bounded by the currency's two decimal places (`250 000.50` has exactly one
  reading), while `"1.200 m²"` has two readings 1000× apart.

### 2.1 Prices that must not parse

| Case id | Input | `failure` |
|---|---|---|
| `placeholder_ask` | `"Zapytaj o cenę"` | `PLACEHOLDER` |
| `placeholder_ask_lower` | `"zapytaj o cenę"` | `PLACEHOLDER` |
| `placeholder_ask_no_diacritic` | `"zapytaj o cene"` | `PLACEHOLDER` |
| `placeholder_agree` | `"cena do uzgodnienia"` | `PLACEHOLDER` |
| `placeholder_negotiate` | `"do negocjacji"` | `PLACEHOLDER` |
| `placeholder_contact` | `"kontakt w sprawie ceny"` | `PLACEHOLDER` |
| `placeholder_dash` | `"—"` | `ABSENT` |
| `empty` | `""` | `ABSENT` |
| `whitespace` | `"    "` | `ABSENT` |
| `zero` | `"0 zł"` | `NON_POSITIVE` |
| `zero_decimal` | `"0,00 zł"` | `NON_POSITIVE` |
| `negative` | `"-1000 zł"` | `NON_POSITIVE` |
| `per_m2_only` | `"200 zł/m²"` | `NOT_A_TOTAL` |
| `per_m2_only_words` | `"200 zł za m²"` | `NOT_A_TOTAL` |
| `rent` | `"2 500 zł/mies."` | `NOT_A_TOTAL` |
| `foreign_currency` | `"60 000 EUR"` | `UNSUPPORTED_CURRENCY` |
| `text_only` | `"okazja!"` | `ABSENT` |

`per_m2_only` gets its own failure member rather than sharing `ABSENT`: a per-m²
figure in the total-price field is a *layout* defect in the connector, and V50's
per-reason rates must be able to show it spiking on one source without the
`ABSENT` count moving. `rent` is the same defect with a worse outcome — a monthly
rent stored as a sale price is a plausible-looking number.

`foreign_currency` is not converted. A conversion needs an FX rate with an as-of
date (rule 7), which v0 does not carry.

---

## 3. Authority order — every pair that can disagree

`resolve_area(register, structured, body, title)` →
`ResolvedArea(m2, source, conflict, candidates)`.

**`candidates` is a contract addition from pass 1.** §4.3 there requires that "the
advert value is retained on the record, not discarded"; a `conflict: bool` cannot
carry it. `candidates` is the full `{source: m2 | None}` mapping, stored on the
listing so the plot page can render *"ogłoszenie: 1200 m² · rejestr: 1450 m²"* the
way `06` §1 renders the zoning disagreement.

Most values below differ by far more than the 5% D81 fixed, so the winner and the
`conflict` flag are both unambiguous. Two rows sit inside 5% and are marked; their
expected `conflict` is **False**, recomputed against D81.

### 3.1 Every ordered pair

| Test | register | structured | body | title | winner | `source` | `conflict` |
|---|---|---|---|---|---|---|---|
| `test_register_beats_structured` | `1450` | `1200` | — | — | `1450` | `register` | True |
| `test_register_beats_body` | `1450` | — | `1200` | — | `1450` | `register` | True |
| `test_register_beats_title` | `1450` | — | — | `1200` | `1450` | `register` | True |
| `test_structured_beats_body` | — | `1200` | `1150` | — | `1200` | `structured` | **False** — 4.17%, inside the 5% threshold (D81) |
| `test_structured_beats_body_conflicting` | — | `1200` | `1100` | — | `1200` | `structured` | True — 8.33% |
| `test_structured_beats_title` | — | `1200` | — | `1000` | `1200` | `structured` | True |
| `test_body_beats_title` | — | — | `1150` | `1000` | `1150` | `body` | True |
| `test_all_four_disagree` | `1450` | `1200` | `1150` | `1000` | `1450` | `register` | True |
| `test_all_four_agree` | `1200` | `1200` | `1200` | `1200` | `1200` | `register` | False |
| `test_register_only` | `1450` | — | — | — | `1450` | `register` | False |
| `test_structured_only` | — | `1200` | — | — | `1200` | `structured` | False |
| `test_body_only` | — | — | `1150` | — | `1150` | `body` | False |
| `test_title_only` | — | — | — | `1000` | `1000` | `title` | False |
| `test_none_present` | — | — | — | — | — | — | raises → `AREA_MISSING` |
| `test_lower_sources_agree_against_register` | `1450` | `1200` | `1200` | `1200` | `1450` | `register` | True |
| `test_precision_is_not_authority` | `1450` | `1449.87` | — | — | `1450` | `register` | **False** — 0.009%, far inside 5% (D81) |
| `test_gap_between_present_sources` | `1450` | — | — | `1000` | `1450` | `register` | True |

`test_lower_sources_agree_against_register` is the row a majority-vote
implementation fails. Three sources say 1200 and one says 1450; the register still
wins, because FR-15 is an authority rule and not a vote.

`test_precision_is_not_authority` splits into two assertions. The **winner** is
`1450` from `register`, because precision is not authority. The **`conflict`
flag** is `False`: 0.009% is far inside the 5% threshold, so a register value and
a more precise advert value that agree do not raise a flag (D81).

`test_structured_beats_body` and `test_structured_beats_body_conflicting` are a
pair on purpose. The winner is `structured` in both. Only the flag differs, and it
differs because of the threshold alone.

### 3.2 Threshold boundary — 5% (D81)

**The threshold is more than 5%.** D81 chose it over the 2% I proposed. The
boundary rows below are recomputed: 2% of 1200 is 24 m², 5% of 1200 is 60 m², so
the edge moves from 1224 to 1260.

The relative difference divides by the **register area**, the authoritative value.
Every row states register `1200`.

| Case | structured | relative Δ | `conflict` |
|---|---|---|---|
| `well_inside` | `1210.00` | 0.83% | False |
| `just_inside` | `1259.99` | 4.9992% | False |
| `on_the_boundary` | `1260.00` | exactly 5% | False — inclusive |
| `just_outside` | `1260.01` | 5.0008% | True |
| `well_outside` | `1450.00` | 20.8% | True |
| `exactly_equal` | `1200.00` | 0% | False |
| `rounding_only` | `1199.99` | 0.0008% | False |
| `below_by_more_than_five` | `1139.99` | 5.0008% | True |

`below_by_more_than_five` is new. It checks the low side of the band. A threshold
written as `(advert - register) / register > 0.05` passes every row above it and
never flags an advert that understates the area.

- `test_conflict_threshold_is_relative_not_absolute` — a 60 m² gap on a 1 200 m²
  plot flags; the same 60 m² gap on a 200 000 m² plot does not. An absolute
  threshold makes every hectare-scale plot conflict.
- `test_conflict_threshold_is_five_percent_not_two` — asserts
  `CONFLICT_THRESHOLD == Decimal("0.05")` **and** that structured `1224.00`
  (exactly 2%) gives `conflict is False`. The superseded value is named so a
  constant copied from an old draft fails at once.
- `test_conflict_threshold_is_symmetric` — the check does not depend on argument
  order. It uses `1200` against `1450` (both directions clear the threshold) and
  `1200` against `1230` (both directions stay inside it), so the assertion holds
  whichever value the implementation divides by.

**The cost of 5%, recorded.** A real register-versus-advert mismatch below 5%
passes unflagged. On a 1 200 m² plot that is a silent gap of up to 60 m², about
5% of the price per m². The register value still wins the resolution (§3.1), so
the stored area is right; only the `conflict` flag is absent, and with it the
"ogłoszenie: … · rejestr: …" line the plot page would otherwise show.

### 3.3 What the resolution records

| Test | Asserts |
|---|---|
| `test_candidates_retains_every_stated_value` | `candidates == {"register": Decimal("1450"), "structured": Decimal("1200"), "body": None, "title": None}` — the loser survives verbatim |
| `test_area_source_is_a_member_of_the_check_constraint` | `source in {"register","structured","body","title"}`, matching the DDL `CHECK` |
| `test_resolution_never_averages` | for every §3.1 row, the winner equals one of the inputs exactly — no derived value |
| `test_conflict_does_not_quarantine` | a conflicting record is a `NormalizedListing`, flagged, not a `QuarantinedRecord` |
| `test_unparseable_source_is_skipped_not_fatal` | body text `"12 morgów"` with a valid structured `1200` → `1200` from `structured`, and the body failure recorded in `candidates["body"] is None` |
| `test_confidence_of_the_winner_is_carried` | a `low`-confidence title value that wins because nothing else exists keeps `confidence == "low"` on the listing |

---

## 4. Bands — flag and keep visible, never quarantine

Band: area `[300, 200 000]` m², price_per_m2 `[1, 100 000]` PLN/m², **inclusive**
both ends (FR-12 as amended by O12).

`price_per_m2` is never computed by the normalizer — it is the generated column.
`band_flags` is therefore given the quotient by its caller and the tests supply it
directly, which is also what makes the arithmetic below exact rather than
floating.

### 4.1 Area boundary

| Row | `area_m2` | `price_pln` | `price_per_m2` | expected flags | record type |
|---|---|---|---|---|---|
| B1 | `299.99` | `59998.00` | `200.00` | `AREA_BELOW_BAND` | Normalized |
| B2 | `300.00` | `60000.00` | `200.00` | ∅ | Normalized |
| B3 | `300.01` | `60002.00` | `200.00` | ∅ | Normalized |
| B4 | `199999.99` | `599999.97` | `3.00` | ∅ | Normalized |
| B5 | `200000.00` | `600000.00` | `3.00` | ∅ | Normalized |
| B6 | `200000.01` | `600000.03` | `3.00` | `AREA_ABOVE_BAND` | Normalized |

### 4.2 Price boundary

| Row | `area_m2` | `price_pln` | `price_per_m2` | expected flags | record type |
|---|---|---|---|---|---|
| B7a | `1000.00` | `990.00` | `0.99` | `PRICE_BELOW_BAND` | Normalized |
| B7b | `1000.00` | `1000.00` | `1.00` | ∅ | Normalized |
| B7c | `1000.00` | `1010.00` | `1.01` | ∅ | Normalized |
| B8a | `1000.00` | `99999990.00` | `99999.99` | ∅ | Normalized |
| B8b | `1000.00` | `100000000.00` | `100000.00` | ∅ | Normalized |
| B8c | `1000.00` | `100000010.00` | `100000.01` | `PRICE_ABOVE_BAND` | Normalized |

### 4.3 The cases the band exists for

| Row | Description | Input | Expected |
|---|---|---|---|
| B9 | The O12 case — 25 ha farmland at 3 zł/m² | area `250000.00`, price `750000.00` | `AREA_ABOVE_BAND`; `NormalizedListing`; appears in emitted rows; **in the corpus and on the plot page, excluded from every aggregate** (D85) |
| B10 | Small plot below the band | area `250.00`, price `100000.00`, `400.00`/m² | `AREA_BELOW_BAND`; visible; excluded from aggregates (D85) |
| B11 | Both edges violated at once | area `200000.01`, price `100000.00`, `0.50`/m² | `{AREA_ABOVE_BAND, PRICE_BELOW_BAND}` — a `frozenset` of two, not the first one found |
| B12 | Rounding at the price edge | area `3.00`, price `300000.01` → exact `100000.00333…`, stored `100000.00` | `PRICE_ABOVE_BAND` on the **exact quotient** (D88), even though the displayed figure sits on the edge |
| B13 | Zero-area guard | area `0` | never reaches `band_flags` — quarantined upstream as `area_non_positive`; `band_flags` raises on non-positive area rather than dividing |

**D85 — out of band means visible, not counted.**

| Test | Asserts |
|---|---|
| `test_out_of_band_record_is_excluded_from_aggregates` | a corpus of 10 in-band records plus B9 → the gmina aggregate's `n == 10`, and its median equals the median of the 10 |
| `test_out_of_band_record_is_in_the_corpus_count` | the same corpus reports 11 records, so the exclusion is visible as a difference, not as a silent loss |
| `test_out_of_band_record_renders_on_the_plot_page` | B9 renders with its flag (rule 7) |
| `test_out_of_band_record_participates_in_dedup` | B9 and an identical second source collapse into one cluster; exclusion happens at the aggregate, not at the cluster |
| `test_adding_an_out_of_band_record_leaves_the_estimate_unchanged` | the V47 construction: adding B9 to a corpus leaves the median and the `n` identical |

**D88 — the band check reads the exact quotient.**

| Test | Asserts |
|---|---|
| `test_band_check_reads_the_exact_quotient` | B12 → `PRICE_ABOVE_BAND`. `Decimal("300000.01") / Decimal("3.00")` is `100000.00333…`, which is above the edge |
| `test_band_check_does_not_read_the_rounded_value` | the same input quantised to `NUMERIC(12,2)` gives `100000.00`, which is **in** band. The test asserts the flag is set anyway, so an implementation that reads the stored column fails |
| `test_band_check_at_the_area_edge_uses_the_stated_area` | area is stored exactly, so no quotient is involved; B2 and B5 remain the area-edge cases |

### 4.4 The flag-not-quarantine assertions

| Test | Asserts |
|---|---|
| `test_band_constants_match_amended_fr12` | `AREA_BAND == (Decimal("300"), Decimal("200000"))`; `PRICE_PER_M2_BAND == (Decimal("1"), Decimal("100000"))` |
| `test_superseded_band_values_are_not_in_band_constants` | `Decimal("100")` and `Decimal("500000")` are not the area edges — fails loudly if V10's stale prose is copied |
| `test_out_of_band_record_is_flagged_not_dropped_and_not_quarantined` | B9 → `isinstance(result, NormalizedListing)`; `not isinstance(result, QuarantinedRecord)` |
| `test_out_of_band_record_is_in_the_emitted_rows` | B9's id is in the run's emitted set — "not quarantined" and "actually emitted" are different claims |
| `test_out_of_band_record_carries_its_flag_to_the_surface` | the flag survives into the render tree the app consumes |
| `test_band_flags_returns_a_frozenset` | B11 returns both members; the return type is `frozenset`, so a caller cannot mutate it into agreement |
| `test_no_band_flag_implies_empty_frozenset` | B2 returns `frozenset()`, not `None` — a `None` return makes `if flags:` and `if flags is not None:` disagree |
| `test_band_check_is_inclusive_at_all_four_edges` | B2, B5, B7b, B8b together, asserted as one statement, killing a `<` → `<=` mutant at any edge |
| `test_quarantine_and_flag_sets_are_disjoint` | over the whole fixture corpus: no record is both flagged and quarantined |

**The V10 errata still stands.** `04-validation.md` V10 has since been corrected to
300–200 000 in its AC and its boundary prose; `test_superseded_band_values_…`
remains, because the stale figures are still quoted in `docs/17-assumption-audit.md`
and in this repository's history.

### 4.5 Low confidence enters the aggregates, flagged (D87)

A `low`-confidence area is a real observation recovered by a lossy route. D87
keeps it in the aggregates and flags it, exactly as rule 7 treats a thin `n`.
Three separate states must not be confused:

| State | In the aggregate? | Visible? | Rule |
|---|---|---|---|
| Quarantined — no usable price or area | No | In the quarantine report | §6 |
| Out of band — usable, outside the validity band | **No** | Yes, flagged | D85 |
| Low confidence — usable, recovered by a lossy route | **Yes** | Yes, flagged | D87 |

| Test | Setup | Asserts |
|---|---|---|
| `test_low_confidence_area_enters_the_aggregate` | 9 `high`-confidence records plus one `low` from `approx_ok_m2` | `n == 10` |
| `test_low_confidence_area_carries_its_flag_to_the_surface` | the same record | the rendered row shows the confidence flag; the figure is never displayed bare |
| `test_low_confidence_is_not_out_of_band` | one `low` record inside the band | no band flag, and the record is in the aggregate — the two flags are independent |
| `test_every_low_confidence_route_is_represented` | one record per `low` route — D80 magnitude, D83 approximate, D86 bare `a`, D90 compound, D79 dot carve-out, title-sourced | all six enter the aggregate and all six carry the flag |

`test_every_low_confidence_route_is_represented` is the guard against a partial
implementation. Five of the six routes are easy to remember and the sixth is the
one that ships unflagged.

---

## 5. Dedup — the concrete rows

All rows share `price_type = 'offering'`, `price_kind = 'asking'` unless stated.
`gm-A` = TERYT `1434032`, `gm-B` = TERYT `1465011`. Sources: `s1` = otodom,
`s2` = olx, `s3` = agency feed.

### 5.1 Rows that must merge

| id | src | external_id | `area_m2` | `price_pln` | teryt | asset_class | zoning_claim | seller hash | `first_seen_at` |
|---|---|---|---|---|---|---|---|---|---|
| D1 | s1 | `OD-4471` | `1234.00` | `247000.00` | gm-A | land_building | działka budowlana | `h:aa1` | 2026-03-02 |
| D1′ | s1 | `OD-4471` | `1234.00` | `247000.00` | gm-A | land_building | działka budowlana | `h:aa1` | 2026-03-09 (re-ingest) |
| D2 | s2 | `OL-88231` | `1234.00` | `247000.00` | gm-A | land_building | działka budowlana | `h:bb2` | 2026-03-04 |
| D3 | s3 | `AG-0071` | `1234.00` | `247000.00` | gm-A | land_building | działka budowlana | `h:aa1` | 2026-03-06 |

| Test | Expected |
|---|---|
| `test_same_source_same_external_id_is_one_listing` | D1 + D1′ → **one** `listing` row (upsert on `UNIQUE (source_id, external_id)`), `last_seen_at` advanced to 2026-03-09, `first_seen_at` unchanged, one `listing_snapshot` per observation |
| `test_cross_source_exact_key_collapses` | D1 + D2 → **one** cluster, `duplicate_count == 2`, both listings carry its `plot_cluster_id` |
| `test_duplicate_count_reflects_cluster_size` | D1 + D2 + D3 → one cluster, `duplicate_count == 3` |
| `test_singleton_gets_duplicate_count_one` | D1 alone → one cluster, `duplicate_count == 1` |
| `test_n_before_and_after_dedup_are_both_reported` | D1, D2, D3 + 7 unrelated singletons → `n_before == 10`, `n_after == 8`, both on `DedupResult` |

`1234.00 m² / 247 000.00 zł` is deliberately **not** round. These rows share all
four fields of the D78 key — area, price, gmina and `asset_class` — so they merge.
The test name says *key*, not *triple*: D78 made the key a quadruple.

### 5.2 Canonical selection (D84)

The order is settled: **earliest `first_seen_at`, then lowest `source_id`, then
lowest `external_id`.** It is a total order, so the result does not change when
the input is permuted. The canonical of {D1, D2, D3} is **D1**.

| Test | Setup | Expected |
|---|---|---|
| `test_canonical_record_selection_is_deterministic` | all 6 permutations of D1, D2, D3 | canonical is D1 in all six |
| `test_canonical_tie_broken_by_source_then_external_id` | D2 and D3 given identical `first_seen_at` 2026-03-04 | canonical is D2 (`s2 < s3`) |
| `test_canonical_tie_broken_by_external_id_last` | two rows, same date, same source, ids `AG-0071` / `AG-0072` | canonical is `AG-0071` |
| `test_canonical_selection_is_a_total_order` | generated clusters (property-based) | the comparator is irreflexive, antisymmetric and transitive — a partial order re-introduces order dependence |
| `test_canonical_key_is_the_three_named_fields_in_order` | — | the sort key is `(first_seen_at, source_id, external_id)` (D84). A "richest record" rule is not the decision and fails this test |

### 5.3 The match key, and the false merge it accepts (D78)

**The key is `(area_m2, price_pln, teryt_gmina, asset_class)`.** Four fields, no
more. `zoning_claim` is not in it. `seller_contact_hash` is not in it. There is no
round-number guard.

The rows below are two genuinely different plots, both `1000.00 m²` at
`100 000.00 zł`, both in gm-B. This is the collision the pass-1 spec flagged,
given concretely.

| id | src | external_id | `area_m2` | `price_pln` | teryt | asset_class | zoning_claim | locality | seller hash | first_seen |
|---|---|---|---|---|---|---|---|---|---|---|
| R1 | s1 | `OD-5510` | `1000.00` | `100000.00` | gm-B | land_building | działka budowlana | Kąty Węgierskie | `h:cc3` | 2026-04-11 |
| R2 | s2 | `OL-77004` | `1000.00` | `100000.00` | gm-B | land_agricultural | działka rolna | Stanisławów | `h:dd4` | 2026-05-19 |
| R3 | s1 | `OD-6120` | `1000.00` | `100000.00` | gm-B | land_building | działka budowlana | Nadma | `NULL` | 2026-04-14 |
| R4 | s2 | `OL-81992` | `1000.00` | `100000.00` | gm-B | land_building | działka budowlana | Słupno | `NULL` | 2026-06-02 |
| R5 | s1 | `OD-6301` | `1000.00` | `100000.00` | gm-B | land_building | działka budowlana | Nadma | `h:ee5` | 2026-04-20 |
| R6 | s2 | `OL-83110` | `1000.00` | `100000.00` | gm-B | land_building | działka budowlana | Nadma | `h:ee5` | 2026-04-22 |

What the decided key does with each pair:

**Each test below feeds only the rows it names.** R3, R4, R5 and R6 share all four
key fields, so a run given all four returns one cluster of four. The pairs are
separate fixture sets, and `test_round_rows_given_together_form_one_cluster`
asserts that outcome so the effect is written down rather than discovered.

| Pair | Truth | Key result | Verdict |
|---|---|---|---|
| R1/R2 | different plots | 2 clusters — `asset_class` differs | Correct |
| R3/R4 | different plots | **1 cluster** — every key field is identical | **Wrong, and accepted** |
| R5/R6 | same plot, two agencies | 1 cluster | Correct |
| R3+R4+R5+R6 | three plots | **1 cluster of four** | The same error at scale |
| D1/D2 (§5.1) | same plot | 1 cluster | Correct |

**The residual risk D78 accepts, stated plainly.** R3 and R4 are two different
building plots in Nadma and Słupno. They share an area, a price, a gmina and an
asset class. v0 merges them. The corpus then holds one observation where the truth
is two, and reports `duplicate_count == 2` where the truth is two separate plots.
Round areas and round prices are common in this market, so this is not a rare
shape. **V56's false-merge monitoring is the only detector.**

I proposed a round-number guard — a merge on a round pair would have required an
equal, non-null `seller_contact_hash`. The owner rejected it and took the simpler
key with the named cost. That guard is **not** in the plan. No test refers to it.

| Test | Expected |
|---|---|
| `test_match_key_is_exactly_the_four_named_fields` | the key tuple is `(area_m2, price_pln, teryt_gmina, asset_class)`, in that order |
| `test_differing_asset_class_never_merges` | R1, R2 → 2 clusters, `duplicate_count == 1` each — this is the field D78 added |
| `test_same_plot_two_agencies_merges` | R5, R6 → 1 cluster, `duplicate_count == 2` |
| `test_identical_round_pair_merges_and_is_a_known_false_merge` | R3, R4 → **1 cluster**, `duplicate_count == 2` |
| `test_round_rows_given_together_form_one_cluster` | R3, R4, R5, R6 → **1 cluster**, `duplicate_count == 4`, where the truth is three plots |
| `test_seller_contact_hash_is_not_in_the_match_key` | R5 and R6 merge, and so would the same pair with null hashes. A hash added to the key changes these results and fails here |
| `test_zoning_claim_is_not_in_the_match_key` | two records identical on the four key fields but with different `zoning_claim` strings still merge |
| `test_run_report_states_the_accepted_false_merge_risk` | the run report and the coverage page carry the caveat: round pairs can merge, and the residual false-merge rate is **unknown, not measured** |

`test_identical_round_pair_merges_and_is_a_known_false_merge` carries this comment
verbatim in the test file:

> This asserts a **known false merge**, not a success. R3 and R4 are two different
> plots. D78 chose the four-field key and accepted this cost: two building plots
> of 1000 m² at 100 000 zł in one gmina merge. A future FR-13 matcher flips this
> test deliberately, in the same commit that adds the labelled set.

R3/R4 are identical in every structured field and distinguishable only by a
locality string the v0 key does not carry. This is the case V56 names as
falsifying — *a near-duplicate being merged; v0 must not over-merge*. The product
ships with it, in the open, monitored.

### 5.4 Near misses that must not merge

| id | src | `area_m2` | `price_pln` | teryt | title | note |
|---|---|---|---|---|---|---|
| N1a | s1 | `1500.00` | `250000.00` | gm-A | "Działka 15 arów, Radzymin" | same plot… |
| N1b | s2 | `1500.00` | `255000.00` | gm-A | "Piękna działka Radzymin 1500 m²" | …2% dearer, two agencies |
| N2a | s1 | `1200.00` | `300000.00` | gm-A | "Działka budowlana 1200 m²" | |
| N2b | s2 | `1205.00` | `300000.00` | gm-A | "Działka budowlana 12 arów" | rounded area |
| N3a | s1 | `1000.00` | `140000.00` | gm-A | "ul. Leśna 12" | adjacent plots… |
| N3b | s2 | `1000.00` | `152000.00` | gm-A | "ul. Leśna 14" | …same street, same area |
| N4a | s1 | `1234.00` | `247000.00` | gm-A | — | identical to D1… |
| N4b | s2 | `1234.00` | `247000.00` | **gm-B** | — | …different gmina |
| N5a | s1 | `1500.00` | `250000.00` | gm-A | "Działka 15 a Radzymin" | reworded title… |
| N5b | s2 | `1500.00` | `260000.00` | gm-A | "Grunt inwestycyjny Radzymin" | …different price |

Every pair asserts **2 clusters** and `duplicate_count == 1` on each.

| Test | Pair |
|---|---|
| `test_price_differing_by_two_percent_does_not_merge` | N1a/N1b — **a known miss, asserted deliberately** |
| `test_rounded_area_does_not_merge` | N2a/N2b |
| `test_adjacent_plots_same_area_same_street_do_not_merge` | N3a/N3b |
| `test_same_area_and_price_in_different_gminas_do_not_merge` | N4a/N4b |
| `test_reworded_title_does_not_merge` | N5a/N5b |

`test_price_differing_by_two_percent_does_not_merge` carries this comment verbatim
in the test file:

> This asserts a **known miss**, not a success. N1a and N1b are the same plot. v0
> exact-match dedup does not catch it, and V56 accepts that. A future FR-13 matcher
> flips this test deliberately, in the same commit that adds the labelled set.

- `test_dedup_equality_is_exact_not_tolerant` — feeding `1500.00` and `1500.01`
  gives two clusters. The mutant this kills is `abs(a - b) < ε`, which passes every
  merge test in §5.1 and quietly merges half of §5.4.

### 5.5 No measured rate may be claimed

| Test | Asserts |
|---|---|
| `test_dedup_result_exposes_no_rate_attribute` | `DedupResult` has no `duplicate_rate`, `false_merge_rate`, `recall` or `precision` attribute — asserted by name over `dir()`, so adding one fails |
| `test_run_report_states_exact_match_only` | the report string contains the caveat: dedup is exact-match only, residual duplicate rate **unknown, not measured** |
| `test_ui_surface_carries_the_exact_match_caveat` | the caveat renders wherever `n` is shown |
| `test_no_module_imports_a_dedup_labelled_set` | nothing under `lpc.dedup` reads `tests/labelled/` |

---

## 6. Quarantine reason vocabulary

The closed enum, its stored strings, and exactly which input produces each. Stored
in `listing_quarantine.reason TEXT NOT NULL` as the **lowercase string**; the enum
member is the Python-side name.

| Enum member | Stored string | Produced by | Upstream failure |
|---|---|---|---|
| `PRICE_MISSING` | `price_missing` | price field absent from the parsed item | `PriceFailure.ABSENT` |
| `PRICE_PLACEHOLDER` | `price_placeholder` | `"Zapytaj o cenę"`, `"cena do uzgodnienia"`, `"do negocjacji"`, `"kontakt w sprawie ceny"` | `PriceFailure.PLACEHOLDER` |
| `PRICE_NON_POSITIVE` | `price_non_positive` | `"0 zł"`, `"0,00 zł"`, `"-1000 zł"` | `PriceFailure.NON_POSITIVE` |
| `PRICE_NOT_A_TOTAL` | `price_not_a_total` | `"200 zł/m²"`, `"2 500 zł/mies."` in the total-price field | `PriceFailure.NOT_A_TOTAL` |
| `PRICE_UNSUPPORTED_CURRENCY` | `price_unsupported_currency` | `"60 000 EUR"` | `PriceFailure.UNSUPPORTED_CURRENCY` |
| `AREA_MISSING` | `area_missing` | no area in register, structured, body or title | `resolve_area` → `AREA_MISSING` |
| `AREA_NO_UNIT` | `area_no_unit` | `"1200"`, `"1200,50"` | `AreaFailure.NO_UNIT` |
| `AREA_NO_VALUE` | `area_no_value` | `"m²"`, `"arów"` | `AreaFailure.NO_VALUE` |
| `AREA_UNIT_UNKNOWN` | `area_unit_unknown` | `"12 morgów"`, `"3 akry"`, `"12000 sq ft"` | `AreaFailure.UNKNOWN_UNIT` |
| `AREA_NON_POSITIVE` | `area_non_positive` | `"0 m²"`, `"-500 m²"` | `AreaFailure.NON_POSITIVE` |
| `AREA_AMBIGUOUS_SEPARATOR` | `area_ambiguous_separator` | `"1.200 m²"`, `"0.12 ha"`, `"12.5 ara"`, `"1.250.000 m²"` (D79) | `AreaFailure.AMBIGUOUS_SEPARATOR` |
| `AREA_NOT_SINGLE_VALUED` | `area_not_single_valued` | `"1200-1500 m²"`, `"od 1200 do 1500 m²"` (D82) | `AreaFailure.NOT_SINGLE_VALUED` |
| `AREA_CONFLICTING_STATEMENTS` | `area_conflicting_statements` | `"1200 m² (15 arów)"` (D90) | `AreaFailure.CONFLICTING_STATEMENTS` |

**Thirteen members, none conditional.** The decisions closed every "only if" in
this table. D79, D82 and D90 each make a reason unconditional. D80 does the
opposite: it parses the magnitude abbreviations, so `PRICE_AMBIGUOUS_MAGNITUDE` has
no producing input and is **removed**. A member no input can produce is dead code
in a closed enum, and `test_every_reason_has_a_producing_fixture` deletes it.

**Not in the vocabulary, deliberately:** there is no `out_of_band`, no
`implausible`, no `suspicious` and no `other`. Out-of-band records are flagged and
kept (§4), and a free-text or catch-all reason makes V50's per-reason rates
uncomputable.

| Test | Asserts |
|---|---|
| `test_quarantine_reason_is_a_member_of_the_closed_enum` | `record.reason in QuarantineReason` for every fixture |
| `test_every_quarantined_record_has_a_non_null_reason` | non-`None`, non-empty, over `tests/fixtures/quarantine/` |
| `test_quarantining_without_a_reason_raises` | `QuarantinedRecord(reason=None)` → `ValueError`; reason is a constructor argument |
| `test_every_reason_has_a_producing_fixture` | **every enum member** is produced by at least one fixture. A member whose question resolves the other way becomes dead and this test deletes it |
| `test_every_parse_failure_maps_to_exactly_one_reason` | the `AreaFailure`/`PriceFailure` → `QuarantineReason` map is total and injective; an unmapped failure raises rather than defaulting |
| `test_no_reason_string_contains_uppercase_or_spaces` | the stored strings are the table's, exactly — they are grouped on in SQL |
| `test_reason_strings_are_stable` | the stored strings are asserted against a frozen literal list; renaming one breaks V50's rolling baseline and must be a deliberate migration |
| `test_quarantined_record_retains_its_listing_ref` | `listing_ref` carries `source`, `external_id`, `url`, `raw_document_hash` (FR-72) |
| `test_out_of_band_is_not_quarantined` | B9 → not a `QuarantinedRecord` |
| `test_quarantined_records_never_reach_aggregates` | 10 records, 3 quarantined → `n == 7` |
| `test_quarantined_count_is_reported_by_the_run` | the run report states 3 |

### 6.1 Per-reason rate assertion (V50)

Synthetic rate histories; the assertion itself lives in `ops/assertions/`.

| Test | Setup | Expected |
|---|---|---|
| `test_per_reason_rates_are_computed_separately` | 100 records: 5 `area_unit_unknown`, 1 `price_placeholder` | report keyed by reason: `{area_unit_unknown: 0.05, price_placeholder: 0.01}` — not `0.06` |
| `test_spike_in_one_reason_alarms_even_when_total_is_flat` | baseline 6% split `{area_unit_unknown: 0.02, price_placeholder: 0.02, area_no_unit: 0.02}`; new run 6% **all** `area_unit_unknown` | alarm — **the F12 test** |
| `test_stable_rates_do_not_alarm` | every reason within baseline ± tolerance | no alarm |
| `test_new_reason_appearing_alarms` | `area_conflicting_statements` at 3% with no baseline | alarm |
| `test_reason_disappearing_alarms` | a reason at a stable 2% drops to 0% | alarm — an upstream change that stopped producing a failure class is drift too |
| `test_alarm_blocks_publication` | alarm fired | the stage returns blocking; the coverage page is not refreshed |
| `test_baseline_is_read_not_hardcoded` | a rate history with three recorded runs | the baseline comes from that history, not from a literal (the O25 discipline) |

---

## 7. Which tests are property-based

Everything in §1–§6 is **example-based**, tier A: an independent correct answer
exists for each row and pinning it is the point. Property-based tests cover the
inputs the tables cannot enumerate.

### 7.1 Property-based (Hypothesis)

Every `parse_area` call below passes `field="structured"`. D86 makes the field
argument required, and the bare `a` forms parse only in a structured field, a
title, or near a keyword.

| Test | Strategy | Property |
|---|---|---|
| `test_cross_unit_equivalence_generated` | `integers(1, 2000)` ares | `parse_area(f"{n} arów") == parse_area(f"{n*100} m²") == parse_area(ha_form(n))` |
| `test_ha_ar_m2_ladder` | `decimals(0.01, 20, places=4)` | `parse_area(f"{h} ha").m2 == 100 * parse_area(f"{h} a").m2` |
| `test_compound_equals_the_sum_of_its_parts` | `integers(1, 20)` ha × `integers(1, 99)` ares | `parse_area(f"{h} ha {a} a").m2 == parse_area(f"{h} ha").m2 + parse_area(f"{a} a").m2` — D90 as a property |
| `test_agreeing_restatement_equals_the_single_statement` | generated `m2` divisible by 100 | `parse_area(f"{m} m² ({m//100} arów)").m2 == parse_area(f"{m} m²").m2`, and the confidence is `high` in both |
| `test_decimal_comma_and_thousands_space_are_equivalent` | generated values ≥ 1000 | with and without the group separator, identical |
| `test_separator_characters_are_equivalent` | `sampled_from([" ", "\u00a0", "\u202f", "\u2009", ""])` | all five give the same `m2` |
| `test_round_trip_canonical_form` | `decimals(1, 10**7, places=2)` | `parse_area(format_area(m2), "structured").m2 == m2` |
| `test_parse_is_total` | `text()` — unrestricted | never raises; always a value **or** a named failure |
| `test_parse_price_is_total` | `text()` | same |
| `test_idempotence` | generated `ParsedItem` | `normalize(normalize(x)) == normalize(x)` |
| `test_band_flags_is_monotone_in_area` | `decimals` | area above the edge is flagged for every larger area — no interior hole |
| `test_adding_an_exact_duplicate_leaves_median_unchanged` | generated corpora | median identical |
| `test_adding_an_exact_duplicate_leaves_n_unchanged` | generated corpora | post-dedup `n` identical; `duplicate_count` increments |
| `test_dedup_is_order_invariant` | `permutations` | same clusters, same canonical |
| `test_dedup_is_idempotent` | generated corpora | `dedup(dedup(x)) == dedup(x)` |
| `test_canonical_selection_is_a_total_order` | generated clusters | comparator axioms |
| `test_scaling_price_and_area_together_leaves_price_per_m2_unchanged` | ×10 on both | zł/m² identical |
| `test_doubling_every_price_doubles_the_median_exactly` | ×2 on price | median exactly ×2 |

### 7.2 Non-vacuity companions

The gap analysis (§E) requires every metamorphic relation to be paired with a proof
that it can fail. Each of these runs the same property against a deliberately broken
stub and asserts the property **fails**:

| Companion | Broken stub |
|---|---|
| `test_duplicate_property_fails_against_a_no_op_dedup` | `dedup` that returns its input unchanged |
| `test_order_invariance_fails_against_a_first_wins_dedup` | canonical = first in input order |
| `test_scaling_property_fails_against_a_wrong_multiplier` | `AR_IN_M2 = 10` |
| `test_band_monotonicity_fails_against_a_one_sided_check` | only the lower edge checked |
| `test_compound_sum_property_fails_against_a_first_value_parser` | the superseded rule D90 replaced: a parser that returns the first value of a compound |

Without these, "adding a duplicate changes nothing" passes trivially against a
dedup that ignores its arguments — which is exactly the failure `20` §4.3 warns
about.

### 7.3 Deliberately **not** property-based

Unit lexicons, band constants, authority order, the reason vocabulary and the
dedup fixture rows. A generator over "Polish area strings" would encode the same
assumption the parser encodes, and the test would agree with the bug.

---

## 8. Fixtures

`tests/fixtures/`, per repo layout §1. Every file carries `captured_at` and is
scrubbed of seller names, phone numbers and addresses at capture (FR-23).

| Directory | Files | Drives |
|---|---|---|
| `portal/areas/` | one recorded advert per §1.1–1.6 case id | §1 |
| `portal/prices/` | one per §2 case id, all placeholder phrasings | §2 |
| `portal/conflict/` | one advert whose title, body and structured field disagree, plus its register area | §3 |
| `portal/both_prices/` | one agreeing, one 100× off | F2 cross-check |
| `bands/` | B2, B5, B9, B10, B11, B12 as complete records | §4 |
| `quarantine/` | one record per `QuarantineReason` member — 13 files | §6 |
| `dedup/exact/` | D1, D1′, D2, D3 | §5.1 |
| `dedup/round/` | R1–R6, including the R3/R4 known false merge | §5.3 |
| `dedup/near/` | N1a–N5b | §5.4 |
| `price_kind/` | one portal, one bailiff, one KOWR record with divergent values | F9 |

- `test_every_fixture_file_has_a_capture_date` — parses `captured_at` from every
  file under `tests/fixtures/`; a fixture with no date is a fixture with no
  provenance (rule 7).
- `test_no_fixture_contains_a_phone_number_or_email` — regex sweep, run in CI, not
  at review time.

---

## 9. CI wiring

`.github/workflows/ci.yml`. Markers registered in `pytest.ini`: `property`,
`architecture`, `integration`, `blocked`, `slow`.

| Job | Trigger | Command | Gate |
|---|---|---|---|
| `unit` | every push, every PR | `pytest tests/unit -m "not blocked"` | blocking |
| `architecture` | every push | `pytest tests/architecture` | blocking |
| `property` | every push | `pytest tests/property -m property --hypothesis-profile=ci` | blocking |
| `integration` | every PR | `pytest tests/integration` with a `postgis/postgis:16` service | blocking |
| `fixtures` | every PR | `pytest tests/unit/test_fixture_hygiene.py` (capture dates, PII sweep) | blocking |
| `blocked-audit` | every push | `pytest -m blocked --collect-only` + `test_every_blocked_marker_names_an_open_question` | blocking — rule 2 |
| `mutation` | nightly, and on the `mutation` PR label | `mutmut run --paths-to-mutate src/lpc/normalize,src/lpc/dedup` | blocking on the named-mutant list (pass-1 §14), advisory on the score |
| `assertions-dryrun` | nightly | `ops/assertions` against the last run's data | advisory — the real gate is inside the pipeline |

Hypothesis profiles:

- `ci` — `max_examples=200`, `deadline=None`, `derandomize=True`, database disabled.
  Deterministic, so a CI failure reproduces locally from the same seed.
- `dev` — `max_examples=25`, database enabled, so a locally-found falsifying example
  is replayed first.
- `nightly` — `max_examples=2000`, `derandomize=False`. The only job allowed to find
  a new counterexample; it opens an issue rather than failing the branch.

Not in CI, by design:

- `scripts/audit_unit_conversion.py` — the 20-listing ar/ha hand audit. Manual, run
  at first ingest and quarterly, **zero errors tolerated**. A hand audit that runs
  in CI is not a hand audit.
- The 50-listing duplicate eyeball (`18` §7). It produces no metric and is recorded
  as an eyeball.
- V7(b)'s git-history sweep — needs full history, which shallow CI clones lack; it
  runs as a pre-push hook.

Ordering gate: the `mutation` job is meaningful only once §3 steps 1–14 of the
pass-1 spec are green, so it is added to the workflow in the same commit as step 15
and not before.

---

## 10. Traceability of this plan

| Pass-1 section | Detailed in | Contract change |
|---|---|---|
| §4.1 area table | §1 | `confidence` field; required `field` argument (D86) |
| §4.2 price table | §2 | `confidence` field; `NOT_A_TOTAL`, `UNSUPPORTED_CURRENCY` failures |
| §4.3 authority | §3 | `candidates` mapping replaces a bare `conflict` bool; threshold 5% (D81) |
| §5 bands | §4 | the band check reads the exact quotient (D88); aggregates exclude an out-of-band record (D85) |
| §6 quarantine | §6 | reason vocabulary fixed at **13 members, none conditional**; `PRICE_AMBIGUOUS_MAGNITUDE` removed (D80) |
| §7 properties | §7 | non-vacuity companions added |
| §13 dedup | §5 | match key `(area, price, gmina, asset_class)` (D78); no round-number guard |
| §10 fixtures | §8 | `dedup/round/` added |
| — | §9 | CI wiring, absent from pass 1 |

The four contract changes are already in the pass-1 spec's §2 table:
`confidence`, `field`, `candidates`, and the two new price failures.
