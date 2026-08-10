"""Units, price per square metre, area bands and quarantine.

Four modules, in the order a record passes through them:

- `units` — Polish area and price strings to exact `Decimal` values.
- `area_authority` — which stated area wins, and what the losers said.
- `bands` — the validity band, which flags a record and never drops one.
- `quarantine` — why a record cannot become a listing.

Nothing here reads a database or a network. Every function is pure, so a
recorded payload can be re-parsed at any time (V42).
"""

from .area_authority import (
    AUTHORITY_ORDER,
    ConflictRule,
    NoAreaStated,
    ResolvedArea,
    resolve_area,
)
from .bands import Bands, Flag, band_flags, price_per_m2
from .quarantine import QuarantinedRecord, QuarantineReason, reason_for
from .units import (
    AR_IN_M2,
    HA_IN_M2,
    MLN_MULTIPLIER,
    TYS_MULTIPLIER,
    AreaFailure,
    AreaParse,
    PriceFailure,
    PriceParse,
    parse_area,
    parse_price,
)

__all__ = [
    "AR_IN_M2",
    "AUTHORITY_ORDER",
    "HA_IN_M2",
    "MLN_MULTIPLIER",
    "TYS_MULTIPLIER",
    "AreaFailure",
    "AreaParse",
    "Bands",
    "ConflictRule",
    "Flag",
    "NoAreaStated",
    "PriceFailure",
    "PriceParse",
    "QuarantineReason",
    "QuarantinedRecord",
    "ResolvedArea",
    "band_flags",
    "parse_area",
    "parse_price",
    "price_per_m2",
    "reason_for",
    "resolve_area",
]
