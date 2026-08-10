"""Which gmina owns a parcel that crosses a boundary.

The majority share decides. A 50/50 split has no majority, and D123 breaks the
tie on the **lowest TERYT code**. That is arbitrary, and deliberately so: the
requirement is a total order, so the same parcel gives the same answer on every
run. A tie left undefined would let the answer follow whatever order the database
happened to return rows in, and change between runs for no visible reason.

The caller shows both gminas and says which one the figures came from. The
tie-break decides the number; it does not hide the straddle.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GminaShare:
    teryt: str
    area_m2: float


@dataclass(frozen=True)
class Ownership:
    """Which gmina's figures apply, and whether the answer was close."""

    teryt: str
    shares: tuple[GminaShare, ...]
    was_tie: bool


def owning_gmina(shares: list[GminaShare]) -> Ownership:
    """Pick the owning gmina from the overlap areas.

    Raises ``ValueError`` on an empty list: a parcel that overlaps no gmina is a
    geometry problem, and returning a default would bury it.
    """
    if not shares:
        raise ValueError("a parcel must overlap at least one gmina")

    ordered = sorted(shares, key=lambda share: (-share.area_m2, share.teryt))
    largest = ordered[0].area_m2
    tied = [share for share in ordered if share.area_m2 == largest]
    return Ownership(
        teryt=tied[0].teryt,  # already the lowest TERYT among the tied
        shares=tuple(ordered),
        was_tie=len(tied) > 1,
    )
