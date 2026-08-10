"""The fixed area bands (D48).

These are the strata `metric_unit_month` is keyed by. They are not the comparable
window: that one is ±50 % of the subject's own area and belongs to the estimator.
The two answer differently on the same set, so this module never calls itself a
window and the estimator never calls itself a band.

Every band is lower-inclusive, `[lower, upper)`. An off-by-one at an edge moves
observations between aggregates and nothing in the output shows it.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class AreaBand:
    """One stratum. ``None`` at either end means the band is open there."""

    label: str
    lower_m2: Decimal | None
    upper_m2: Decimal | None

    def holds(self, area_m2: Decimal) -> bool:
        at_or_above_lower = self.lower_m2 is None or area_m2 >= self.lower_m2
        below_upper = self.upper_m2 is None or area_m2 < self.upper_m2
        return at_or_above_lower and below_upper


AREA_BANDS = (
    AreaBand("<800", None, Decimal(800)),
    AreaBand("800-1500", Decimal(800), Decimal(1500)),
    AreaBand("1500-3000", Decimal(1500), Decimal(3000)),
    AreaBand("3000-10000", Decimal(3000), Decimal(10000)),
    AreaBand(">10000", Decimal(10000), None),
)


def band_for(area_m2: Decimal | int) -> str:
    """The label of the one band that holds ``area_m2``.

    The ladder is open at both ends, so every positive area lands somewhere. An
    area of zero or less has no price per square metre either, and raises.
    """
    area = Decimal(area_m2)
    if area <= 0:
        raise ValueError(f"an area must be positive, not {area}")

    for band in AREA_BANDS:
        if band.holds(area):
            return band.label
    raise ValueError(f"the band ladder has a gap at {area} m²")
