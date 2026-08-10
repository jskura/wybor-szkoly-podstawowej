"""Ring membership, defined once (D64).

A gmina belongs to a ring when **any part of its boundary lies within the radius
of the anchor point**. Not the centroid, not the gmina seat.

The three rules give materially different gmina sets, and boundary-intersects is
the inclusive one. That matches rule 7: a gmina half inside the ring is more
useful shown with its `n` than silently excluded.

The result is materialised into `admin_unit.in_ring`. Every consumer reads that
column; nothing recomputes it. One definition means one place to be wrong.
"""

from __future__ import annotations

# geography, not geometry: ST_DWithin on geography measures metres on the
# spheroid. On geometry in EPSG:4326 it would measure degrees, and 25000 degrees
# is the whole planet.
ASSIGN = """
    UPDATE admin_unit u
       SET in_ring = array_append(u.in_ring, a.key)
      FROM anchor a
     WHERE u.level = 'gmina'
       AND ST_DWithin(u.geom::geography, a.geom::geography, %s)
       -- Idempotent. Without this, a second run gives every member the key
       -- twice and every count that reads the array doubles.
       AND NOT (a.key = ANY(u.in_ring))
"""


def assign_rings(conn, *, radius_m: int) -> None:
    """Recompute `admin_unit.in_ring` for every anchor."""
    conn.execute(ASSIGN, (radius_m,))
