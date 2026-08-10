"""R14 — road adjacency and the D114 public-road proxy.

Free EGiB data carries no ownership. Without a substitute `road_public_status`
reads `unknown` for every road in production, and the one `likely` cell of the
54 never occurs. D114 accepts a substitute: register class `dr` plus an OSM
highway class.

That pair is evidence, not proof. A private access road can carry both marks, so
FR-76 makes a `likely` verdict resting on it say so. The wording tests live in
`test_r14_wording.py`; this file tests the inference itself.
"""

from __future__ import annotations

import datetime
import pathlib

import pytest
import yaml

pytestmark = [pytest.mark.unit]


@pytest.fixture
def scene(repo_root: pathlib.Path) -> dict:
    path = repo_root / "tests" / "fixtures" / "synthetic" / "wz_scene.yml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def parcel(scene: dict, identifier: str):
    from dzialki.enrich.geometry import PLANAR_SRID, Rectangle

    for row in scene["parcels"]:
        if row["id"] == identifier:
            return Rectangle(*row["rectangle"], srid=PLANAR_SRID)
    raise LookupError(identifier)


def roads_of(scene: dict):
    from dzialki.enrich.geometry import PLANAR_SRID, Rectangle
    from dzialki.enrich.wz.road import RoadParcel

    return tuple(
        RoadParcel(
            identifier=row["id"],
            rectangle=Rectangle(*row["rectangle"], srid=PLANAR_SRID),
            register_class=row["register_class"],
            osm_highway_class=row["osm_highway_class"],
            ownership_confirmed=row["ownership_confirmed"],
            as_of=datetime.date.fromisoformat(scene["as_of"]),
        )
        for row in scene["roads"]
    )


def road(scene: dict, identifier: str):
    return next(item for item in roads_of(scene) if item.identifier == identifier)


# --- the proxy ------------------------------------------------------------


def test_register_class_and_an_osm_highway_class_make_the_proxy(scene: dict) -> None:
    """D114. R1 carries `dr` and `highway=residential`, and no ownership."""
    from dzialki.enrich.wz.road import public_road_status

    status = public_road_status(road(scene, "R1"))
    assert status.value == "public_by_proxy"
    assert status.basis == "register_class_and_osm_highway"
    assert status.register_class == "dr"
    assert status.osm_highway_class == "residential"


def test_a_road_parcel_of_unknown_ownership_without_an_osm_class_is_unknown(
    scene: dict,
) -> None:
    """R2 is a `dr` parcel that OSM does not classify.

    `unknown`, never `no access`. The same discipline the building layer gets.
    """
    from dzialki.enrich.wz.road import public_road_status

    status = public_road_status(road(scene, "R2"))
    assert status.value == "unknown"
    assert status.basis is None


def test_confirmed_ownership_outranks_the_proxy() -> None:
    """The value the proxy stands in for. Free EGiB never produces it today."""
    from dzialki.enrich.geometry import PLANAR_SRID, Rectangle
    from dzialki.enrich.wz.road import RoadParcel, public_road_status

    confirmed = RoadParcel(
        identifier="R-owned",
        rectangle=Rectangle(
            599_000.0, 614_000.0, 499_990.0, 500_000.0, srid=PLANAR_SRID
        ),
        register_class="dr",
        osm_highway_class="residential",
        ownership_confirmed=True,
        as_of=datetime.date(2026, 8, 8),
    )
    status = public_road_status(confirmed)
    assert status.value == "public_confirmed"
    assert status.basis == "ownership_record"


def test_a_non_road_register_class_is_not_evidence() -> None:
    from dzialki.enrich.geometry import PLANAR_SRID, Rectangle
    from dzialki.enrich.wz.road import RoadParcel, public_road_status

    not_a_road = RoadParcel(
        identifier="R-field",
        rectangle=Rectangle(
            599_000.0, 599_100.0, 499_990.0, 500_000.0, srid=PLANAR_SRID
        ),
        register_class="R",
        osm_highway_class="residential",
        ownership_confirmed=False,
        as_of=datetime.date(2026, 8, 8),
    )
    assert public_road_status(not_a_road).value == "unknown"


def test_an_unmapped_osm_highway_class_alarms_rather_than_defaulting() -> None:
    """FR-49's discipline. A classification we do not recognise is a surprise,
    and a surprise that silently becomes "not a public road" is invisible."""
    from dzialki.enrich.geometry import PLANAR_SRID, Rectangle
    from dzialki.enrich.wz.road import (
        RoadParcel,
        UnmappedHighwayClass,
        public_road_status,
    )

    strange = RoadParcel(
        identifier="R-strange",
        rectangle=Rectangle(
            599_000.0, 599_100.0, 499_990.0, 500_000.0, srid=PLANAR_SRID
        ),
        register_class="dr",
        osm_highway_class="teleportacyjna",
        ownership_confirmed=False,
        as_of=datetime.date(2026, 8, 8),
    )
    with pytest.raises(UnmappedHighwayClass) as caught:
        public_road_status(strange)
    assert "teleportacyjna" in str(caught.value)


def test_the_osm_highway_vocabulary_is_declared_data() -> None:
    """A hardcoded branch on a tag value is how an unmapped class becomes a
    silent `False`. The vocabulary is a declared set, and the alarm above is
    what a value outside it produces."""
    from dzialki.enrich.wz.road import OSM_HIGHWAY_CLASSES

    assert "residential" in OSM_HIGHWAY_CLASSES
    assert "teleportacyjna" not in OSM_HIGHWAY_CLASSES
    assert isinstance(OSM_HIGHWAY_CLASSES, frozenset)


# --- adjacency ------------------------------------------------------------


def test_a_shared_edge_is_adjacency(scene: dict) -> None:
    from dzialki.enrich.wz.road import is_adjacent

    assert is_adjacent(parcel(scene, "P1"), road(scene, "R1")) is True


def test_a_single_shared_vertex_is_not_adjacency(scene: dict) -> None:
    """P3 meets R3 at exactly one point. A corner is not access."""
    from dzialki.enrich.wz.road import is_adjacent

    assert is_adjacent(parcel(scene, "P3"), road(scene, "R3")) is False


def test_a_parcel_touching_no_road_is_not_adjacent(scene: dict) -> None:
    from dzialki.enrich.wz.road import is_adjacent

    assert [
        item.identifier
        for item in roads_of(scene)
        if is_adjacent(parcel(scene, "P8"), item)
    ] == []


# --- the shared-road condition -------------------------------------------


def test_a_neighbour_on_the_same_public_road_satisfies_the_condition(
    scene: dict,
) -> None:
    from dzialki.enrich.wz.road import shared_road

    result = shared_road(parcel(scene, "P1"), parcel(scene, "P1N"), roads_of(scene))
    assert result.value == "true"
    assert result.road == "R1"
    assert result.status.value == "public_by_proxy"


def test_a_developed_neighbour_on_a_different_road_does_not(scene: dict) -> None:
    """P7 fronts R1. Its developed neighbour P7N fronts R2 and never touches R1."""
    from dzialki.enrich.wz.road import shared_road

    result = shared_road(parcel(scene, "P7"), parcel(scene, "P7N"), roads_of(scene))
    assert result.value == "false"
    assert result.road is None


def test_the_condition_cannot_be_evaluated_without_a_developed_neighbour(
    scene: dict,
) -> None:
    """P2 has no neighbour inside the radius, so the second half of the WZ
    condition has nothing to be about. `unknown`, which can only lower a verdict
    to `uncertain` or `unknown`, never to `unlikely`."""
    from dzialki.enrich.wz.road import shared_road

    result = shared_road(parcel(scene, "P2"), None, roads_of(scene))
    assert result.value == "unknown"


def test_the_condition_cannot_be_evaluated_without_road_adjacency(
    scene: dict,
) -> None:
    from dzialki.enrich.wz.road import shared_road

    result = shared_road(parcel(scene, "P8"), parcel(scene, "P7N"), roads_of(scene))
    assert result.value == "unknown"


def test_a_road_of_unknown_public_status_cannot_satisfy_the_condition(
    scene: dict,
) -> None:
    """P7N and R2 share an edge, but R2's public status is unknown, so a
    neighbour reachable only along R2 proves nothing about public access."""
    from dzialki.enrich.wz.road import is_adjacent, public_road_status, shared_road

    assert is_adjacent(parcel(scene, "P7N"), road(scene, "R2")) is True
    assert public_road_status(road(scene, "R2")).value == "unknown"

    result = shared_road(parcel(scene, "P7N"), parcel(scene, "P7"), roads_of(scene))
    assert result.value == "unknown"
