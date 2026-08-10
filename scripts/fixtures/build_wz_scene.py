"""Build the synthetic WZ scene. Deterministic, offline, no network.

The scene is the fixture for stage S14. It carries the parcels, the buildings,
the roads and the protected areas that make every distance in
`docs/tdd/plans/05-feasibility-test-plan.md` §1 an exact decimal.

**Nothing in this file refers to real land.** Every coordinate is a round number
on a fabricated grid origin. Every TERYT code starts with `99`, a voivodeship
code the TERC register does not hold and never will, so a synthetic identifier
cannot collide with a real gmina.

Every shape is an axis-aligned rectangle, so a reader can re-derive any expected
value with a pocket calculator. A rotated or curved fixture would make the
expected values opaque, and an opaque expected value is not ground truth.

The script writes two files. `wz_scene.yml` holds the declaration and the values
computed from it. `wz_scene.wkt` holds the generated geometry as a golden file.
`test_scene_generator_reproduces_the_golden_files` regenerates both and asserts
byte equality, so the generator and the code under test cannot drift into one
shared bug.

The degree controls at the end are separate. They live in WGS84, they are placed
by geodesic offset from a fabricated graticule crossing, and they exist to prove
that a distance computed in degrees fails the metre tolerance.
"""

from __future__ import annotations

import math
import pathlib

import yaml
from pyproj import Geod

# --- frame ----------------------------------------------------------------

CRS = "EPSG:2180"
# Traditional GIS order, which PostGIS and GDAL use. EPSG's own axis order for
# 2180 is northing first, and the fixture deliberately does not follow it.
ORDINATE_ORDER = "easting_first"

# The scene ranges do not overlap. That is what makes a transposed easting and
# northing detectable per coordinate: the national 2180 ranges overlap over most
# of their length and would not catch it.
SCENE_EASTING = (599_000.0, 614_000.0)
SCENE_NORTHING = (495_000.0, 505_000.0)

BUILD_DATE = "2026-08-08"

# The fixture's working parameters. They are NOT the shipped ones: the shipped
# values live in `config/params.yml` and the 20-parcel labelled set arbitrates
# them (D102, D103). These values are chosen so §1.5's arithmetic stays exact.
# `test_scene_parameters_differ_from_the_shipped_ones` records the difference.
WORKING_PARAMETERS = {
    "good_neighbour_radius_m": 100,
    "coverage_probe_radius_m": 2000,
    "coverage_probe_min_buildings": 5,
    "coverage_max_age_days": 90,
}

# --- administrative units -------------------------------------------------

# teryt, name, easting extent, coverage source, has_coverage, checked_at
UNITS = [
    ("999901", "SYNTH-A", 599_000.0, 604_500.0, "egib", True, "2026-08-01"),
    ("999903", "SYNTH-C", 604_500.0, 607_000.0, "egib", True, "2026-08-01"),
    ("999904", "SYNTH-D", 607_000.0, 609_000.0, "egib", True, "2025-01-01"),
    ("999902", "SYNTH-B", 609_000.0, 612_000.0, "none", False, "2026-08-01"),
    ("999905", "SYNTH-E", 612_000.0, 614_000.0, "osm", True, "2026-08-01"),
]

# --- roads and protected areas --------------------------------------------

# id, rectangle, register class, osm highway class, ownership confirmed
ROADS = [
    ("R1", (599_000.0, 614_000.0, 499_990.0, 500_000.0), "dr", "residential", False),
    ("R2", (603_800.0, 604_300.0, 500_165.0, 500_175.0), "dr", None, False),
    ("R3", (601_000.0, 602_000.0, 500_060.0, 500_070.0), "dr", "residential", False),
]

PROTECTED_AREAS = [
    ("SYNTH-PARK", (605_030.0, 606_000.0, 499_000.0, 501_000.0), "landscape_park"),
    (
        "SYNTH-OTULINA",
        (604_800.0, 605_030.0, 499_000.0, 501_000.0),
        "landscape_park_buffer",
    ),
]

# --- buildings ------------------------------------------------------------

# All buildings are 10 m squares. `sits_on` names the parcel that holds it.
BUILDINGS = [
    ("B1", (600_090.0, 600_100.0, 500_020.0, 500_030.0), "egib", "P1N"),
    ("B2", (600_760.0, 600_770.0, 500_020.0, 500_030.0), "egib", "P2N"),
    ("B2own", (600_420.0, 600_430.0, 500_020.0, 500_030.0), "egib", "P2"),
    ("B5", (605_100.0, 605_110.0, 500_020.0, 500_030.0), "egib", "P5N"),
    ("B6", (602_930.0, 602_940.0, 500_000.0, 500_010.0), "egib", "P6N"),
    ("B7", (604_020.0, 604_030.0, 500_105.0, 500_115.0), "egib", "P7N"),
    ("B9", (607_590.0, 607_600.0, 500_020.0, 500_030.0), "egib", "P9N"),
    ("B11", (612_590.0, 612_600.0, 500_020.0, 500_030.0), "osm", "P11N"),
]

# The C-cluster is a hamlet. It sits more than 500 m from every subject parcel
# and less than 2 km from P1, P2 and P3. That separation is the whole point: it
# lets the fixture prove that coverage and good neighbourhood are two different
# questions. A cluster inside the good-neighbour radius would flip both at once.
for _index, _easting in enumerate(
    (601_000.0, 601_050.0, 601_100.0, 601_150.0, 601_200.0, 601_250.0), start=1
):
    BUILDINGS.append(
        (
            f"C{_index}",
            (_easting, _easting + 10.0, 500_500.0, 500_510.0),
            "egib",
            None,
        )
    )

# --- parcels --------------------------------------------------------------

# id, parcel identifier, rectangle, register land-use class, role
PARCELS = [
    ("P1", "999901_9.9001.1", (600_000.0, 600_060.0, 500_000.0, 500_060.0), "B"),
    ("P1N", "999901_9.9001.2", (600_090.0, 600_150.0, 500_000.0, 500_060.0), "B"),
    ("P2", "999901_9.9001.3", (600_400.0, 600_460.0, 500_000.0, 500_060.0), "B"),
    ("P2N", "999901_9.9001.4", (600_760.0, 600_820.0, 500_000.0, 500_060.0), "B"),
    ("P3", "999901_9.9001.5", (602_000.0, 602_060.0, 500_000.0, 500_060.0), "R"),
    ("P6", "999901_9.9001.6", (603_000.0, 603_350.0, 500_000.0, 500_010.0), "R"),
    ("P6N", "999901_9.9001.7", (602_880.0, 602_940.0, 500_000.0, 500_010.0), "B"),
    ("P7", "999901_9.9001.8", (604_000.0, 604_060.0, 500_000.0, 500_060.0), "B"),
    ("P7N", "999901_9.9001.9", (604_000.0, 604_060.0, 500_105.0, 500_165.0), "B"),
    ("P8", "999901_9.9001.10", (604_460.0, 604_520.0, 500_200.0, 500_260.0), "R"),
    ("P10", "999901_9.9001.11", (601_000.0, 601_060.0, 503_000.0, 503_060.0), "B"),
    # P12 straddles the SYNTH-A / SYNTH-C boundary in equal halves. The test
    # plan asks for it: P8 stays at 40/20 and a separate parcel exercises the
    # D123 tie, because a rule with no test is a rule that drifts.
    ("P12", "999901_9.9001.12", (604_470.0, 604_530.0, 500_200.0, 500_260.0), "R"),
    ("P4", "999902_9.9002.1", (610_000.0, 610_060.0, 500_000.0, 500_060.0), "R"),
    ("P5", "999903_9.9003.1", (605_000.0, 605_060.0, 500_000.0, 500_060.0), "B"),
    ("P5N", "999903_9.9003.2", (605_100.0, 605_160.0, 500_000.0, 500_060.0), "B"),
    ("P9", "999904_9.9004.1", (607_500.0, 607_560.0, 500_000.0, 500_060.0), "B"),
    ("P9N", "999904_9.9004.2", (607_590.0, 607_650.0, 500_000.0, 500_060.0), "B"),
    ("P11", "999905_9.9005.1", (612_500.0, 612_560.0, 500_000.0, 500_060.0), "B"),
    ("P11N", "999905_9.9005.2", (612_590.0, 612_650.0, 500_000.0, 500_060.0), "B"),
]

# The parcels the assertions are about. The neighbour parcels exist to hold the
# buildings and are not themselves subjects.
SUBJECTS = (
    "P1",
    "P2",
    "P3",
    "P4",
    "P5",
    "P6",
    "P7",
    "P8",
    "P9",
    "P10",
    "P11",
    "P12",
)

# --- the degree controls --------------------------------------------------

# A round graticule crossing in the reserved 98 namespace. Not an address, and
# nowhere near either real anchor. The same convention `build_ring_fixture.py`
# uses, and for the same reason.
CONTROL_LON, CONTROL_LAT = 19.0, 53.0
GEOD = Geod(ellps="WGS84")

# The bug that actually ships is "a degree is 111 320 metres". It is right to
# 0.01 % north-south and badly wrong east-west, so it passes a north-south
# known-answer test. That is why the controls carry both orientations.
FLAT_METRES_PER_DEGREE = 111_320.0


def rounded(value: float, places: int = 3) -> float:
    """Round for storage. A stored float with 15 digits invites a false tolerance."""
    return round(value + 0.0, places)


def interval_gap(low_a: float, high_a: float, low_b: float, high_b: float) -> float:
    """The gap between two intervals on one axis. Zero when they overlap."""
    if high_a < low_b:
        return low_b - high_a
    if high_b < low_a:
        return low_a - high_b
    return 0.0


def rectangle_distance_m(a: tuple, b: tuple) -> float:
    """The shortest distance between two axis-aligned rectangles, in metres."""
    east_gap = interval_gap(a[0], a[1], b[0], b[1])
    north_gap = interval_gap(a[2], a[3], b[2], b[3])
    return math.hypot(east_gap, north_gap)


def rectangle_centroid(rectangle: tuple) -> tuple[float, float]:
    return ((rectangle[0] + rectangle[1]) / 2, (rectangle[2] + rectangle[3]) / 2)


def centroid_distance_m(parcel: tuple, other: tuple) -> float:
    """The distance a centroid implementation would report. The trap P6 sets."""
    east, north = rectangle_centroid(parcel)
    return rectangle_distance_m((east, east, north, north), other)


def overlap_area_m2(a: tuple, b: tuple) -> float:
    east = max(0.0, min(a[1], b[1]) - max(a[0], b[0]))
    north = max(0.0, min(a[3], b[3]) - max(a[2], b[2]))
    return east * north


def rectangle_area_m2(rectangle: tuple) -> float:
    return (rectangle[1] - rectangle[0]) * (rectangle[3] - rectangle[2])


def shared_edge_length_m(a: tuple, b: tuple) -> float:
    """The length two rectangles share along a touching edge.

    A single touching vertex gives 0.0, which is what separates access from
    corner contact.
    """
    if rectangle_distance_m(a, b) > 0.0:
        return 0.0
    east = min(a[1], b[1]) - max(a[0], b[0])
    north = min(a[3], b[3]) - max(a[2], b[2])
    if east > 0.0 and north == 0.0:
        return east
    if north > 0.0 and east == 0.0:
        return north
    if east == 0.0 and north == 0.0:
        return 0.0
    # They overlap in both axes, so the shared boundary is not a single edge.
    return 0.0


def rectangle_wkt(rectangle: tuple) -> str:
    """A closed ring, easting first, in the order a reader would draw it."""
    e_min, e_max, n_min, n_max = rectangle
    corners = (
        (e_min, n_min),
        (e_max, n_min),
        (e_max, n_max),
        (e_min, n_max),
        (e_min, n_min),
    )
    body = ", ".join(f"{east:.3f} {north:.3f}" for east, north in corners)
    return f"POLYGON(({body}))"


def unit_rectangle(easting_from: float, easting_to: float) -> tuple:
    """A gmina strip, spanning the whole scene from south to north."""
    return (easting_from, easting_to, SCENE_NORTHING[0], SCENE_NORTHING[1])


def unit_of(rectangle: tuple) -> str:
    """The TERYT of the gmina holding the greater part of the rectangle.

    Ties go to the lowest TERYT (D123). Arbitrary, but total, so the answer is
    the same on every run.
    """
    shares = []
    for teryt, _name, easting_from, easting_to, *_rest in UNITS:
        area = overlap_area_m2(rectangle, unit_rectangle(easting_from, easting_to))
        shares.append((area, teryt))
    best = max(area for area, _teryt in shares)
    return min(teryt for area, teryt in shares if area == best)


def straddle_of(rectangle: tuple) -> list[dict]:
    """Every gmina the rectangle touches, with the area in each."""
    found = []
    for teryt, _name, easting_from, easting_to, *_rest in UNITS:
        area = overlap_area_m2(rectangle, unit_rectangle(easting_from, easting_to))
        if area > 0.0:
            found.append({"teryt": teryt, "area_m2": rounded(area, 2)})
    return sorted(found, key=lambda row: row["teryt"])


def shape_table() -> list[tuple[str, tuple]]:
    """Every shape in the scene, in the order the golden file lists them."""
    shapes: list[tuple[str, tuple]] = []
    for teryt, name, easting_from, easting_to, *_rest in UNITS:
        shapes.append((f"{name}:{teryt}", unit_rectangle(easting_from, easting_to)))
    for identifier, rectangle, *_rest in ROADS:
        shapes.append((identifier, rectangle))
    for identifier, rectangle, _kind in PROTECTED_AREAS:
        shapes.append((identifier, rectangle))
    for identifier, rectangle, *_rest in sorted(BUILDINGS):
        shapes.append((identifier, rectangle))
    for identifier, _parcel_id, rectangle, _land_use in PARCELS:
        shapes.append((identifier, rectangle))
    return shapes


def golden_wkt() -> str:
    lines = [
        f"{identifier}\t{rectangle_wkt(rect)}" for identifier, rect in shape_table()
    ]
    return "\n".join(lines) + "\n"


def _building_rows() -> dict[str, tuple]:
    return {identifier: rectangle for identifier, rectangle, *_rest in BUILDINGS}


def _building_owner() -> dict[str, str | None]:
    return {identifier: sits_on for identifier, _rect, _source, sits_on in BUILDINGS}


def _building_source() -> dict[str, str]:
    return {identifier: source for identifier, _rect, source, _sits in BUILDINGS}


def _parcel_rows() -> dict[str, tuple]:
    return {identifier: rectangle for identifier, _pid, rectangle, _use in PARCELS}


def neighbour_distances(subject: str) -> list[dict]:
    """Every building that is not on the subject parcel, with its distance.

    Sorted by distance, then by identifier, so the order is total and the file
    is reproducible.
    """
    parcels = _parcel_rows()
    buildings = _building_rows()
    owners = _building_owner()
    sources = _building_source()
    parcel = parcels[subject]

    rows = []
    for identifier, rectangle in buildings.items():
        if owners[identifier] == subject:
            continue
        rows.append(
            {
                "building": identifier,
                "source": sources[identifier],
                "distance_m": rounded(rectangle_distance_m(parcel, rectangle)),
                "centroid_distance_m": rounded(centroid_distance_m(parcel, rectangle)),
            }
        )
    return sorted(rows, key=lambda row: (row["distance_m"], row["building"]))


def own_buildings(subject: str) -> list[str]:
    return sorted(
        identifier
        for identifier, _rect, _source, sits_on in BUILDINGS
        if sits_on == subject
    )


def road_contacts(subject: str) -> list[dict]:
    """Every road the parcel touches, and how it touches it."""
    parcel = _parcel_rows()[subject]
    rows = []
    for identifier, rectangle, register_class, highway, confirmed in ROADS:
        gap = rectangle_distance_m(parcel, rectangle)
        if gap > 0.0:
            continue
        edge = shared_edge_length_m(parcel, rectangle)
        rows.append(
            {
                "road": identifier,
                "register_class": register_class,
                "osm_highway_class": highway,
                "ownership_confirmed": confirmed,
                "shared_edge_m": rounded(edge),
                "contact": "shared_edge" if edge > 0.0 else "single_vertex",
            }
        )
    return sorted(rows, key=lambda row: row["road"])


def protection_overlaps(subject: str) -> list[dict]:
    parcel = _parcel_rows()[subject]
    area = rectangle_area_m2(parcel)
    rows = []
    for identifier, rectangle, kind in PROTECTED_AREAS:
        overlap = overlap_area_m2(parcel, rectangle)
        if overlap <= 0.0:
            continue
        rows.append(
            {
                "area": identifier,
                "kind": kind,
                "overlap_m2": rounded(overlap, 2),
                "overlap_fraction": rounded(overlap / area, 4),
            }
        )
    return sorted(rows, key=lambda row: row["area"])


def subject_row(subject: str) -> dict:
    parcels = _parcel_rows()
    parcel = parcels[subject]
    identifier = next(pid for name, pid, _r, _u in PARCELS if name == subject)
    land_use = next(use for name, _pid, _r, use in PARCELS if name == subject)

    distances = neighbour_distances(subject)
    radius = WORKING_PARAMETERS["good_neighbour_radius_m"]
    probe = WORKING_PARAMETERS["coverage_probe_radius_m"]

    within_radius = [row for row in distances if row["distance_m"] <= radius]
    within_probe = [row for row in distances if row["distance_m"] <= probe]
    # A building on the subject parcel counts for neither. It is not a
    # neighbour, and the test plan's control counts exclude it as well.
    own = own_buildings(subject)

    return {
        "id": subject,
        "parcel_identifier": identifier,
        "rectangle": list(parcel),
        "area_m2": rounded(rectangle_area_m2(parcel), 2),
        "south_west_corner": [rounded(parcel[0]), rounded(parcel[2])],
        "land_use_class": land_use,
        "teryt_gmina": unit_of(parcel),
        "straddles": straddle_of(parcel),
        "own_buildings": own,
        "nearest_neighbour_building": distances[0]["building"] if distances else None,
        "nearest_neighbour_distance_m": (
            distances[0]["distance_m"] if distances else None
        ),
        "nearest_neighbour_centroid_distance_m": (
            distances[0]["centroid_distance_m"] if distances else None
        ),
        "buildings_within_good_neighbour_radius": len(within_radius),
        "buildings_within_probe_radius": len(within_probe),
        "neighbour_sources_within_radius": sorted(
            {row["source"] for row in within_radius}
        ),
        "roads": road_contacts(subject),
        "protection": protection_overlaps(subject),
    }


def degree_controls() -> dict:
    """Two 300 m baselines and one 25 km baseline, placed by geodesic offset.

    The points are generated, never recalled. The metres per degree below are
    read off the same generated pair, so the control's expected magnitudes stay
    consistent with the points the test actually uses.
    """
    controls = []
    for name, azimuth, length, orientation in (
        ("C_short_north_south", 0.0, 300.0, "north_south"),
        ("C_short_east_west", 90.0, 300.0, "east_west"),
        ("C_ring_north_south", 0.0, 25_000.0, "north_south"),
        ("C_ring_east_west", 90.0, 25_000.0, "east_west"),
    ):
        lon, lat, _back = GEOD.fwd(CONTROL_LON, CONTROL_LAT, azimuth, length)
        point_b = (round(lon, 9), round(lat, 9))
        degrees = math.hypot(point_b[0] - CONTROL_LON, point_b[1] - CONTROL_LAT)
        controls.append(
            {
                "name": name,
                "orientation": orientation,
                "separation_m": rounded(length, 3),
                "separation_kind": "geodesic",
                "point_a_4326": [CONTROL_LON, CONTROL_LAT],
                "point_b_4326": [point_b[0], point_b[1]],
                # What a distance computed in degrees returns. Five orders of
                # magnitude short, and the reason the metre kernel refuses a
                # geographic input rather than returning a number.
                "naive_degree_distance": round(degrees, 12),
                # What "a degree is 111 320 metres" returns. Right to 0.01 %
                # north-south, and 66 % long east-west. This is the bug that
                # ships, because the north-south case passes a known-answer test.
                "flat_degree_distance_m": rounded(degrees * FLAT_METRES_PER_DEGREE, 3),
            }
        )

    one_degree_north = GEOD.inv(
        CONTROL_LON, CONTROL_LAT, CONTROL_LON, CONTROL_LAT + 1.0
    )[2]
    one_degree_east = GEOD.inv(
        CONTROL_LON, CONTROL_LAT, CONTROL_LON + 1.0, CONTROL_LAT
    )[2]

    return {
        "origin_4326": [CONTROL_LON, CONTROL_LAT],
        "ellipsoid": "WGS84",
        "metres_per_degree_latitude": rounded(one_degree_north, 2),
        "metres_per_degree_longitude": rounded(one_degree_east, 2),
        "flat_metres_per_degree": FLAT_METRES_PER_DEGREE,
        "baselines": controls,
    }


def build() -> dict:
    units = []
    for teryt, name, easting_from, easting_to, source, has, checked in UNITS:
        units.append(
            {
                "teryt": teryt,
                "name": name,
                "rectangle": list(unit_rectangle(easting_from, easting_to)),
                "coverage": {
                    "source": source,
                    "has_coverage": has,
                    "checked_at": checked,
                },
            }
        )

    return {
        "as_of": BUILD_DATE,
        "source_name": "synthetic",
        "crs": CRS,
        "ordinate_order": ORDINATE_ORDER,
        "scene_easting_range": list(SCENE_EASTING),
        "scene_northing_range": list(SCENE_NORTHING),
        "working_parameters": dict(WORKING_PARAMETERS),
        "units": units,
        "roads": [
            {
                "id": identifier,
                "rectangle": list(rectangle),
                "register_class": register_class,
                "osm_highway_class": highway,
                "ownership_confirmed": confirmed,
            }
            for identifier, rectangle, register_class, highway, confirmed in ROADS
        ],
        "protected_areas": [
            {"id": identifier, "rectangle": list(rectangle), "kind": kind}
            for identifier, rectangle, kind in PROTECTED_AREAS
        ],
        "buildings": [
            {
                "id": identifier,
                "rectangle": list(rectangle),
                "source": source,
                "sits_on": sits_on,
            }
            for identifier, rectangle, source, sits_on in BUILDINGS
        ],
        "parcels": [
            {
                "id": identifier,
                "parcel_identifier": parcel_id,
                "rectangle": list(rectangle),
                "land_use_class": land_use,
            }
            for identifier, parcel_id, rectangle, land_use in PARCELS
        ],
        "subjects": [subject_row(name) for name in SUBJECTS],
        "degree_controls": degree_controls(),
    }


def _target(name: str) -> pathlib.Path:
    return (
        pathlib.Path(__file__).resolve().parents[2]
        / "tests"
        / "fixtures"
        / "synthetic"
        / name
    )


def yaml_text() -> str:
    return yaml.safe_dump(build(), sort_keys=False, allow_unicode=True)


if __name__ == "__main__":
    for name, text in (("wz_scene.yml", yaml_text()), ("wz_scene.wkt", golden_wkt())):
        target = _target(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        print(f"wrote {target}")
