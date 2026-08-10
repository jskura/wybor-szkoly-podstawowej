"""The developed-neighbour signal.

> Absence of observed buildings in a poorly-mapped county is absence of *data*,
> not absence of *neighbours*.

So the signal consults the coverage record before it consults geometry. Where the
record says the gmina publishes no building layer, the answer is `unknown` and
the reason names it. Where the record says a layer exists and our read of it
failed, the answer is also `unknown` and the reason names *that*. The two are
different facts and they call for different operator actions, so they never share
a code.

A building standing on the subject parcel is not a neighbour. The condition is
about *neighbouring* development, and a naive "any building inside the radius"
implementation reports the subject's own outbuilding at zero metres and answers
`present` on a parcel with nothing around it.

Distance is measured from the parcel **boundary**, never from its centroid. On a
long thin parcel the two differ by hundreds of metres, and the centroid
measurement answers a question nobody asked.
"""

from __future__ import annotations

import dataclasses
import datetime
from collections.abc import Sequence

from ..coverage import CoverageRecord
from ..geometry import Rectangle, distance_m, overlap_m2

# Register data first, OSM second. The order decides whether the composite caps
# the verdict, so it is declared rather than left to whichever row came back
# first.
SOURCE_PREFERENCE: tuple[str, ...] = ("egib", "osm")

NEIGHBOUR_VALUES: tuple[str, ...] = ("present", "absent", "unknown")


@dataclasses.dataclass(frozen=True)
class Building:
    """One observed building, with the source that observed it and when."""

    identifier: str
    rectangle: Rectangle
    source: str
    as_of: datetime.date


@dataclasses.dataclass(frozen=True)
class NeighbourSignal:
    """What we found, how far away, from which source, and how many.

    Rule 7: the verdict ships with `n` and the radius, never as a bare word.
    """

    value: str
    reason_code: str | None
    source: str | None
    count: int
    radius_m: int
    nearest_distance_m: float | None
    nearest_building: str | None
    as_of: datetime.date | None


def buildings_within(
    parcel: Rectangle, buildings: Sequence[Building], *, radius_m: int
) -> tuple[Building, ...]:
    """Every building inside the radius that does not stand on the parcel.

    Sorted by distance, then by identifier, so the order is total and the
    nearest neighbour is the same on every run.
    """
    found = [
        (distance_m(parcel, building.rectangle), building.identifier, building)
        for building in buildings
        if overlap_m2(parcel, building.rectangle) == 0.0
    ]
    inside = sorted(row for row in found if row[0] <= radius_m)
    return tuple(building for _distance, _identifier, building in inside)


def nearest_neighbour(
    parcel: Rectangle, buildings: Sequence[Building]
) -> tuple[float, Building] | None:
    """The closest building not standing on the parcel, at any distance."""
    candidates = [
        (distance_m(parcel, building.rectangle), building.identifier, building)
        for building in buildings
        if overlap_m2(parcel, building.rectangle) == 0.0
    ]
    if not candidates:
        return None
    distance, _identifier, building = min(candidates)
    return distance, building


def preferred_source(buildings: Sequence[Building]) -> str | None:
    for source in SOURCE_PREFERENCE:
        if any(building.source == source for building in buildings):
            return source
    return None


def neighbour_signal(
    parcel: Rectangle,
    buildings: Sequence[Building] | None,
    coverage_record: CoverageRecord | None,
    *,
    radius_m: int,
) -> NeighbourSignal:
    """The developed-neighbour signal for one parcel.

    ``buildings`` of ``None`` means the query failed. An empty sequence means the
    query succeeded and returned nothing, which is a different fact.
    """
    if coverage_record is None or not coverage_record.has_coverage:
        return NeighbourSignal(
            value="unknown",
            reason_code="building_data_unavailable",
            source=None,
            count=0,
            radius_m=radius_m,
            nearest_distance_m=None,
            nearest_building=None,
            as_of=None,
        )

    if buildings is None:
        return NeighbourSignal(
            value="unknown",
            reason_code="building_query_failed",
            source=None,
            count=0,
            radius_m=radius_m,
            nearest_distance_m=None,
            nearest_building=None,
            as_of=None,
        )

    nearest = nearest_neighbour(parcel, buildings)
    inside = buildings_within(parcel, buildings, radius_m=radius_m)

    return NeighbourSignal(
        value="present" if inside else "absent",
        reason_code=None if inside else "no_neighbour_within_radius",
        source=preferred_source(inside),
        count=len(inside),
        radius_m=radius_m,
        nearest_distance_m=round(nearest[0], 3) if nearest else None,
        nearest_building=nearest[1].identifier if nearest else None,
        as_of=max((building.as_of for building in inside), default=None),
    )
