"""S11 — the Streamlit adapter draws every role, or refuses.

The adapter decides nothing. Every honesty rule is tested against the node tree
in `render/`, where no browser is needed. What is left to check here is
narrower and still worth checking: that no node can silently fail to appear.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Self

import pytest

from dzialki.app.shell import (
    WIDGET_FOR_ROLE,
    UnhandledRole,
    draw,
    plan,
    unhandled_roles,
    widget_for,
)
from dzialki.render.contract import ROLES, RenderNode

pytestmark = [pytest.mark.unit]


@dataclass
class RecordingStreamlit:
    """A stand-in that records calls instead of drawing.

    The adapter takes Streamlit as an argument precisely so this exists. A test
    that needed a running session would test the framework, not the mapping.
    """

    calls: list[tuple[str, str]] = field(default_factory=list)

    def __getattr__(self, name: str) -> Any:
        def record(text: str = "", *args: Any, **kwargs: Any) -> Any:
            self.calls.append((name, text))
            return _NullContext()

        return record


class _NullContext:
    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> bool:
        return False


def node(role: str, text: str = "x", **kwargs: Any) -> RenderNode:
    return RenderNode(
        role=role,
        text=text,
        prominence=kwargs.pop("prominence", "equal"),
        disclosure=kwargs.pop("disclosure", "always"),
        **kwargs,
    )


def test_the_adapter_handles_every_declared_role() -> None:
    """Equality with the vocabulary, not containment.

    A role added to `render/` without a widget here would draw nothing, and the
    number it carried would leave the page while every tree test still passed.
    """
    assert unhandled_roles() == frozenset()
    assert frozenset(WIDGET_FOR_ROLE) == frozenset(ROLES)


def test_an_unknown_role_raises_rather_than_being_skipped() -> None:
    """A skipped node is a number that silently stops appearing."""

    @dataclass(frozen=True)
    class Impostor:
        role: str = "role_that_does_not_exist"

    with pytest.raises(UnhandledRole) as caught:
        widget_for(Impostor())
    assert "role_that_does_not_exist" in str(caught.value)


def test_the_plan_visits_every_node_in_document_order() -> None:
    tree = node(
        "section",
        "Podobne oferty",
        children=(
            node("value", "mediana 118"),
            node("spread", "zakres międzykwartylowy 96–141"),
            node("sample_size", "n = 23"),
        ),
    )
    assert [row[1] for row in plan(tree)] == [
        "section",
        "value",
        "spread",
        "sample_size",
    ]
    assert [row[0] for row in plan(tree)] == [0, 1, 1, 1]


def test_a_collapsed_node_draws_inside_an_expander() -> None:
    """D98. The verdict is collapsed so the evidence is read first.

    The tree says which nodes hide. The adapter obeys it and never decides.
    """
    tree = node(
        "verdict",
        "WERDYKT",
        disclosure="expander",
        children=(node("basis", "Podstawa: 23 oferty"),),
    )
    recorder = RecordingStreamlit()
    draw(tree, streamlit=recorder)
    assert ("expander", "WERDYKT") in recorder.calls
    assert ("markdown", "Podstawa: 23 oferty") in recorder.calls


def test_an_always_visible_node_never_draws_inside_an_expander() -> None:
    """The companion. Without it the test above passes for a tree that hides
    everything, which is the opposite of what rule 7 asks for."""
    tree = node("value", "mediana 118", disclosure="always")
    recorder = RecordingStreamlit()
    draw(tree, streamlit=recorder)
    assert [name for name, _text in recorder.calls] == ["markdown"]


def test_every_node_reaches_a_widget() -> None:
    """One node per role, drawn, and the call count matches the node count."""
    children = tuple(node(role) for role in ROLES if role != "section")
    tree = node("section", "root", children=children)
    recorder = RecordingStreamlit()
    draw(tree, streamlit=recorder)
    assert len(recorder.calls) == len(ROLES)
