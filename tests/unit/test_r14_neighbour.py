"""R14 — the first test of the stage: missing building data yields `unknown`.

> Absence of observed buildings in a poorly-mapped county is absence of *data*,
> not absence of *neighbours*. A verdict of `unlikely` is an assertion about the
> world. We may only make it when we hold positive evidence that the world was
> actually looked at.

This file is written before the composite, because it is the rule the whole
stage exists to satisfy, and it is the one under pressure later when `unknown`
looks unhelpful on a screen and someone wants to "default sensibly".

An implementation that answers `unknown` everywhere passes the headline test.
The three companions below take its teeth back.
"""

from __future__ import annotations

import datetime
import pathlib

import pytest
import yaml

pytestmark = [pytest.mark.unit]

RUN_DATE = datetime.date(2026, 8, 8)


@pytest.fixture
def scene(repo_root: pathlib.Path) -> dict:
    path = repo_root / "tests" / "fixtures" / "synthetic" / "wz_scene.yml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def rectangle(scene: dict, group: str, identifier: str):
    from dzialki.enrich.geometry import PLANAR_SRID, Rectangle

    for row in scene[group]:
        if row["id"] == identifier:
            return Rectangle(*row["rectangle"], srid=PLANAR_SRID)
    raise LookupError(f"{identifier} is not in {group}")


def buildings_of(scene: dict):
    from dzialki.enrich.geometry import PLANAR_SRID, Rectangle
    from dzialki.enrich.wz.neighbour import Building

    return tuple(
        Building(
            identifier=row["id"],
            rectangle=Rectangle(*row["rectangle"], srid=PLANAR_SRID),
            source=row["source"],
            as_of=datetime.date.fromisoformat(scene["as_of"]),
        )
        for row in scene["buildings"]
    )


def coverage_record(scene: dict, teryt: str):
    from dzialki.enrich.coverage import CoverageRecord

    for row in scene["units"]:
        if row["teryt"] == teryt:
            return CoverageRecord(
                teryt_gmina=teryt,
                source=row["coverage"]["source"],
                has_coverage=row["coverage"]["has_coverage"],
                checked_at=datetime.date.fromisoformat(row["coverage"]["checked_at"]),
            )
    raise LookupError(teryt)


def signal_for(scene: dict, subject: str, *, radius_m: int = 100, buildings=...):
    from dzialki.enrich.wz.neighbour import neighbour_signal

    row = next(item for item in scene["subjects"] if item["id"] == subject)
    if buildings is ...:
        buildings = buildings_of(scene)
    return neighbour_signal(
        rectangle(scene, "parcels", subject),
        buildings,
        coverage_record(scene, row["teryt_gmina"]),
        radius_m=radius_m,
    )


# --- the headline test ----------------------------------------------------


def test_missing_building_data_yields_unknown_not_unlikely(scene: dict) -> None:
    """P4 sits in SYNTH-B, which publishes parcels and no building layer.

    P4 is geometrically indistinguishable from P3 at parcel scale. Only the
    gmina's coverage record separates them, and an implementation that reads the
    two the same way is exactly the F14 failure.
    """
    signal = signal_for(scene, "P4")

    assert signal.value == "unknown"
    assert signal.value != "absent"
    assert signal.reason_code == "building_data_unavailable"
    assert signal.source is None
    assert signal.count == 0


# --- the three companions, without which the headline is degenerate -------


def test_an_isolated_parcel_with_positive_coverage_is_absent_not_unknown(
    scene: dict,
) -> None:
    """P3. Zero buildings within 100 m, eleven within 2 km.

    This is the test that gives the headline its teeth: an always-`unknown`
    implementation fails here.
    """
    signal = signal_for(scene, "P3")

    assert signal.value == "absent"
    assert signal.count == 0
    assert signal.nearest_distance_m == 860.930
    assert signal.radius_m == 100


def test_a_failed_building_query_is_a_different_unknown(scene: dict) -> None:
    """`unknown` from no data and `unknown` from a failed read are two facts.

    Without a distinguishing code the interface cannot say which, and both
    collapse into an unactionable shrug.
    """
    signal = signal_for(scene, "P1", buildings=None)

    assert signal.value == "unknown"
    assert signal.reason_code == "building_query_failed"


def test_the_osm_source_is_recorded_so_the_composite_can_cap_it(
    scene: dict,
) -> None:
    """P11's only neighbour is an OSM building. The signal says so."""
    signal = signal_for(scene, "P11")

    assert signal.value == "present"
    assert signal.source == "osm"
    assert signal.nearest_distance_m == 30.0


# --- what the signal reports ---------------------------------------------


def test_a_building_within_the_radius_counts(scene: dict) -> None:
    signal = signal_for(scene, "P1")
    assert signal.value == "present"
    assert signal.count == 1
    assert signal.nearest_distance_m == 30.0
    assert signal.source == "egib"


def test_a_building_on_the_subject_parcel_is_not_a_neighbour(scene: dict) -> None:
    """P2 carries B2own inside its own boundary and two buildings at 300 m.

    A naive "any building within the radius" implementation reports `present` at
    0.000 m and fails here.
    """
    signal = signal_for(scene, "P2")

    assert signal.value == "absent"
    assert signal.count == 0
    assert signal.nearest_distance_m == 300.0


def test_distance_is_measured_from_the_boundary(scene: dict) -> None:
    """P6. A centroid implementation reports 235 m and answers `absent`."""
    signal = signal_for(scene, "P6")
    assert signal.value == "present"
    assert signal.nearest_distance_m == 60.0


def test_egib_is_preferred_over_osm_when_both_are_in_range(scene: dict) -> None:
    """The source recorded with the signal decides whether M1 caps the verdict."""
    from dzialki.enrich.geometry import PLANAR_SRID, Rectangle
    from dzialki.enrich.wz.neighbour import Building, neighbour_signal

    parcel = rectangle(scene, "parcels", "P1")
    both = (
        Building(
            identifier="OSM-1",
            rectangle=Rectangle(
                600_090.0, 600_100.0, 500_020.0, 500_030.0, srid=PLANAR_SRID
            ),
            source="osm",
            as_of=datetime.date(2026, 8, 8),
        ),
        Building(
            identifier="EGIB-1",
            rectangle=Rectangle(
                600_110.0, 600_120.0, 500_020.0, 500_030.0, srid=PLANAR_SRID
            ),
            source="egib",
            as_of=datetime.date(2026, 8, 8),
        ),
    )
    signal = neighbour_signal(
        parcel, both, coverage_record(scene, "999901"), radius_m=100
    )
    assert signal.count == 2
    assert signal.source == "egib"


def test_the_signal_reports_its_count_and_its_radius(scene: dict) -> None:
    """Rule 7. The verdict ships with `n` and the radius, never as a bare word."""
    signal = signal_for(scene, "P1")
    assert (signal.count, signal.radius_m) == (1, 100)
    assert signal.as_of == datetime.date(2026, 8, 8)


# --- the radius is configuration -----------------------------------------


def test_changing_the_radius_changes_the_answer(scene: dict) -> None:
    """P2 is the only subject that flips on radius alone: its two neighbours sit
    at exactly 300.000 m, so it is `absent` up to 200 m and `present` at 350."""
    assert signal_for(scene, "P2", radius_m=200).value == "absent"
    assert signal_for(scene, "P2", radius_m=350).value == "present"


def test_a_building_exactly_on_the_radius_counts(scene: dict) -> None:
    """`<=`, not `<`. The boundary is asserted, not assumed."""
    assert signal_for(scene, "P2", radius_m=300).value == "present"
    assert signal_for(scene, "P2", radius_m=299).value == "absent"


def test_the_number_of_buildings_in_the_probe_radius_is_countable(
    scene: dict,
) -> None:
    """The control count, which is a different question from the neighbour."""
    from dzialki.enrich.wz.neighbour import buildings_within

    expected = {
        "P1": 9,
        "P2": 8,
        "P3": 11,
        "P4": 0,
        "P5": 2,
        "P6": 7,
        "P7": 3,
        "P8": 3,
        "P9": 1,
        "P10": 0,
        "P11": 1,
        "P12": 3,
    }
    for subject, count in expected.items():
        found = buildings_within(
            rectangle(scene, "parcels", subject),
            buildings_of(scene),
            radius_m=2_000,
        )
        assert len(found) == count, subject
