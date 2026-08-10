"""One parcel in, one verdict out, with the evidence that produced it.

The order the steps run in is the order the rules require, and it is not
arbitrary:

1. the neighbour signal, which consults the coverage record before geometry;
2. the developed neighbour parcel, so the shared-road question has a subject;
3. the shared-road condition, which needs both the parcel and that neighbour;
4. the control count and the coverage probe, which apply M0 before the table;
5. the land-use axis, from the register class and never from the advert;
6. the table;
7. the caps, M1 and M2, which can lower `likely` and touch nothing else.

Step 4 before step 6 is the load-bearing one. A stale coverage record must be
able to turn `unlikely` into `unknown`, and a cap applied after the table could
not do it, because a cap never touches `unlikely`.
"""

from __future__ import annotations

import dataclasses
import datetime

from ..coverage import CoverageRecord, coverage_probe
from ..geometry import Rectangle, overlap_m2
from ..settings import WzParameters
from .composite import apply_caps
from .landuse import dedesignation_requirement
from .neighbour import Building, buildings_within, neighbour_signal
from .road import RoadParcel, public_roads_of, shared_road
from .table import lookup
from .wording import FeasibilityRender, render_feasibility


@dataclasses.dataclass(frozen=True)
class ParcelScene:
    """Everything the assessment reads about one parcel and its surroundings."""

    parcel: Rectangle
    land_use_class: str | None
    buildings: tuple[Building, ...] | None
    neighbour_parcels: tuple[Rectangle, ...]
    roads: tuple[RoadParcel, ...]
    protected_areas: tuple[tuple[str, Rectangle], ...]
    coverage_record: CoverageRecord | None


@dataclasses.dataclass(frozen=True)
class WzAssessment:
    """The verdict, the four axes it came from, and the evidence behind them."""

    verdict: str
    reason_codes: tuple[str, ...]
    cell_number: int
    neighbour_value: str
    neighbour_source: str | None
    neighbour_count: int
    nearest_distance_m: float | None
    shares_road_value: str
    road_status: str | None
    road_identifier: str | None
    landuse_value: str
    landuse_alarm: bool
    coverage_value: str
    coverage_reason_code: str
    coverage_source: str | None
    coverage_observation_count: int
    protection: tuple[tuple[str, float], ...]
    search_radius_m: int
    as_of: datetime.date
    # The two marks the D114 proxy rests on. They are carried on the assessment
    # so the render can name the evidence without re-deriving it, and so a test
    # can read what the verdict actually used.
    road_register_class: str | None
    road_highway_class: str | None
    coverage_checked_at: datetime.date | None

    @property
    def reason_code(self) -> str:
        """The single code the database row carries."""
        return self.reason_codes[0]

    def render(self) -> FeasibilityRender:
        """The lines a reader sees, with the disclaimer this verdict carries."""
        checked_at = self.coverage_checked_at
        return render_feasibility(
            verdict=self.verdict,
            reason_code=self.reason_code,
            radius_m=self.search_radius_m,
            distance_m=self.nearest_distance_m,
            neighbour_count=self.neighbour_count,
            source=self.neighbour_source,
            as_of=self.as_of.isoformat(),
            checked_at=checked_at.isoformat() if checked_at else None,
            road_status=self.road_status,
            register_class=self.road_register_class,
            osm_highway_class=self.road_highway_class,
        )


def _developed_neighbour(
    scene: ParcelScene, nearest_building: Building | None
) -> Rectangle | None:
    """The parcel the nearest in-radius building stands on.

    The shared-road condition is about that parcel, not about the building, so
    a building we cannot attach to a parcel leaves the question unanswerable.
    """
    if nearest_building is None:
        return None
    for candidate in scene.neighbour_parcels:
        if overlap_m2(candidate, nearest_building.rectangle) > 0.0:
            return candidate
    return None


def _protection(scene: ParcelScene) -> tuple[tuple[str, float], ...]:
    found = [
        (kind, round(overlap_m2(scene.parcel, area), 2))
        for kind, area in scene.protected_areas
        if overlap_m2(scene.parcel, area) > 0.0
    ]
    return tuple(sorted(found))


def assess_parcel(
    scene: ParcelScene,
    *,
    as_of: datetime.date,
    parameters: WzParameters,
    regime_by_class: dict[str, str],
) -> WzAssessment:
    """Run the whole chain for one parcel."""
    signal = neighbour_signal(
        scene.parcel,
        scene.buildings,
        scene.coverage_record,
        radius_m=parameters.good_neighbour_radius_m,
    )

    nearest_building = None
    if scene.buildings is not None and signal.value == "present":
        inside = buildings_within(
            scene.parcel,
            scene.buildings,
            radius_m=parameters.good_neighbour_radius_m,
        )
        nearest_building = inside[0] if inside else None

    neighbour_parcel = _developed_neighbour(scene, nearest_building)
    road = shared_road(scene.parcel, neighbour_parcel, scene.roads)

    in_probe = 0
    if scene.buildings is not None:
        in_probe = len(
            buildings_within(
                scene.parcel,
                scene.buildings,
                radius_m=parameters.coverage_probe_radius_m,
            )
        )

    probe = coverage_probe(
        scene.coverage_record,
        buildings_in_probe_radius=in_probe,
        neighbour_found=signal.value == "present",
        as_of=as_of,
        parameters=parameters,
    )

    land_use = dedesignation_requirement(
        scene.land_use_class, regime_by_class=regime_by_class
    )

    cell = lookup(
        neighbour=signal.value,
        shares_road=road.value,
        landuse=land_use.value,
        coverage=probe.value,
    )

    reasons = (probe.reason_code,) if cell.reason_from_coverage else cell.reasons
    verdict, cap_reasons = apply_caps(
        cell.verdict,
        osm_source=signal.source == "osm",
        protected=bool(_protection(scene)),
    )

    ours = public_roads_of(scene.parcel, scene.roads)
    subject_status = ours[0][1] if ours else None

    return WzAssessment(
        verdict=verdict,
        reason_codes=(*reasons, *cap_reasons),
        cell_number=cell.number,
        neighbour_value=signal.value,
        neighbour_source=signal.source,
        neighbour_count=signal.count,
        nearest_distance_m=signal.nearest_distance_m,
        shares_road_value=road.value,
        road_status=subject_status.value if subject_status else None,
        road_identifier=road.road,
        landuse_value=land_use.value,
        landuse_alarm=land_use.alarm,
        coverage_value=probe.value,
        coverage_reason_code=probe.reason_code,
        coverage_source=probe.source,
        coverage_observation_count=probe.observation_count,
        protection=_protection(scene),
        search_radius_m=parameters.good_neighbour_radius_m,
        as_of=as_of,
        road_register_class=(subject_status.register_class if subject_status else None),
        road_highway_class=(
            subject_status.osm_highway_class if subject_status else None
        ),
        coverage_checked_at=(
            scene.coverage_record.checked_at if scene.coverage_record else None
        ),
    )
