"""Does the land need agricultural de-designation?

The answer comes from the **register** land-use class and never from the advert's
claim. An advert saying *działka budowlana* over a register class of `R` is an
advert that is wrong, and FR-48 says which one wins.

The class-to-regime table is data, not a list in this module. Stage S15 brings
`config/register_classes.yml` with a regime per class and a citation per row;
until it lands, the caller supplies the mapping. That is deliberate: a branch on
a class symbol here is how a wrong regime gets hardcoded and then outlives the
table.

Silence is not a clean bill of health. A missing, blank or unrecognised class
yields `unknown`, never `not_required`. An unrecognised symbol additionally
alarms, because a missing value is a known state and an unrecognised one is a
surprise.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping

LANDUSE_VALUES: tuple[str, ...] = ("not_required", "required", "unknown")

AGRICULTURAL_REGIME = "agricultural"


@dataclasses.dataclass(frozen=True)
class LandUse:
    """The de-designation axis, and whether the symbol surprised us."""

    value: str
    register_class: str | None
    regime: str | None
    alarm: bool


def dedesignation_requirement(
    register_class: str | None, *, regime_by_class: Mapping[str, str]
) -> LandUse:
    """Map a register class to the de-designation axis of the rule table."""
    if register_class is None or not register_class.strip():
        return LandUse(value="unknown", register_class=None, regime=None, alarm=False)

    regime = regime_by_class.get(register_class)
    if regime is None:
        return LandUse(
            value="unknown",
            register_class=register_class,
            regime=None,
            alarm=True,
        )

    return LandUse(
        value="required" if regime == AGRICULTURAL_REGIME else "not_required",
        register_class=register_class,
        regime=regime,
        alarm=False,
    )
