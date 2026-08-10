"""Build tests/fixtures/synthetic/ring_membership.json. Deterministic.

The fixture discriminates between the three candidate ring rules — boundary
within 25 km, centroid within 25 km, seat within 25 km. D64 chose the first, and
that choice is invisible unless the fixture contains a gmina the three rules
disagree about. Two of the four sectors are exactly that.

Every vertex is a geodesic offset from the anchor, so each sector's distance from
the anchor is exact by construction rather than measured afterwards. Only the
WGS84 ellipsoid is needed: no PROJ grids, no download.
"""

from __future__ import annotations

import json
import pathlib

from pyproj import Geod

# Matches PostGIS geography ST_DWithin, which uses the spheroid by default.
GEOD = Geod(ellps="WGS84")

# A round graticule crossing in the reserved 98 namespace. Not an address, and
# nowhere near either real anchor.
ANCHOR_LON, ANCHOR_LAT = 19.0, 53.0
ANCHOR_KEY = "T"
RADIUS_M = 25_000

# teryt, name, azimuth from, azimuth to, inner radius, outer radius, step
SECTORS = [
    ("9801011", "Straddler", 0.0, 30.0, 24_000, 40_000, 1.0),
    ("9801021", "JustInside", 60.0, 90.0, 24_900, 26_000, 0.25),
    ("9801031", "JustOutside", 120.0, 150.0, 25_100, 30_000, 0.25),
    ("9801041", "FullyInside", 180.0, 210.0, 1_000, 10_000, 1.0),
]


def _arc(azimuth_from: float, azimuth_to: float, radius: float, step: float):
    points = []
    azimuth = azimuth_from
    while azimuth < azimuth_to:
        lon, lat, _back = GEOD.fwd(ANCHOR_LON, ANCHOR_LAT, azimuth, radius)
        points.append((lon, lat))
        azimuth += step
    lon, lat, _back = GEOD.fwd(ANCHOR_LON, ANCHOR_LAT, azimuth_to, radius)
    points.append((lon, lat))
    return points


def sector_wkt(
    azimuth_from: float,
    azimuth_to: float,
    r_inner: float,
    r_outer: float,
    step: float,
) -> str:
    """An annular sector as a closed WGS84 ring.

    Sampled finely enough that the chord sag between consecutive vertices stays
    under 0.1 m at these radii, so the nearest-boundary distance the test asserts
    is the radius and not a chord shortcut.
    """
    outer = _arc(azimuth_from, azimuth_to, r_outer, step)
    inner = list(reversed(_arc(azimuth_from, azimuth_to, r_inner, step)))
    ring = outer + inner + [outer[0]]
    body = ", ".join(f"{lon:.9f} {lat:.9f}" for lon, lat in ring)
    return f"MULTIPOLYGON((({body})))"


def area_centroid_radius(r_inner: float, r_outer: float) -> float:
    """Radius of an annular sector's area centroid.

    This is why `JustInside` sits at 25.45 km while its boundary reaches 24.9 km:
    a member under D64 and a non-member under the centroid rule.
    """
    return 2 / 3 * (r_outer**3 - r_inner**3) / (r_outer**2 - r_inner**2)


def _hull_wkt(children: list[str]) -> str:
    """A crude convex hull: the bounding box of every child vertex.

    The parents exist so the hierarchy foreign keys resolve. Area additivity is
    asserted against `admin_hierarchy.json`, not this fixture, so a box is
    honest here and a real hull would suggest a precision it does not have.
    """
    lons: list[float] = []
    lats: list[float] = []
    for wkt in children:
        body = wkt[wkt.index("(((") + 3 : wkt.index(")))")]
        for pair in body.split(", "):
            lon, lat = pair.split()
            lons.append(float(lon))
            lats.append(float(lat))
    west, east = min(lons), max(lons)
    south, north = min(lats), max(lats)
    return (
        f"MULTIPOLYGON((({west:.9f} {south:.9f}, {east:.9f} {south:.9f}, "
        f"{east:.9f} {north:.9f}, {west:.9f} {north:.9f}, "
        f"{west:.9f} {south:.9f})))"
    )


def build() -> dict:
    units = []
    geometries = []
    nearest: dict[str, float] = {}
    centroid: dict[str, float] = {}

    for teryt, name, az_from, az_to, r_in, r_out, step in SECTORS:
        wkt = sector_wkt(az_from, az_to, r_in, r_out, step)
        geometries.append(wkt)
        units.append(
            {
                "teryt": teryt,
                "level": "gmina",
                "name": name,
                "parent_teryt": "9801",
                "wkt": wkt,
            }
        )
        # Exact by construction: the inner arc sits at r_in from the anchor.
        nearest[teryt] = round(float(r_in), 2)
        centroid[teryt] = round(area_centroid_radius(r_in, r_out), 2)

    powiat_wkt = _hull_wkt(geometries)
    units[:0] = [
        {
            "teryt": "98",
            "level": "voivodeship",
            "name": "Pierscieniowskie",
            "parent_teryt": None,
            "wkt": powiat_wkt,
        },
        {
            "teryt": "9801",
            "level": "powiat",
            "name": "pierscieniowski",
            "parent_teryt": "98",
            "wkt": powiat_wkt,
        },
    ]

    in_ring = sorted(t for t, r in nearest.items() if r <= RADIUS_M)
    under_centroid = sorted(t for t, r in centroid.items() if r <= RADIUS_M)

    return {
        "as_of": "2026-08-10",
        "source_name": "synthetic",
        "anchor": {
            "key": ANCHOR_KEY,
            "label": "SYNTHETIC_RING_ANCHOR",
            "lon": ANCHOR_LON,
            "lat": ANCHOR_LAT,
        },
        "units": units,
        "expected": {
            "radius_m": RADIUS_M,
            "in_ring_T": in_ring,
            "not_in_ring_T": sorted(set(nearest) - set(in_ring)),
            "would_be_in_ring_under_centroid_rule": under_centroid,
            "measured_nearest_m": nearest,
            "measured_centroid_m": centroid,
        },
    }


if __name__ == "__main__":
    target = (
        pathlib.Path(__file__).resolve().parents[2]
        / "tests"
        / "fixtures"
        / "synthetic"
        / "ring_membership.json"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(f"wrote {target}")
