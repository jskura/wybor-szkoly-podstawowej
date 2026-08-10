"""The plot-check header — what the reader pasted, read back with its labels.

The header carries no range of its own, so its thin note reads "few comparable
offers" rather than "wide range". The two sentences answer different questions
and the header can only answer one of them.
"""

from __future__ import annotations

import datetime

from .contract import RenderNode
from .format import Formatter
from .price import render_price
from .provenance import provenance_meta
from .state import Payload, RenderConfig
from .wording import HEADER, NOTE_THIN_NARROW

# Every figure in the header comes from the one listing the reader pasted.
LISTING_OBSERVATIONS = 1


def render_plot_check_header(
    payload: Payload,
    *,
    config: RenderConfig,
    formatter: Formatter,
    now: datetime.date,
    prominence: str = "primary",
) -> RenderNode:
    """Area, gmina and price per m², each labelled with where it came from."""
    from .aggregate import staleness_node

    handle = provenance_meta(
        sources=payload.sources,
        as_of=payload.as_of,
        method_version=config.method_version,
        n=LISTING_OBSERVATIONS,
    )
    area = formatter.format_area(payload.area_m2)
    price = formatter.format_ppm2(payload.price_per_m2)

    children: list[RenderNode] = [
        RenderNode(
            role="value",
            text=area,
            prominence="equal",
            disclosure="always",
            meta={"field": "area_m2", "as_of": payload.as_of, "provenance": handle},
        ),
        RenderNode(
            role="basis",
            text=f"gmina {payload.gmina}",
            prominence="equal",
            disclosure="always",
            meta={"field": "teryt", "teryt": payload.teryt},
        ),
        *render_price(
            payload.price_per_m2,
            price_type=payload.price_type,
            price_kind=payload.price_kind,
            formatter=formatter,
            field="price_per_m2",
            provenance=handle,
            as_of=payload.as_of,
        ),
        RenderNode(
            role="value",
            text=formatter.format_pln(payload.price_pln),
            prominence="equal",
            disclosure="always",
            meta={"field": "price_pln", "as_of": payload.as_of, "provenance": handle},
        ),
    ]
    stale = staleness_node(payload, config=config, formatter=formatter, now=now)
    if stale is not None:
        children.insert(1, stale)
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
        role="header",
        text=HEADER.format(area=area, gmina=payload.gmina, price=price),
        prominence=prominence,
        disclosure="always",
        children=tuple(children),
        meta={
            "n": payload.n,
            "as_of": payload.as_of,
            "price_type": payload.price_type,
            "price_kind": payload.price_kind,
        },
    )
