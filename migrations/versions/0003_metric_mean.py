"""Add `metric_unit_month.mean_ppm2`.

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-10

FR-24 lists the mean beside the count, median, percentiles and bounds. The table
carried every other one. Found by writing the aggregate writer, which computed a
mean it had nowhere to put.

The mean is not a headline figure and never becomes one — D42 makes the median
the answer, always with its range and its sample size. The mean is stored because
the gap between the two is evidence: a mean far from the median means one
observation is carrying the group, and that is worth being able to see rather
than worth hiding.

Nullable, because a source that publishes a central value and no observations
(D69) has no mean to compute. The same reasoning as the spread columns.
"""

from __future__ import annotations

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE metric_unit_month ADD COLUMN mean_ppm2 NUMERIC(12,2)")


def downgrade() -> None:
    op.execute("ALTER TABLE metric_unit_month DROP COLUMN mean_ppm2")
