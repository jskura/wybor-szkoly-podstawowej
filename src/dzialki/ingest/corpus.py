"""Does our corpus agree with what the source says it holds?

A crawl that silently collects half a market produces medians that look
healthy. The source usually states its own result count, so the cheapest
detector is to compare ours against theirs on every run.

Two rules keep the alarm worth reading. The allowance is **the larger of a fixed
number of listings or a percentage** (D95) — two percent of a twenty-result query
is less than one listing, so a percentage alone would fire on a corpus that is
exactly right. And an **approximate** stated total is reported, never blocking
(D96): a source saying "about 1 200" has not promised 1 200, and an alarm that
cries wolf trains the reader to ignore it.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

# A stated total is approximate when the page hedges it. These are the hedges a
# Polish results page uses.
APPROXIMATE_MARKERS = ("około", "ok.", "ponad", "blisko", "~")

_DIGITS = re.compile(r"\d[\d\s  ]*")


@dataclass(frozen=True)
class StatedTotal:
    value: int
    approximate: bool


@dataclass(frozen=True)
class Agreement:
    collected: int
    stated: StatedTotal
    allowance: int
    agrees: bool
    blocking: bool
    reason: str | None = None


def parse_stated_total(text: str) -> StatedTotal:
    """Read a results count, and whether the page hedged it."""
    found = _DIGITS.search(text)
    if not found:
        raise ValueError(f"no count in {text!r}")
    digits = re.sub(r"[\s  ]", "", found.group())
    lowered = text.lower()
    return StatedTotal(
        value=int(digits),
        approximate=any(marker in lowered for marker in APPROXIMATE_MARKERS),
    )


def allowance_for(stated: int, *, abs_listings: int, pct: int) -> int:
    """The larger of the two allowances (D95).

    The absolute floor exists because a percentage of a small query rounds below
    one listing, and an allowance under one listing can never be met.
    """
    return max(abs_listings, math.ceil(stated * pct / 100))


def check(
    *, collected: int, stated_text: str, abs_listings: int, pct: int
) -> Agreement:
    """Compare our corpus against the source's own total."""
    stated = parse_stated_total(stated_text)
    allowance = allowance_for(stated.value, abs_listings=abs_listings, pct=pct)
    agrees = abs(collected - stated.value) <= allowance

    if stated.approximate:
        # D96. Rounding is not a shortfall, and blocking on one would stop a
        # healthy run because a page said "about".
        return Agreement(
            collected=collected,
            stated=stated,
            allowance=allowance,
            agrees=agrees,
            blocking=False,
            reason="stated total is approximate — reported only",
        )

    return Agreement(
        collected=collected,
        stated=stated,
        allowance=allowance,
        agrees=agrees,
        blocking=not agrees,
        reason=None if agrees else "corpus disagrees with the stated total",
    )
