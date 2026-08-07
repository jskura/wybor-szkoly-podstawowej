# PRD — Land & Housing Price Comparison for łódzkie and mazowieckie

Status: draft v0.1 · Owner: jskura · Derived from [`01-user-journeys.md`](./01-user-journeys.md)

---

## 1. Problem

Someone looking for a plot to build on in łódzkie or mazowieckie has to answer two
questions that no existing tool answers:

1. **"Where does my budget work?"** Portals filter listing-by-listing. There is no
   view of the price surface across ~490 gminas, so buyers search where they
   happen to have heard of, not where the price/commute trade-off is best.
2. **"Is this price fair, and may I even build here?"** Asking prices are
   anchors, not values. Actual transaction prices sit in a public register almost
   nobody reads, and buildability sits in planning documents that are only now
   becoming machine-readable.

The gap is widest for **land**, because land is the least standardized asset: two
plots 200 m apart can differ 5× in price per m² for reasons (zoning, road access,
utilities, soil class) that listings state inconsistently or not at all.

## 2. What we are building

A data product that continuously collects land and housing offers plus official
registry data for two voivodeships, normalizes them to comparable units, enriches
them with the parcel and planning context that determines value, and presents the
result as **a map you explore, a verdict on a single plot, and a side-by-side
board** — with the source, date and sample size behind every number.

## 3. Goals / non-goals

**Goals (v1)**
- G1 — A user can identify the gminas where their budget buys a buildable plot at
  an acceptable commute, in one session. *(J1)*
- G2 — For any plot in scope, produce a price-per-m² verdict against a transparent
  comparable set, plus buildability and risk flags. *(J2, J3)*
- G3 — Numbers are auditable: source, as-of date, sample size, method, always one
  click away; aggregates below n=10 are suppressed. *(J8)*
- G4 — Coverage of ≥ 90% of gminas in both voivodeships with ≥ 1 land observation
  per quarter, and ≥ 60% with a usable monthly median (n ≥ 10).

**Non-goals (v1)**
- Other voivodeships. The design must not *prevent* it (region is a parameter),
  but nothing ships for them.
- A public commercial AVM, a paid API, or reselling listing content.
- Mortgage/financing calculators, agent CRM, native mobile app, listing your own
  plot for sale, contacting sellers through us.
- Housing beyond what J6/J7 need — flats and houses are collected but get no
  dedicated UI in v1.
- Legal certainty. Every buildability statement is informational; the binding
  document is the *wypis i wyrys* from the gmina.

## 4. Users and priority

P1 self-builder (primary) → P2 patient investor → P3 relocator → P4 us.
See [user journeys §Personas](./01-user-journeys.md#personas).

## 5. Success metrics

| | Metric | Target at v1 |
|---|---|---|
| Coverage | Gminas with ≥10 active land listings | ≥ 60% of 491 |
| Coverage | Land listings resolved to a parcel geometry | ≥ 40% |
| Coverage | Listings with a zoning designation attached | ≥ 50% |
| Quality | Duplicate rate after dedup (manually audited sample of 200) | ≤ 3% |
| Quality | PLN/m² outliers surviving validation (manual audit) | ≤ 1% |
| Freshness | Gminas crawled within the last 48 h | ≥ 95% |
| Value | Time from landing to a 3-gmina shortlist (J1, moderated test, 5 users) | ≤ 10 min |
| Value | Users who say the J2 verdict changed their view of a plot | ≥ 3 of 5 |

Deliberately not a metric in v1: traffic, sign-ups, revenue. This is a decision
tool for a small number of people first.

## 6. Scope

**Geography.** łódzkie (24 powiats, ~177 gminas) and mazowieckie (42 powiats,
~314 gminas). Aggregation levels: voivodeship → powiat → gmina → (later) obręb
ewidencyjny. Gmina is the default unit — it is the level at which planning
decisions are made and at which GUS/RCN data is reliably available.

**Asset classes**, in priority order:
1. `land_building` — działka budowlana (priority)
2. `land_agricultural` — działka rolna (the investor thesis, and the rezoning gap)
3. `land_recreational` — działka rekreacyjna / ROD-adjacent
4. `house` — dom jednorodzinny, secondary market
5. `flat` — mieszkanie, secondary market (needed for J6's sell-side)

Land types 1–3 are v1. Types 4–5 are ingested from day 1 (so history accrues) but
surfaced only in J6/J7.

**Out of scope entirely:** commercial/industrial property, forests as timber
assets, rental data.

## 7. Data sources

Detailed endpoints, formats, licensing and open questions live in
[`03-data-sources.md`](./03-data-sources.md). Summary:

| Layer | Source | Role | Confidence |
|---|---|---|---|
| Asking prices | Listing portals (Otodom, OLX, and land-specific boards) | Volume, freshness, granularity | High volume, biased upward |
| Transaction prices | **RCN / RCiWN** (property price register, opened up nationally in 2026; GML/API via geoportal) | Ground truth for what things sell for | Authoritative, lagging, patchy |
| Official aggregates | **GUS BDL API** — average transaction prices of land for residential construction, by powiat, urban/rural split | Baseline, sanity check, pre-history | Authoritative, coarse, quarterly |
| Parcels | **GUGiK ULDK** (parcel by ID / by coordinates, geometry in EPSG:2180) + county **WFS** for EGiB | Turns a listing into a real object | Good coverage, uneven per county |
| Zoning | **Rejestr Urbanistyczny** (live 2026-07-01) — *plan ogólny* + MPZP as standardized spatial data; GUGiK national register of general plans | Buildability, the differentiator | Rolling rollout, incomplete until 2029 |
| Boundaries | GUGiK PRG (administrative units) | Aggregation geometry | Stable |
| Constraints | Flood hazard maps (ISOK/Wody Polskie), soil class from EGiB, protected areas (GDOŚ) | Risk flags | Good |
| Accessibility | OSM + a routing engine (self-hosted OSRM/Valhalla) | Drive-time rings | Good |

**Design principle:** official registries are the *authoritative* layer; portal
listings are the *high-frequency* layer. Where they disagree, the registry wins
and the discrepancy is shown, not hidden — the asking-vs-transaction gap is itself
a feature (J5).

## 8. Functional requirements

### 8.1 Ingestion
- FR-1 Per-source connectors, scheduled, incremental, resumable, each writing to a
  raw immutable landing zone (source payload + fetch timestamp + source URL).
- FR-2 Respect `robots.txt`, per-host rate limits and backoff; identify with an
  honest user agent; never authenticate to bypass access controls; never solve or
  circumvent anti-bot challenges. See §12.
- FR-3 **Snapshot semantics**: every crawl records the observed state of each
  listing. Price changes, delisting and relisting are derived from the snapshot
  series, not from the portal's own history (which it does not expose).
- FR-4 Prefer official APIs (GUS BDL, ULDK, WFS, RCN) over scraping wherever the
  same fact is obtainable from both.
- FR-5 Ingestion failures are visible: a per-source health record with last
  success, item counts and a schema-drift alarm (a connector silently returning 0
  items must page us, not quietly flatten a median).

### 8.2 Normalization
- FR-6 Map every listing to a canonical schema (§10) with: price PLN, area m²,
  asset class, zoning claim, utilities, road access, coordinates, gmina TERYT.
- FR-7 Compute `price_per_m2`. Reject or quarantine records failing validation:
  area outside [100 m², 500 000 m²] for land, price outside [1, 100 000] PLN/m²,
  price/area missing, "cena do negocjacji"/"zapytaj o cenę" placeholders.
- FR-8 **Deduplication.** The same plot is routinely listed by 3–6 agencies. Match
  on: (rounded area, price band, geohash-6, normalized title shingles, image
  perceptual hash, phone/agency where present). Group into a `plot_cluster` with
  one canonical record and a `duplicate_count` — which is itself a signal (many
  agencies = motivated seller).
- FR-9 Geocode to gmina TERYT; where a parcel ID is present in the text, resolve
  via ULDK to a real geometry and prefer that over the portal's pin.

### 8.3 Enrichment
- FR-10 Attach parcel attributes: area (registry, not advert), land-use class,
  soil class, precinct.
- FR-11 Attach zoning: designation from *plan ogólny*/MPZP where published, plus
  the derived `buildability` tier — `buildable` / `conditional` / `agricultural` /
  `unknown`. `unknown` must never be silently treated as buildable.
- FR-12 Attach constraints: flood zone, protected area, class I–III farmland,
  no public-road access, transmission-line easement.
- FR-13 Attach accessibility: drive time to Warsaw centre, Łódź centre, nearest
  powiat seat, nearest railway station.

### 8.4 Analytics
- FR-14 Aggregates per (gmina × asset class × month): count, median, p25, p75,
  mean, and the median's sample size. Suppress below n=10; surface the suppression.
- FR-15 Comparable-set engine: given a subject plot, select comparables by
  geography (same gmina, else radius), zoning class, area band ±50%, recency
  ≤ 12 months; return the set, the median, and the subject's deviation. The user
  can exclude comparables and recompute (J2).
- FR-16 Asking-vs-transaction spread per gmina, from RCN vs. our listing corpus.
- FR-17 Time series per gmina/powiat with sample sizes, nominal and CPI-adjusted.
- FR-18 (post-MVP) Hedonic model — `log(price_per_m2) ~ area + buildability +
  utilities + road access + drive time + gmina fixed effects` — used for a
  residual-based "underpriced" flag, shipped only once it beats the naive
  gmina-median baseline on held-out data. Never shipped as an opaque score.

### 8.5 Presentation
- FR-19 **Map view**: choropleth by gmina, metric and filter driven, greying out
  gminas with no matching supply; zoom to individual listings/parcels.
- FR-20 **Plot page**: verdict card, comparable set (map + table), risk badges,
  price history, negotiation panel.
- FR-21 **Comparison board**: 2–4 plots, column-per-plot, differences highlighted,
  weighted ranking with visible reasoning, export to PDF/PNG.
- FR-22 **Trends view**: multi-gmina time series with sample-size bars.
- FR-23 **Coverage/method page**: per-source freshness, per-gmina counts, match
  rates, and a written method note for every computed metric.
- FR-24 (post-MVP) Saved searches and alert digests (J4).
- FR-25 Polish UI copy with Polish domain terms used correctly (*działka
  budowlana*, *plan ogólny*, *wypis i wyrys*, *media*, *droga dojazdowa*).

## 9. Sequencing

Listing data **cannot be backfilled** — the price history that J3/J4/J5/J7 depend
on only exists if we are already collecting. Therefore M1 ships ingestion before
any user-facing surface, and the crawler runs from day one even while the UI is
being designed.

| Milestone | Weeks | Contents | Journeys unblocked |
|---|---|---|---|
| **M0 — Spine** | 1–2 | Repo, schema, boundaries (PRG), TERYT dictionary, GUS BDL baseline import, source health scaffolding | — |
| **M1 — Collect** | 2–5 | Land connectors for both voivodeships, snapshot pipeline, dedup, normalization, validation, coverage page | (data accrues) |
| **M2 — See** | 5–8 | Gmina aggregates, choropleth map, filters, drive-time layer | **J1** |
| **M3 — Judge** | 8–11 | ULDK parcel resolution, zoning + constraint enrichment, comparable engine, plot page, comparison board | **J2, J3**, J8 |
| **M4 — Ground-truth** | 11–14 | RCN ingestion, asking-vs-transaction spread, trends view | **J5, J7** |
| **M5 — Extend** | 14+ | Saved searches + alerts; housing surfaced; buy-vs-build | **J4, J6** |

M2 is the first demoable milestone; M3 is the first genuinely useful one.

## 10. Data model (core entities)

```
source                (id, name, kind[portal|registry|api], base_url, robots_ok,
                       rate_limit, last_success_at, health)
raw_document          (id, source_id, url, fetched_at, payload, content_hash)

listing               (id, source_id, external_id, first_seen_at, last_seen_at,
                       is_active, url, title, description,
                       price_pln, area_m2, price_per_m2,
                       asset_class, zoning_claim, utilities[], road_access,
                       lat, lon, teryt_gmina, parcel_id?, plot_cluster_id,
                       seller_type[private|agency])
listing_snapshot      (listing_id, observed_at, price_pln, is_active)   -- price history
plot_cluster          (id, canonical_listing_id, duplicate_count, member_ids[])

parcel                (id, parcel_identifier, teryt_gmina, obreb, geom,
                       registry_area_m2, land_use_class, soil_class)
parcel_zoning         (parcel_id, plan_type[plan_ogolny|mpzp|none], designation,
                       buildability[buildable|conditional|agricultural|unknown],
                       source_doc, as_of)
parcel_constraint     (parcel_id, kind, severity, source, as_of)

transaction           (id, source[rcn], parcel_id?, teryt_gmina, transacted_at,
                       price_pln, area_m2, price_per_m2, property_kind)

admin_unit            (teryt, level[woj|powiat|gmina], name, geom, parent_teryt,
                       drive_min_to_warszawa, drive_min_to_lodz)
metric_gmina_month    (teryt_gmina, month, asset_class,
                       n, median_ppm2, p25, p75, mean, is_suppressed)
```

Two invariants worth stating: `listing_snapshot` is append-only (it is the only
history we will ever have), and every derived row carries `as_of` + `source` so
FR-23 and G3 are mechanically satisfiable rather than aspirational.

## 11. Architecture (proposed)

- **Ingestion**: Python. `httpx` + `selectolax` for static pages; Playwright
  (already available in this environment) only where a source genuinely requires
  a browser. One module per source implementing a common `fetch → parse → emit`
  contract. Scheduled via cron/GitHub Actions initially; Prefect/Dagster only if
  the DAG earns it.
- **Storage**: PostgreSQL + **PostGIS**. Non-negotiable — every core question
  ("plots within this drive-time ring", "parcels intersecting this zoning
  polygon") is spatial. Raw payloads to object storage or a `raw_document` table.
- **Transformation**: SQL models (dbt-style, or plain versioned SQL) producing the
  `metric_*` tables. Analysis notebooks read the same tables the app does — no
  parallel truth.
- **API**: FastAPI, serving GeoJSON/vector tiles for the choropleth and JSON for
  plot pages.
- **Frontend**: Next.js + **MapLibre GL** (choropleth, listing pins, parcel
  outlines) + a small chart library for trends.
- **Routing**: self-hosted OSRM on an OSM extract of both voivodeships, run
  offline to precompute drive-time columns per gmina.

*Shortcut worth considering:* if we want J1 on screen in two weeks rather than
six, M2 can ship as a Streamlit + pydeck internal tool over the same Postgres,
with the Next.js frontend arriving at M3. The data layer is identical either way,
so this is a reversible choice — recommended if the first audience is us.

## 12. Legal, ethical and operating constraints

Framing: **v1 is a private analytical tool for personal purchase decisions, not a
published service.** That framing is what keeps the following manageable, and it
changes materially if we ever publish or commercialize — treat that as a gate
requiring a fresh review, not a growth step.

- Respect `robots.txt` and portal terms; crawl at a polite rate (single-digit
  requests/minute per host, off-peak); never bypass authentication, paywalls or
  anti-bot measures.
- Store the **minimum** from adverts: price, area, location, attributes. Do not
  store seller names or phone numbers as readable fields — keep only a salted
  hash where needed for deduplication (FR-8), which keeps GDPR exposure minimal.
- Do not republish listing text or photos. Show our derived numbers and link back
  to the source listing.
- Substantial systematic extraction of a portal's database is the specific legal
  risk (sui generis database right), and it grows sharply with commercial reuse of
  a competing product. Keeping v1 private, derived-metrics-only and modest in
  volume is the mitigation.
- Prefer official open data (GUS BDL, ULDK, WFS, RCN, PRG) wherever it answers the
  same question — it is licensed for reuse and carries none of the above risk.
- RCN access may involve fees or per-county request procedures; budget effort for
  that in M4 rather than assuming a clean API everywhere.

## 13. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Portals block or throttle us | Kills the high-frequency layer | Polite crawling; multiple sources; official data as the floor; degrade to GUS/RCN-only aggregates rather than going dark |
| Zoning data incomplete until 2029 | Buildability unknown for many plots | Explicit `unknown` tier, never inferred as buildable; prioritise gminas with published *plan ogólny*; fall back to land-use class as a weak signal |
| Thin rural samples | Misleading medians | n≥10 suppression, IQR shown, sample-size bars everywhere |
| Duplicates inflate counts | Wrong "supply" and skewed medians | plot_cluster dedup; audit 200 records manually per §5 |
| RCN access is bureaucratic/paid | M4 slips | Start the access process during M1; GUS BDL as the interim transaction baseline |
| Silent scraper drift | Corrupted history, unrecoverable | Schema-drift alarms (FR-5), raw payloads retained so re-parsing is always possible |
| Scope creep into all of Poland | Nothing finishes | Region is a parameter, but no non-target-voivodeship data ships in v1 |

## 14. Open questions

1. **Private or public?** Personal decision tool, shared with friends, or a public
   product? This changes §12 from "manageable" to "needs counsel", and changes the
   metrics in §5 entirely.
2. **Budget** for paid data (RCN county fees, a commercial listing-data provider,
   hosting)? A paid feed would remove most of §12's risk.
3. **Which portals** exactly, and are there land-specific boards worth more than
   the big two for rural plots (agricultural land often trades off-portal)?
4. **How far back** should the GUS/RCN baseline go — 3 years or 10?
5. **Warsaw-centric or symmetric?** Do we treat Warsaw as *the* gravity centre
   (which mazowieckie's market suggests), or model łódzkie's Łódź-centred market
   with equal weight?
6. **Drive time vs. distance** — is a self-hosted routing engine worth the setup
   in M2, or does straight-line distance to the nearest station suffice initially?

---

## Appendix — traceability

Every FR traces to at least one journey; every MVP journey has full FR coverage.

| Journey | Requirements |
|---|---|
| J1 Where can I afford | FR-1..9, 14, 19 |
| J2 Is it fairly priced | FR-6..12, 15, 16, 20 |
| J3 Side-by-side | FR-3, 10..13, 15, 21 |
| J4 Alerts | FR-1, 3, 8, 24 |
| J5 Negotiation | FR-3, 16, 20 |
| J6 Buy vs build | FR-6, 14, 22 |
| J7 Trends | FR-14, 17, 22 |
| J8 Trust | FR-5, 7, 14, 23 |
