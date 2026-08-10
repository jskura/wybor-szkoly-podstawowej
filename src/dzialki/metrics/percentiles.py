"""The percentile function, and the one place a figure becomes a stored number.

Percentile conventions differ. R's `type=7` interpolates between the two ranks a
quantile falls between; other conventions take the lower rank, the higher rank,
the nearest, or the midpoint. They give different answers on the same data, and a
convention picked by accident produces slightly wrong ranges forever. F11 is that
failure mode. `PERCENTILE_METHOD` is the decision written down, and the
differential test against numpy is the check on it.

`percentiles` returns unrounded floats. Rounding here would hide a convention
error from the reference. `round_for_storage` is the single rounding boundary,
and it goes through `str`: `Decimal(1.005)` is 1.00499999… and `ROUND_HALF_UP`
would then give 1.00.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

# R-7, the default in numpy and in R alike.
PERCENTILE_METHOD = "linear"

# `NUMERIC(12,2)`, so two decimal places.
_STORED_PLACES = Decimal("0.01")


@dataclass(frozen=True)
class Percentiles:
    """Six statistics over one set of prices per square metre.

    The mean is here because FR-24 stores it. It is never the displayed figure —
    one far outlier moves it by hundreds and moves the median by seven.
    """

    n: int
    p25: float
    median: float
    p75: float
    minimum: float
    maximum: float
    mean: float


def quantile(ordered: list[float], fraction: float) -> float:
    """The R-7 quantile of an already sorted list."""
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (position - lower) * (ordered[upper] - ordered[lower])


def percentiles(values: Iterable[float]) -> Percentiles:
    """Every statistic over ``values``, unrounded.

    Raises ``ValueError`` on an empty input. Absence of data is absence; a zero
    here would reach the map as a price.
    """
    ordered = sorted(float(value) for value in values)
    if not ordered:
        raise ValueError("a percentile needs at least one observation")

    return Percentiles(
        n=len(ordered),
        p25=quantile(ordered, 0.25),
        median=quantile(ordered, 0.5),
        p75=quantile(ordered, 0.75),
        minimum=ordered[0],
        maximum=ordered[-1],
        mean=math.fsum(ordered) / len(ordered),
    )


def round_for_storage(value: float | Decimal) -> Decimal:
    """Round to the two places the column stores, half away from zero.

    The conversion goes through ``str`` on purpose. Building the ``Decimal`` from
    the binary float turns ``ROUND_HALF_UP`` into truncation on any value that is
    not exactly representable, which is most of them.
    """
    return Decimal(str(value)).quantize(_STORED_PLACES, rounding=ROUND_HALF_UP)
