"""The spread beside every number, and which range the interface shows.

Rule 7 is *always show, always flag*. An aggregate over four observations is
still published; it is published with its sample size and its range, so that thin
evidence looks thin. Nothing here suppresses a figure at any sample size.

Which range shows depends on the sample size. Below the threshold an
interquartile range over four points says less than the min and the max, so the
min and the max show. At and above it the interquartile range is the better
summary. Both are stored either way — only the displayed pair switches.

**The threshold is a parameter, not a constant.** D67 moved it out of the
database for that reason, and it stays out of this module too: every function
below takes it as an argument, sourced from `config/params.yml`. A copy here
would not follow a change to the file that holds it.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from .percentiles import percentiles, round_for_storage

IQR = "iqr"
MIN_MAX = "min_max"
# D69. GUS publishes a central value and no spread. Saying so is rule 7; showing
# a blank is not.
UNAVAILABLE = "unavailable"

RANGE_KINDS = frozenset({IQR, MIN_MAX, UNAVAILABLE})


def range_kind_for(n: int, *, iqr_switch_n: int) -> str:
    """Which range a sample of ``n`` observations shows.

    ``iqr_switch_n`` comes from `config/params.yml` (D67). Changing it is one
    edit, not an audit of every call site.
    """
    if n < 1:
        raise ValueError("a spread needs at least one observation")
    return IQR if n >= iqr_switch_n else MIN_MAX


@dataclass(frozen=True)
class Spread:
    """The stored statistics and the label saying which range to display.

    No field has a default. A bare median must be unconstructible, not merely
    untested — rule 7 made structural rather than remembered.
    """

    n: int
    median_ppm2: Decimal
    p25_ppm2: Decimal | None
    p75_ppm2: Decimal | None
    min_ppm2: Decimal | None
    max_ppm2: Decimal | None
    mean_ppm2: Decimal | None
    range_kind: str

    def __post_init__(self) -> None:
        if self.range_kind not in RANGE_KINDS:
            raise ValueError(f"{self.range_kind!r} is not a range kind")
        if self.n < 1:
            raise ValueError("an aggregate of no observations is an absence")

    @property
    def low(self) -> Decimal | None:
        if self.range_kind == UNAVAILABLE:
            return None
        return self.p25_ppm2 if self.range_kind == IQR else self.min_ppm2

    @property
    def high(self) -> Decimal | None:
        if self.range_kind == UNAVAILABLE:
            return None
        return self.p75_ppm2 if self.range_kind == IQR else self.max_ppm2

    def as_displayed(self) -> dict[str, object]:
        """What the interface needs, with the absent range still named.

        `low` and `high` stay in the mapping when they are ``None``. A dropped
        field reads as a bug in the reader; a present ``None`` beside
        ``range_kind = 'unavailable'`` reads as the source publishing no spread.
        """
        return {
            "n": self.n,
            "median_ppm2": self.median_ppm2,
            "range_kind": self.range_kind,
            "low": self.low,
            "high": self.high,
        }


def spread_from_values(values: Iterable[float], *, iqr_switch_n: int) -> Spread:
    """Summarise prices per square metre into one stored spread."""
    computed = percentiles(values)
    return Spread(
        n=computed.n,
        median_ppm2=round_for_storage(computed.median),
        p25_ppm2=round_for_storage(computed.p25),
        p75_ppm2=round_for_storage(computed.p75),
        min_ppm2=round_for_storage(computed.minimum),
        max_ppm2=round_for_storage(computed.maximum),
        mean_ppm2=round_for_storage(computed.mean),
        range_kind=range_kind_for(computed.n, iqr_switch_n=iqr_switch_n),
    )


def spread_from_central_value(median_ppm2: Decimal, *, n: int) -> Spread:
    """A source that publishes a central value and no spread (D69).

    Every bound is ``None``, including the mean, because the source publishes
    none of them. Inventing one would be worse than the absence: it would look
    like evidence.
    """
    return Spread(
        n=n,
        median_ppm2=round_for_storage(median_ppm2),
        p25_ppm2=None,
        p75_ppm2=None,
        min_ppm2=None,
        max_ppm2=None,
        mean_ppm2=None,
        range_kind=UNAVAILABLE,
    )
