"""The parameters the WZ assessment reads, gathered in one place.

Three of the four come from `config/params.yml` (D102, D103). The fourth does
not exist there yet.

**`coverage_max_age_days` has no ratified value.** The test plan's fixture works
at 90 days; nobody decided that number and no decision entry carries it. So this
module takes it as an argument with no default. A default would be a value in
hiding: the application would start with a number nobody chose, deciding when
evidence about the world goes stale. The key needs a decision and a row in the
parameter file before the assessment ships.
"""

from __future__ import annotations

import dataclasses

from dzialki.config.params import Feasibility


@dataclasses.dataclass(frozen=True)
class WzParameters:
    """Every number the good-neighbour test uses, and nothing else."""

    good_neighbour_radius_m: int
    coverage_probe_radius_m: int
    coverage_probe_min_buildings: int
    coverage_max_age_days: int


def wz_parameters(
    feasibility: Feasibility, *, coverage_max_age_days: int
) -> WzParameters:
    """Build the parameter set from the ratified file plus the one open value."""
    return WzParameters(
        good_neighbour_radius_m=feasibility.good_neighbour_radius_m,
        coverage_probe_radius_m=feasibility.coverage_probe_radius_m,
        coverage_probe_min_buildings=feasibility.coverage_probe_min_buildings,
        coverage_max_age_days=coverage_max_age_days,
    )
