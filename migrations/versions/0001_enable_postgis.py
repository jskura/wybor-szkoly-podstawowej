"""Enable PostGIS.

Revision ID: 0001
Revises:
Create Date: 2026-08-10

Nothing else belongs here. The schema lands in 0002, and keeping the extension
in its own revision means `downgrade base` can be tested against an empty
database rather than one that still holds PostGIS-owned tables.
"""

from __future__ import annotations

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")


def downgrade() -> None:
    # Dropping the extension would take spatial_ref_sys with it. R1.14 treats
    # PostGIS-owned relations as not ours, so leaving it is the correct
    # reversal of "we turned this on".
    pass
