"""Road adjacency, and the D114 public-road proxy.

Free EGiB data carries no ownership. Nothing in the open sources states that a
road is public, so without a substitute `road_public_status` reads `unknown` for
every road in production and the one `likely` cell of the fifty-four never
occurs.

**D114 accepts a substitute: register class `dr` plus an OSM highway class.**
That pair is evidence, not proof. A private access road can carry both marks. So
FR-76 makes every `likely` verdict resting on it render its own disclaimer and a
marker naming the evidence, in wording that differs from the wording reserved for
confirmed ownership. The wording lives in `wording.py`; this module produces the
status the wording reads.

Adjacency means a **shared edge**. A single shared vertex is corner contact, not
access, and a parcel that touches a road at one point has no way onto it.

The WZ condition is a developed neighbour reachable from the **same** public
road. Both halves matter: a house across a field on a different road does not
satisfy it, and a shared road of unknown public status does not either.
"""

from __future__ import annotations

import dataclasses
import datetime

from ..geometry import Rectangle, shared_edge_m

# The register class for a road parcel. Stage S15 brings
# `config/register_classes.yml`, and this constant moves there when it lands.
ROAD_REGISTER_CLASS = "dr"

# The OSM `highway` values that count as a road classification. A value outside
# this set alarms rather than reading as "not a road": an unrecognised tag is a
# surprise, and a surprise that silently becomes `False` is invisible.
#
# **Unratified.** Nobody decided this list. It is the OSM road vocabulary as the
# tool reads it today, and it needs a decision entry before the proxy ships.
OSM_HIGHWAY_CLASSES: frozenset[str] = frozenset(
    {
        "motorway",
        "motorway_link",
        "trunk",
        "trunk_link",
        "primary",
        "primary_link",
        "secondary",
        "secondary_link",
        "tertiary",
        "tertiary_link",
        "unclassified",
        "residential",
        "living_street",
        "service",
        "track",
    }
)

ROAD_PUBLIC_STATUSES: tuple[str, ...] = (
    "public_confirmed",
    "public_by_proxy",
    "unknown",
)

SHARED_ROAD_VALUES: tuple[str, ...] = ("true", "false", "unknown")


class UnmappedHighwayClass(ValueError):
    """Raised for an OSM highway value the vocabulary does not hold."""


@dataclasses.dataclass(frozen=True)
class RoadParcel:
    """A road parcel as the free sources describe it."""

    identifier: str
    rectangle: Rectangle
    register_class: str
    osm_highway_class: str | None
    ownership_confirmed: bool
    as_of: datetime.date


@dataclasses.dataclass(frozen=True)
class RoadStatus:
    """Whether the road is public, and what says so."""

    value: str
    basis: str | None
    register_class: str | None
    osm_highway_class: str | None


@dataclasses.dataclass(frozen=True)
class SharedRoad:
    """Whether the developed neighbour is reachable from the same public road."""

    value: str
    road: str | None
    status: RoadStatus | None


def public_road_status(road: RoadParcel) -> RoadStatus:
    """Decide the road's public status from the evidence we actually hold."""
    highway = road.osm_highway_class
    if highway is not None and highway not in OSM_HIGHWAY_CLASSES:
        raise UnmappedHighwayClass(
            f"the OSM highway class {highway!r} is outside the declared "
            "vocabulary. An unmapped classification alarms; it never defaults."
        )

    if road.ownership_confirmed:
        return RoadStatus(
            value="public_confirmed",
            basis="ownership_record",
            register_class=road.register_class,
            osm_highway_class=highway,
        )

    if road.register_class == ROAD_REGISTER_CLASS and highway is not None:
        return RoadStatus(
            value="public_by_proxy",
            basis="register_class_and_osm_highway",
            register_class=road.register_class,
            osm_highway_class=highway,
        )

    return RoadStatus(
        value="unknown",
        basis=None,
        register_class=road.register_class,
        osm_highway_class=highway,
    )


def is_adjacent(parcel: Rectangle, road: RoadParcel) -> bool:
    """A shared edge, not a shared vertex."""
    return shared_edge_m(parcel, road.rectangle) > 0.0


def public_roads_of(
    parcel: Rectangle, roads: tuple[RoadParcel, ...]
) -> tuple[tuple[RoadParcel, RoadStatus], ...]:
    """Every adjacent road whose public status is established, proxy included."""
    found = []
    for road in roads:
        if not is_adjacent(parcel, road):
            continue
        status = public_road_status(road)
        if status.value == "unknown":
            continue
        found.append((road, status))
    return tuple(found)


def shared_road(
    parcel: Rectangle,
    developed_neighbour: Rectangle | None,
    roads: tuple[RoadParcel, ...],
) -> SharedRoad:
    """Is the developed neighbour reachable from the same public road?

    ``unknown`` whenever the question cannot be asked: no established public road
    on the subject's frontage, or no developed neighbour to ask about. An
    `unknown` here can only lower a verdict to `uncertain` or `unknown`, never to
    `unlikely`.
    """
    ours = public_roads_of(parcel, roads)
    if not ours:
        return SharedRoad(value="unknown", road=None, status=None)
    if developed_neighbour is None:
        return SharedRoad(value="unknown", road=None, status=None)

    theirs = {
        road.identifier for road, _status in public_roads_of(developed_neighbour, roads)
    }
    for road, status in ours:
        if road.identifier in theirs:
            return SharedRoad(value="true", road=road.identifier, status=status)
    return SharedRoad(value="false", road=None, status=ours[0][1])
