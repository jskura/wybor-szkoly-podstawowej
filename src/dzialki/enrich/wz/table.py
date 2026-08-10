"""The composite rule table. Fifty-four cells, written out, one at a time.

`3 (neighbour) × 3 (shares_road) × 3 (landuse) × 2 (coverage) = 54`. Every cell
is declared. No cell falls through to a default, and no cell is computed from a
rule, because a rule is where a reader stops being able to check the answer.

**It is a table, not a score.** A weighted sum would let two weak positives
outvote a missing-data `unknown`, which is the one thing this stage may not do.
There is no arithmetic in this module at all.

`likely` occupies exactly one cell. That is the mechanical form of the
presentation rule in `19` §1.2: the optimistic answer is the dangerous one,
because it is the answer that would make somebody spend money. Every one of the
eight degradations removes it.

The nine cells with no neighbour and no coverage defer their reason to the
coverage probe. "The record says there is no layer", "the record is too old" and
"the count did not reach the minimum" call for different operator actions and
different sentences, and one code across all three would pass every verdict test
and still be wrong.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from types import MappingProxyType

NEIGHBOUR_VALUES: tuple[str, ...] = ("present", "absent", "unknown")
SHARES_ROAD_VALUES: tuple[str, ...] = ("true", "false", "unknown")
LANDUSE_VALUES: tuple[str, ...] = ("not_required", "required", "unknown")
COVERAGE_VALUES: tuple[str, ...] = ("present", "absent")

VERDICTS: tuple[str, ...] = ("likely", "uncertain", "unlikely", "unknown")


@dataclasses.dataclass(frozen=True)
class Cell:
    """One row of the table: a verdict and why."""

    number: int
    verdict: str
    reasons: tuple[str, ...]
    reason_from_coverage: bool = False


# number, neighbour, shares_road, landuse, coverage, verdict, reasons
_ROWS: tuple[tuple, ...] = (
    # Block 1 — neighbour present, coverage present.
    (
        1,
        "present",
        "true",
        "not_required",
        "present",
        "likely",
        ("good_neighbour_satisfied",),
    ),
    (
        2,
        "present",
        "true",
        "required",
        "present",
        "uncertain",
        ("dedesignation_required",),
    ),
    (3, "present", "true", "unknown", "present", "uncertain", ("landuse_unknown",)),
    (
        4,
        "present",
        "false",
        "not_required",
        "present",
        "uncertain",
        ("neighbour_on_different_road",),
    ),
    (
        5,
        "present",
        "false",
        "required",
        "present",
        "uncertain",
        ("neighbour_on_different_road", "dedesignation_required"),
    ),
    (
        6,
        "present",
        "false",
        "unknown",
        "present",
        "uncertain",
        ("neighbour_on_different_road", "landuse_unknown"),
    ),
    (
        7,
        "present",
        "unknown",
        "not_required",
        "present",
        "uncertain",
        ("road_status_unknown",),
    ),
    (
        8,
        "present",
        "unknown",
        "required",
        "present",
        "uncertain",
        ("road_status_unknown", "dedesignation_required"),
    ),
    (
        9,
        "present",
        "unknown",
        "unknown",
        "present",
        "uncertain",
        ("road_status_unknown", "landuse_unknown"),
    ),
    # Block 2 — neighbour present, coverage absent. Reachable through a stale or
    # negative record contradicted by an observed building. The observation
    # stands; the optimism does not.
    (
        10,
        "present",
        "true",
        "not_required",
        "absent",
        "uncertain",
        ("capped_by_coverage_absent",),
    ),
    (
        11,
        "present",
        "true",
        "required",
        "absent",
        "uncertain",
        ("capped_by_coverage_absent", "dedesignation_required"),
    ),
    (
        12,
        "present",
        "true",
        "unknown",
        "absent",
        "uncertain",
        ("capped_by_coverage_absent", "landuse_unknown"),
    ),
    (
        13,
        "present",
        "false",
        "not_required",
        "absent",
        "uncertain",
        ("capped_by_coverage_absent", "neighbour_on_different_road"),
    ),
    (
        14,
        "present",
        "false",
        "required",
        "absent",
        "uncertain",
        (
            "capped_by_coverage_absent",
            "neighbour_on_different_road",
            "dedesignation_required",
        ),
    ),
    (
        15,
        "present",
        "false",
        "unknown",
        "absent",
        "uncertain",
        ("capped_by_coverage_absent", "neighbour_on_different_road", "landuse_unknown"),
    ),
    (
        16,
        "present",
        "unknown",
        "not_required",
        "absent",
        "uncertain",
        ("capped_by_coverage_absent", "road_status_unknown"),
    ),
    (
        17,
        "present",
        "unknown",
        "required",
        "absent",
        "uncertain",
        ("capped_by_coverage_absent", "road_status_unknown", "dedesignation_required"),
    ),
    (
        18,
        "present",
        "unknown",
        "unknown",
        "absent",
        "uncertain",
        ("capped_by_coverage_absent", "road_status_unknown", "landuse_unknown"),
    ),
    # Block 3 — neighbour absent, coverage present. The good-neighbour condition
    # has demonstrably failed. Road and land use can add obstacles, never remove
    # this one, so the whole block is one verdict.
    (
        19,
        "absent",
        "true",
        "not_required",
        "present",
        "unlikely",
        ("no_neighbour_within_radius",),
    ),
    (
        20,
        "absent",
        "true",
        "required",
        "present",
        "unlikely",
        ("no_neighbour_within_radius", "dedesignation_required"),
    ),
    (
        21,
        "absent",
        "true",
        "unknown",
        "present",
        "unlikely",
        ("no_neighbour_within_radius", "landuse_unknown"),
    ),
    (
        22,
        "absent",
        "false",
        "not_required",
        "present",
        "unlikely",
        ("no_neighbour_within_radius",),
    ),
    (
        23,
        "absent",
        "false",
        "required",
        "present",
        "unlikely",
        ("no_neighbour_within_radius", "dedesignation_required"),
    ),
    (
        24,
        "absent",
        "false",
        "unknown",
        "present",
        "unlikely",
        ("no_neighbour_within_radius", "landuse_unknown"),
    ),
    (
        25,
        "absent",
        "unknown",
        "not_required",
        "present",
        "unlikely",
        ("no_neighbour_within_radius", "road_status_unknown"),
    ),
    (
        26,
        "absent",
        "unknown",
        "required",
        "present",
        "unlikely",
        ("no_neighbour_within_radius", "road_status_unknown", "dedesignation_required"),
    ),
    (
        27,
        "absent",
        "unknown",
        "unknown",
        "present",
        "unlikely",
        ("no_neighbour_within_radius", "road_status_unknown", "landuse_unknown"),
    ),
    # Block 4 — neighbour absent, coverage absent. The block O17 exists for, and
    # the one the schema makes unwritable in its wrong form. `unlikely` appears
    # nowhere in it. The reason comes from the probe.
    (28, "absent", "true", "not_required", "absent", "unknown", ()),
    (29, "absent", "true", "required", "absent", "unknown", ()),
    (30, "absent", "true", "unknown", "absent", "unknown", ()),
    (31, "absent", "false", "not_required", "absent", "unknown", ()),
    (32, "absent", "false", "required", "absent", "unknown", ()),
    (33, "absent", "false", "unknown", "absent", "unknown", ()),
    (34, "absent", "unknown", "not_required", "absent", "unknown", ()),
    (35, "absent", "unknown", "required", "absent", "unknown", ()),
    (36, "absent", "unknown", "unknown", "absent", "unknown", ()),
    # Block 5 — neighbour unknown, coverage present. The layer exists and is
    # populated; our read of it did not succeed.
    (
        37,
        "unknown",
        "true",
        "not_required",
        "present",
        "unknown",
        ("building_query_failed",),
    ),
    (
        38,
        "unknown",
        "true",
        "required",
        "present",
        "unknown",
        ("building_query_failed",),
    ),
    (
        39,
        "unknown",
        "true",
        "unknown",
        "present",
        "unknown",
        ("building_query_failed",),
    ),
    (
        40,
        "unknown",
        "false",
        "not_required",
        "present",
        "unknown",
        ("building_query_failed",),
    ),
    (
        41,
        "unknown",
        "false",
        "required",
        "present",
        "unknown",
        ("building_query_failed",),
    ),
    (
        42,
        "unknown",
        "false",
        "unknown",
        "present",
        "unknown",
        ("building_query_failed",),
    ),
    (
        43,
        "unknown",
        "unknown",
        "not_required",
        "present",
        "unknown",
        ("building_query_failed",),
    ),
    (
        44,
        "unknown",
        "unknown",
        "required",
        "present",
        "unknown",
        ("building_query_failed",),
    ),
    (
        45,
        "unknown",
        "unknown",
        "unknown",
        "present",
        "unknown",
        ("building_query_failed",),
    ),
    # Block 6 — neighbour unknown, coverage absent. There is no layer to read.
    (
        46,
        "unknown",
        "true",
        "not_required",
        "absent",
        "unknown",
        ("building_data_unavailable",),
    ),
    (
        47,
        "unknown",
        "true",
        "required",
        "absent",
        "unknown",
        ("building_data_unavailable",),
    ),
    (
        48,
        "unknown",
        "true",
        "unknown",
        "absent",
        "unknown",
        ("building_data_unavailable",),
    ),
    (
        49,
        "unknown",
        "false",
        "not_required",
        "absent",
        "unknown",
        ("building_data_unavailable",),
    ),
    (
        50,
        "unknown",
        "false",
        "required",
        "absent",
        "unknown",
        ("building_data_unavailable",),
    ),
    (
        51,
        "unknown",
        "false",
        "unknown",
        "absent",
        "unknown",
        ("building_data_unavailable",),
    ),
    (
        52,
        "unknown",
        "unknown",
        "not_required",
        "absent",
        "unknown",
        ("building_data_unavailable",),
    ),
    (
        53,
        "unknown",
        "unknown",
        "required",
        "absent",
        "unknown",
        ("building_data_unavailable",),
    ),
    (
        54,
        "unknown",
        "unknown",
        "unknown",
        "absent",
        "unknown",
        ("building_data_unavailable",),
    ),
)

TRUTH_TABLE: Mapping[tuple[str, str, str, str], Cell] = MappingProxyType(
    {
        (neighbour, shares_road, landuse, coverage): Cell(
            number=number,
            verdict=verdict,
            reasons=reasons,
            reason_from_coverage=not reasons,
        )
        for number, neighbour, shares_road, landuse, coverage, verdict, reasons in _ROWS
    }
)


def lookup(*, neighbour: str, shares_road: str, landuse: str, coverage: str) -> Cell:
    """The cell for these four axis values, or an error naming the offender.

    Keyword-only, so the caller cannot transpose two axes silently, and the
    verdict cannot depend on the order the signals were evaluated in.
    """
    key = (neighbour, shares_road, landuse, coverage)
    try:
        return TRUTH_TABLE[key]
    except KeyError:
        raise ValueError(f"{key} is outside the declared axis values") from None
