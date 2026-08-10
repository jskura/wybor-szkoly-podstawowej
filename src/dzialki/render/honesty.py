"""The interaction rules of `21` §3 and §7.1, as predicates over a tree.

Whether `142 zł/m²` is a fair price is unknowable here. Whether the number was
rendered with its n, its range, its price type, its price kind and its as-of
date, at equal prominence and outside any hover container, is a property of the
output — exactly computable. This module computes it.

Each check returns the violations it found, never a boolean. A boolean tells a
reader that something is wrong; a violation tells them which node and why.
"""

from __future__ import annotations

import dataclasses
import datetime
from collections.abc import Callable, Mapping
from decimal import Decimal

from .contract import (
    RenderNode,
    disclosure_chain,
    index_of,
    nodes_by_role,
    siblings_of,
    top_level_nodes,
    walk,
)
from .state import RenderConfig, is_stale
from .wording import (
    NOTE_NO_SPREAD,
    NOTE_THIN_NARROW,
    NOTE_THIN_WIDE,
    NOTE_WIDE,
    SENSITIVITY_TEXTS,
    SPREAD_UNAVAILABLE,
    UNCERTAINTY_VOCABULARY,
    VERDICT,
)

# A blank reads as "nothing to worry about", and a Python repr reads as data.
BLANKS = frozenset(
    {"", " ", "-", "–", "—", "?", "n/a", "N/A", "None", "null", "nan", "NaN", "0"}
)

# What a staleness node must sit beside. A number with no age beside it is the
# failure U8 names; an age in a page corner is the same failure, relocated.
NUMBER_BEARING = frozenset({"value", "price", "sample_size", "basis", "comparable"})

EVIDENCE = (
    "aggregate_block",
    "comparable_set",
    "unknown",
    "sensitivity_note",
    "disclosure_banner",
)

TWO = Decimal(2)


@dataclasses.dataclass(frozen=True)
class HonestyContext:
    """The configuration and the clock, both arguments and never read here."""

    config: RenderConfig
    now: datetime.date


@dataclasses.dataclass(frozen=True)
class Violation:
    """One rule broken at one node."""

    rule: str
    role: str
    text: str
    detail: str


def _violation(rule: str, node: RenderNode, detail: str) -> Violation:
    return Violation(rule=rule, role=node.role, text=node.text, detail=detail)


# --- U1 --------------------------------------------------------------------


def check_u1(tree: RenderNode, context: HonestyContext) -> tuple[Violation, ...]:
    """No aggregate without its n and its range, at equal prominence."""
    found: list[Violation] = []
    for block in nodes_by_role(tree, "aggregate_block"):
        direct = {
            role: tuple(child for child in block.children if child.role == role)
            for role in ("value", "spread", "sample_size")
        }
        complete = True
        for role, children in direct.items():
            if len(children) == 1:
                continue
            complete = False
            if not children:
                elsewhere = nodes_by_role(block, role)
                if elsewhere:
                    chain = disclosure_chain(tree, elsewhere[0])
                    found.append(
                        _violation(
                            "U1",
                            block,
                            f"the {role} is not a direct child; "
                            f"its disclosure chain is {list(chain)}",
                        )
                    )
                else:
                    found.append(_violation("U1", block, f"the {role} is absent"))
            else:
                found.append(
                    _violation("U1", block, f"{len(children)} {role} nodes, expected 1")
                )
        if not complete:
            continue

        value = direct["value"][0]
        spread = direct["spread"][0]
        sample = direct["sample_size"][0]
        if not value.prominence == spread.prominence == sample.prominence:
            found.append(
                _violation(
                    "U1",
                    block,
                    "the value, the spread and the sample size differ in prominence: "
                    f"{value.prominence}, {spread.prominence}, {sample.prominence}",
                )
            )
        if value.prominence == "primary":
            found.append(
                _violation(
                    "U1",
                    value,
                    "primary belongs on the block, never on the value inside it",
                )
            )
        for node in (spread, sample):
            chain = disclosure_chain(tree, node)
            for step in ("hover", "expander"):
                if step in chain:
                    found.append(
                        _violation("U1", node, f"reachable only through a {step}")
                    )
    return tuple(found)


# --- U1a -------------------------------------------------------------------


def check_u1a(tree: RenderNode, context: HonestyContext) -> tuple[Violation, ...]:
    """Where the source publishes no spread, the interface says so in words."""
    found: list[Violation] = []
    for node in nodes_by_role(tree, "spread"):
        ranges = node.meta.get("range") or {}
        if ranges.get("kind") != "unavailable":
            continue
        if node.text != SPREAD_UNAVAILABLE:
            found.append(
                _violation(
                    "U1a",
                    node,
                    "an unavailable spread renders its own sentence, "
                    f"not {node.text!r}",
                )
            )
        if node.prominence != "equal" or node.disclosure != "always":
            found.append(_violation("U1a", node, "the sentence is demoted or hidden"))
    for block in nodes_by_role(tree, "aggregate_block"):
        ranges = block.meta.get("range") or {}
        if ranges.get("kind") != "unavailable":
            continue
        if not any(child.role == "spread" for child in block.children):
            found.append(
                _violation(
                    "U1a",
                    block,
                    "the spread line is omitted, which reads as no uncertainty",
                )
            )
    return tuple(found)


# --- U2 --------------------------------------------------------------------


def check_u2(tree: RenderNode, context: HonestyContext) -> tuple[Violation, ...]:
    """Every price shows its type and its kind, and neither on hover."""
    found: list[Violation] = []
    for price in nodes_by_role(tree, "price"):
        roles = {node.role for node in siblings_of(tree, price)}
        for label in ("price_type_label", "price_kind_label"):
            if label not in roles:
                found.append(_violation("U2", price, f"no {label} beside the price"))
        if "hover" in disclosure_chain(tree, price):
            found.append(_violation("U2", price, "the price is reachable on hover"))
    return tuple(found)


# --- U3 --------------------------------------------------------------------


def check_u3(tree: RenderNode, context: HonestyContext) -> tuple[Violation, ...]:
    """Flow and stock both shown, both labelled, flow first, never averaged."""
    found: list[Violation] = []
    blocks = nodes_by_role(tree, "aggregate_block")
    flow = [node for node in blocks if node.meta.get("basis") == "flow"]
    stock = [node for node in blocks if node.meta.get("basis") == "stock"]
    if not flow and not stock:
        return ()
    if not flow or not stock:
        missing = "stock" if flow else "flow"
        found.append(
            _violation("U3", (flow or stock)[0], f"the {missing} aggregate is absent")
        )
        return tuple(found)
    if index_of(tree, flow[0]) > index_of(tree, stock[0]):
        found.append(_violation("U3", stock[0], "the stock block renders first"))
    flow_median = flow[0].meta.get("median")
    stock_median = stock[0].meta.get("median")
    blendable = (
        flow_median is not None
        and stock_median is not None
        and flow_median != stock_median
    )
    if blendable:
        blend = (flow_median + stock_median) / TWO
        for node in walk(tree):
            if node.meta.get("median") == blend:
                found.append(
                    _violation("U3", node, "flow and stock are blended into one")
                )
    return tuple(found)


# --- U4 --------------------------------------------------------------------


def check_u4(tree: RenderNode, context: HonestyContext) -> tuple[Violation, ...]:
    """The flow window sits beside every flow figure."""
    found: list[Violation] = []
    for node in walk(tree):
        if node.meta.get("basis") != "flow":
            continue
        family = (
            node.children if node.role == "aggregate_block" else siblings_of(tree, node)
        )
        if not any(relative.role == "flow_window_label" for relative in family):
            found.append(
                _violation("U4", node, "a flow figure with no window beside it")
            )
    return tuple(found)


# --- U5 --------------------------------------------------------------------


def check_u5(tree: RenderNode, context: HonestyContext) -> tuple[Violation, ...]:
    """The verdict is collapsed, and its own text carries no conclusion."""
    found: list[Violation] = []
    for verdict in nodes_by_role(tree, "verdict"):
        if verdict.text != VERDICT:
            found.append(
                _violation("U5", verdict, "the collapsed bar leaks its conclusion")
            )
        if verdict.disclosure != "expander":
            found.append(_violation("U5", verdict, "the verdict is not collapsed"))
        if verdict.meta.get("expanded") is not False:
            found.append(_violation("U5", verdict, "the verdict opens by default"))
        if verdict.prominence == "primary":
            found.append(_violation("U5", verdict, "the verdict outranks the evidence"))
        for node in walk(verdict):
            if node is verdict:
                continue
            if "expander" not in disclosure_chain(tree, node):
                found.append(
                    _violation("U5", node, "readable without expanding the verdict")
                )
    return tuple(found)


# --- U6 --------------------------------------------------------------------


def check_u6(tree: RenderNode, context: HonestyContext) -> tuple[Violation, ...]:
    """Nothing renders blank, and an unknown never reads as reassurance."""
    found: list[Violation] = []
    for node in walk(tree):
        if node.role != "value" and node.text.strip() in BLANKS:
            found.append(_violation("U6", node, f"the text is {node.text!r}"))
    for node in nodes_by_role(tree, "unknown"):
        if node.meta.get("tone") != "warning":
            found.append(_violation("U6", node, "an unknown styled as reassurance"))
        if node.prominence == "secondary":
            found.append(_violation("U6", node, "an unknown demoted to secondary"))
    return tuple(found)


# --- U7 --------------------------------------------------------------------


def check_u7(tree: RenderNode, context: HonestyContext) -> tuple[Violation, ...]:
    """Each absence reason keeps its own sentence and its own next action."""
    found: list[Violation] = []
    by_text: dict[str, object] = {}
    for node in nodes_by_role(tree, "absence"):
        reason = node.meta.get("absence_reason")
        seen = by_text.get(node.text)
        if seen is not None and seen != reason:
            found.append(
                _violation("U7", node, f"{seen} and {reason} share one sentence")
            )
        by_text[node.text] = reason
        if not any(child.role == "basis" for child in node.children):
            found.append(_violation("U7", node, "the absence names no next action"))
        if any(child.role == "value" for child in node.children):
            found.append(_violation("U7", node, "an absence renders a number"))
    return tuple(found)


# --- U8 --------------------------------------------------------------------


def check_u8(tree: RenderNode, context: HonestyContext) -> tuple[Violation, ...]:
    """Stale data shows its age on the number, never in a page banner."""
    found: list[Violation] = []
    for node in nodes_by_role(tree, "staleness"):
        roles = {relative.role for relative in siblings_of(tree, node)}
        if not roles & NUMBER_BEARING:
            found.append(
                _violation("U8", node, "the age sits beside no number of its own")
            )
    for node in nodes_by_role(tree, "value"):
        if not is_stale(
            node.meta.get("as_of"),
            now=context.now,
            threshold_days=context.config.staleness_threshold_days,
        ):
            continue
        if not any(
            relative.role == "staleness" for relative in siblings_of(tree, node)
        ):
            found.append(_violation("U8", node, "a stale number with no age beside it"))
    return tuple(found)


# --- U9 --------------------------------------------------------------------


def check_u9(tree: RenderNode, context: HonestyContext) -> tuple[Violation, ...]:
    """Every number is one interaction from its source, date and method."""
    found: list[Violation] = []
    for node in nodes_by_role(tree, "value"):
        handle = node.meta.get("provenance")
        if not isinstance(handle, Mapping):
            found.append(_violation("U9", node, "the number carries no provenance"))
            continue
        if not handle.get("source"):
            found.append(_violation("U9", node, "the provenance names no source"))
        if handle.get("as_of") is None:
            found.append(_violation("U9", node, "the provenance carries no as-of date"))
        if not handle.get("method_version"):
            found.append(_violation("U9", node, "the provenance names no method"))
        if not isinstance(handle.get("n"), int):
            found.append(_violation("U9", node, "the provenance carries no count"))
    for node in nodes_by_role(tree, "provenance"):
        chain = disclosure_chain(tree, node)
        if chain.count("expander") != 1:
            found.append(
                _violation("U9", node, f"{chain.count('expander')} expanders deep")
            )
        if "hover" in chain:
            found.append(_violation("U9", node, "provenance reachable on hover only"))
    return tuple(found)


# --- U10 -------------------------------------------------------------------


def expected_note(meta: Mapping[str, object], config: RenderConfig) -> str | None:
    """The note this aggregate warrants, from the closed vocabulary."""
    ranges = meta.get("range") or {}
    if ranges.get("kind") == "unavailable":
        return NOTE_NO_SPREAD
    low = ranges.get("low")
    high = ranges.get("high")
    median = meta.get("median")
    if low is None or high is None or not median:
        return None
    wide = (high - low) / median >= config.wide_spread_ratio
    count = meta.get("n")
    thin = not isinstance(count, int) or count < config.thin_n_threshold
    if thin:
        return NOTE_THIN_WIDE if wide else NOTE_THIN_NARROW
    return NOTE_WIDE if wide else None


def check_u10(tree: RenderNode, context: HonestyContext) -> tuple[Violation, ...]:
    """Uncertainty is stated in words, from a closed and reviewed vocabulary."""
    found: list[Violation] = []
    for node in nodes_by_role(tree, "uncertainty_note"):
        if node.text not in UNCERTAINTY_VOCABULARY:
            found.append(_violation("U10", node, "a note outside the vocabulary"))
        if node.disclosure != "always" or node.prominence != "equal":
            found.append(_violation("U10", node, "the note is demoted or hidden"))
    for block in nodes_by_role(tree, "aggregate_block"):
        if "range" not in block.meta:
            continue
        expected = expected_note(block.meta, context.config)
        actual = [
            child.text for child in block.children if child.role == "uncertainty_note"
        ]
        if expected is None and actual:
            found.append(
                _violation("U10", block, "a note on a tight, well-supported aggregate")
            )
        if expected is not None and actual != [expected]:
            found.append(
                _violation(
                    "U10", block, f"expected the note {expected!r}, found {actual}"
                )
            )
    return tuple(found)


# --- U11 -------------------------------------------------------------------


def check_u11(tree: RenderNode, context: HonestyContext) -> tuple[Violation, ...]:
    """The tool volunteers when it is out of its depth, and leads with it."""
    found: list[Violation] = []
    counted = [
        node.meta["n"]
        for node in walk(tree)
        if node.role in ("aggregate_block", "comparable_set")
        and isinstance(node.meta.get("n"), int)
    ]
    if not counted:
        return ()
    below = min(counted) < context.config.out_of_depth_min_comparables
    notices = nodes_by_role(tree, "out_of_depth_notice")
    if below:
        if not notices:
            found.append(_violation("U11", tree, "thin evidence and no admission"))
        else:
            rows = top_level_nodes(tree)
            if not rows or rows[0].role != "out_of_depth_notice":
                found.append(
                    _violation("U11", tree, "the admission does not lead the screen")
                )
        for verdict in nodes_by_role(tree, "verdict"):
            if verdict.prominence == "primary":
                found.append(
                    _violation("U11", verdict, "a confident band on thin evidence")
                )
    elif notices:
        found.append(_violation("U11", notices[0], "an admission on adequate evidence"))
    return tuple(found)


# --- U13 -------------------------------------------------------------------


def check_u13(tree: RenderNode, context: HonestyContext) -> tuple[Violation, ...]:
    """Each note is derived from a missing attribute and names a question."""
    found: list[Violation] = []
    written = set(SENSITIVITY_TEXTS.values())
    for node in nodes_by_role(tree, "sensitivity_note"):
        if node.text not in written:
            found.append(
                _violation("U13", node, "a generic caveat, not a derived note")
            )
        action = node.meta.get("action")
        if not isinstance(action, Mapping):
            found.append(_violation("U13", node, "the note names no next question"))
        elif not action.get("office") or not action.get("document"):
            found.append(
                _violation("U13", node, "the action names no office or document")
            )
        if node.prominence != "equal":
            found.append(_violation("U13", node, "the note is demoted"))
    return tuple(found)


# --- U14 -------------------------------------------------------------------


def check_u14(tree: RenderNode, context: HonestyContext) -> tuple[Violation, ...]:
    """The evidence is shown before the verdict, and nothing follows it."""
    verdicts = nodes_by_role(tree, "verdict")
    if not verdicts or verdicts[0] is tree:
        return ()
    verdict = verdicts[0]
    found: list[Violation] = []
    rows = top_level_nodes(tree)
    if rows and rows[-1] is not verdict:
        found.append(_violation("U14", rows[-1], "a row renders after the verdict"))
    position = index_of(tree, verdict)
    for node in walk(tree):
        if node.role in EVIDENCE and index_of(tree, node) > position:
            found.append(_violation("U14", node, "evidence rendered after the verdict"))
    return tuple(found)


HONESTY_CHECKS: dict[
    str, Callable[[RenderNode, HonestyContext], tuple[Violation, ...]]
] = {
    "U1": check_u1,
    "U1a": check_u1a,
    "U2": check_u2,
    "U3": check_u3,
    "U4": check_u4,
    "U5": check_u5,
    "U6": check_u6,
    "U7": check_u7,
    "U8": check_u8,
    "U9": check_u9,
    "U10": check_u10,
    "U11": check_u11,
    "U13": check_u13,
    "U14": check_u14,
}


def check_all(tree: RenderNode, context: HonestyContext) -> tuple[Violation, ...]:
    """Every rule, in the order they are numbered."""
    found: list[Violation] = []
    for check in HONESTY_CHECKS.values():
        found.extend(check(tree, context))
    return tuple(found)
