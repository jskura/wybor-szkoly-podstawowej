"""U14 — the comparable set, listed before the verdict.

If the comparables look wrong to the reader, the verdict is wrong, and that is a
judgement a layperson can make even when pricing a plot is out of reach. So each
comparable states its price, area, gmina and date, and carries the control that
removes it.
"""

from __future__ import annotations

import datetime

from .contract import RenderNode
from .format import Formatter
from .price import check_one_price_kind, price_labels
from .state import Comparable, Payload, RenderConfig
from .wording import COMPARABLE, COMPARABLE_SET, EXCLUDE_CONTROL, NOTE_THIN_NARROW


def comparable_node(item: Comparable, *, formatter: Formatter) -> RenderNode:
    return RenderNode(
        role="comparable",
        text=COMPARABLE.format(
            price=formatter.format_ppm2(item.price_per_m2),
            area=formatter.format_area(item.area_m2),
            gmina=item.gmina,
            date=formatter.format_date(item.listed_on),
        ),
        prominence="equal",
        disclosure="always",
        children=price_labels(item.price_type, item.price_kind),
        meta={
            "comparable_id": item.comparable_id,
            "exclude_control": {
                "comparable_id": item.comparable_id,
                "label": EXCLUDE_CONTROL,
            },
            "price_type": item.price_type,
            "price_kind": item.price_kind,
            "as_of": item.listed_on,
        },
    )


def render_comparable_set(
    payload: Payload,
    *,
    config: RenderConfig,
    formatter: Formatter,
    now: datetime.date,
    prominence: str = "primary",
) -> RenderNode:
    """Every comparable, each with its own figures and its own control."""
    check_one_price_kind(item.price_kind for item in payload.comparables)
    children = [
        comparable_node(item, formatter=formatter) for item in payload.comparables
    ]
    if payload.n is not None and payload.n < config.thin_n_threshold:
        children.append(
            RenderNode(
                role="uncertainty_note",
                text=NOTE_THIN_NARROW,
                prominence="equal",
                disclosure="always",
                meta={"tone": "warning"},
            )
        )
    return RenderNode(
        role="comparable_set",
        text=COMPARABLE_SET.format(count=payload.n),
        prominence=prominence,
        disclosure="always",
        children=tuple(children),
        meta={"n": payload.n, "as_of": payload.as_of},
    )
