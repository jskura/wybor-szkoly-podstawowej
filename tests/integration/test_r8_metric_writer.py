"""R8 — the writer that puts an aggregate into `metric_unit_month`.

Two claims, and they pull in opposite directions on purpose.

The application owns the sample-size threshold (D67), so the database accepts a
row the application would never build. The database owns internal consistency, so
it rejects a row the application could only produce by being wrong. A test for
each, because a threshold frozen into a migration cannot be changed without one.

The canonical five are restated here rather than imported. `tests/unit` is not on
the import path while `tests/integration` is collected, and a stored row that
follows a unit fixture without a failure would be worse than the duplication.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import pathlib
import zoneinfo
from decimal import Decimal

import psycopg
import pytest

from dzialki.config import load_params
from dzialki.metrics import (
    METRIC_COLUMNS,
    Aggregate,
    Observation,
    Series,
    aggregate,
    spread_from_central_value,
    write_aggregates,
)

pytestmark = [pytest.mark.integration, pytest.mark.needs_db]

WARSAW = zoneinfo.ZoneInfo("Europe/Warsaw")
AS_OF = dt.date(2026, 8, 8)
MONTH = dt.date(2026, 8, 1)
TERYT = "9901011"


def _row(listing_id: str, area: str, price: str, first_seen: dt.date) -> Observation:
    return Observation(
        listing_id=listing_id,
        teryt_unit=TERYT,
        unit_level="gmina",
        asset_class="land_building",
        buildability="buildable",
        price_type="offering",
        price_kind="asking",
        area_m2=Decimal(area),
        price_pln=Decimal(price),
        first_seen=dt.datetime(
            first_seen.year, first_seen.month, first_seen.day, 12, tzinfo=WARSAW
        ),
        observed_at=dt.datetime(2026, 8, 8, 12, tzinfo=WARSAW),
        active=True,
        source_id=1,
    )


CANONICAL = [
    _row("C1", "2000", "192000", dt.date(2026, 6, 20)),
    _row("C2", "2500", "275000", dt.date(2026, 7, 11)),
    _row("C3", "3000", "378000", dt.date(2026, 7, 30)),
    _row("C4", "3600", "504000", dt.date(2026, 8, 4)),
    _row("C5", "4400", "660000", dt.date(2025, 4, 2)),  # the stale one
]


@pytest.fixture(scope="module")
def params(repo_root: pathlib.Path):
    return load_params(repo_root / "config" / "params.yml")


@pytest.fixture
def unit(conn) -> str:
    source_id = conn.execute(
        "INSERT INTO source (name, kind, rate_limit_rpm) "
        "VALUES ('r8', 'api', 5) RETURNING id"
    ).fetchone()[0]
    conn.execute(
        "INSERT INTO admin_unit (teryt, level, name, geom, as_of, source_id) "
        "VALUES (%s, 'gmina', 'Testowo', "
        "ST_GeomFromText('MULTIPOLYGON(((20 52, 20.1 52, 20.1 52.1, 20 52.1, "
        "20 52)))', 4326), %s, %s)",
        (TERYT, AS_OF, source_id),
    )
    return TERYT


def rows_for(params):
    return aggregate(
        CANONICAL,
        as_of=AS_OF,
        flow_window_days=params.aggregates.flow_window_days,
        iqr_switch_n=params.aggregates.iqr_switch_n,
    )


def test_the_restated_fixture_matches_the_unit_one() -> None:
    """A guard on the duplication above."""
    assert [row.price_per_m2 for row in CANONICAL] == [96.0, 110.0, 126.0, 140.0, 150.0]


def test_the_canonical_five_land_as_four_rows(conn, unit: str, params) -> None:
    written = write_aggregates(conn, rows_for(params), generation=1)
    assert written == 4

    stored = conn.execute(
        "SELECT area_band, series_kind, n, median_ppm2, p25_ppm2, p75_ppm2, "
        "min_ppm2, max_ppm2, range_kind, flow_window_days "
        # `series_kind` is an enum, and an enum sorts by declaration order.
        # Casting makes the order the test asserts the one a reader expects.
        "FROM metric_unit_month ORDER BY area_band, series_kind::text"
    ).fetchall()
    assert stored == [
        (
            "1500-3000",
            "flow",
            2,
            Decimal("103.00"),
            Decimal("99.50"),
            Decimal("106.50"),
            Decimal("96.00"),
            Decimal("110.00"),
            "min_max",
            90,
        ),
        (
            "1500-3000",
            "stock",
            2,
            Decimal("103.00"),
            Decimal("99.50"),
            Decimal("106.50"),
            Decimal("96.00"),
            Decimal("110.00"),
            "min_max",
            None,
        ),
        (
            "3000-10000",
            "flow",
            2,
            Decimal("133.00"),
            Decimal("129.50"),
            Decimal("136.50"),
            Decimal("126.00"),
            Decimal("140.00"),
            "min_max",
            90,
        ),
        (
            "3000-10000",
            "stock",
            3,
            Decimal("140.00"),
            Decimal("133.00"),
            Decimal("145.00"),
            Decimal("126.00"),
            Decimal("150.00"),
            "min_max",
            None,
        ),
    ]


def test_every_stored_row_carries_its_provenance(conn, unit: str, params) -> None:
    write_aggregates(conn, rows_for(params), generation=1)
    stored = conn.execute(
        "SELECT DISTINCT teryt_unit, unit_level, month, asset_class, buildability, "
        "price_type, price_kind, as_of, source_ids FROM metric_unit_month"
    ).fetchall()
    assert stored == [
        (
            TERYT,
            "gmina",
            MONTH,
            "land_building",
            "buildable",
            "offering",
            "asking",
            AS_OF,
            [1],
        )
    ]


def test_writing_the_same_generation_twice_is_rejected(conn, unit: str, params) -> None:
    write_aggregates(conn, rows_for(params), generation=1)
    with pytest.raises(psycopg.errors.UniqueViolation):
        write_aggregates(conn, rows_for(params), generation=1)


def test_a_recomputation_writes_a_new_generation(conn, unit: str, params) -> None:
    """`08` §4. Recomputation is versioned, never silent, so "the August median
    as we understood it in September" stays answerable."""
    write_aggregates(conn, rows_for(params), generation=1)
    write_aggregates(conn, rows_for(params), generation=2)
    assert conn.execute("SELECT count(*) FROM metric_unit_month").fetchone()[0] == 8
    assert (
        conn.execute(
            "SELECT count(DISTINCT generation) FROM metric_unit_month"
        ).fetchone()[0]
        == 2
    )


def test_the_writer_names_every_column_it_writes() -> None:
    """A column added in silence would store a default nobody chose."""
    assert METRIC_COLUMNS == (
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
        "mean_ppm2",
        "p25_ppm2",
        "p75_ppm2",
        "min_ppm2",
        "max_ppm2",
        "range_kind",
        "as_of",
        "source_ids",
    )


# --- D4 · the database enforces consistency, not the threshold ------------


def test_a_thin_row_labelled_iqr_still_inserts(conn, unit: str, params) -> None:
    """D67, first half. The application owns the switch; D2 is the test for it.

    A row one observation below the threshold, labelled `iqr`, must insert. The
    threshold living in a CHECK is exactly what D67 removed.
    """
    thin = rows_for(params)[0]
    below = params.aggregates.iqr_switch_n - 1
    forced = dataclasses.replace(
        thin,
        series=dataclasses.replace(
            thin.series,
            spread=dataclasses.replace(thin.series.spread, n=below, range_kind="iqr"),
        ),
    )
    assert write_aggregates(conn, [forced], generation=1) == 1
    assert conn.execute("SELECT n, range_kind FROM metric_unit_month").fetchone() == (
        below,
        "iqr",
    )


def test_no_check_constraint_names_the_threshold(conn, params) -> None:
    """D67, restated against the live database rather than the migration source.

    Prose in a migration may name a constraint while explaining its absence.
    """
    clauses = [
        row[0]
        for row in conn.execute(
            "SELECT pg_get_constraintdef(c.oid) FROM pg_constraint c "
            "JOIN pg_class r ON r.oid = c.conrelid "
            "WHERE r.relname = 'metric_unit_month' AND c.contype = 'c'"
        ).fetchall()
    ]
    assert clauses
    threshold = str(params.aggregates.iqr_switch_n)
    for clause in clauses:
        assert f"n < {threshold}" not in clause
        assert f"n >= {threshold}" not in clause


def test_bounds_out_of_order_are_rejected(conn, unit: str, params) -> None:
    """D67, second half. The database is the backstop for a wrong computation."""
    row = rows_for(params)[0]
    broken = dataclasses.replace(
        row,
        series=dataclasses.replace(
            row.series,
            spread=dataclasses.replace(row.series.spread, p25_ppm2=Decimal("999.00")),
        ),
    )
    with pytest.raises(psycopg.errors.CheckViolation):
        write_aggregates(conn, [broken], generation=1)


def test_a_flow_row_without_its_window_is_rejected(conn, unit: str, params) -> None:
    """A flow median means nothing without the window it covers (V62).

    `Series` refuses to build such a row, so the test forges one past the
    constructor. That is the point: the database is the last line, not the only
    one.
    """
    flow = next(row for row in rows_for(params) if row.series_kind == "flow")
    object.__setattr__(flow.series, "flow_window_days", None)
    with pytest.raises(psycopg.errors.CheckViolation):
        write_aggregates(conn, [flow], generation=1)


# --- D69 · a source that publishes no spread ------------------------------


def test_a_central_value_with_no_spread_is_storable(conn, unit: str) -> None:
    """The test plan's question 7 says this row cannot be written, because `15`
    §9 declares the four bound columns `NOT NULL`. The shipped schema declares
    them nullable and guards them with `spread_present_unless_unavailable`, so
    the row stores. This test records which of the two is true.
    """
    row = Aggregate(
        teryt_unit=TERYT,
        unit_level="gmina",
        month=MONTH,
        asset_class="land_building",
        buildability="unknown",
        price_type="sales",
        price_kind="transaction",
        area_band="3000-10000",
        series=Series(
            series_kind="stock",
            flow_window_days=None,
            spread=spread_from_central_value(Decimal("130.00"), n=37),
        ),
        as_of=AS_OF,
        source_ids=(1,),
    )
    assert write_aggregates(conn, [row], generation=1) == 1
    assert conn.execute(
        "SELECT n, median_ppm2, range_kind, p25_ppm2, p75_ppm2, min_ppm2, max_ppm2 "
        "FROM metric_unit_month"
    ).fetchone() == (37, Decimal("130.00"), "unavailable", None, None, None, None)


def test_the_month_is_stored_as_the_first_day(conn, unit: str, params) -> None:
    write_aggregates(conn, rows_for(params), generation=1)
    months = {
        row[0] for row in conn.execute("SELECT month FROM metric_unit_month").fetchall()
    }
    assert months == {MONTH}
