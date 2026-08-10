# Complete scope

> ## ⚠ Not the current plan
>
> This is the **full** build: 26 epics, roughly **150–200 focused days** — three
> years at a day a week, or 18–24 months at two. I documented it without ever
> stating that total, which the audit ([`17`](./17-assumption-audit.md) §D) called
> out.
>
> **The plan of record is [`18-v0-scope.md`](./18-v0-scope.md)** — ~26–29 days,
> both anchor rings, portals plus KOWR, auctions and gmina BIP, and the
> feasibility layer (D47, D49, D55). This document is
> retained as the menu to draw from *after* v0 shows which gaps are real.
>
> Enter it deliberately, one epic at a time, and only where v0 produced evidence
> that the epic is needed. In particular: **E8 (zoning) is the most likely first
> addition**, because price without buildability is close to meaningless — and
> **E15–E21 (API + frontend) are roughly half the total effort** for an audience
> of one to five, which is where the cost is least justified.

The full work breakdown for the application: every epic, its work items, what
validates it, what it depends on, and a size estimate.

Sizes are **days of focused work** for one person, and are estimates rather than
commitments: `XS` <1, `S` 1–2, `M` 3–5, `L` 6–10, `XL` >10.

Traceability: FR numbers → [`02-prd.md`](./02-prd.md), V numbers →
[`04-validation.md`](./04-validation.md), D numbers → [`00-decisions.md`](./00-decisions.md).

---

## 1. Scope boundary

### 1.1 In scope

| Area | Extent |
|---|---|
| Geography | łódzkie (~177 gminas), mazowieckie (~314), Elbląg area (~10) — D9 |
| Anchor rings | Budy Grabskie 25 km, Elbląg 25 km — deeper enrichment and QA (D7, D11) |
| Land classes | budowlana, rekreacyjna, rolna, leśna/inne (D6) |
| Housing | Collected from M1, surfaced only in J6/J7 (E23) |
| Price types | Offering **and** sales, always separate (rule 6, D3) |
| Users | Owner plus a few known people; single shared gate (D1, O4) |
| Data cost | Zero — free sources only (D2) |
| Runtime | Docker Compose on one small VPS (D16) |

### 1.2 Explicitly out of scope

Recorded so that "could we also…" has a documented answer:

- Other voivodeships (region is a parameter; no data ships for them)
- Public launch, commercial use, paid API, reselling listing content
- Any paid data source
- Commercial/industrial property, rental data, forests valued as timber
- Mortgage or financing calculators; contacting sellers; listing your own plot
- Native mobile apps (responsive web only, and even that is deferred — `09` §5)
- User accounts, registration, password reset (D1 makes these unnecessary)
- Legal certainty of any kind — the *wypis i wyrys* remains the binding document
- Real-time data; daily is the contract (D14)
- Automated offers, bidding, or transaction execution

### 1.3 Deferred with a known home

| Item | Where it lands |
|---|---|
| Size adjustment (O6), standard-plot benchmark (O7) | E12, blocked on decision |
| Digest cadence and channel (O8) | E22 |
| Notebook access mechanism (O9) | E15 |
| Housing attribute extraction | E23, spec required first (`06` §5) |
| Mobile layout | Post-M5 |

---

## 2. Epic map

```
E1  Foundation
 └─ E2  Reference data ──┬─ E3  Official sales data
                         ├─ E4  Listing ingestion ─ E5 Normalization ─ E6 Dedup
                         │                                     │
                         │                            E7 Geospatial resolution
                         │                                     │
                         │              ┌──────────────────────┼───────────────┐
                         │           E8 Zoning        E9 Constraints/nature  E10 Access
                         │              └──────────────────────┼───────────────┘
                         └──────────────────────────── E11 Aggregation ─ E12 Valuation
                                                              │              │
                                                    E13 Feature model    E14 Scoring
                                                              │
                                                          E15 API ─ E16..E21 Frontend
                                                                       │
                                                                   E22 Alerts/digests
E24 Operations · E25 Quality harness · E26 Access control  (cross-cutting, start at E1)
```

**Critical path**: E1 → E2 → E4 → E5 → E7 → E11 → E15 → E16. Everything else
either hangs off this or runs in parallel.

---

## 3. Epics

### E1 — Foundation · `M` · no dependencies

| # | Work item | Validates |
|---|---|---|
| E1.1 | Repo layout, Python packaging, lint/format/type-check config | — |
| E1.2 | Docker Compose: Postgres+PostGIS, app, migrations | V40 restore target |
| E1.3 | Migration framework and the initial schema (E1 covers mechanism; `15` covers content) | V1 |
| E1.4 | Config loading, incl. gitignored `config/anchors.yml` + example | **V7** |
| E1.5 | Test harness, fixture layout and loading conventions | fixtures policy |
| E1.6 | CI: run tests, assertions, type checks on every commit | V-suite |
| E1.7 | Structured logging and the alarm channel abstraction | V8, `11` §5 |

**Gate:** `docker compose up` produces a working empty system; V7 passes; CI green.

### E2 — Reference data · `M` · after E1

| # | Work item | Validates |
|---|---|---|
| E2.1 | PRG boundary import for the three target units | **V6** |
| E2.2 | TERYT dictionary and hierarchy (gmina → powiat → voivodeship) | V6, V30 |
| E2.3 | `admin_unit` geometries, validity and overlap checks | V6 |
| E2.4 | Anchor loading and the 25 km ring definitions | V7 |
| E2.5 | Known-answer spatial fixture: Budy Grabskie → gmina Skierniewice (rural) | **V30** |

**Gate:** every in-scope gmina present with a valid geometry; the two Skierniewice
units are distinct; V6 and V30 pass.

### E3 — Official sales data · `L` · after E2

| # | Work item | Validates |
|---|---|---|
| E3.1 | GUS BDL API client (variable discovery, paging, retries) | V13 |
| E3.2 | Land-price series import for all in-scope powiats, `price_type='sales'` | **V13** |
| E3.3 | Urban/rural split preservation; absence recorded as absence | V13 |
| E3.4 | **RCN access research across ~70 powiats** (FR-31) | **V9** |
| E3.5 | RCN GML parser for the formats found by E3.4 | deferred method |
| E3.6 | RCN import with `transacted_at` ≠ `as_of` handling | **V32** |
| E3.7 | Completeness indicator for still-filling periods | **V34** |

E3.4 is a **research spike and gates E3.5–E3.7**. Start it during E1 — it involves
waiting on third parties, and it is the only item here whose duration is not ours
to control.

**Gate:** 100% of in-scope powiats have a sales series; V9, V13, V32, V34 pass.

### E4 — Listing ingestion · `L` · after E2

| # | Work item | Validates |
|---|---|---|
| E4.1 | Connector contract: `fetch → parse → emit`, resumable, incremental | `16` |
| E4.2 | `robots.txt` handling, per-host rate limiting, backoff | **V14** |
| E4.3 | Raw document store with content hashing | V42 |
| E4.4 | Snapshot writer, append-only, with DB-level protection | **V12** |
| E4.5 | Source health records and the schema-drift alarm | **V8** |
| E4.6 | Portal connector #1, land classes, three target units | V8, V14 |
| E4.7 | Portal connector #2 (redundancy against blocking) | V8, V14 |
| E4.8 | Housing collection through the same connectors (stored, not surfaced) | — |
| E4.9 | Daily scheduling and resumability | **V41** |

**Blocked on O1** (which portals). E4.1–E4.5 are portal-agnostic and can proceed.

**Gate:** a full daily run collects land listings across all three units; snapshots
are provably append-only; a zero-item run alarms rather than publishing.

### E5 — Normalization & taxonomy · `L` · after E4

| # | Work item | Validates |
|---|---|---|
| E5.1 | Canonical listing schema and mapping | FR-11 |
| E5.2 | Category maps per portal, exhaustive, alarming on unmapped | **V26** |
| E5.3 | `zoning_claim` captured verbatim, **never** written to `buildability` | **V25** |
| E5.4 | Area unit normalisation (ar, ha, decimal comma) + authority order | **V28** |
| E5.5 | `price_per_m2`, validation bands, quarantine with reasons | **V10** |
| E5.6 | Attribute extraction: utilities, road access, with inflection handling | **V27** |
| E5.7 | Negation and proximity qualifier handling | **V27** |
| E5.8 | Per-attribute confidence; `unknown` never coerced to `absent` | V27 |
| E5.9 | **200-advert labelled evaluation set**, hand-labelled, scrubbed | V27, `06` §4 |
| E5.10 | Per-attribute precision/recall scoring harness | **V27** |

E5.9 is manual work that gates E5.10 and cannot be skipped — without it,
extraction quality is an assertion rather than a measurement.

**Gate:** per-attribute precision ≥ threshold on the labelled set; no negated
phrase extracted positively; hectare listings priced correctly.

### E6 — Deduplication · `M` · after E5

| # | Work item | Validates |
|---|---|---|
| E6.1 | Matcher: area, price band, geohash, title shingles, contact hash | **V11** |
| E6.2 | Perceptual image hashing | V11 |
| E6.3 | `plot_cluster` assembly, canonical selection, `duplicate_count` | V11 |
| E6.4 | 200-listing hand-labelled dedup sample | V11 |
| E6.5 | Scoring: false-negative and **false-merge** rates reported separately | **V11** |
| E6.6 | Cluster-size distribution monitoring assertion | V11 |

**Gate:** duplicate rate ≤3%, false-merge ≤1% on the labelled sample.

### E7 — Geospatial resolution · `L` · after E5

| # | Work item | Validates |
|---|---|---|
| E7.1 | Parcel identifier extraction from advert text | V29 |
| E7.2 | GUGiK ULDK client, geometry retrieval, EPSG:2180 handling | **V31** |
| E7.3 | Self-hosted Nominatim over a Poland extract | `07` §6 |
| E7.4 | Resolution ladder with `location_precision` recording | **V29** |
| E7.5 | Pin-cluster detection and demotion | `07` §2 |
| E7.6 | Boundary-risk flagging within 500 m | V30 |
| E7.7 | Gmina assignment by TERYT only; no name lookups | **V30** |
| E7.8 | Precision gating of downstream attributes | **V29** |
| E7.9 | Versioned re-resolution | `07` §7 |

**Gate:** no nature attribute exists on a `pin`-precision listing; distances
correct to 1 m against a known-answer pair.

### E8 — Zoning enrichment · `L` · after E7

| # | Work item | Validates |
|---|---|---|
| E8.1 | Rejestr Urbanistyczny / plan ogólny data acquisition | deferred method |
| E8.2 | MPZP spatial data ingestion where published | deferred method |
| E8.3 | Parcel → designation spatial join | deferred method |
| E8.4 | `buildability` derivation from designation | FR-16 |
| E8.5 | **`unknown` as terminal** — never inferred from neighbours or land use | **deferred, FR-17** |
| E8.6 | Claim-vs-data disagreement flag | **V25** |
| E8.7 | Per-gmina plan-coverage tracking (also prioritises enrichment) | V15 |

Highest-uncertainty epic: coverage is partial until 2029 and varies by gmina. E8.5
is the one item that must not be compromised for coverage.

**Gate:** a plot with buildable neighbours and no plan data still reads `unknown`.

### E9 — Constraints & nature · `M` · after E7

| # | Work item | Validates |
|---|---|---|
| E9.1 | Flood hazard layer import and intersection | FR-18 |
| E9.2 | Protected areas (GDOŚ); landscape park, Natura 2000, reserves | FR-18, FR-20 |
| E9.3 | Soil class from EGiB; class I–III flag | FR-18 |
| E9.4 | Road-access derivation | FR-18 |
| E9.5 | OSM landcover → distance to forest | FR-19 |
| E9.6 | OSM water → distance to water, with water kind | FR-19 |
| E9.7 | Distance to major road and railway | FR-19 |
| E9.8 | Protected status rendered as **both** amenity and constraint | **FR-20** |

**Gate:** distances hand-checked against a map for a sample; precision gate honoured.

### E10 — Accessibility · `S` · after E7

| # | Work item | Validates |
|---|---|---|
| E10.1 | Self-hosted OSRM over a target-area OSM extract | `10` §6 |
| E10.2 | Batch travel-time computation to each configured anchor | deferred method |
| E10.3 | Known-answer test against an independent routing source | deferred method |
| E10.4 | Precomputed per-gmina travel-time columns for map filtering | FR-21 |

### E11 — Aggregation & metrics · `L` · after E5 (E7/E8 improve it)

| # | Work item | Validates |
|---|---|---|
| E11.1 | `metric_unit_month` computation, keyed **including** `price_type` | **V2** |
| E11.2 | Median, p25, p75, min, max, mean, n | V4 |
| E11.3 | Range selection: IQR at n≥5, min–max below | **V4** |
| E11.4 | Strata definition (class × buildability × area band) | **V23** |
| E11.5 | Fixed-basket reweighting → mix-adjusted index | **V23** |
| E11.6 | Empty strata carried with gap markers, never dropped | **V23** |
| E11.7 | Offering-price interval expansion into monthly contributions | **V33** |
| E11.8 | Versioned recomputation generations | **V34**, `08` §4 |
| E11.9 | Coverage and freshness metrics feeding the coverage page | **V15** |
| E11.10 | Cross-source agreement assertion | **V16** |

**Gate:** synthetic composition-shift series moves the plain median and leaves the
index flat.

### E12 — Valuation engine · `XL` · after E11 (needs E7, E8 for good features)

The product's central capability (D26).

| # | Work item | Validates |
|---|---|---|
| E12.1 | Comparable-set selection: hard filters incl. exact buildability | **V18** |
| E12.2 | Widening ladder, recorded step, buildability never relaxed | **V18, V19** |
| E12.3 | `estimate()` returning a range, never a point | **V17** |
| E12.4 | Feature-bundle input path (no listing required) | FR-33 |
| E12.5 | Dual estimates: offering and sales, disjoint, absence explicit | **V20** |
| E12.6 | Verdict phrased relative to the range | FR-38 |
| E12.7 | Comparable set enumerable and editable, live recompute | FR-36 |
| E12.8 | "Same plot, different place" | FR-31 |
| E12.9 | Rezoning uplift via strata contrast + mandatory caveat | **V22** |
| E12.10 | **`valuation_log` writing from the first estimate** | **V24** |
| E12.11 | `method_version` stamping and increment discipline | **V24** |
| E12.12 | Size adjustment — **O6 closed**: measure elasticity, adjust only if LOOCV shows size-correlated error | deferred |

**Gate:** no mixed-buildability comparable set anywhere; every estimate path logs.

### E13 — Feature-value model · `L` · after E12 + accumulated data

| # | Work item | Validates |
|---|---|---|
| E13.1 | Hedonic specification, gmina effects, held-out split | FR-39 |
| E13.2 | Coefficients with intervals, expressed in zł/m² | FR-39 |
| E13.3 | **Structural separation** from the verdict path | **V21** |
| E13.4 | "Model estimate" marking on every output | **V21** |
| E13.5 | Sign-agreement check against comparable contrasts | `05` §10 |

Cannot start until enough enriched observations exist — which is why it is M5.

### E14 — Scoring & evaluation · `M` · after E12 + elapsed time

| # | Work item | Validates |
|---|---|---|
| E14.1 | Outcome matching: RCN transactions ↔ logged predictions | **V24** |
| E14.2 | Calibration, bias, MAPE, coverage, widening profile | **V24** |
| E14.3 | Per-`method_version` scoring, never pooled | **V24** |
| E14.4 | Weak-signal path: final asking price before delisting, labelled | V34 |
| E14.5 | Quarterly falsification review against `05` §10 | `05` §10 |

Needs elapsed time as much as effort — outcomes arrive months after predictions.

### E15 — API · `M` · after E11

| # | Work item | Validates |
|---|---|---|
| E15.1 | FastAPI skeleton, error model, pagination | — |
| E15.2 | Response models enforcing `price_type` on every price | **V3** |
| E15.3 | Boundary enforcement: no aggregate without `n` **and** range | **V4** |
| E15.4 | Vector tiles / GeoJSON for the choropleth | V38 |
| E15.5 | Plot, estimate, what-if, trends, coverage endpoints | `14` |
| E15.6 | Read-only query layer + stability contract (post-v0) | deferred |

### E16–E21 — Frontend · `XL` total · after E15

| Epic | Screen | Size | Validates |
|---|---|---|---|
| E16 | Map + filters + gmina panel (J1) | `L` | V35, V36, deferred choropleth method |
| E17 | Plot page: verdict, risks, nature, comparables, history (J2, J5) | `L` | V35, V36 |
| E18 | What-if calculator, four tabs (J9, J10) | `M` | V21, V22 |
| E19 | Comparison board (J3) | `M` | V35 |
| E20 | Trends: mix-adjusted headline, completeness markers (J7, J11) | `M` | V23, V34 |
| E21 | Coverage & method page (J8) | `S` | V15 |

Cross-cutting within all of these: the six honesty rules (`09` §1), all five
component states (`09` §3), Polish formatting and terminology (V37).

### E22 — Alerts, saved searches, digests · `M` · after E16

| # | Work item | Validates |
|---|---|---|
| E22.1 | Saved search persistence and matching | deferred method |
| E22.2 | Stable listing identity across relistings | E6 dependency |
| E22.3 | New / price-cut / relisting detection | V33 |
| E22.4 | Digest composition incl. **data-quality events** | **deferred, FR-47** |
| E22.5 | Delivery channel — **blocked on O8** | deferred |

### E23 — Housing · `L` · post-M5

| # | Work item |
|---|---|
| E23.1 | Housing attribute spec (`06` §5) — **required before any extractor** |
| E23.2 | Housing extraction and validation |
| E23.3 | Build-cost parameter and source |
| E23.4 | Buy-vs-build comparison (J6) |

### E24 — Operations · `M` · cross-cutting, starts at E1

| # | Work item | Validates |
|---|---|---|
| E24.1 | Nightly encrypted off-VPS backup | **V40** |
| E24.2 | **Quarterly restore drill, scripted and failing loudly** | **V40** |
| E24.3 | Pipeline orchestration in the documented order | V41 |
| E24.4 | Fail-safe behaviour; assertions block publication | **V41** |
| E24.5 | Alarm routing to a channel actually read | `11` §5 |
| E24.6 | Re-parse recovery drill from `raw_document` | **V42** |
| E24.7 | Deployment, migration and post-deploy invariant checks | V1–V5 |

E24.1 and E24.2 are **not deferrable to the end**. The irreplaceable data starts
accumulating at E4; backups must exist by then.

### E25 — Quality harness · `M` · cross-cutting, starts at E1

| # | Work item |
|---|---|
| E25.1 | Fixture recording tooling with personal-data scrubbing |
| E25.2 | Δ data-assertion framework wired into the pipeline |
| E25.3 | Architectural tests (module boundaries — V21, V25) |
| E25.4 | Snapshot-testing setup for UI honesty rules (V35–V37) |
| E25.5 | Benchmark suite at projected volume (V38) |
| E25.6 | Quarterly manual audit scripts (V10, V11, V27) |

### E26 — Access control · `S` · before first deployment

| # | Work item | Validates |
|---|---|---|
| E26.1 | Reverse proxy, HTTPS, shared-password gate (**O4**) | **V39** |
| E26.2 | Postgres not externally reachable | V39 |
| E26.3 | Separate read / write / pipeline roles | V39 |
| E26.4 | Secret handling off-repo | `11` §7 |

---

## 4. Which epics v0 touches

v0 ([`18`](./18-v0-scope.md)) takes thin slices of seven epics, plus parts of E7,
E9 and E16 added by batch 11/14:

| Epic | v0 takes | v0 skips |
|---|---|---|
| E1 Foundation | Repo, Docker, Postgres+PostGIS, migrations, config | CI depth, alarm routing, full test harness |
| E2 Reference data | PRG + TERYT **for the two rings only**; the Skierniewice known-answer test | The other ~440 gminas |
| E3 Official sales | GUS BDL import for the rings' powiats | RCN entirely (research still worth starting) |
| E4 Ingestion | robots gate, rate limiting, list-page-first fetch, raw store, snapshots | Second portal, health/drift alarms, resumability |
| E5 Normalization | Area units, zł/m², validity bands, quarantine | Attribute extraction, category maps, labelled sets |
| E6 Dedup | Exact/near-exact only | Labelled scoring, image hashing, cluster monitoring |
| E11 Metrics | Gmina + area-band medians with spread | Strata, mix adjustment, generations, coverage suite |

Partly touched: **E7** (parcels for the good-neighbour test), **E9** (buildings and
protected areas), **E16** (the Streamlit surface, D59).
Not touched: E8, E10, E12–E15, E17–E26.

## 5. Milestone composition

| Milestone | Epics | Rough size | Exit gate |
|---|---|---|---|
| **M0 Spine** | E1, E2, E3.4 spike, E24.1, E25.1–2, E26 skeleton | `L`–`XL` | Empty system runs; boundaries correct; V6, V7, V30 pass; RCN research underway |
| **M1 Collect** | E3.1–3.3, E4, E5, E6, E24 | `XL` | Daily collection of both price types; V8–V16 pass; backups verified |
| **M2 See** | E7, E10, E11, E15, E16, E21, E26 | `XL` | J1 works; map honest under V35/V36 |
| **M3 Judge** | E8, E9, E17, E19 | `XL` | J2, J3 work; `unknown` provably terminal |
| **M3.5 Value** | E12, E18 | `XL` | J9 works; V17–V22, V24 pass; every estimate logged |
| **M4 Sales depth** | E3.5–3.7, E11.4–11.6, E20 | `L` | J5, J7, J11; mix adjustment validated |
| **M5 Extend** | E13, E14, E22, E23 | `XL` | J10, J12, J4, J6 |

**Assumption, flagged (rule 2):** milestone sizes assume part-time solo work and
no parallelism. They are ranges for sequencing discussion, not a schedule.

## 6. Dependency risks

| Risk | Affects | Mitigation |
|---|---|---|
| O1 unresolved (which portals) | E4.6–4.7, all of M1 | E4.1–4.5 are portal-agnostic; build those first |
| E3.4 RCN research slow (third parties) | E3.5–3.7, M4 | Start during M0; GUS BDL floor means sales prices exist regardless |
| E8 zoning coverage thin | M3 quality | `unknown` is a valid, honest outcome; prioritise gminas with published plans |
| E13 needs accumulated data | M5 | Nothing to do but wait; E12 is unaffected |
| E14 needs elapsed time | Evaluation | Start logging at E12.10 so the clock starts as early as possible |
| Labelled sets (E5.9, E6.4) are manual | M1 | Budget them explicitly; they are not optional |

## 7. Work not yet estimated

Honest gaps, listed rather than hidden:

- E8.1–8.3 depend on the Rejestr Urbanistyczny's actual data shapes, which need a
  spike before sizing.
- E22.5 and E15.6 relate to O8/O9, both closed as out-of-v0 in `00` batch 13.
- E12.12 follows O6's measurement plan; the standard-plot benchmark (O7) is adopted and rendered in `21` §2.2.
- E23 cannot be sized before E23.1 exists.
