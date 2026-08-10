"""The component registry — the sweep's source of truth.

Every data-bearing component is named here with the copy its non-normal states
use. A component outside the registry ships outside every sweep, which is how
the honesty rules would erode one helper at a time; the completeness test reads
this file against the builders that exist.

A component builder is recognised structurally: a module-level function whose
name starts with ``render_`` and whose first parameter is named ``payload``.
Helpers that render a fragment take their fragment, not a payload, so the two
kinds cannot be confused.
"""

from __future__ import annotations

import dataclasses
import datetime
import inspect
from collections.abc import Callable

from . import (
    absence as absence_module,
)
from . import (
    aggregate as aggregate_module,
)
from . import (
    comparables as comparables_module,
)
from . import (
    header as header_module,
)
from . import (
    notes as notes_module,
)
from . import (
    price as price_module,
)
from . import (
    provenance as provenance_module,
)
from . import (
    screen as screen_module,
)
from . import (
    uncertainty as uncertainty_module,
)
from . import (
    verdict as verdict_module,
)
from .absence import render_absence
from .aggregate import block_heading, render_aggregate_block
from .comparables import render_comparable_set
from .contract import RenderNode
from .format import Formatter
from .header import render_plot_check_header
from .provenance import render_provenance_panel
from .state import Payload, RenderConfig, state_of
from .uncertainty import render_uncertainty_panel
from .verdict import render_verdict_block
from .wording import (
    COMPARABLE_SET_HEADING,
    ERROR_TEXTS,
    LOADING_TEXTS,
    PLOT_CHECK,
    PROVENANCE,
    UNCERTAINTY_PANEL,
    VERDICT,
)

_MODULES = (
    absence_module,
    aggregate_module,
    comparables_module,
    header_module,
    notes_module,
    price_module,
    provenance_module,
    screen_module,
    uncertainty_module,
    verdict_module,
)


@dataclasses.dataclass(frozen=True)
class Component:
    """One registered component, with the copy its five states need."""

    name: str
    builder: Callable[..., RenderNode]
    root_role: str
    root_disclosure: str
    empty_reason: str


COMPONENT_REGISTRY: dict[str, Component] = {
    "plot_check_header": Component(
        name="plot_check_header",
        builder=render_plot_check_header,
        root_role="header",
        root_disclosure="always",
        empty_reason="out_of_scope",
    ),
    "flow_aggregate_block": Component(
        name="flow_aggregate_block",
        builder=render_aggregate_block,
        root_role="aggregate_block",
        root_disclosure="always",
        empty_reason="not_yet_crawled",
    ),
    "stock_aggregate_block": Component(
        name="stock_aggregate_block",
        builder=render_aggregate_block,
        root_role="aggregate_block",
        root_disclosure="always",
        empty_reason="no_listings",
    ),
    "gus_sales_block": Component(
        name="gus_sales_block",
        builder=render_aggregate_block,
        root_role="aggregate_block",
        root_disclosure="always",
        empty_reason="not_yet_crawled",
    ),
    "comparable_set": Component(
        name="comparable_set",
        builder=render_comparable_set,
        root_role="comparable_set",
        root_disclosure="always",
        empty_reason="no_listings",
    ),
    "verdict_block": Component(
        name="verdict_block",
        builder=render_verdict_block,
        root_role="verdict",
        root_disclosure="expander",
        empty_reason="too_few_comparables",
    ),
    "uncertainty_panel": Component(
        name="uncertainty_panel",
        builder=render_uncertainty_panel,
        root_role="section",
        root_disclosure="always",
        empty_reason="too_few_comparables",
    ),
    "provenance_panel": Component(
        name="provenance_panel",
        builder=render_provenance_panel,
        root_role="provenance",
        root_disclosure="expander",
        empty_reason="not_yet_crawled",
    ),
}


def public_builders() -> dict[str, Callable[..., RenderNode]]:
    """Every component builder the render package defines."""
    found: dict[str, Callable[..., RenderNode]] = {}
    for module in _MODULES:
        for name, value in vars(module).items():
            if not name.startswith("render_") or not callable(value):
                continue
            if getattr(value, "__module__", "") != module.__name__:
                continue
            parameters = list(inspect.signature(value).parameters)
            if parameters and parameters[0] == "payload":
                found[name] = value
    return found


def heading_of(
    component: str,
    payload: Payload,
    *,
    config: RenderConfig,
    formatter: Formatter,
) -> str:
    """The component's own heading, which survives every state."""
    if component == "plot_check_header":
        return PLOT_CHECK
    if component.endswith("_block") and component != "verdict_block":
        return block_heading(payload, config=config, formatter=formatter)
    if component == "comparable_set":
        return COMPARABLE_SET_HEADING
    if component == "verdict_block":
        return VERDICT
    if component == "uncertainty_panel":
        return UNCERTAINTY_PANEL
    return PROVENANCE


def build_component(
    component: str,
    payload: Payload,
    *,
    config: RenderConfig,
    formatter: Formatter,
    now: datetime.date,
) -> RenderNode:
    """Build one registered component in whichever state its payload is in."""
    entry = COMPONENT_REGISTRY[component]
    state = state_of(payload, config=config, now=now)

    if state in ("loading", "empty", "error"):
        if state == "loading":
            child = RenderNode(
                role="loading",
                text=LOADING_TEXTS[component],
                prominence="equal",
                disclosure="always",
            )
        elif state == "empty":
            child = render_absence(payload.absence_reason)
        else:
            child = RenderNode(
                role="error",
                text=ERROR_TEXTS[component],
                prominence="equal",
                disclosure="always",
                meta={"tone": "warning", "field": component},
            )
        meta: dict[str, object] = {"component": component, "state": state}
        if entry.root_role == "verdict":
            meta["expanded"] = False
        return RenderNode(
            role=entry.root_role,
            text=heading_of(component, payload, config=config, formatter=formatter),
            prominence="primary" if entry.root_role != "verdict" else "secondary",
            disclosure=entry.root_disclosure,
            children=(child,),
            meta=meta,
        )

    tree = entry.builder(payload, config=config, formatter=formatter, now=now)
    return dataclasses.replace(
        tree, meta={**dict(tree.meta), "component": component, "state": state}
    )
