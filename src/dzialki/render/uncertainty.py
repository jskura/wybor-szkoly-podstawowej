"""U10 and U11 — uncertainty in words, and the admission that leads.

A range is legible only to a reader who already has a prior, and the reader this
product is for does not have one (D63). So the range is stated and then said in
words.

Below the comparable threshold the tool says so first, in its own sentence, and
demotes everything else. Silence would read as confidence.
"""

from __future__ import annotations

import datetime

from .aggregate import staleness_node, uncertainty_note_text
from .contract import RenderNode
from .format import Formatter
from .state import Payload, RenderConfig
from .wording import OUT_OF_DEPTH, UNCERTAINTY_BASIS, UNCERTAINTY_PANEL


def is_out_of_depth(payload: Payload, *, config: RenderConfig) -> bool:
    if payload.n is None:
        return True
    return payload.n < config.out_of_depth_min_comparables


def render_out_of_depth_notice(prominence: str = "primary") -> RenderNode:
    """The sentence that leads a thin screen."""
    return RenderNode(
        role="out_of_depth_notice",
        text=OUT_OF_DEPTH,
        prominence=prominence,
        disclosure="always",
        meta={"tone": "warning"},
    )


def render_uncertainty_panel(
    payload: Payload,
    *,
    config: RenderConfig,
    formatter: Formatter,
    now: datetime.date,
    prominence: str = "primary",
) -> RenderNode:
    """What the tool thinks of its own answer, said in words."""
    from .aggregate import flow_window_text

    children: list[RenderNode] = []
    if is_out_of_depth(payload, config=config):
        children.append(render_out_of_depth_notice("equal"))
    note = uncertainty_note_text(payload, config=config)
    if note is not None:
        children.append(
            RenderNode(
                role="uncertainty_note",
                text=note,
                prominence="equal",
                disclosure="always",
                meta={"tone": "warning"},
            )
        )
    children.append(
        RenderNode(
            role="basis",
            text=UNCERTAINTY_BASIS.format(
                offers=formatter.format_offers(payload.n),
                window=flow_window_text(config, formatter),
            ),
            prominence="equal",
            disclosure="always",
            meta={"basis": payload.basis, "n": payload.n},
        )
    )
    children.append(
        RenderNode(
            role="flow_window_label",
            text=flow_window_text(config, formatter),
            prominence="equal",
            disclosure="always",
            meta={"flow_window_days": config.flow_window_days},
        )
    )
    stale = staleness_node(payload, config=config, formatter=formatter, now=now)
    if stale is not None:
        children.append(stale)

    return RenderNode(
        role="section",
        text=UNCERTAINTY_PANEL,
        prominence=prominence,
        disclosure="always",
        children=tuple(children),
        meta={"n": payload.n, "as_of": payload.as_of},
    )
