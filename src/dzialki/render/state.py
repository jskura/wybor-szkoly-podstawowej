"""The payload a component renders, the configuration it reads, and the state.

The state is **derived**, never passed. A caller that believes a four-listing
aggregate is normal cannot say so: no builder takes a state argument, and
``state_of`` reads the payload. That is V36's requirement in one function.

The clock is an argument too. ``render/`` never reads it, so a staleness test
runs without freezing time for the whole process.
"""

from __future__ import annotations

import dataclasses
import datetime
from collections.abc import Mapping
from decimal import Decimal

STATES: tuple[str, ...] = ("normal", "loading", "empty", "thin", "stale", "error")

# A percentage is a scale of ten to the minus two. Written as a shift so that
# no ratified value appears as a literal in the source (FR-75, V65).
PERCENT_EXPONENT = -2


@dataclasses.dataclass(frozen=True)
class RenderConfig:
    """Every number the renderer needs, and none of them a literal in a module.

    ``thousands_sep``, ``flow_window_days``, ``thin_n_threshold`` and
    ``area_band_pct`` are ratified and come from ``config/params.yml``. The
    other four are not in that file yet, so the caller states them and the
    absence is visible rather than hidden behind a default.
    """

    thousands_sep: str
    flow_window_days: int
    thin_n_threshold: int
    area_band_pct: int
    out_of_depth_min_comparables: int
    wide_spread_ratio: Decimal
    staleness_threshold_days: int
    method_version: str


def render_config_from_params(
    params,
    *,
    out_of_depth_min_comparables: int,
    wide_spread_ratio: Decimal,
    staleness_threshold_days: int,
    method_version: str,
) -> RenderConfig:
    """Build the render configuration from the loaded parameter file."""
    return RenderConfig(
        thousands_sep=params.surface.thousands_sep,
        flow_window_days=params.aggregates.flow_window_days,
        thin_n_threshold=params.aggregates.iqr_switch_n,
        area_band_pct=params.comparables.area_band_pct,
        out_of_depth_min_comparables=out_of_depth_min_comparables,
        wide_spread_ratio=wide_spread_ratio,
        staleness_threshold_days=staleness_threshold_days,
        method_version=method_version,
    )


@dataclasses.dataclass(frozen=True)
class Comparable:
    """One plot the estimate is built from."""

    comparable_id: str
    price_per_m2: Decimal
    area_m2: int
    gmina: str
    listed_on: datetime.date
    price_type: str
    price_kind: str


@dataclasses.dataclass(frozen=True)
class Payload:
    """What a component is asked to render.

    There is no ``state`` field, and that absence is the point.
    """

    pending: bool = False
    absent: bool = False
    absence_reason: str | None = None
    failed: bool = False

    n: int | None = None
    median: Decimal | None = None
    low: Decimal | None = None
    high: Decimal | None = None
    spread_published: bool = True

    price_type: str | None = None
    price_kind: str | None = None
    basis: str | None = None
    as_of: datetime.date | None = None
    sources: tuple[str, ...] = ()

    gmina: str | None = None
    teryt: str | None = None
    powiat: str | None = None
    quarter: tuple[int, int] | None = None

    area_m2: int | None = None
    price_pln: int | None = None
    price_per_m2: Decimal | None = None

    comparables: tuple[Comparable, ...] = ()


def staleness_days(as_of: datetime.date, *, now: datetime.date) -> int:
    """Whole days between the two dates, excluding the ``as_of`` date.

    An inclusive count renders 221 where the GUS row must read 220, and the
    difference is invisible until someone checks it by hand.
    """
    return (now - as_of).days


def is_stale(
    as_of: datetime.date | None, *, now: datetime.date, threshold_days: int
) -> bool:
    """Strictly more than the threshold. Exactly the threshold is fresh."""
    if as_of is None:
        return False
    return staleness_days(as_of, now=now) > threshold_days


def state_of(payload: Payload, *, config: RenderConfig, now: datetime.date) -> str:
    """The one state this payload is in.

    The order is fixed here so that two components never disagree about which
    condition wins when a payload satisfies several.
    """
    if payload.failed:
        return "error"
    if payload.pending:
        return "loading"
    if payload.absent:
        return "empty"
    if payload.n is None or payload.n < config.thin_n_threshold:
        return "thin"
    if is_stale(payload.as_of, now=now, threshold_days=config.staleness_threshold_days):
        return "stale"
    return "normal"


def spread_kind(payload: Payload, *, config: RenderConfig) -> str:
    """``unavailable`` where the source publishes none (D69), else n decides."""
    if not payload.spread_published:
        return "unavailable"
    if payload.n is not None and payload.n >= config.thin_n_threshold:
        return "iqr"
    return "min_max"


def spread_ratio(payload: Payload) -> Decimal | None:
    """``(high − low) / median``. ``None`` where the source publishes no spread."""
    if payload.low is None or payload.high is None or not payload.median:
        return None
    return (payload.high - payload.low) / payload.median


def area_band(area_m2: int, *, config: RenderConfig) -> tuple[Decimal, Decimal]:
    """The comparable area band D108 ratified, as a pair of areas."""
    span = Decimal(config.area_band_pct).scaleb(PERCENT_EXPONENT)
    area = Decimal(area_m2)
    return (area * (Decimal(1) - span), area * (Decimal(1) + span))


def range_meta(payload: Payload, *, config: RenderConfig) -> Mapping[str, object]:
    kind = spread_kind(payload, config=config)
    if kind == "unavailable":
        return {"low": None, "high": None, "kind": kind}
    return {"low": payload.low, "high": payload.high, "kind": kind}
