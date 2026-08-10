"""The coverage probe: did we look, or is the map empty?

This is the detector for the failure the whole stage exists to prevent. A county
that publishes no building layer returns zero buildings, and zero buildings looks
exactly like open countryside. A verdict of `unlikely` built on that reads as
decisive and specific, and nothing in the output reveals that the map was blank.

Coverage is `present` when three things hold at once:

1. the gmina's record says a building layer is published,
2. the record is not older than the configured maximum age, and
3. either a neighbouring building was actually found, or the count inside the
   probe radius reaches the configured minimum.

The third clause is worth reading twice. **A neighbour found proves coverage a
fortiori** — we are holding a building geometry from this place, so the map is
populated here and no count is needed. The control count exists only to answer
the question an empty result poses: when we found nothing, was there nothing, or
did we not look?

D103 makes the radius and the minimum count configuration, and the 20-parcel
labelled set arbitrates them. That set does not exist. Until it does, the shipped
values rest on nothing, and setting the minimum too low reproduces the exact
error `unknown` exists to prevent, one parcel at a time.
"""

from __future__ import annotations

import dataclasses
import datetime

from .settings import WzParameters

COVERAGE_VALUES: tuple[str, ...] = ("present", "absent")

COVERAGE_REASON_CODES: tuple[str, ...] = (
    "coverage_confirmed_by_neighbour",
    "coverage_confirmed_by_control_count",
    "building_data_unavailable",
    "coverage_record_stale",
    "coverage_unproven",
)


@dataclasses.dataclass(frozen=True)
class CoverageRecord:
    """What a gmina publishes, and when we last checked."""

    teryt_gmina: str
    source: str
    has_coverage: bool
    checked_at: datetime.date


@dataclasses.dataclass(frozen=True)
class CoverageProbe:
    """The evidence a verdict of `unlikely` rests on, with its provenance.

    `source` and `as_of` are ``None`` whenever the value is `absent`. The
    database constraint `unlikely_requires_coverage` reads the source, so an
    absent probe that still named one would let the constraint pass on evidence
    we do not hold.
    """

    value: str
    reason_code: str
    source: str | None
    as_of: datetime.date | None
    observation_count: int
    probe_radius_m: int
    min_buildings: int
    age_days: int | None


def coverage_probe(
    record: CoverageRecord | None,
    *,
    buildings_in_probe_radius: int,
    neighbour_found: bool,
    as_of: datetime.date,
    parameters: WzParameters,
) -> CoverageProbe:
    """Decide whether the map around this parcel is demonstrably populated."""

    def outcome(
        value: str,
        reason_code: str,
        *,
        age_days: int | None,
        attested: bool,
    ) -> CoverageProbe:
        return CoverageProbe(
            value=value,
            reason_code=reason_code,
            source=record.source if attested and record is not None else None,
            as_of=record.checked_at if attested and record is not None else None,
            observation_count=buildings_in_probe_radius,
            probe_radius_m=parameters.coverage_probe_radius_m,
            min_buildings=parameters.coverage_probe_min_buildings,
            age_days=age_days,
        )

    if record is None or not record.has_coverage:
        return outcome(
            "absent", "building_data_unavailable", age_days=None, attested=False
        )

    age_days = (as_of - record.checked_at).days
    if age_days > parameters.coverage_max_age_days:
        return outcome(
            "absent", "coverage_record_stale", age_days=age_days, attested=False
        )

    if neighbour_found:
        return outcome(
            "present",
            "coverage_confirmed_by_neighbour",
            age_days=age_days,
            attested=True,
        )

    if buildings_in_probe_radius >= parameters.coverage_probe_min_buildings:
        return outcome(
            "present",
            "coverage_confirmed_by_control_count",
            age_days=age_days,
            attested=True,
        )

    return outcome("absent", "coverage_unproven", age_days=age_days, attested=False)
