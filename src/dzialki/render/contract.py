"""The render tree, and the walkers every honesty rule reads.

A rendering helper is a pure function from a payload to a ``RenderNode``. The
node says what a reader sees and where it sits; it says nothing about widgets.
That is what turns "the range is not hidden in a tooltip" from a design review
into an assertion.

``disclosure_chain`` is the load-bearing walker. It answers the question a
node's own ``disclosure`` cannot: what does a reader have to do before this text
appears. A container two levels up can hide a node whose own disclosure reads
``always``, and that is the failure V35 names.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Iterable, Mapping, Sequence
from types import MappingProxyType

from .errors import InvalidNodeError, UnknownMetaKeyError

# D101 added `section` and `header`, so a container needs no role of its own.
ROLES: tuple[str, ...] = (
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

PROMINENCES: tuple[str, ...] = ("primary", "equal", "secondary")
DISCLOSURES: tuple[str, ...] = ("always", "expander", "hover")

# The closed vocabulary. `teryt` and `sources` are here because the plot-check
# tree needs them; every other key is the one the test plan lists.
META_KEYS: frozenset[str] = frozenset(
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

_EMPTY_META: Mapping[str, object] = MappingProxyType({})


@dataclasses.dataclass(frozen=True)
class RenderNode:
    """One thing a reader sees, with its place in the disclosure hierarchy."""

    role: str
    text: str
    prominence: str
    disclosure: str
    children: tuple[RenderNode, ...] = ()
    meta: Mapping[str, object] = dataclasses.field(default_factory=lambda: _EMPTY_META)

    def __post_init__(self) -> None:
        if self.role not in ROLES:
            raise InvalidNodeError(f"role {self.role!r} is outside the role vocabulary")
        if self.prominence not in PROMINENCES:
            raise InvalidNodeError(
                f"prominence {self.prominence!r} is outside the prominence vocabulary"
            )
        if self.disclosure not in DISCLOSURES:
            raise InvalidNodeError(
                f"disclosure {self.disclosure!r} is outside the disclosure vocabulary"
            )
        unknown = sorted(set(self.meta) - META_KEYS)
        if unknown:
            raise UnknownMetaKeyError(
                f"meta key {unknown[0]!r} is outside the closed vocabulary"
            )
        object.__setattr__(self, "children", tuple(self.children))
        object.__setattr__(self, "meta", MappingProxyType(dict(self.meta)))


def walk(tree: RenderNode) -> tuple[RenderNode, ...]:
    """Every node, the root first, in the order a reader meets them."""
    found: list[RenderNode] = [tree]
    for child in tree.children:
        found.extend(walk(child))
    return tuple(found)


def nodes_by_role(tree: RenderNode, role: str) -> tuple[RenderNode, ...]:
    """Every node of ``role``, in document order. Reads a subtree as well."""
    return tuple(node for node in walk(tree) if node.role == role)


def text_tokens(tree: RenderNode) -> tuple[str, ...]:
    return tuple(node.text for node in walk(tree))


def top_level_nodes(tree: RenderNode) -> tuple[RenderNode, ...]:
    """The children of the root — the rows of the screen."""
    return tree.children


def _paths(tree: RenderNode) -> dict[int, tuple[RenderNode, ...]]:
    """Every node's ancestors, keyed by identity.

    Identity, not equality: two nodes can carry the same text and sit in
    different places, and the rule that separates them is about place.
    """
    found: dict[int, tuple[RenderNode, ...]] = {}

    def visit(node: RenderNode, ancestors: tuple[RenderNode, ...]) -> None:
        found.setdefault(id(node), ancestors)
        for child in node.children:
            visit(child, (*ancestors, node))

    visit(tree, ())
    return found


def _locate(tree: RenderNode, node: RenderNode) -> tuple[RenderNode, ...]:
    ancestors = _paths(tree).get(id(node))
    if ancestors is None:
        raise LookupError(f"the node {node.role!r} {node.text!r} is not in this tree")
    return ancestors


def ancestors_of(tree: RenderNode, node: RenderNode) -> tuple[RenderNode, ...]:
    """The node's ancestors, root first. Empty for the root itself."""
    return _locate(tree, node)


def siblings_of(tree: RenderNode, node: RenderNode) -> tuple[RenderNode, ...]:
    """The other children of the node's parent. Empty for the root."""
    ancestors = _locate(tree, node)
    if not ancestors:
        return ()
    return tuple(child for child in ancestors[-1].children if child is not node)


def index_of(tree: RenderNode, node: RenderNode) -> int:
    """The node's position in document order."""
    _locate(tree, node)
    for position, candidate in enumerate(walk(tree)):
        if candidate is node:
            return position
    raise LookupError(f"the node {node.role!r} {node.text!r} is not in this tree")


def disclosure_chain(tree: RenderNode, node: RenderNode) -> tuple[str, ...]:
    """What a reader must do before this text appears.

    The disclosures of the node's ancestors, root first, then the node's own,
    with every ``always`` removed. An empty chain means the text is on screen.
    """
    ancestors = _locate(tree, node)
    chain = [*(ancestor.disclosure for ancestor in ancestors), node.disclosure]
    return tuple(step for step in chain if step != "always")


def one(nodes: Sequence[RenderNode] | Iterable[RenderNode]) -> RenderNode:
    """The single node of a sequence, or an error naming the count."""
    found = tuple(nodes)
    if len(found) != 1:
        raise LookupError(f"expected exactly one node, found {len(found)}")
    return found[0]
