"""The estimate, and the absence that stands in its place.

Two return types, and no third. An `Estimate` always carries its range, its
sample size and the step it came from. An `Absence` carries a reason and **no
numeric price field at all** — not a nullable one, not a zero. A caller cannot
accidentally render an absence as a price, because there is no price attribute to
reach for.

A median never travels alone (D42). That is why `Estimate` has no constructor
path that produces a bare central value: `low`, `median` and `high` are all
required, and `range_kind` says which kind of range the outer two are.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal

from ..metrics import range_kind_for, round_for_storage
from ..metrics.percentiles import quantile
from .comparables import ComparableSet

BELOW = "below"
WITHIN = "within"
ABOVE = "above"

NO_COMPARABLES = "no_comparables"


@dataclass(frozen=True)
class Absence:
    """No estimate, and no number that could be mistaken for one."""

    reason: str
    n: int
    widening_step: str
    band_low: Decimal
    band_high: Decimal


@dataclass(frozen=True)
class Estimate:
    low: Decimal
    median: Decimal
    high: Decimal
    n: int
    basis: str
    widening_step: str
    range_kind: str
    price_type: str
    price_kind: str
    as_of: dt.date
    comparable_ids: tuple[int, ...]
    # D109 put the minimum at three and recorded the cost: a median of three
    # plots is close to noise. The answer is this flag beside the `n` and the
    # range, not suppression.
    below_min_comparables: bool


def estimate(
    comparable_set: ComparableSet,
    *,
    as_of: dt.date,
    price_type: str,
    price_kind: str,
    iqr_switch_n: int,
    min_before_widening: int,
) -> Estimate | Absence:
    """Turn a comparable set into an estimate, or into an absence."""
    if comparable_set.n == 0:
        return Absence(
            reason=NO_COMPARABLES,
            n=0,
            widening_step=comparable_set.widening_step,
            band_low=comparable_set.band_low,
            band_high=comparable_set.band_high,
        )

    values = [float(value) for value in comparable_set.values]
    range_kind = range_kind_for(comparable_set.n, iqr_switch_n=iqr_switch_n)
    median = round_for_storage(quantile(values, 0.50))

    if range_kind == "iqr":
        low = round_for_storage(quantile(values, 0.25))
        high = round_for_storage(quantile(values, 0.75))
    else:
        # Below the switch, the quartiles of a handful of points say less than
        # the two ends do, and they look more precise than they are.
        low = round_for_storage(min(values))
        high = round_for_storage(max(values))

    return Estimate(
        low=low,
        median=median,
        high=high,
        n=comparable_set.n,
        basis=comparable_set.widening_step,
        widening_step=comparable_set.widening_step,
        range_kind=range_kind,
        price_type=price_type,
        price_kind=price_kind,
        as_of=as_of,
        comparable_ids=tuple(m.listing_id for m in comparable_set.members),
        below_min_comparables=comparable_set.n < min_before_widening,
    )


def verdict(observed_ppm2: Decimal, est: Estimate) -> str:
    """Where the asking price sits **relative to the range** (FR-38).

    Never a percentage off the median. A percentage implies the median is a
    point the price ought to be at, and it is not: it is the middle of a spread
    that is often wide. Both bounds are inclusive, so a price exactly on the edge
    reads as inside rather than as a near miss.
    """
    if observed_ppm2 < est.low:
        return BELOW
    if observed_ppm2 > est.high:
        return ABOVE
    return WITHIN
