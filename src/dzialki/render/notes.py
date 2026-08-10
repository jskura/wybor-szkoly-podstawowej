"""U13 — what would change the answer.

An abstract caveat teaches nothing. "Gdyby ta działka miała plan miejscowy,
porównania byłyby inne" turns an unknown into a question the reader can take to
the gmina office, and it names the office and the document to ask for.

The notes are derived from the subject's own missing attributes. A note that
appears whatever the subject is is a constant, and a constant is ignored.
"""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal

from .contract import RenderNode
from .errors import UnknownFieldError
from .wording import BINDING_DOCUMENT, GMINA_OFFICE, SENSITIVITY_TEXTS

# Where no stratum gap is supplied, this is the order the notes take. It is the
# order of the gaps measured on the labelled set, largest first.
DEFAULT_ORDER: tuple[str, ...] = ("buildability", "road_access", "utilities")


def notes_for(
    unknown_fields,
    *,
    gmina: str,
    stratum_gaps: Mapping[str, Decimal] | None = None,
) -> tuple[RenderNode, ...]:
    """One note per missing attribute, largest difference first."""
    fields = tuple(unknown_fields)
    for field in fields:
        if field not in SENSITIVITY_TEXTS:
            raise UnknownFieldError(f"the attribute {field!r} has no written note")

    def rank(field: str) -> tuple[Decimal, int]:
        gap = (stratum_gaps or {}).get(field)
        position = (
            DEFAULT_ORDER.index(field) if field in DEFAULT_ORDER else len(DEFAULT_ORDER)
        )
        return (-(gap if gap is not None else Decimal(0)), position)

    return tuple(
        RenderNode(
            role="sensitivity_note",
            text=SENSITIVITY_TEXTS[field],
            prominence="equal",
            disclosure="always",
            meta={
                "field": field,
                "action": {
                    "office": GMINA_OFFICE.format(gmina=gmina),
                    "document": BINDING_DOCUMENT,
                },
            },
        )
        for field in sorted(fields, key=rank)
    )
