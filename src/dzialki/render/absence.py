"""U6 and U7 — nothing renders blank, and no two absences share one sentence.

A blank reads as "nothing to worry about". A shared "Brak danych" reads as one
fact when it is four, and the four imply four different next actions: wait,
look elsewhere, accept the tool cannot help, or widen the search.

A reason outside the four raises. Without that, the four collapse back into one
the first time a fifth appears.
"""

from __future__ import annotations

from .contract import RenderNode
from .errors import UnknownAbsenceReasonError, UnknownFieldError
from .wording import ABSENCE_ACTIONS, ABSENCE_TEXTS, FROM_THE_ADVERT, UNKNOWN_TEXTS

ABSENCE_REASONS: tuple[str, ...] = (
    "not_yet_crawled",
    "no_listings",
    "out_of_scope",
    "too_few_comparables",
)

UNKNOWN_FIELDS: tuple[str, ...] = tuple(UNKNOWN_TEXTS)


def render_absence(reason: str) -> RenderNode:
    """The absence, and the one action it implies, as its child."""
    if reason not in ABSENCE_REASONS:
        raise UnknownAbsenceReasonError(
            f"absence reason {reason!r} is outside the four the surface renders"
        )
    action = RenderNode(
        role="basis",
        text=ABSENCE_ACTIONS[reason],
        prominence="equal",
        disclosure="always",
        meta={"absence_reason": reason},
    )
    return RenderNode(
        role="absence",
        text=ABSENCE_TEXTS[reason],
        prominence="equal",
        disclosure="always",
        children=(action,),
        meta={"absence_reason": reason, "tone": "warning"},
    )


def render_unknown(field: str) -> RenderNode:
    """One sentence per attribute, so three unknowns stay three sentences."""
    if field not in UNKNOWN_TEXTS:
        raise UnknownFieldError(f"the attribute {field!r} has no written sentence")
    return RenderNode(
        role="unknown",
        text=UNKNOWN_TEXTS[field],
        prominence="equal",
        disclosure="always",
        meta={"field": field, "tone": "warning"},
    )


def render_advert_claim(claim: str, *, provenance, as_of) -> RenderNode:
    """What the advert says, labelled as such.

    ``zoning_claim`` and ``buildability`` are different columns and are never
    reconciled (FR-17). The claim renders beside the unknown, never instead.
    """
    return RenderNode(
        role="value",
        text=claim,
        prominence="equal",
        disclosure="always",
        children=(
            RenderNode(
                role="basis",
                text=FROM_THE_ADVERT,
                prominence="equal",
                disclosure="always",
            ),
        ),
        meta={"field": "zoning_claim", "provenance": provenance, "as_of": as_of},
    )
