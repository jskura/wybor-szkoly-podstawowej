"""R14 — the synthetic scene, and the absolute checks a distance cannot make.

Swapping easting and northing reflects the plane about the line E = N, and a
reflection is an isometry. If the pipeline transposes **both** points, every
pairwise distance survives exactly, at every orientation and at every scale. A
consistently transposed pipeline therefore passes every distance assertion in
this suite.

Only an assertion about where a point *is* catches it. That is what this file
holds, and it is why the last test in it asserts the invariance on purpose.
"""

from __future__ import annotations

import pathlib
import sys

import pytest
import yaml

pytestmark = [pytest.mark.unit]

SCENE_YML = ("tests", "fixtures", "synthetic", "wz_scene.yml")
SCENE_WKT = ("tests", "fixtures", "synthetic", "wz_scene.wkt")
GENERATOR = ("scripts", "fixtures", "build_wz_scene.py")


@pytest.fixture
def scene(repo_root: pathlib.Path) -> dict:
    return yaml.safe_load(repo_root.joinpath(*SCENE_YML).read_text(encoding="utf-8"))


def rectangle_of(scene: dict, group: str, identifier: str) -> tuple[float, ...]:
    for row in scene[group]:
        if row["id"] == identifier:
            return tuple(row["rectangle"])
    raise LookupError(f"{identifier} is not in {group}")


def subject(scene: dict, identifier: str) -> dict:
    for row in scene["subjects"]:
        if row["id"] == identifier:
            return row
    raise LookupError(f"{identifier} is not a subject parcel")


# --- the generator is the only author of the fixture ----------------------


def test_scene_generator_reproduces_the_golden_files(repo_root: pathlib.Path) -> None:
    """Byte equality, so the generator and the code under test cannot drift.

    A fixture edited by hand records what someone believed, not what the
    declaration produces.
    """
    sys.path.insert(0, str(repo_root.joinpath(*GENERATOR[:-1])))
    try:
        import build_wz_scene
    finally:
        sys.path.pop(0)

    assert build_wz_scene.yaml_text() == repo_root.joinpath(*SCENE_YML).read_text(
        encoding="utf-8"
    )
    assert build_wz_scene.golden_wkt() == repo_root.joinpath(*SCENE_WKT).read_text(
        encoding="utf-8"
    )


def test_the_generator_runs_without_a_network(repo_root: pathlib.Path) -> None:
    """It needs the WGS84 ellipsoid and nothing else. No download, no grids."""
    source = repo_root.joinpath(*GENERATOR).read_text(encoding="utf-8")
    for forbidden in ("requests", "httpx", "urllib", "socket"):
        assert forbidden not in source


# --- absolute position ----------------------------------------------------


def test_parcel_corner_coordinates_match_the_scene_declaration(scene: dict) -> None:
    """P1's south-west corner, ordinate by ordinate.

    A transposed P1 gives (500 000, 600 000) and fails on both.
    """
    assert subject(scene, "P1")["south_west_corner"] == [600_000.0, 500_000.0]
    assert rectangle_of(scene, "parcels", "P1") == (
        600_000.0,
        600_060.0,
        500_000.0,
        500_060.0,
    )


def test_the_scene_easting_and_northing_ranges_do_not_overlap(scene: dict) -> None:
    """Why the ordinate check below is decisive, and the national extent is not.

    Poland's 2180 easting and northing ranges overlap over most of their length,
    so a range check against them passes a transposed pair. The scene's ranges
    are disjoint on purpose.
    """
    easting = scene["scene_easting_range"]
    northing = scene["scene_northing_range"]
    assert easting == [599_000.0, 614_000.0]
    assert northing == [495_000.0, 505_000.0]
    assert northing[1] < easting[0]


def test_ordinate_order_is_easting_first(scene: dict) -> None:
    e_min, e_max = scene["scene_easting_range"]
    n_min, n_max = scene["scene_northing_range"]
    assert scene["ordinate_order"] == "easting_first"

    checked = 0
    for group in ("units", "roads", "protected_areas", "buildings", "parcels"):
        for row in scene[group]:
            rectangle = row["rectangle"]
            named = row.get("id", row.get("teryt"))
            assert e_min <= rectangle[0] <= e_max, named
            assert e_min <= rectangle[1] <= e_max
            assert n_min <= rectangle[2] <= n_max
            assert n_min <= rectangle[3] <= n_max
            checked += 1
    assert checked == 43


def test_parcel_falls_inside_its_declared_gmina(scene: dict) -> None:
    """Containment fails on a transposition. Area and perimeter do not."""
    from dzialki.enrich.geometry import PLANAR_SRID, Rectangle, overlap_m2, transpose

    parcel = Rectangle(*rectangle_of(scene, "parcels", "P1"), srid=PLANAR_SRID)
    synth_a = Rectangle(
        *next(row["rectangle"] for row in scene["units"] if row["teryt"] == "999901"),
        srid=PLANAR_SRID,
    )
    assert overlap_m2(parcel, synth_a) == 3_600.0
    assert overlap_m2(transpose(parcel), synth_a) == 0.0


def test_distance_is_invariant_under_transposition_and_this_is_why_containment_is_required(
    scene: dict,
) -> None:
    """Deliberately perverse, and the most important test in the file.

    It records the hole in the obvious approach, so the next reader meets it
    before repeating the mistake. The two tests above cannot be deleted: this
    one proves no distance assertion can replace them.
    """
    from dzialki.enrich.geometry import PLANAR_SRID, Rectangle, distance_m, transpose

    parcel = Rectangle(*rectangle_of(scene, "parcels", "P1"), srid=PLANAR_SRID)
    building = Rectangle(*rectangle_of(scene, "buildings", "B1"), srid=PLANAR_SRID)

    assert distance_m(parcel, building) == 30.0
    assert distance_m(transpose(parcel), transpose(building)) == 30.0


# --- the scene is synthetic, and provably so ------------------------------


def test_every_synthetic_teryt_is_outside_the_real_register(scene: dict) -> None:
    """Voivodeship 99 does not exist in TERC and never will."""
    codes = [row["teryt"] for row in scene["units"]]
    assert codes == ["999901", "999903", "999904", "999902", "999905"]
    for row in scene["parcels"]:
        assert row["parcel_identifier"].startswith("99")


def test_scene_working_parameters_differ_from_the_shipped_ones(
    repo_root: pathlib.Path, scene: dict
) -> None:
    """The scene's numbers are not the shipped numbers, and the gap is recorded.

    D102 and D103 make the three values configuration, and the 20-parcel
    labelled set arbitrates them. That set does not exist, so the shipped values
    are provisional and the scene's arithmetic uses its own. Recording the
    difference here stops someone reading the scene as evidence for a shipped
    value.
    """
    from dzialki.config import load_params

    shipped = load_params(repo_root / "config" / "params.yml").feasibility
    working = scene["working_parameters"]

    assert working["good_neighbour_radius_m"] == shipped.good_neighbour_radius_m
    assert working["coverage_probe_radius_m"] == 2_000
    assert shipped.coverage_probe_radius_m == 500
    assert working["coverage_probe_min_buildings"] == 5
    assert shipped.coverage_probe_min_buildings == 3


def test_the_tie_parcel_is_resolved_by_the_lowest_teryt(scene: dict) -> None:
    """D123, exercised against a real 50/50 split rather than a rule on paper."""
    from dzialki.geo.straddle import GminaShare, owning_gmina

    shares = [
        GminaShare(teryt=row["teryt"], area_m2=row["area_m2"])
        for row in subject(scene, "P12")["straddles"]
    ]
    assert [(share.teryt, share.area_m2) for share in shares] == [
        ("999901", 1_800.0),
        ("999903", 1_800.0),
    ]
    ownership = owning_gmina(shares)
    assert ownership.teryt == "999901"
    assert ownership.was_tie is True


def test_the_majority_straddle_is_assigned_by_area_not_by_order(scene: dict) -> None:
    """P8's counterweight to the tie: 40 m in one gmina, 20 m in the other."""
    from dzialki.geo.straddle import GminaShare, owning_gmina

    shares = [
        GminaShare(teryt=row["teryt"], area_m2=row["area_m2"])
        for row in subject(scene, "P8")["straddles"]
    ]
    assert [(share.teryt, share.area_m2) for share in shares] == [
        ("999901", 2_400.0),
        ("999903", 1_200.0),
    ]
    ownership = owning_gmina(shares)
    assert ownership.teryt == "999901"
    assert ownership.was_tie is False
