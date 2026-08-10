"""U1, U1a, U4, U8 and U10 — the aggregate block, which is where rule 7 lives.

Every aggregate renders its value, its spread and its sample size as siblings,
at the same prominence, with nothing between them and the reader. ``primary``
sits on the block, never on the value inside it: a headline with a footnote is
arithmetically identical to three equal lines and reads as certainty.

Two payloads never render. One with no sample size and one with no range both
raise, so the violation is unrepresentable rather than discouraged.

D69 is the exception that proves the rule holds. A source that publishes a
central value and no spread still renders a spread line — one that says so in
words. A missing line would read as "no uncertainty".
"""

from __future__ import annotations

import datetime
from decimal import Decimal

from .contract import RenderNode
from .errors import BareAggregateError, UnlabelledAggregateError
from .format import Formatter
from .price import check_price_pair, price_labels
from .provenance import provenance_meta, provenance_node
from .state import (
    Payload,
    RenderConfig,
    is_stale,
    range_meta,
    spread_kind,
    spread_ratio,
    staleness_days,
)
from .wording import (
    BASIS_LABELS,
    FLOW_BLOCK,
    FLOW_STOCK_GAP,
    FLOW_WINDOW,
    GUS_BLOCK,
    MEAN_VALUE,
    MEDIAN_VALUE,
    NOTE_NO_SPREAD,
    NOTE_THIN_NARROW,
    NOTE_THIN_WIDE,
    NOTE_WIDE,
    SAMPLE_SIZE,
    SPREAD_IQR,
    SPREAD_MIN_MAX,
    SPREAD_UNAVAILABLE,
    STALENESS,
    STOCK_BLOCK,
    STOCK_FLOW_GAP,
)

GUS_SOURCE = "gus_bdl"


def flow_window_text(config: RenderConfig, formatter: Formatter) -> str:
    """``ostatnie 90 dni`` — the length comes from the configuration (D107)."""
    return FLOW_WINDOW.format(window=formatter.format_days(config.flow_window_days))


def block_heading(
    payload: Payload, *, config: RenderConfig, formatter: Formatter
) -> str:
    if payload.basis == "flow":
        return FLOW_BLOCK.format(window=flow_window_text(config, formatter))
    if payload.basis == "stock":
        return STOCK_BLOCK
    if payload.basis == "gus_powiat":
        year, quarter = payload.quarter
        return GUS_BLOCK.format(
            powiat=payload.powiat,
            quarter=formatter.format_source_quarter(GUS_SOURCE, year, quarter),
        )
    raise UnlabelledAggregateError(
        f"the basis {payload.basis!r} has no written heading"
    )


def spread_text(payload: Payload, *, config: RenderConfig, formatter: Formatter) -> str:
    """D100 names the interquartile range in full, because the short word does
    not say which range it is. The min-max range is a different range and keeps
    the short word."""
    kind = spread_kind(payload, config=config)
    if kind == "unavailable":
        return SPREAD_UNAVAILABLE
    rendered = formatter.format_range(payload.low, payload.high)
    template = SPREAD_IQR if kind == "iqr" else SPREAD_MIN_MAX
    return template.format(range=rendered)


def uncertainty_note_text(payload: Payload, *, config: RenderConfig) -> str | None:
    """The closed vocabulary of U10.

    A wide spread reads the same whether the sample is large or small, so the
    two large-sample rows of the table share one sentence and the boundary
    between them is not observable. It is therefore not a parameter.
    """
    if spread_kind(payload, config=config) == "unavailable":
        return NOTE_NO_SPREAD
    ratio = spread_ratio(payload)
    if ratio is None:
        return None
    wide = ratio >= config.wide_spread_ratio
    thin = payload.n is None or payload.n < config.thin_n_threshold
    if thin:
        return NOTE_THIN_WIDE if wide else NOTE_THIN_NARROW
    return NOTE_WIDE if wide else None


def staleness_node(
    payload: Payload, *, config: RenderConfig, formatter: Formatter, now: datetime.date
) -> RenderNode | None:
    """U8 — the age sits on the number, never in a corner banner."""
    if not is_stale(
        payload.as_of, now=now, threshold_days=config.staleness_threshold_days
    ):
        return None
    days = staleness_days(payload.as_of, now=now)
    return RenderNode(
        role="staleness",
        text=STALENESS.format(
            days=formatter.format_days(days),
            date=formatter.format_date(payload.as_of),
        ),
        prominence="equal",
        disclosure="always",
        meta={"as_of": payload.as_of},
    )


def _check_renderable(payload: Payload, *, config: RenderConfig) -> None:
    if payload.basis is None:
        raise UnlabelledAggregateError(
            "an aggregate with no basis does not render: flow and stock read alike"
        )
    if payload.n is None:
        raise BareAggregateError("an aggregate with no n does not render (U1)")
    if payload.median is None:
        raise BareAggregateError("an aggregate with no median does not render")
    if spread_kind(payload, config=config) == "unavailable":
        return
    if payload.low is None or payload.high is None:
        raise BareAggregateError("an aggregate with no range does not render (U1)")


def render_aggregate_block(
    payload: Payload,
    *,
    config: RenderConfig,
    formatter: Formatter,
    now: datetime.date,
    prominence: str = "primary",
) -> RenderNode:
    """One aggregate, with every qualifier it cannot honestly appear without."""
    _check_renderable(payload, config=config)
    check_price_pair(payload.price_type, payload.price_kind)

    handle = provenance_meta(
        sources=payload.sources,
        as_of=payload.as_of,
        method_version=config.method_version,
        n=payload.n,
    )
    value_template = MEAN_VALUE if payload.basis == "gus_powiat" else MEDIAN_VALUE
    ranges = range_meta(payload, config=config)

    children: list[RenderNode] = [
        RenderNode(
            role="basis",
            text=BASIS_LABELS[payload.basis],
            prominence="equal",
            disclosure="always",
            meta={"basis": payload.basis},
        )
    ]
    if payload.basis == "flow":
        children.append(
            RenderNode(
                role="flow_window_label",
                text=flow_window_text(config, formatter),
                prominence="equal",
                disclosure="always",
                meta={"flow_window_days": config.flow_window_days},
            )
        )
    children.append(
        RenderNode(
            role="value",
            text=value_template.format(price=formatter.format_ppm2(payload.median)),
            prominence="equal",
            disclosure="always",
            meta={
                "median": payload.median,
                "basis": payload.basis,
                "as_of": payload.as_of,
                "provenance": handle,
            },
        )
    )
    stale = staleness_node(payload, config=config, formatter=formatter, now=now)
    if stale is not None:
        children.append(stale)
    children.append(
        RenderNode(
            role="spread",
            text=spread_text(payload, config=config, formatter=formatter),
            prominence="equal",
            disclosure="always",
            meta={"range": ranges},
        )
    )
    children.append(
        RenderNode(
            role="sample_size",
            text=SAMPLE_SIZE.format(n=payload.n),
            prominence="equal",
            disclosure="always",
            meta={"n": payload.n},
        )
    )
    children.extend(price_labels(payload.price_type, payload.price_kind))

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
        provenance_node(
            sources=payload.sources,
            as_of=payload.as_of,
            method_version=config.method_version,
            n=payload.n,
            formatter=formatter,
        )
    )

    meta: dict[str, object] = {
        "basis": payload.basis,
        "n": payload.n,
        "median": payload.median,
        "range": ranges,
        "price_type": payload.price_type,
        "price_kind": payload.price_kind,
        "as_of": payload.as_of,
    }
    if payload.basis == "flow":
        meta["flow_window_days"] = config.flow_window_days

    return RenderNode(
        role="aggregate_block",
        text=block_heading(payload, config=config, formatter=formatter),
        prominence=prominence,
        disclosure="always",
        children=tuple(children),
        meta=meta,
    )


def gap_commentary(
    flow_median: Decimal,
    stock_median: Decimal,
    *,
    sources: tuple[str, ...],
    as_of: datetime.date,
    method_version: str,
    n: int,
) -> RenderNode | None:
    """U3 — the gap is described, never reconciled into one number."""
    if flow_median == stock_median:
        return None
    text = STOCK_FLOW_GAP if stock_median > flow_median else FLOW_STOCK_GAP
    return RenderNode(
        role="value",
        text=text,
        prominence="equal",
        disclosure="always",
        meta={
            "field": "stock_flow_gap",
            "basis": "derived",
            "as_of": as_of,
            "provenance": provenance_meta(
                sources=sources, as_of=as_of, method_version=method_version, n=n
            ),
        },
    )
