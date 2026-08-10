"""The pure render layer.

Nothing here imports Streamlit, opens a file, reads a clock or touches the
database. A rendering helper takes a payload, the configuration, a formatter and
``now``, and returns an immutable tree. The shell draws the tree; this package
decides what the tree says.

That separation is what makes the honesty rules of `21` §3 testable at all: a
rule about what the reader sees becomes a predicate over a data structure, and a
predicate can be run over every component in every state on every commit.
"""

from __future__ import annotations

from .contract import (
    DISCLOSURES,
    META_KEYS,
    PROMINENCES,
    ROLES,
    RenderNode,
    ancestors_of,
    disclosure_chain,
    index_of,
    nodes_by_role,
    siblings_of,
    text_tokens,
    top_level_nodes,
    walk,
)
from .format import Formatter
from .honesty import HONESTY_CHECKS, HonestyContext, Violation, check_all
from .inventory import COMPONENT_REGISTRY, build_component, public_builders
from .screen import ScreenPayload, assemble_plot_check
from .state import (
    STATES,
    Comparable,
    Payload,
    RenderConfig,
    render_config_from_params,
    state_of,
)

__all__ = [
    "COMPONENT_REGISTRY",
    "DISCLOSURES",
    "HONESTY_CHECKS",
    "META_KEYS",
    "PROMINENCES",
    "ROLES",
    "STATES",
    "Comparable",
    "Formatter",
    "HonestyContext",
    "Payload",
    "RenderConfig",
    "RenderNode",
    "ScreenPayload",
    "Violation",
    "ancestors_of",
    "assemble_plot_check",
    "build_component",
    "check_all",
    "disclosure_chain",
    "index_of",
    "nodes_by_role",
    "public_builders",
    "render_config_from_params",
    "siblings_of",
    "state_of",
    "text_tokens",
    "top_level_nodes",
    "walk",
]
