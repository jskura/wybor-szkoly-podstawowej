"""Choosing the comparable set. The only source of a verdict.

Four filters, and one of them is never relaxed.

**Buildability is matched exactly.** Relaxing it would be the easiest way to find
more comparables and the fastest way to make the number meaningless: a plot you
may build on and a plot you may not are different goods at the same size in the
same gmina. Every other filter has a widening story; this one has none.

**v0 does not widen at all.** D109 sets the minimum at three comparables, and the
ladder that acts on it is out of v0 scope and unratified besides (O41). So a thin
set stays thin and says so, and an empty set returns an absence rather than
reaching into the next gmina. A number borrowed from somewhere else, unlabelled,
is worse than no number.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal

WIDENING_STEP_GMINA = "gmina"

# Months carry no fixed length, so the recency cutoff is computed by walking
# back whole months rather than by subtracting a day count. Twelve times thirty
# days is eleven months and twenty-five days, which would silently drop a week
# of observations every year.
DAYS_PER_MONTH_IS_NOT_FIXED = True


@dataclass(frozen=True)
class Subject:
    """The plot being valued."""

    area_m2: Decimal
    teryt_gmina: str
    asset_class: str
    buildability: str
    price_type: str = "offering"
    price_kind: str = "asking"


@dataclass(frozen=True)
class Candidate:
    """One observation that might belong in the set."""

    listing_id: int
    area_m2: Decimal
    teryt_gmina: str
    asset_class: str
    buildability: str
    price_per_m2: Decimal
    observed_at: dt.date
    price_type: str = "offering"
    price_kind: str = "asking"


@dataclass(frozen=True)
class ComparableSet:
    members: tuple[Candidate, ...]
    widening_step: str
    band_low: Decimal
    band_high: Decimal

    @property
    def n(self) -> int:
        return len(self.members)

    @property
    def values(self) -> list[Decimal]:
        return [member.price_per_m2 for member in self.members]


def area_band(area_m2: Decimal, *, band_pct: int) -> tuple[Decimal, Decimal]:
    """The ±band around the subject's area (D108). Both bounds inclusive."""
    fraction = Decimal(band_pct) / Decimal(100)
    return (area_m2 * (1 - fraction), area_m2 * (1 + fraction))


def recency_cutoff(as_of: dt.date, *, months: int) -> dt.date:
    """The earliest observation date still inside the window (D110)."""
    year = as_of.year - (months // 12)
    month = as_of.month - (months % 12)
    if month <= 0:
        month += 12
        year -= 1
    day = min(as_of.day, 28)  # never lands on a month that lacks the day
    return dt.date(year, month, day)


def select_comparables(
    subject: Subject,
    candidates: list[Candidate],
    *,
    as_of: dt.date,
    band_pct: int,
    recency_months: int,
) -> ComparableSet:
    """Every candidate that matches the subject on all four axes."""
    low, high = area_band(subject.area_m2, band_pct=band_pct)
    cutoff = recency_cutoff(as_of, months=recency_months)

    members = [
        candidate
        for candidate in candidates
        if candidate.teryt_gmina == subject.teryt_gmina
        and candidate.asset_class == subject.asset_class
        # Never relaxed. See the module docstring.
        and candidate.buildability == subject.buildability
        and candidate.price_type == subject.price_type
        and candidate.price_kind == subject.price_kind
        and low <= candidate.area_m2 <= high
        and cutoff <= candidate.observed_at <= as_of
    ]
    members.sort(key=lambda candidate: (candidate.price_per_m2, candidate.listing_id))
    return ComparableSet(
        members=tuple(members),
        widening_step=WIDENING_STEP_GMINA,
        band_low=low,
        band_high=high,
    )
