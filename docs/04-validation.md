# Validation methods

Per [`CLAUDE.md`](../CLAUDE.md) rule 5, **no feature is implemented before its
validation method is written here**. Rule 4 then orders the work: PRD entry →
validation method → failing test → implementation → passing test.

Each entry states four things:

- **AC** — acceptance criteria: observable, specific, falsifiable
- **How** — the mechanism that verifies it
- **Against** — the data it is verified against
- **Falsified by** — the specific observation that means it is broken

Entries are grouped by milestone. `Δ` marks a **data assertion** — it runs on every
pipeline execution, not once (rule 5). `⏱` marks a scheduled check.

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

### V1 — Every price carries a price type (FR-7, rule 6)

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

### V2 — Offering and sales prices are never mixed (FR-8, rule 6)

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

### V4 — Always show, always flag (FR-25, rule 7, D17/D18)

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

### V5 — Provenance on every number (rule 7)

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

- **AC** Every gmina **in the two 25 km rings** (D64: any part of its boundary
  within 25 km of an anchor) is present with a valid, non-empty PostGIS geometry
  and correct TERYT code. The expected set is an **exact list in the fixture
  manifest**, not an approximate count — "~177" is not falsifiable. The full
  three-voivodeship extent belongs to the deferred full plan, not to v0.
  Every gmina's `parent_teryt` resolves to its powiat, no geometry is invalid
  (`ST_IsValid`), and no two gmina geometries overlap beyond a rounding tolerance.
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
  outside the accepted band (**land area 300–200 000 m²**, price 1–100 000 PLN/m²)
  are **flagged and kept visible**, never silently dropped (FR-12 as amended by
  O12). Records with no usable price or area are quarantined with a reason. Area stated in
  ares or hectares is converted correctly. Manual audit of a 200-record sample finds
  ≤1% surviving outliers (§5).
- **How** (a) Unit tests per rule, including boundary values at exactly 300 m² and
  200 000 m², plus a guard test that fails if the superseded 100/500 000 figures
  reappear; (b) a unit conversion test with ares and hectares fixtures;
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

### V13 — GUS BDL sales-price baseline (FR-5, rule 6)

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

### V16 — Cross-source agreement (rule 5, data assertion)

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

## M3.5 — Valuation (docs 05)

### V17 — A median never travels without its range and n (FR-32, D32, **corrected by D42**)

> Corrected after audit A4. The previous wording — "no internal code path produces
> a bare scalar price" — contradicted the `Estimate` type, which carries a `median`
> field. The rule is not "no point value exists"; it is "a median is never
> returned, stored or displayed *alone*".

- **AC** Every return from `estimate()` carries `low`, `median`, `high`, `n`,
  `basis` and `widening_step`, all non-null. No function returns a median without
  its range and sample size in the same value. Where n < 5 ‡ the range is min–max;
  where n ≥ 5 ‡ it is p25–p75.
- **How** (a) Property test over generated inputs asserting the return type always
  carries all six fields; (b) a static check that no valuation function returns a
  bare numeric price *outside* an estimate object; (c) unit tests at n = 1, 4, 5, 30
  asserting the correct range definition is used at each.
- **Against** Generated feature bundles plus fixture comparable sets at controlled n.
- **Falsified by** Any estimate serialized without a range; any point estimate
  reachable from the API.

### V18 — Comparable sets never widen across buildability (FR-34, D28)

- **AC** No comparable set ever contains a plot whose buildability differs from the
  subject's, at any widening step, including the most relaxed. `unknown` subjects
  draw only on `unknown` comparables. Price type likewise never widens.
- **How** (a) Unit test walking every widening step for a subject with deliberately
  few local comparables, asserting buildability homogeneity at each step;
  (b) a test that a subject with **zero** same-buildability comparables anywhere
  returns "cannot estimate" rather than a set containing other classes; (c) `Δ`
  assertion over `valuation_log` that no logged comparable set mixed classes.
- **Against** A fixture area seeded with plots of every buildability class, where a
  buggy widener would obviously pick up the wrong ones.
- **Falsified by** A single mixed-buildability comparable set; an `unknown` subject
  estimated from `buildable` comparables.

### V19 — Widening step is recorded and displayed (FR-35)

- **AC** Every estimate records which widening step produced it, and the UI shows
  it. An estimate from a 25 km radius is visually distinguishable from a same-gmina
  one without reading numbers.
- **How** Unit test asserting the step matches the data available (seed a fixture
  where same-gmina has 4 comparables and 10 km has 12; assert the step is `10km`
  and not `gmina`); UI snapshot test asserting the step label renders.
- **Against** Seeded fixtures at each rung of the ladder.
- **Falsified by** An estimate whose recorded step does not match the data it used;
  a rendered estimate with no visible basis.

### V20 — Offering and sales estimates stay separate (FR-37, rule 6)

- **AC** `expected_offering` and `expected_sales` are computed from disjoint inputs
  and shown separately. Where sales comparables are absent, the sales estimate is
  an explicit absence — never the offering estimate, never an interpolation.
- **How** (a) Unit test with a fixture area having offering comparables and **zero**
  sales comparables; assert the sales estimate is an absence marker and that the
  offering value appears nowhere in the sales field; (b) the V2 divergent-value
  fixture reused at the estimator level.
- **Against** Fixture areas with each combination of present/absent by price type.
- **Falsified by** A sales estimate numerically equal to the offering estimate; any
  fallback path between the two.

### V21 — The regression can never produce a verdict (FR-39, D33)

- **AC** The verdict code path has **no access** to regression output — structurally,
  not by convention. Feature values are always rendered with the model marker.
- **How** (a) An architectural test asserting the verdict module does not import
  the model module, and that no model output type appears in the verdict's return
  type; (b) UI test asserting every feature-value figure carries *"szacunek
  modelu"*; (c) a test that deleting the fitted model entirely leaves verdicts
  working and only feature values unavailable — the strongest proof of separation.
- **Against** The module dependency graph; rendered components.
- **Falsified by** Any import path from verdict to model; a feature value rendered
  without its marker; verdicts breaking when the model is removed.

### V22 — Rezoning uplift carries its caveat (FR-40)

- **AC** The uplift figure is computed from strata contrast within the same gmina
  and period, and is never rendered without the caveat that it is an observed
  market gap and not a probability of rezoning.
- **How** Unit test on the contrast computation with known strata medians; UI test
  asserting the caveat text is present in the same visual block as the number and
  is not a tooltip.
- **Against** A fixture gmina with known buildable and agricultural medians.
- **Falsified by** The uplift rendered anywhere without the caveat; the uplift
  computed across different gminas or periods.

### V23 — Mix adjustment actually removes composition effects (FR-41, FR-42, D27)

- **AC** Given a synthetic series where **no price changes** but composition shifts
  hard (month 2 adds many large cheap agricultural plots), the plain median moves
  and the **mix-adjusted index stays flat within tolerance**. Given a series where
  prices move uniformly and composition is constant, both move together. Empty
  strata are carried with a gap marker, not dropped.
- **How** Two synthetic series constructed to isolate each effect, asserted
  directly. Plus a test that removing a stratum's observations does not change the
  basket weights.
- **Against** Hand-constructed synthetic series with known ground truth — the only
  way to test this, since real data confounds the two effects by definition.
- **Falsified by** The index moving when only composition changed; the index failing
  to move when prices changed; a dropped empty stratum shifting the weights.

### V24 — Prediction logging and scoring (FR-44..46, D35)

- **AC** Every estimate produced anywhere — UI, API, digest, notebook helper —
  writes a `valuation_log` row with inputs, output range, comparable count,
  widening step and `method_version`. Zero estimates go unlogged. Scoring computes
  calibration, bias, MAPE, coverage and widening profile **per `method_version`**.
  A method change increments the version and does not rewrite old rows.
- **How** (a) A test harness that calls every public estimate entry point and
  asserts a log row appears for each — this is the test that catches a new endpoint
  added later without logging; (b) `Δ` assertion comparing estimate-serving counts
  to log row counts; (c) scoring computed against a fixture of predictions with
  known realized outcomes, verifying each measure arithmetically; (d) a test that
  changing a comparable rule without incrementing `method_version` fails a check.
- **Against** A fixture prediction set with known realized prices, including cases
  inside and outside the predicted range.
- **Falsified by** Any estimate path that does not log; scoring that pools versions;
  a silent method change.

**Falsification of the valuation itself** (`05` §10), evaluated quarterly once
outcomes accumulate: a p25–p75 range containing ~90% or ~15% of realized prices
rather than roughly half; persistent directional bias surviving a version change;
regression feature values disagreeing in **sign** with comparable contrasts. Any of
these means the methodology is wrong, not merely imprecise, and the affected
figures come out of the UI until resolved.

## M1/M3 — Pipeline correctness (docs 06–08)

### V25 — `zoning_claim` is never reconciled into `buildability` (FR-48, `06` §1)

- **AC** The two remain separate columns. A listing whose advert says *"budowlana"*
  while planning data says agricultural retains both values and is displayed with
  the disagreement flagged. No code path writes `zoning_claim` into `buildability`.
- **How** (a) Unit test with a deliberately mislabelled fixture advert, asserting
  both values survive and the disagreement flag is set; (b) a static check that
  `buildability` is only ever assigned from planning-data sources; (c) `Δ` assertion
  counting rows where `buildability` was sourced from advert text — must be 0.
- **Against** Fixture adverts with known-false zoning claims.
- **Falsified by** A single `buildability` value traceable to advert text.

### V26 — Category maps are exhaustive (FR-49)

- **AC** Every source category encountered maps explicitly to a class or raises an
  alarm. No default assignment exists.
- **How** Unit test feeding an unmapped category and asserting an alarm plus no
  class assignment; a test that the map contains no wildcard or fallback entry.
- **Against** Recorded category lists per portal, plus a synthetic unknown category.
- **Falsified by** An unmapped category silently receiving a class.

### V27 — Extraction handles negation and proximity (FR-50, `06` §3)

- **AC** "brak prądu" → `absent`, never `present`. "prąd w drodze" → `at_boundary`,
  never `present`. "media w planach" → not `present`. Unmentioned attributes →
  `unknown`, never `absent`. Precision on `present` claims ≥ 0.95 on the labelled
  set, reported **per attribute**, not averaged.
- **How** (a) A dedicated negation test suite over the ≥30 negation/proximity
  adverts in the labelled set; (b) per-attribute precision/recall scoring against
  the 200-advert labelled set, failing if any attribute falls below threshold;
  (c) a test asserting no extractor can emit `absent` from absence of mention.
- **Against** The 200-advert hand-labelled set (`06` §4), personal fields scrubbed.
- **Falsified by** Any negated phrase extracted as positive; an unmentioned
  attribute stored as `absent`; per-attribute precision below threshold hidden by a
  good average.

### V28 — Area unit normalisation (FR-51, `06` §3.2)

- **AC** "12 arów" → 1200 m², "0,12 ha" → 1200 m², "1 200 m²" → 1200 m². Where
  advert and register disagree, the register wins and the source is recorded.
- **How** Unit tests per unit form including decimal comma and thousands space;
  a conflict test where the advert says 1200 m² and the register says 1450 m²,
  asserting 1450 is used and `area_source = 'register'`.
- **Against** Fixture adverts in each unit form; a parcel with a known register area.
- **Falsified by** A hectare listing priced as if in m² (a 100× error); the advert
  overriding the register.

### V29 — `location_precision` gates downstream use (FR-53, `07` §3)

- **AC** Nature attributes and parcel enrichment are computed **only** for
  `address` precision or better. A `pin`-precision listing has no
  distance-to-forest value at all — not zero, not null-rendered-as-zero, but
  absent, with the UI showing *"brak dokładnej lokalizacji"*.
- **How** (a) Unit test per precision level asserting exactly which attributes are
  populated; (b) `Δ` assertion that zero rows have a nature distance where
  precision is below `address`; (c) UI test for the absent state.
- **Against** Fixture listings at each precision level.
- **Falsified by** Any nature distance on a `pin` or coarser listing.

### V30 — Gmina assignment by TERYT, and the Skierniewice trap (FR-54, `07` §4)

- **AC** Assignment uses TERYT codes throughout; no code path resolves a gmina by
  name. Gmina Skierniewice (rural) and the city of Skierniewice resolve to
  different units. Budy Grabskie resolves to the rural gmina.
- **How** (a) Static check for gmina lookups by name string; (b) a known-answer
  test asserting Budy Grabskie → gmina Skierniewice (rural), and a listing in the
  city → the city unit, with different TERYT codes; (c) boundary-proximity flag
  test at 400 m and 600 m from a boundary.
- **Against** PRG boundaries; the confirmed location of Budy Grabskie.
- **Falsified by** The two Skierniewice units merging; any name-based lookup.

### V31 — Projections (FR-55, `07` §5)

- **AC** Distances and areas are computed in EPSG:2180, storage is EPSG:4326, every
  geometry column has a declared SRID. **Tolerance is scale-dependent**: ≤1 m at
  good-neighbour scale (<1 km) and ≤0.1% of the measured distance at ring scale,
  because the projection distorts by roughly a metre per kilometre — the flat
  "within 1 m" criterion was unachievable at 25 km and has been replaced.
- **How** Known-answer tests at both scales against an independent projection
  library, plus a **control asserting that computing in degrees fails** the check —
  otherwise a correct-looking test passes against a wrong projection; a schema test asserting no geometry column lacks an SRID;
  a test that a distance computed in degrees would fail the known-answer check.
- **Against** Two points with an independently known separation.
- **Falsified by** A distance off by the ~111 km/degree factor; an SRID-less column.

### V32 — The four times stay distinct (FR-56, `08` §1)

- **AC** `observed_at`, validity interval, `transacted_at` and `as_of` are separate
  fields, never conflated. Sales series plot on `transacted_at`; offering series on
  the validity interval. No series plots on `observed_at` or `as_of`.
- **How** (a) A fixture where `transacted_at` and `as_of` differ by 14 months;
  assert the transaction lands in the correct period and not the publication one;
  (b) a static check that charting queries never group by `observed_at`/`as_of`.
- **Against** RCN-shaped fixtures with a deliberately long publication lag.
- **Falsified by** A transaction appearing in the quarter it was published rather
  than signed.

### V33 — Offering prices behave as intervals (FR-57, `08` §2)

- **AC** A listing active January–June contributes to all six monthly medians, at
  the price in force in each. A crawl gap produces recorded uncertainty, never
  interpolation.
- **How** Simulated six-month snapshot fixture with a price cut in March and a
  three-day crawl outage in April; assert monthly contributions, the price used in
  each month, and that the April interval carries `boundary_uncertainty` rather
  than an invented change date.
- **Against** The synthetic six-month crawl fixture.
- **Falsified by** A listing counted only in its first month; an interpolated price
  across a crawl gap.

### V34 — Delisting is not sale, and incomplete periods are labelled (FR-58, FR-59)

- **AC** No metric labels a delisting as a sale; time-on-market is labelled time
  listed. Sales aggregates for periods still accumulating carry an incomplete
  marker, and the UI shows it.
- **How** (a) A static/textual check that no user-facing string pairs delisting
  with "sprzedane"; (b) a fixture where a recent quarter holds 30% of its eventual
  deeds, asserting the incomplete marker is set and rendered; (c) a regression test
  that the most recent quarter is never presented as final.
- **Against** A backdated RCN fixture simulating late arrival.
- **Falsified by** A chart showing a recent-quarter decline with no incompleteness
  marker — the specific trap `08` §4 describes.

## M2+ — Platform (docs 09–11)

### V35 — No bare numbers, anywhere (`09` §1, rule 7)

- **AC** Every aggregate rendered anywhere in the UI is accompanied by its sample
  size and range at equal prominence — not in a tooltip, not on hover.
- **How** An automated sweep over rendered component snapshots asserting that each
  element matching a numeric-aggregate pattern has sibling elements for `n` and
  range; a test that no such element's `n`/range sits inside a hover-only container.
- **Against** Snapshots of every data-bearing component in every state.
- **Falsified by** One aggregate rendered bare; one range reachable only on hover.

### V36 — All five component states exist (`09` §3)

- **AC** Every data-bearing component defines loading, empty, thin, stale and error
  states. Empty distinguishes "not yet crawled" from "no listings" from "out of
  scope". A failed sales query does not blank offering figures.
- **How** Snapshot tests per component per state; a test enumerating components and
  failing when any lacks a defined state; a partial-failure test asserting
  independent degradation.
- **Against** Component inventory.
- **Falsified by** A component with an undefined state; a loading dash readable as
  a value; one failed query blanking unrelated data.

### V37 — Polish formatting and terminology (`09` §4, `12`)

- **AC** Numbers use space thousands separators and comma decimals; dates
  `DD.MM.YYYY`; the terms in the glossary are used consistently, and protected
  terms are never loosely translated.
- **How** Formatting unit tests; a terminology lint over UI strings checking against
  the glossary's protected-term list.
- **Against** [`12-glossary.md`](./12-glossary.md).
- **Falsified by** `1,234.56` formatting; *cena ofertowa* rendered as "market price".

### V38 — Performance targets (`10` §2)

- **AC** Map < 1.5 s, gmina panel < 500 ms, plot page < 2 s, what-if < 1 s, daily
  pipeline < 4 h, aggregate recomputation < 30 min, measured on production-shaped
  data volumes (`10` §1).
- **How** A benchmark suite run against a seeded database at projected volume
  (40k listings, 15M snapshot rows), asserting each target; plus a test that the
  map path issues no query against the listing table.
- **Against** A synthetic database seeded to projected scale.
- **Falsified by** Any target missed at projected volume; a map query touching
  listings.

### V39 — Access control (`10` §5, O4)

- **AC** No endpoint, including the API, is reachable without passing the proxy
  gate. Postgres is not reachable from outside the host. The read role cannot
  write; the pipeline role is separate.
- **How** An integration test issuing unauthenticated requests to every route and
  asserting rejection; a connection test asserting Postgres refuses external
  connections; a permissions test asserting the read role's writes fail.
- **Against** The running deployment.
- **Falsified by** One reachable unauthenticated route; a successful external
  database connection; a successful write by the read role.

### V40 — Backups exist and are restorable (`11` §2, §3)

- **AC** A nightly encrypted dump lands off-VPS. The **quarterly restore drill**
  succeeds: a clean container restored from the latest dump passes all V1–V5
  invariants, row counts are within expected bounds, and `listing_snapshot`'s
  maximum `observed_at` is within 24 h of the dump. Restore completes within 2 h.
- **How** Automated: nightly backup presence and size-anomaly check; quarterly the
  full restore drill run as a scripted job that fails loudly.
- **Against** The actual production backup, restored — never a synthetic one.
- **Falsified by** A drill that fails, exceeds 2 h, or has never been run. **An
  untested backup counts as no backup.**

### V41 — The pipeline is fail-safe, not fail-open (`11` §4, `10` §3)

- **AC** A connector failure leaves the previous day's data intact and alarms; it
  never publishes partial results as complete. A failed Δ assertion **blocks** the
  coverage-page refresh. Steps 02–06 resume rather than restart after a crash.
- **How** (a) Fault-injection test failing a connector mid-run, asserting prior
  data intact, an alarm raised, and no aggregate published; (b) a test that a
  failing assertion prevents the coverage refresh; (c) a kill-and-resume test
  asserting no reprocessing from zero and no duplicate snapshot rows.
- **Against** A fault-injection harness over the real pipeline.
- **Falsified by** Partial data published as complete; a coverage page refreshed
  despite a failed assertion; a crash losing a day's collection.

### V42 — Recovery from a bad parse (`11` §6)

- **AC** After a parser fix, affected listings can be re-parsed from
  `raw_document` and aggregates recomputed for the window, **without** mutating
  `listing_snapshot`, producing a new metric generation and a coverage-page note.
- **How** A full drill: introduce a deliberately wrong parser on a fixture window,
  detect via V16, fix, re-parse, recompute, and assert the corrected values,
  unchanged snapshots, a new generation, and the visible note.
- **Against** A fixture window with known-correct expected values.
- **Falsified by** Re-parsing being impossible because raw payloads were not
  retained; a recomputation that mutates snapshots or silently overwrites history.

## v0 additions — methods the reshaped scope requires

Added after [`20-verification-strategy.md`](./20-verification-strategy.md). These
cover the new sources (D47), the biases in §3 and §5 of that document, and the
techniques that work where no oracle exists. Tier references are to `20` §2.

### V43 — Corpus completeness against the source's own count (F5, tier B)

- **AC** For each portal query, the number of listings we collect matches the
  count the source itself reports for that query, within a small tolerance for
  churn during the crawl. A systematic shortfall — pagination stopping early,
  a filter silently excluding results — raises an alarm and blocks publication.
- **How** (a) Parse the source's stated result count and compare to rows emitted,
  per query, every run, as a `Δ` assertion; (b) a unit test with a fixture whose
  pagination truncates at page 3 of 10, asserting the alarm fires.
- **Against** The source's own reported totals; a deliberately truncated fixture.
- **Falsified by** Collecting materially fewer rows than the source reports with no
  alarm. **This is the highest-value single check in the ingestion path** — a
  silently partial corpus still produces confident medians.

### V44 — Sort-order independence (F6, tier B)

- **AC** The same query crawled under two different sort orders yields
  statistically indistinguishable price distributions. If they differ, our sample
  is biased by collection order, not by the market.
- **How** A scheduled comparison run — crawl one representative query sorted by
  price ascending and by date, compare the resulting distributions; alarm on a
  material divergence.
- **Against** The source itself, queried two ways.
- **Falsified by** Distributions that differ beyond sampling noise, which means the
  corpus depends on how we asked rather than what exists.

### V45 — Stock and flow are computed and labelled separately (`20` §5)

- **AC** Every aggregate is available as **stock** (all active listings) and
  **flow** (first seen within the window), each labelled. **Flow is the headline**
  (D56); stock is shown alongside. Neither is ever rendered
  without saying which it is. The two are never averaged.
- **How** (a) Unit test on a fixture where a long-standing overpriced listing sits
  alongside recent cheaper ones: assert stock median > flow median by the
  constructed amount, and that both are returned; (b) a UI test asserting the label
  is present on both; (c) an architectural check that no function returns an
  unlabelled aggregate.
- **Against** A hand-constructed fixture with a known stock/flow gap.
- **Falsified by** An unlabelled aggregate anywhere; the two blended; only one
  computed.

### V46 — Auction and tender prices never blend with asking prices (F9, O19)

- **AC** Bailiff/bankruptcy starting prices and KOWR tender prices carry a distinct
  price kind and never enter an aggregate with portal asking prices. An auction
  starting price is a statutorily-derived floor, not an ask, and mixing them would
  drag every median down and look like a market movement.
- **How** (a) A schema constraint plus a `Δ` assertion that no aggregate's source
  set spans price kinds; (b) a unit test with an auction fixture priced far below
  the asking distribution, asserting the asking median is unchanged by its
  presence; (c) an architectural test that the aggregation key includes price kind.
- **Against** A fixture combining all three kinds with deliberately divergent values.
- **Falsified by** Any aggregate whose inputs span kinds; a median that moves when
  auction rows are added to an asking-price query.

### V47 — Metamorphic properties of the numeric core (`20` §4.3)

- **AC** All of the following hold on generated inputs: doubling every price
  doubles the median exactly; scaling price and area together leaves zł/m²
  unchanged; permuting input order leaves output identical; adding an exact
  duplicate leaves the post-dedup median and `n` unchanged; adding an observation
  outside the area band leaves the estimate unchanged; adding one of a different
  buildability class leaves the estimate unchanged.
- **How** Property-based tests over generated fixtures, one per relation.
- **Against** No oracle needed — these are relations between outputs, which is
  precisely why they work where ground truth is unavailable.
- **Falsified by** Any relation failing. The out-of-band and wrong-class cases are
  the load-bearing ones: they catch a filter that is silently ignoring its
  arguments, which fixture-based tests can pass straight through.

### V48 — Differential test of percentile logic (F11, tier A)

- **AC** Our median, p25 and p75 agree with a reference implementation
  (numpy/pandas) on random inputs, including even-length arrays, ties, and n=1,2,4,5.
- **How** Property-based comparison against the reference across generated arrays.
- **Against** The reference implementation.
- **Falsified by** Any disagreement. Percentile conventions differ; adopting one
  silently produces slightly-wrong ranges forever.

### V49 — Golden-corpus regression (`20` §4.5) — **NOT SELECTED for v0 (D58)**

> Retained as a specification. Dropping it leaves the drift-detection gap recorded
> as O26: nothing else in the suite notices output changing quietly over time.


- **AC** A frozen, scrubbed crawl of one gmina produces byte-stable aggregate
  outputs. Any change to normalization, dedup or aggregation that alters them fails
  the test until the diff is explained in the commit message.
- **How** Golden-file comparison in CI.
- **Against** The committed corpus and its recorded expected outputs (gmina choice
  is O24).
- **Falsified by** Silent output drift — the main defence against slow degradation
  that no single test notices.

### V50 — Quarantine composition monitoring (F12)

- **AC** Quarantine rate is tracked **per reason**, not in aggregate. A spike in one
  reason alarms, because it usually means a whole segment is being silently dropped
  — every hectare-stated plot, or every listing from one agency template.
- **How** `Δ` assertion on per-reason rates against a rolling baseline.
- **Against** The live quarantine table.
- **Falsified by** A segment disappearing from the corpus without an alarm.

### V51 — Leave-one-out cross-validation (D54, D57, `20` §6.1)

> Replaces the pre-registered known-plot check, which the owner declined (D57).
> This is stronger, not a fallback: it is tier A/B rather than tier C, automatic,
> and re-runnable on every change.

- **AC** For every listing in the corpus: remove it, build its comparable set from
  the remainder, produce an estimate, and compare to its actual asking price.
  Reports coverage, hit rate (share falling inside the predicted range), median
  absolute percentage error, and tail (share missed by more than 2x). Hit rate
  should approach the range's nominal coverage — a p25–p75 range containing ~90%
  or ~15% of actual prices is broken in opposite directions.
- **How** A CI job over the committed corpus, re-run on any change to comparable
  selection, banding or aggregation. Thresholds are set from the first run's
  actuals (O25), not guessed in advance; subsequent regressions against them fail.
- **Against** The corpus itself, with each listing held out in turn.
- **Falsified by** Hit rate far from nominal; a fat tail of >2x misses; coverage
  collapsing when the comparable rules change.
- **Limitation** Proves the estimator predicts *asking* prices consistently, not
  that asking prices are fair. A uniformly overpriced corpus would score perfectly.
  Price *level* is constrained separately by V16 (GUS cross-check); this constrains
  internal consistency. Neither is tier D.

### V51b — Zero-effort human spot check — **WITHDRAWN (D63)**

> The owner cannot price plots, so a verdict rating would be uninformed input
> presented as evidence. Replaced by V51c.

### V51c — Comparability feedback (D63, `21` §7)

- **AC** Each comparable in a set carries a "nie pasuje" control. Marking one
  removes it and recomputes the estimate, and the exclusion is logged with the
  subject, the comparable, and the resulting change in the estimate. Repeated
  exclusions of the same *kind* of comparable are surfaced as a signal that a
  selection rule is wrong.
- **How** (a) Unit test that exclusion recomputes and logs; (b) a report over the
  exclusion log grouping by attribute, so a systematic pattern is visible.
- **Against** The owner's comparability judgement — which is answerable without
  pricing expertise, unlike a verdict rating.
- **Falsified by** Exclusions that do not recompute; a pattern of exclusions never
  feeding back into the selection rules.

### V52 — Mutation testing of the numeric core (`20` §4.8, **in scope — D58**)

- **AC** Deliberate faults injected into normalization, aggregation and estimation
  — swapping p25 and p75, dropping a filter clause, flipping a comparison — are
  caught by the existing suite.
- **How** A mutation-testing run over those modules only.
- **Against** The test suite itself.
- **Falsified by** A surviving mutant in the numeric core. A suite that passes
  against a mutated median function is not testing the median.

## Coverage gaps found by audit — methods for FR-61..72

> Answering *"is every feature supported by a validation method?"* mechanically
> produced **no**. KOWR, auctions, gmina BIP, the good-neighbour test and the
> purchasability badge appeared **zero times** in the PRD, and several v0 work
> items had no method at all. FR-61..72 close the rule-1 gap; V53–V62 close the
> rule-4 gap.

### V53 — KOWR connector (FR-61)

- **AC** Notices for both rings are collected, normalized, and carry
  `price_kind = 'tender'`. Every record resolves to a gmina TERYT and an area in
  m². Notices without a usable price or area are quarantined with a reason, not
  dropped. The corpus count matches KOWR's own listing count for the same filter.
- **How** Integration test against a recorded fixture per notice layout; `Δ`
  count-agreement assertion (as V43); quarantine-reason assertion (as V50).
- **Against** Recorded KOWR fixtures, including at least one notice with no stated
  area and one tender with a price range rather than a figure.
- **Falsified by** A KOWR record entering an asking-price aggregate; a silently
  dropped notice; an unresolved TERYT.

### V54 — Auction connector (FR-62)

- **AC** Bailiff and bankruptcy notices are collected with
  `price_kind = 'auction_start'`, the **statutory fraction** of the valuation
  recorded where stated, and the auction date captured. An auction starting price
  never enters an asking-price aggregate.
- **How** (a) Fixture-based parse tests per source layout; (b) the V46 separation
  test; (c) a test that a notice stating "cena wywoławcza 3/4 sumy oszacowania"
  records both the figure **and** the fraction, since the fraction is what makes
  the number interpretable.
- **Against** Recorded auction fixtures from whichever sources O16 selects.
- **Falsified by** A starting price treated as an ask; a lost fraction; an auction
  whose date is not captured, since a past auction is not supply.

### V55 — Gmina BIP connector (FR-63)

- **AC** Each of the ~50 gminas in the two rings is either **covered** by a working
  parser or **explicitly listed as uncovered**, with a reason. There is no silent
  middle: a gmina we cannot parse is reported as a coverage gap, never as a gmina
  with no land for sale.
- **How** (a) A per-gmina coverage report, asserted to account for **every** gmina
  in scope; (b) fixture tests per distinct bulletin layout; (c) a `Δ` assertion
  that the covered-gmina count matches the parser registry.
- **Against** Recorded BIP fixtures per layout family.
- **Falsified by** A gmina silently absent from both the covered and uncovered
  lists — the specific failure that would make an empty area look like a cheap one.

### V56 — v0 dedup, weaker but real (FR-70)

- **AC** Exact duplicates — same source, same external id, or identical
  (area, price, gmina) triples — collapse to one record with a `duplicate_count`.
  **No labelled-set scoring** is claimed, and the coverage page states that dedup
  is exact-match only, so the duplicate rate is *unknown rather than measured*.
- **How** (a) Unit tests on the exact-match rules; (b) metamorphic: adding an exact
  duplicate leaves the median and `n` unchanged (V47); (c) a test that the UI/report
  carries the "exact-match only" caveat.
- **Against** Fixtures with exact duplicates and with near-duplicates that v0 is
  **not** expected to catch.
- **Falsified by** An exact duplicate surviving; a near-duplicate being merged
  (v0 must not over-merge); a claim of a measured duplicate rate anywhere.

### V57 — Raw payload storage and re-parse (FR-72)

- **AC** Every fetched document is stored with source, URL, fetch time and content
  hash; identical re-fetches do not duplicate storage. A parser fix can re-derive
  listings for a past window from raw payloads and recompute aggregates **without**
  mutating snapshots.
- **How** (a) Unit test on hash-based deduplication of stored payloads; (b) a
  re-parse drill on a fixture window with a deliberately wrong parser, asserting
  corrected outputs, unchanged snapshots and a recorded correction.
- **Against** A fixture window with known-correct expected values.
- **Falsified by** Re-parse being impossible; snapshots mutated during recovery.

### V58 — List-page-first sufficiency (FR-68, D40)

- **AC** The list page yields price and active status accurately enough that
  detail-page fetches can be limited to first sight and observed changes. Where a
  list page's price disagrees with its detail page, the **detail page wins** and
  the disagreement is counted.
- **How** (a) A sampled reconciliation: fetch detail pages for a random subset and
  compare to what the list page reported; assert the disagreement rate stays below
  a threshold set from the first run; (b) a test that a price change visible only
  on the detail page is still caught on the next cycle.
- **Against** A live sampled comparison, plus fixtures with a deliberate list/detail
  mismatch.
- **Falsified by** A material disagreement rate with no alarm — it would mean the
  cheap path is quietly wrong, and the cheap path is nearly the whole corpus.

### V59 — v0 surface honesty (FR-71)

- **AC** The Streamlit app obeys `09` §1: no aggregate without `n` and spread; every
  price labelled with **type and kind**; stock and flow always distinguished;
  verdict collapsed by default (`21` §U5); `unknown` rendered explicitly rather than
  blank.
- **How** Output-snapshot tests over the app's rendering helpers — the same
  assertions V35/V36 make of the full UI, applied to the surface v0 actually ships.
- **Against** Rendered app outputs for each state, including thin data,
  no data, and stale data.
- **Falsified by** A bare aggregate; an unlabelled price kind; a blank where
  `unknown` belongs.

### V60 — WZ good-neighbour test (FR-65)

Specified in [`19-legal-and-feasibility.md`](./19-legal-and-feasibility.md) §1.3
and registered here so the coverage table sees it. Summary: 10 hand-checked
parcels per ring, half with obvious built neighbours and half clearly isolated;
the computed signal matches orthophoto inspection; **no parcel with missing
building data is ever reported `unlikely`**; no verdict renders without its
disclaimer.

### V61 — Farmland purchasability badge (FR-66)

Specified in [`19-legal-and-feasibility.md`](./19-legal-and-feasibility.md) §2.3
and registered here. Summary: badge present for every agricultural register class,
absent for every non-agricultural one, and an unknown class produces neither a
badge nor an implication that the plot is unrestricted. Copy thresholds are
citation-checked against the consolidated act on the date shipped.

### V62 — Flow window is defined, ratified and visible (FR-67)

- **AC** The "flow" window has a single defined length, stated wherever a flow
  figure appears. Changing it is a versioned method change, not a silent tweak.
- **How** (a) Unit test that the window is read from configuration, not hardcoded
  at call sites; (b) a rendering test that the window length appears alongside every
  flow figure; (c) sensitivity check — report flow medians at several window
  lengths, so the choice can be made on evidence (O27).
- **Against** Fixtures spanning several months.
- **Falsified by** A flow figure with no stated window; two call sites using
  different windows.

---

## v0 work item → validation coverage

The mechanical answer to *"is every feature covered?"*. Regenerate this table when
the work plan changes.

| `18` §6 item | Validation |
|---|---|
| 0 robots.txt gate | V14 + **decision recorded in `00`** (a gate, not a feature) |
| 1 Repo, Docker, migrations, config | V7 (anchor privacy); migrations covered by V1's constraint-existence test |
| 2 Schema + `price_type` CHECKs | V1, V2 |
| 3 PRG + TERYT, both rings | V6, V30, V31 |
| 4 GUS BDL client | V13, V16 |
| 5 Portal connector | V12, V14, V43, V44, **V57**, **V58** |
| 6 Parse + normalize | V10, V28, V50 |
| 7 KOWR connector | **V53**, V46 |
| 8 Auction connector | **V54**, V46 |
| 9 Dedup (v0 form) | **V56**, V47 |
| 10 Aggregates, stock + flow | V4, V45, V47, V48, **V62** |
| 11 Streamlit app | **V59**, V51, **V51c** |
| 12 Choropleth + table | **V59** (same helpers); V35–V37 apply if a real frontend arrives |
| 13 Gmina BIP | **V55** |
| 14 Parcels + good-neighbour | **V60** (`19` §1.3) |
| 15 Purchasability badge | **V61** (`19` §2.3) |
| Cross-cutting | V5 provenance, V51 LOOCV, V52 mutation, V47 metamorphic, V48 differential |

**Still uncovered, deliberately:** the drift-detection gap from dropping
golden-file regression (O26), and everything at verification tier D — whether the
valuation is actually right — which no v0 method can reach.

## Deferred — method required before implementation

These have no validation method yet. Per rule 5, one must be written here before
any of them is implemented — they are listed so the gap is explicit rather than
discovered later.

| Feature | PRD | Note for the method |
|---|---|---|
| Travel time to anchors | FR-21 | Known-answer test: hand-checked drive times for ~10 plots against an independent routing source |
| Choropleth and filters | FR-30 | Must test that thin-data gminas render hatched with visible spread, and that "no supply" is visually distinct from "thin supply" |
| Parcel resolution via ULDK | FR-14 | Known-answer test against parcels with published identifiers |
| Zoning and `unknown` as terminal | FR-16, FR-17 | Must prove `unknown` is never inferred: a plot surrounded by buildable neighbours with no plan data must still read `unknown` |
| Nature attributes | FR-19, FR-20 | Distances hand-checked against a map; protected status must render as both amenity and constraint |
| Comparable-set engine | FR-26, FR-36 | Needs a hand-picked "correct comparables" set for ~5 subject plots as ground truth, plus a test that exclusion recomputes |
| Asking-vs-sales spread | FR-10 | Must show both sample sizes and both as-of dates; test that differing periods are not presented as simultaneous |
| RCN connector | FR-31 → M4 | Method depends on V9's outcome |
| Size adjustment | O6 — **closed**: measure elasticity, adjust only if LOOCV shows size-correlated error | Needs an elasticity-reporting check |
| Standard-plot benchmark | O7 — **adopted**; rendered in `21` §2.2 | Needs an FR and a method |
| Read-only query layer | FR-47 (post-v0) | Needs a stability contract: which views are guaranteed, and what changing them requires |
| Digest generation | FR-47, O8 | Must test that data-quality events appear alongside market events — a silent pipeline failure must not read as a quiet market |
| Saved searches and alerts | J4 | Needs stable listing identity across relistings |
| Housing extraction | `06` §5 | Attribute list must be written before any housing extractor exists |

---

## Verification cadence summary

| When | What runs |
|---|---|
| Every commit | V1–V4, V6–V8, V10–V14 unit and integration tests; V17–V37 unit, architectural and snapshot tests |
| Every pipeline run | All `Δ` assertions: V1, V2, V5, V8, V10, V11, V12, V15, V16, V18, V24, V25, V29 |
| Every deploy | V1–V5 against the live database; V39 access control |
| Daily | `⏱` V8 connector freshness, V15 coverage, V16 cross-source agreement, V40 backup presence |
| Quarterly | Fixture re-recording; V11 and V27 labelled-set refresh; V10 manual 200-record audit; **V40 restore drill**; V24 valuation scoring; `05` §10 methodology falsification review |
| Before a benchmark-affecting change | V38 performance suite at projected volume |
| Once, before its milestone | V9 (RCN research) |
| After any parser incident | V42 recovery drill |

## Coverage of requirements

Every FR in [`02-prd.md`](./02-prd.md) §8 maps to at least one validation method.
The mapping is the gate: an FR with no V entry cannot be implemented (rule 5).

| FR range | Validation |
|---|---|
| FR-1..6 ingestion | V8, V12, V14, V41 |
| FR-7..10 price types | V1, V2, V3, V20 |
| FR-11..14 normalization | V10, V11, V28 |
| FR-15..21 enrichment | V6, V29, V30, V31, deferred table |
| FR-22..23 config & privacy | V7 |
| FR-24..28 analytics | V4, V5, V23 |
| FR-29..30 presentation | V35, V36, V37 |
| FR-31 research | V9 |
| FR-32..38 estimator | V17, V18, V19, V20 |
| FR-39..40 model separation | V21, V22 |
| FR-41..43 mix adjustment | V23 |
| FR-44..47 logging & scoring | V24 |
| FR-48..52 taxonomy & extraction | V25, V26, V27, V28 |
| FR-53..55 geocoding | V29, V30, V31 |
| FR-56..60 temporal | V32, V33, V34 |
| FR-61..63 off-portal sources | V53, V54, V55 |
| FR-64 price kinds | V46 |
| FR-65..66 feasibility | V60, V61 |
| FR-67 stock/flow | V45, V62 |
| FR-68 list-page-first | V58 |
| FR-69..70 acceptance, v0 dedup | V51, V56 |
| FR-71..72 surface, raw payloads | V59, V57 |
