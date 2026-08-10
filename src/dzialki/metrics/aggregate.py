"""Aggregates by gmina and area band, as both stock and flow.

**Stock** is what stands on the market at the valuation date. **Flow** is what
arrived inside the recent window. They differ, and the difference is the point.
A plot that nobody buys stays in stock and keeps lifting the stock median, while
the plots that sold have left the pool. `20` §5 describes that bias; D56 makes
flow the headline and keeps stock beside it.

The flow window is 90 days (D107), read from `config/params.yml` and passed in.
Every flow figure states the window it covers, because a flow median without one
says nothing.

**Two date columns, two different jobs.** Flow membership reads `first_seen`: it
asks when the listing arrived. The month bucket reads `observed_at`: it asks when
we saw it. Crossing the two produces a fixture nobody can satisfy.

Month buckets follow the Europe/Warsaw calendar (`08` §6). A listing first seen
at 23:30 on 30 June is a June listing; bucketing in UTC would call it July.
"""

from __future__ import annotations

import datetime as dt
import zoneinfo
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import NamedTuple

from .bands import band_for
from .spread import Spread, spread_from_values

WARSAW = zoneinfo.ZoneInfo("Europe/Warsaw")

STOCK = "stock"
FLOW = "flow"


class GroupKey(NamedTuple):
    """The D66 key, minus `generation`.

    `price_type`, `price_kind`, `series_kind` and `area_band` are in it because
    without them two rows that mean different things collide on insert and the
    second replaces the first. `unit_level` is out of it, because `teryt_unit`
    determines it.
    """

    teryt_unit: str
    month: dt.date
    asset_class: str
    buildability: str
    price_type: str
    price_kind: str
    series_kind: str
    area_band: str


@dataclass(frozen=True)
class Observation:
    """One listing as one aggregate sees it.

    Deduplication and comparable selection happen before this point. This module
    computes over the set it is handed and adds no filter of its own beyond
    `active` and the flow window.
    """

    listing_id: str
    teryt_unit: str
    unit_level: str
    asset_class: str
    buildability: str
    price_type: str
    price_kind: str
    area_m2: Decimal
    price_pln: Decimal
    first_seen: dt.datetime
    observed_at: dt.datetime
    active: bool
    source_id: int

    @property
    def price_per_m2(self) -> float:
        """The area arrives normalised (V10, V28). Nothing is re-converted here."""
        return float(self.price_pln) / float(self.area_m2)

    @property
    def area_band(self) -> str:
        return band_for(self.area_m2)

    @property
    def month(self) -> dt.date:
        local = self.observed_at.astimezone(WARSAW)
        return dt.date(local.year, local.month, 1)


@dataclass(frozen=True)
class Series:
    """One spread, labelled stock or flow.

    Neither series is ever unlabelled (V45 c), and a flow series always states
    its window. Both rules live in the constructor, so an unlabelled figure
    cannot be built and then explained away later.
    """

    series_kind: str
    flow_window_days: int | None
    spread: Spread

    def __post_init__(self) -> None:
        if self.series_kind not in (STOCK, FLOW):
            raise ValueError(f"{self.series_kind!r} is neither stock nor flow")
        if (self.series_kind == FLOW) != (self.flow_window_days is not None):
            raise ValueError("a flow series states its window and a stock one does not")

    @property
    def n(self) -> int:
        return self.spread.n

    @property
    def median_ppm2(self) -> Decimal:
        return self.spread.median_ppm2

    @property
    def p25_ppm2(self) -> Decimal | None:
        return self.spread.p25_ppm2

    @property
    def p75_ppm2(self) -> Decimal | None:
        return self.spread.p75_ppm2

    @property
    def min_ppm2(self) -> Decimal | None:
        return self.spread.min_ppm2

    @property
    def max_ppm2(self) -> Decimal | None:
        return self.spread.max_ppm2

    @property
    def mean_ppm2(self) -> Decimal | None:
        return self.spread.mean_ppm2

    @property
    def range_kind(self) -> str:
        return self.spread.range_kind

    @property
    def low(self) -> Decimal | None:
        return self.spread.low

    @property
    def high(self) -> Decimal | None:
        return self.spread.high


@dataclass(frozen=True)
class Aggregate:
    """One published figure, with everything rule 7 requires beside it.

    No field has a default, so the source, the as-of date and the sample size
    cannot be forgotten. They can only be supplied.
    """

    teryt_unit: str
    unit_level: str
    month: dt.date
    asset_class: str
    buildability: str
    price_type: str
    price_kind: str
    area_band: str
    series: Series
    as_of: dt.date
    source_ids: tuple[int, ...]

    @property
    def key(self) -> GroupKey:
        return GroupKey(
            teryt_unit=self.teryt_unit,
            month=self.month,
            asset_class=self.asset_class,
            buildability=self.buildability,
            price_type=self.price_type,
            price_kind=self.price_kind,
            series_kind=self.series_kind,
            area_band=self.area_band,
        )

    @property
    def series_kind(self) -> str:
        return self.series.series_kind

    @property
    def flow_window_days(self) -> int | None:
        return self.series.flow_window_days

    @property
    def n(self) -> int:
        return self.series.n

    @property
    def median_ppm2(self) -> Decimal:
        return self.series.median_ppm2

    @property
    def p25_ppm2(self) -> Decimal | None:
        return self.series.p25_ppm2

    @property
    def p75_ppm2(self) -> Decimal | None:
        return self.series.p75_ppm2

    @property
    def min_ppm2(self) -> Decimal | None:
        return self.series.min_ppm2

    @property
    def max_ppm2(self) -> Decimal | None:
        return self.series.max_ppm2

    @property
    def mean_ppm2(self) -> Decimal | None:
        return self.series.mean_ppm2

    @property
    def range_kind(self) -> str:
        return self.series.range_kind

    @property
    def low(self) -> Decimal | None:
        return self.series.low

    @property
    def high(self) -> Decimal | None:
        return self.series.high


def in_flow_window(
    observation: Observation, *, as_of: dt.date, flow_window_days: int
) -> bool:
    """Did this listing arrive inside the window?

    The cutoff itself counts. A listing first seen exactly on the boundary day is
    in flow.
    """
    cutoff = as_of - dt.timedelta(days=flow_window_days)
    return observation.first_seen.astimezone(WARSAW).date() >= cutoff


class _Bucket(NamedTuple):
    """The `GroupKey`, minus the series label, plus the unit level.

    Stock and flow come out of one group, so the label is added after the split.
    `unit_level` rides along because `teryt_unit` determines it, so grouping on
    both cannot split a gmina in two.
    """

    teryt_unit: str
    unit_level: str
    month: dt.date
    asset_class: str
    buildability: str
    price_type: str
    price_kind: str
    area_band: str


def _bucket_for(row: Observation) -> _Bucket:
    return _Bucket(
        teryt_unit=row.teryt_unit,
        unit_level=row.unit_level,
        month=row.month,
        asset_class=row.asset_class,
        buildability=row.buildability,
        price_type=row.price_type,
        price_kind=row.price_kind,
        area_band=row.area_band,
    )


def _partition(
    observations: Sequence[Observation], *, as_of: dt.date, flow_window_days: int
) -> tuple[list[Observation], list[Observation]]:
    """The two pools: everything standing, and the part of it that is recent."""
    standing = [row for row in observations if row.active]
    recent = [
        row
        for row in standing
        if in_flow_window(row, as_of=as_of, flow_window_days=flow_window_days)
    ]
    return standing, recent


def stock_and_flow(
    observations: Sequence[Observation],
    *,
    as_of: dt.date,
    flow_window_days: int,
    iqr_switch_n: int,
) -> tuple[Series | None, Series | None]:
    """Both series over one set, from one call.

    Neither is optional and neither is computed on its own. Returning them
    together is what stops a caller publishing a stock figure while believing it
    is a flow one.
    """
    standing, recent = _partition(
        observations, as_of=as_of, flow_window_days=flow_window_days
    )

    stock = (
        Series(
            series_kind=STOCK,
            flow_window_days=None,
            spread=spread_from_values(
                [row.price_per_m2 for row in standing], iqr_switch_n=iqr_switch_n
            ),
        )
        if standing
        else None
    )
    flow = (
        Series(
            series_kind=FLOW,
            flow_window_days=flow_window_days,
            spread=spread_from_values(
                [row.price_per_m2 for row in recent], iqr_switch_n=iqr_switch_n
            ),
        )
        if recent
        else None
    )
    return stock, flow


def headline(stock: Series | None, flow: Series | None) -> Series:
    """The figure that leads (D56).

    Raises when handed only one of the pair. One series alone cannot say which
    figure is the secondary one, and a caller with one series has already lost
    the comparison the rule exists for.
    """
    if stock is None or flow is None:
        raise ValueError("the headline needs both series, not one")
    return flow


def aggregate(
    observations: Iterable[Observation],
    *,
    as_of: dt.date,
    flow_window_days: int,
    iqr_switch_n: int,
) -> list[Aggregate]:
    """Every `metric_unit_month` row the observations support.

    A group with no observations produces no row. Absence of data is absence,
    never a zero and never an aggregate with `n = 0`.
    """
    groups: dict[_Bucket, list[Observation]] = {}
    for row in observations:
        groups.setdefault(_bucket_for(row), []).append(row)

    built: list[Aggregate] = []
    for bucket, members in groups.items():
        stock, flow = stock_and_flow(
            members,
            as_of=as_of,
            flow_window_days=flow_window_days,
            iqr_switch_n=iqr_switch_n,
        )
        # The two pools again, because `source_ids` names the sources behind
        # each series and the two series rest on different rows.
        standing, recent = _partition(
            members, as_of=as_of, flow_window_days=flow_window_days
        )
        for series, contributors in ((stock, standing), (flow, recent)):
            if series is None:
                continue
            built.append(
                Aggregate(
                    teryt_unit=bucket.teryt_unit,
                    unit_level=bucket.unit_level,
                    month=bucket.month,
                    asset_class=bucket.asset_class,
                    buildability=bucket.buildability,
                    price_type=bucket.price_type,
                    price_kind=bucket.price_kind,
                    area_band=bucket.area_band,
                    series=series,
                    as_of=as_of,
                    source_ids=tuple(sorted({row.source_id for row in contributors})),
                )
            )

    return sorted(built, key=lambda row: row.key)


def flow_sensitivity(
    observations: Sequence[Observation],
    *,
    as_of: dt.date,
    windows: Iterable[int],
    iqr_switch_n: int,
) -> dict[int, Series]:
    """The flow median at each of several window lengths (V62 c).

    D107 settled the window at 90 days, so this report is evidence kept on the
    record rather than an input to a pending choice. It still runs, because a
    later change of window has to be argued from measurements.
    """
    report: dict[int, Series] = {}
    for window in windows:
        _stock, flow = stock_and_flow(
            observations,
            as_of=as_of,
            flow_window_days=window,
            iqr_switch_n=iqr_switch_n,
        )
        if flow is not None:
            report[window] = flow
    return report
