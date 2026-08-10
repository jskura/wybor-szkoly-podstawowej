"""Add `valuation_log` and `valuation_exclusion`.

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-10

The log ships with the estimator, never after it. A comparable set cannot be
reconstructed later — listings change price, go inactive and disappear — so an
estimate made in August is unexplainable in December unless the set that produced
it was written down at the time.

`comparable_ids` is the column that matters. Without it, scoring can say a
prediction was wrong but not why.
"""

from __future__ import annotations

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE valuation_log (
          id              BIGSERIAL PRIMARY KEY,
          created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
          subject_kind    TEXT NOT NULL
                            CHECK (subject_kind IN ('listing','hypothetical')),
          listing_id      BIGINT REFERENCES listing(id),
          parcel_id       BIGINT,
          teryt_unit      TEXT REFERENCES admin_unit(teryt),
          features        JSONB NOT NULL,
          price_type      price_type NOT NULL,
          -- All three, always. A bare median is not an estimate (D42), and a
          -- nullable bound would let one be written.
          estimate_low    NUMERIC(12,2) NOT NULL,
          estimate_median NUMERIC(12,2) NOT NULL,
          estimate_high   NUMERIC(12,2) NOT NULL,
          range_kind      range_kind NOT NULL,
          n_comparables   INT NOT NULL,
          widening_step   TEXT NOT NULL,
          comparable_ids  BIGINT[] NOT NULL,
          method_version  TEXT NOT NULL,
          observed_ppm2   NUMERIC(12,2),
          CONSTRAINT estimate_bounds_ordered
            CHECK (estimate_low <= estimate_median
                   AND estimate_median <= estimate_high)
        )
    """)
    op.execute("CREATE INDEX ON valuation_log (method_version, created_at)")

    op.execute("""
        CREATE TABLE valuation_exclusion (
          id                  BIGSERIAL PRIMARY KEY,
          valuation_id        BIGINT NOT NULL REFERENCES valuation_log(id),
          excluded_listing_id BIGINT NOT NULL,
          median_before       NUMERIC(12,2) NOT NULL,
          median_after        NUMERIC(12,2) NOT NULL,
          excluded_at         TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # Write-once (FR-44). The log exists to answer "what did we think in
    # August"; a row that can be edited answers nothing.
    op.execute(
        "REVOKE UPDATE, DELETE ON valuation_log FROM app_read, app_write, app_pipeline"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS valuation_exclusion")
    op.execute("DROP TABLE IF EXISTS valuation_log")
