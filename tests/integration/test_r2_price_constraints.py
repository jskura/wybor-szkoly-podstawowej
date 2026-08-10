"""R2.4–R2.10 — rule 6 encoded as constraints, not as a convention.

Every table using the shared `price_kind` enum pins its own subset. `listing`
allows `asking` alone (D115), `notice` allows the two auction kinds (D91), and
`transaction` allows `transaction` alone (D68). The enum says which labels exist;
these CHECKs say which table may carry which.

Each positive test has a negative companion. A CHECK that exists but never fires
is not a constraint, it is decoration.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import psycopg
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.needs_db]

DAY = dt.date(2026, 8, 1)
NOW = dt.datetime(2026, 8, 1, 12, 0, tzinfo=dt.UTC)


def _source(conn) -> int:
    return conn.execute(
        "INSERT INTO source (name, kind, rate_limit_rpm) "
        "VALUES ('t', 'portal', 5) RETURNING id"
    ).fetchone()[0]


def _unit(conn) -> str:
    source_id = _source(conn)
    conn.execute(
        "INSERT INTO admin_unit (teryt, level, name, geom, as_of, source_id) "
        "VALUES ('9901011', 'gmina', 'Testowo', "
        "ST_GeomFromText('MULTIPOLYGON(((20 52, 20.1 52, 20.1 52.1, 20 52.1, 20 52)))', 4326), "
        "%s, %s)",
        (DAY, source_id),
    )
    return "9901011"


def _insert_listing(conn, source_id: int, **overrides) -> None:
    row = {
        "source_id": source_id,
        "external_id": "x1",
        "url": "https://example.invalid/1",
        "first_seen_at": NOW,
        "last_seen_at": NOW,
        "is_active": True,
        "price_pln": Decimal("400000.00"),
        "area_m2": Decimal("3200.00"),
        "area_source": "structured",
        "asset_class": "land_building",
    }
    row.update(overrides)
    columns = ", ".join(row)
    marks = ", ".join(["%s"] * len(row))
    conn.execute(
        f"INSERT INTO listing ({columns}) VALUES ({marks})", tuple(row.values())
    )


def _constraint_defs(conn, relation: str) -> list[str]:
    return [
        row[0]
        for row in conn.execute(
            "SELECT pg_get_constraintdef(c.oid) FROM pg_constraint c "
            "JOIN pg_class r ON r.oid = c.conrelid "
            "WHERE r.relname = %s AND c.contype = 'c'",
            (relation,),
        ).fetchall()
    ]


# --- the constraints exist -------------------------------------------------


def test_listing_pins_price_type_and_price_kind(conn) -> None:
    defs = " ".join(_constraint_defs(conn, "listing"))
    assert "price_type = 'offering'::price_type" in defs
    # D115. Before it, a parser bug could store a sales price as a listing.
    assert "price_kind = 'asking'::price_kind" in defs


def test_transaction_pins_price_type_and_price_kind(conn) -> None:
    defs = " ".join(_constraint_defs(conn, "transaction"))
    assert "price_type = 'sales'::price_type" in defs
    assert "price_kind = 'transaction'::price_kind" in defs


def test_notice_pins_the_two_auction_kinds(conn) -> None:
    defs = " ".join(_constraint_defs(conn, "notice"))
    assert "price_type = 'offering'::price_type" in defs
    assert "auction_start" in defs
    assert "tender" in defs


# --- and they fire ---------------------------------------------------------


def test_listing_rejects_a_sales_price_type(conn) -> None:
    source_id = _source(conn)
    with pytest.raises(psycopg.errors.CheckViolation):
        _insert_listing(conn, source_id, price_type="sales")


def test_listing_rejects_a_transaction_price_kind(conn) -> None:
    """D115's negative test. This insert succeeded before the CHECK existed."""
    source_id = _source(conn)
    with pytest.raises(psycopg.errors.CheckViolation):
        _insert_listing(conn, source_id, price_kind="transaction")


def test_listing_rejects_an_auction_price_kind(conn) -> None:
    """D91 moved every auction into `notice`, so a listing cannot carry one."""
    source_id = _source(conn)
    with pytest.raises(psycopg.errors.CheckViolation):
        _insert_listing(conn, source_id, price_kind="auction_start")


def test_listing_defaults_to_asking_when_kind_is_omitted(conn) -> None:
    source_id = _source(conn)
    _insert_listing(conn, source_id)
    kind = conn.execute("SELECT price_kind FROM listing").fetchone()[0]
    assert kind == "asking"


def test_an_invalid_enum_label_is_rejected_before_any_check(conn) -> None:
    """`asking` is a valid price_kind and an invalid price_type.

    The test documents that the two axes are distinct, and that a typo fails at
    the type rather than reaching a constraint.
    """
    source_id = _source(conn)
    with pytest.raises(psycopg.errors.InvalidTextRepresentation) as caught:
        _insert_listing(conn, source_id, price_type="asking")
    assert "asking" in str(caught.value)


def test_notice_rejects_an_asking_price_kind(conn) -> None:
    source_id = _source(conn)
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            "INSERT INTO notice (source_id, external_id, url, notice_date, "
            "price_kind, as_of) VALUES (%s, 'n1', 'https://example.invalid/n', "
            "%s, 'asking', %s)",
            (source_id, DAY, DAY),
        )


def test_transaction_rejects_an_asking_price_kind(conn) -> None:
    teryt = _unit(conn)
    source_id = conn.execute("SELECT id FROM source LIMIT 1").fetchone()[0]
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            "INSERT INTO transaction (source_id, teryt_unit, unit_level, "
            "transacted_at, as_of, price_pln, price_kind) "
            "VALUES (%s, %s, 'gmina', %s, %s, 100000, 'asking')",
            (source_id, teryt, DAY, DAY),
        )


def test_transaction_rejects_publication_before_the_sale(conn) -> None:
    """A loader that swaps the two dates fails here rather than plotting a
    series on the wrong axis."""
    teryt = _unit(conn)
    source_id = conn.execute("SELECT id FROM source LIMIT 1").fetchone()[0]
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            "INSERT INTO transaction (source_id, teryt_unit, unit_level, "
            "transacted_at, as_of, price_pln) "
            "VALUES (%s, %s, 'gmina', %s, %s, 100000)",
            (source_id, teryt, dt.date(2026, 8, 2), dt.date(2026, 8, 1)),
        )


def test_price_per_m2_is_generated_and_cannot_drift(conn) -> None:
    source_id = _source(conn)
    _insert_listing(
        conn, source_id, price_pln=Decimal("400000.00"), area_m2=Decimal("3200.00")
    )
    value = conn.execute("SELECT price_per_m2 FROM listing").fetchone()[0]
    assert value == Decimal("125.00")
    with pytest.raises(psycopg.errors.GeneratedAlways):
        conn.execute("UPDATE listing SET price_per_m2 = 999")
