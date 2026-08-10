"""The words a verdict is allowed to reach a reader in.

Two rules govern this module.

**`likely` never appears without the same disclaimer as `unlikely`.** The
optimistic answer is the dangerous one, because it is the one that would make
somebody spend money, so it carries the heaviest warning rather than the
lightest. The disclaimer is one constant and one object, so nobody can soften a
second copy of it later.

**A `likely` verdict resting on the D114 road proxy says so (FR-76, V66).** Its
disclaimer and its evidence marker differ from the wording reserved for confirmed
ownership, and a test asserts the two are never equal by hash.

**The road copy is not ratified. O39 is open.** `19` §1.2 ratified the WZ
disclaimer and the `unlikely` sentence; nobody has written the Polish for the
proxy. The strings below are a proposal, pinned by hash so an edit shows up as a
changed hash instead of a silent rewrite. `ROAD_COPY_IS_RATIFIED` records the
state in the code rather than in a comment somebody will delete.

This module returns lines, not a screen. Where the lines sit — and in particular
that the disclaimer sits at the collapsed level rather than behind an expander —
is the render package's rule, and it is not discharged here.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from types import MappingProxyType

# Ratified in `19` §1.2. NFC, U+2014 EM DASH, U+0020 either side of it.
WZ_DISCLAIMER = "wstępna ocena — nie jest to gwarancja wydania WZ"

WZ_UNLIKELY_TEMPLATE = (
    "brak spełnienia warunku dobrego sąsiedztwa w promieniu {radius} m"
)

WZ_LIKELY_TEMPLATE = (
    "warunek dobrego sąsiedztwa wygląda na spełniony — "
    "budynek w odległości {distance} m, w promieniu {radius} m"
)

WZ_UNCERTAIN_LINE = "warunku dobrego sąsiedztwa nie udało się jednoznacznie ocenić"

# One sentence per kind of `unknown`. A single sentence across all four would
# tell a reader that we do not know, and never which of four different things we
# do not know.
UNKNOWN_LINES: Mapping[str, str] = MappingProxyType(
    {
        "building_data_unavailable": (
            "brak danych o budynkach w tej gminie — "
            "nie wiemy, czy w pobliżu stoją budynki"
        ),
        "coverage_unproven": (
            "nie potwierdziliśmy, że mapa budynków w tej okolicy jest wypełniona"
        ),
        "coverage_record_stale": (
            "dane o budynkach dla tej gminy są nieaktualne (sprawdzone {checked_at})"
        ),
        "building_query_failed": "nie udało się odczytać danych o budynkach",
    }
)

PROVENANCE_TEMPLATE = (
    "n = {count} w promieniu {radius} m, źródło {source}, dane z {as_of}"
)

# --- the two road wordings, which must never be equal (V66) ---------------

ROAD_COPY_IS_RATIFIED = False

ROAD_CONFIRMED_WORDING = "dostęp do drogi publicznej potwierdzony w rejestrze własności"

ROAD_PROXY_DISCLAIMER = (
    "status drogi publicznej wnioskujemy z klasy użytku i z klasy drogi OSM — "
    "to przesłanka, nie potwierdzenie własności"
)

ROAD_PROXY_EVIDENCE_TEMPLATE = (
    "przesłanka drogi publicznej: klasa użytku {register_class}, "
    "klasa drogi OSM {osm_highway_class}"
)


class CrossedRoadWording(AssertionError):
    """Raised when a road wording appears on a verdict it does not belong to."""


@dataclasses.dataclass(frozen=True)
class FeasibilityRender:
    """The lines one verdict produces, and the disclaimer it always carries."""

    verdict: str
    reason_code: str
    disclaimer: str
    verdict_line: str
    evidence_marker: str | None
    lines: tuple[str, ...]


def _verdict_line(
    verdict: str,
    reason_code: str,
    *,
    radius_m: int,
    distance_m: float | None,
    checked_at: str | None,
) -> str:
    if verdict == "likely":
        return WZ_LIKELY_TEMPLATE.format(distance=distance_m, radius=radius_m)
    if verdict == "unlikely":
        return WZ_UNLIKELY_TEMPLATE.format(radius=radius_m)
    if verdict == "uncertain":
        return WZ_UNCERTAIN_LINE
    if verdict == "unknown":
        try:
            template = UNKNOWN_LINES[reason_code]
        except KeyError:
            raise ValueError(
                f"the reason code {reason_code!r} has no sentence. An unknown "
                "verdict that names no kind of unknown is an unactionable shrug."
            ) from None
        return template.format(checked_at=checked_at)
    raise ValueError(f"{verdict!r} is outside the verdict vocabulary")


def _road_lines(
    road_status: str | None,
    *,
    register_class: str | None,
    osm_highway_class: str | None,
) -> tuple[tuple[str, ...], str | None]:
    if road_status == "public_confirmed":
        return (ROAD_CONFIRMED_WORDING,), None
    if road_status == "public_by_proxy":
        marker = ROAD_PROXY_EVIDENCE_TEMPLATE.format(
            register_class=register_class,
            osm_highway_class=osm_highway_class,
        )
        return (ROAD_PROXY_DISCLAIMER, marker), marker
    return (), None


def render_feasibility(
    *,
    verdict: str,
    reason_code: str,
    radius_m: int,
    distance_m: float | None = None,
    neighbour_count: int = 0,
    source: str | None = None,
    as_of: str | None = None,
    checked_at: str | None = None,
    road_status: str | None = None,
    register_class: str | None = None,
    osm_highway_class: str | None = None,
) -> FeasibilityRender:
    """Render one verdict as lines, always with its disclaimer.

    The radius is the radius the verdict was computed at, never a value read
    from configuration at render time. Re-rendering an old verdict after a
    configuration change must not restate it with the new radius.
    """
    verdict_line = _verdict_line(
        verdict,
        reason_code,
        radius_m=radius_m,
        distance_m=distance_m,
        checked_at=checked_at,
    )
    road_lines, marker = _road_lines(
        road_status,
        register_class=register_class,
        osm_highway_class=osm_highway_class,
    )
    provenance = PROVENANCE_TEMPLATE.format(
        count=neighbour_count,
        radius=radius_m,
        source=source or "brak",
        as_of=as_of or "brak",
    )

    lines = (verdict_line, provenance, *road_lines, WZ_DISCLAIMER)
    check_road_wording(lines, road_status=road_status)

    return FeasibilityRender(
        verdict=verdict,
        reason_code=reason_code,
        disclaimer=WZ_DISCLAIMER,
        verdict_line=verdict_line,
        evidence_marker=marker,
        lines=lines,
    )


def check_road_wording(lines: tuple[str, ...], *, road_status: str | None) -> None:
    """Refuse a page that states the wrong thing about the road (V66).

    The scans in the test suite are negative assertions, and a negative
    assertion passes trivially against a page that says nothing about roads at
    all. This check is the positive form, and it runs on every render.
    """
    text = "\n".join(lines)
    if road_status == "public_by_proxy" and ROAD_CONFIRMED_WORDING in text:
        raise CrossedRoadWording(
            "a verdict with road status 'public_by_proxy' carries the wording "
            "reserved for confirmed ownership"
        )
    if road_status != "public_by_proxy" and ROAD_PROXY_DISCLAIMER in text:
        raise CrossedRoadWording(
            f"a verdict with road status {road_status!r} carries the proxy "
            "disclaimer, which belongs to 'public_by_proxy' alone"
        )
