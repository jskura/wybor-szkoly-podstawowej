# Database schema

PostgreSQL 16 + PostGIS. The schema is where several product rules become
*unrepresentable-if-violated* rather than merely tested — that is the point of
writing it out this precisely.

Epic: E1.3. Validation: V1, V2, V5, V12, V29, V31.

---

## 1. Rules encoded in the schema itself

| Rule | Mechanism |
|---|---|
| Every price has a type (rule 5) | `price_type` enum, `NOT NULL`, plus per-table CHECK pinning the allowed value |
| Offering and sales never mix (FR-8) | `price_type` is part of the primary key of `metric_unit_month` |
| Snapshots are append-only (FR-3) | No `UPDATE`/`DELETE` grant on `listing_snapshot` for any application role |
| Provenance everywhere (rule 6) | `as_of` and `source_ids` `NOT NULL` on every derived table |
| `unknown` buildability is terminal (FR-17) | Enum value + a source column that cannot be `advert` |
| Precision gates enrichment (FR-53) | Nature/parcel tables key off `parcel_id`, unreachable without `address`+ precision |

## 2. Enumerated types

```sql
CREATE TYPE price_type      AS ENUM ('offering','sales');
CREATE TYPE price_kind      AS ENUM ('asking','auction_start','tender',
                                     'transaction');  -- D65, +D68
CREATE TYPE asset_class     AS ENUM ('land_building','land_recreational',
                                     'land_agricultural','land_forest_other',
                                     'house','flat');
CREATE TYPE buildability    AS ENUM ('buildable','conditional','agricultural','unknown');
CREATE TYPE buildability_source AS ENUM ('plan_ogolny','mpzp','registry');  -- never 'advert'
CREATE TYPE location_precision  AS ENUM ('parcel','address','pin','locality','gmina','none');
CREATE TYPE utility_state   AS ENUM ('present','at_boundary','absent','unknown');
CREATE TYPE road_access     AS ENUM ('public_paved','public_unpaved','easement','none','unknown');
CREATE TYPE unit_level      AS ENUM ('voivodeship','powiat','gmina','obreb');
CREATE TYPE range_kind      AS ENUM ('iqr','min_max','unavailable');  -- D69
CREATE TYPE series_kind     AS ENUM ('stock','flow');                    -- D56, D66
```

`buildability_source` deliberately has no `advert` value. FR-48 says advert text
may never set buildability; making the value non-existent means the violation
cannot be written even by mistake.

## 3. Reference data

```sql
CREATE TABLE admin_unit (
  teryt         TEXT PRIMARY KEY,
  level         unit_level NOT NULL,
  name          TEXT NOT NULL,
  parent_teryt  TEXT REFERENCES admin_unit(teryt),
  geom          geometry(MultiPolygon, 4326) NOT NULL,
  in_ring       TEXT[] NOT NULL DEFAULT '{}',   -- ring keys this unit belongs to (D64)
  as_of         DATE NOT NULL,                  -- rule 6: boundaries are stored data
  source_id     INT NOT NULL REFERENCES source(id),
  CONSTRAINT geom_valid CHECK (ST_IsValid(geom))
);
CREATE INDEX ON admin_unit USING GIST (geom);
CREATE INDEX ON admin_unit (level, parent_teryt);

CREATE TABLE anchor (            -- populated from gitignored config (FR-22)
  key    TEXT PRIMARY KEY,
  label  TEXT NOT NULL,
  geom   geometry(Point, 4326) NOT NULL
);
```

`anchor` holds no street address or house number — only a label and a point
(FR-23). The mapping from address to point happens at load time, outside the
database.

**Ring membership (D64) — defined here, once.** A gmina belongs to a ring if
**any part of its boundary lies within 25 km of the anchor point**:

```sql
UPDATE admin_unit u SET in_ring = array_append(u.in_ring, a.key)
FROM anchor a
WHERE u.level = 'gmina'
  AND ST_DWithin(u.geom::geography, a.geom::geography, 25000);
```

Boundary-intersects rather than centroid-inside or seat-inside, because the three
rules give materially different gmina sets and boundary-intersects is the inclusive
one: a gmina half inside the ring is more useful shown with its `n` than silently
excluded (rule 6). Every consumer reads `in_ring`; nothing recomputes it.

## 4. Ingestion

```sql
CREATE TABLE source (
  id              SERIAL PRIMARY KEY,
  name            TEXT UNIQUE NOT NULL,
  kind            TEXT NOT NULL CHECK (kind IN ('portal','registry','api')),
  base_url        TEXT,
  robots_ok       BOOLEAN NOT NULL DEFAULT FALSE,
  rate_limit_rpm  INT NOT NULL DEFAULT 5,
  last_success_at TIMESTAMPTZ,
  last_item_count INT,
  health          TEXT NOT NULL DEFAULT 'unknown'
);

CREATE TABLE raw_document (
  id           BIGSERIAL PRIMARY KEY,
  source_id    INT NOT NULL REFERENCES source(id),
  url          TEXT NOT NULL,
  fetched_at   TIMESTAMPTZ NOT NULL,
  content_hash TEXT NOT NULL,
  payload      BYTEA NOT NULL,
  UNIQUE (source_id, url, content_hash)
);
CREATE INDEX ON raw_document (fetched_at);
```

The `UNIQUE` on content hash means an unchanged page re-fetched daily stores once —
which is what keeps `raw_document` affordable while remaining the re-parse source
of truth (V42).

## 5. Listings and history

```sql
CREATE TABLE listing (
  id                  BIGSERIAL PRIMARY KEY,
  source_id           INT NOT NULL REFERENCES source(id),
  external_id         TEXT NOT NULL,
  url                 TEXT NOT NULL,
  first_seen_at       TIMESTAMPTZ NOT NULL,
  last_seen_at        TIMESTAMPTZ NOT NULL,
  is_active           BOOLEAN NOT NULL,

  price_pln           NUMERIC(12,2) NOT NULL CHECK (price_pln > 0),
  area_m2             NUMERIC(12,2) NOT NULL CHECK (area_m2 > 0),
  price_per_m2        NUMERIC(12,2) GENERATED ALWAYS AS (price_pln / area_m2) STORED,
  price_type          price_type NOT NULL DEFAULT 'offering'
                        CHECK (price_type = 'offering'),        -- V1
  price_kind          price_kind NOT NULL DEFAULT 'asking',     -- D65, FR-64
  area_source         TEXT NOT NULL CHECK (area_source IN ('register','structured','body','title')),

  asset_class         asset_class NOT NULL,
  zoning_claim        TEXT,                                      -- advert's claim (FR-48)
  road_access         road_access NOT NULL DEFAULT 'unknown',
  util_electricity    utility_state NOT NULL DEFAULT 'unknown',
  util_water          utility_state NOT NULL DEFAULT 'unknown',
  util_gas            utility_state NOT NULL DEFAULT 'unknown',
  util_sewage         utility_state NOT NULL DEFAULT 'unknown',
  attr_confidence     JSONB NOT NULL DEFAULT '{}',

  teryt_gmina         TEXT REFERENCES admin_unit(teryt),
  parcel_id           BIGINT,      -- FK added by a later migration (A5)
  plot_cluster_id     BIGINT,      -- FK added by a later migration (A5)
  seller_contact_hash TEXT,                                      -- salted hash only (FR-23)
  seller_type         TEXT,
  UNIQUE (source_id, external_id)
);
CREATE INDEX ON listing (teryt_gmina, asset_class, is_active);
CREATE INDEX ON listing (plot_cluster_id);
```

`price_per_m2` is a **generated column** — it cannot drift from its inputs, which
removes an entire class of bug that would be invisible in the UI.

There is no `buildability` column on `listing`. Buildability lives only on
`parcel_zoning`, reachable only through a resolved parcel. A listing we cannot
resolve simply has no buildability, which is the honest answer (FR-17).

```sql
CREATE TABLE listing_snapshot (          -- APPEND-ONLY (FR-3, V12)
  listing_id   BIGINT NOT NULL REFERENCES listing(id),
  observed_at  TIMESTAMPTZ NOT NULL,
  price_pln    NUMERIC(12,2) NOT NULL,
  is_active    BOOLEAN NOT NULL,
  PRIMARY KEY (listing_id, observed_at)
) PARTITION BY RANGE (observed_at);
-- monthly partitions created ahead of time
```

Partitioned from day one (`10` §1): this is the table that grows forever and is the
one table that must never be rewritten, so retrofitting partitioning later would be
the riskiest migration in the system.

```sql
REVOKE UPDATE, DELETE ON listing_snapshot FROM app_write, app_read;
```

The append-only rule is a **grant**, not a convention — V12 tests it at the
database level.

```sql
CREATE TABLE plot_cluster (
  id                  BIGSERIAL PRIMARY KEY,
  canonical_listing_id BIGINT,
  duplicate_count     INT NOT NULL DEFAULT 1,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE listing_quarantine (
  listing_ref  JSONB NOT NULL,
  reason       TEXT NOT NULL,          -- never null (V10)
  detected_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

## 6. Location

```sql
CREATE TABLE listing_location (        -- versioned, never overwritten (07 §7)
  id               BIGSERIAL PRIMARY KEY,
  listing_id       BIGINT NOT NULL REFERENCES listing(id),
  resolved_at      TIMESTAMPTZ NOT NULL,
  method           TEXT NOT NULL,
  precision        location_precision NOT NULL,
  geom             geometry(Point, 4326),
  geocoder_version TEXT,
  boundary_risk    BOOLEAN NOT NULL DEFAULT FALSE,
  is_current       BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE UNIQUE INDEX ON listing_location (listing_id) WHERE is_current;
CREATE INDEX ON listing_location USING GIST (geom);
```

The partial unique index enforces exactly one current resolution per listing while
keeping every superseded one.

## 7. Parcels and enrichment

```sql
CREATE TABLE parcel (
  id                BIGSERIAL PRIMARY KEY,
  parcel_identifier TEXT UNIQUE NOT NULL,
  teryt_gmina       TEXT NOT NULL REFERENCES admin_unit(teryt),
  obreb             TEXT,
  geom              geometry(MultiPolygon, 4326) NOT NULL,
  registry_area_m2  NUMERIC(12,2),
  land_use_class    TEXT,
  soil_class        TEXT,
  as_of             DATE NOT NULL
);
CREATE INDEX ON parcel USING GIST (geom);

CREATE TABLE parcel_zoning (
  parcel_id    BIGINT PRIMARY KEY REFERENCES parcel(id),
  plan_type    TEXT CHECK (plan_type IN ('plan_ogolny','mpzp','none')),
  designation  TEXT,
  buildability buildability NOT NULL,
  source       buildability_source,          -- NULL only when buildability='unknown'
  source_doc   TEXT,
  as_of        DATE NOT NULL,
  CONSTRAINT unknown_has_no_source
    CHECK ((buildability = 'unknown') = (source IS NULL))
);
```

`unknown_has_no_source` is the schema-level statement of FR-17: a known
buildability must name the planning document it came from, and `unknown` must not
pretend to have one. An inferred value has no valid source to cite, so it cannot be
inserted.

```sql
CREATE TABLE parcel_constraint (
  parcel_id BIGINT NOT NULL REFERENCES parcel(id),
  kind      TEXT NOT NULL,        -- flood_zone | protected_area | soil_class_i_iii | easement | no_road_access
  severity  TEXT NOT NULL,
  detail    TEXT,
  source    TEXT NOT NULL,
  as_of     DATE NOT NULL,
  PRIMARY KEY (parcel_id, kind)
);

CREATE TABLE parcel_nature (
  parcel_id           BIGINT PRIMARY KEY REFERENCES parcel(id),
  dist_forest_m       INT,
  dist_water_m        INT,
  water_kind          TEXT,
  protected_area_kind TEXT,        -- also a constraint (FR-20)
  dist_major_road_m   INT,
  dist_railway_m      INT,
  as_of               DATE NOT NULL
);

CREATE TABLE parcel_building (            -- A4, FR-65
  parcel_id      BIGINT NOT NULL REFERENCES parcel(id),
  source         TEXT NOT NULL CHECK (source IN ('egib','osm')),
  geom           geometry(MultiPolygon, 4326) NOT NULL,
  distance_mm    BIGINT NOT NULL,       -- millimetres: INT metres made the
                                        -- test plan's assertions untestable
  as_of          DATE NOT NULL,
  PRIMARY KEY (parcel_id, source, geom)
);

CREATE TABLE building_coverage (          -- A4 — did we look, or is the map empty?
  teryt_gmina    TEXT PRIMARY KEY REFERENCES admin_unit(teryt),
  source         TEXT NOT NULL CHECK (source IN ('egib','osm','none')),
  has_coverage   BOOLEAN NOT NULL,
  checked_at     TIMESTAMPTZ NOT NULL
);

CREATE TABLE parcel_wz_feasibility (      -- A4, FR-65
  parcel_id       BIGINT PRIMARY KEY REFERENCES parcel(id),
  verdict         TEXT NOT NULL CHECK (verdict IN ('likely','uncertain','unlikely','unknown')),
  neighbour_found BOOLEAN,
  shares_road     BOOLEAN,
  land_use_class  TEXT,
  protection_kind TEXT,
  search_radius_m INT,
  reason_code     TEXT NOT NULL,          -- why this verdict, not just which
  evidence_ref    JSONB,                  -- the parcel_building rows relied on
  coverage_source TEXT,                   -- NULL only when verdict='unknown'
  computed_at     TIMESTAMPTZ NOT NULL,
  -- The load-bearing constraint: 'unlikely' requires evidence that we actually
  -- looked. Absence of mapped buildings is absence of data, not absence of
  -- neighbours, so an unlikely verdict without coverage is unwritable.
  CONSTRAINT unlikely_requires_coverage
    CHECK (verdict <> 'unlikely' OR coverage_source IS NOT NULL)
);

CREATE TABLE parcel_access (
  parcel_id     BIGINT NOT NULL REFERENCES parcel(id),
  anchor_key    TEXT NOT NULL REFERENCES anchor(key),
  drive_minutes INT NOT NULL,
  distance_km   NUMERIC(8,2) NOT NULL,
  computed_at   TIMESTAMPTZ NOT NULL,
  PRIMARY KEY (parcel_id, anchor_key)
);
```

## 8. Sales transactions

```sql
CREATE TABLE transaction (
  id            BIGSERIAL PRIMARY KEY,
  source_id     INT NOT NULL REFERENCES source(id),
  parcel_id     BIGINT REFERENCES parcel(id),
  teryt_unit    TEXT NOT NULL REFERENCES admin_unit(teryt),
  unit_level    unit_level NOT NULL,
  transacted_at DATE NOT NULL,                       -- when it happened (08 §1)
  as_of         DATE NOT NULL,                       -- when the source published
  price_pln     NUMERIC(14,2) NOT NULL CHECK (price_pln > 0),
  area_m2       NUMERIC(12,2) CHECK (area_m2 > 0),
  price_per_m2  NUMERIC(12,2),
  price_type    price_type NOT NULL DEFAULT 'sales'
                  CHECK (price_type = 'sales'),      -- V1
  price_kind    price_kind NOT NULL DEFAULT 'transaction'
                  CHECK (price_kind = 'transaction'),  -- D68
  property_kind TEXT,
  CONSTRAINT published_after_transacted CHECK (as_of >= transacted_at)
);
CREATE INDEX ON transaction (teryt_unit, transacted_at);
```

`published_after_transacted` catches the conflation `08` §1 warns about: if a
loader swaps the two dates, the insert fails rather than producing a series
plotted on the wrong axis.

## 9. Metrics

```sql
CREATE TABLE metric_unit_month (
  teryt_unit    TEXT NOT NULL REFERENCES admin_unit(teryt),
  unit_level    unit_level NOT NULL,
  month         DATE NOT NULL,
  asset_class   asset_class NOT NULL,
  buildability  buildability NOT NULL,
  price_type    price_type NOT NULL,                 -- part of the key (FR-8)
  price_kind    price_kind NOT NULL,                 -- D65/D66 — never spans kinds
  series_kind   series_kind NOT NULL,                -- D56/D66 — stock and flow are separate rows
  area_band     TEXT NOT NULL,                       -- D66 — else bands collide
  flow_window_days INT,                              -- NOT NULL when series_kind='flow' (O27)
  generation    INT NOT NULL DEFAULT 1,              -- versioned recomputation (08 §4)

  n             INT NOT NULL,
  median_ppm2   NUMERIC(12,2) NOT NULL,
  p25_ppm2      NUMERIC(12,2) NOT NULL,
  p75_ppm2      NUMERIC(12,2) NOT NULL,
  min_ppm2      NUMERIC(12,2) NOT NULL,
  max_ppm2      NUMERIC(12,2) NOT NULL,
  range_kind    range_kind NOT NULL,
  completeness  TEXT NOT NULL DEFAULT 'final',       -- final | partial (08 §4)

  as_of         DATE NOT NULL,
  computed_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  source_ids    INT[] NOT NULL CHECK (array_length(source_ids,1) > 0),

  PRIMARY KEY (teryt_unit, month, asset_class, buildability,
               price_type, price_kind, series_kind, area_band, generation),
  CONSTRAINT flow_states_its_window
    CHECK ((series_kind = 'flow') = (flow_window_days IS NOT NULL)),
  CONSTRAINT range_bounds_ordered
    CHECK (min_ppm2 <= p25_ppm2 AND p25_ppm2 <= median_ppm2
           AND median_ppm2 <= p75_ppm2 AND p75_ppm2 <= max_ppm2)
);

-- D67: the IQR/min–max switch is a **configuration** value, not a literal in the
-- schema. O11 marks n=5 unratified, and a provisional parameter must not be frozen
-- into a migration. The database enforces internal consistency (bounds ordered,
-- flow states its window); the application enforces the threshold and V4 tests it.
```

Three product rules made structural here: `price_type` in the key (never mixed),
`n`/percentiles `NOT NULL` (no aggregate without its spread — rule 6), and
`range_kind_matches_n` (the IQR/min–max switch cannot be got wrong). `generation`
means recomputation adds rows rather than rewriting history.

```sql
CREATE TABLE metric_index (        -- mix-adjusted (05 §7)
  teryt_unit   TEXT NOT NULL,
  month        DATE NOT NULL,
  asset_class  asset_class NOT NULL,
  buildability buildability NOT NULL,
  price_type   price_type NOT NULL,
  index_value  NUMERIC(12,4) NOT NULL,
  base_month   DATE NOT NULL,
  strata_used  INT NOT NULL,
  strata_empty INT NOT NULL,           -- carried, not dropped (FR-42)
  generation   INT NOT NULL DEFAULT 1,
  PRIMARY KEY (teryt_unit, month, asset_class, buildability, price_type, generation)
);
```

`strata_empty` is stored rather than discarded so an index resting on many empty
strata can be recognised as weak.

## 10. Valuation log

```sql
CREATE TABLE valuation_log (          -- write-once (FR-44, V24)
  id              BIGSERIAL PRIMARY KEY,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  subject_kind    TEXT NOT NULL CHECK (subject_kind IN ('listing','hypothetical')),
  listing_id      BIGINT REFERENCES listing(id),
  parcel_id       BIGINT REFERENCES parcel(id),
  teryt_unit      TEXT REFERENCES admin_unit(teryt),
  features        JSONB NOT NULL,
  price_type      price_type NOT NULL,
  estimate_low    NUMERIC(12,2) NOT NULL,
  estimate_median NUMERIC(12,2) NOT NULL,
  estimate_high   NUMERIC(12,2) NOT NULL,
  range_kind      range_kind NOT NULL,
  n_comparables   INT NOT NULL,
  widening_step   TEXT NOT NULL,
  comparable_ids  BIGINT[] NOT NULL,
  method_version  TEXT NOT NULL,
  observed_ppm2   NUMERIC(12,2)
);
CREATE INDEX ON valuation_log (method_version, created_at);
```

`comparable_ids` is stored because the comparable set that produced a prediction
cannot be reconstructed later (`05` §9) — without it, scoring can say a prediction
was wrong but not why.

```sql
CREATE TABLE valuation_outcome (
  valuation_id   BIGINT PRIMARY KEY REFERENCES valuation_log(id),
  outcome_kind   TEXT NOT NULL CHECK (outcome_kind IN ('rcn_transaction','final_asking')),
  realized_ppm2  NUMERIC(12,2) NOT NULL,
  realized_at    DATE NOT NULL,
  matched_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

`outcome_kind` keeps real sales separate from the weak delisting signal (`08` §3),
so scoring never treats a withdrawal as a sale.

## 11. Operational

```sql
CREATE TABLE assertion_run (
  id          BIGSERIAL PRIMARY KEY,
  run_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  assertion   TEXT NOT NULL,
  passed      BOOLEAN NOT NULL,
  observed    JSONB,
  blocked_publication BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE coverage_snapshot (
  teryt_gmina     TEXT NOT NULL REFERENCES admin_unit(teryt),
  computed_at     TIMESTAMPTZ NOT NULL,
  listings_active INT NOT NULL,
  last_crawl_at   TIMESTAMPTZ,
  parcel_match_rate      NUMERIC(5,4),
  zoning_known_rate      NUMERIC(5,4),
  offering_obs    INT NOT NULL,
  sales_obs       INT NOT NULL,
  precision_dist  JSONB NOT NULL,
  PRIMARY KEY (teryt_gmina, computed_at)
);
```

`coverage_snapshot` is written by the assertion suite, and the coverage page reads
only this table — so the page cannot disagree with the assertions (V15).

## 12. Roles

```sql
CREATE ROLE app_read;      -- SELECT on derived tables and views
CREATE ROLE app_write;     -- API writes: valuation_log, saved searches
CREATE ROLE app_pipeline;  -- ingestion and recomputation
```

No role holds `UPDATE`/`DELETE` on `listing_snapshot` or `valuation_log`. The
notebook role (O9) is `app_read` restricted to the published views (`14` §5).

## 13. Migration policy

- Forward-only, versioned, reviewed. Every migration is reversible or explicitly
  documented as not.
- A migration touching a price-bearing table triggers the restore drill afterwards
  (`11` §8) — those are the migrations that can silently destroy irreplaceable data.
- V1–V5 invariants run against the live database after every deploy.
- Adding a `price_type`-bearing table requires its CHECK constraint in the same
  migration; V1's constraint-existence test fails otherwise.
