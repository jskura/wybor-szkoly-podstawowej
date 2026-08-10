"""The minimal schema: enums, ingestion, listings, notices, sales, metrics.

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-10

Written as SQL rather than generated from models. The test suite builds its
database only from these migrations (V65(B)), so a model-driven schema would let
a migration bug pass every constraint test that runs on top of it.

Order matters twice: `source` before `admin_unit`, which carries `source_id`; and
`admin_unit` before the four tables that reference it.

Two things deliberately absent. The sample-size threshold has no CHECK here —
D67 moved it to configuration because it is unratified, and a provisional value
must not need a migration to change. There is no DEFAULT on
`source.rate_limit_rpm` — FR-75 puts it in the parameter file, and a column
default would freeze a second copy here.
"""

from __future__ import annotations

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

ENUMS = [
    ("price_type", ["offering", "sales"]),
    # D65 named the first three. D68 added the fourth so a sales row can carry
    # a kind at all.
    ("price_kind", ["asking", "auction_start", "tender", "transaction"]),
    (
        "asset_class",
        [
            "land_building",
            "land_recreational",
            "land_agricultural",
            "land_forest_other",
            "house",
            "flat",
        ],
    ),
    ("buildability", ["buildable", "conditional", "agricultural", "unknown"]),
    # FR-48: no 'advert'. The value does not exist, so the violation cannot be
    # written even by mistake.
    ("buildability_source", ["plan_ogolny", "mpzp", "registry"]),
    (
        "location_precision",
        ["parcel", "address", "pin", "locality", "gmina", "none"],
    ),
    ("utility_state", ["present", "at_boundary", "absent", "unknown"]),
    (
        "road_access",
        ["public_paved", "public_unpaved", "easement", "none", "unknown"],
    ),
    ("unit_level", ["voivodeship", "powiat", "gmina", "obreb"]),
    # D69 added 'unavailable': GUS publishes a central value and no spread.
    ("range_kind", ["iqr", "min_max", "unavailable"]),
    ("series_kind", ["stock", "flow"]),
]

TABLES = [
    "coverage_snapshot",
    "assertion_run",
    "metric_unit_month",
    "transaction",
    "listing_quarantine",
    "plot_cluster",
    "notice",
    "listing_snapshot",
    "listing",
    "raw_document",
    "anchor",
    "admin_unit",
    "source",
]

ROLES = ["app_read", "app_write", "app_pipeline"]


def upgrade() -> None:
    for name, labels in ENUMS:
        values = ", ".join(f"'{label}'" for label in labels)
        op.execute(f"CREATE TYPE {name} AS ENUM ({values})")

    op.execute("""
        CREATE TABLE source (
          id              SERIAL PRIMARY KEY,
          name            TEXT UNIQUE NOT NULL,
          kind            TEXT NOT NULL CHECK (kind IN ('portal','registry','api')),
          base_url        TEXT,
          robots_ok       BOOLEAN NOT NULL DEFAULT FALSE,
          rate_limit_rpm  INT NOT NULL,
          last_success_at TIMESTAMPTZ,
          last_item_count INT,
          health          TEXT NOT NULL DEFAULT 'unknown'
        )
    """)

    op.execute("""
        CREATE TABLE admin_unit (
          teryt         TEXT PRIMARY KEY,
          level         unit_level NOT NULL,
          name          TEXT NOT NULL,
          parent_teryt  TEXT REFERENCES admin_unit(teryt),
          geom          geometry(MultiPolygon, 4326) NOT NULL,
          in_ring       TEXT[] NOT NULL DEFAULT '{}',
          as_of         DATE NOT NULL,
          source_id     INT NOT NULL REFERENCES source(id),
          CONSTRAINT geom_valid CHECK (ST_IsValid(geom))
        )
    """)
    op.execute("CREATE INDEX ON admin_unit USING GIST (geom)")
    op.execute("CREATE INDEX ON admin_unit (level, parent_teryt)")

    # No street and no house number, ever. Only a label and a point (FR-23).
    op.execute("""
        CREATE TABLE anchor (
          key    TEXT PRIMARY KEY,
          label  TEXT NOT NULL,
          geom   geometry(Point, 4326) NOT NULL
        )
    """)

    op.execute("""
        CREATE TABLE raw_document (
          id           BIGSERIAL PRIMARY KEY,
          source_id    INT NOT NULL REFERENCES source(id),
          url          TEXT NOT NULL,
          fetched_at   TIMESTAMPTZ NOT NULL,
          content_hash TEXT NOT NULL,
          payload      BYTEA NOT NULL,
          UNIQUE (source_id, url, content_hash)
        )
    """)
    op.execute("CREATE INDEX ON raw_document (fetched_at)")

    op.execute("""
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
          price_per_m2        NUMERIC(12,2)
                                GENERATED ALWAYS AS (price_pln / area_m2) STORED,
          price_type          price_type NOT NULL DEFAULT 'offering'
                                CHECK (price_type = 'offering'),
          price_kind          price_kind NOT NULL DEFAULT 'asking'
                                CHECK (price_kind = 'asking'),

          area_source         TEXT NOT NULL
                                CHECK (area_source IN ('register','structured','body','title')),

          asset_class         asset_class NOT NULL,
          zoning_claim        TEXT,
          road_access         road_access NOT NULL DEFAULT 'unknown',
          util_electricity    utility_state NOT NULL DEFAULT 'unknown',
          util_water          utility_state NOT NULL DEFAULT 'unknown',
          util_gas            utility_state NOT NULL DEFAULT 'unknown',
          util_sewage         utility_state NOT NULL DEFAULT 'unknown',
          attr_confidence     JSONB NOT NULL DEFAULT '{}',

          teryt_gmina         TEXT REFERENCES admin_unit(teryt),
          -- Plain BIGINT. The foreign keys arrive with `parcel` and
          -- `plot_cluster`, and R2.30 pins their absence so that migration has
          -- to add them on purpose.
          parcel_id           BIGINT,
          plot_cluster_id     BIGINT,
          seller_contact_hash TEXT,
          seller_type         TEXT,
          UNIQUE (source_id, external_id)
        )
    """)
    op.execute("CREATE INDEX ON listing (teryt_gmina, asset_class, is_active)")
    op.execute("CREATE INDEX ON listing (plot_cluster_id)")

    op.execute("""
        CREATE TABLE listing_snapshot (
          listing_id   BIGINT NOT NULL REFERENCES listing(id),
          observed_at  TIMESTAMPTZ NOT NULL,
          price_pln    NUMERIC(12,2) NOT NULL,
          is_active    BOOLEAN NOT NULL,
          PRIMARY KEY (listing_id, observed_at)
        ) PARTITION BY RANGE (observed_at)
    """)

    op.execute("""
        CREATE TABLE notice (
          id              BIGSERIAL PRIMARY KEY,
          source_id       INT NOT NULL REFERENCES source(id),
          external_id     TEXT NOT NULL,
          url             TEXT NOT NULL,
          notice_date     DATE NOT NULL,
          auction_at      TIMESTAMPTZ,
          price_pln       NUMERIC(14,2),
          area_m2         NUMERIC(12,2),
          price_per_m2    NUMERIC(12,2) GENERATED ALWAYS AS (
                            CASE WHEN price_pln IS NOT NULL AND area_m2 > 0
                                 THEN price_pln / area_m2 END) STORED,
          price_type      price_type NOT NULL DEFAULT 'offering'
                            CHECK (price_type = 'offering'),
          price_kind      price_kind NOT NULL
                            CHECK (price_kind IN ('auction_start','tender')),
          valuation_pln   NUMERIC(14,2),
          -- A fraction of a plot at a stated price is meaningless without the
          -- fraction, so the column exists beside the figure it qualifies.
          statutory_fraction TEXT,
          parcel_identifier  TEXT,
          teryt_gmina     TEXT REFERENCES admin_unit(teryt),
          as_of           DATE NOT NULL,
          UNIQUE (source_id, external_id)
        )
    """)
    op.execute("CREATE INDEX ON notice (teryt_gmina, notice_date)")

    op.execute("""
        CREATE TABLE plot_cluster (
          id                   BIGSERIAL PRIMARY KEY,
          canonical_listing_id BIGINT,
          duplicate_count      INT NOT NULL DEFAULT 1,
          created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE listing_quarantine (
          listing_ref  JSONB NOT NULL,
          reason       TEXT NOT NULL,
          detected_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE transaction (
          id            BIGSERIAL PRIMARY KEY,
          source_id     INT NOT NULL REFERENCES source(id),
          parcel_id     BIGINT,
          teryt_unit    TEXT NOT NULL REFERENCES admin_unit(teryt),
          unit_level    unit_level NOT NULL,
          transacted_at DATE NOT NULL,
          as_of         DATE NOT NULL,
          price_pln     NUMERIC(14,2) NOT NULL CHECK (price_pln > 0),
          area_m2       NUMERIC(12,2) CHECK (area_m2 > 0),
          price_per_m2  NUMERIC(12,2),
          price_type    price_type NOT NULL DEFAULT 'sales'
                          CHECK (price_type = 'sales'),
          price_kind    price_kind NOT NULL DEFAULT 'transaction'
                          CHECK (price_kind = 'transaction'),
          property_kind TEXT,
          CONSTRAINT published_after_transacted CHECK (as_of >= transacted_at)
        )
    """)
    op.execute("CREATE INDEX ON transaction (teryt_unit, transacted_at)")

    op.execute("""
        CREATE TABLE metric_unit_month (
          teryt_unit    TEXT NOT NULL REFERENCES admin_unit(teryt),
          unit_level    unit_level NOT NULL,
          month         DATE NOT NULL,
          asset_class   asset_class NOT NULL,
          buildability  buildability NOT NULL,
          price_type    price_type NOT NULL,
          price_kind    price_kind NOT NULL,
          series_kind   series_kind NOT NULL,
          area_band     TEXT NOT NULL,
          flow_window_days INT,
          generation    INT NOT NULL DEFAULT 1,

          n             INT NOT NULL,
          median_ppm2   NUMERIC(12,2) NOT NULL,
          p25_ppm2      NUMERIC(12,2),
          p75_ppm2      NUMERIC(12,2),
          min_ppm2      NUMERIC(12,2),
          max_ppm2      NUMERIC(12,2),
          range_kind    range_kind NOT NULL,
          completeness  TEXT NOT NULL DEFAULT 'final',

          as_of         DATE NOT NULL,
          computed_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
          -- COALESCE, not a bare comparison: array_length('{}', 1) is NULL,
          -- and a CHECK treats NULL as satisfied. Written the obvious way
          -- this let an empty source list through, and rule 7 with it.
          source_ids    INT[] NOT NULL
                          CHECK (COALESCE(array_length(source_ids,1), 0) > 0),

          PRIMARY KEY (teryt_unit, month, asset_class, buildability,
                       price_type, price_kind, series_kind, area_band, generation),
          CONSTRAINT flow_states_its_window
            CHECK ((series_kind = 'flow') = (flow_window_days IS NOT NULL)),
          CONSTRAINT spread_present_unless_unavailable
            CHECK (
              (range_kind = 'unavailable'
                AND p25_ppm2 IS NULL AND p75_ppm2 IS NULL
                AND min_ppm2 IS NULL AND max_ppm2 IS NULL)
              OR
              (range_kind IN ('iqr','min_max')
                AND p25_ppm2 IS NOT NULL AND p75_ppm2 IS NOT NULL
                AND min_ppm2 IS NOT NULL AND max_ppm2 IS NOT NULL)
            ),
          CONSTRAINT range_bounds_ordered
            CHECK (range_kind = 'unavailable'
                   OR (min_ppm2 <= p25_ppm2 AND p25_ppm2 <= median_ppm2
                       AND median_ppm2 <= p75_ppm2 AND p75_ppm2 <= max_ppm2))
        )
    """)

    op.execute("""
        CREATE TABLE assertion_run (
          id          BIGSERIAL PRIMARY KEY,
          run_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
          assertion   TEXT NOT NULL,
          passed      BOOLEAN NOT NULL,
          observed    JSONB,
          blocked_publication BOOLEAN NOT NULL DEFAULT FALSE
        )
    """)

    op.execute("""
        CREATE TABLE coverage_snapshot (
          teryt_gmina     TEXT NOT NULL REFERENCES admin_unit(teryt),
          computed_at     TIMESTAMPTZ NOT NULL,
          listings_active INT NOT NULL,
          last_crawl_at   TIMESTAMPTZ,
          parcel_match_rate NUMERIC(5,4),
          zoning_known_rate NUMERIC(5,4),
          offering_obs    INT NOT NULL,
          sales_obs       INT NOT NULL,
          precision_dist  JSONB NOT NULL,
          PRIMARY KEY (teryt_gmina, computed_at)
        )
    """)

    for role in ROLES:
        op.execute(f"""
            DO $$ BEGIN
              IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN
                CREATE ROLE {role};
              END IF;
            END $$
        """)

    # Append-only is a grant, not a convention (FR-3, V12). `app_pipeline` is
    # included: the pipeline writes snapshots, it never rewrites them.
    op.execute(
        "REVOKE UPDATE, DELETE ON listing_snapshot "
        "FROM app_read, app_write, app_pipeline"
    )


def downgrade() -> None:
    for table in TABLES:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
    for name, _labels in reversed(ENUMS):
        op.execute(f"DROP TYPE IF EXISTS {name}")
    # The roles are cluster-wide, not database-scoped. Dropping them here would
    # remove them from every other database in the cluster, so they stay.
