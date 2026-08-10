"""U9 — every number is one interaction from its source, date and method.

One interaction, not two. Provenance behind a second expander is provenance
nobody opens, and provenance on hover is unreachable on a touch device and
cannot be put in a screenshot. So the panel is an expander, and everything
inside it is ``always``.
"""

from __future__ import annotations

import datetime
from collections.abc import Mapping

from .contract import RenderNode
from .format import Formatter
from .state import Payload, RenderConfig
from .wording import (
    PROVENANCE,
    PROVENANCE_AS_OF,
    PROVENANCE_METHOD,
    PROVENANCE_N,
    PROVENANCE_SOURCE,
)


def provenance_meta(
    *,
    sources: tuple[str, ...],
    as_of: datetime.date | None,
    method_version: str,
    n: int,
) -> Mapping[str, object]:
    """The handle every ``value`` node carries."""
    return {
        "source": tuple(sources),
        "as_of": as_of,
        "method_version": method_version,
        "n": n,
    }


def provenance_node(
    *,
    sources: tuple[str, ...],
    as_of: datetime.date | None,
    method_version: str,
    n: int,
    formatter: Formatter,
) -> RenderNode:
    """The panel, one expander deep, listing every contributing source."""
    handle = provenance_meta(
        sources=sources, as_of=as_of, method_version=method_version, n=n
    )
    lines = (
        PROVENANCE_SOURCE.format(sources=", ".join(sources)),
        PROVENANCE_AS_OF.format(date=formatter.format_date(as_of)),
        PROVENANCE_METHOD.format(method_version=method_version),
        PROVENANCE_N.format(n=n),
    )
    return RenderNode(
        role="provenance",
        text=PROVENANCE,
        prominence="equal",
        disclosure="expander",
        children=tuple(
            RenderNode(
                role="value",
                text=line,
                prominence="equal",
                disclosure="always",
                meta={"provenance": handle},
            )
            for line in lines
        ),
    )


def render_provenance_panel(
    payload: Payload,
    *,
    config: RenderConfig,
    formatter: Formatter,
    now: datetime.date,
) -> RenderNode:
    """The provenance panel as a component in its own right."""
    return provenance_node(
        sources=payload.sources,
        as_of=payload.as_of,
        method_version=config.method_version,
        n=payload.n,
        formatter=formatter,
    )
