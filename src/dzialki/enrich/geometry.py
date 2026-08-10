"""The metre kernel and the tolerance budget.

Compute in EPSG:2180, store in EPSG:4326. A rectangle carries its SRID, and a
geographic one is refused at construction rather than measured. A wrong number
that looks like a number is the failure this guard exists to prevent: a distance
of 0.0035 in degrees reads as a small number of metres and passes any check that
only asks whether the answer is positive.

Every shape in the WZ scene is an axis-aligned rectangle. Real parcels are not,
and this kernel is deliberately narrow: it is what the synthetic scene needs to
make its expected values exact decimals. The production geometry work happens in
PostGIS, which is where a real boundary belongs.

**The tolerance budget is a declared table, one row per scale.** V31 says "within
1 m". That holds under a kilometre and does not hold at ring scale: PUWG 1992 is
a transverse Mercator with a scale factor of 0.9993, and its length distortion
reaches roughly 0.7 m per kilometre across Poland. Declaring the tiers stops "1 m"
being redefined quietly later, and makes a comparison at an undeclared scale an
error instead of a guess.
"""

from __future__ import annotations

import dataclasses
import math

# The projected CRS every metre in this package is measured in.
PLANAR_SRID = 2180
# The CRS every geometry is stored in.
STORAGE_SRID = 4326


class GeographicSridError(ValueError):
    """Raised when a geographic coordinate reaches the metre kernel."""


class UndeclaredScaleError(ValueError):
    """Raised for a tolerance nobody declared, or a tier nobody named."""


@dataclasses.dataclass(frozen=True)
class Rectangle:
    """An axis-aligned rectangle in a projected CRS whose unit is the metre.

    Easting first, then northing. EPSG's own axis order for 2180 is northing
    first; this follows PostGIS and GDAL instead, and the scene's tests pin the
    choice so it cannot drift.
    """

    e_min: float
    e_max: float
    n_min: float
    n_max: float
    srid: int

    def __post_init__(self) -> None:
        if self.srid != PLANAR_SRID:
            raise GeographicSridError(
                f"SRID {self.srid} is not the metre CRS {PLANAR_SRID}. "
                "Reproject before measuring; a degree is not a metre."
            )
        if self.e_min > self.e_max or self.n_min > self.n_max:
            raise ValueError(
                f"the rectangle {self.e_min},{self.e_max},"
                f"{self.n_min},{self.n_max} has a negative side"
            )


@dataclasses.dataclass(frozen=True)
class Tier:
    """One row of the tolerance budget."""

    name: str
    kind: str
    budget: float
    covers_from_m: float
    covers_to_m: float


# S is the synthetic tier. The scene is constructed *in* 2180, so its distances
# are definitions rather than measurements, and the only permissible error is
# floating point. It is the one tier that does not narrow with scale, because
# no projection is involved in it at any distance.
#
# G is V31's contract under a kilometre. G_round_trip is a tighter tripwire on
# the storage round trip alone, where no projection distortion applies, so the
# 1 m budget cannot be eaten a centimetre at a time.
#
# R is the ring tier. At 25 km the projection alone costs 14 to 18 m, which is
# why the budget is relative and why it must be asserted against a geodesic and
# never against a second grid computation.
TOLERANCE_BUDGET: tuple[Tier, ...] = (
    Tier("S", "absolute_m", 0.001, 0.0, 50_000.0),
    Tier("G", "absolute_m", 1.0, 0.0, 1_000.0),
    Tier("G_round_trip", "absolute_m", 0.050, 0.0, 1_000.0),
    Tier("R", "relative_fraction", 0.001, 1_000.0, 50_000.0),
)


def tier(name: str) -> Tier:
    for row in TOLERANCE_BUDGET:
        if row.name == name:
            return row
    declared = ", ".join(row.name for row in TOLERANCE_BUDGET)
    raise UndeclaredScaleError(f"{name!r} is not a declared tier. Declared: {declared}")


def within_tolerance(observed: float, expected: float, *, tier_name: str) -> bool:
    """Compare at a declared scale, or refuse.

    The refusal is the point. A comparison at a scale the table does not cover
    would otherwise pick whichever tolerance happened to be nearest, and nobody
    would see it happen.
    """
    row = tier(tier_name)
    if not row.covers_from_m <= abs(expected) <= row.covers_to_m:
        raise UndeclaredScaleError(
            f"tier {row.name!r} covers {row.covers_from_m:.3f} m to "
            f"{row.covers_to_m:.3f} m and the baseline is {abs(expected):.3f} m"
        )
    allowed = row.budget if row.kind == "absolute_m" else row.budget * abs(expected)
    return abs(observed - expected) <= allowed


def _gap(low_a: float, high_a: float, low_b: float, high_b: float) -> float:
    """The gap between two intervals on one axis. Zero when they overlap."""
    if high_a < low_b:
        return low_b - high_a
    if high_b < low_a:
        return low_a - high_b
    return 0.0


def distance_m(a: Rectangle, b: Rectangle) -> float:
    """The shortest distance between two rectangles, from boundary to boundary.

    Zero when they touch or overlap. The WZ condition is about a neighbouring
    building's distance from the parcel *boundary*, so a centroid measurement
    answers a different question and gives a different verdict.
    """
    return math.hypot(
        _gap(a.e_min, a.e_max, b.e_min, b.e_max),
        _gap(a.n_min, a.n_max, b.n_min, b.n_max),
    )


def centroid(rectangle: Rectangle) -> tuple[float, float]:
    return (
        (rectangle.e_min + rectangle.e_max) / 2,
        (rectangle.n_min + rectangle.n_max) / 2,
    )


def centroid_distance_m(parcel: Rectangle, other: Rectangle) -> float:
    """What a centroid implementation would report. Kept so a test can compare."""
    east, north = centroid(parcel)
    return distance_m(Rectangle(east, east, north, north, srid=parcel.srid), other)


def area_m2(rectangle: Rectangle) -> float:
    return (rectangle.e_max - rectangle.e_min) * (rectangle.n_max - rectangle.n_min)


def overlap_m2(a: Rectangle, b: Rectangle) -> float:
    east = max(0.0, min(a.e_max, b.e_max) - max(a.e_min, b.e_min))
    north = max(0.0, min(a.n_max, b.n_max) - max(a.n_min, b.n_min))
    return east * north


def shared_edge_m(a: Rectangle, b: Rectangle) -> float:
    """The length of the boundary two touching rectangles share.

    A single shared vertex gives 0.0. That is the whole difference between road
    access and corner contact, so the two cases must not return the same number.
    """
    if distance_m(a, b) > 0.0:
        return 0.0
    east = min(a.e_max, b.e_max) - max(a.e_min, b.e_min)
    north = min(a.n_max, b.n_max) - max(a.n_min, b.n_min)
    if east > 0.0 and north == 0.0:
        return east
    if north > 0.0 and east == 0.0:
        return north
    return 0.0


def transpose(rectangle: Rectangle) -> Rectangle:
    """Swap easting and northing.

    Exists so a test can prove that no distance assertion catches a
    transposition. A reflection is an isometry, so every pairwise distance
    survives it exactly. Only an absolute position or a containment check finds
    the bug.
    """
    return Rectangle(
        rectangle.n_min,
        rectangle.n_max,
        rectangle.e_min,
        rectangle.e_max,
        srid=rectangle.srid,
    )


def translate(rectangle: Rectangle, east: float, north: float) -> Rectangle:
    return Rectangle(
        rectangle.e_min + east,
        rectangle.e_max + east,
        rectangle.n_min + north,
        rectangle.n_max + north,
        srid=rectangle.srid,
    )


def scale(rectangle: Rectangle, factor: float) -> Rectangle:
    east, north = centroid(rectangle)
    half_east = (rectangle.e_max - rectangle.e_min) * factor / 2
    half_north = (rectangle.n_max - rectangle.n_min) * factor / 2
    return Rectangle(
        east - half_east,
        east + half_east,
        north - half_north,
        north + half_north,
        srid=rectangle.srid,
    )


def euclidean_in_degrees(a: tuple[float, float], b: tuple[float, float]) -> float:
    """The distance a naive implementation returns from geographic coordinates.

    It is not metres and it is not a distance. It exists so a control test can
    show it failing the metre tolerance rather than arguing that it would.
    """
    return math.hypot(b[0] - a[0], b[1] - a[1])


def flat_degree_distance_m(
    a: tuple[float, float],
    b: tuple[float, float],
    *,
    metres_per_degree: float,
) -> float:
    """The bug that actually ships: one constant for both axes.

    It is right to a hundredth of a percent on a north-south baseline and badly
    wrong east-west, so it passes a north-south known-answer test. That is why
    the controls carry both orientations.
    """
    return euclidean_in_degrees(a, b) * metres_per_degree
