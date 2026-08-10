"""The caps, applied outside the table.

Three modifiers exist and they are not axes.

**M0 — staleness.** A coverage record older than the configured maximum rewrites
the coverage axis to `absent` **before** the table is consulted. That ordering is
load-bearing: a stale record must be able to turn `unlikely` into `unknown`, and
a cap applied afterwards could not, because a cap never touches `unlikely`. M0
lives in the coverage probe, which is where the record is read.

**M1 — source.** A neighbour seen only in OSM caps the verdict. OSM building
coverage is hobby-mapped and uneven, and an optimistic answer off it reads
exactly like an optimistic answer off the register.

**M2 — protection.** Any overlap with a protected area of any kind caps the
verdict. Protection changes the procedure; it does not forbid building, and
saying otherwise is the overreach `19` §1.2 rules out.

On the ordering `likely > uncertain > unlikely`, a cap replaces the verdict with
`uncertain` **only when the verdict is `likely`**. It never touches `unlikely` and
never touches `unknown`. So the caps commute, they are idempotent, and no
sequence of them ever makes a verdict more optimistic.
"""

from __future__ import annotations

CAPPED_VERDICT = "likely"
CAP_RESULT = "uncertain"

# `unknown` sits below the scale rather than on it: it is not a pessimistic
# answer, it is the absence of one. Putting it at the bottom is what makes "no
# modifier ever raises a verdict" a single comparison.
OPTIMISM: dict[str, int] = {
    "unknown": 0,
    "unlikely": 1,
    "uncertain": 2,
    "likely": 3,
}


def cap(verdict: str) -> str:
    """Lower `likely` to `uncertain`. Leave every other verdict alone."""
    return CAP_RESULT if verdict == CAPPED_VERDICT else verdict


def apply_caps(
    verdict: str, *, osm_source: bool, protected: bool
) -> tuple[str, tuple[str, ...]]:
    """Apply M1 and M2, and name the caps that fired.

    A cap that fires on a verdict it cannot lower still names itself, because the
    reader needs to know the evidence was weak whether or not it changed the
    answer. A cap that did not fire names nothing.
    """
    reasons: list[str] = []
    result = verdict
    if osm_source:
        reasons.append("capped_by_osm_source")
        result = cap(result)
    if protected:
        reasons.append("capped_by_protection")
        result = cap(result)
    if result == verdict:
        return verdict, ()
    return result, tuple(reasons)
