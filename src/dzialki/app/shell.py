"""The Streamlit adapter — the only module permitted to import Streamlit.

It maps a node tree onto widgets and decides nothing. Every honesty rule lives
in `render/`, where a test can read the tree directly; if a rule lived here it
would need a browser to check, and rules that need a browser are rules nobody
checks.

The adapter is therefore **total and dumb**. It has one handler per role, a test
asserts the handler set equals the role vocabulary exactly, and an unknown role
raises rather than being skipped. A skipped node is a number that silently stops
appearing, which is the failure the whole surface layer exists to prevent.

Streamlit is imported lazily inside `draw`. Importing it at module scope would
make the architecture test that forbids Streamlit outside this file depend on
Streamlit being installed, and would drag a UI framework into every unit run.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from dzialki.render.contract import DISCLOSURES, ROLES, RenderNode


class UnhandledRole(Exception):
    """A node role the adapter does not know how to draw.

    Raised, never skipped. Skipping would drop the node and its number from the
    page while every test on the tree still passed.
    """


def _text(node: RenderNode) -> str:
    return node.text


# Which Streamlit call each role uses. The values are method names rather than
# bound calls so the mapping can be asserted without importing Streamlit.
WIDGET_FOR_ROLE: Mapping[str, str] = {
    "section": "container",
    "header": "subheader",
    "aggregate_block": "container",
    "value": "markdown",
    "sample_size": "markdown",
    "spread": "markdown",
    "price": "markdown",
    "price_type_label": "markdown",
    "price_kind_label": "markdown",
    "flow_window_label": "markdown",
    "basis": "markdown",
    "unknown": "markdown",
    "absence": "info",
    "staleness": "markdown",
    "provenance": "caption",
    "verdict": "markdown",
    "comparable_set": "container",
    "comparable": "markdown",
    "uncertainty_note": "caption",
    "out_of_depth_notice": "warning",
    "sensitivity_note": "caption",
    "disclosure_banner": "warning",
    "selector": "radio",
    "map_feature": "markdown",
    "legend": "caption",
    "table_row": "markdown",
    "fallback_form": "text_input",
    "error": "error",
    "loading": "markdown",
}


def widget_for(node: RenderNode) -> str:
    """The Streamlit call this node draws with."""
    try:
        return WIDGET_FOR_ROLE[node.role]
    except KeyError as exc:
        raise UnhandledRole(
            f"role {node.role!r} has no widget. Add one rather than letting the "
            "node disappear from the page."
        ) from exc


def plan(node: RenderNode) -> list[tuple[int, str, str, str]]:
    """A flat drawing plan: depth, role, widget, text.

    Returned rather than drawn so a test can assert what the adapter would do
    without a Streamlit session. The disclosure level travels with each row,
    because a node the tree marks as `expander` must not be drawn inline.
    """
    rows: list[tuple[int, str, str, str]] = []

    def visit(current: RenderNode, depth: int) -> None:
        rows.append((depth, current.role, widget_for(current), _text(current)))
        for child in current.children:
            visit(child, depth + 1)

    visit(node, 0)
    return rows


def draw(node: RenderNode, *, streamlit: Any = None) -> None:
    """Draw ``node`` and its children.

    ``streamlit`` is injected so a test can pass a recorder. Importing it here
    rather than at module scope keeps the unit suite free of a UI framework.
    """
    if streamlit is None:  # pragma: no cover — exercised only in the real app
        import streamlit as streamlit_module

        streamlit = streamlit_module

    _draw(node, streamlit)


def _draw(node: RenderNode, streamlit: Any) -> None:
    widget: Callable[..., Any] = getattr(streamlit, widget_for(node))

    if node.disclosure == "expander":
        # D98: the verdict is collapsed so the evidence is read first. The tree
        # says which nodes hide; the adapter obeys and never decides.
        with streamlit.expander(node.text):
            for child in node.children:
                _draw(child, streamlit)
        return

    widget(node.text)
    for child in node.children:
        _draw(child, streamlit)


def unhandled_roles() -> frozenset[str]:
    """Roles the vocabulary declares and the adapter cannot draw."""
    return frozenset(ROLES) - frozenset(WIDGET_FOR_ROLE)


__all__ = [
    "DISCLOSURES",
    "WIDGET_FOR_ROLE",
    "UnhandledRole",
    "draw",
    "plan",
    "unhandled_roles",
    "widget_for",
]
