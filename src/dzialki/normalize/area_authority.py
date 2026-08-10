"""Which stated area wins, and what the losers said.

FR-15 is an authority rule, not a vote: register, then structured field, then
body, then title. Three advert sources agreeing against the register do not
outweigh it, and a more precise advert value does not either. Precision is not
authority.

The disagreement is kept. `candidates` carries every stated value, so the plot
page can render "ogłoszenie: 1200 m² · rejestr: 1450 m²" instead of showing one
number and hiding the other (rule 7).

D81 sets the conflict threshold at more than 5%, and D120 makes the register
area the denominator. The base matters at the boundary: 1260.01 is 5.0008% of
a register 1200 and 4.76% of itself.

The cost of 5%, recorded plainly: a real mismatch below it passes unflagged. On
a 1200 m² plot that is a silent gap of up to 60 m². The register value still
wins, so the stored area is right; only the flag is absent.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ..config import Params
from .units import AreaFailure, AreaParse, Confidence

AUTHORITY_ORDER = ("register", "structured", "body", "title")

# Percent to fraction. This is arithmetic, not a parameter: the ratified number
# is the percentage in `config/params.yml`.
_PERCENT = Decimal("100")  # noqa: FURB157 — see the note in `units.py`

Candidate = Decimal | AreaParse | None


class NoAreaStated(Exception):
    """No source stated an area, so the record cannot become a listing."""

    def __init__(self) -> None:
        super().__init__("no source stated an area")
        self.failure = AreaFailure.ABSENT


@dataclass(frozen=True)
class ConflictRule:
    """The D81 threshold and the D120 denominator, both read from the file."""

    threshold: Decimal
    base: str

    @classmethod
    def from_params(cls, params: Params) -> ConflictRule:
        base = params.validation.conflict_threshold_base
        if base != AUTHORITY_ORDER[0]:
            raise ValueError(
                f"conflict_threshold_base {base!r} has no implementation. "
                f"D120 fixed the denominator at {AUTHORITY_ORDER[0]!r}."
            )
        return cls(
            threshold=Decimal(params.validation.conflict_threshold_pct) / _PERCENT,
            base=base,
        )


@dataclass(frozen=True)
class ResolvedArea:
    m2: Decimal
    source: str
    conflict: bool
    candidates: dict[str, Decimal | None]
    confidence: Confidence


def _value(candidate: Candidate) -> Decimal | None:
    """A failed parse contributes no candidate, and costs only its own source."""
    if isinstance(candidate, AreaParse):
        return candidate.m2
    return candidate


def _confidence(candidate: Candidate) -> Confidence:
    if isinstance(candidate, AreaParse):
        return candidate.confidence
    return "high"


def resolve_area(
    register: Candidate,
    structured: Candidate,
    body: Candidate,
    title: Candidate,
    *,
    rule: ConflictRule,
) -> ResolvedArea:
    """Choose the authoritative area and record every value that lost."""
    given = dict(zip(AUTHORITY_ORDER, (register, structured, body, title)))
    candidates = {name: _value(value) for name, value in given.items()}

    winning_source = next(
        (name for name in AUTHORITY_ORDER if candidates[name] is not None), None
    )
    if winning_source is None:
        raise NoAreaStated()

    winner = candidates[winning_source]
    conflict = any(
        abs(other - winner) / winner > rule.threshold
        for name, other in candidates.items()
        if name != winning_source and other is not None
    )

    confidence = _confidence(given[winning_source])
    if winning_source == AUTHORITY_ORDER[-1]:
        # The title is the least trustworthy field. A value that wins from it
        # wins because nothing better exists, which is a lossy route (D87).
        confidence = "low"

    return ResolvedArea(
        m2=winner,
        source=winning_source,
        conflict=conflict,
        candidates=candidates,
        confidence=confidence,
    )
