"""The plot-check screen, assembled from the components.

The order is D98's: evidence, then unknowns, then the honest disclosure, then
the verdict — last, and shut. The verdict exists to be read after the
comparables, so nothing may follow it, not even a warning. A warning after the
conclusion is a footer, and a footer is not read.

This function composes; it bears no data of its own, which is why it is not a
registry component.
"""

from __future__ import annotations

import dataclasses
import datetime
from collections.abc import Mapping
from decimal import Decimal

from .absence import render_advert_claim, render_unknown
from .aggregate import gap_commentary, render_aggregate_block
from .comparables import render_comparable_set
from .contract import RenderNode
from .format import Formatter
from .header import render_plot_check_header
from .notes import notes_for
from .provenance import provenance_meta
from .state import Comparable, Payload, RenderConfig
from .uncertainty import is_out_of_depth, render_out_of_depth_notice
from .verdict import render_verdict_block
from .wording import HONEST_DISCLOSURE, NO_PLAN_CHECK, PLOT_CHECK


@dataclasses.dataclass(frozen=True)
class ScreenPayload:
    """Everything the plot-check screen draws, and nothing it computes."""

    subject_id: str
    subject: Payload
    flow: Payload
    stock: Payload
    gus: Payload
    comparables: tuple[Comparable, ...]
    unknown_fields: tuple[str, ...]
    stratum_gaps: Mapping[str, Decimal]
    zoning_claim: str | None = None


def assemble_plot_check(
    screen: ScreenPayload,
    *,
    config: RenderConfig,
    formatter: Formatter,
    now: datetime.date,
) -> RenderNode:
    """The whole screen, in the order D98 settles."""
    comparable_payload = dataclasses.replace(
        screen.flow, n=len(screen.comparables), comparables=screen.comparables
    )
    thin = is_out_of_depth(comparable_payload, config=config)
    evidence_prominence = "secondary" if thin else "primary"

    children: list[RenderNode] = []
    if thin:
        children.append(render_out_of_depth_notice())

    children.append(
        render_plot_check_header(
            screen.subject,
            config=config,
            formatter=formatter,
            now=now,
            prominence=evidence_prominence,
        )
    )
    for payload in (screen.flow, screen.stock):
        children.append(
            render_aggregate_block(
                payload,
                config=config,
                formatter=formatter,
                now=now,
                prominence=evidence_prominence,
            )
        )
    gap = gap_commentary(
        screen.flow.median,
        screen.stock.median,
        sources=screen.flow.sources,
        as_of=screen.flow.as_of,
        method_version=config.method_version,
        n=screen.flow.n + screen.stock.n,
    )
    if gap is not None:
        children.append(gap)
    children.append(
        render_aggregate_block(
            screen.gus,
            config=config,
            formatter=formatter,
            now=now,
            prominence=evidence_prominence,
        )
    )
    children.append(
        render_comparable_set(
            comparable_payload,
            config=config,
            formatter=formatter,
            now=now,
            prominence=evidence_prominence,
        )
    )

    children.append(
        RenderNode(
            role="unknown",
            text=NO_PLAN_CHECK,
            prominence="equal",
            disclosure="always",
            meta={"field": "buildability", "tone": "warning"},
        )
    )
    children.extend(render_unknown(field) for field in screen.unknown_fields)
    if screen.zoning_claim is not None:
        children.append(
            render_advert_claim(
                screen.zoning_claim,
                provenance=provenance_meta(
                    sources=screen.subject.sources,
                    as_of=screen.subject.as_of,
                    method_version=config.method_version,
                    n=1,
                ),
                as_of=screen.subject.as_of,
            )
        )
    children.extend(
        notes_for(
            screen.unknown_fields,
            gmina=screen.subject.gmina,
            stratum_gaps=screen.stratum_gaps,
        )
    )
    children.append(
        RenderNode(
            role="disclosure_banner",
            text=HONEST_DISCLOSURE,
            prominence="equal",
            disclosure="always",
        )
    )
    children.append(
        render_verdict_block(
            dataclasses.replace(
                screen.flow,
                price_per_m2=screen.subject.price_per_m2,
                area_m2=screen.subject.area_m2,
            ),
            config=config,
            formatter=formatter,
            now=now,
        )
    )

    return RenderNode(
        role="section",
        text=PLOT_CHECK,
        prominence="primary",
        disclosure="always",
        children=tuple(children),
        meta={
            "component": "plot_check",
            "state": "thin" if thin else "normal",
            "subject_id": screen.subject_id,
        },
    )
