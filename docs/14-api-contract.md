# API contract

The interface between the backend and every consumer (frontend, digests,
query layer). Two invariants are enforced **at this boundary** rather than trusted
to callers, because this is the last place they can be checked:

- **No price without `price_type`** (V3, rule 6)
- **No aggregate without both `n` and a range** (V4, rule 7)

A response violating either is a server error, not a rendering problem.

Epic: E15. Validation: V3, V4, V38, V39.

---

## 1. Conventions

- Base path `/api/v1`. Behind the access gate (`10` §5); no public routes.
- JSON, UTF-8. Money in PLN; areas in m²; distances in metres; durations in minutes.
- Timestamps ISO-8601 UTC. Dates `YYYY-MM-DD`.
- Errors: `{ "error": {"code", "message", "details"} }`. Codes are stable strings.
- Pagination: `?limit=&cursor=`, response `{items, next_cursor}`.
- **Nothing is omitted for thinness.** Absence means genuinely absent, and is
  expressed as an explicit object, never a bare `null` that a client might render
  as zero.

## 2. Shared types

### 2.1 `Money` / `PricePerM2`

```jsonc
{ "value": 118.0, "currency": "PLN", "price_type": "offering" }   // "offering" | "sales"
```

`price_type` is **required**. There is no representation of a price without it.

### 2.2 `Aggregate` — the type that enforces rule 7

```jsonc
{
  "median": 118.0,
  "range": { "low": 96.0, "high": 141.0, "kind": "iqr" },
  // "iqr" (n>=5) | "min_max" (n<5) | "unavailable" (source publishes no spread — D69)
  "n": 23,
  "price_type": "offering",
  "as_of": "2026-08-01",
  "sources": ["portal_a", "gus_bdl"],
  "completeness": { "status": "final" }        // or {"status":"partial","note":"..."}
}
```

Every field is required. There is **no** aggregate type without `n` and `range` —
the shape makes the violation unrepresentable rather than merely forbidden.

### 2.3 `Absent` — why something is missing

```jsonc
{ "absent": true, "reason": "no_sales_data", "detail": "Brak danych transakcyjnych dla tej gminy" }
```

Reasons: `no_sales_data`, `no_listings`, `not_yet_crawled`, `out_of_scope`,
`precision_too_low`, `no_comparables`, `no_plan_data`, `no_building_coverage`. Clients render each differently (`09` §3) — which
is only possible because they are distinguished here.

### 2.4 `Estimate` — the valuation return (FR-32)

```jsonc
{
  "price_type": "offering",
  "range": { "low": 95.0, "high": 140.0, "kind": "iqr" },
  "median": 118.0,
  "n": 23,
  "basis": {
    "widening_step": "gmina",     // gmina | radius_10km | radius_25km | powiat | powiat_wide_area
    "area_band": [800, 2400],
    "buildability": "buildable",
    "recency_months": 12
  },
  "method_version": "cmp-2026.08.1",
  "comparables_url": "/api/v1/estimates/{id}/comparables"
}
```

No `point` field exists (V17). `widening_step` is required so clients can show how
far the search had to reach.

### 2.5 `ModelEstimate` — regression output only (V21)

```jsonc
{
  "kind": "model_estimate",
  "feature": "forest_distance",
  "effect_pln_m2": -0.04,
  "interval": [-0.07, -0.01],
  "model_version": "hedonic-2026.08.1",
  "caveat": "Szacunek modelu — zależność, nie przyczynowość"
}
```

A distinct type from `Estimate`, carrying `kind` and a mandatory `caveat`. The
verdict endpoints can never return this type — enforced by the response models,
which is the serialization half of V21's structural separation.

## 3. Endpoints

### 3.1 Geography and aggregates

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/units` | In-scope units, TERYT, level, parents |
| `GET` | `/units/{teryt}` | One unit with its current aggregates, both price types |
| `GET` | `/units/{teryt}/metrics` | Time series; `?price_type=&asset_class=&buildability=&series=` where `series` ∈ `mix_adjusted` (default) \| `plain_median` |
| `GET` | `/tiles/{z}/{x}/{y}.mvt` | Choropleth vector tiles; filter params in query |
| `GET` | `/coverage` | Per-gmina coverage, freshness, precision distribution |

`/units/{teryt}` returns offering and sales as **separate objects**, never merged:

```jsonc
{
  "teryt": "<TERC>", "name": "Skierniewice", "level": "gmina",   // code to be read from the register, never invented
  "offering": { /* Aggregate */ },
  "sales":    { /* Aggregate or Absent */ },
  "gap": { "pct": 9.4, "offering_as_of": "2026-08-01", "sales_as_of": "2025-12-31" }
}
```

`gap` carries **both** as-of dates because the two are measured over different
periods (V-deferred, FR-10) — presenting them as simultaneous would be wrong.

### 3.2 Listings and plots

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/listings` | Filtered search; returns clusters, not raw duplicates |
| `GET` | `/plots/{id}` | Full plot page payload |
| `GET` | `/plots/{id}/history` | Price intervals with crawl-gap markers |
| `GET` | `/plots/{id}/comparables` | The comparable set behind the verdict |
| `GET` | `/parcels/{identifier}` | Parcel lookup by cadastral identifier |

`/plots/{id}` composes: asking price, `estimate.offering`, `estimate.sales`,
verdict, buildability (or `Absent{no_plan_data}`), `zoning_claim` and any
disagreement flag, risks, nature attributes (or `Absent{precision_too_low}`),
travel times, `location_precision`, and `duplicate_count`.

### 3.3 Valuation

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/estimates` | Estimate from a feature bundle — **no listing needed** (FR-33) |
| `GET` | `/estimates/{id}/comparables` | Enumerated comparable set |
| `POST` | `/estimates/{id}/recompute` | Recompute excluding listed comparable ids (FR-36) |
| `POST` | `/estimates/compare-places` | Same features, several places (FR-33) |
| `GET` | `/features/values` | Feature values — returns `ModelEstimate[]` only |
| `GET` | `/units/{teryt}/rezoning-uplift` | Strata contrast + mandatory caveat (FR-40) |

`POST /estimates` request:

```jsonc
{
  "place": { "kind": "gmina", "teryt": "<TERC>" },   // or {"kind":"point","lat":..,"lon":..,"radius_km":10}
  "features": {
    "area_m2": 1500, "buildability": "buildable",
    "utilities": {"electricity":"at_boundary","water":"present","gas":"unknown","sewage":"septic"},
    "road_access": "public_unpaved"
  },
  "price_types": ["offering", "sales"]
}
```

Response returns one `Estimate` **per requested price type**, plus `Absent` for any
that cannot be produced. Every call writes a `valuation_log` row (V24) — including
calls from notebooks and digests, which is why logging lives in the service layer
rather than in the HTTP handler.

### 3.4 Saved searches and digests (M5)

| Method | Path | Purpose |
|---|---|---|
| `GET`/`POST`/`DELETE` | `/searches` | Saved search CRUD |
| `GET` | `/digests/latest` | Most recent digest, market **and** data-quality events |

### 3.5 Operational

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Liveness |
| `GET` | `/sources` | Per-connector health, last success, item counts |
| `GET` | `/assertions/latest` | Δ assertion results from the last run |
| `GET` | `/method/{metric}` | Method note for a metric — backs the provenance affordance |

`/sources` and `/assertions/latest` are what make J8 answerable: the coverage page
reads them directly, so it cannot disagree with the assertion suite (V15).

## 4. Boundary enforcement

Implemented as response-model validation running on **every** response, not as
review discipline:

1. Any object containing a price-like field lacking `price_type` → 500 + alarm.
2. Any object with `median` lacking `n` or `range` → 500 + alarm.
3. Any `ModelEstimate` reachable from a verdict endpoint → 500 + alarm.
4. Any `range` where `kind` disagrees with `n` (IQR below 5, min–max at or above) → 500.

Failing loudly here is deliberate. A silently malformed response becomes a
confident-looking wrong number in the UI, which is the failure mode this whole
document exists to prevent.

## 5. Stability contract

- `/api/v1` response shapes are additive-only; removals or type changes require
  `v2`.
- The **notebook query layer** (O9) exposes a named set of read-only views with the
  same stability contract. Base tables are explicitly *not* part of it — they may
  change freely, which is what keeps the internal schema evolvable.
- `method_version` and `model_version` are surfaced in every relevant response so a
  consumer can tell when the method behind a number changed (FR-46).
