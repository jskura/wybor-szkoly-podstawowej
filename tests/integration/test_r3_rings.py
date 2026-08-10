"""R3.19–R3.20 — ring membership is boundary-intersects, and provably so.

D64 chose "any part of the boundary within 25 km" over centroid-inside and
seat-inside. The three rules give materially different gmina sets, and an
implementation that quietly used centroids would pass any test whose fixture the
three rules agree about.

The fixture is built so they disagree. `tests/fixtures/synthetic/ring_membership.json`
holds four annular sectors: two are members under D64 and non-members under the
centroid rule. The discriminating assertion is that the two answers differ.
"""

from __future__ import annotations

import json
import pathlib

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.needs_db]


@pytest.fixture
def ring_fixture(repo_root: pathlib.Path) -> dict:
    path = repo_root / "tests" / "fixtures" / "synthetic" / "ring_membership.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def loaded_ring(conn, ring_fixture: dict):
    from dzialki.geo import assign_rings, load_admin_units, load_anchor

    load_admin_units(conn, ring_fixture)
    load_anchor(conn, ring_fixture["anchor"])
    assign_rings(conn, radius_m=ring_fixture["expected"]["radius_m"])
    return ring_fixture


def _in_ring(conn, key: str) -> list[str]:
    return [
        row[0]
        for row in conn.execute(
            "SELECT teryt FROM admin_unit WHERE level = 'gmina' AND %s = ANY(in_ring) "
            "ORDER BY teryt",
            (key,),
        ).fetchall()
    ]


def test_ring_membership_is_boundary_intersects(conn, loaded_ring) -> None:
    assert _in_ring(conn, "T") == loaded_ring["expected"]["in_ring_T"]


def test_the_boundary_rule_disagrees_with_the_centroid_rule(conn, loaded_ring) -> None:
    """The assertion that makes this fixture worth having.

    If these two lists were equal, every test in this file would pass against an
    implementation using centroids, and D64 would be untested.
    """
    expected = loaded_ring["expected"]
    assert expected["in_ring_T"] != expected["would_be_in_ring_under_centroid_rule"]
    assert _in_ring(conn, "T") != expected["would_be_in_ring_under_centroid_rule"]


def test_a_gmina_just_outside_is_excluded(conn, loaded_ring) -> None:
    """200 m outside, and out. The rule is inclusive at the edge, not vague."""
    for teryt in loaded_ring["expected"]["not_in_ring_T"]:
        assert teryt not in _in_ring(conn, "T")


def test_assigning_rings_twice_changes_nothing(conn, loaded_ring) -> None:
    """R3.19b. Ring assignment appends to an array, so a second run that did not
    guard would give every gmina the key twice."""
    from dzialki.geo import assign_rings

    before = _in_ring(conn, "T")
    arrays_before = conn.execute(
        "SELECT teryt, in_ring FROM admin_unit ORDER BY teryt"
    ).fetchall()
    assign_rings(conn, radius_m=loaded_ring["expected"]["radius_m"])
    assert _in_ring(conn, "T") == before
    assert (
        conn.execute("SELECT teryt, in_ring FROM admin_unit ORDER BY teryt").fetchall()
        == arrays_before
    )


def test_only_gminas_join_a_ring(conn, loaded_ring) -> None:
    """The powiat overlaps the anchor too. Rings are a gmina-level concept, and
    a powiat carrying the key would double-count it in every aggregate."""
    non_gmina = conn.execute(
        "SELECT count(*) FROM admin_unit "
        "WHERE level <> 'gmina' AND cardinality(in_ring) > 0"
    ).fetchone()[0]
    assert non_gmina == 0


def test_measured_distances_match_the_fixture_declaration(conn, loaded_ring) -> None:
    """The fixture claims each sector's inner arc sits at a stated radius.

    Measuring it back through PostGIS proves the geometry says what the manifest
    says. Without this, a bug in the builder would move the sectors and every
    membership assertion would still pass, against the wrong shapes.
    """
    expected = loaded_ring["expected"]["measured_nearest_m"]
    for teryt, declared in expected.items():
        measured = conn.execute(
            "SELECT ST_Distance(u.geom::geography, a.geom::geography) "
            "FROM admin_unit u, anchor a WHERE u.teryt = %s AND a.key = 'T'",
            (teryt,),
        ).fetchone()[0]
        # One metre at 25 km. The sampling step bounds the chord sag well below
        # this, so a wider tolerance would hide a real displacement.
        assert abs(measured - declared) < 1.0, f"{teryt}: {measured} vs {declared}"
