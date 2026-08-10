"""Add the parcel, building, coverage and WZ feasibility tables.

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-10

`unlikely_requires_coverage` is the load-bearing constraint. A test can be
deleted; a check constraint cannot. A verdict of `unlikely` says that nobody has
built near this parcel, and that is an assertion about the world. Without a
coverage source the row states it on evidence that nobody looked, so the database
refuses the insert.

The constraint is an implication, not a biconditional. A `likely` verdict must
stay free to record the coverage evidence it also relied on, and a biconditional
would forbid it.

`distance_mm` is millimetres. An `INT` count of metres made 30.000 and 30.4
indistinguishable and put the test plan's tolerances out of reach of any
assertion that reads the database back.

`coverage_source_matches_presence` closes gap 7 of the test plan §8.1:
`source = 'none'` with `has_coverage = true` is representable and meaningless. It
says a layer exists and names no publisher of it.
"""

from __future__ import annotations

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
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
        )
    """)
    op.execute("CREATE INDEX ON parcel USING GIST (geom)")
    op.execute("CREATE INDEX ON parcel (teryt_gmina)")

    op.execute("""
        CREATE TABLE parcel_building (
          parcel_id      BIGINT NOT NULL REFERENCES parcel(id),
          source         TEXT NOT NULL CHECK (source IN ('egib','osm')),
          geom           geometry(MultiPolygon, 4326) NOT NULL,
          -- Millimetres. Metres as an integer lose the tolerance the tests need.
          distance_mm    BIGINT NOT NULL CHECK (distance_mm >= 0),
          as_of          DATE NOT NULL,
          PRIMARY KEY (parcel_id, source, geom)
        )
    """)
    op.execute("CREATE INDEX ON parcel_building (parcel_id, distance_mm)")

    op.execute("""
        CREATE TABLE building_coverage (
          teryt_gmina    TEXT PRIMARY KEY REFERENCES admin_unit(teryt),
          source         TEXT NOT NULL CHECK (source IN ('egib','osm','none')),
          has_coverage   BOOLEAN NOT NULL,
          checked_at     TIMESTAMPTZ NOT NULL,
          -- A layer with no publisher is not a layer.
          CONSTRAINT coverage_source_matches_presence
            CHECK ((source = 'none') = (has_coverage = FALSE))
        )
    """)

    op.execute("""
        CREATE TABLE parcel_wz_feasibility (
          parcel_id       BIGINT PRIMARY KEY REFERENCES parcel(id),
          verdict         TEXT NOT NULL
                            CHECK (verdict IN
                                   ('likely','uncertain','unlikely','unknown')),
          neighbour_found BOOLEAN,
          shares_road     BOOLEAN,
          land_use_class  TEXT,
          protection_kind TEXT,
          search_radius_m INT,
          -- Why this verdict, not only which. Every verdict carries a reason,
          -- not only `unknown`.
          reason_code     TEXT NOT NULL,
          evidence_ref    JSONB,
          coverage_source TEXT,
          computed_at     TIMESTAMPTZ NOT NULL,
          CONSTRAINT unlikely_requires_coverage
            CHECK (verdict <> 'unlikely' OR coverage_source IS NOT NULL)
        )
    """)
    op.execute("CREATE INDEX ON parcel_wz_feasibility (verdict, reason_code)")


def downgrade() -> None:
    op.execute("DROP TABLE parcel_wz_feasibility")
    op.execute("DROP TABLE building_coverage")
    op.execute("DROP TABLE parcel_building")
    op.execute("DROP TABLE parcel")
