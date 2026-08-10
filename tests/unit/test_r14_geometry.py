"""R14 — the metre kernel, the tolerance budget, and the degree controls.

Every later assertion in this stage is a number of metres. If metres are wrong,
none of them mean anything, so this file comes before the data it measures.

The tolerance budget is a declared table with one row per scale. V31 says
"within 1 m", and that holds at good-neighbour scale and does not hold at ring
scale, where PUWG 1992's own length distortion is about 0.7 m per kilometre.
Declaring the tiers keeps someone from widening "1 m" quietly later.

The degree controls are the other half. C1 to C3 compute in raw degrees and are
off by five orders of magnitude, so they die on contact with any assertion. C4
and C5 are the controls that matter: "a degree is 111 320 metres" is right to
0.01 % north-south and badly wrong east-west, so it **passes** a north-south
known-answer test. That is the trap, and the tests below assert both halves of
it.
"""

from __future__ import annotations

import math
import pathlib

import pytest
import yaml

pytestmark = [pytest.mark.unit]


@pytest.fixture
def scene(repo_root: pathlib.Path) -> dict:
    path = repo_root / "tests" / "fixtures" / "synthetic" / "wz_scene.yml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def rect(scene: dict, group: str, identifier: str):
    from dzialki.enrich.geometry import PLANAR_SRID, Rectangle

    for row in scene[group]:
        if row["id"] == identifier:
            return Rectangle(*row["rectangle"], srid=PLANAR_SRID)
    raise LookupError(f"{identifier} is not in {group}")


def baseline(scene: dict, name: str) -> dict:
    for row in scene["degree_controls"]["baselines"]:
        if row["name"] == name:
            return row
    raise LookupError(f"{name} is not a declared control baseline")


# --- the kernel refuses what it cannot measure ----------------------------


def test_the_metre_kernel_refuses_a_geographic_srid() -> None:
    """A wrong number that looks like a number is the failure this prevents."""
    from dzialki.enrich.geometry import GeographicSridError, Rectangle

    with pytest.raises(GeographicSridError) as caught:
        Rectangle(19.0, 19.1, 53.0, 53.1, srid=4326)
    assert "4326" in str(caught.value)
    assert "2180" in str(caught.value)


def test_an_inverted_rectangle_is_refused() -> None:
    from dzialki.enrich.geometry import PLANAR_SRID, Rectangle

    with pytest.raises(ValueError):
        Rectangle(600_060.0, 600_000.0, 500_000.0, 500_060.0, srid=PLANAR_SRID)


# --- tier S: the scene's distances are definitions, not measurements ------


@pytest.mark.parametrize(
    "identifier,expected_m",
    [
        ("P1", 30.0),
        ("P2", 300.0),
        ("P3", 860.930),
        ("P4", 2_400.0),
        ("P5", 40.0),
        ("P6", 60.0),
        ("P7", 45.0),
        ("P8", 438.321),
        ("P9", 30.0),
        ("P10", 2_490.0),
        ("P11", 30.0),
    ],
)
def test_nearest_neighbour_distance_matches_the_declaration(
    scene: dict, identifier: str, expected_m: float
) -> None:
    """Tier S: pure planar arithmetic, so the only permissible error is float."""
    from dzialki.enrich.geometry import distance_m, within_tolerance

    subject = next(row for row in scene["subjects"] if row["id"] == identifier)
    parcel = rect(scene, "parcels", identifier)
    building = rect(scene, "buildings", subject["nearest_neighbour_building"])

    computed = distance_m(parcel, building)
    assert round(computed, 3) == expected_m
    assert within_tolerance(computed, expected_m, tier_name="S") is True


def test_distance_measured_from_boundary_not_centroid(scene: dict) -> None:
    """P6 is the trap. At radius 100 the two implementations disagree."""
    from dzialki.enrich.geometry import centroid_distance_m, distance_m

    parcel = rect(scene, "parcels", "P6")
    building = rect(scene, "buildings", "B6")

    assert round(distance_m(parcel, building), 3) == 60.0
    assert round(centroid_distance_m(parcel, building), 3) == 235.0


def test_a_building_on_the_parcel_is_at_zero_distance(scene: dict) -> None:
    """B2own is inside P2. A naive "any building in radius" reports 0.000 m."""
    from dzialki.enrich.geometry import distance_m

    assert (
        distance_m(rect(scene, "parcels", "P2"), rect(scene, "buildings", "B2own"))
        == 0.0
    )


# --- shared edges and single vertices -------------------------------------


def test_parcel_sharing_an_edge_with_a_road_parcel_is_adjacent(scene: dict) -> None:
    from dzialki.enrich.geometry import shared_edge_m

    assert (
        shared_edge_m(rect(scene, "parcels", "P1"), rect(scene, "roads", "R1")) == 60.0
    )
    assert (
        shared_edge_m(rect(scene, "parcels", "P6"), rect(scene, "roads", "R1")) == 350.0
    )


def test_single_vertex_contact_is_not_road_adjacency(scene: dict) -> None:
    """P3 touches R3 at exactly one point. Corner contact is not access."""
    from dzialki.enrich.geometry import distance_m, shared_edge_m

    parcel = rect(scene, "parcels", "P3")
    road = rect(scene, "roads", "R3")
    assert distance_m(parcel, road) == 0.0
    assert shared_edge_m(parcel, road) == 0.0


def test_protected_overlap_is_measured_by_area_and_kind(scene: dict) -> None:
    from dzialki.enrich.geometry import overlap_m2

    parcel = rect(scene, "parcels", "P5")
    assert overlap_m2(parcel, rect(scene, "protected_areas", "SYNTH-PARK")) == 1_800.0
    assert (
        overlap_m2(parcel, rect(scene, "protected_areas", "SYNTH-OTULINA")) == 1_800.0
    )


# --- the tolerance budget -------------------------------------------------


def test_distance_tolerance_budget_is_declared_per_scale() -> None:
    from dzialki.enrich.geometry import TOLERANCE_BUDGET

    declared = {
        tier.name: (tier.kind, tier.budget, tier.covers_from_m, tier.covers_to_m)
        for tier in TOLERANCE_BUDGET
    }
    assert declared == {
        "S": ("absolute_m", 0.001, 0.0, 50_000.0),
        "G": ("absolute_m", 1.0, 0.0, 1_000.0),
        "G_round_trip": ("absolute_m", 0.050, 0.0, 1_000.0),
        "R": ("relative_fraction", 0.001, 1_000.0, 50_000.0),
    }


def test_the_helper_refuses_a_comparison_at_an_undeclared_scale() -> None:
    """A tolerance nobody declared is a tolerance nobody chose."""
    from dzialki.enrich.geometry import UndeclaredScaleError, within_tolerance

    with pytest.raises(UndeclaredScaleError) as caught:
        within_tolerance(200_000.0, 200_000.5, tier_name="R")
    assert "R" in str(caught.value)
    assert "200000" in str(caught.value).replace(" ", "").replace(",", "")


def test_an_unknown_tier_name_is_refused() -> None:
    from dzialki.enrich.geometry import UndeclaredScaleError, within_tolerance

    with pytest.raises(UndeclaredScaleError):
        within_tolerance(300.0, 300.0, tier_name="whatever")


def test_the_round_trip_tier_fails_before_the_good_neighbour_tier() -> None:
    """G_round_trip is the tripwire. It sits below the projection distortion, so
    the 1 m budget cannot be eaten a centimetre at a time."""
    from dzialki.enrich.geometry import within_tolerance

    assert within_tolerance(300.0, 300.2, tier_name="G") is True
    assert within_tolerance(300.0, 300.2, tier_name="G_round_trip") is False


def test_the_ring_tier_is_relative_not_absolute() -> None:
    from dzialki.enrich.geometry import within_tolerance

    assert within_tolerance(25_000.0, 25_020.0, tier_name="R") is True
    assert within_tolerance(25_000.0, 25_030.0, tier_name="R") is False


# --- the degree controls, which must fail ---------------------------------


@pytest.mark.parametrize(
    "name,expected_naive,tier_name",
    [
        ("C_short_north_south", 0.00269575, "G"),
        ("C_short_east_west", 0.004468460001, "G"),
        ("C_ring_north_south", 0.224641596, "R"),
        ("C_ring_east_west", 0.372368765386, "R"),
    ],
)
def test_raw_degree_distance_is_off_by_five_orders_of_magnitude(
    scene: dict,
    name: str,
    expected_naive: float,
    tier_name: str,
) -> None:
    """C1 to C3. The error is so large that the order is what to assert."""
    from dzialki.enrich.geometry import euclidean_in_degrees, within_tolerance

    row = baseline(scene, name)
    naive = euclidean_in_degrees(tuple(row["point_a_4326"]), tuple(row["point_b_4326"]))
    expected_m = row["separation_m"]

    assert round(naive, 12) == expected_naive
    assert naive < 1.0
    assert abs(naive - expected_m) > expected_m - 1.0
    assert 6.5e4 < expected_m / naive < 1.2e5
    assert within_tolerance(naive, expected_m, tier_name=tier_name) is False


def test_the_flat_degree_constant_fails_east_west_and_passes_north_south(
    scene: dict,
) -> None:
    """C4, and the whole point of the control.

    "A degree is 111 320 metres" passes a north-south known-answer test at
    tier G. That is why the second known-answer pair must be east-west, and why
    nobody may "simplify" the two pairs into one.
    """
    from dzialki.enrich.geometry import flat_degree_distance_m, within_tolerance

    flat = scene["degree_controls"]["flat_metres_per_degree"]
    assert flat == 111_320.0

    north_south = baseline(scene, "C_short_north_south")
    east_west = baseline(scene, "C_short_east_west")

    good = flat_degree_distance_m(
        tuple(north_south["point_a_4326"]),
        tuple(north_south["point_b_4326"]),
        metres_per_degree=flat,
    )
    bad = flat_degree_distance_m(
        tuple(east_west["point_a_4326"]),
        tuple(east_west["point_b_4326"]),
        metres_per_degree=flat,
    )

    assert round(good, 3) == 300.091
    assert round(bad, 3) == 497.429

    # The trap: the naive constant passes the north-south check.
    assert within_tolerance(good, 300.0, tier_name="G") is True
    # And fails the east-west one by 197 times the budget.
    assert abs(bad - 300.0) > 180.0
    assert within_tolerance(bad, 300.0, tier_name="G") is False


def test_the_flat_degree_constant_fails_the_ring_tier_east_west(scene: dict) -> None:
    """C5. The same 1.66 : 1 error, now against the 0.1 % ring budget."""
    from dzialki.enrich.geometry import flat_degree_distance_m, within_tolerance

    flat = scene["degree_controls"]["flat_metres_per_degree"]
    north_south = baseline(scene, "C_ring_north_south")
    east_west = baseline(scene, "C_ring_east_west")

    good = flat_degree_distance_m(
        tuple(north_south["point_a_4326"]),
        tuple(north_south["point_b_4326"]),
        metres_per_degree=flat,
    )
    bad = flat_degree_distance_m(
        tuple(east_west["point_a_4326"]),
        tuple(east_west["point_b_4326"]),
        metres_per_degree=flat,
    )

    assert round(good, 3) == 25_007.102
    assert round(bad, 3) == 41_452.091
    assert within_tolerance(good, 25_000.0, tier_name="R") is True
    assert within_tolerance(bad, 25_000.0, tier_name="R") is False
    assert round(bad / 25_000.0, 3) == 1.658


def test_the_recorded_metres_per_degree_differ_between_the_two_axes(
    scene: dict,
) -> None:
    """The reason a single constant cannot serve both orientations."""
    controls = scene["degree_controls"]
    assert controls["metres_per_degree_latitude"] == 111_295.65
    assert controls["metres_per_degree_longitude"] == 67_136.68
    assert controls["ellipsoid"] == "WGS84"


# --- metamorphic properties of the kernel ---------------------------------


def test_distance_is_symmetric(scene: dict) -> None:
    from dzialki.enrich.geometry import distance_m

    parcel = rect(scene, "parcels", "P1")
    building = rect(scene, "buildings", "B1")
    assert distance_m(parcel, building) == distance_m(building, parcel)


def test_distance_is_invariant_under_a_common_translation(scene: dict) -> None:
    from dzialki.enrich.geometry import distance_m, translate

    parcel = rect(scene, "parcels", "P1")
    building = rect(scene, "buildings", "B1")
    moved = distance_m(
        translate(parcel, 1_234.0, -567.0), translate(building, 1_234.0, -567.0)
    )
    assert abs(moved - distance_m(parcel, building)) < 0.001


def test_distance_satisfies_the_triangle_inequality(scene: dict) -> None:
    """On points, not on rectangles.

    Rectangle-to-rectangle distance is a distance between *sets*, and that is not
    a metric: three overlapping strips break the inequality without any bug. The
    kernel is asserted where the property actually holds.
    """
    from dzialki.enrich.geometry import PLANAR_SRID, Rectangle, centroid, distance_m

    def point(name: str) -> Rectangle:
        east, north = centroid(rect(scene, "parcels", name))
        return Rectangle(east, east, north, north, srid=PLANAR_SRID)

    names = ("P1", "P2", "P3", "P5", "P7", "P9")
    for first in names:
        for second in names:
            for third in names:
                a, b, c = point(first), point(second), point(third)
                assert distance_m(a, c) <= distance_m(a, b) + distance_m(b, c) + 1e-9


def test_area_scales_quadratically_under_uniform_scaling(scene: dict) -> None:
    from dzialki.enrich.geometry import area_m2, scale

    parcel = rect(scene, "parcels", "P1")
    assert area_m2(parcel) == 3_600.0
    assert math.isclose(area_m2(scale(parcel, 3.0)), 9 * 3_600.0, rel_tol=1e-12)
