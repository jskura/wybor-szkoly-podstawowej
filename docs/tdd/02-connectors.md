# TDD specification — the ingestion connectors

Covers [`18-v0-scope.md`](../18-v0-scope.md) §6 work items **4** (GUS BDL),
**5** (portal), **7** (KOWR), **8** (auctions) and **13** (gmina BIP).

Rules in force: [`CLAUDE.md`](../../CLAUDE.md) rule 4 (PRD → validation method →
failing test → implementation → passing test) and rule 5 (a validation method
before implementation). The methods already exist — V8, V13, V14, V43, V44, V46,
V53, V54, V55, V57, V58 — so this document is the layer between them and the
keyboard: **the order the tests are written in, and the exact assertion each one
makes**.

Per [`20-verification-strategy.md`](../20-verification-strategy.md) §1, an
assertion that only checks "a number came back" is worthless here. Every test
below pins **a specific value or a specific relationship**.

---

## 0. The blocking gate — work item 0 (O10)

Work item 0 is *"open each candidate portal's `/robots.txt`, record the verbatim
text and the date in `docs/evidence/`"*. It is a **human gate**, it is unresolved,
and it decides whether work item 5 exists at all
([`03-data-sources.md`](../03-data-sources.md) §"Unverified gate").

### 0.1 What can be written before it resolves

Everything that does not depend on a **recorded fixture from a real portal**:

- all of §1 (the connector-contract tests) — they run against any connector,
  including the three off-portal ones;
- all of §2 (robots and rate limiting), because those tests use **hand-written
  `robots.txt` fixtures and a fake transport**, never a live host;
- all of §3 (GUS BDL) — a public API, no crawl gate;
- all of §5, §6, §7 (KOWR, auctions, BIP) — subject to their **own** robots
  evidence, see §0.4.

### 0.2 What cannot be written until it resolves

| Blocked | Why |
|---|---|
| §4.4 portal parse tests (`test_parse_list_page_pins_first_item` and the whole variant set) | They pin values from a fixture of **the chosen portal's** markup, and no fixture may be recorded before the gate |
| §4.5 corpus-completeness tests (V43) | The stated-result-count string is portal-specific text |
| §4.6 list/detail reconciliation (V58) | Needs both page kinds from the real portal; also needs a live sample to set the disagreement threshold |
| §4.7 snapshot three-day fixture (V12) | Must be a real three-day capture, not a hand-written one, or it proves nothing about the portal |
| §4.8 sort-order independence (V44) | Inherently a **live** comparison run — two crawls of the same query. Only its alarm logic can be tested offline |
| Portal choice (O1) | *"whichever permits crawling wins"* — O1 is downstream of O10 |

Writing these against invented markup would be worse than not writing them: a
green test against a fixture that does not resemble the source is the false green
[`04-validation.md`](../04-validation.md) §Fixtures policy rule 5 exists to
prevent.

### 0.3 The three branches, and what each does to this document

| O10 outcome | Effect |
|---|---|
| **Allowed** | §4 proceeds as written |
| **Disallowed** | §4 is **deleted**. Items 4, 7, 8, 13 stand alone; V43, V44, V58 and V12's portal case become moot; V16 loses its offering side and the whole cross-source check with it. That is the smaller product `03` describes, and the decision to accept it is the owner's |
| **Partially allowed** (list yes, detail no) | §4.4–§4.7 survive in `list_only` mode. §4.6's reconciliation is **unrunnable** — there are no detail pages to reconcile against — and is replaced by `test_list_only_mode_marks_attributes_unavailable`, asserting that every attribute that would have come from a detail page is `unknown` and flagged, never inferred from the list page |

### 0.4 The gate generalises to every host — still blocking

Item 0 named the portals. The same gate covers three more source families: KOWR,
the two auction sources (D111) and the ~50 BIP hosts. A connector may not fetch
from a host whose `robots.txt` nobody recorded. The gate is testable rather than
remembered — `source.robots_ok` defaults to `FALSE` in
[`15-database-schema.md`](../15-database-schema.md) §4:

```
tests/architecture/test_robots_evidence.py

  test_every_enabled_source_has_recorded_robots_evidence
    for each source in config/sources.yml where enabled is true:
      assert (docs/evidence/robots/<host>.txt) exists
      assert its first line records a capture date within the last 180 days
      assert source.robots_ok is True in the seeded source row
  test_a_source_without_evidence_cannot_be_fetched
    seed source with robots_ok = False
    assert runner raises RobotsEvidenceMissing before any transport call
    assert transport.calls == []
```

This is the gate made structural: a connector cannot be run for a host whose
`robots.txt` nobody recorded.

**Two robots rules, stated separately (D92).**

1. A **missing** `robots.txt` is not permission. The runner stops. This is our
   own rule, and it is stricter than the RFC.
2. A **served** `robots.txt` that parses to **no matching group** is an allow.
   RFC 9309 says so.

The asymmetry is deliberate. The tests state each rule on its own, and no test
derives one rule from the other. Test 2.4 covers rule 1. Test 2.4b covers
rule 2.

---

## 1. The connector contract — tests that apply to all six

[`16-repository-layout.md`](../16-repository-layout.md) §2 states three stages and
four rules. Each rule gets a test, parametrised over the connector registry so a
seventh connector added later inherits them automatically. **These are written
first, before any individual connector**, because they are what makes the drift
alarm generic.

D111 builds both auction sources, so the registry holds **six** connectors. The
central e-auction service and the bankruptcy gazette are separate hosts with
separate documents, so each one is a connector and each one needs its own robots
evidence under §0.4.

Location: `tests/architecture/test_connector_contract.py`,
`tests/unit/ingest/test_contract_parametrised.py`.

### 1.1 Red-green sequence

| # | Test | Assertion | Discharges |
|---|---|---|---|
| 1.1 | `test_registry_lists_every_connector` | `set(registry) == {"gus_bdl","portal","kowr","auction_central","auction_gazette","gmina_bip"}` (D111) — a new connector must be registered or this fails, which is what keeps 1.2–1.9 exhaustive | contract |
| 1.2 | `test_connector_satisfies_protocol[<name>]` | The class has `name`, `kind ∈ {portal,registry,api}`, and `fetch`/`parse`/`emit` with the signatures in `16` §2 | contract |
| 1.3 | `test_parse_performs_no_io[<name>]` | Under the `no_network` autouse fixture (patches `socket.socket` to raise `AssertionError`) **and** a DB session double whose every attribute access raises, `parse(fixture_doc)` returns the expected item count. No exception ⇒ no I/O | V57, `16` §2 rule 2 |
| 1.4 | `test_parse_is_deterministic_and_clock_free[<name>]` | `parse(doc)` called twice, under two different frozen clocks (`2026-01-01` and `2027-06-30`), returns **equal** item lists. Catches a `datetime.now()` inside `parse`, which would make re-parsing (V42/V57) irreproducible | V57 |
| 1.5 | `test_parse_accepts_only_bytes_from_raw_document[<name>]` | `parse` takes a `RawDocument`; passing a URL string raises `TypeError`. A parser that can be handed a URL will eventually fetch it | `16` §2 rule 2 |
| 1.6 | `test_only_the_shared_http_module_imports_an_http_library` | AST walk over `src/lpc/`: the names `httpx`, `requests`, `urllib.request`, `aiohttp`, `selenium`, `playwright` appear **only** in `src/lpc/ingest/http.py`. Asserted as `offending_modules == []`, printing the offenders | V14, `16` §2 rule 3 |
| 1.7 | `test_no_connector_constructs_a_client` | No `Client(`/`Session(` construction outside `ingest/http.py`; every connector receives its client by injection (constructor parameter present in 1.2's signature check) | V14 |
| 1.8 | `test_connector_never_writes_metric_or_valuation_tables` | AST/text scan of `src/lpc/ingest/`: the tokens `metric_unit_month`, `metric_index`, `valuation_log` do not occur | `16` §2 rule 5 |
| 1.9 | `test_connector_does_not_decide_its_own_health[<name>]` | The connector class has **no** `is_healthy`/`should_publish` attribute; `IngestResult` carries `items_emitted`, `parse_failures`, `parse_failure_rate`, `stated_total`, `alarms` | V8, `16` §2 rule 4 |

### 1.2 The zero-item rule (V8) — the one that must never be skipped

```
tests/unit/ingest/test_source_health.py

  test_zero_item_run_alarms_and_publishes_nothing[<name>]
    seed source.last_item_count = 200, floor = 10
    feed the connector an empty fixture (a valid page listing no items)
    assert result.items_emitted == 0
    assert "zero_items" in result.alarms
    assert runner.publish_called is False
    assert count(metric_unit_month rows written) == 0
    assert count(listing rows written) == 0
    assert count(notice rows written) == 0          # D91: the second target table
    assert assertion_run row exists with passed=False, blocked_publication=True

  test_zero_items_on_a_first_ever_run_does_not_alarm
    source.last_item_count is NULL
    assert result.alarms == []          # nothing to drift from yet
    assert result.published is False    # but still publishes nothing

  test_parse_failure_rate_above_threshold_alarms_instead_of_nulling[<name>]
    fixture mutated: the price field renamed (see §8, *_drift-renamed-price.*)
    assert result.parse_failure_rate == 1.0
    assert "schema_drift" in result.alarms
    assert result.items_emitted == 0
    assert no row with price_pln IS NULL was attempted

  test_partial_parse_failure_below_threshold_still_records_the_rate
    fixture: 40 items, 1 unparseable
    assert result.items_emitted == 39
    assert result.parse_failure_rate == pytest.approx(0.025)
    assert result.alarms == []
```

The fourth test is the guard against the opposite failure — an alarm so eager that
one malformed advert stops the pipeline.

### 1.3 Resumability (FR-1)

```
  test_fetch_resumes_without_refetching_completed_pages
    transport raises ConnectionError after page 2 of 5
    first run: assert raw_document rows == 2
    second run with the same cursor: assert transport.paths[0] == "/search?page=3"
    assert total raw_document rows == 5, no duplicates (UNIQUE source_id,url,hash)
```

---

## 2. Robots and rate limiting, tested with no network (V14)

The harness is the point. Three doubles, all committed under `tests/support/`:

- **`FakeClock`** — `monotonic()` returns a controlled value; `sleep(s)` records
  `s` and advances the clock. No test ever waits in real time.
- **`RecordingTransport`** — implements the client's transport protocol, returns
  queued responses, and appends `(timestamp, method, host, path, headers)` to
  `transport.calls`.
- **`no_network`** — an autouse fixture patching `socket.socket` to raise. The
  suite therefore *cannot* reach the network, which is what lets §2 claim it
  tests politeness rather than assuming it.

Fixtures: `tests/fixtures/robots/*.txt`, hand-written (a synthetic `robots.txt`
is legitimate here — we are testing our parser, not the portal's file; the *real*
one lives in `docs/evidence/robots/`).

### 2.1 Red-green sequence — robots

| # | Test | Assertion | Discharges |
|---|---|---|---|
| 2.1 | `test_robots_is_fetched_before_any_content_request` | `transport.calls[0].path == "/robots.txt"` and `len(transport.calls) == 1` before any yield | V14 |
| 2.2 | `test_disallowed_path_is_never_requested` | Fixture `disallow-oferta.txt` (`Disallow: /oferta/`): `policy.allows("/oferta/123") is False`, `policy.allows("/szukaj?...") is True`; after a full `fetch()`, `[c.path for c in transport.calls if c.path.startswith("/oferta/")] == []` | V14 |
| 2.3 | `test_user_agent_specific_rules_win_over_wildcard` | Fixture with `User-agent: *  Disallow: /` and a named-agent block allowing `/szukaj`: with our configured agent, `allows("/szukaj") is True`; with agent `"other"`, `False` | V14 |
| 2.4 | `test_missing_robots_is_not_permission` | **Our own rule, D92 part 1.** Transport returns 404 for `/robots.txt` → `policy.state == "unknown"`; the runner raises `RobotsEvidenceMissing` unless `source.robots_ok` was set from recorded evidence. Assert `transport.calls == ["/robots.txt"]` | V14, §0.4 |
| 2.4b | `test_a_served_file_with_no_matching_group_allows` | **RFC 9309, D92 part 2.** Fixtures `no-group.txt` and `other-agent-only.txt` (a served 200 with no group that matches us) → `allows("/szukaj?q=x") is True`, `allows("/oferta/1") is True`, and `policy.warnings == ["no_matching_group"]`. The test states this rule on its own and never reads it off test 2.4 | V14, §0.4 |
| 2.5 | `test_robots_5xx_is_treated_as_disallow` | 503 on `/robots.txt` → zero content requests, alarm `robots_unavailable`. A failing robots endpoint must not read as an open door | V14 |
| 2.6 | `test_crawl_delay_overrides_config_when_stricter` | `Crawl-delay: 20` with `rate_limit_rpm: 9` (6.67 s) → `effective_interval_s == 20.0`; with `Crawl-delay: 2` → `effective_interval_s == pytest.approx(6.667, abs=1e-3)` (ours is stricter, ours wins) | V14 |
| 2.7 | `test_partial_permission_yields_list_only_mode` | List path allowed, detail path disallowed → `connector.mode == "list_only"`, and every emitted item has `detail_fetched is False` | V14, §0.3 |
| 2.8 | `test_no_credential_or_anti_bot_code_path_exists` | Text/AST scan of `src/lpc/ingest/`: zero occurrences of `password`, `login(`, `set_cookie`, `captcha`, `undetected`, `stealth`, `selenium`, `playwright`. Asserted as an empty list of `(file, line)` hits | V14 |

### 2.2 Red-green sequence — rate limiting and backoff

| # | Test | Assertion | Discharges |
|---|---|---|---|
| 2.9 | `test_minimum_interval_holds_over_500_requests` | Simulate 500 requests to one host at `rate_limit_rpm: 9`; `diffs = [t[i+1]-t[i]]`; assert `len(transport.calls) == 500` and `min(diffs) >= 6.666` — **not** the mean, which would hide a burst | V14 |
| 2.10 | `test_limit_is_per_host_not_global` | 100 requests alternating two hosts; assert per-host minimum intervals both hold, and that wall-clock advanced ~half of what a global limiter would need | V14 |
| 2.11 | `test_429_backs_off_exponentially` | Transport returns 429×4 then 200; assert `clock.sleeps == [1, 2, 4, 8]` and the 5th call succeeds | V14 |
| 2.12 | `test_retry_after_header_overrides_the_backoff_curve` | 429 with `Retry-After: 120` → `clock.sleeps == [120]`, not `[1]` | V14 |
| 2.12b | `test_retry_after_longer_than_an_hour_ends_the_run` | **D93.** `Retry-After: 3600` → `clock.sleeps == [3600.0]` and the run continues; `Retry-After: 3601` → `clock.sleeps == []`, raises `SourceUnavailable(reason="retry_after_exceeds_budget")`, `result.published is False`, and yesterday's rows stay in place | V14, V8 |
| 2.13 | `test_5xx_gives_up_after_max_attempts_without_publishing` | 5×503 → raises `SourceUnavailable`; `result.published is False`; prior day's rows untouched (row count and max `observed_at` unchanged) | V14, V8, `11` §4 |
| 2.14 | `test_backoff_never_shortens_the_interval` | After a backoff sleep the limiter's next-slot calculation is not reset — assert the interval following a 120 s `Retry-After` is still ≥ the configured minimum | V14 |
| 2.15 | `test_off_peak_window_is_honoured` | With `window: 01:00–06:00 Europe/Warsaw` and a clock at 14:00, `runner.should_run() is False`; at 02:00, `True`. Europe/Warsaw explicit, per F10 | FR-4 |

---

## 3. Work item 4 — GUS BDL (V13, V16)

Tier **A/B** (`20` §2): the API is an oracle for its own values; the BDL web
interface is an **independent** oracle for a hand-checked sample.
Silent-failure modes touched: F8 (stale), F10 (period boundaries), and the
pagination case of F5.

`kind = "api"`. No robots gate — but §0.4's evidence test still applies.

### 3.1 Red-green sequence

| # | Test | Assertion | Discharges |
|---|---|---|---|
| 3.1 | `test_request_shape_is_built_from_config_not_hardcoded` | `client.build_url(var_id=cfg.land_sales_var_id, teryt="1415", page=0)` equals the exact string `".../data/by-unit/011415000000?var-id=<id>&format=json&page-size=100"`; the var id comes from `config/sources.yml`, asserted by changing the config value and re-checking the URL | V13 |
| 3.1b | `test_teryt_to_bdl_unit_id_mapping_is_recorded_not_derived` | **D97.** `mapping["1415"] == "011415000000"`, read from config; every in-scope powiat TERYT has an entry; a TERYT absent from the map raises `UnmappedUnit`. A static scan asserts the connector builds no unit id by string concatenation, padding or slicing | V13 |
| 3.2 | `test_parse_pins_every_value_in_the_fixture` | Against `2026-08-08_by-unit_1415_land-sales.json`: `[(p.period, p.value) for p in items] == [("2025-Q1", 61.20), ("2025-Q2", 64.80), ("2025-Q3", 66.10), ("2025-Q4", 68.40)]`, and `len(items) == 4` | V13 |
| 3.3 | `test_every_item_is_labelled_sales` | `{p.price_type for p in items} == {"sales"}`; `{p.unit_level} == {"powiat"}`; `{p.teryt} == {"1415"}` | V13, V1 |
| 3.4 | `test_as_of_and_transacted_are_distinct_fields` | Fixture's publication date `2026-05-20` with period `2025-Q4`: `item.transacted_at == date(2025,12,31)`, `item.as_of == date(2026,5,20)`, and `as_of > transacted_at`. Assert the `published_after_transacted` CHECK accepts it and rejects the swap | V13, V32 |
| 3.5 | `test_period_bucketing_uses_europe_warsaw` | A period boundary value does not shift quarter under a `TZ=UTC` and a `TZ=America/New_York` environment — same parsed `transacted_at` in both | F10 |
| 3.6 | `test_missing_rural_split_is_absence_not_zero` | Fixture `..._no-rural-split.json`: `item.rural_value is None`, `item.rural_absence_reason == "not_published"`, and `0 not in [i.value for i in items]` | V13 |
| 3.7 | `test_pagination_collects_every_page_and_matches_stated_total` | 3-page fixture with `totalRecords: 250`: `len(items) == 250`, `result.stated_total == 250`, `result.alarms == []` | V13, V43 |
| 3.8 | `test_truncated_pagination_alarms_and_blocks_publication` | Same fixture with page 3 removed: `len(items) == 200`, `"corpus_incomplete" in result.alarms`, `result.published is False` | V43 |
| 3.9 | `test_emit_writes_transaction_rows_with_provenance` | After `emit`: every row has `price_type == "sales"` and `price_kind == "transaction"` (D68), non-null `as_of`, `source_ids` of length ≥ 1; attempting `price_type='offering'` raises the DB CHECK, and so does any other `price_kind` | V13, V1, V5 |
| 3.10 | `test_reimport_is_idempotent` | Running `emit` twice on the same fixture leaves the row count unchanged and no duplicate `(teryt_unit, transacted_at, property_kind)` | V13 |
| 3.11 | `test_coverage_assertion_names_the_missing_powiat` | Δ assertion over a fixture missing powiat `2804`: assertion fails, and its `observed` JSON contains `{"missing": ["2804"]}` — naming it, not just counting | V13 |
| 3.12 | `test_handcheck_matches_the_bdl_web_interface` | Golden comparison against `2026-08-08_web-handcheck.csv` (three powiats, transcribed by hand from the BDL web UI, one per target unit): every value equal to the published precision. **This is the only test in item 4 that does not go through our own client** | V13 |
| 3.13 | `test_gus_ratio_assertion_is_report_only_until_the_band_is_set` | With `band: null`, an offering/sales ratio of 2.4 → assertion passes and writes `observed={"ratio": 2.4}`; with `band: [1.05, 2.5]`, a ratio of 0.8 (**inversion**) → fails with `reason="offering_below_sales"` | V16 |

### 3.2 Fixtures

| Path | Variant it covers |
|---|---|
| `tests/fixtures/gus_bdl/2026-08-08_by-unit_1415_land-sales.json` | Nominal quarterly series, powiat skierniewicki |
| `tests/fixtures/gus_bdl/2026-08-08_by-unit_2804_land-sales.json` | Second ring (powiat elbląski) |
| `tests/fixtures/gus_bdl/2026-08-08_no-rural-split.json` | Urban/rural split absent |
| `tests/fixtures/gus_bdl/2026-08-08_paged-1of3.json` … `-3of3.json` | Pagination, `totalRecords: 250` |
| `tests/fixtures/gus_bdl/2026-08-08_paged-truncated.json` | Page 3 missing — the V43 alarm case |
| `tests/fixtures/gus_bdl/2026-08-08_drift-renamed-value-field.json` | Schema drift for §1.2 |
| `tests/fixtures/gus_bdl/2026-08-08_web-handcheck.csv` | Independent oracle |

---

## 4. Work item 5 — the portal connector (V12, V14, V43, V57, V58, V44)

**Blocked on O10 from §4.4 onward.** §4.1–§4.3 are writable now.

Tier **A** for parsing and raw storage, **B** for corpus completeness (the
portal's own count is the second source). Silent-failure modes: F1 (units),
F2 (price for something else), F5 (pagination), F6 (sort order), F7 (stock/flow),
F8 (staleness).

### 4.1 Raw payload storage (V57) — before any parser

Written first, because everything after it is recoverable only if raw payloads
exist ( `18` §5).

```
tests/integration/ingest/test_raw_store.py

  test_stored_document_carries_source_url_time_and_hash
    store(doc_bytes, url="https://<portal>/szukaj?p=1", fetched_at=T)
    assert row.content_hash == sha256(doc_bytes).hexdigest()   # pinned literal in the test
    assert row.url == the exact url, row.fetched_at == T, row.source_id == portal id

  test_identical_refetch_does_not_duplicate_storage
    store the same bytes twice → assert row count == 1        # the UNIQUE (source_id,url,content_hash)
    flip one byte → assert row count == 2

  test_changed_page_keeps_both_versions
    assert {r.content_hash for r in rows} has size 2 and both fetched_at values survive

  test_reparse_from_raw_equals_parse_from_fetch
    items_live = list(connector.parse(doc_from_fetch))
    items_raw  = list(connector.parse(load_raw(row.id)))
    assert items_live == items_raw

  test_reparse_drill_corrects_values_without_touching_snapshots
    ingest a fixture window with a deliberately wrong parser (areas ÷10)
    record snapshot rowids and a checksum of listing_snapshot
    fix the parser, re-parse the window, recompute aggregates
    assert median_ppm2 changed from 631.0 to 63.1
    assert the listing_snapshot checksum is byte-identical
    assert a new metric generation exists (generation == 2) and generation 1 survives
```

The last test is V57's second half and V42's drill in v0 form.

### 4.2 Politeness (V14)

All of §2, instantiated for the portal connector. No new tests; the parametrised
ones must be green for `name == "portal"`.

### 4.3 Snapshot semantics (V12)

Writable now only in its **synthetic** form; the real three-day capture waits on
O10.

```
tests/integration/ingest/test_snapshots.py

  test_three_day_crawl_produces_the_exact_expected_series
    day1: listing X at 189000 active; day2: 179000 active; day3: absent
    assert [(s.observed_at.date(), s.price_pln, s.is_active) for s in snapshots(X)] == [
        (d1, 189000, True), (d2, 179000, True), (d3, 179000, False)]
    assert len(snapshots(X)) == 3

  test_price_history_derives_exactly_one_change
    assert price_changes(X) == [(d2, 189000, 179000)]

  test_delisting_is_recorded_not_deleted
    assert snapshot row count unchanged after day 3; listing.is_active is False

  test_relisting_links_to_the_same_plot_cluster
    same external_id reappears on day 5 → assert cluster_id unchanged, and a 4th snapshot

  test_no_update_or_delete_targets_listing_snapshot
    (a) source scan: zero UPDATE/DELETE statements naming listing_snapshot
    (b) as app_pipeline: UPDATE listing_snapshot ... raises InsufficientPrivilege

  test_a_crawl_gap_is_recorded_not_interpolated
    skip day 2 entirely → assert no snapshot row for d2
    assert the derived interval carries boundary_uncertainty is True
    assert no invented price for d2
```

### 4.4 Parsing the list page — **blocked on O10**

```
tests/unit/ingest/portal/test_parse_list.py

  test_parse_list_page_pins_the_first_item
    assert items[0] == ParsedItem(external_id="61234567",
                                  price_pln=Decimal("189000.00"),
                                  area_m2=Decimal("3000.00"),
                                  area_raw="3000 m²",
                                  url=".../oferta/61234567",
                                  is_active=True)
    assert len(items) == 40                     # the page size, pinned

  test_price_per_m2_is_not_computed_in_the_connector
    assert not hasattr(items[0], "price_per_m2")   # it is a generated column (15 §5)

  test_price_on_request_is_quarantined_with_a_reason
    fixture *_price-on-request: assert item.price_pln is None
    assert quarantine == [("price_on_request", external_id)]
    assert no listing row was written, and no row with price_pln == 0

  test_area_in_ares_and_hectares_convert_exactly
    "12 arów"  -> 1200; "0,12 ha" -> 1200; "1 200 m²" -> 1200; "1,2 ha" -> 12000
    assert all four parse to the same Decimal where they should be equal
    (F1: this is the 100× error, and it is silent)

  test_area_without_a_unit_is_quarantined_not_assumed
    "1,24" -> quarantine reason "area_unit_missing"; assert no m² assumption

  test_missing_coordinates_do_not_become_a_null_island
    fixture *_no-coords: assert item.geom is None
    assert item.location_precision == "locality"
    assert (item.lat, item.lon) != (0.0, 0.0)

  test_unmapped_category_alarms_rather_than_defaulting
    category "działka inwestycyjna" absent from the map -> alarm, asset_class unset  (V26)

  test_seller_contact_is_hashed_never_stored_raw
    assert item.seller_contact_hash != the fixture's phone string
    assert the phone digits appear nowhere in the emitted item (FR-23)
```

### 4.5 Corpus completeness (V43) — **blocked on O10**

> *"the highest-value single check in the ingestion path"* — a silently partial
> corpus still produces confident medians.

```
tests/unit/ingest/portal/test_completeness.py

  test_stated_result_count_is_parsed_from_the_list_page
    assert parse_stated_total(page1) == 248        # "Znaleziono 248 ogłoszeń"

  test_full_pagination_matches_the_stated_total
    6-page fixture: assert items_emitted == 248, alarms == []

  test_truncation_at_page_3_of_10_alarms_and_blocks_publication
    assert items_emitted == 72
    assert "corpus_incomplete" in result.alarms
    assert result.shortfall_ratio == pytest.approx(1 - 72/248, abs=1e-4)
    assert result.published is False
    assert assertion_run.blocked_publication is True

  test_small_churn_during_a_crawl_does_not_alarm
    tolerance = max(3 listings, 2% of the stated total)          # D95
    collected 246 of stated 248, allowance 5
    assert result.alarms == []

  test_the_tolerance_boundary_is_inclusive                       # D95
    collected 243 of stated 248 -> shortfall 5, allowance 5 -> no alarm
    collected 242 of stated 248 -> shortfall 6, allowance 5 -> corpus_incomplete
    collected 17 of stated 20   -> shortfall 3, allowance 3 -> no alarm
    (the absolute floor exists because 2% of 20 is less than one listing)

  test_an_approximate_stated_total_never_blocks_publication      # D96
    stated "ponad 1 000", collected 987
    assert result.alarms == []
    assert result.published is True
    assert assertion_run.passed is True and its observed records the comparison

  test_the_tolerance_is_read_from_config_not_hardcoded
    set churn_relative to 0.0 and churn_abs_floor to 0
    -> the 246/248 case now alarms

  test_a_missing_next_link_is_distinguished_from_a_last_page
    last page without a next link and count satisfied -> no alarm
    non-last page without a next link -> "pagination_broken" alarm
```

### 4.6 List-page-first sufficiency (V58, FR-68) — **blocked on O10**

```
tests/integration/ingest/portal/test_list_first.py

  test_detail_pages_are_fetched_on_first_sight_only
    day1 with 40 new listings -> assert detail_requests == 40
    day2 identical            -> assert detail_requests == 0
    day2 with 3 price changes -> assert detail_requests == 3
    assert the detail URLs requested are exactly those three external_ids

  test_request_budget_stays_inside_the_politeness_envelope
    corpus of 400 listings, page size 40, 10 changed
    assert total_requests == 10 + 10 + 1        # pages + details + robots
    assert simulated wall clock <= 1 hour at 9 rpm      (10 §2.1: v0 fits in an hour)

  test_detail_price_wins_and_the_disagreement_is_counted
    list says 189000, detail says 179000
    assert stored price_pln == Decimal("179000.00")
    assert result.list_detail_disagreements == 1
    assert result.list_detail_disagreement_rate == pytest.approx(1/40)

  test_a_detail_only_price_change_is_caught_on_the_next_cycle
    price changes on the detail page while the list page is stale
    assert the change appears in the snapshot series within one cycle of the
    list page updating, and that the gap is flagged rather than backdated

  test_disagreement_rate_above_threshold_alarms
    12 of 40 disagree, threshold 0.10 -> "list_detail_divergence" in result.alarms
```

The **sampled live reconciliation** V58 actually specifies (fetch a random subset
of detail pages, compare) is a scheduled job, not a unit test. Its threshold is
set from the first run's actuals, so the test above pins *behaviour given a
threshold*, never a guessed number.

### 4.7 Sort-order independence (V44) — **live; only the alarm is testable offline**

```
tests/unit/ingest/portal/test_sort_order.py

  test_divergent_sort_orders_raise_the_alarm
    two hand-built samples: price-asc median 55.0, date-sorted median 78.0
    assert compare(a, b).statistic exceeds the configured bound
    assert "sort_order_bias" in alarms

  test_matched_sort_orders_do_not_alarm
    two samples drawn from the same distribution -> alarms == []

  test_the_comparison_reports_both_medians_and_both_n
    assert the report carries (median, n, p25, p75) for each arm — never a bare
    verdict (rule 7)
```

### 4.8 Stock and flow at ingestion time (F7, feeds V45)

```
  test_first_seen_at_is_never_overwritten
    listing observed on d1 and again on d10
    assert listing.first_seen_at == d1 and last_seen_at == d10
```

Without this, flow is unrecoverable, and flow is the headline (D56).

---

## 5. Work item 7 — KOWR (V53, V46)

Tier **A/B**. `kind = "registry"`. Silent-failure modes: F1 (ha areas — KOWR
states almost everything in hectares), F5 (pagination), F9 (tender prices
blending with asks), F12 (quarantine swallowing a segment).

**Where a KOWR record lives (D91).** Every emitted KOWR record is a row in
`notice`, never in `listing`. A `notice` row carries a notice date and an auction
date; `listing` carries neither and requires a non-null price and area. Each row
carries `price_type = 'offering'` and `price_kind = 'tender'` (D65, D68).

D91 leaves the quarantine path alone. A notice with no price, no area or an
unresolvable gmina still goes to `listing_quarantine` with its reason and its
identifying JSON, exactly as 5.5 to 5.9 state.

### 5.1 Red-green sequence

| # | Test | Assertion | Discharges |
|---|---|---|---|
| 5.1 | `test_price_kind_is_tender_for_every_kowr_item` | `{i.price_kind for i in items} == {"tender"}` and `{i.price_type for i in items} == {"offering"}` (D65); `price_kind` is a required constructor argument — omitting it raises, so it cannot default | V53, V46 |
| 5.2 | `test_parse_pins_the_notice_values` | `items[0].price_pln == Decimal("145000.00")`, `area_m2 == Decimal("12400.00")`, `area_raw == "1,2400 ha"`, `teryt_gmina == "1015052"`, `notice_date == date(2026,7,14)` | V53 |
| 5.3 | `test_hectares_convert_exactly_including_decimal_comma` | `"1,2400 ha" → 12400`, `"0,1500 ha" → 1500`, `"15 a" → 1500`, `"12 arów" → 1200`. Assert `parse("0,15 ha") == parse("15 a") == parse("1500 m²")` | V53, V28, F1 |
| 5.4 | `test_area_without_a_unit_is_quarantined` | `"1,24"` → quarantine `area_unit_missing`; assert **no** hectare assumption, since assuming ha here is a 10 000× error | V53, F1 |
| 5.5 | `test_notice_without_a_price_is_quarantined_not_dropped` | Fixture `*_no-price`: `quarantine == [("price_missing", id)]`, `reason is not None`, and the notice's identifying JSON is retained in `listing_quarantine.listing_ref` | V53, V50 |
| 5.6 | `test_price_stated_as_a_range_keeps_both_endpoints` | `"cena wywoławcza od 120 000 do 150 000 zł"` → quarantine `price_is_range`, `listing_ref["price_low"] == 120000`, `listing_ref["price_high"] == 150000`. Never a midpoint of 135 000 | V53 |
| 5.7 | `test_notice_without_a_usable_area_is_quarantined_with_its_reason` | Fixture `*_no-area`: reason `area_missing`; assert `quarantine_count == 1` and `emitted_count == 0` for that notice | V53 |
| 5.8 | `test_teryt_is_resolved_by_code_never_by_name` | Notice naming *"Skierniewice"* resolves to the **rural** gmina `1015052`, not the city `1062011`; and a static scan asserts no `WHERE name =` gmina lookup in the connector | V53, V30 |
| 5.9 | `test_unresolvable_gmina_is_quarantined_not_guessed` | Ambiguous locality → reason `teryt_unresolved`; assert no row with a null `teryt_gmina` reaches `notice` | V53 |
| 5.10 | `test_collected_count_matches_kowrs_own_stated_total` | Stated 87, collected 87 → no alarm; truncated at 60 → `corpus_incomplete`, `published is False` | V53, V43 |
| 5.11 | `test_missing_coordinates_yield_gmina_precision` | KOWR notices carry no coordinates: `location_precision == "gmina"`, `geom is None`, and (per V29) parcel/nature enrichment is unreachable for the row | V53, V29 |
| 5.12 | `test_tender_rows_never_move_an_asking_median` | Asking fixture median `80.00`, `n = 20`. Add 5 KOWR rows at `20.00`. Assert the asking aggregate is still `median == 80.00` **and** `n == 20`; assert a separate `tender` aggregate exists with `n == 5, median == 20.00` | **V46** |
| 5.13 | `test_the_aggregation_key_includes_price_kind` | Architecture test: the aggregate group-by tuple contains `price_kind`; removing it from the key makes 5.12 fail (verified by the mutation run, V52) | **V46** |
| 5.14 | `test_kowr_rows_are_written_to_notice_not_listing` | **D91.** After `emit` on the nominal fixture: `count(notice) == 87`, `count(listing) == 0`; every notice row carries a non-null `notice_date`; the connector's target table name is read from the mapping, and a static scan asserts the token `listing` never appears as an insert target in `src/lpc/ingest/kowr/` | V53 |
| 5.15 | `test_a_notice_keeps_its_notice_date_and_has_no_auction_date` | KOWR sale notices are tenders, not auctions: `notice_date == date(2026,7,14)`, `auction_at is None`. Assert the two columns are distinct fields, so a later auction source cannot overwrite one with the other | V53 |

### 5.2 Fixtures

| Path | Variant |
|---|---|
| `…/kowr/2026-08-08_notice-list_p1.html` | Nominal list, stated total 87 |
| `…/kowr/2026-08-08_notice_ha-area.html` | Area in hectares with decimal comma |
| `…/kowr/2026-08-08_notice_ares.html` | Area in ares |
| `…/kowr/2026-08-08_notice_no-price.html` | Price absent |
| `…/kowr/2026-08-08_notice_price-range.html` | *od … do …* — required by V53 |
| `…/kowr/2026-08-08_notice_no-area.html` | Area absent — required by V53 |
| `…/kowr/2026-08-08_list_truncated-p2of4.html` | Pagination truncation |
| `…/kowr/2026-08-08_drift-renamed-price.html` | Schema drift for §1.2 |

---

## 6. Work item 8 — bailiff and bankruptcy auctions (V54, V46)

**Both auction sources are built (D111):** the central e-auction service
(`auction_central`) and the bankruptcy gazette (`auction_gazette`). They are two
connectors, because they are two hosts with two document formats. Each one needs
its own robots evidence under §0.4, and that evidence is the only gate left on
this work item.

**Where an auction record lives (D91).** Every emitted auction record is a row in
`notice`, never in `listing`. The row carries the notice date and the auction
date. Each row carries `price_type = 'offering'` and
`price_kind = 'auction_start'` (D65, D68).

Tier **A** for the fraction arithmetic, **B** for counts. The fraction
arithmetic needs no recorded document, so it is greenable now.

### 6.1 The statutory fraction — the load-bearing part

A *cena wywoławcza* is a legally derived floor: three quarters of the *suma
oszacowania* at the first auction, two thirds at the second. The number is
uninterpretable without the fraction, so the fraction is data, not prose.

```
tests/unit/ingest/auction/test_fraction.py

  test_first_auction_three_quarters_is_recorded_with_its_valuation
    notice: "cena wywoławcza 90 000 zł, tj. 3/4 sumy oszacowania 120 000 zł"
    assert item.price_pln == Decimal("90000.00")
    assert item.valuation_pln == Decimal("120000.00")
    assert item.statutory_fraction == Fraction(3, 4)
    assert item.auction_round == 1
    assert item.fraction_consistent is True

  test_second_auction_two_thirds
    "2/3 sumy oszacowania" -> Fraction(2, 3), auction_round == 2

  test_fraction_written_in_words_is_parsed
    "trzy czwarte sumy oszacowania" -> Fraction(3, 4)
    "75% sumy oszacowania"          -> Fraction(3, 4)

  test_fraction_without_a_stated_valuation_is_still_kept
    assert item.statutory_fraction == Fraction(3, 4)
    assert item.valuation_pln is None
    assert item.fraction_consistent is None        # unknown, not False

  test_valuation_without_a_stated_fraction_is_not_inferred
    assert item.statutory_fraction is None         # never defaulted to 3/4
    assert item.valuation_pln == Decimal("120000.00")

  test_an_inconsistent_notice_is_flagged_and_neither_number_is_corrected
    "cena wywoławcza 90 000 zł, 3/4 sumy oszacowania 130 000 zł"
    assert item.fraction_consistent is False
    assert item.price_pln == 90000 and item.valuation_pln == 130000
    assert "fraction_mismatch" in item.flags
    # we record the disagreement; we do not recompute the source's arithmetic

  test_the_arithmetic_must_agree_within_one_zloty            # D94
    fraction_consistent is True iff
      abs(price_pln - valuation_pln * statutory_fraction) <= Decimal("1.00")
    "2/3 sumy oszacowania 130 000 zł, cena wywoławcza 86 667,00 zł"
      -> difference 0,33 zł -> fraction_consistent is True
    "2/3 sumy oszacowania 130 000 zł, cena wywoławcza 86 668,00 zł"
      -> difference 1,33 zł -> fraction_consistent is False
    assert the tolerance is read from config, not written into the parser
```

The tolerance is one złoty, and D94 settles it. Notices round to the whole
złoty, so a smaller tolerance flags every second-auction notice.

### 6.2 The rest of the sequence

| # | Test | Assertion | Discharges |
|---|---|---|---|
| 6.7 | `test_price_kind_is_auction_start` | `{i.price_kind} == {"auction_start"}` and `{i.price_type} == {"offering"}` (D65), required argument, no default | V54, V46 |
| 6.8 | `test_auction_date_is_captured` | `item.auction_at == datetime(2026,9,12,10,0, tz=Europe/Warsaw)`; tz explicit (F10). After `emit` the value lands in `notice.auction_at`, and `notice.notice_date` holds the publication date — two distinct columns (D91) | V54 |
| 6.8b | `test_auction_rows_are_written_to_notice_not_listing` | **D91.** `count(notice) == n`, `count(listing) == 0`; a static scan asserts no insert targets `listing` in either auction connector | V54 |
| 6.9 | `test_a_notice_without_a_date_is_quarantined` | Reason `auction_date_missing` — *"a past auction is not supply"*, so an undated one cannot be treated as supply | V54 |
| 6.10 | `test_a_past_auction_is_retained_but_not_counted_as_supply` | Auction date before `now` → `is_supply is False`, row retained; assert it is excluded from the active-supply count and included in the historical one | V54 |
| 6.11 | `test_parcel_identifier_is_extracted_when_present` | `"101505_2.0012.123/4"` → `parcel_identifier` pinned exactly; auctions carry these far more often than adverts do | V54 |
| 6.12 | `test_area_in_hectares_converts_exactly` | `"0,3000 ha" → 3000 m²`; `"3 000 m²" → 3000`; assert equality | V54, F1 |
| 6.13 | `test_missing_coordinates_fall_back_to_the_parcel_not_a_pin` | No coordinates but a parcel id → `location_precision == "parcel"` after resolution, `geom is None` at parse time | V54, V29 |
| 6.14 | `test_auction_rows_never_move_an_asking_median` | Asking median `80.00`, `n = 20`; add 5 auction rows at `30.00`; assert asking median `== 80.00`, `n == 20`; separate `auction_start` aggregate `n == 5` | **V46** |
| 6.15 | `test_collected_count_matches_the_sources_stated_total[<source>]` | As V43, with the D95 tolerance; parametrised over both sources; truncation alarms and blocks | V54, V43 |
| 6.16 | `test_each_source_layout_has_its_own_fixture_and_parser` | Parametrised over the layout registry; assert every registered layout has ≥1 dated fixture, and every fixture directory has a registered layout | V54 |
| 6.17 | `test_both_auction_sources_are_registered` | **D111.** `{s.name for s in auction_sources} == {"auction_central","auction_gazette"}`; each source has ≥1 layout in the layout registry; dropping either source fails the test. This is what stops the gazette from being postponed and then forgotten | V54 |
| 6.18 | `test_the_same_auction_published_by_both_sources_is_one_notice` | The central service and the gazette both publish one auction: assert `count(notice) == 1` after both connectors run, and that the surviving row records both `source_ids`. The match key is D78's (area, price, gmina, asset class) | V54, V56 |

### 6.3 Fixtures

One directory per source, then one per layout:
`…/auction/<source>/<layout>/2026-08-08_*.html`, with `<source>` in
`{auction_central, auction_gazette}` (D111).

Variants per layout: `…_first-auction-3-4.html` ·
`…_second-auction-2-3.html` · `…_fraction-in-words.html` ·
`…_fraction-no-valuation.html` · `…_inconsistent-fraction.html` ·
`…_no-date.html` · `…_past-date.html` · `…_ha-area.html` ·
`…_with-parcel-id.html` · `…_list-truncated.html` ·
`…_drift-renamed-price.html`

Plus `…/auction/<source>/<layout>/2026-08-08_cross-source.html` in **both**
source directories. That pair is what 6.18 needs.

---

## 7. Work item 13 — gmina BIP notices (V55)

~50 gminas, each with its own bulletin. The point of V55 is not parser coverage —
it is that **the uncovered ones are visible**: *"a gmina we cannot parse is
reported as a coverage gap, never as a gmina with no land for sale"*. That is the
failure that would make an empty area look like a cheap one.

Tier **A** per layout, **B** in aggregate. Silent-failure modes: F1, F5, F12, and
a variant of F13 (absence read as evidence).

### 7.1 Red-green sequence — coverage first, parsers second

Deliberately inverted relative to the other connectors. The registry test is
written **before** the first BIP parser exists, so the first green state is
*"50 gminas, 0 covered, 50 declared uncovered with reasons"* — which is honest and
publishable, unlike *"50 gminas, 0 listings"*.

| # | Test | Assertion | Discharges |
|---|---|---|---|
| 7.1 | `test_every_in_scope_gmina_is_covered_or_declared_uncovered` | `covered ∪ uncovered == gminas_in_both_rings` (the set produced by work item 3), `covered ∩ uncovered == ∅`, and the count is pinned to the ring computation rather than a literal | **V55** |
| 7.2 | `test_every_uncovered_entry_has_a_non_empty_reason` | `all(e.reason for e in uncovered)`; reasons drawn from a closed vocabulary `{no_bulletin_found, pdf_scan_no_text, layout_unsupported, robots_disallowed, requires_js}` — an unknown reason string fails | **V55** |
| 7.3 | `test_an_uncovered_gmina_never_reports_zero_supply` | For an uncovered gmina: `coverage.status == "uncovered"`, `coverage.listings_active is None`; and the render helper produces *"brak parsera"*, asserting the string *"brak ogłoszeń"* does **not** appear | **V55**, V59 |
| 7.4 | `test_a_covered_gmina_with_no_notices_reports_zero_explicitly` | `status == "covered"`, `listings_active == 0`, `last_crawl_at` not null — the opposite case, and the two must be distinguishable | **V55**, V36 |
| 7.5 | `test_the_delta_assertion_matches_registry_to_coverage_report` | Δ: `covered_count_in_report == len(parser_registry)`; drop a parser from the registry without updating the report → assertion fails | **V55** |
| 7.6 | `test_layout_family_parse_pins_values[<family>]` | Parametrised over layout families; each pins `price_pln`, `area_m2`, `notice_date`, `parcel_identifier`, `teryt_gmina` exactly, e.g. `("bip_gov_table", 46000, 1500, date(2026,6,2), "101505_2.0012.123/4")` | **V55** |
| 7.7 | `test_ares_are_the_default_trap_here` | `"15 a" → 1500`, `"15 arów" → 1500`, `"0,15 ha" → 1500`, `"1500 m²" → 1500` — assert all four equal. BIP notices state ares more often than any other source | **V55**, F1 |
| 7.8 | `test_a_pdf_only_notice_registers_as_uncovered_not_empty` | Fixture whose notice body is a scanned PDF: gmina appears in `uncovered` with `pdf_scan_no_text`, and zero `notice` rows are emitted for it | **V55** |
| 7.9 | `test_paginated_bulletin_truncation_alarms` | Bulletin index truncating at page 2 of 5 → `corpus_incomplete` for that gmina only; the other gminas still publish | **V55**, V43 |
| 7.10 | `test_one_gminas_failure_does_not_block_the_others` | Transport raises for gmina A; assert gmina B's rows are emitted, A is marked `failed` in the coverage report, and `published` is per-gmina | **V55**, `11` §4 |
| 7.11 | `test_missing_coordinates_yield_locality_precision_from_obreb` | `geom is None`, `location_precision in {"locality","gmina"}`, and nature/parcel enrichment unreachable | **V55**, V29 |
| 7.12 | `test_price_kind_is_tender` | BIP sale notices are *przetarg* → `price_kind == "tender"`, `price_type == "offering"` (D65); assert a BIP row cannot enter an asking aggregate (as 5.12) | **V55**, V46 |
| 7.14 | `test_bip_rows_are_written_to_notice_not_listing` | **D91.** `count(notice) == n`, `count(listing) == 0`; every row carries a non-null `notice_date` and a null `auction_at` unless the bulletin states an auction date | **V55** |
| 7.13 | `test_adding_a_gmina_to_the_rings_fails_the_registry_test` | Add a synthetic gmina to the ring fixture; assert 7.1 fails until it is classified. This is what stops the coverage table from silently going stale | **V55** |

### 7.2 Fixtures

One directory per **layout family**, not per gmina —
`tests/fixtures/gmina_bip/<family>/2026-08-08_*.html`. Families to seed:
`bip_gov_table`, `wordpress_attachment_list`, `plain_html_ordinance`,
`scanned_pdf` (the uncovered case), `js_rendered` (the uncovered case).
Plus `tests/fixtures/gmina_bip/rings_gminas.json` — the ring membership from work
item 3, which 7.1 asserts against.

---

## 8. Fixture inventory — structural variants required

Every variant named in the brief, mapped to the connector that must handle it.
[`04-validation.md`](../04-validation.md) §Fixtures policy rule 4 requires at
least one fixture per variant; this is that list, made explicit.

The **Auction** column covers both sources (D111). Every variant in that column
needs one fixture per source, and 6.17 fails if a source has none.

| Variant | GUS BDL | Portal | KOWR | Auction | BIP |
|---|:--:|:--:|:--:|:--:|:--:|
| Nominal | ✓ | ✓ (O10) | ✓ | ✓ per source | ✓ per family |
| **Price on request / absent** | — | ✓ | ✓ | — | ✓ |
| **Price stated as a range** | — | — | ✓ | — | ✓ |
| **Area in ares** | — | ✓ | ✓ | — | ✓ |
| **Area in hectares** | — | ✓ | ✓ | ✓ | ✓ |
| Area with no unit | — | ✓ | ✓ | ✓ | ✓ |
| **Missing coordinates** | n/a | ✓ | ✓ (always) | ✓ | ✓ (always) |
| **Paginated, truncating** | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Statutory fraction of valuation** | — | — | — | ✓ (3/4, 2/3, words, %, no valuation, inconsistent, ±1 zł boundary) | — |
| Same auction published by both sources | — | — | — | ✓ (D111, test 6.18) | — |
| Missing date | — | — | — | ✓ | ✓ |
| Unmapped category | — | ✓ | ✓ | — | — |
| Schema drift (renamed price field) | ✓ | ✓ | ✓ | ✓ | ✓ |
| Empty result (zero items) | ✓ | ✓ | ✓ | ✓ | ✓ |
| Personal data present, to be scrubbed at capture | — | ✓ | ✓ | ✓ | ✓ |

Fixture naming: `tests/fixtures/<source>/<YYYY-MM-DD>_<variant>.<ext>`. The date
is the capture date and is load-bearing — the quarterly re-record check reads it,
and a fixture older than two quarters fails
`test_fixtures_are_not_stale` in `tests/architecture/`.

---

## 9. Entry criteria (`20` §8) — checked per work item

| | 4 GUS BDL | 5 Portal | 7 KOWR | 8 Auction | 13 BIP |
|---|---|---|---|---|---|
| 1. PRD / work-plan entry | FR-5, FR-1 | FR-1..4, FR-68, FR-72 | FR-61 | FR-62, FR-64 | FR-63 |
| 2. Validation method | V13, V16 | V12, V14, V43, V44, V57, V58 | V53, V46 | V54, V46 | V55 |
| 3. Verification tier | A/B | A (parse), B (counts) | A/B | A (fraction), B (counts) | A (per layout), B |
| 4. Silent-failure detectors | F8, F10 | F1, F2, F5, F6, F7, F8 | F1, F5, F9, F12 | F1, F9, F10 | F1, F5, F12 |
| 5. Fixtures exist and are scrubbed | ✓ (recordable now) | **blocked O10** | **blocked, robots evidence** | **blocked, robots evidence** | **blocked, robots evidence** |
| 6. Metamorphic properties listed | §10 | §10 | §10 | §10 | §10 |

Items 5, 7, 8 and 13 therefore **fail criterion 5 today**. Item 5 waits on O10.
Items 7, 8 and 13 wait on the §0.4 robots evidence for their own hosts, which is
an afternoon of recording rather than a product decision. D111 removed the source
question from item 8, so recording is now the only thing left there. Per rule 4
their tests may be written; they may not be greened against invented fixtures.

## 10. Metamorphic properties that apply at the connector layer

Stated here because `20` §8 criterion 6 requires them, and because they catch the
bug class fixture tests pass straight through — a filter that ignores its
arguments.

| Property | Where |
|---|---|
| `parse(doc)` twice ⇒ identical output | §1.1 test 1.4, all connectors |
| Permuting the order of items on a page ⇒ same emitted set | all parsers |
| `parse("12 arów") == parse("0,12 ha") == parse("1200 m²")` | portal, KOWR, BIP |
| Doubling every price in a fixture ⇒ every emitted `price_pln` doubles, `area_m2` unchanged | all parsers |
| Adding an exact duplicate item to a page ⇒ emitted count unchanged after v0 dedup (V56) | portal, KOWR, BIP |
| Adding a `tender`/`auction_start` row to `notice` ⇒ the asking aggregate over `listing` is **unchanged** | 5.12, 6.14 — the V46 property, and the most important one here |
| The same auction from both auction sources ⇒ one `notice` row, two `source_ids` | 6.18 (D111) |
| Re-fetching an unchanged page ⇒ `raw_document` row count unchanged | §4.1 |

---

## 11. Settled rules, and what still blocks a green suite

### 11.1 Settled — write these as stated

Each rule below is decided. No test may treat one as open, and no test may derive
one rule from another.

| Decision | The rule the tests state | Where |
|---|---|---|
| **D91** | KOWR, auction and BIP records live in `notice`, never in `listing`. A `notice` row carries a notice date and an auction date. `listing` keeps its non-null price and area constraint | 5.14, 5.15, 6.8, 6.8b, 7.14 |
| **D92** | A served `robots.txt` that parses to no matching group is an **allow** (RFC 9309). A **missing** `robots.txt` is not permission and stops the run. Both rules are stated on their own | 2.4, 2.4b, §0.4 |
| **D93** | A `Retry-After` longer than one hour ends the run and publishes nothing | 2.12b |
| **D94** | The auction fraction arithmetic must agree within 1 zł | §6.1 |
| **D95** | The count-agreement tolerance is `max(3 listings, 2%)` | §4.5, 5.10, 6.15 |
| **D96** | An approximate stated total is report-only and never blocks publication | §4.5 |
| **D97** | The TERYT to BDL unit-id mapping is data in config. No test derives it by string operations | 3.1, 3.1b |
| **D111** | Both auction sources are built: the central e-auction service and the bankruptcy gazette | §6, 6.17, 6.18 |
| **D65, D68** | `price_kind ∈ {asking, auction_start, tender, transaction}`. Auction and tender rows carry `price_type = 'offering'`. Transaction rows carry `price_type = 'sales'` | 5.1, 6.7, 7.12, 3.9 |

### 11.2 Still open

Per rule 2 these are asked, not assumed. Each one prevents a test in this
document from being written truthfully.

| # | Question | Blocks | Note |
|---|---|---|---|
| **Q1** | **O10 — do the portals' `robots.txt` permit crawling listing and search paths?** Human gate, minutes to check, unresolved | All of §4.4–§4.8 | The branch table is §0.3 |
| **Q2** | O1 — which portal, once O10 answers | §4 fixtures | Downstream of Q1 |
| **Q9** | Who records the `robots.txt` evidence for KOWR, the two auction hosts and the ~50 BIP hosts, and when? §0.4 makes it a precondition of fetching | Every KOWR, auction and BIP fixture | The gate is blocking and it covers three source families. An afternoon of recording, not a product decision |
| **Q7** | GUS BDL variable IDs for the land-price series are marked **verify** in `03`. 3.1 reads them from config; the actual IDs must be recorded in `docs/evidence/` before 3.2 can pin values | 3.2, 3.12 | D97 settles the unit-id mapping. The variable IDs are a separate recording job |
| **Q8** | Thresholds: V58 disagreement rate, V44 divergence bound, V8 parse-failure rate and zero-item floor. Per O25 these are set from first-run actuals | Their tests pin *behaviour given a threshold*, never a number | The V43 churn tolerance left this list — D95 sets it |

---

## 12. Order of work

1. §1 connector contract + §2 politeness harness — **no source needed**, and
   everything else inherits them.
2. §3 GUS BDL — the only connector with no gate, and the one that gives a working
   sales baseline before any scraping exists (`03` §Source priority).
3. §6.1 auction fraction arithmetic — it needs no recorded document, and it is
   the highest-risk arithmetic in this layer.
4. §5 KOWR — off-portal, no O10 dependency. Its document parses wait on Q9.
5. §6 auction documents — both sources (D111), after their robots evidence.
6. §4 portal — after O10, and only then.
7. §7 BIP — coverage registry first (7.1–7.5), parsers after.

Note that this order is **not** `18` §6's numeric order. Items 7 and 13's
registry half are unblocked while item 5 is not, and starting with a blocked item
would idle behind a gate that only the owner can open.
