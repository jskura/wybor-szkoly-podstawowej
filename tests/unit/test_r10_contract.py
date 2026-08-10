"""S10.1 — the render tree, and the walkers every honesty rule reads.

The contract is the whole premise of stage S10. Every rendering helper is a pure
function from a payload to an immutable tree, so a rule about the interface
becomes a predicate over that tree.

`disclosure_chain` carries most of the weight, so its definition is pinned here
rather than inferred from a caller: the disclosures of the node's ancestors,
root first, then the node's own, with every ``always`` removed.
"""

from __future__ import annotations

import dataclasses

import pytest

from dzialki.render.contract import (
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
from dzialki.render.errors import InvalidNodeError, UnknownMetaKeyError

pytestmark = [pytest.mark.unit]


def leaf(role: str, text: str, prominence: str = "equal", disclosure="always"):
    return RenderNode(
        role=role, text=text, prominence=prominence, disclosure=disclosure
    )


@pytest.fixture
def tree() -> RenderNode:
    """A block with a value, its qualifiers, and provenance behind one expander."""
    return RenderNode(
        role="section",
        text="Sprawdzenie działki",
        prominence="primary",
        disclosure="always",
        children=(
            RenderNode(
                role="aggregate_block",
                text="Podobne oferty (przepływ, ostatnie 90 dni)",
                prominence="primary",
                disclosure="always",
                children=(
                    leaf("value", "mediana 118 zł/m²"),
                    leaf("spread", "zakres międzykwartylowy 96–141"),
                    leaf("sample_size", "n = 23"),
                    RenderNode(
                        role="provenance",
                        text="Źródło i metoda",
                        prominence="equal",
                        disclosure="expander",
                        children=(leaf("value", "Źródło: portal_a, portal_b"),),
                    ),
                ),
            ),
            RenderNode(
                role="section",
                text="szczegóły",
                prominence="secondary",
                disclosure="hover",
                children=(leaf("sample_size", "n = 61"),),
            ),
            leaf("verdict", "WERDYKT", "secondary", "expander"),
        ),
    )


# --- the node itself -------------------------------------------------------


def test_the_render_node_is_immutable(tree: RenderNode) -> None:
    node = nodes_by_role(tree, "value")[0]

    with pytest.raises(dataclasses.FrozenInstanceError):
        node.text = "x"
    with pytest.raises(AttributeError):
        node.children.append(node)
    with pytest.raises(TypeError):
        node.meta["n"] = 1


def test_children_and_meta_are_normalised_to_immutable_types() -> None:
    node = RenderNode(
        role="value",
        text="mediana 118 zł/m²",
        prominence="equal",
        disclosure="always",
        children=[leaf("basis", "przepływ")],
        meta={"n": 23},
    )
    assert isinstance(node.children, tuple)
    assert dict(node.meta) == {"n": 23}
    with pytest.raises(TypeError):
        node.meta["n"] = 24


def test_the_vocabularies_are_closed_and_exact() -> None:
    assert PROMINENCES == ("primary", "equal", "secondary")
    assert DISCLOSURES == ("always", "expander", "hover")
    assert ROLES == (
        "section",
        "header",
        "aggregate_block",
        "value",
        "sample_size",
        "spread",
        "price",
        "price_type_label",
        "price_kind_label",
        "flow_window_label",
        "basis",
        "unknown",
        "absence",
        "staleness",
        "provenance",
        "verdict",
        "comparable_set",
        "comparable",
        "uncertainty_note",
        "out_of_depth_notice",
        "sensitivity_note",
        "disclosure_banner",
        "selector",
        "map_feature",
        "legend",
        "table_row",
        "fallback_form",
        "error",
        "loading",
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("role", "headline"),
        ("prominence", "loud"),
        ("disclosure", "tooltip"),
    ],
)
def test_a_value_outside_the_vocabulary_is_refused_by_name(
    field: str, value: str
) -> None:
    kwargs = {
        "role": "value",
        "text": "mediana 118 zł/m²",
        "prominence": "equal",
        "disclosure": "always",
    }
    kwargs[field] = value
    with pytest.raises(InvalidNodeError) as caught:
        RenderNode(**kwargs)
    assert value in str(caught.value)
    assert field in str(caught.value)


def test_a_meta_key_outside_the_closed_set_is_refused_by_name() -> None:
    """A private key name is how an unqualified figure would be smuggled in."""
    with pytest.raises(UnknownMetaKeyError) as caught:
        RenderNode(
            role="value",
            text="mediana 118 zł/m²",
            prominence="equal",
            disclosure="always",
            meta={"headline_number": 118},
        )
    assert "headline_number" in str(caught.value)


def test_the_meta_vocabulary_is_exactly_the_documented_set() -> None:
    assert META_KEYS == frozenset(
        {
            "component",
            "state",
            "n",
            "median",
            "range",
            "price_type",
            "price_kind",
            "basis",
            "flow_window_days",
            "as_of",
            "provenance",
            "absence_reason",
            "tone",
            "expanded",
            "exclude_control",
            "comparable_id",
            "action",
            "fill",
            "pattern",
            "legend_key",
            "opacity",
            "field",
            "subject_id",
            "teryt",
            "sources",
        }
    )


# --- the walkers -----------------------------------------------------------


def test_walk_returns_every_node_in_document_order(tree: RenderNode) -> None:
    assert [node.role for node in walk(tree)] == [
        "section",
        "aggregate_block",
        "value",
        "spread",
        "sample_size",
        "provenance",
        "value",
        "section",
        "sample_size",
        "verdict",
    ]


def test_walk_includes_the_root(tree: RenderNode) -> None:
    assert walk(tree)[0] is tree


def test_nodes_by_role_reads_a_subtree_as_well_as_a_whole_tree(
    tree: RenderNode,
) -> None:
    block = nodes_by_role(tree, "aggregate_block")[0]
    assert [node.text for node in nodes_by_role(block, "value")] == [
        "mediana 118 zł/m²",
        "Źródło: portal_a, portal_b",
    ]
    assert len(nodes_by_role(tree, "sample_size")) == 2


def test_index_of_is_the_document_order_position(tree: RenderNode) -> None:
    verdict = nodes_by_role(tree, "verdict")[0]
    block = nodes_by_role(tree, "aggregate_block")[0]
    assert index_of(tree, block) == 1
    assert index_of(tree, verdict) == 9


def test_index_of_finds_the_node_by_identity_not_by_equality() -> None:
    """Two nodes can be equal and still be different places on the screen."""
    first = leaf("sample_size", "n = 23")
    second = leaf("sample_size", "n = 23")
    assert first == second
    root = RenderNode(
        role="section",
        text="Sprawdzenie działki",
        prominence="primary",
        disclosure="always",
        children=(first, second),
    )
    assert index_of(root, first) == 1
    assert index_of(root, second) == 2


def test_ancestors_of_is_root_first_and_empty_for_the_root(tree: RenderNode) -> None:
    source = nodes_by_role(tree, "provenance")[0].children[0]
    assert [node.role for node in ancestors_of(tree, source)] == [
        "section",
        "aggregate_block",
        "provenance",
    ]
    assert ancestors_of(tree, tree) == ()


def test_siblings_of_excludes_the_node_itself(tree: RenderNode) -> None:
    value = nodes_by_role(tree, "value")[0]
    assert [node.role for node in siblings_of(tree, value)] == [
        "spread",
        "sample_size",
        "provenance",
    ]


def test_top_level_nodes_are_the_children_of_the_root(tree: RenderNode) -> None:
    assert [node.role for node in top_level_nodes(tree)] == [
        "aggregate_block",
        "section",
        "verdict",
    ]


def test_text_tokens_is_every_text_in_document_order(tree: RenderNode) -> None:
    assert text_tokens(tree)[:4] == (
        "Sprawdzenie działki",
        "Podobne oferty (przepływ, ostatnie 90 dni)",
        "mediana 118 zł/m²",
        "zakres międzykwartylowy 96–141",
    )


def test_a_node_outside_the_tree_is_refused_by_every_walker(tree: RenderNode) -> None:
    stranger = leaf("value", "mediana 999 zł/m²")
    for walker in (index_of, ancestors_of, siblings_of, disclosure_chain):
        with pytest.raises(LookupError):
            walker(tree, stranger)


# --- disclosure_chain, the load-bearing definition -------------------------


def test_disclosure_chain_omits_always_and_includes_the_node_itself(
    tree: RenderNode,
) -> None:
    sample = nodes_by_role(tree, "sample_size")[0]
    spread = nodes_by_role(tree, "spread")[0]
    provenance = nodes_by_role(tree, "provenance")[0]

    assert disclosure_chain(tree, sample) == ()
    assert disclosure_chain(tree, spread) == ()
    assert disclosure_chain(tree, provenance) == ("expander",)
    assert disclosure_chain(tree, provenance.children[0]) == ("expander",)


def test_disclosure_chain_reports_a_container_the_node_cannot_see(
    tree: RenderNode,
) -> None:
    """The assertion V35 names. The hidden node's own disclosure reads
    ``always``; only the chain shows the hover container above it."""
    hidden = nodes_by_role(tree, "sample_size")[1]
    assert hidden.disclosure == "always"
    assert disclosure_chain(tree, hidden) == ("hover",)
