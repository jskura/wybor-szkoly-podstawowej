# Test plan — the ingestion connectors (pass 2)

Pass 2, step 5 of [`CLAUDE.md`](../../../CLAUDE.md) rule 8, for
[`02-connectors.md`](../02-connectors.md). Pass 1 gave the ordered red-green
sequence; this document gives **the detail a developer types straight in**:
literal fixture contents, the harness interfaces, exact inputs and exact expected
outputs, and the CI wiring that decides which of them can be green today.

Where pass 1 and this document disagree, the disagreement is marked
**⟳ refines** and is a deliberate correction — pass 2 is allowed to sharpen a
number that pass 1 stated loosely. Six such refinements exist; they are collected
in §9.

**Status legend used throughout:**

| Mark | Meaning |
|---|---|
| **S** | Synthetic — hand-written, committed now, tests *our* code against markup or text we own |
| **R‑portal** | Recorded from a live portal — **cannot exist until O10 resolves** |
| **R‑host** | Recorded from KOWR / auction / BIP hosts — needs that host's own `robots.txt` evidence first (§0.4 of pass 1), and for auctions also O16 |
| **✎** | A literal value pinned in a test; changing the fixture without changing the literal is a fixture-policy violation |

---

## 1. The fixture tier rule, stated once

Pass 1 §0.2 forbids inventing portal markup, and
[`04-validation.md`](../../04-validation.md) §Fixtures policy rule 2 forbids
hand-editing fixtures. Neither forbids hand-writing a fixture **whose content we
are the author of**. The distinction that governs every fixture below:

> A fixture may be hand-written when the thing under test is **our parser of a
> format we do not control the values of but do control the sample of** — a
> `robots.txt` we wrote, a Polish legal phrase whose wording is fixed by statute,
> a page skeleton emitted by a test double we own.
>
> A fixture **must be recorded** when the test pins a value that only the source
> can produce — a portal's markup, KOWR's notice layout, a BIP bulletin, a BDL
> value.

Applied:

| Tier | Where it is legitimate | Where it would be a false green |
|---|---|---|
| **S** | `robots.txt` parsing, rate limiting, backoff, raw-payload storage, health/alarm logic, count-agreement arithmetic, aggregate separation (V46), coverage registry (V55 §7.1–7.5), area-unit arithmetic, statutory-fraction phrase parsing | Any test asserting "the portal's price is in `<span class="price">`" |
| **R‑portal** | §4.4–§4.8 of pass 1 | — |
| **R‑host** | §5 (KOWR), §6 (auction), §7.6–§7.11 (BIP layouts) | — |

**The consequence nobody has written down yet:** pass 1 §9 marks KOWR and BIP
fixtures "✓ recordable now", but §0.4 requires recorded `robots.txt` evidence for
*every* host before it is fetched, and no evidence file exists for any host. KOWR
and the ~50 BIP hosts are therefore **also blocked**, just by a much smaller gate
than O10 — an afternoon of recording, not a product decision. Recorded as **Q9**
(§10). Until it clears, the only recordable source is GUS BDL, and even that needs
Q7 (variable IDs).

---

## 2. Fixture inventory — literal contents

Naming, from pass 1 §8: `tests/fixtures/<source>/<YYYY-MM-DD>_<variant>.<ext>`.
Synthetic fixtures use the same layout under a `synthetic/` subdirectory so
`test_fixtures_are_not_stale` can exempt them (a synthetic fixture does not go
stale; a recorded one does).

### 2.1 `robots.txt` — `tests/fixtures/robots/` (S, all of them)

Nine files. Each is given verbatim; trailing newline present in every file.

**`allow-all.txt`**

```
User-agent: *
Disallow:
```

**`disallow-oferta.txt`** — the list-allowed/detail-disallowed case, used by both
2.2 and 2.7

```
User-agent: *
Disallow: /oferta/
Disallow: /ogloszenie/
Allow: /szukaj
Sitemap: https://example.invalid/sitemap.xml
```

**`disallow-all.txt`**

```
User-agent: *
Disallow: /
```

**`agent-specific.txt`** — 2.3

```
User-agent: *
Disallow: /

User-agent: lpc-research-bot
Allow: /szukaj
Disallow: /oferta/
```

**`crawl-delay-20.txt`** — 2.6, stricter than ours

```
User-agent: *
Crawl-delay: 20
Disallow: /admin/
```

**`crawl-delay-2.txt`** — 2.6, laxer than ours

```
User-agent: *
Crawl-delay: 2
Disallow: /admin/
```

**`malformed.txt`** — every tolerable defect in one file: BOM, CRLF line endings,
a typo'd directive, an unparseable delay, a comment, a group with no `User-agent`

```
﻿# robots
Disalow: /oferta/
Crawl-delay: soon
Allow /szukaj
User-agent: *
Disallow: /admin/
```

**`unparseable.txt`** — no recognisable group at all

```
<!DOCTYPE html>
<html><body>404 Not Found</body></html>
```

**`empty.txt`** — zero bytes.

Two further cases are **response scripts, not files**: `/robots.txt` → `404`
(2.4) and `/robots.txt` → `503` (2.5).

**Parsing semantics pinned by the tests** (RFC 9309 where it decides, our
fail-closed rule where it does not):

| Input | `policy.state` | `allows("/szukaj?q=x")` | `allows("/oferta/1")` | Notes |
|---|---|---|---|---|
| `allow-all.txt` | `allow_all` | `True` ✎ | `True` ✎ | |
| `empty.txt` (0 bytes) | `allow_all` | `True` ✎ | `True` ✎ | An empty file is full allow — but `source.robots_ok` still gates the fetch (§0.4) |
| `disallow-oferta.txt` | `partial` | `True` ✎ | `False` ✎ | Drives `mode == "list_only"` |
| `disallow-all.txt` | `disallow_all` | `False` ✎ | `False` ✎ | |
| `agent-specific.txt`, agent `lpc-research-bot` | `partial` | `True` ✎ | `False` ✎ | Named group wins outright; the `*` group is not merged in |
| `agent-specific.txt`, agent `other` | `disallow_all` | `False` ✎ | `False` ✎ | |
| `malformed.txt` | `partial` | `True` ✎ | `True` ✎ | Unrecognised lines dropped **per line**; `warnings == ["line 2: unknown directive 'Disalow'", "line 3: unparseable Crawl-delay 'soon'", "line 4: missing colon"]` ✎ |
| `unparseable.txt` | `unparseable` | `False` ✎ | `False` ✎ | Zero recognisable groups ⇒ fail closed, alarm `robots_unparseable` |
| 404 | `unknown` | raises `RobotsEvidenceMissing` | — | Absence is not permission |
| 503 | `unavailable` | `False` ✎ | `False` ✎ | Alarm `robots_unavailable`, zero content requests |

Longest-match precedence gets its own case, because it is the rule most parsers
get wrong: against `disallow-oferta.txt` extended with `Allow: /oferta/public/`,
`allows("/oferta/public/1") is True` ✎ and `allows("/oferta/1") is False` ✎.

The line-tolerant-but-document-fail-closed split is a decision, not a reading of
the RFC. Recorded as **Q10** (§10).

### 2.2 GUS BDL — `tests/fixtures/gus_bdl/`

Two sub-tiers, and the split matters:

- `synthetic/` (**S**) — pagination, drift, absence and zero-item **mechanics**.
  These test our client, not GUS's numbers.
- the dated top level (**recordable once Q7 closes**) — value pinning (3.2) and
  the independent hand-check (3.12).

The synthetic envelope below is **our contract, asserted against the first real
capture**. If the recorded response has different key names, the synthetic
fixtures are regenerated and that mismatch is itself the finding — see
`test_the_recorded_capture_matches_the_synthetic_envelope` in §7.3.

**`synthetic/by-unit_1415_land-sales.json`** (S) — verbatim:

```json
{
  "unitId": "011415000000",
  "unitName": "powiat skierniewicki",
  "measureUnitId": 8,
  "measureName": "zl/m2",
  "lastUpdate": "2026-05-20",
  "results": [
    {
      "id": 633712,
      "variableId": 633712,
      "values": [
        {"year": "2025", "period": "Q1", "val": 61.20, "attrId": 0},
        {"year": "2025", "period": "Q2", "val": 64.80, "attrId": 0},
        {"year": "2025", "period": "Q3", "val": 66.10, "attrId": 0},
        {"year": "2025", "period": "Q4", "val": 68.40, "attrId": 0}
      ]
    }
  ],
  "totalRecords": 4,
  "page": 0,
  "pageSize": 100,
  "links": {"self": "...", "first": "...", "next": null}
}
```

Derived expectations, all ✎:

| Field | Expected |
|---|---|
| `len(items)` | `4` |
| `[(p.period, p.value) for p in items]` | `[("2025-Q1", Decimal("61.20")), ("2025-Q2", Decimal("64.80")), ("2025-Q3", Decimal("66.10")), ("2025-Q4", Decimal("68.40"))]` |
| `sum(p.value for p in items)` | `Decimal("260.50")` — a total-check that catches a dropped record anywhere |
| `items[3].transacted_at` | `date(2025, 12, 31)` |
| `items[3].as_of` | `date(2026, 5, 20)` — from `lastUpdate`, never from `now()` |
| `{p.price_type}` | `{"sales"}` |
| `{p.unit_level}` | `{"powiat"}` |
| `{p.teryt}` | `{"1415"}` |
| `str(items[0].value)` | `"61.20"` — exponent pinned, see §5.4 |

**`synthetic/by-unit_1415_no-rural-split.json`** (S) — the `results` array carries
the *ogółem* variable only; the urban (`633713`) and rural (`633714`) blocks are
absent, and a companion `synthetic/by-variable_633714_empty.json` carries
`{"results": [], "totalRecords": 0, "page": 0, "pageSize": 100}`.

Expected: `item.rural_value is None` ✎, `item.rural_absence_reason ==
"not_published"` ✎, `0 not in [i.value for i in items]` ✎, and no row is written
with `value = 0`.

**`synthetic/paged-1of3.json` / `-2of3.json` / `-3of3.json`** (S) — the
by-variable call across all units. Deterministic content, so every expectation is
arithmetic rather than a transcription:

- record *n* runs `n = 1 … 250`
- `unitId` = `"TEST-%04d" % n` (`TEST-0001` … `TEST-0250`)
- `val` = `50.00 + 0.10 * (n - 1)`
- page 0 holds records 1–100, page 1 holds 101–200, page 2 holds 201–250
- every page carries `"totalRecords": 250, "pageSize": 100`
- page 0 and 1 carry a non-null `links.next`; page 2 carries `"next": null`

| Assertion | Expected |
|---|---|
| `len(items)` | `250` ✎ |
| `items[0].value` | `Decimal("50.00")` ✎ |
| `items[99].value` | `Decimal("59.90")` ✎ |
| `items[100].value` | `Decimal("60.00")` ✎ |
| `items[249].value` | `Decimal("74.90")` ✎ |
| `sum(i.value for i in items)` | `Decimal("15612.50")` ✎ |
| `result.stated_total` | `250` ✎ |
| `result.alarms` | `[]` ✎ |

**`synthetic/paged-truncated.json`** (S) — page 2 (records 201–250) is not served;
page 1 still advertises a `next`.

| Assertion | Expected |
|---|---|
| `len(items)` | `200` ✎ |
| `sum(i.value for i in items)` | `Decimal("11990.00")` ✎ |
| `result.shortfall_ratio` | `pytest.approx(0.2, abs=1e-9)` ✎ |
| `"corpus_incomplete" in result.alarms` | `True` |
| `result.published` | `False` |
| `assertion_run.blocked_publication` | `True` |

**`synthetic/drift-renamed-value-field.json`** (S) — identical to the nominal
fixture with `"val"` renamed to `"value"` in all four records. Expected:
`result.parse_failure_rate == 1.0` ✎, `"schema_drift" in result.alarms`,
`result.items_emitted == 0` ✎, and **no** insert is attempted with a null value.

**`synthetic/zero-items.json`** (S) — `{"results": [{"id": 633712, "values": []}],
"totalRecords": 0, ...}`. A structurally valid response carrying nothing, which is
what V8's zero-item test needs.

**`synthetic/partial-failure-40-items.json`** (S) — 40 records, one of which
carries `"val": "brak danych"`. Expected `items_emitted == 39` ✎,
`parse_failure_rate == pytest.approx(0.025)` ✎, `alarms == []`.

**`2026-XX-XX_by-unit_1415_land-sales.json` (recordable, gated on Q7)** — the real
capture. Its literals are transcribed into the test **at capture time**, replacing
the synthetic ones in test 3.2. Until then 3.2 runs against `synthetic/` and is
marked `requires_recorded_fixture` so the skip manifest (§7.3) shows it as
knowingly unverified against reality.

**`2026-XX-XX_web-handcheck.csv` (recorded by hand, gated on Q7)** — the
independent oracle for 3.12, transcribed from the BDL **web interface**, never
through our client. Committed shape, header verbatim:

```csv
teryt,unit_name,period,variable_name,value_pln_m2,bdl_url,transcribed_by,transcribed_at
1415,powiat skierniewicki,2025-Q4,<variable name as shown in the web UI>,<value>,<url>,<initials>,<YYYY-MM-DD>
2804,powiat elblaski,2025-Q4,...,...,...,...,...
<third powiat from the ring manifest>,...,2025-Q4,...,...,...,...,...
```

The third row is deliberately not invented here — it comes from work item 3's ring
manifest, which does not exist yet.

**A gap this fixture exposed.** The pass-1 URL assertion (3.1) uses
`unit="1415"`, but BDL addresses units by a 12-character identifier
(`011415000000` in the envelope above), not by a bare TERYT code. The
TERYT → BDL-unit-id mapping is data we must record, not derive. New test:

```
tests/unit/ingest/gus_bdl/test_unit_ids.py

  test_teryt_to_bdl_unit_id_mapping_is_recorded_not_derived
    assert mapping["1415"] == "011415000000"          # from config, ✎ at capture
    assert every in-scope powiat TERYT has a mapping entry
    assert the loader raises UnmappedUnit for a TERYT absent from the map,
           rather than constructing an id by string surgery
```

### 2.3 The synthetic listing corpus — `tests/fixtures/fake_source/` (S)

A page skeleton **we author**, served by a test double, used for everything in
pass 1 §1 (contract, health, resumability), §2 (politeness), §4.1 (raw store) and
§4.5's arithmetic. It is not a stand-in for a portal and no test pins a value from
it *as if* it were one.

**`2026-08-08_list_nominal_p1.html`** — verbatim skeleton, items 2–40 elided by
the generation rule below:

```html
<html><head><meta charset="utf-8"><title>fake source — wyniki</title></head>
<body>
<p class="results-count">Znaleziono 248 ogłoszeń</p>
<ul class="results">
  <li class="item" data-id="F0000001" data-lat="51.9550" data-lon="20.1420">
    <a class="link" href="/oferta/F0000001">Działka</a>
    <span class="category">działka budowlana</span>
    <span class="price">101 000 zł</span>
    <span class="area">1000 m²</span>
    <span class="locality">Testowo</span>
    <span class="posted">2026-08-01</span>
  </li>
  <!-- items F0000002 … F0000040 by the generation rule -->
</ul>
<a class="next" href="/szukaj?p=2">Następna</a>
</body></html>
```

**Generation rule** (a committed script, `scripts/gen_fake_fixtures.py`, so the
corpus is reproducible byte-for-byte):

- items `n = 1 … 248`, `data-id = "F%07d" % n`
- `price` = `100000 + 1000 * n` zł, rendered with U+00A0 thousands separators
- `area` = `1000 m²` for every item — so `price_per_m2` is exactly `100 + n`
- page *p* (1…7) holds items `40(p−1)+1 … min(40p, 248)`; page 7 holds 8 items
- `posted` = `2026-08-01`, `locality` = `Testowo`, coordinates constant

| Assertion | Expected |
|---|---|
| `len(parse(p1))` | `40` ✎ |
| `items[0].external_id` | `"F0000001"` ✎ |
| `str(items[0].price_pln)` | `"101000.00"` ✎ |
| `str(items[0].area_m2)` | `"1000.00"` ✎ |
| `items[0].area_raw` | `"1000 m²"` ✎ |
| last item of page 7 | `external_id "F0000248"`, `price_pln Decimal("348000.00")` ✎ |
| median `price_per_m2` over all 248 | `Decimal("224.50")` ✎ (mean of the 124th and 125th, `224.00` and `225.00`) |
| `parse_stated_total(p1)` | `StatedTotal(value=248, is_approximate=False)` ✎ |

**Structural variants.** Each is the nominal page with exactly one change, named
in the file. The change and the expected output:

| File (`2026-08-08_list_*`) | The one change | Expected |
|---|---|---|
| `_price-on-request.html` | item F0000003's price cell → `Cena do uzgodnienia` | `item.price_pln is None`; `quarantine == [("price_on_request", "F0000003")]` ✎; 39 rows written; **no** row with `price_pln == 0` |
| `_price-range.html` | item F0000003's price cell → `od 120 000 do 150 000 zł` | quarantine `price_is_range`; `listing_ref["price_low"] == 120000` ✎, `["price_high"] == 150000` ✎; **no** `135000` anywhere in the emitted rows |
| `_area-ares.html` | F0000004's area cell → `12 arów` | `area_m2 == Decimal("1200.00")` ✎, `area_raw == "12 arów"` ✎ |
| `_area-ares-abbrev.html` | F0000004 → `12 a` | `Decimal("1200.00")` ✎ |
| `_area-hectares.html` | F0000005 → `0,12 ha` | `Decimal("1200.00")` ✎ |
| `_area-hectares-large.html` | F0000005 → `1,2 ha` | `Decimal("12000.00")` ✎ |
| `_area-spaced-m2.html` | F0000005 → `1 200 m²` (U+00A0) | `Decimal("1200.00")` ✎ |
| `_area-no-unit.html` | F0000006 → `1,24` | quarantine `area_unit_missing` ✎; assert the emitted set contains no item with `area_m2 in (Decimal("1.24"), Decimal("124.00"), Decimal("12400.00"))` — the three ways an assumption would show up |
| `_no-coords.html` | F0000007 loses `data-lat`/`data-lon` | `geom is None` ✎, `location_precision == "locality"` ✎, `(lat, lon) != (0.0, 0.0)` ✎ |
| `_unmapped-category.html` | F0000008's category → `działka inwestycyjna` | alarm `unmapped_category`, `asset_class` unset ✎, item quarantined not defaulted (V26) |
| `_personal-data.html` | F0000009 gains `<span class="phone">+48 000 000 000</span><span class="seller">Jan Testowy</span>` | `item.seller_contact_hash != "+48 000 000 000"`; the string `000000000` appears nowhere in `repr(item)` ✎; hash is stable across runs under a fixed salt and differs under a different salt |
| `_duplicate-item.html` | F0000007's `<li>` repeated on page 1 (41 elements) | `items_emitted == 40` ✎, `intra_page_duplicates == 1` ✎ |
| `_cross-page-duplicate.html` | F0000041 appears on both page 1 and page 2 | distinct emitted `== 247` ✎, `cross_page_duplicates == 1` ✎ (see §6.2) |
| `_drift-renamed-price.html` | `class="price"` → `class="cena"` on every item | `parse_failure_rate == 1.0` ✎, `schema_drift` alarm, `items_emitted == 0` ✎ |
| `_zero-items.html` | count cell → `Znaleziono 0 ogłoszeń`, `<ul class="results"></ul>` | valid page, `items_emitted == 0`, `stated_total == 0`, `zero_items` alarm when `last_item_count = 200` |
| `_stated-total-approximate.html` | count cell → `ponad 1 000 ogłoszeń` | `StatedTotal(1000, is_approximate=True)` ✎; count agreement runs **report-only** |
| `_stated-total-missing.html` | count element removed | `stated_total is None`; alarm `stated_total_missing`; `published is True` (absence of their count is not evidence of our shortfall) |
| `_stated-total-drift_p1/_p7.html` | page 1 says `248`, page 7 says `251` | `stated_total == 248` (first wins) ✎, `stated_total_drift == 3` ✎, tolerance widened by 3 |
| `_truncated-p3of7.html` | pages 1–3 only, page 3 still links a next | `items_emitted == 120` ✎, `corpus_incomplete`, `published is False` |
| `_no-next-link-last-page.html` | page 7 without the `next` anchor | no alarm (count satisfied) |
| `_no-next-link-mid.html` | page 3 without the `next` anchor, count unsatisfied | alarm `pagination_broken` ✎ |

**The fake connector is not in the production registry.** Contract test 1.1 pins
`set(registry) == {"gus_bdl","portal","kowr","auction","gmina_bip"}`, so
`FakeConnector` lives in `tests/support/fake_connector.py` and is injected into a
*copy* of the registry by fixture. Its companion is the non-vacuity double:

```
tests/architecture/test_contract_has_teeth.py

  test_the_contract_suite_rejects_a_violating_connector
    BadConnector: parse() opens a socket, __init__ constructs httpx.Client(),
                  class defines is_healthy, parse() calls datetime.now(),
                  parse() accepts a str url
    for each of contract tests 1.2–1.5, 1.7, 1.9:
      assert it FAILS against BadConnector
    # a contract suite that passes everything proves nothing
```

### 2.4 Auction phrases — `tests/fixtures/auction/phrases/*.txt` (S)

The wording of a *cena wywoławcza* clause is fixed by the Code of Civil
Procedure, not by a website; the sentence is therefore ours to write, while the
**document** it sits in is not. So: the fraction arithmetic (pass 1 §6.1) is
tested against plain-text phrase fixtures **now**, and the document-level
extraction (which element holds the sentence) waits on O16.

Each file is one line, UTF-8, no trailing whitespace.

| File | Verbatim content | `price_pln` | `valuation_pln` | `statutory_fraction` | `auction_round` | `fraction_consistent` | `flags` |
|---|---|---|---|---|---|---|---|
| `first-auction-3-4.txt` | `Cena wywoławcza 3/4 sumy oszacowania wynosi 90 000,00 zł. Suma oszacowania wynosi 120 000,00 zł.` | `Decimal("90000.00")` ✎ | `Decimal("120000.00")` ✎ | `Fraction(3, 4)` ✎ | `1` ✎ | `True` | `[]` |
| `second-auction-2-3.txt` | `Cena wywoławcza 2/3 sumy oszacowania wynosi 80 000,00 zł. Suma oszacowania wynosi 120 000,00 zł.` | `Decimal("80000.00")` | `Decimal("120000.00")` | `Fraction(2, 3)` | `2` | `True` | `[]` |
| `second-auction-rounded.txt` | `Cena wywoławcza stanowi 2/3 sumy oszacowania i wynosi 86 667,00 zł. Suma oszacowania: 130 000,00 zł.` | `Decimal("86667.00")` | `Decimal("130000.00")` | `Fraction(2, 3)` | `2` | `True` (|Δ| = 0,33 zł ≤ 1,00 zł) | `[]` |
| `fraction-in-words.txt` | `Cena wywoławcza stanowi trzy czwarte sumy oszacowania i wynosi 90 000,00 zł.` | `Decimal("90000.00")` | `None` | `Fraction(3, 4)` | `1` | `None` (unknown, **not** `False`) | `[]` |
| `fraction-in-percent.txt` | `Cena wywoławcza stanowi 75% sumy oszacowania, tj. 90 000,00 zł.` | `Decimal("90000.00")` | `None` | `Fraction(3, 4)` | `1` | `None` | `[]` |
| `fraction-percent-approx.txt` | `Cena wywoławcza stanowi 66,67% sumy oszacowania, tj. 86 667,00 zł.` | `Decimal("86667.00")` | `None` | `Fraction(2, 3)` | `2` | `None` | `[]` |
| `fraction-percent-unknown.txt` | `Cena wywoławcza stanowi 80% sumy oszacowania, tj. 96 000,00 zł.` | `Decimal("96000.00")` | `None` | `None` ✎ | `None` ✎ | `None` | `["fraction_unrecognised"]` ✎ |
| `valuation-no-fraction.txt` | `Cena wywoławcza wynosi 90 000,00 zł. Suma oszacowania wynosi 120 000,00 zł.` | `Decimal("90000.00")` | `Decimal("120000.00")` | `None` ✎ — never defaulted to 3/4 | `None` | `None` | `[]` |
| `inconsistent-fraction.txt` | `Cena wywoławcza 3/4 sumy oszacowania wynosi 90 000,00 zł. Suma oszacowania wynosi 130 000,00 zł.` | `Decimal("90000.00")` | `Decimal("130000.00")` | `Fraction(3, 4)` | `1` | `False` | `["fraction_mismatch"]` — neither number is corrected to 97 500 |
| `round-fraction-conflict.txt` | `Druga licytacja. Cena wywoławcza 3/4 sumy oszacowania wynosi 90 000,00 zł.` | `Decimal("90000.00")` | `None` | `Fraction(3, 4)` | `None` ✎ | `None` | `["round_fraction_conflict"]` ✎ |
| `parcel-number-trap.txt` | `Nieruchomość: działka nr 123/4, obręb 0012. Cena wywoławcza wynosi 90 000,00 zł.` | `Decimal("90000.00")` | `None` | `None` ✎ | `None` | `None` | `[]` — `123/4` is a parcel number, not a fraction |
| `no-price.txt` | `Suma oszacowania wynosi 120 000,00 zł.` | quarantine `price_missing` | — | — | — | — | — |
| `no-date.txt` | `Cena wywoławcza wynosi 90 000,00 zł.` (no auction date anywhere) | quarantine `auction_date_missing` ✎ | — | — | — | — | — |

Number-format variants, all parsing to `Decimal("90000.00")` ✎, each its own
one-line file under `phrases/amounts/`:

`90 000,00 zł` (U+00A0) · `90 000,00 zł` (U+202F) · `90 000,00 zł` (ASCII space) ·
`90.000,00 zł` · `90000 zł` · `90 000 złotych` · `90 000,00 PLN`

And two that must **not** parse to a price: `90 000,00 zł/m²` → flag
`price_is_unit_rate`, quarantine ✎ (F2 — a per-m² figure read as a total is the
same class of error as the ares trap); `90 000 000,00 zł` → parses to
`Decimal("90000000.00")` and is left to the outlier band, not silently rescaled.

**Consistency rule, pinned once:** `fraction_consistent` is `True` iff
`abs(price_pln − valuation_pln × fraction) ≤ Decimal("1.00")`; `None` when either
side is absent; `False` otherwise. The 1,00 zł tolerance is a threshold to ratify
(**Q11**, §10) — notices round to the full złoty.

The auction **date** fixture, for 6.8: `phrases/date.txt` containing
`Licytacja odbędzie się w dniu 12 września 2026 r. o godz. 10:00.` →
`auction_at == datetime(2026, 9, 12, 10, 0, tzinfo=ZoneInfo("Europe/Warsaw"))` ✎,
asserted under `TZ=UTC` and `TZ=America/New_York` alike (F10).

### 2.5 KOWR, BIP and auction documents — shape only (R‑host)

No markup is written here. What a capture session must produce, per source:

**KOWR** — `tests/fixtures/kowr/` (R‑host, blocked on Q9)

| File | What the capture must contain | Values the test will pin at capture |
|---|---|---|
| `<date>_notice-list_p1.html` | A notice index page including the source's own stated total | stated total (pass 1 uses `87`), item count on the page, the `next` link's shape |
| `<date>_notice_ha-area.html` | One notice, area stated in hectares with a decimal comma | `price_pln`, `area_m2`, `area_raw`, `teryt_gmina`, `notice_date` (pass 1 pins `145000.00`, `12400.00`, `"1,2400 ha"`, `"1015052"`, `2026-07-14` — **provisional until capture**) |
| `<date>_notice_ares.html` | Area in ares | as above |
| `<date>_notice_no-price.html` | A notice with no stated price | quarantine `price_missing`, `listing_ref` retains the identifying JSON |
| `<date>_notice_price-range.html` | *od … do …* | `price_low`, `price_high`, no midpoint |
| `<date>_notice_no-area.html` | No usable area | quarantine `area_missing` |
| `<date>_notice_named-locality.html` | A notice naming a locality that collides between a city and a rural gmina | resolves to the rural TERYT, never by name match |
| `<date>_list_truncated-p2of4.html` | Index truncated | `corpus_incomplete` |
| `<date>_drift-renamed-price.html` | The nominal notice with the price element renamed | `schema_drift` |

**Auctions** — `tests/fixtures/auction/<layout>/` (R‑host, blocked on Q9 **and**
O16). One directory per layout the layout registry declares; the phrase fixtures
above supply the arithmetic, the recorded documents supply "the phrase is in this
part of the page". Test 6.16 asserts every registered layout has ≥ 1 dated
fixture and every fixture directory has a registered layout — that test is green
today with **zero** layouts and zero directories, so it needs its non-vacuity
companion: `test_a_layout_without_a_fixture_fails_the_registry_check`, which
registers a synthetic layout and asserts 6.16 fails.

**BIP** — `tests/fixtures/gmina_bip/<family>/` (R‑host, blocked on Q9). Families
to seed: `bip_gov_table`, `wordpress_attachment_list`, `plain_html_ordinance`,
`scanned_pdf`, `js_rendered`. Plus one fixture that is **S** and unblocked:

**`tests/fixtures/gmina_bip/rings_gminas.json`** (S until work item 3 produces the
real manifest) — the ring membership 7.1 asserts against:

```json
{
  "computed_by": "work-item-3 ring builder",
  "rule": "D64 — any part of the gmina boundary within 25 km of the anchor",
  "as_of": "2026-08-08",
  "gminas": [
    {"teryt": "1015052", "name": "<name>", "ring": "A"},
    {"teryt": "...", "name": "...", "ring": "B"}
  ]
}
```

7.1's count is asserted as `len(covered) + len(uncovered) == len(manifest.gminas)`
✎ — pinned to the manifest, never to a literal, which is what B3 in the gap
analysis corrected.

### 2.6 The V46 separation fixture — `tests/fixtures/aggregates/price-kinds.json` (S)

The one fixture in this document whose numbers must be exactly right, because it
is the only test that proves D65 works. Thirty rows, every `area_m2 = 1000.00`,
so `price_per_m2` equals `price_pln / 1000` exactly.

| Group | n | `price_kind` | `price_per_m2` values |
|---|---|---|---|
| Asking | 20 | `asking` | `71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89` |
| Tender (KOWR) | 5 | `tender` | `20, 20, 20, 20, 20` |
| Auction | 5 | `auction_start` | `30, 30, 30, 30, 30` |

Every row carries `price_type = "offering"` (D65) and a distinct `price_kind`.

| Assertion | Expected |
|---|---|
| asking `n` | `20` ✎ |
| asking median | `Decimal("80.00")` ✎ (10th and 11th are both 80) |
| asking p25 / p75 | `Decimal("75.75")` / `Decimal("84.25")` ✎ (linear interpolation, `idx = q(n−1)`) |
| tender `n`, median | `5`, `Decimal("20.00")` ✎ |
| auction `n`, median | `5`, `Decimal("30.00")` ✎ |
| asking median **after** loading tender and auction rows | still `Decimal("80.00")`, `n` still `20` ✎ |
| **non-vacuity control** — a deliberately blended computation over all 30 | `Decimal("75.50")` ✎ |
| blended over asking + tender only | `Decimal("78.00")` ✎ |

The last two rows are the point. If the separation is broken the test does not
merely fail — it fails **to a specific known wrong number**, so a green run proves
the fixture can detect the failure it is aimed at.

### 2.7 Scrubbing and fixture hygiene

Personal data is scrubbed **at capture, before the first commit** (FR-23,
fixtures policy rule 3), by `scripts/scrub_fixture.py`, which replaces phone
numbers with `+48 000 000 000` and seller names with `Jan Testowy` and prints a
diff for review. The scrub is enforced, not trusted:

```
tests/architecture/test_fixture_hygiene.py

  test_no_fixture_contains_a_phone_shaped_string
    regex over every file under tests/fixtures/:
      (?:\+48[\s ]?)?(?:\d[\s -]?){9}
    allowlist: exactly "+48 000 000 000"
    assert hits == []                     # prints (file, line, match) on failure

  test_no_fixture_contains_an_anchor_address_token
    tokens read from config/anchors.yml if present; skipped-with-reason if not

  test_fixtures_are_not_stale
    for every file under tests/fixtures/ NOT under a synthetic/ directory:
      assert capture date in the filename is within 180 days
    assert the scan visited at least one file per ENABLED source
      # the second assertion is what stops this test passing vacuously
      # while zero recorded fixtures exist

  test_every_structural_variant_in_the_pass_1_matrix_has_a_file
    the §8 matrix of 02-connectors.md, encoded as a table in this test;
    a missing file is reported as (source, variant), and a variant marked
    R-portal/R-host is reported as BLOCKED rather than MISSING
```

The last test turns pass 1's §8 matrix into something that fails when a variant is
forgotten, and — importantly — distinguishes *forgotten* from *gated*.

---

## 3. The politeness harness

Everything in this section runs with no network, no real clock and no database.
All three doubles live in `tests/support/`.

### 3.1 `FakeClock`

```python
# tests/support/clock.py
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

WARSAW = ZoneInfo("Europe/Warsaw")

class FakeClock:
    """The only source of time in ingest/. Never advances by itself."""

    def __init__(
        self,
        start_wall: datetime = datetime(2026, 8, 8, 2, 0, tzinfo=WARSAW),
        start_monotonic: float = 0.0,
    ) -> None:
        self._wall = start_wall            # tz-aware, always
        self._mono = start_monotonic
        self.sleeps: list[float] = []      # every sleep, in order, as requested

    def monotonic(self) -> float: ...      # returns self._mono
    def now(self) -> datetime: ...         # start_wall + elapsed monotonic
    def sleep(self, seconds: float) -> None:
        if seconds < 0: raise ValueError("negative sleep")
        self.sleeps.append(seconds)
        self.advance(seconds)
    def advance(self, seconds: float) -> None: ...
```

Four properties the harness itself is tested for, in
`tests/support/test_clock.py` — a broken double produces false greens everywhere
downstream:

| Test | Assertion |
|---|---|
| `test_monotonic_never_decreases` | 1 000 random `advance` calls; `all(t[i+1] >= t[i])` |
| `test_wall_and_monotonic_cannot_drift` | after `sleep(3600)`, `now() - start_wall == timedelta(seconds=3600)` and `monotonic() - 0.0 == 3600.0` |
| `test_sleep_records_what_was_asked_not_what_elapsed` | `sleep(6.6667)`; `clock.sleeps == [6.6667]` |
| `test_negative_sleep_is_a_bug_not_a_no_op` | `pytest.raises(ValueError)` |

Injection is structural, not conventional:

```
tests/architecture/test_time_is_injected.py

  test_no_module_under_ingest_reads_the_wall_clock_directly
    AST walk over src/lpc/ingest/:
      no time.sleep, time.monotonic, time.time,
      no datetime.now(), datetime.utcnow(), date.today()
    assert offenders == []      # prints (file, line, call)
  test_the_http_module_requires_a_clock_argument
    inspect.signature(HttpClient.__init__) has a required 'clock' parameter
```

### 3.2 `RecordingTransport` and the response script

```python
@dataclass(frozen=True)
class Call:
    t: float          # clock.monotonic() at request time
    method: str
    host: str
    path: str
    headers: dict[str, str]

class RecordingTransport:
    """Returns scripted responses; records every call. Never opens a socket."""
    def __init__(self, script: dict[tuple[str, str], list[Response]], clock: FakeClock): ...
    calls: list[Call]
    def content_calls(self) -> list[Call]:   # calls excluding /robots.txt
```

A script entry is keyed `(host, path)` and consumed in order, so
`[Response(429), Response(429), Response(200, body=...)]` expresses "two 429s then
success" without a server. Exhausting a script is an error, never a silent 404 —
`test_an_exhausted_script_is_an_error` pins that.

### 3.3 The 500-request run — exact timestamps

Config used by §3.3–§3.6 unless a test overrides it:

```yaml
# the config object the tests construct, not a committed file
rate_limit_rpm: 9            # → minimum interval 60/9 = 6.6666… s exactly
backoff:
  base_s: 1.0
  factor: 2.0
  max_attempts: 5            # 1 initial + 4 retries
  cap_s: 300.0
  jitter: none               # tests only; production injects Random(seed)
retry_after_max_s: 3600
window: "01:00-06:00 Europe/Warsaw"
```

**The composition rule, stated once and pinned by tests:** every wait is
`sleep(max(rate_limit_remaining_s, backoff_or_retry_after_s))`. There is exactly
one sleep per attempt. This is what makes 2.11 and 2.14 consistent instead of
contradictory (§9, refinement R3).

**Interval arithmetic.** The limiter computes slot *i* as
`t0 + i * Fraction(60, rpm)`, not by repeatedly adding a float — repeated addition
accumulates error and can dip below the minimum after a few hundred requests,
which is precisely the bug 2.9 exists to catch.

**Timestamps.** `/robots.txt` is a request to the host and consumes slot 0
(⟳ refines pass 1 2.9, which counted 500 total calls):

| Request | `clock.monotonic()` at request |
|---|---|
| `GET /robots.txt` | `0.0` ✎ |
| content #1 | `20/3 = 6.666666…` ✎ |
| content #2 | `40/3 = 13.333333…` ✎ |
| content #3 | `20.0` ✎ |
| content #4 | `80/3 = 26.666666…` ✎ |
| content #*i* | `i * 20/3` |
| content #500 | `10000/3 = 3333.333333…` ✎ |

```
tests/unit/ingest/test_rate_limit.py

  test_minimum_interval_holds_over_500_requests
    script: 1 robots (200) + 500 content (200)
    run the limiter to exhaustion
    assert len(transport.content_calls()) == 500
    assert len(transport.calls) == 501
    ts = [c.t for c in transport.content_calls()]
    diffs = [b - a for a, b in zip(ts, ts[1:])]
    assert min(diffs) >= 60/9 - 1e-9                 # not the mean — a burst hides in a mean
    assert sum(1 for d in diffs if d < 60/9 - 1e-9) == 0
    assert ts[0]  == pytest.approx(20/3,     abs=1e-9)
    assert ts[-1] == pytest.approx(10000/3,  abs=1e-6)   # no accumulated drift
    assert clock.monotonic() == pytest.approx(10000/3, abs=1e-6)
    assert max(diffs) <= 60/9 + 1e-6                 # and no gratuitous over-sleeping

  test_the_interval_test_catches_a_burst          # non-vacuity companion
    limiter configured with a deliberately broken "every 10th request is free" rule
    assert the assertions above FAIL
```

The `max(diffs)` bound is the half of this test people forget: a limiter that
sleeps 60 s between requests also satisfies "never below the minimum", and would
turn a 55-minute crawl into a 8-hour one.

### 3.4 Per-host, not global

```
  test_limit_is_per_host_not_global
    100 content requests alternating hosts A and B (50 each), plus one robots each
    A's content #i at i * 20/3;  B's content #i at i * 20/3   (independent schedules)
    assert min(diffs_A) >= 60/9 - 1e-9  and  min(diffs_B) >= 60/9 - 1e-9
    assert clock.monotonic() == pytest.approx(50 * 20/3, abs=1e-6)   # 333.333… s ✎
    global_equivalent = 101 * 20/3                                    # 673.333… s
    assert clock.monotonic() < 0.55 * global_equivalent
```

And its companion, which matters because "per host" is easy to fake by keying on
the full URL: `test_two_paths_on_one_host_share_a_limiter` — requests to
`https://h/a` and `https://h/b` interleaved still show `min(diffs) >= 60/9`.

### 3.5 Backoff — exact sequences

| Test | Script | `clock.sleeps` | Outcome |
|---|---|---|---|
| `test_429_backs_off_exponentially` (rpm **60**, interval 1.0) | `429, 429, 429, 429, 200` | `[1.0, 2.0, 4.0, 8.0]` ✎ | 5th attempt succeeds; `result.published is True` |
| `test_backoff_never_shortens_the_interval` (rpm 9, interval 6.667) | `429, 429, 429, 429, 200` | `[20/3, 20/3, 20/3, 8.0]` ✎ | the curve only wins once it exceeds the interval |
| `test_5xx_gives_up_after_max_attempts` | `503 × 5` | `[1.0, 2.0, 4.0, 8.0]` ✎ — four sleeps, five attempts, **no fifth sleep** | raises `SourceUnavailable`; `result.published is False`; prior day's `listing` row count and `max(observed_at)` unchanged ✎ |
| `test_the_cap_bounds_the_curve` (`max_attempts: 12`, `cap_s: 300`) | `429 × 12` | `[1, 2, 4, 8, 16, 32, 64, 128, 256, 300, 300]` ✎ | eleven sleeps, twelve attempts |
| `test_backoff_is_per_host` | host A `429×2` then `200`; host B all `200` | A sleeps `[1.0, 2.0]`; B's schedule untouched | B's `min(diffs) >= 60/9` still holds |
| `test_a_429_on_robots_backs_off_and_fetches_no_content` | `/robots.txt` → `429, 429, 200(allow-all)` | `[1.0, 2.0]` | `transport.content_calls()` is empty until robots succeeds ✎ |

`test_5xx_gives_up_after_max_attempts` also asserts `sum(clock.sleeps) == 15.0` ✎
— the total wait is a budget, and a budget nobody pins drifts.

### 3.6 `Retry-After` — the override matrix

Clock wall time for these tests: `2026-08-08T02:00:00+02:00` (= `00:00Z`).

| Header value | `clock.sleeps` | Notes |
|---|---|---|
| `Retry-After: 120` | `[120.0]` ✎ | Overrides the curve's `1.0` (pass 1 2.12) |
| `Retry-After: 1` (rpm 9) | `[20/3]` ✎ | `max()` rule — never faster than politeness |
| `Retry-After: 0` | `[20/3]` ✎ | Zero is not permission to hammer |
| `Retry-After: Sat, 08 Aug 2026 00:05:00 GMT` | `[300.0]` ✎ | HTTP-date form, resolved against `clock.now()` in UTC; asserted identically under `TZ=UTC` and `TZ=America/New_York` |
| `Retry-After: Sat, 08 Aug 2026 00:00:00 GMT` (now) | `[20/3]` ✎ | A past or present date floors to the interval, never negative |
| `Retry-After: soon` | `[1.0]` ✎ | Unparseable ⇒ fall back to the curve; `"retry_after_unparseable" in result.warnings` |
| `Retry-After: -5` | `[1.0]` ✎ | Same treatment |
| `Retry-After: 86400` | `[]` ✎ | Exceeds `retry_after_max_s`; raises `SourceUnavailable(reason="retry_after_exceeds_budget")` immediately, publishes nothing — we do not hold a crawl open for a day |

Plus the resumption test, which is where a naive limiter produces a burst:

```
  test_no_catch_up_burst_after_a_long_backoff
    Retry-After: 120 on content #1, then 10 successful responses
    assert clock.sleeps[0] == 120.0
    assert content #1 request t == 120.0 + 20/3      # the slot re-anchors to the retry
    ts = [c.t for c in transport.content_calls()]
    assert min(b - a for a, b in zip(ts, ts[1:])) >= 60/9 - 1e-9
    # a limiter that "owes" 18 slots after a 120 s wait would fire them back-to-back
```

### 3.7 The off-peak window (FR-4)

| Clock (Europe/Warsaw) | `runner.should_run()` |
|---|---|
| `2026-08-08 14:00` | `False` ✎ |
| `2026-08-08 02:00` | `True` ✎ |
| `2026-08-08 01:00:00` | `True` ✎ (inclusive lower bound) |
| `2026-08-08 06:00:00` | `False` ✎ (exclusive upper bound) |
| `2026-10-25 02:30` `fold=0` (CEST) and `fold=1` (CET) — the repeated hour | `True` for both ✎, and no exception |
| `2026-03-29 02:30` — the hour that does not exist | raises `NonexistentLocalTime` ✎, never silently shifted into peak hours |

The two DST rows are not pedantry: a scheduler that resolves a nonexistent local
time by shifting forward moves a crawl from 02:30 to 03:30 once a year, and a
scheduler that raises on the repeated hour skips a night's crawl once a year.
Both are F10.

### 3.8 Resumability (FR-1) — exact call sequence

```
  test_fetch_resumes_without_refetching_completed_pages
    script: /robots.txt 200, /szukaj?p=1 200, /szukaj?p=2 200, /szukaj?p=3 ConnectionError
    first run:
      assert [c.path for c in transport.content_calls()] == ["/szukaj?p=1", "/szukaj?p=2", "/szukaj?p=3"]  ✎
      assert raw_document row count == 2                    ✎ (only complete fetches stored)
      assert cursor.next_page == 3                          ✎
    second run, same cursor, script now serves pages 3–5:
      assert transport.content_calls()[0].path == "/szukaj?p=3"   ✎  (robots re-checked first)
      assert transport.calls[0].path == "/robots.txt"             ✎
      assert total raw_document rows == 5                          ✎
      assert no UNIQUE (source_id, url, content_hash) violation was swallowed
```

---

## 4. Parse purity — the mechanics

### 4.1 Installing the socket block

```python
# tests/support/no_network.py
import socket, ssl, pytest

class NetworkAccessAttempted(AssertionError): ...

@pytest.fixture(autouse=True)
def no_network(request, monkeypatch):
    if "allow_network" in request.keywords:      # opt-out for drills and live jobs
        yield; return
    def blocked(*a, **k):
        raise NetworkAccessAttempted(f"the test suite attempted network I/O: {a!r}")
    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket, "getaddrinfo", blocked)
    monkeypatch.setattr(ssl.SSLContext, "wrap_socket", blocked)
    yield
```

Three things about this that are easy to get wrong, each pinned by a test:

1. **Patch the methods, not `socket.socket` itself.** Replacing the class breaks
   `socketpair`, which pytest's own capture and several async runtimes use. The
   fixture therefore patches `connect`/`connect_ex`/`getaddrinfo`, leaving local
   socket pairs working.
2. **The monkeypatch is not sufficient on its own.** A module that did
   `from socket import create_connection` at import time holds its own reference.
   So the runtime block is backed by the static check (contract test 1.6): the
   names `httpx`, `requests`, `urllib.request`, `aiohttp`, `selenium`,
   `playwright` appear only in `src/lpc/ingest/http.py`, asserted as
   `offending_modules == []` with the offenders printed.
3. **The fixture must be proved to work.** Its non-vacuity companion:

```
tests/support/test_no_network.py

  test_the_no_network_fixture_actually_blocks
    with pytest.raises(NetworkAccessAttempted):
        httpx.get("http://127.0.0.1:9/")      # port 9 = discard, never listening
  test_the_fixture_can_be_opted_out_of        @pytest.mark.allow_network
    assert socket.getaddrinfo is the real one
```

### 4.2 The database poison

`parse` receives no session, so proving it does no DB I/O means poisoning the
*global* it could reach for:

```python
class PoisonedSession:
    def __getattr__(self, name):  raise DatabaseAccessAttempted(name)
    def __call__(self, *a, **k):  raise DatabaseAccessAttempted("session factory called")

@pytest.fixture
def poisoned_db(monkeypatch):
    monkeypatch.setattr("lpc.db.session.SessionLocal", PoisonedSession())
    monkeypatch.setattr("lpc.db.session.engine", PoisonedSession())
```

`test_parse_performs_no_io[<name>]` runs under `no_network` **and** `poisoned_db`,
and asserts the item count, not merely the absence of an exception — a `parse`
that returns `iter([])` would otherwise pass:

| Connector | Fixture | `len(list(parse(doc)))` |
|---|---|---|
| `gus_bdl` | `synthetic/by-unit_1415_land-sales.json` | `4` ✎ |
| `portal` | R‑portal | blocked — parametrisation skips with reason |
| `kowr` | R‑host | blocked |
| `auction` | R‑host | blocked |
| `gmina_bip` | R‑host | blocked |

Which is worth saying plainly: **today this test can only be green for one
connector**, and the skip manifest (§7.3) is what stops that from reading as
success.

### 4.3 The two-clock determinism check

```python
@pytest.mark.parametrize("name", CONNECTOR_NAMES)
def test_parse_is_deterministic_and_clock_free(name, doc):
    conn = registry[name]
    with time_machine.travel(datetime(2026, 1, 1, 0, 0, tzinfo=UTC), tick=False):
        a = list(conn.parse(doc))
    with time_machine.travel(datetime(2027, 6, 30, 23, 59, tzinfo=UTC), tick=False):
        b = list(conn.parse(doc))
    assert a == b
    assert [repr(x) for x in a] == [repr(x) for x in b]     # see §4.4
```

Four mechanics decisions behind those six lines:

- **`time_machine`, not `freezegun`.** It patches at the C level, so
  `time.time()` and `datetime.now()` reached through a C extension are also
  frozen. A parser calling `time.time()` must not slip through the check meant to
  catch it.
- **`tick=False`**, so the two runs are not merely different but *internally*
  frozen — a parser that computes a duration would otherwise get 0 in both and
  compare equal by luck.
- **The dates are 546 days apart and straddle a year boundary**, so a parser that
  defaults a missing year to "this year" produces `2026` in one run and `2027` in
  the other.
- **A third run under `TZ=America/New_York`** (a whole CI job, §7.2) catches naive
  local-time parsing, which two UTC-frozen runs cannot.

**The design consequence, which is the real output of this test:** a parser that
must resolve a relative date has nowhere to get "now" from except the document.

```
  test_relative_dates_resolve_against_doc_fetched_at
    doc.fetched_at = 2026-08-08T02:00+02:00, body says "dodano wczoraj"
    assert item.posted_at == date(2026, 8, 7)              ✎
    assert the same value under both frozen clocks and both TZ env values
  test_a_parser_with_no_fetched_at_cannot_resolve_a_relative_date
    RawDocument(fetched_at=None) is unconstructable — the dataclass field is required
```

### 4.4 Equality mechanics — why `==` is not enough

`Decimal("3000") == Decimal("3000.00")` is `True`, but the two are different
values for our purposes: one says "three thousand", the other says "three thousand
to the centiare". Every exactness assertion in this document therefore pins
`str(...)`, and the determinism test compares `repr` alongside `==`.

`ParsedItem` must be a **frozen dataclass with `eq=True`**, all money and area
fields `Decimal`, no `float` anywhere in the type. Pinned structurally:

```
tests/architecture/test_parsed_item.py

  test_parsed_item_is_frozen_and_comparable
    assert dataclasses.is_dataclass(ParsedItem) and ParsedItem.__dataclass_params__.frozen
  test_no_float_field_anywhere_in_the_parse_path
    typing.get_type_hints over ParsedItem and RawDocument:
      assert float not in the annotation of any field       ✎
    # a float price is a rounding bug waiting for a large number
```

### 4.5 Type guard at runtime

```
  test_parse_accepts_only_bytes_from_a_raw_document[<name>]
    with pytest.raises(TypeError):
        conn.parse("https://example.invalid/oferta/1")
  test_the_type_guard_is_runtime_not_an_annotation
    strip annotations (a subclass with __annotations__ = {}) and assert the
    TypeError still raises — mypy does not run at test time, so the check
    must be executable
```

---

## 5. Count agreement (V43) in exact terms

Pass 1 calls this "the highest-value single check in the ingestion path". Its
detail is where it can go wrong.

### 5.1 What the source's stated total looks like

In the synthetic corpus it is one element, verbatim:

```html
<p class="results-count">Znaleziono 248 ogłoszeń</p>
```

`parse_stated_total` returns a `StatedTotal(value: int, is_approximate: bool)`,
never a bare `int`. The forms it must handle, each its own one-line fixture under
`tests/fixtures/fake_source/counts/`:

| Input string | Expected |
|---|---|
| `Znaleziono 248 ogłoszeń` | `StatedTotal(248, False)` ✎ |
| `Znaleziono 1 ogłoszenie` | `StatedTotal(1, False)` ✎ |
| `Znaleziono 2 ogłoszenia` | `StatedTotal(2, False)` ✎ (Polish declension changes the noun, not the digits) |
| `Znaleziono 1 248 ogłoszeń` (U+00A0) | `StatedTotal(1248, False)` ✎ |
| `Znaleziono 1.248 ogłoszeń` | `StatedTotal(1248, False)` ✎ |
| `248 ofert` | `StatedTotal(248, False)` ✎ |
| `ponad 1 000 ogłoszeń` | `StatedTotal(1000, True)` ✎ |
| `około 250 ogłoszeń` | `StatedTotal(250, True)` ✎ |
| `Znaleziono 0 ogłoszeń` | `StatedTotal(0, False)` ✎ |
| (element absent) | `None` ✎ |
| `Strona 3 z 7` alone | `None` ✎ — a page count is not a result count, and reading it as one gives a shortfall of 241 |

**An approximate total never blocks publication.** `is_approximate=True` puts the
check in report-only mode: it writes `assertion_run(passed=True,
observed={"stated": 1000, "approximate": true, "collected": 987})` and raises no
alarm. Falsifying a real count against a rounded one manufactures alarms, and an
alarm that cries wolf is worse than no alarm.

For GUS the stated total is `"totalRecords": 250` — exact, never approximate. For
KOWR it is the index page's own figure (pass 1 uses 87), R‑host.

### 5.2 What "our extracted count" means

**Distinct `external_id`s emitted for the query**, not rows parsed. During a
55-minute crawl the source may re-sort under us, so the same advert can appear on
two pages (F6) — counting parsed rows would then *hide* a shortfall by
double-counting.

```
  test_our_count_is_distinct_external_ids_not_rows_parsed
    fixture _cross-page-duplicate.html: F0000041 on page 1 and page 2
    assert rows_parsed == 248                    ✎
    assert items_emitted == 247                  ✎   (distinct)
    assert result.cross_page_duplicates == 1     ✎
    assert the shortfall is computed on 247, not 248
```

### 5.3 The tolerance, with its boundary pinned

```
shortfall  = stated_total − distinct_emitted
allowance  = max(churn_abs_floor, ceil(churn_relative × stated_total))
alarm      = shortfall > allowance   or   distinct_emitted > stated_total + allowance
```

Proposed config (a threshold to ratify, **Q12** — pass 1's Q8 family):
`churn_relative: 0.02`, `churn_abs_floor: 3`.

| Stated | Collected | Shortfall | Allowance | Alarm | Note |
|---|---|---|---|---|---|
| 248 | 248 | 0 | 5 | no ✎ | nominal |
| 248 | 246 | 2 | 5 | no ✎ | pass 1's churn case |
| 248 | 243 | 5 | 5 | **no** ✎ | the boundary is inclusive |
| 248 | 242 | 6 | 5 | **yes** ✎ | one past the boundary |
| 248 | 120 | 128 | 5 | yes ✎ | truncated at page 3 of 7; `shortfall_ratio == pytest.approx(1 − 120/248, abs=1e-4)` |
| 248 | 72 | 176 | 5 | yes ✎ | pass 1's page-3-of-10 case |
| 20 | 17 | 3 | 3 | no ✎ | why the absolute floor exists — 2 % of 20 is 0.4 |
| 20 | 16 | 4 | 3 | yes ✎ | |
| 248 | 254 | −6 | 5 | **yes** ✎ | `corpus_overshoot` — collecting more than the source claims means the filter or the pagination is wrong |
| 248 | 0 | 248 | 5 | yes ✎ | `zero_items` fires too; both alarms, one block |
| 1000 (approx.) | 987 | 13 | 20 | no, report-only ✎ | approximate totals never alarm |
| `None` | 248 | — | — | `stated_total_missing`, **no block** ✎ | |

```
  test_the_tolerance_is_read_from_config_not_hardcoded
    churn_relative: 0.0, churn_abs_floor: 0
    assert the 246-of-248 case now alarms       ✎
    # the test that stops the tolerance being a magic number in the source
```

### 5.4 Churn during the crawl

A 7-page crawl at 9 rpm spans about 47 seconds of requests but sits inside a
55-minute run; the stated total genuinely moves. Rule: **the first page's total
is authoritative**, the last page's total is recorded as drift, and the allowance
is widened by the drift's magnitude.

```
  test_stated_total_drift_widens_the_allowance_and_is_recorded
    fixture _stated-total-drift: page 1 says 248, page 7 says 251
    collected 249
    assert result.stated_total == 248                 ✎
    assert result.stated_total_drift == 3             ✎
    assert result.alarms == []                        ✎   (allowance 5 + 3)
    assert assertion_run.observed == {"stated_first": 248, "stated_last": 251,
                                      "collected": 249, "allowance": 8}   ✎
  test_large_drift_is_itself_an_alarm
    page 1 says 248, page 7 says 800
    assert "stated_total_unstable" in result.alarms    ✎
    # the query is not stable enough to be a completeness oracle at all
```

### 5.5 What an alarm does

| Condition | Alarm | `published` | `assertion_run` row |
|---|---|---|---|
| Shortfall beyond allowance | `corpus_incomplete` | `False` | `passed=False, blocked_publication=True` |
| Overshoot beyond allowance | `corpus_overshoot` | `False` | `passed=False, blocked_publication=True` |
| Approximate stated total | — | `True` | `passed=True`, observed records the comparison |
| No stated total | `stated_total_missing` | `True` | `passed=False, blocked_publication=False` |
| Unstable stated total | `stated_total_unstable` | `False` | `passed=False, blocked_publication=True` |
| Zero items, prior run 200 | `zero_items` | `False` | `passed=False, blocked_publication=True` |
| Zero items, first ever run | — | `False` | no row — nothing to drift from (pass 1 §1.2) |

`published is False` must be proved by absence, not by a flag:
`count(metric_unit_month rows written) == 0` ✎ and `count(listing rows written) ==
0` ✎ in every blocking row above.

---

## 6. Per-test input and expected output

Pass 1's sequence, with the input each test is handed and the value it pins.
Tests already given in full above are cross-referenced rather than repeated.

### 6.1 §1 — the connector contract

| # | Input | Expected output |
|---|---|---|
| 1.1 | the production registry | `set(registry) == {"gus_bdl","portal","kowr","auction","gmina_bip"}` ✎ |
| 1.2 | each class | `name: str`; `kind in {"portal","registry","api"}`; `fetch(since: datetime\|None)`, `parse(doc: RawDocument)`, `emit(items)`; `__init__` has a required `client` parameter |
| 1.3 | §4.2 table | item counts per connector; `gus_bdl` → `4` ✎ |
| 1.4 | §4.3 | two frozen clocks × two `TZ` values, `a == b` and `repr` equal |
| 1.5 | `"https://…"` | `TypeError` ✎, also with annotations stripped |
| 1.6 | AST of `src/lpc/` | `offending_modules == []` ✎ |
| 1.7 | AST of `src/lpc/` | no `Client(`/`Session(` outside `ingest/http.py` ✎ |
| 1.8 | text scan of `src/lpc/ingest/` | `metric_unit_month`, `metric_index`, `valuation_log` occur 0 times ✎ |
| 1.9 | each class | no `is_healthy`/`should_publish` attribute; `IngestResult` fields exactly `{items_emitted, parse_failures, parse_failure_rate, stated_total, stated_total_drift, shortfall_ratio, cross_page_duplicates, list_detail_disagreements, alarms, published, warnings}` ✎ |
| 1.2b | `FakeConnector`, `BadConnector` | the teeth test of §2.3 |

Health (§1.2 of pass 1), against the fake corpus:

| Test | Input | Expected |
|---|---|---|
| zero items, prior 200 | `_zero-items.html`, `source.last_item_count = 200`, floor 10 | `items_emitted == 0` ✎; `"zero_items" in alarms`; `publish_called is False`; 0 metric rows; 0 listing rows; `assertion_run(passed=False, blocked_publication=True)` |
| zero items, first run | same page, `last_item_count IS NULL` | `alarms == []` ✎, `published is False` ✎ |
| full drift | `_drift-renamed-price.html` | `parse_failure_rate == 1.0` ✎, `schema_drift`, `items_emitted == 0` ✎, no insert attempted with a null price |
| partial failure | 40 items, 1 unparseable | `items_emitted == 39` ✎, `parse_failure_rate == pytest.approx(0.025)` ✎, `alarms == []` ✎ |
| threshold boundary | 40 items, 4 unparseable, threshold 0.10 | `parse_failure_rate == 0.10`, `alarms == []` ✎ (inclusive) |
| threshold exceeded | 40 items, 5 unparseable | `parse_failure_rate == 0.125`, `schema_drift` ✎ |

### 6.2 §2 — robots and rate limiting

Fully specified in §2.1 (semantics table) and §3.3–§3.7 (timings). The two
remaining assertions:

| # | Input | Expected |
|---|---|---|
| 2.1 | any fetch | `transport.calls[0].path == "/robots.txt"` ✎ and `len(transport.calls) == 1` before the first yield ✎ |
| 2.7 | `disallow-oferta.txt` | `connector.mode == "list_only"` ✎; every emitted item has `detail_fetched is False` ✎; and (per pass 1 §0.3) every detail-only attribute is `unknown` and flagged, never inferred from the list page |
| 2.8 | text scan of `src/lpc/ingest/` | zero hits for `password`, `login(`, `set_cookie`, `captcha`, `undetected`, `stealth`, `selenium`, `playwright`; asserted as `hits == []` with `(file, line)` printed |

### 6.3 §3 — GUS BDL

Inputs and expected values are the fixture tables of §2.2. Three tests need their
input spelled out beyond the fixture:

| # | Input | Expected |
|---|---|---|
| 3.1 | `cfg.land_sales_var_id = 633712`, `unit = "1415"`, `page = 0` | the exact URL string ✎; then `cfg.land_sales_var_id = 999999` and re-check — the id must move with the config, proving it is not hardcoded; plus the new mapping test of §2.2 |
| 3.4 | nominal fixture, `lastUpdate 2026-05-20`, period `2025-Q4` | `transacted_at == date(2025,12,31)` ✎, `as_of == date(2026,5,20)` ✎, `as_of > transacted_at`; the swap `as_of=2025-12-31, transacted_at=2026-05-20` raises `IntegrityError` on `published_after_transacted` ✎ |
| 3.5 | nominal fixture | identical `transacted_at` under `TZ=UTC`, `TZ=America/New_York`, `TZ=Europe/Warsaw` ✎ |
| 3.9 | after `emit` | every row `price_type == "sales"` ✎, `as_of` non-null, `len(source_ids) >= 1`; inserting the same row with `price_type='offering'` raises the CHECK ✎ |
| 3.10 | `emit` twice | row count unchanged ✎; no duplicate `(teryt_unit, transacted_at, property_kind)` ✎ |
| 3.11 | fixture missing powiat `2804` | assertion fails; `observed == {"missing": ["2804"]}` ✎ — the code, not just a count |
| 3.13 | ratio 2.4 with `band: null` | `passed is True`, `observed == {"ratio": 2.4}` ✎; then ratio 0.8 with `band: [1.05, 2.5]` → `passed is False`, `reason == "offering_below_sales"` ✎ |

### 6.4 §4 — the portal (R‑portal, blocked on O10)

§4.1 (raw store) and §4.3 (snapshots) run **now** against the fake corpus; §4.4
onward do not exist as files until O10 resolves.

Raw store, exact:

| Test | Input | Expected |
|---|---|---|
| hash and provenance | `store(b"<html>abc</html>", url=".../szukaj?p=1", fetched_at=T)` | `row.content_hash == hashlib.sha256(b"<html>abc</html>").hexdigest()`, pinned as the literal `"c0f...".` transcribed once ✎; `row.url`, `row.fetched_at == T`, `row.source_id` |
| identical refetch | store the same bytes twice | row count `1` ✎; flip one byte → `2` ✎ |
| changed page | two versions | `len({r.content_hash}) == 2` ✎, both `fetched_at` values survive ✎ |
| reparse equality | `parse(doc_from_fetch)` vs `parse(load_raw(row.id))` | equal lists, and equal `repr` ✎ |
| reparse drill | a window ingested with areas ÷ 10, then fixed | `median_ppm2` moves `631.0 → 63.1` ✎; `listing_snapshot` checksum byte-identical ✎; `generation == 2` exists and generation 1 survives ✎ |

Snapshots (V12), with the exact three-day series:

| Day | Event | Expected snapshot row |
|---|---|---|
| d1 | X active at 189 000 | `(d1, Decimal("189000.00"), True)` ✎ |
| d2 | X active at 179 000 | `(d2, Decimal("179000.00"), True)` ✎ |
| d3 | X absent from the corpus | `(d3, Decimal("179000.00"), False)` ✎ — last known price, `is_active False` |

`len(snapshots(X)) == 3` ✎; `price_changes(X) == [(d2, 189000, 179000)]` ✎;
after d3 the row count is unchanged and `listing.is_active is False` ✎; a d5
relisting under the same `external_id` keeps `cluster_id` and adds a 4th snapshot
✎; skipping d2 entirely yields **no** row for d2 ✎, `boundary_uncertainty is
True` ✎ and no invented price; `UPDATE listing_snapshot …` as `app_pipeline`
raises `InsufficientPrivilege` ✎.

Blocked rows, recorded so the gap is visible rather than forgotten:

| Pass 1 test | Blocked on | What the capture must supply |
|---|---|---|
| 4.4 all | O10 + O1 | the list page's markup for id, price, area, url, active state |
| 4.5 all | O10 + O1 | the stated-count phrase, verbatim, from page 1 **and** the last page |
| 4.6 all | O10 + O1 | list and detail page pairs with at least one price disagreement |
| 4.7 three-day | O10 + O1 | a real three-day capture — a hand-written one proves nothing |
| 4.8 sort order | O10 + O1 | two live crawls; only the alarm arithmetic is testable offline, against two hand-built samples with medians `55.0` and `78.0` ✎ |

### 6.5 §5 — KOWR (R‑host)

Values from pass 1, marked provisional until capture. The area arithmetic is
**not** blocked — it is unit conversion over strings, tested against the phrase
fixtures:

| Input | Expected `area_m2` |
|---|---|
| `1,2400 ha` | `Decimal("12400.00")` ✎ |
| `0,1500 ha` | `Decimal("1500.00")` ✎ |
| `15 a` | `Decimal("1500.00")` ✎ |
| `12 arów` | `Decimal("1200.00")` ✎ |
| `1500 m²` | `Decimal("1500.00")` ✎ |
| `1,24` | quarantine `area_unit_missing` ✎ — assert none of `1.24`, `124`, `12400` appears; assuming hectares here is a 10 000× error |

`parse("0,15 ha") == parse("15 a") == parse("1500 m²")` ✎ — the metamorphic form,
which catches a converter that is right for one unit and wrong for another.

TERYT (5.8): the notice names *Skierniewice*; expected `teryt_gmina ==
"1015052"` (rural gmina) ✎, **not** `"1062011"` (the city), plus a static scan
asserting no `WHERE name =` gmina lookup exists in the connector ✎.

V46 (5.12, 5.13): the fixture and every number are in §2.6.

### 6.6 §6 — auctions

The fraction arithmetic is fully specified in §2.4 and is **writable and greenable
now** against phrase fixtures — which is a change from pass 1's "not greenable
until O16" (§9, refinement R5). What O16 still blocks: which element of which
document the phrase is extracted from, and the count-agreement fixture.

| # | Input | Expected |
|---|---|---|
| 6.7 | any auction item | `price_kind == "auction_start"` ✎; `price_type == "offering"` (D65) ✎; `price_kind` is a required constructor argument — omitting it raises `TypeError` ✎ |
| 6.8 | `phrases/date.txt` | `datetime(2026,9,12,10,0, tzinfo=ZoneInfo("Europe/Warsaw"))` ✎, under three `TZ` values |
| 6.9 | `phrases/no-date.txt` | quarantine `auction_date_missing` ✎ |
| 6.10 | auction dated `2026-07-01`, `now = 2026-08-08` | `is_supply is False` ✎; row retained ✎; excluded from the active-supply count and included in the historical one ✎ |
| 6.11 | `101505_2.0012.123/4` | `parcel_identifier == "101505_2.0012.123/4"` ✎ and `statutory_fraction is None` (the parcel-trap case of §2.4) |
| 6.12 | `0,3000 ha`, `3 000 m²` | both `Decimal("3000.00")` ✎, and equal to each other |
| 6.13 | no coords, parcel id present | `location_precision == "parcel"` after resolution ✎, `geom is None` at parse time ✎ |
| 6.14 | §2.6 fixture | asking median `Decimal("80.00")`, `n == 20`; `auction_start` aggregate `n == 5`, median `Decimal("30.00")`; blended control `Decimal("75.50")` |
| 6.16 | layout registry | every layout has ≥ 1 dated fixture; every fixture directory has a layout; **plus** the non-vacuity companion of §2.5 |

### 6.7 §7 — gmina BIP

Coverage first (7.1–7.5), and all five are **S** — they run against
`rings_gminas.json` and the parser registry, with no BIP markup involved.

| # | Input | Expected |
|---|---|---|
| 7.1 | manifest + registry | `covered ∪ uncovered == set(manifest.gminas)` ✎; `covered ∩ uncovered == ∅` ✎; count asserted against `len(manifest.gminas)`, never a literal |
| 7.2 | the uncovered list | every entry has a non-empty reason ✎; reasons ⊆ `{no_bulletin_found, pdf_scan_no_text, layout_unsupported, robots_disallowed, requires_js}` ✎; an unknown reason string fails ✎ |
| 7.3 | an uncovered gmina | `coverage.status == "uncovered"` ✎; `coverage.listings_active is None` ✎; the render helper emits `"brak parsera"` and the string `"brak ogłoszeń"` does **not** appear ✎ |
| 7.4 | a covered gmina with no notices | `status == "covered"`, `listings_active == 0` ✎, `last_crawl_at` not null ✎ |
| 7.5 | Δ assertion | `covered_count_in_report == len(parser_registry)` ✎; dropping a parser without updating the report fails ✎ |
| 7.13 | manifest + one synthetic gmina | 7.1 fails until the new gmina is classified ✎ — the staleness guard |
| 7.10 | transport raises for gmina A | gmina B's rows emitted ✎; A marked `failed` ✎; `published` is per-gmina ✎ |
| 7.12 | any BIP item | `price_kind == "tender"` ✎, `price_type == "offering"` ✎; a BIP row cannot enter an asking aggregate (§2.6) |

**The first green state is `50 gminas, 0 covered, 50 uncovered with reasons`** —
honest and publishable. 7.6–7.9 and 7.11 need R‑host fixtures.

Area arithmetic (7.7) is **S** and green now: `15 a`, `15 arów`, `0,15 ha`,
`1500 m²` all → `Decimal("1500.00")` ✎, asserted equal to one another.

---

## 7. CI wiring

### 7.1 Markers

```ini
# pyproject.toml [tool.pytest.ini_options]
markers = [
  "requires_recorded_fixture(source): needs a fixture recorded from a live source",
  "live: performs real network I/O; never runs in the commit pipeline",
  "slow: benchmarks and drills",
  "allow_network: opts out of the no_network autouse fixture",
]
addopts = "--strict-markers -m 'not live and not slow'"
```

A test whose fixture does not exist yet is `@pytest.mark.requires_recorded_fixture("portal")` and
**skips with a reason naming the gate**, e.g.
`skip("blocked on O10 — no portal fixture may be recorded")`. It is never
deleted, never `xfail`, and never quietly commented out.

### 7.2 Jobs

| Job | Trigger | Runs | Notes |
|---|---|---|---|
| `unit` | every commit | `tests/unit`, `tests/architecture` | No DB, no network. Whole-suite budget: under 60 s |
| `unit-tz` | every commit | the same suite with `TZ=America/New_York` | Makes 1.4, 3.5, 6.8 and §3.7 real rather than decorative |
| `integration` | every commit | `tests/integration` against a Postgres service container | Migrations applied fresh; DB grants tested as `app_pipeline` |
| `hash-seed` | every commit | `tests/unit` with `PYTHONHASHSEED=random` | Order-independence (the permutation metamorphic property) |
| `fixture-hygiene` | every commit | §2.7 | Cheap; catches a personal-data leak before it is in history |
| `skip-manifest` | every commit | §7.3 | Fails when the blocked set changes without a documented reason |
| `mutation` | weekly | `mutmut` over `src/lpc/ingest/` and the numeric core (V52) | Not per-commit; it is minutes, not seconds |
| `live-politeness` | nightly, after O10 | V44 sort-order comparison, V58 sampled reconciliation | `-m live`, real hosts, inside the off-peak window |
| `freshness` | daily | the `⏱` half of V8 — every connector's last success within its cadence | Reads production data, not fixtures |
| `anchor-scan` | pre-push hook | V7(b), the git-history scan | Cannot run in CI: shallow clones lack the history |

The commit pipeline is **fully offline**. Nothing in it fetches, and the
`no_network` fixture means nothing in it *can*.

### 7.3 Making the blocked set visible

The failure mode this repo is most exposed to is a suite that is green because
most of it is skipped.

```
tests/architecture/test_skip_manifest.py

  test_the_blocked_set_matches_the_recorded_gates
    collect every test marked requires_recorded_fixture
    group by source
    compare to docs/evidence/blocked.md, which lists (source, gate, count)
    assert they match exactly; on mismatch print the added/removed tests
    # a newly blocked test must be recorded deliberately, not accumulate silently

  test_the_recorded_capture_matches_the_synthetic_envelope
    @pytest.mark.requires_recorded_fixture("gus_bdl")
    load the recorded BDL response and the synthetic one
    assert the JSON key sets at every level are equal
    # if GUS's envelope differs from our synthetic contract, that IS the finding,
    # and every synthetic fixture is regenerated from the capture

  test_the_robots_evidence_check_is_not_vacuous
    no source is enabled today, so §0.4's test passes over an empty set
    flip one source to enabled: true in a temp config
    assert test_every_enabled_source_has_recorded_robots_evidence FAILS
```

`docs/evidence/blocked.md` starts as:

| Source | Gate | Blocked tests |
|---|---|---|
| portal | O10, then O1 | §4.4–§4.8 |
| kowr | Q9 (host robots evidence) | §5 document parses |
| auction | Q9 + O16 | §6 document parses (**not** the fraction arithmetic) |
| gmina_bip | Q9 | §7.6–§7.11 |
| gus_bdl | Q7 (variable IDs) | 3.2 value pinning, 3.12 hand-check |

### 7.4 What is green when

| Milestone | Turns green |
|---|---|
| **Today, offline** | §1 contract (parametrised, `gus_bdl` param only), §2 robots and limiter in full, §4.1 raw store, §4.3 snapshots, §1.2 health, §5 count-agreement arithmetic, §6.1 fraction arithmetic, §7.1–§7.5 and §7.13 coverage registry, §2.6 V46 separation, all architecture tests |
| **After Q7** (BDL variable IDs recorded) | 3.2, 3.12, and the envelope-match test |
| **After Q9** (per-host robots evidence) | §5 KOWR document parses, §7.6–§7.11 BIP layouts |
| **After Q9 + O16** | §6 document parses, 6.15, 6.16 with real layouts |
| **After O10 + O1** | §4.4–§4.7; §4.8 remains live-only |

Roughly two-thirds of the tests in pass 1 are writable **and** greenable before
any gate opens — which is the answer to "should we wait for O10 before starting".

---

## 8. Order of work, refined

Pass 1 §12's order stands, with one change: the auction **fraction** work moves
ahead of KOWR, because §2.4 showed it needs no recorded fixture at all and it is
the highest-risk arithmetic in the connector layer.

1. `tests/support/` — `FakeClock`, `RecordingTransport`, `no_network`,
   `PoisonedSession`, and the four harness self-tests of §3.1. Nothing else is
   trustworthy until these are.
2. §1 contract + `BadConnector` teeth test.
3. §2 / §3 robots and limiter, against the nine `robots.txt` fixtures.
4. §4.1 raw store, §4.3 snapshots, §1.2 health — all against the fake corpus.
5. §5 count-agreement arithmetic and §2.6 V46 separation.
6. §6.1 auction fraction arithmetic, against the phrase fixtures.
7. §3 GUS BDL, synthetic first, recorded when Q7 closes.
8. §7.1–§7.5 BIP coverage registry.
9. Everything gated, in gate order: Q9 → KOWR and BIP layouts; O16 → auction
   documents; O10 → portal.

---

## 9. Where this refines pass 1

| # | Pass 1 said | This plan says | Why |
|---|---|---|---|
| **R1** | 2.9: `len(transport.calls) == 500` | `len(content_calls) == 500`, `len(calls) == 501` | `/robots.txt` is a request to the host and consumes a slot; pretending otherwise makes the arithmetic wrong by one interval |
| **R2** | 2.9 asserts only `min(diffs) >= 6.666` | also `max(diffs) <= 60/9 + 1e-6` and no accumulated drift at request 500 | A limiter that sleeps a minute between requests also passes "never below the minimum" |
| **R3** | 2.11 `sleeps == [1,2,4,8]` and 2.14 "never shortens the interval" | one composition rule, `sleep(max(interval_remaining, backoff))`; 2.11 runs at rpm 60 so the curve dominates, 2.14 at rpm 9 so the interval does | As written the two tests contradicted each other at rpm 9 |
| **R4** | V43 compares "rows emitted" to the stated total | compares **distinct `external_id`s**, and adds the overshoot alarm | Cross-page duplicates during a re-sort would mask a shortfall |
| **R5** | §6 is "writable but not greenable until O16" | the **fraction arithmetic** is greenable now against statutory phrase fixtures; only the document-level extraction waits on O16 | The wording of a *cena wywoławcza* clause comes from the Code of Civil Procedure, not from a website |
| **R6** | §9 marks KOWR and BIP fixtures "✓ recordable now" | blocked on **Q9** — per-host `robots.txt` evidence, which §0.4 requires and which nobody has recorded | §0.4 and §9 of pass 1 contradicted each other |

---

## 10. New questions this pass raised

Per rule 3, asked rather than assumed. O-numbers are allocated only in
[`00-decisions.md`](../../00-decisions.md), so these carry local Q-numbers until
they are.

| # | Question | Blocks | Proposal on the table |
|---|---|---|---|
| **Q9** | **Who records `robots.txt` evidence for KOWR, the auction service and the ~50 BIP hosts, and when?** §0.4 makes it a precondition of fetching; §9 assumed it was done | Every KOWR, auction and BIP fixture | An afternoon's work, same procedure as O10 — but it must actually happen before anything is recorded |
| **Q10** | Is a `robots.txt` with **no recognisable group** a disallow, or an allow-all? | The `unparseable.txt` row of §2.1 | Fail closed, consistent with 2.4 (missing ≠ permission) and 2.5 (5xx ⇒ disallow). Individual malformed *lines* are still dropped per RFC 9309 |
| **Q11** | The `fraction_consistent` tolerance | §2.4 | `≤ 1,00 zł`, because notices round to the full złoty. A larger tolerance would swallow a real mismatch; a smaller one would flag every 2/3 notice |
| **Q12** | V43 churn tolerance (pass 1's Q8, made concrete) | §5.3 | `max(3, 2 % of stated)`. The absolute floor exists because 2 % of a 20-result query is 0.4 |
| **Q13** | Does a `Retry-After` longer than an hour end the run, or is it honoured? | §3.6 | End the run — `SourceUnavailable`, publish nothing. Holding a crawl open for a day is indistinguishable from a hang |
| **Q14** | What does BDL call our units? The URL in 3.1 uses TERYT `1415`, the envelope uses `011415000000` | 3.1, 3.2, the coverage assertion | Record the TERYT → BDL-unit-id mapping in config as data; never derive it by string surgery |
| **Q15** | Does an **approximate** stated total ("ponad 1 000") ever block publication? | §5.1, §5.3 | No — report-only. An alarm that cries wolf is worse than no alarm, and rounding is not shortfall |
