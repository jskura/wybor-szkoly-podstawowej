# Validation methods

Per [`CLAUDE.md`](../CLAUDE.md) rule 4, **no feature is implemented before its
validation method is written here**. Rule 3 then orders the work: PRD entry →
validation method → failing test → implementation → passing test.

Each entry states four things:

- **AC** — acceptance criteria: observable, specific, falsifiable
- **How** — the mechanism that verifies it
- **Against** — the data it is verified against
- **Falsified by** — the specific observation that means it is broken

Entries are grouped by milestone. `Δ` marks a **data assertion** — it runs on every
pipeline execution, not once (rule 4). `⏱` marks a scheduled check.

---

## Fixtures policy

Everything verified against "recorded fixtures" means: a real response captured
once from the live source, committed under `tests/fixtures/<source>/`, with the
capture date in the filename. Rules:

1. Fixtures are **never** hand-edited to make a test pass. If a fixture is wrong,
   re-record it and note why in the commit.
2. Fixtures contain **no personal data** — seller names, phone numbers and the
   owner's anchor addresses are scrubbed at capture time (FR-23).
3. Every connector keeps at least one fixture per structural variant it must
   handle (e.g. price-on-request, area in ares vs m², missing coordinates).
4. Re-record fixtures quarterly. A fixture that no longer resembles live output is
   a false green — that is exactly the schema drift FR-6 exists to catch.

---

## Hard invariants

These are not features; they are properties that must hold at all times. Each has
a test that runs on every commit **and** an assertion that runs on every pipeline
execution. A failure here blocks a release.

### V1 — Every price carries a price type (FR-7, rule 5)

- **AC** Every row in `listing`, `transaction` and `metric_unit_month` has a
  non-null `price_type ∈ {offering, sales}`. `listing.price_type` is always
  `offering`; `transaction.price_type` is always `sales`. Enforced by a database
  CHECK constraint, so violation is impossible rather than merely untested.
- **How** (a) A migration test asserting the CHECK constraints exist; (b) a test
  that attempts to insert a null and a bogus price type into each table and
  requires both to be rejected by the database; (c) `Δ` a post-load assertion
  counting rows with null or unexpected `price_type` — must be exactly 0.
- **Against** The live schema, plus deliberately malformed insert attempts.
- **Falsified by** Any insert with a null or out-of-domain `price_type` succeeding;
  any non-zero count from the assertion.

### V2 — Offering and sales prices are never mixed (FR-8, rule 5)

- **AC** No aggregate is computed across both price types. `metric_unit_month` is
  keyed including `price_type`, so a single row can only ever draw on one type. No
  code path substitutes one type for the other when the requested type is missing —
  a missing sales median returns "no sales data for this unit", never the offering
  median.
- **How** (a) Unit test: build a fixture unit containing both offering and sales
  observations with deliberately far-apart values (offering 200 PLN/m², sales
  100 PLN/m²); assert the offering median is 200, the sales median is 100, and no
  row anywhere reports 150; (b) unit test: request the sales median for a unit with
  zero sales observations, assert the response is an explicit absence marker and not
  a number; (c) `Δ` uniqueness assertion on `(teryt_unit, unit_level, month,
  asset_class, price_type)`.
- **Against** A hand-built fixture with known, deliberately divergent values.
- **Falsified by** Any figure equal to the blended mean; any fallback returning an
  offering figure when sales were requested.

### V3 — Every price is labelled in the API and UI (FR-9)

- **AC** Every price field in every API response is accompanied by its
  `price_type`. Every price rendered in the UI shows *cena ofertowa* or *cena
  transakcyjna*. Zero exceptions.
- **How** (a) A schema-level test walking every API response model and asserting
  that any field matching `price*`/`*_ppm2`/`median*` sits in an object that also
  carries `price_type`; (b) a UI snapshot test over the map panel, plot page,
  comparison board and trends view asserting each rendered price string is adjacent
  to a type label.
- **Against** The full API response-model set and rendered component snapshots.
- **Falsified by** A single price field reachable without an accompanying type.

### V4 — Always show, always flag (FR-25, rule 6, D17/D18)

- **AC** No aggregate is ever suppressed or hidden, **and** no aggregate is ever
  returned or rendered without both its sample size `n` and its spread. Spread is
  the IQR (p25–p75) when n ≥ 5, and min–max when n < 5. A unit with n=1 still
  returns a number, accompanied by n=1 and a degenerate range.
- **How** (a) Unit test over a fixture with units at n = 1, 3, 4, 5, 10, 100:
  assert every one returns a median (none is null, none is an "insufficient data"
  marker), assert n < 5 units carry min–max and n ≥ 5 units carry IQR; (b) an API
  boundary test that rejects any serialized aggregate missing `n` or spread —
  this is the enforcement point named in FR-25; (c) UI snapshot test asserting the
  spread and n are visible, not hidden behind a tooltip or hover.
- **Against** A synthetic fixture with controlled sample sizes, plus one real thin
  gmina from the Budy Grabskie ring where n is naturally small.
- **Falsified by** Any aggregate returned as a bare number; any "insufficient data"
  string appearing anywhere; any spread rendered only on hover.

### V5 — Provenance on every number (rule 6)

- **AC** Every derived row carries `as_of` and its source identifiers, and every
  displayed number is one click from source, as-of date, sample size and method.
- **How** (a) `Δ` assertion: zero rows in any `metric_*` or enriched table with a
  null `as_of` or an empty source list; (b) a UI test asserting every number on the
  plot page and map panel has a reachable provenance affordance.
- **Against** The live tables after a full pipeline run.
- **Falsified by** A single null `as_of`; a number with no path to its source.

---

## M0 — Spine

### V6 — Administrative boundaries and TERYT import

- **AC** All gminas of łódzkie (~177), mazowieckie (~314) and powiat elbląski +
  m. Elbląg (~10) are present with valid, non-empty PostGIS geometries and correct
  TERYT codes. Every gmina's `parent_teryt` resolves to an in-scope powiat. No
  gmina geometry is invalid (`ST_IsValid`), and no two gmina geometries overlap by
  more than a rounding tolerance.
- **How** Integration test against the recorded PRG fixture: count per unit,
  `ST_IsValid` on every geometry, pairwise overlap check, parent resolution check.
  Independently: assert that the point for Budy Grabskie falls inside gmina
  Skierniewice, powiat skierniewicki — a known-answer spatial test.
- **Against** GUGiK PRG fixture; the Budy Grabskie location independently confirmed
  as gmina Skierniewice / powiat skierniewicki / łódzkie.
- **Falsified by** A missing gmina, an invalid geometry, an overlap, or Budy
  Grabskie landing in the wrong gmina.

### V7 — Anchor configuration and privacy (FR-22, FR-23, D21)

- **AC** The application loads anchors from `config/anchors.yml`; that path is
  gitignored; `config/anchors.example.yml` exists with placeholder values only. No
  real address appears anywhere in the repository or its history. Starting the app
  without `anchors.yml` produces a clear error naming the example file, not a crash
  and not a silent fallback to hardcoded coordinates.
- **How** (a) Test asserting `config/anchors.yml` matches a `.gitignore` rule;
  (b) a repository scan test — grep the working tree **and** `git log -p` for the
  anchor street names and house number, asserting zero matches; (c) test that the
  example file parses and contains only placeholders; (d) test that a missing
  config raises a named, actionable error.
- **Against** The repository tree and full git history; the example config.
- **Falsified by** Any occurrence of a real anchor address in tracked content or
  history; a hardcoded coordinate fallback; a silent start with no anchors.

### V8 — Source health and schema-drift alarm (FR-6)

- **AC** Each connector records last success, item count and status. A connector
  returning zero items when its last successful run returned more than a
  configurable floor raises an alarm and **does not** write an empty result into
  the metrics layer. A parse failure rate above a threshold raises the same alarm.
- **How** (a) Unit test: feed a connector a fixture that parses to zero items after
  a prior run of 200; assert an alarm is raised and no metric row is written;
  (b) unit test: feed a structurally changed fixture (renamed price field); assert
  a parse-failure alarm rather than silent nulls; (c) `⏱` a daily check that every
  connector's last success is within its expected cadence.
- **Against** Recorded fixtures plus a deliberately mutated copy simulating drift.
- **Falsified by** A zero-item run flowing through to metrics; renamed fields
  producing nulls without an alarm.

### V9 — RCN access research spike (FR-31, D5)

- **AC** A committed table covering every in-scope powiat with: whether RCN data is
  published openly, the format, the request procedure, and any fee. Coverage of the
  table is complete — no powiat left blank — and every "free" classification cites
  the specific page or endpoint that supports it.
- **How** Manual research, output reviewed against the criterion that a reader can
  act on each row without repeating the research. Each free/paid classification is
  spot-checked by attempting to reach the cited resource.
- **Against** Official county and GUGiK/geoportal sources, cited per row.
- **Falsified by** Any blank row; any "free" claim whose cited source does not
  actually offer the data without payment.

---

## M1 — Both price types flowing

### V10 — Normalization and outlier quarantine (FR-12)

- **AC** `price_per_m2 = price_pln / area_m2` for every accepted listing. Records
  outside the accepted bands (land area 100–500 000 m², price 1–100 000 PLN/m²) are
  quarantined with a reason, not dropped silently and not accepted. Area stated in
  ares or hectares is converted correctly. Manual audit of a 200-record sample finds
  ≤1% surviving outliers (§5).
- **How** (a) Unit tests per rule, including boundary values at exactly 100 m² and
  500 000 m²; (b) a unit conversion test with ares and hectares fixtures;
  (c) `Δ` assertion that the quarantine table's reason field is never null and that
  the quarantine rate stays within a band — a sudden spike means upstream drift;
  (d) a documented manual audit script over 200 sampled records.
- **Against** Recorded listing fixtures including known-bad records; a hand-labelled
  200-record sample.
- **Falsified by** A record with an implausible PLN/m² reaching the metrics layer; a
  silently dropped record; a hectare listing priced as if in m².

### V11 — Deduplication (FR-13)

- **AC** The same plot advertised by multiple agencies collapses into one
  `plot_cluster` with one canonical listing and a correct `duplicate_count`.
  Genuinely distinct neighbouring plots are **not** merged. Measured on a
  hand-labelled sample of 200 listings from the anchor rings: duplicate rate after
  dedup ≤3% (false negatives) and false-merge rate ≤1%.
- **How** (a) Unit tests on the matcher with crafted near-duplicate pairs (same
  plot, different agency, price differing by 2%, title reworded) and crafted
  near-miss pairs (adjacent plots, same area, same street); (b) an evaluation
  script scoring the matcher against the hand-labelled sample and printing both
  error rates; (c) `Δ` a monitoring assertion on cluster-size distribution — a
  sudden jump in mean cluster size signals over-merging.
- **Against** A hand-labelled sample of 200 real listings, labelled once and
  committed (with personal fields scrubbed).
- **Falsified by** Either error rate exceeding its threshold; two plots at
  different parcel identifiers merged into one cluster.

### V12 — Snapshot history is append-only (FR-3)

- **AC** Every crawl appends one `listing_snapshot` row per observed listing. Rows
  are never updated or deleted. A price change between two crawls is derivable
  from consecutive snapshots; a disappearance is recorded as `is_active = false`
  rather than a deleted row; a relisting of the same plot links to the same
  `plot_cluster`.
- **How** (a) Test asserting no UPDATE or DELETE statement targets
  `listing_snapshot` anywhere in the codebase, plus a database-level revocation
  test; (b) a simulated three-day crawl over fixtures with a price cut on day 2 and
  a delisting on day 3 — assert the derived price history has exactly the expected
  shape; (c) `Δ` assertion that snapshot count is monotonically non-decreasing.
- **Against** A three-day synthetic crawl fixture.
- **Falsified by** Any mutation of a snapshot row; a price change not recoverable
  from the series; a delisting that removes history.

### V13 — GUS BDL sales-price baseline (FR-5, rule 5)

- **AC** For every in-scope powiat, the land transaction price series is imported,
  labelled `price_type = sales`, with the correct unit level, as-of date and source.
  Values match the source to the published precision. History goes as deep as BDL
  publishes (D8). The urban/rural split is preserved where present, and its absence
  is recorded as absence, not as zero.
- **How** (a) Integration test against a recorded BDL API fixture, comparing
  imported values field-by-field to the fixture; (b) a hand-check of three powiats
  (one per target unit) against the figure shown on the BDL web interface —
  independent of our own client code; (c) `Δ` coverage assertion: 100% of in-scope
  powiats have at least one sales observation (this is a §5 target).
- **Against** Recorded BDL API responses plus the BDL web interface as an
  independent ground truth.
- **Falsified by** A powiat with no series; a value differing from the BDL web
  interface; a missing split recorded as 0.

### V14 — Crawl politeness (FR-2, FR-4)

- **AC** The crawler reads and honours `robots.txt` per host before its first
  request; request rate stays within the configured per-host limit; it backs off on
  429/5xx; it never attempts authentication or anti-bot circumvention.
- **How** (a) Unit test: a fixture `robots.txt` disallowing a path, assert the
  crawler does not request it; (b) a rate-limiter test asserting the observed
  interval between requests to one host never falls below the configured minimum
  across a simulated 500-request run; (c) a backoff test against simulated 429
  responses; (d) a code-level test asserting no credential or CAPTCHA-handling code
  path exists in any connector.
- **Against** Fixture `robots.txt` files and a simulated HTTP server.
- **Falsified by** A request to a disallowed path; any interval below the limit;
  retry without backoff.

### V15 — Coverage and freshness (§5 targets)

- **AC** `Δ⏱` Each pipeline run records, per gmina: listings collected, last
  successful crawl, parcel-match rate, zoning-known rate, and both price types'
  observation counts. The coverage page reflects these without transformation. The
  §5 targets are checked as assertions, and a shortfall is reported, not hidden.
- **How** A scheduled assertion suite computing each §5 metric and comparing it to
  target; results written to a coverage table that the coverage page reads directly,
  so the page cannot disagree with the assertions.
- **Against** The live database after each daily run.
- **Falsified by** The coverage page showing a figure that the assertion suite does
  not produce; a shortfall not surfaced.

### V16 — Cross-source agreement (rule 4, data assertion)

- **AC** `Δ⏱` Our offering-price median per powiat is compared against the GUS BDL
  sales figure for the same powiat. Offering prices are expected to sit *above*
  sales prices; the ratio is expected within a plausible band. A ratio outside the
  band, or an offering median *below* the sales median, raises an investigation
  alarm — it usually means a broken parser, not a real market move.
- **How** A scheduled assertion computing the ratio per powiat, alarming outside
  the band. The band's initial values are set from the first full run and recorded
  here once known — until then the assertion runs in report-only mode.
- **Against** Our own metrics vs. GUS BDL, per powiat, per quarter.
- **Falsified by** A systematic inversion, or a ratio drifting outside the band
  without a market explanation.

---

## M2+ — deferred, method required before implementation

These have no validation method yet. Per rule 4, one must be written here before
any of them is implemented — they are listed so the gap is explicit rather than
discovered later.

| Feature | PRD | Note for the method |
|---|---|---|
| Travel time to anchors | FR-21 | Needs a known-answer test: hand-checked drive times for ~10 plots against an independent routing source |
| Choropleth and filters | FR-30 | Must include a test that thin-data gminas render with visible spread (V4 at the UI layer) |
| Parcel resolution via ULDK | FR-14 | Known-answer test against parcels with published identifiers |
| Zoning and `unknown` as terminal | FR-16, FR-17 | Must prove `unknown` is never inferred: a plot surrounded by buildable neighbours and no plan data must still read `unknown` |
| Nature attributes | FR-19, FR-20 | Distances hand-checked against a map for a sample; protected-area status must render as both amenity and constraint |
| Comparable-set engine | FR-26 | Needs a hand-picked "correct comparables" set for ~5 subject plots as ground truth |
| Asking-vs-sales spread | FR-10 | Must show both sample sizes and both as-of dates; test that differing periods are not presented as simultaneous |
| RCN connector | FR-31 → M4 | Method depends on V9's outcome |
| Hedonic model | FR-28 | Must beat the gmina-median baseline on held-out data, or it does not ship |

---

## Verification cadence summary

| When | What runs |
|---|---|
| Every commit | V1–V4 constraint and unit tests, V6–V8, V10–V14 unit and integration tests |
| Every pipeline run | All `Δ` assertions: V1, V2, V5, V8, V10, V11, V12, V15, V16 |
| Daily | `⏱` V8 connector freshness, V15 coverage, V16 cross-source agreement |
| Quarterly | Fixture re-recording; V11 hand-labelled sample refresh; V10 manual 200-record audit |
| Once, before its milestone | V9 (RCN research) |
