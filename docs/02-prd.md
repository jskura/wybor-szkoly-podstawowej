# PRD — Land & Housing Price Comparison

Status: **draft v0.3** · Owner: jskura · Date: 2026-08-07
Inputs: [`00-decisions.md`](./00-decisions.md) (D1–D63) · [`01-user-journeys.md`](./01-user-journeys.md)
Validation methods: [`04-validation.md`](./04-validation.md) — required before any implementation ([`CLAUDE.md`](../CLAUDE.md) rule 4)

> ## ⚠ Read this first — scope changed after the audit
>
> [`17-assumption-audit.md`](./17-assumption-audit.md) found seven internal
> contradictions and a long list of choices I made without asking. The scope
> decision that followed (D38) is:
>
> **The plan of record is [`18-v0-scope.md`](./18-v0-scope.md) — a ~26–29 day
> version covering both 25 km anchor rings, off-portal sources and the
> feasibility layer.** This PRD describes the *full* system,
> which is now a possible future rather than the current plan. Requirements below
> are still the reference for anything we build, but they are not a commitment to
> build all of it.
>
> Corrections applied in v0.3: mix adjustment restricted to powiat level and above
> (D41); the "never a point estimate" rule restated (D42); the crawl budget made
> arithmetically possible (D40); fabricated personas and the impossible five-user
> testing programme removed (D43); infrastructure sizing corrected (D44).

Changes from v0.1→v0.2: sales prices promoted to first-class (D3); Elbląg area
added (D9); anchor rings (D7, D11); always-show-with-spread (D13, D17, D18);
nature attributes (D12, D22); anchors in gitignored config (D19, D21).

---

## 1. Problem

Someone buying land in these areas has to answer questions no existing tool
answers:

1. **"Where does my budget work?"** Portals filter listing-by-listing. There is no
   view of the price surface across the ~530 gminas in scope.
2. **"May I even build here?"** Buildability sits in planning documents that are
   only now becoming machine-readable, and it is the single biggest determinant of
   what a plot is worth.
3. **"Is this price real?"** Asking prices are anchors, not values. What plots
   actually *sold* for sits in a public register almost nobody reads.

The gap is widest for **land**: two plots 200 m apart can differ 5× in price per m²
for reasons — zoning, road access, utilities, soil class, protection status — that
listings state inconsistently or not at all.

## 2. What we are building

A data product that continuously collects **both offering prices and actual sales
prices** for land and housing across the target areas, normalizes them to
comparable units, enriches them with the parcel, planning and nature context that
determines value, and presents the result as a map you explore, a verdict on a
single plot, and a side-by-side board — with source, as-of date, sample size and
spread behind every number.

### 2.1 The two price types (rule 5)

This is the product's spine, not an implementation detail.

| | **Offering price** (*cena ofertowa*) | **Actual sales price** (*cena transakcyjna*) |
|---|---|---|
| Source | Listing portals | RCN/RCiWN notarial records; GUS BDL aggregates |
| Frequency | Daily | Quarterly, with lag |
| Granularity | Individual plot | Parcel or precinct (RCN); powiat (GUS) |
| Bias | Upward — an ask, not a price | None, but historical and incomplete |
| Coverage | Only what is currently for sale | Only what has already sold |

Neither substitutes for the other. **Every price in the data model, the API and
the UI is explicitly labelled with its type.** They are never averaged together,
never silently swapped when one is missing, and the gap between them is a
first-class feature (J5) rather than a discrepancy to reconcile away.

## 3. Goals / non-goals

**Goals (v1)**
- G1 — Identify gminas where a given budget buys a buildable plot at acceptable
  travel time, in one session. *(J1)*
- G2 — For any plot in scope, produce a price-per-m² verdict against a transparent
  comparable set, plus buildability, nature and risk attributes. *(J2, J3)*
- G3 — **Both price types available** for every target area at the finest
  granularity the free sources allow, always labelled. *(J5, J7, rule 5)*
- G4 — Every number is auditable: source, as-of date, sample size, spread, method.
  Nothing suppressed, nothing shown bare. *(J8, rule 6)*
- G5 — Coverage of ≥90% of gminas in the two 25 km anchor rings with at least one
  land observation per month, and ≥70% of all in-scope gminas per quarter.

**Non-goals (v1)**
- Voivodeships beyond scope (§6). Region is a pipeline parameter, but nothing ships.
- Public launch, commercial use, a paid API, or reselling listing content (D1).
- Paid data of any kind (D2).
- Mortgage calculators, agent CRM, native mobile app, listing your own plot,
  contacting sellers through us.
- Housing beyond what J6/J7 need — flats and houses are collected from day one so
  history accrues, but get no dedicated UI in v1.
- Legal certainty. Every buildability statement is informational; the binding
  document is the *wypis i wyrys* from the gmina.

## 4. Users

**The owner, buying land to build on** (D37). Audience is the owner plus a few
known people (D1).

The earlier persona — "Marek & Ania", a couple in their 30s with a 150–350k plot
budget — was **fabricated by me and has been removed** (audit B2). Nothing in this
document should be justified by reference to an invented user. Where a requirement
needs a user motivation, it cites a journey in
[`01-user-journeys.md`](./01-user-journeys.md), which is written against the real
decision: find and buy a buildable plot in one of the two anchor areas.

Secondary interest: land as an investment (the buildable-vs-agricultural gap).
Out: valuing land already owned (D36 — Budy Grabskie 53 is a place visited, not
owned).

## 5. Success metrics

> **Corrected (D43).** The previous table targeted *"≤10 min to shortlist
> (moderated test, 5 users)"* and *"≥3 of 5 users say the verdict changed their
> view"*. There is no pool of five test users for a private tool — these were
> leftovers from imagining a broader product (audit A6). They are replaced with
> checks the owner can actually run alone.

**Hard invariants** — these are not targets, they are conditions of shipping:

| Metric | Required |
|---|---|
| Aggregates displayed without sample size **and** spread | **0** |
| Prices displayed without a price-type label | **0** |
| Buildability values sourced from advert text | **0** |
| Personal addresses in git or fixtures | **0** |

**Coverage and quality**, measured and reported rather than targeted — the honest
position is that we do not yet know what is achievable, and pretending otherwise
produced the invented numbers the audit found:

| Metric | Status |
|---|---|
| Gminas in anchor rings with ≥5 listings | **Measure in v0**, then set a target |
| In-scope powiats with a GUS sales series | 100% expected — free and guaranteed |
| Powiats with parcel-level RCN | Unknown until the O2 research |
| Listings resolved to a parcel | Unknown until parcel work exists |
| Duplicate rate, outlier rate, extraction precision | Provisional targets in `04`, all unratified (O11) |

**Product value** — the v0 checks in [`18-v0-scope.md`](./18-v0-scope.md) §7.
Since D63 the owner cannot price plots, so the primary test is leave-one-out
cross-validation (V51), with the GUS comparison (V16) as the only external
constraint on price level.

Not metrics: traffic, sign-ups, revenue.

## 6. Scope

### 6.1 Geography (D7, D9, D10, D11)

Three target units, region-wide exploration within each:

| Unit | Approx. gminas | Role |
|---|---|---|
| **łódzkie** | ~177 | Contains anchor A |
| **mazowieckie** | ~314 | Contains the Warsaw travel anchor |
| **Elbląg area** — powiat elbląski + m. Elbląg | ~10 | Contains anchor B |

Two **anchor areas** get priority for enrichment, daily crawl depth and QA:

- **Anchor A — Budy Grabskie**, gmina Skierniewice, powiat skierniewicki, łódzkie.
  In Bolimów Landscape Park on the Rawka. 25 km ring.
- **Anchor B — Elbląg**, warmińsko-mazurskie. 25 km ring.

Anchors set *priority*, not *scope*: the full map of all three units still ships
(D10). Aggregation levels: voivodeship → powiat → gmina → (later) obręb.

### 6.2 Asset classes (D6)

Priority order, land first:
1. `land_building` — działka budowlana
2. `land_recreational` — działka rekreacyjna
3. `land_agricultural` — działka rolna
4. `land_forest_other` — działka leśna / inna
5. `house` — dom, secondary market · 6. `flat` — mieszkanie, secondary market

Land 1–4 are v1 UI. Housing 5–6 is ingested from day one, surfaced in J6/J7 only.
Out of scope entirely: commercial/industrial, rental data.

## 7. Data sources

Details in [`03-data-sources.md`](./03-data-sources.md). All free (D2).

| Layer | Source | Price type | Confidence |
|---|---|---|---|
| Listings | Portals, daily | **Offering** | High volume, upward bias |
| RCN/RCiWN | Registry, GML from 2021-07-31 | **Sales** | Authoritative, access varies by county — see FR-31 |
| GUS BDL | API, powiat-level, quarterly | **Sales** | Authoritative, coarse, guaranteed free |
| Parcels | GUGiK ULDK + county EGiB WFS | — | Good, uneven by county |
| Zoning | Rejestr Urbanistyczny / plan ogólny / MPZP | — | Incomplete until 2029 |
| Boundaries | GUGiK PRG + TERYT | — | Stable |
| Nature | OSM landcover/water, GDOŚ protected areas | — | Good |
| Constraints | Flood hazard, soil class, road access | — | Good |
| Routing | OSM + self-hosted OSRM | — | Good |

**Principle:** registries are authoritative, listings are high-frequency. Where
they disagree, both are shown, labelled by type, and the gap is the feature.

## 8. Functional requirements

### 8.1 Ingestion

- **FR-1** Per-source connectors: scheduled, incremental, resumable, writing raw
  immutable payloads with fetch timestamp and source URL.
- **FR-2** Respect `robots.txt` and per-host rate limits; honest user agent;
  never bypass authentication or anti-bot measures. See §12.
- **FR-3** **Snapshot semantics** — every crawl records observed state per listing.
  Price changes, delisting and relisting are derived from the snapshot series.
- **FR-4** Daily crawl cadence (D14), off-peak, with backoff, using the
  **list-page-first strategy** (D40): list pages give price and active status for
  the whole corpus, detail pages are fetched only for new or changed listings.
  Without this the politeness policy and daily refresh are incompatible by ~18×
  (audit A1, `10` §2.1).
- **FR-5** Prefer official APIs over scraping wherever both answer the same question.
- **FR-6** Source health record per connector: last success, item count, schema-drift
  alarm. A connector silently returning zero items must alarm, not flatten a median.

### 8.2 Price types (rule 5)

- **FR-7** Every price-bearing row carries a non-null `price_type ∈ {offering, sales}`.
  Enforced as a database constraint, not a convention.
- **FR-8** Offering and sales prices are never averaged into a single figure, and
  never substituted for one another when one is missing.
- **FR-9** Every price rendered in the UI or returned by the API is labelled with
  its type, in Polish (*cena ofertowa* / *cena transakcyjna*).
- **FR-10** Asking-vs-sales spread per gmina (or the finest unit available):
  `median(offering) − median(sales)`, shown with both sample sizes and both as-of
  dates, since the two are measured over different periods.

### 8.3 Normalization

- **FR-11** Canonical schema per listing: price PLN, area m², asset class, zoning
  claim, utilities, road access, coordinates, gmina TERYT.
- **FR-12** Compute `price_per_m2`. Land area outside **[300 m², 200 000 m²]** and
  price outside [1, 100 000] PLN/m² are **flagged and kept visible, never silently
  dropped** (O12) — the earlier 50 ha cap would have discarded legitimate farmland.
  Records with no usable price or area, or "zapytaj o cenę" placeholders, are
  quarantined with a reason.
- **FR-13** **Deduplication** — the same plot is routinely listed by 3–6 agencies.
  Match on rounded area, price band, geohash-6, title shingles, image perceptual
  hash, hashed seller contact. Group into a `plot_cluster` with a canonical record
  and a `duplicate_count` (itself a motivated-seller signal).
- **FR-14** Geocode to gmina TERYT; where a parcel identifier appears in the text,
  resolve via ULDK and prefer that geometry over the portal's pin.

### 8.4 Enrichment

- **FR-15** Parcel attributes: registry area (not advert area), land-use class,
  soil class, precinct.
- **FR-16** Zoning: designation from plan ogólny/MPZP, plus derived `buildability ∈
  {buildable, conditional, agricultural, unknown}`.
- **FR-17** **`unknown` is a terminal state** (D20). It is never inferred from
  neighbours or land-use class, never defaulted to buildable, and renders in the UI
  as *"brak danych — sprawdź w gminie"* with a pointer to obtaining the wypis i wyrys.
- **FR-18** Constraints: flood zone, protected area, class I–III farmland, no public
  road access, transmission-line easement.
- **FR-19** **Nature attributes** (D22), each stored and displayed separately:
  distance to nearest forest edge; distance to nearest water (river, lake, lagoon);
  protected-area status; distance to nearest major road and railway.
- **FR-20** Protected-area status is presented as **both amenity and constraint** —
  it is genuinely both, and showing only one framing misleads.
- **FR-21** **Travel time** by road to each configured anchor address (D19).

### 8.5 Configuration and privacy

- **FR-22** Routing anchors live in `config/anchors.yml`, which is **gitignored**
  (D21). The repo ships `config/anchors.example.yml` with placeholder addresses.
  The real file exists only on the owner's machine and the VPS.
- **FR-23** No personal address, name or phone number is ever committed to git or
  written to a shared artifact. Seller contacts are stored only as salted hashes,
  for dedup (FR-13).

### 8.6 Analytics

- **FR-24** Aggregates per (gmina × asset class × price type × month): count,
  median, p25, p75, min, max, mean.
- **FR-25** **Always show, always flag** (rule 6, D13/D17/D18). No aggregate is
  suppressed. Every aggregate is returned and rendered with its sample size **and**
  its spread — IQR normally, min–max when n < 5. An aggregate without both is a
  bug, enforced at the API boundary.
- **FR-26** Comparable-set engine: select by geography (same gmina, else radius),
  zoning class, area band ±50%, recency ≤12 months; return the set, its median, its
  spread, and the subject's deviation. User can exclude comparables and recompute.
- **FR-27** Time series per gmina/powiat, **both price types plotted separately**,
  with sample-size bars, nominal and CPI-adjusted.
- **FR-28** (post-MVP) Hedonic model for a residual-based "underpriced" flag,
  shipped only if it beats the gmina-median baseline on held-out data. Never an
  opaque score.

### 8.7 Presentation

- **FR-29** Polish UI, English code and docs (D15). Domain terms used correctly:
  *działka budowlana*, *plan ogólny*, *wypis i wyrys*, *media*, *droga dojazdowa*,
  *cena ofertowa*, *cena transakcyjna*.
- **FR-30** Map view (choropleth by gmina, filter-driven), plot page (verdict card,
  comparables, risk and nature badges, price history, negotiation panel),
  comparison board (2–4 plots, differences highlighted, weighted ranking with
  visible reasoning, export), trends view, and a coverage/method page.

### 8.8 Valuation and analytics (D26–D33)

Method is specified in [`05-analytics-methodology.md`](./05-analytics-methodology.md);
these are the requirements it must satisfy.

- **FR-32** **Estimator**: `estimate(features, place, price_type, as_of)` returns
  `{low, median, high, n, basis, widening_step}`. **A median is never returned,
  stored or displayed without its range and sample size** (D32, restated by D42).
  The earlier phrasing — "no point estimate, ever, including internally" —
  contradicted the `median` field it also mandated (audit A4).
- **FR-33** The estimator works with **no listing involved** — features may be
  supplied directly, so the product answers "what should a plot like this cost
  here" and not only "is this listing fair" (D26, D31).
- **FR-34** **Comparable-set median is the only source of a verdict** (D30).
  Comparable sets match buildability **exactly** and never widen across it (D28),
  and never widen across price type or the `unknown` boundary.
- **FR-35** The **widening step** reached is recorded and displayed. An estimate
  built from a 25 km radius is a weaker claim than a same-gmina one and must be
  legible as such.
- **FR-36** The comparable set is fully **enumerable and editable** — every
  contributing plot is listed, and excluding one recomputes the estimate.
- **FR-37** Both `expected_offering` and `expected_sales` are produced and shown
  **separately**, with the gap (rule 5, D29). A missing sales estimate renders as
  absent, never filled from the offering estimate.
- **FR-38** The verdict is expressed **relative to the range** — below / within /
  above — not as a percentage deviation from the median.
- **FR-39** **Hedonic regression is restricted to feature values** (D33). Its
  output is always marked as a model estimate and is **never** the verdict.
  Enforced structurally: the verdict code path has no access to model output.
- **FR-40** **Rezoning uplift** ("value if it became buildable") is computed by
  contrasting buildability strata, and is presented with an unavoidable caveat that
  it is an observed market gap, **not** a probability of obtaining rezoning.
- **FR-41** **Mix-adjusted index** (D27, **narrowed by D41**): stratify by asset
  class × buildability × area band, reweight to a fixed basket. Computed at
  **powiat level and above only** — 80 strata over a gmina's few dozen listings is
  noise, not a measurement (audit A2). Gmina-level series are plain medians,
  explicitly labelled *unadjusted*. Where computable, the mix-adjusted series is
  the headline; the plain median is secondary and labelled.
- **FR-42** Strata with no observations in a period are carried with an explicit
  gap marker, never dropped — dropping them silently reweights the basket.
- **FR-43** Cross-area comparison is by like-for-like estimate or stratified
  distribution only. A raw area average is **not** offered as a comparison tool.
- **FR-44** **Every estimate ever produced is logged** to `valuation_log` with its
  inputs, output, comparable count, widening step and `method_version` (D35). This
  is a precondition of the first estimate, not a later addition — predictions
  cannot be reconstructed afterwards.
- **FR-45** **Scoring**: calibration, bias, MAPE, coverage and widening profile,
  computed per `method_version` against realized outcomes. RCN transactions are
  the real test; final asking price before delisting is a weak signal, labelled.
- **FR-46** A method change **increments `method_version`**; historical predictions
  keep the version that produced them and are scored within it.
- **FR-47** **Analytical surfaces** (D25): in-app screens, a documented read-only
  query layer for notebooks, and scheduled digests. The digest includes
  data-quality events alongside market events, because a silent pipeline failure
  and a quiet market look identical otherwise.

### 8.9 Pipeline correctness (docs 06–08)

- **FR-48** `zoning_claim` (what the advert says) and `buildability` (what planning
  data says) are **separate columns, never reconciled**. Disagreement is displayed
  as a risk flag (`06` §1).
- **FR-49** Portal category maps are explicit and exhaustive; an unmapped category
  alarms rather than defaulting to a class.
- **FR-50** Attribute extraction handles Polish inflection, **negation** and
  proximity qualifiers, and emits a confidence per attribute. `unknown` is never
  coerced to `absent` (`06` §3).
- **FR-51** Area unit normalisation (ar, hektar, decimal comma) with an
  authority order: parcel register → structured field → body → title, source
  recorded (`06` §3.2).
- **FR-52** Extraction quality is measured against a **200-advert hand-labelled
  set**, scored per attribute, with a negation subset (`06` §4).
- **FR-53** **`location_precision`** is recorded per listing and **gates use**:
  nature attributes and parcel enrichment require `address` or better; a fuzzed
  pin never yields a distance-to-forest figure (`07` §3).
- **FR-54** Gmina assignment is by TERYT code, never by name; boundary-proximate
  listings are flagged (`07` §4).
- **FR-55** Distances and areas are computed in EPSG:2180; storage is EPSG:4326;
  every geometry carries an explicit SRID (`07` §5).
- **FR-56** The four times — `observed_at`, validity interval, `transacted_at`,
  `as_of` — are distinct fields. Series are plotted on **when the fact was true**,
  never on when we saw it or when it was published (`08` §1).
- **FR-57** Offering prices are **intervals**, so a listing contributes to every
  month it was active, at the price in force. Crawl gaps are recorded as
  uncertainty, never interpolated (`08` §2).
- **FR-58** Delisting is **not** treated as sale. Time-on-market is reported as
  time listed (`08` §3).
- **FR-59** Sales aggregates carry a **completeness indicator**; periods still
  filling are labelled incomplete, so late-arriving registry data does not read as
  a price drop (`08` §4).
- **FR-60** Recomputation is **versioned, never silent**; material revisions are
  surfaced on the coverage page (`08` §4).

### 8.10 Batch-11 features — off-portal sources and feasibility

> **Rule-1 gap, now closed.** D47, D50, D51, D56 and D40 were decided and
> documented in `18`, `19` and `20`, but **never written as requirements**. Five
> features were about to be implemented with no PRD entry. Added here.

- **FR-61** **KOWR connector** — sale and tender notices for state agricultural
  land across both rings, normalized to the canonical schema (D47).
- **FR-62** **Auction connector** — bailiff (*licytacje komornicze*) and bankruptcy
  (*syndyk*) land sales (D47). Source selection is O16.
- **FR-63** **Gmina BIP connector** — municipal sale notices across the ~50 gminas
  in the two rings, each with its own bulletin layout (D47).
- **FR-64** **Price-kind taxonomy** (resolves O19). `price_kind` is distinct from
  `price_type`: an **asking** price, an **auction starting** price (a statutory
  floor derived from a valuation) and a **tender** price are three different
  quantities. No aggregate may span kinds. Blending them would drag medians down
  and read as a market movement.
- **FR-65** **WZ feasibility — the good-neighbour test** (D50). Composite signal
  `{likely, uncertain, unlikely, unknown}` from building proximity, shared public
  road access, land-use class and protected-area overlap. Never a prediction:
  missing building data yields `unknown`, **never** `unlikely`, and `likely`
  carries the same disclaimer as `unlikely` (`19` §1.2).
- **FR-66** **Farmland purchasability badge** (D51). Driven by the **register**
  land-use class, never the advert's claim. States *possible* restrictions, never
  certainty; never a filter; unknown class produces no badge **and** no reassurance.
- **FR-67** **Stock and flow** (D56). Every aggregate is computed both ways —
  stock (all active) and flow (first seen within the window) — each labelled, never
  blended. **Flow is the headline.** The flow window length is unratified (O27).
- **FR-68** **List-page-first crawl** (D40). List pages supply price and active
  status for the whole corpus; detail pages are fetched only on first sight or when
  a list page shows a change. This is what makes daily observation compatible with
  the politeness policy (`10` §2.1).
- **FR-69** **LOOCV acceptance harness** (D57). Hold out each listing, rebuild its
  comparable set from the remainder, estimate, compare to actual asking price;
  report coverage, hit rate, median absolute error and >2× tail per run.
- **FR-70** **v0 dedup** — exact and near-exact matching only, without the labelled
  scoring set the full FR-13 requires. A deliberately weaker feature, so it needs
  its own weaker-but-real acceptance criteria rather than inheriting FR-13's.
- **FR-71** **Streamlit app surface** (D59) — the v0 delivery vehicle. Subject to
  the same honesty rules as any UI (`09` §1): no bare aggregate, every price
  labelled with type **and** kind, verdict collapsed by default (`21` §U5).
  Comparable exclusion feedback per V51c.
- **FR-72** **Raw payload retention and re-parse** in v0 form — every fetched
  document stored with its hash, and a documented path from a parser fix to
  recomputed aggregates without touching snapshots.

### 8.11 Research spikes

- **FR-31** **RCN access research** (D5), before any RCN connector is scheduled.
  Deliverable: a table of the ~70 in-scope powiats with, for each, whether RCN data
  is published openly, the format, and any fee or request procedure. Feeds O2 and
  decides whether the ≥40% parcel-level sales coverage target in §5 is achievable
  for free.

## 9. Sequencing

Two constraints drive the order. Listing data **cannot be backfilled** — the price
history J3/J4/J5/J7 need only exists if we are already collecting. And sales prices
are **first-class from the start** (D3), so GUS BDL lands in M1, not M4.

| Milestone | Contents | Journeys |
|---|---|---|
| **M0 — Spine** | Schema with `price_type` constraint, PRG boundaries, TERYT, anchor config, source health scaffolding, RCN access research (FR-31) | — |
| **M1 — Both price types flowing** | Land connectors (daily) for all three units; **GUS BDL sales baseline**; snapshot pipeline; dedup; normalization; coverage page | data accrues |
| **M2 — See** | Gmina aggregates for both price types, choropleth, filters, travel time to anchors | **J1** |
| **M3 — Judge** | ULDK parcel resolution, zoning, nature and constraint enrichment, comparable engine, plot page, comparison board | **J2, J3**, J8 |
| **M3.5 — Value** | Comparable-set estimator, what-if calculator, `valuation_log` from the first estimate | **J9** |
| **M4 — Parcel-level sales** | RCN connector for whichever powiats FR-31 found free; asking-vs-sales spread; mix-adjusted index; trends | **J5, J7, J11** |
| **M5 — Extend** | Hedonic feature values; scoring of logged predictions; digests; saved searches; housing surfaced | **J10, J12, J4, J6** |

M2 is the first demoable milestone; M3 the first genuinely useful one; **M3.5 is
where the product answers its central question** (D26).

Two ordering constraints beyond the backfill rule: `valuation_log` (FR-44) must
exist from the very first estimate, and the hedonic model (FR-39) cannot be fitted
until enough enriched data has accumulated — which is why feature values land in
M5 rather than alongside the estimator.

## 10. Data model

```
source              (id, name, kind[portal|registry|api], base_url, robots_ok,
                     rate_limit, last_success_at, health)
raw_document        (id, source_id, url, fetched_at, payload, content_hash)

listing             (id, source_id, external_id, first_seen_at, last_seen_at,
                     is_active, url, title, description,
                     price_pln, area_m2, price_per_m2,
                     price_type CHECK = 'offering'  NOT NULL,      -- FR-7
                     asset_class, zoning_claim, utilities[], road_access,
                     lat, lon, teryt_gmina, parcel_id?, plot_cluster_id,
                     seller_contact_hash, seller_type)
listing_snapshot    (listing_id, observed_at, price_pln, is_active)   -- append-only
plot_cluster        (id, canonical_listing_id, duplicate_count, member_ids[])

transaction         (id, source[rcn|gus_bdl], parcel_id?, teryt_unit, unit_level,
                     transacted_at, price_pln, area_m2, price_per_m2,
                     price_type CHECK = 'sales' NOT NULL,           -- FR-7
                     property_kind, as_of)

parcel              (id, parcel_identifier, teryt_gmina, obreb, geom,
                     registry_area_m2, land_use_class, soil_class)
parcel_zoning       (parcel_id, plan_type, designation,
                     buildability[buildable|conditional|agricultural|unknown],
                     source_doc, as_of)
parcel_constraint   (parcel_id, kind, severity, source, as_of)
parcel_nature       (parcel_id, dist_forest_m, dist_water_m, water_kind,
                     protected_area_kind?, dist_major_road_m, dist_railway_m)
parcel_access       (parcel_id, anchor_key, drive_minutes, distance_km)

anchor              (key, label, lat, lon)          -- populated from gitignored config
admin_unit          (teryt, level, name, geom, parent_teryt)

metric_unit_month   (teryt_unit, unit_level, month, asset_class,
                     price_type,                                     -- FR-7/FR-8
                     n, median_ppm2, p25, p75, min_ppm2, max_ppm2, mean_ppm2,
                     as_of, source_ids[])
```

Invariants worth stating explicitly, because the validation doc tests each one:

1. `listing_snapshot` is append-only — it is the only history we will ever have.
2. Every price-bearing table has a non-null `price_type` with a CHECK constraint.
3. `metric_unit_month` rows are keyed *including* `price_type`; no row ever mixes.
4. Every derived row carries `as_of` and source, so provenance is mechanical.
5. No row is ever deleted for being thin — thinness is expressed via `n` and spread.

## 11. Architecture

- **Ingestion** — Python. `httpx` + `selectolax` for static pages, Playwright only
  where genuinely required. One module per source, common `fetch → parse → emit`
  contract. Scheduled by cron on the VPS.
- **Storage** — PostgreSQL + **PostGIS**. Every core question is spatial.
- **Transformation** — versioned SQL models producing `metric_*` tables. Analysis
  reads the same tables the app does; no parallel truth.
- **API** — FastAPI, GeoJSON/vector tiles for the map, JSON for plot pages.
- **Frontend** — Next.js + MapLibre GL, Polish copy.
- **Routing** — self-hosted OSRM over an OSM extract of the target areas;
  drive times to anchors precomputed offline.
- **Deployment** — Docker Compose on a cheap VPS (D16), daily cron. A simple access
  gate for the handful of users is open question O4.
- **Testing** — pytest, with fixtures recorded from real sources. Per rule 3, tests
  precede implementation; per rule 4, each feature's validation method precedes its
  tests.

## 12. Legal, ethical and operating constraints

Framing: **a private analytical tool for personal purchase decisions, shared with a
few known people** (D1) — not a published service. Publishing or commercializing is
a gate requiring fresh review, not a growth step.

- Respect `robots.txt`, portal terms, polite rate limits (single-digit
  requests/minute per host, off-peak, daily cadence per D14).
- Never bypass authentication, paywalls, anti-bot measures or CAPTCHAs.
- Store the minimum from adverts. Seller names and phone numbers → salted hash only
  (FR-23), never a readable field.
- Never republish listing text or photos; show derived numbers and link to source.
- The specific legal risk is substantial systematic extraction (sui generis database
  right), rising sharply with commercial reuse. Private, low-volume,
  derived-metrics-only is the mitigation.
- Prefer official open data wherever it answers the same question — licensed for
  reuse, no such risk.
- Personal addresses never enter git (FR-22, FR-23).

## 13. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| RCN turns out to be paid in most in-scope powiats | Sales prices stay coarse, undermining D3 | FR-31 research first; GUS BDL guarantees a free powiat-level sales floor everywhere |
| Portals block us | Kills the offering-price layer | Polite crawling, multiple sources, degrade to registry-only aggregates rather than going dark |
| Zoning incomplete until 2029 | Buildability unknown for many plots | Terminal `unknown` state (FR-17); prioritise gminas with published plan ogólny |
| Thin rural samples around Budy Grabskie | Misleading medians | Mandatory spread + n on every aggregate (FR-25); min–max below n=5 |
| Always-show is misread as confident | User acts on n=3 | Spread is not optional anywhere; enforced at the API boundary and tested |
| Duplicates inflate counts | Wrong supply, skewed medians | plot_cluster dedup, 200-record manual audit |
| Silent scraper drift | Corrupted, unrecoverable history | Schema-drift alarms (FR-6); raw payloads retained so re-parsing is always possible |
| Anchor addresses leak into git | Personal privacy | Gitignored config, example file only, no addresses in fixtures |
| Scope creep to all of Poland | Nothing finishes | Region is a parameter; only the three units in §6.1 ship |

## 14. Open questions

Tracked in [`00-decisions.md`](./00-decisions.md) batch 13, which closes or assigns
every item O1–O31. **O10 (robots.txt) blocks all offering-price work, including
day 1.** O18 (is this worth building against a six-month horizon) and O3 (repo
rename) are the other two still with you.

---

## Appendix — traceability

| Journey | Requirements |
|---|---|
| J1 Where can I afford | FR-1..6, 11..14, 21, 24, 25, 30 |
| J2 Is it fairly priced | FR-7..20, 26, 30, 32..38, 48 |
| J3 Side-by-side | FR-3, 15..21, 26, 30 |
| J4 Alerts | FR-1, 3, 4, 13 (+M5) |
| J5 Negotiation | FR-3, 7..10, 27, 30, 58 |
| J6 Buy vs build | FR-11, 24, 27 |
| J7 Trends | FR-7..10, 24, 25, 27, 41, 42, 59 |
| J8 Trust | FR-6, 12, 25, 29, 30, 35, 60 |
| **J9 What should it cost** | **FR-32..38, 44, 53** |
| **J10 Feature values** | **FR-39, 40, 45** |
| **J11 Real move or mix shift** | **FR-41, 42, 43, 56, 59** |
| **J12 Digest** | **FR-47, 6** |
| Rule 5 (two price types) | FR-7, 8, 9, 10, 24, 27, 37 |
| Rule 6 (always show, always flag) | FR-25, 32, 35 |

## Appendix — document map

| Doc | Covers |
|---|---|
| [`00-decisions.md`](./00-decisions.md) | D1–D63, open items O1–O31 |
| [`01-user-journeys.md`](./01-user-journeys.md) | J1–J12 |
| `02-prd.md` | This document — FR-1..72 |
| [`03-data-sources.md`](./03-data-sources.md) | Sources, licensing, scraping rules |
| [`04-validation.md`](./04-validation.md) | V1–V62 |
| [`05-analytics-methodology.md`](./05-analytics-methodology.md) | Valuation, comparables, mix adjustment, scoring |
| [`06-taxonomy-and-extraction.md`](./06-taxonomy-and-extraction.md) | Asset classes, attribute extraction |
| [`07-geocoding.md`](./07-geocoding.md) | Location resolution and precision gating |
| [`08-temporal-model.md`](./08-temporal-model.md) | The four times, intervals, revisions |
| [`09-ux-specification.md`](./09-ux-specification.md) | Screens, states, honesty rules |
| [`10-nfr-and-access.md`](./10-nfr-and-access.md) | Scale, performance, retention, access |
| [`11-operations.md`](./11-operations.md) | Pipeline, backup, monitoring, recovery |
| [`12-glossary.md`](./12-glossary.md) | Polish ↔ code terminology |
| [`13-scope.md`](./13-scope.md) | **Complete work breakdown** — epics E1–E26, work items, sizes, critical path, out-of-scope register |
| [`14-api-contract.md`](./14-api-contract.md) | Endpoints, shared types, boundary enforcement |
| [`15-database-schema.md`](./15-database-schema.md) | Full DDL; the rules encoded as constraints |
| [`16-repository-layout.md`](./16-repository-layout.md) | Module layout, connector contract, enforced boundaries, definition of done |
| [`17-assumption-audit.md`](./17-assumption-audit.md) | Self-review of docs 00–16 |
| [`18-v0-scope.md`](./18-v0-scope.md) | **The plan of record** |
| [`19-legal-and-feasibility.md`](./19-legal-and-feasibility.md) | WZ good-neighbour test; agricultural purchase law |
| [`20-verification-strategy.md`](./20-verification-strategy.md) | Verification tiers, silent-failure catalogue, techniques |
| [`21-v0-ui-and-ux.md`](./21-v0-ui-and-ux.md) | The v0 interface |
