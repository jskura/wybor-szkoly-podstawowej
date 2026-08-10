"""R2.11–R2.19 — the metric table cannot blend what must stay separate.

D66 put `price_type`, `price_kind`, `series_kind` and `area_band` into the primary
key. Without them, a stock row and a flow row for the same gmina and month collide
on insert, and the second silently replaces the first.

D67 kept the sample-size threshold out of the schema, because it is unratified and
a provisional value must not need a migration to change. The database enforces
internal consistency; the application enforces the threshold.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import psycopg
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.needs_db]

MONTH = dt.date(2026, 8, 1)
DAY = dt.date(2026, 8, 1)

EXPECTED_KEY = [
    "teryt_unit",
    "month",
    "asset_class",
    "buildability",
    "price_type",
    "price_kind",
    "series_kind",
    "area_band",
    "generation",
]


def _unit(conn) -> str:
    source_id = conn.execute(
        "INSERT INTO source (name, kind, rate_limit_rpm) "
        "VALUES ('t', 'api', 5) RETURNING id"
    ).fetchone()[0]
    conn.execute(
        "INSERT INTO admin_unit (teryt, level, name, geom, as_of, source_id) "
        "VALUES ('9901011', 'gmina', 'Testowo', "
        "ST_GeomFromText('MULTIPOLYGON(((20 52, 20.1 52, 20.1 52.1, 20 52.1, 20 52)))', 4326), "
        "%s, %s)",
        (DAY, source_id),
    )
    return "9901011"


def _spread(median: str) -> dict:
    """A coherent spread around ``median``.

    Overriding the median alone would leave the default bounds in place and trip
    `range_bounds_ordered` — which is the constraint doing its job, not the test
    finding a defect.
    """
    value = Decimal(median)
    return {
        "median_ppm2": value,
        "p25_ppm2": value * Decimal("0.8"),
        "p75_ppm2": value * Decimal("1.2"),
        "min_ppm2": value * Decimal("0.5"),
        "max_ppm2": value * Decimal("2.0"),
    }


def _metric(conn, teryt: str, **overrides) -> None:
    row = {
        "teryt_unit": teryt,
        "unit_level": "gmina",
        "month": MONTH,
        "asset_class": "land_building",
        "buildability": "unknown",
        "price_type": "offering",
        "price_kind": "asking",
        "series_kind": "stock",
        "area_band": "1000-3000",
        "n": 23,
        "median_ppm2": Decimal("118.00"),
        "p25_ppm2": Decimal("96.00"),
        "p75_ppm2": Decimal("141.00"),
        "min_ppm2": Decimal("61.00"),
        "max_ppm2": Decimal("240.00"),
        "range_kind": "iqr",
        "as_of": DAY,
        "source_ids": [1],
    }
    row.update(overrides)
    columns = ", ".join(row)
    marks = ", ".join(["%s"] * len(row))
    conn.execute(
        f"INSERT INTO metric_unit_month ({columns}) VALUES ({marks})",
        tuple(row.values()),
    )


def test_primary_key_is_exactly_the_nine_columns(conn) -> None:
    columns = [
        row[0]
        for row in conn.execute(
            "SELECT a.attname FROM pg_index i "
            "JOIN pg_class c ON c.oid = i.indrelid "
            "JOIN unnest(i.indkey) WITH ORDINALITY AS k(attnum, ord) ON TRUE "
            "JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum = k.attnum "
            "WHERE c.relname = 'metric_unit_month' AND i.indisprimary "
            "ORDER BY k.ord"
        ).fetchall()
    ]
    assert columns == EXPECTED_KEY
    # unit_level is derivable from teryt_unit. In the key it would let one gmina
    # hold two rows that disagree about what it is.
    assert "unit_level" not in columns


def test_stock_and_flow_do_not_collide(conn) -> None:
    teryt = _unit(conn)
    _metric(conn, teryt, series_kind="stock", **_spread("127.00"))
    _metric(conn, teryt, series_kind="flow", flow_window_days=90, **_spread("118.00"))
    values = dict(
        conn.execute(
            "SELECT series_kind, median_ppm2 FROM metric_unit_month"
        ).fetchall()
    )
    assert values == {"stock": Decimal("127.00"), "flow": Decimal("118.00")}


def test_price_types_do_not_collide(conn) -> None:
    teryt = _unit(conn)
    _metric(conn, teryt, price_type="offering", **_spread("200.00"))
    _metric(
        conn, teryt, price_type="sales", price_kind="transaction", **_spread("100.00")
    )
    assert conn.execute("SELECT count(*) FROM metric_unit_month").fetchone()[0] == 2
    blended = conn.execute(
        "SELECT count(*) FROM metric_unit_month WHERE median_ppm2 = 150.00"
    ).fetchone()[0]
    assert blended == 0


def test_price_kinds_do_not_collide(conn) -> None:
    teryt = _unit(conn)
    _metric(conn, teryt, price_kind="asking", **_spread("200.00"))
    _metric(conn, teryt, price_kind="auction_start", **_spread("60.00"))
    assert conn.execute("SELECT count(*) FROM metric_unit_month").fetchone()[0] == 2


def test_area_bands_do_not_collide(conn) -> None:
    teryt = _unit(conn)
    _metric(conn, teryt, area_band="1000-3000")
    _metric(conn, teryt, area_band="3000-10000", **_spread("70.00"))
    assert conn.execute("SELECT count(*) FROM metric_unit_month").fetchone()[0] == 2


def test_an_identical_row_is_rejected(conn) -> None:
    teryt = _unit(conn)
    _metric(conn, teryt)
    with pytest.raises(psycopg.errors.UniqueViolation):
        _metric(conn, teryt)


def test_flow_must_state_its_window(conn) -> None:
    """A flow median means nothing without the window it covers (O27, V62)."""
    teryt = _unit(conn)
    with pytest.raises(psycopg.errors.CheckViolation):
        _metric(conn, teryt, series_kind="flow")


def test_stock_must_not_state_a_window(conn) -> None:
    teryt = _unit(conn)
    with pytest.raises(psycopg.errors.CheckViolation):
        _metric(conn, teryt, series_kind="stock", flow_window_days=90)


@pytest.mark.parametrize(
    "field,value",
    [
        ("min_ppm2", Decimal("200.00")),  # above p25
        ("p75_ppm2", Decimal("90.00")),  # below the median
        ("max_ppm2", Decimal("100.00")),  # below p75
    ],
)
def test_bounds_out_of_order_are_rejected(conn, field, value) -> None:
    teryt = _unit(conn)
    with pytest.raises(psycopg.errors.CheckViolation):
        _metric(conn, teryt, **{field: value})


def test_a_source_publishing_no_spread_is_writable(conn) -> None:
    """D69. GUS publishes a central value and nothing else.

    Before `unavailable` existed, that row could not be stored at all, so rule 7
    would have forced us to either invent a spread or drop the sales half.
    """
    teryt = _unit(conn)
    _metric(
        conn,
        teryt,
        price_type="sales",
        price_kind="transaction",
        range_kind="unavailable",
        median_ppm2=Decimal("104.00"),
        p25_ppm2=None,
        p75_ppm2=None,
        min_ppm2=None,
        max_ppm2=None,
    )
    row = conn.execute("SELECT range_kind, p25_ppm2 FROM metric_unit_month").fetchone()
    assert row == ("unavailable", None)


def test_a_missing_spread_needs_the_unavailable_label(conn) -> None:
    """Nullability must not become a way to skip rule 7."""
    teryt = _unit(conn)
    with pytest.raises(psycopg.errors.CheckViolation):
        _metric(conn, teryt, range_kind="iqr", p25_ppm2=None)


def test_unavailable_must_omit_every_bound(conn) -> None:
    """Half a spread is worse than none: it looks like a range and is not."""
    teryt = _unit(conn)
    with pytest.raises(psycopg.errors.CheckViolation):
        _metric(
            conn,
            teryt,
            range_kind="unavailable",
            p25_ppm2=Decimal("96.00"),
            p75_ppm2=None,
            min_ppm2=None,
            max_ppm2=None,
        )


def test_source_ids_may_not_be_empty(conn) -> None:
    """Rule 7: every figure names where it came from."""
    teryt = _unit(conn)
    with pytest.raises(psycopg.errors.CheckViolation):
        _metric(conn, teryt, source_ids=[])


def test_no_constraint_freezes_the_sample_size_threshold(conn) -> None:
    """D67 removed `range_kind_matches_n`. This stops it returning.

    The threshold is unratified (O11). Frozen into the schema, changing it would
    need a migration on the table holding every published figure. The assertion
    reads the database rather than the migration source, because prose in a
    migration may name the constraint while explaining its absence.
    """
    names = {
        row[0]
        for row in conn.execute(
            "SELECT c.conname FROM pg_constraint c "
            "JOIN pg_class r ON r.oid = c.conrelid "
            "WHERE r.relname = 'metric_unit_month'"
        ).fetchall()
    }
    assert "range_kind_matches_n" not in names
    # The companions that should exist, so this test cannot pass by the table
    # having no constraints at all.
    assert {"flow_states_its_window", "range_bounds_ordered"} <= names
