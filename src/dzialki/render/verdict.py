"""U5 — the verdict, phrased against the range and shut until asked for.

The verdict is collapsed so the evidence is read first, and it is last on the
screen so nothing follows the conclusion (D98). Its own text is one word, so a
reader who never expands it learns nothing they have not earned.

It is never a percentage off a midpoint. A midpoint is a point estimate wearing
a range's clothes, and the whole product refuses point estimates.
"""

from __future__ import annotations

import datetime

from .contract import RenderNode
from .format import Formatter
from .provenance import provenance_meta
from .state import Payload, RenderConfig, area_band
from .wording import (
    VERDICT,
    VERDICT_ABOVE,
    VERDICT_BASIS,
    VERDICT_BELOW,
    VERDICT_WITHIN,
)


def verdict_text(payload: Payload, *, formatter: Formatter) -> str:
    """One of three sanctioned forms, each naming the range it judges against."""
    rendered = formatter.format_range(payload.low, payload.high)
    if payload.price_per_m2 > payload.high:
        return VERDICT_ABOVE.format(range=rendered)
    if payload.price_per_m2 < payload.low:
        return VERDICT_BELOW.format(range=rendered)
    return VERDICT_WITHIN.format(range=rendered)


def verdict_basis_text(
    payload: Payload, *, config: RenderConfig, formatter: Formatter
) -> str:
    from .aggregate import flow_window_text

    low, high = area_band(payload.area_m2, config=config)
    return VERDICT_BASIS.format(
        offers=formatter.format_offers(payload.n),
        band=formatter.join_unit(formatter.format_range(low, high), "m²"),
        window=flow_window_text(config, formatter),
    )


def render_verdict_block(
    payload: Payload,
    *,
    config: RenderConfig,
    formatter: Formatter,
    now: datetime.date,
    prominence: str = "secondary",
) -> RenderNode:
    """The collapsed bar, with the conclusion and its basis inside it."""
    from .aggregate import flow_window_text, staleness_node

    handle = provenance_meta(
        sources=payload.sources,
        as_of=payload.as_of,
        method_version=config.method_version,
        n=payload.n,
    )
    children: list[RenderNode] = [
        RenderNode(
            role="value",
            text=verdict_text(payload, formatter=formatter),
            prominence="equal",
            disclosure="always",
            meta={
                "basis": payload.basis,
                "as_of": payload.as_of,
                "provenance": handle,
            },
        ),
        RenderNode(
            role="basis",
            text=verdict_basis_text(payload, config=config, formatter=formatter),
            prominence="equal",
            disclosure="always",
            meta={
                "basis": payload.basis,
                "flow_window_days": config.flow_window_days,
                "n": payload.n,
            },
        ),
        RenderNode(
            role="flow_window_label",
            text=flow_window_text(config, formatter),
            prominence="equal",
            disclosure="always",
            meta={"flow_window_days": config.flow_window_days},
        ),
    ]
    stale = staleness_node(payload, config=config, formatter=formatter, now=now)
    if stale is not None:
        children.append(stale)

    return RenderNode(
        role="verdict",
        text=VERDICT,
        prominence=prominence,
        disclosure="expander",
        children=tuple(children),
        meta={"expanded": False},
    )
