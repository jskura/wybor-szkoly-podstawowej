"""Loading administrative units and anchors from a manifest.

Every unit carries its `as_of` and its source, because rule 7 applies to
boundaries as much as to prices: a gmina's shape is stored data with a date, not
a constant.
"""

from __future__ import annotations

SOURCE_KIND = "registry"


def _source_id(conn, name: str) -> int:
    found = conn.execute("SELECT id FROM source WHERE name = %s", (name,)).fetchone()
    if found:
        return found[0]
    # rate_limit_rpm has no column default (FR-75). A manifest source is never
    # fetched over the network, so the slowest sensible value is honest here.
    return conn.execute(
        "INSERT INTO source (name, kind, rate_limit_rpm) VALUES (%s, %s, 1) "
        "RETURNING id",
        (name, SOURCE_KIND),
    ).fetchone()[0]


def load_admin_units(conn, manifest: dict) -> int:
    """Insert every unit in ``manifest``, parents first.

    Returns the number of rows written. The manifest lists parents before
    children, so the self-referencing foreign key resolves without deferring it.
    """
    source_id = _source_id(conn, manifest["source_name"])
    written = 0
    for unit in manifest["units"]:
        conn.execute(
            "INSERT INTO admin_unit "
            "(teryt, level, name, parent_teryt, geom, as_of, source_id) "
            "VALUES (%s, %s, %s, %s, ST_GeomFromText(%s, 4326), %s, %s)",
            (
                unit["teryt"],
                unit["level"],
                unit["name"],
                unit["parent_teryt"],
                unit["wkt"],
                manifest["as_of"],
                source_id,
            ),
        )
        written += 1
    return written


def load_anchor(conn, anchor: dict) -> None:
    """Insert one anchor as a label and a point.

    No street and no house number reach the database (FR-23). The mapping from
    an address to a point happens at load time, outside it.
    """
    conn.execute(
        "INSERT INTO anchor (key, label, geom) "
        "VALUES (%s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326))",
        (anchor["key"], anchor["label"], anchor["lon"], anchor["lat"]),
    )
