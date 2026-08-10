"""U2 — a price renders with its type and its kind, or it does not render.

An auction start price beside an asking price, both unlabelled, is not a
cosmetic problem: the two answer different questions and the reader cannot tell
which one is on screen. So the labels are siblings of the price, never a
tooltip, and a payload without them raises.

D68 fixes the legal pairs. ``transaction`` belongs to ``sales`` and to nothing
else; the three offering kinds belong to ``offering``. Rule 6 is untouched —
``price_type`` still separates offering from sales, and ``price_kind`` is the
finer axis inside each.
"""

from __future__ import annotations

from decimal import Decimal

from .contract import RenderNode
from .errors import (
    IllegalPriceCombinationError,
    MixedPriceKindError,
    UnlabelledPriceError,
)
from .format import Formatter
from .wording import PRICE_KIND_LABELS, PRICE_TYPE_LABELS

TYPE_LABELS = PRICE_TYPE_LABELS
KIND_LABELS = PRICE_KIND_LABELS

LEGAL_PRICE_PAIRS: tuple[tuple[str, str], ...] = (
    ("offering", "asking"),
    ("offering", "auction_start"),
    ("offering", "tender"),
    ("sales", "transaction"),
)


def check_price_pair(price_type: str | None, price_kind: str | None) -> None:
    """Refuse an unlabelled price, and refuse an illegal pair (D68)."""
    if price_type is None:
        raise UnlabelledPriceError("a price with no price_type does not render")
    if price_kind is None:
        raise UnlabelledPriceError("a price with no price_kind does not render")
    if price_type not in TYPE_LABELS:
        raise IllegalPriceCombinationError(f"price_type {price_type!r} is unknown")
    if price_kind not in KIND_LABELS:
        raise IllegalPriceCombinationError(f"price_kind {price_kind!r} is unknown")
    if (price_type, price_kind) not in LEGAL_PRICE_PAIRS:
        raise IllegalPriceCombinationError(
            f"price_kind {price_kind!r} is not legal with price_type {price_type!r}"
        )


def check_one_price_kind(kinds) -> None:
    """One aggregate, one price kind. The render half of F9's detector."""
    distinct = sorted(set(kinds))
    if len(distinct) > 1:
        raise MixedPriceKindError(
            f"an aggregate spans the price kinds {', '.join(distinct)}"
        )


def price_labels(price_type: str, price_kind: str) -> tuple[RenderNode, RenderNode]:
    """The two label nodes, always siblings of the price they describe."""
    return (
        RenderNode(
            role="price_type_label",
            text=TYPE_LABELS[price_type],
            prominence="equal",
            disclosure="always",
            meta={"price_type": price_type},
        ),
        RenderNode(
            role="price_kind_label",
            text=KIND_LABELS[price_kind],
            prominence="equal",
            disclosure="always",
            meta={"price_kind": price_kind},
        ),
    )


def render_price(
    value: Decimal,
    *,
    price_type: str | None,
    price_kind: str | None,
    formatter: Formatter,
    field: str | None = None,
    provenance=None,
    as_of=None,
    prominence: str = "equal",
) -> tuple[RenderNode, ...]:
    """The price node and its two labels, in that order."""
    check_price_pair(price_type, price_kind)
    meta: dict[str, object] = {"price_type": price_type, "price_kind": price_kind}
    if field is not None:
        meta["field"] = field
    if provenance is not None:
        meta["provenance"] = provenance
    if as_of is not None:
        meta["as_of"] = as_of
    price = RenderNode(
        role="price",
        text=formatter.format_ppm2(value),
        prominence=prominence,
        disclosure="always",
        meta=meta,
    )
    return (price, *price_labels(price_type, price_kind))
