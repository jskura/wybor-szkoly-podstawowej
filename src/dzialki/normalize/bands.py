"""The validity band. It flags a record; it never drops one.

FR-12 as amended by O12: area [300, 200 000] m², price [1, 100 000] PLN/m²,
inclusive at both ends. A record outside the band stays in the corpus and on
the plot page with its flag (D85, rule 7). Aggregates exclude it, and that is a
separate stage.

The band that O12 replaced was 100–500 000 m². Copying it back would quietly
discard 20–50 ha farmland, which is the product's own subject.

D88: the check reads the exact quotient, not the NUMERIC(12,2) value the
generated column stores. A record whose stored figure rounds back onto the edge
is still above it.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from ..config import Params


class Flag(str, Enum):
    """A flag is shown with the record. It is never a reason to hide one."""

    AREA_BELOW_BAND = "area_below_band"
    AREA_ABOVE_BAND = "area_above_band"
    PRICE_BELOW_BAND = "price_below_band"
    PRICE_ABOVE_BAND = "price_above_band"


@dataclass(frozen=True)
class Bands:
    area: tuple[Decimal, Decimal]
    price_per_m2: tuple[Decimal, Decimal]

    @classmethod
    def from_params(cls, params: Params) -> Bands:
        return cls(
            area=(
                Decimal(params.validation.area_min_m2),
                Decimal(params.validation.area_max_m2),
            ),
            price_per_m2=(
                Decimal(params.validation.price_per_m2_min_pln),
                Decimal(params.validation.price_per_m2_max_pln),
            ),
        )


def price_per_m2(price_pln: Decimal, area_m2: Decimal) -> Decimal:
    """The exact quotient, for the band check to read (D88).

    The database stores a rounded copy in a generated column. This value is the
    one the band judges, so a record that rounds onto the edge is still flagged.
    """
    if area_m2 <= 0:
        raise ValueError(f"area_m2 must be positive, not {area_m2}")
    return price_pln / area_m2


def band_flags(
    area_m2: Decimal, price_per_m2: Decimal, *, bands: Bands
) -> frozenset[Flag]:
    """Which band edges this record crosses. An empty set means it is in band."""
    if area_m2 <= 0:
        # A non-positive area is quarantined upstream as `area_non_positive`.
        # Refusing it here keeps the two stages from disagreeing silently.
        raise ValueError(f"area_m2 must be positive, not {area_m2}")

    area_min, area_max = bands.area
    price_min, price_max = bands.price_per_m2
    flags: set[Flag] = set()
    if area_m2 < area_min:
        flags.add(Flag.AREA_BELOW_BAND)
    if area_m2 > area_max:
        flags.add(Flag.AREA_ABOVE_BAND)
    if price_per_m2 < price_min:
        flags.add(Flag.PRICE_BELOW_BAND)
    if price_per_m2 > price_max:
        flags.add(Flag.PRICE_ABOVE_BAND)
    return frozenset(flags)
