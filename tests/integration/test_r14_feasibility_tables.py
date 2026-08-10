"""R14 — the feasibility tables, and the rule the database makes unwritable.

A test can be deleted. `unlikely_requires_coverage` cannot: a verdict of
`unlikely` without a coverage source is refused by the database, so code that
never runs a test still cannot state that nobody built here on evidence that
nobody looked.

`parcel_building.distance_mm` stores millimetres. An `INT` count of metres made
30.000 and 30.4 indistinguishable and put the test plan's tolerances out of reach
of any assertion that reads the database.
"""

from __future__ import annotations

import datetime

import psycopg
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.needs_db]

PARCEL_IDENTIFIER = "999901_9.9001.1"
# A 60 m square on the synthetic frame, matching the scene's P1. Stored in 4326
# because that is the storage CRS; the metre computation happens in 2180.
PARCEL_WKT = (
    "MULTIPOLYGON(((19.000000 53.000000, 19.000900 53.000000, "
    "19.000900 53.000540, 19.000000 53.000540, 19.000000 53.000000)))"
)
BUILDING_WKT = (
    "MULTIPOLYGON(((19.001350 53.000180, 19.001500 53.000180, "
    "19.001500 53.000270, 19.001350 53.000270, 19.001350 53.000180)))"
)


UNIT_WKT = (
    "MULTIPOLYGON(((19.000000 52.990000, 19.100000 52.990000, "
    "19.100000 53.010000, 19.000000 53.010000, 19.000000 52.990000)))"
)


def insert_unit(conn, teryt: str, name: str) -> None:
    source_id = conn.execute(
        "INSERT INTO source (name, kind, rate_limit_rpm) "
        "VALUES (%s, 'registry', 1) ON CONFLICT (name) DO UPDATE SET kind = 'registry' "
        "RETURNING id",
        ("synthetic",),
    ).fetchone()[0]
    conn.execute(
        "INSERT INTO admin_unit (teryt, level, name, geom, as_of, source_id) "
        "VALUES (%s, 'gmina', %s, ST_GeomFromText(%s, 4326), %s, %s)",
        (teryt, name, UNIT_WKT, datetime.date(2026, 8, 8), source_id),
    )


@pytest.fixture
def parcel_id(conn) -> int:
    insert_unit(conn, "999901", "SYNTH-A")
    row = conn.execute(
        """
        INSERT INTO parcel (parcel_identifier, teryt_gmina, obreb, geom,
                            registry_area_m2, land_use_class, as_of)
        VALUES (%s, %s, %s, ST_GeomFromText(%s, 4326), %s, %s, %s)
        RETURNING id
        """,
        (
            PARCEL_IDENTIFIER,
            "999901",
            "9001",
            PARCEL_WKT,
            3600.00,
            "B",
            datetime.date(2026, 8, 8),
        ),
    ).fetchone()
    conn.execute(
        """
        INSERT INTO building_coverage (teryt_gmina, source, has_coverage, checked_at)
        VALUES (%s, 'egib', TRUE, %s)
        """,
        ("999901", datetime.datetime(2026, 8, 1, tzinfo=datetime.UTC)),
    )
    return row[0]


def insert_verdict(conn, parcel_id: int, **overrides):
    payload = {
        "verdict": "unlikely",
        "neighbour_found": False,
        "shares_road": None,
        "land_use_class": "B",
        "protection_kind": None,
        "search_radius_m": 100,
        "reason_code": "no_neighbour_within_radius",
        "evidence_ref": None,
        "coverage_source": "egib",
    }
    payload.update(overrides)
    conn.execute(
        """
        INSERT INTO parcel_wz_feasibility
          (parcel_id, verdict, neighbour_found, shares_road, land_use_class,
           protection_kind, search_radius_m, reason_code, evidence_ref,
           coverage_source, computed_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
        """,
        (parcel_id, *payload.values()),
    )


# --- the load-bearing constraint -----------------------------------------


def test_unlikely_without_coverage_evidence_is_rejected_by_the_database(
    conn, parcel_id: int
) -> None:
    with pytest.raises(psycopg.errors.IntegrityError) as caught:
        insert_verdict(conn, parcel_id, coverage_source=None)
    assert "unlikely_requires_coverage" in str(caught.value)


def test_unlikely_with_coverage_evidence_is_accepted(conn, parcel_id: int) -> None:
    """The non-vacuity companion. Without it the test above would pass against a
    table that refuses every insert."""
    insert_verdict(conn, parcel_id)
    assert conn.execute(
        "SELECT verdict, coverage_source FROM parcel_wz_feasibility"
    ).fetchone() == ("unlikely", "egib")


def test_a_likely_verdict_may_still_record_its_coverage_evidence(
    conn, parcel_id: int
) -> None:
    """The constraint is an implication, not a biconditional.

    An earlier draft asked for `(verdict = 'unlikely') = (evidence IS NOT NULL)`,
    which forbids a `likely` verdict from recording the coverage evidence it also
    relied on. The implication is the correct shape.
    """
    insert_verdict(
        conn,
        parcel_id,
        verdict="likely",
        neighbour_found=True,
        shares_road=True,
        reason_code="good_neighbour_satisfied",
        coverage_source="egib",
    )
    assert conn.execute(
        "SELECT verdict, coverage_source FROM parcel_wz_feasibility"
    ).fetchone() == ("likely", "egib")


def test_an_unknown_verdict_needs_no_coverage_source(conn, parcel_id: int) -> None:
    insert_verdict(
        conn,
        parcel_id,
        verdict="unknown",
        neighbour_found=None,
        reason_code="building_data_unavailable",
        coverage_source=None,
    )
    assert conn.execute("SELECT count(*) FROM parcel_wz_feasibility").fetchone() == (1,)


def test_every_verdict_row_carries_a_reason_code(conn, parcel_id: int) -> None:
    """Stronger than "unknown carries a reason": every verdict carries one."""
    with pytest.raises(psycopg.errors.NotNullViolation):
        insert_verdict(conn, parcel_id, reason_code=None)


def test_a_verdict_outside_the_vocabulary_is_refused(conn, parcel_id: int) -> None:
    with pytest.raises(psycopg.errors.IntegrityError) as caught:
        insert_verdict(conn, parcel_id, verdict="probably")
    assert "verdict" in str(caught.value)


def test_a_parcel_holds_at_most_one_feasibility_row(conn, parcel_id: int) -> None:
    insert_verdict(conn, parcel_id)
    with pytest.raises(psycopg.errors.UniqueViolation):
        insert_verdict(conn, parcel_id, reason_code="no_neighbour_within_radius")


# --- distances survive the round trip ------------------------------------


def test_distance_is_stored_in_millimetres_not_metres(conn, parcel_id: int) -> None:
    """30.0004 m goes in, 30 000 mm comes back. A round trip that loses the
    millimetre fails, and an integer count of metres loses it by construction."""
    conn.execute(
        """
        INSERT INTO parcel_building (parcel_id, source, geom, distance_mm, as_of)
        VALUES (%s, 'egib', ST_GeomFromText(%s, 4326), %s, %s)
        """,
        (parcel_id, BUILDING_WKT, round(30.0004 * 1_000), datetime.date(2026, 8, 8)),
    )
    stored = conn.execute("SELECT distance_mm FROM parcel_building").fetchone()[0]
    assert stored == 30_000
    assert stored / 1_000 == 30.0

    column = conn.execute(
        """
        SELECT data_type FROM information_schema.columns
         WHERE table_name = 'parcel_building' AND column_name = 'distance_mm'
        """
    ).fetchone()
    assert column == ("bigint",)


def test_a_building_source_outside_the_vocabulary_is_refused(
    conn, parcel_id: int
) -> None:
    with pytest.raises(psycopg.errors.IntegrityError):
        conn.execute(
            """
            INSERT INTO parcel_building (parcel_id, source, geom, distance_mm, as_of)
            VALUES (%s, 'guesswork', ST_GeomFromText(%s, 4326), 1, %s)
            """,
            (parcel_id, BUILDING_WKT, datetime.date(2026, 8, 8)),
        )


# --- SRID is declared, never assumed -------------------------------------


def test_every_new_geometry_column_declares_its_srid(conn) -> None:
    rows = conn.execute(
        """
        SELECT f_table_name, f_geometry_column, srid
          FROM geometry_columns
         WHERE f_table_name IN ('parcel', 'parcel_building')
         ORDER BY f_table_name
        """
    ).fetchall()
    assert rows == [
        ("parcel", "geom", 4326),
        ("parcel_building", "geom", 4326),
    ]


def test_the_coverage_record_cannot_claim_a_layer_it_has_no_source_for(
    conn,
) -> None:
    """Gap 7 of the test plan §8.1, closed here.

    `source = 'none'` with `has_coverage = true` is representable and
    meaningless: it says a layer exists and names no publisher of it.
    """
    insert_unit(conn, "999902", "SYNTH-B")
    with pytest.raises(psycopg.errors.IntegrityError) as caught:
        conn.execute(
            """
            INSERT INTO building_coverage (teryt_gmina, source, has_coverage,
                                           checked_at)
            VALUES ('999902', 'none', TRUE, now())
            """
        )
    assert "coverage_source_matches_presence" in str(caught.value)


def test_a_gmina_without_a_building_layer_is_recordable(conn) -> None:
    """The non-vacuity companion for the constraint above."""
    insert_unit(conn, "999902", "SYNTH-B")
    conn.execute(
        """
        INSERT INTO building_coverage (teryt_gmina, source, has_coverage, checked_at)
        VALUES ('999902', 'none', FALSE, now())
        """
    )
    assert conn.execute(
        "SELECT has_coverage FROM building_coverage WHERE teryt_gmina = '999902'"
    ).fetchone() == (False,)
