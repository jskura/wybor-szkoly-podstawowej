"""S9 — every estimate writes a log row, from the first estimate onward.

The log cannot be backfilled. A comparable set is a snapshot of listings that
change price, go inactive and disappear, so an estimate is unexplainable a month
later unless the set that produced it was recorded at the time.
"""

from __future__ import annotations

import datetime as dt
import json
from decimal import Decimal

import psycopg
import pytest

from dzialki.valuation import LOG_COLUMNS, Estimate, write_estimate

pytestmark = [pytest.mark.integration, pytest.mark.needs_db]

AS_OF = dt.date(2026, 8, 8)


def _unit(conn) -> str:
    source_id = conn.execute(
        "INSERT INTO source (name, kind, rate_limit_rpm) "
        "VALUES ('t', 'portal', 5) RETURNING id"
    ).fetchone()[0]
    conn.execute(
        "INSERT INTO admin_unit (teryt, level, name, geom, as_of, source_id) "
        "VALUES ('9901011', 'gmina', 'Testowo', "
        "ST_GeomFromText('MULTIPOLYGON(((20 52, 20.1 52, 20.1 52.1, "
        "20 52.1, 20 52)))', 4326), %s, %s)",
        (AS_OF, source_id),
    )
    return "9901011"


def an_estimate(**overrides) -> Estimate:
    fields = {
        "low": Decimal("110.00"),
        "median": Decimal("126.00"),
        "high": Decimal("140.00"),
        "n": 5,
        "basis": "gmina",
        "widening_step": "gmina",
        "range_kind": "iqr",
        "price_type": "offering",
        "price_kind": "asking",
        "as_of": AS_OF,
        "comparable_ids": (1, 2, 3, 4, 5),
        "below_min_comparables": False,
    }
    fields.update(overrides)
    return Estimate(**fields)


def test_an_estimate_writes_its_comparable_set(conn) -> None:
    """The column that makes scoring able to say *why* a prediction was wrong."""
    teryt = _unit(conn)
    log_id = write_estimate(
        conn,
        an_estimate(),
        subject_kind="hypothetical",
        teryt_unit=teryt,
        features=json.dumps({"area_m2": 3000}),
        observed_ppm2=Decimal("142.00"),
    )
    row = conn.execute(
        "SELECT comparable_ids, n_comparables, estimate_median, method_version "
        "FROM valuation_log WHERE id = %s",
        (log_id,),
    ).fetchone()
    assert row[0] == [1, 2, 3, 4, 5]
    assert row[1] == 5
    assert row[2] == Decimal("126.00")
    assert row[3] != ""


def test_the_log_row_names_every_column_it_writes() -> None:
    """A column added in silence would store a default nobody chose."""
    assert LOG_COLUMNS == (
        "subject_kind",
        "listing_id",
        "parcel_id",
        "teryt_unit",
        "features",
        "price_type",
        "estimate_low",
        "estimate_median",
        "estimate_high",
        "range_kind",
        "n_comparables",
        "widening_step",
        "comparable_ids",
        "method_version",
        "observed_ppm2",
    )


def test_a_log_row_with_bounds_out_of_order_is_rejected(conn) -> None:
    """A bare median is not an estimate. Neither is an inverted range."""
    teryt = _unit(conn)
    with pytest.raises(psycopg.errors.CheckViolation):
        write_estimate(
            conn,
            an_estimate(low=Decimal("200.00")),
            subject_kind="hypothetical",
            teryt_unit=teryt,
            features=json.dumps({}),
        )


def test_no_role_may_rewrite_a_logged_estimate(conn) -> None:
    """FR-44. The log answers "what did we think in August". A row that can be
    edited answers nothing."""
    for role in ("app_read", "app_write", "app_pipeline"):
        for privilege in ("UPDATE", "DELETE"):
            granted = conn.execute(
                "SELECT has_table_privilege(%s, 'valuation_log', %s)",
                (role, privilege),
            ).fetchone()[0]
            assert granted is False, f"{role} may {privilege}"


def test_an_exclusion_records_the_delta_it_caused(conn) -> None:
    """V51c. The reader's judgement changed the answer, so both the judgement
    and its effect are recorded rather than applied silently."""
    teryt = _unit(conn)
    log_id = write_estimate(
        conn,
        an_estimate(),
        subject_kind="hypothetical",
        teryt_unit=teryt,
        features=json.dumps({}),
    )
    conn.execute(
        "INSERT INTO valuation_exclusion "
        "(valuation_id, excluded_listing_id, median_before, median_after) "
        "VALUES (%s, %s, %s, %s)",
        (log_id, 1, Decimal("126.00"), Decimal("133.00")),
    )
    delta = conn.execute(
        "SELECT median_after - median_before FROM valuation_exclusion "
        "WHERE valuation_id = %s",
        (log_id,),
    ).fetchone()[0]
    assert delta == Decimal("7.00")
