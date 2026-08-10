"""Writing an aggregate into `metric_unit_month`.

Every column this table holds is named here. Letting the database fill one in
would store a value nobody chose, which is the failure `config/params.yml` exists
to prevent one level up.

A recomputation writes a new `generation` rather than rewriting the old rows
(`08` §4), so "the August median as we understood it in September" stays
answerable. The caller supplies the generation, because only the caller knows
whether this run is a first computation or a revision.

The table refuses a row whose bounds are out of order and a flow row with no
window. Those are the database's job. The sample-size threshold is not: D67 moved
it to configuration, and a row one observation below it still inserts.
"""

from __future__ import annotations

from collections.abc import Iterable

from .aggregate import Aggregate

METRIC_COLUMNS = (
    "teryt_unit",
    "unit_level",
    "month",
    "asset_class",
    "buildability",
    "price_type",
    "price_kind",
    "series_kind",
    "area_band",
    "flow_window_days",
    "generation",
    "n",
    "median_ppm2",
    # FR-24 lists the mean beside the median. It is never a headline figure —
    # D42 makes the median the answer — but the gap between the two says whether
    # one observation is carrying the group, and that is worth being able to see.
    "mean_ppm2",
    "p25_ppm2",
    "p75_ppm2",
    "min_ppm2",
    "max_ppm2",
    "range_kind",
    "as_of",
    "source_ids",
)

INSERT = (
    f"INSERT INTO metric_unit_month ({', '.join(METRIC_COLUMNS)}) "
    f"VALUES ({', '.join(['%s'] * len(METRIC_COLUMNS))})"
)


def row_values(row: Aggregate, *, generation: int) -> tuple:
    """The aggregate as one tuple, in `METRIC_COLUMNS` order.

    `source_ids` becomes a list: a tuple reaches Postgres as a record, not as an
    array, and the column is `INT[]`.
    """
    return (
        row.teryt_unit,
        row.unit_level,
        row.month,
        row.asset_class,
        row.buildability,
        row.price_type,
        row.price_kind,
        row.series_kind,
        row.area_band,
        row.flow_window_days,
        generation,
        row.n,
        row.median_ppm2,
        row.mean_ppm2,
        row.p25_ppm2,
        row.p75_ppm2,
        row.min_ppm2,
        row.max_ppm2,
        row.range_kind,
        row.as_of,
        list(row.source_ids),
    )


def write_aggregates(conn, aggregates: Iterable[Aggregate], *, generation: int) -> int:
    """Insert every aggregate and return how many rows landed.

    The caller owns the transaction. Nothing here commits, so a failed row leaves
    the whole run out rather than half of it in.
    """
    written = 0
    for row in aggregates:
        conn.execute(INSERT, row_values(row, generation=generation))
        written += 1
    return written
