"""R8 §7 — stock and flow, and the gap the stale listing puts between them.

The flow window is 90 days (D107). C5 was first seen 493 days before the
valuation date, is still active, and is the most expensive plot in the set. It is
therefore in stock and out of flow, and it lifts the stock median above the flow
median by a constructed amount.

Every flow figure states its window. A flow median without one says nothing.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import pathlib
from decimal import Decimal

import pytest
from test_r8_fixtures import (
    AS_OF,
    C5,
    CANONICAL,
    WINDOW_SENSITIVITY,
    observation,
    warsaw,
)

from dzialki.config import load_params
from dzialki.metrics import (
    Series,
    aggregate,
    flow_sensitivity,
    headline,
    in_flow_window,
    stock_and_flow,
)

pytestmark = [pytest.mark.unit]

SENSITIVITY_WINDOWS = (30, 60, 90, 180)


@pytest.fixture(scope="module")
def params(repo_root: pathlib.Path):
    return load_params(repo_root / "config" / "params.yml")


def series_pair(observations, params, *, as_of=AS_OF, flow_window_days=None):
    """The comparable-set view: one set, both series, one call."""
    return stock_and_flow(
        observations,
        as_of=as_of,
        flow_window_days=flow_window_days or params.aggregates.flow_window_days,
        iqr_switch_n=params.aggregates.iqr_switch_n,
    )


def banded(observations, params, *, as_of=AS_OF):
    return aggregate(
        observations,
        as_of=as_of,
        flow_window_days=params.aggregates.flow_window_days,
        iqr_switch_n=params.aggregates.iqr_switch_n,
    )


def pick(rows, **criteria):
    found = [
        row
        for row in rows
        if all(getattr(row, name) == value for name, value in criteria.items())
    ]
    assert len(found) == 1, f"{len(found)} rows match {criteria}"
    return found[0]


# --- S1 · the constructed gap ---------------------------------------------


def test_the_stale_listing_lifts_the_stock_median_above_the_flow_median(
    params,
) -> None:
    stock, flow = series_pair(CANONICAL, params)

    assert stock.median_ppm2 == Decimal("126.00")
    assert flow.median_ppm2 == Decimal("118.00")
    # The relation itself, pinned rather than implied by the two values above.
    assert stock.median_ppm2 - flow.median_ppm2 == Decimal("8.00")

    assert stock.n == 5
    assert stock.p25_ppm2 == Decimal("110.00")
    assert stock.p75_ppm2 == Decimal("140.00")
    assert stock.min_ppm2 == Decimal("96.00")
    assert stock.max_ppm2 == Decimal("150.00")
    assert stock.range_kind == "iqr"

    assert flow.n == 4
    assert flow.p25_ppm2 == Decimal("106.50")
    assert flow.p75_ppm2 == Decimal("129.50")
    assert flow.min_ppm2 == Decimal("96.00")
    assert flow.max_ppm2 == Decimal("140.00")
    assert flow.range_kind == "min_max"


def test_the_banded_gaps_name_their_view(params) -> None:
    """The 8.00 above is the comparable-set gap. The D66 rows give 7.00 and 0.00.

    The 0.00 is not filler. A gap in both bands would mean something other than
    C5 produces it.
    """
    rows = banded(CANONICAL, params)

    upper_stock = pick(rows, area_band="3000-10000", series_kind="stock")
    upper_flow = pick(rows, area_band="3000-10000", series_kind="flow")
    assert upper_stock.median_ppm2 == Decimal("140.00")
    assert upper_flow.median_ppm2 == Decimal("133.00")
    assert upper_stock.median_ppm2 - upper_flow.median_ppm2 == Decimal("7.00")

    lower_stock = pick(rows, area_band="1500-3000", series_kind="stock")
    lower_flow = pick(rows, area_band="1500-3000", series_kind="flow")
    assert lower_stock.median_ppm2 == Decimal("103.00")
    assert lower_flow.median_ppm2 == Decimal("103.00")
    assert lower_stock.median_ppm2 - lower_flow.median_ppm2 == Decimal("0.00")


# --- S2 · both series are labelled ----------------------------------------


def test_both_series_are_labelled_and_neither_is_ever_unlabelled(params) -> None:
    stock, flow = series_pair(CANONICAL, params)
    assert stock.series_kind == "stock"
    assert flow.series_kind == "flow"
    assert isinstance(stock, Series)
    assert isinstance(flow, Series)

    for row in banded(CANONICAL, params):
        assert row.series_kind in {"stock", "flow"}
        assert row.series_kind is not None


@pytest.mark.architecture
def test_the_series_label_has_no_default_and_no_none_member() -> None:
    label = {field.name: field for field in dataclasses.fields(Series)}["series_kind"]
    assert label.default is dataclasses.MISSING
    with pytest.raises(ValueError):
        Series(series_kind="neither", flow_window_days=None, spread=None)  # type: ignore[arg-type]


# --- S3 · flow is the headline (D56) --------------------------------------


def test_flow_is_the_headline(params) -> None:
    stock, flow = series_pair(CANONICAL, params)
    assert headline(stock, flow) is flow


def test_the_headline_helper_refuses_half_a_pair(params) -> None:
    """One series alone cannot say which figure is secondary."""
    stock, flow = series_pair(CANONICAL, params)
    with pytest.raises(ValueError):
        headline(stock, None)
    with pytest.raises(ValueError):
        headline(None, flow)


# --- S4 · never averaged ---------------------------------------------------


def test_stock_and_flow_are_never_averaged(params) -> None:
    """The mirror of the price-separation scan. 122.00 is the mean of 126 and 118."""
    stock, flow = series_pair(CANONICAL, params)
    rows = banded(CANONICAL, params)
    forbidden = {Decimal("122.00"), Decimal("136.50"), Decimal("110.50")}

    values = set()
    for row in (stock, flow, *rows):
        values.update(
            value
            for value in (
                row.median_ppm2,
                row.p25_ppm2,
                row.p75_ppm2,
                row.min_ppm2,
                row.max_ppm2,
                row.low,
                row.high,
            )
            if value is not None
        )
    # 136.50 is a legitimate p75 in the 3000-10000 flow row, so the medians are
    # what the scan can speak for.
    medians = {row.median_ppm2 for row in (stock, flow, *rows)}
    assert not (medians & forbidden)
    assert Decimal("122.00") not in values


# --- S5 · removing the stale listing collapses the gap --------------------


def test_removing_the_stale_listing_collapses_the_gap(params) -> None:
    """Proves S1's gap comes from C5 and not from how the two sets are built."""
    without = [row for row in CANONICAL if row is not C5]
    stock, flow = series_pair(without, params)
    assert stock == dataclasses.replace(
        flow, series_kind="stock", flow_window_days=None
    )
    assert stock.median_ppm2 == Decimal("118.00")
    assert flow.median_ppm2 == Decimal("118.00")
    assert stock.median_ppm2 - flow.median_ppm2 == Decimal("0.00")
    assert stock.n == 4

    rows = banded(without, params)
    upper_stock = pick(rows, area_band="3000-10000", series_kind="stock")
    upper_flow = pick(rows, area_band="3000-10000", series_kind="flow")
    assert upper_stock.median_ppm2 == Decimal("133.00")
    assert upper_flow.median_ppm2 == Decimal("133.00")
    assert pick(rows, area_band="1500-3000", series_kind="stock").median_ppm2 == (
        Decimal("103.00")
    )


# --- S6 · the window boundary ---------------------------------------------


@pytest.mark.parametrize(
    "first_seen,expected",
    [
        (dt.date(2026, 5, 11), True),
        (dt.date(2026, 5, 10), True),  # the cutoff itself is inclusive
        (dt.date(2026, 5, 9), False),
    ],
)
def test_flow_window_boundary_is_inclusive(
    params, first_seen: dt.date, expected: bool
) -> None:
    row = observation(
        "edge",
        area_m2="3000",
        price_pln="300000",
        first_seen=warsaw(first_seen.year, first_seen.month, first_seen.day),
    )
    assert (
        in_flow_window(
            row, as_of=AS_OF, flow_window_days=params.aggregates.flow_window_days
        )
        is expected
    )


def test_a_shorter_window_moves_the_oldest_listing_out_of_flow(params) -> None:
    """D107 fixes the value. The constant stays in configuration so the
    sensitivity report can vary it.

    The plan's §3.2 gives p25 111.00 and p75 138.00 for this row. Those are the
    percentiles of `SPREAD_N3` = [96, 126, 150], copied one row across. The
    30-day flow set is [110, 126, 140], and R-7 gives 118.00 and 133.00.
    """
    _stock, flow = series_pair(CANONICAL, params, flow_window_days=30)
    assert flow.n == 3
    assert flow.median_ppm2 == Decimal("126.00")
    assert flow.p25_ppm2 == Decimal("118.00")
    assert flow.p75_ppm2 == Decimal("133.00")
    assert flow.min_ppm2 == Decimal("110.00")
    assert flow.max_ppm2 == Decimal("140.00")
    assert flow.range_kind == "min_max"


# --- S7 · every flow figure states its window -----------------------------


def test_every_flow_figure_carries_its_window_length(params) -> None:
    stock, flow = series_pair(CANONICAL, params)
    assert flow.flow_window_days == params.aggregates.flow_window_days
    assert flow.flow_window_days == 90
    assert stock.flow_window_days is None

    for row in banded(CANONICAL, params):
        if row.series_kind == "flow":
            assert row.flow_window_days == 90
        else:
            assert row.flow_window_days is None


def test_a_flow_series_without_its_window_cannot_be_built() -> None:
    with pytest.raises(ValueError):
        Series(series_kind="flow", flow_window_days=None, spread=None)  # type: ignore[arg-type]


# --- S8 · the window sensitivity report -----------------------------------


@pytest.mark.parametrize(
    "window,n,median,p25,p75,minimum,maximum,kind",
    [
        (30, 3, "140.00", "120.00", "160.00", "100.00", "180.00", "min_max"),
        (60, 5, "100.00", "80.00", "140.00", "60.00", "180.00", "iqr"),
        (90, 7, "80.00", "50.00", "120.00", "20.00", "180.00", "iqr"),
        (180, 9, "60.00", "20.00", "100.00", "10.00", "180.00", "iqr"),
    ],
)
def test_window_sensitivity_report_covers_thirty_sixty_ninety_and_one_eighty(
    params,
    window: int,
    n: int,
    median: str,
    p25: str,
    p75: str,
    minimum: str,
    maximum: str,
    kind: str,
) -> None:
    """V62 (c). The window is settled at 90 days, so this report is evidence kept
    on the record, not an input to a pending choice."""
    report = flow_sensitivity(
        WINDOW_SENSITIVITY,
        as_of=AS_OF,
        windows=SENSITIVITY_WINDOWS,
        iqr_switch_n=params.aggregates.iqr_switch_n,
    )
    assert sorted(report) == sorted(SENSITIVITY_WINDOWS)
    series = report[window]
    assert series.series_kind == "flow"
    assert series.flow_window_days == window
    assert series.n == n
    assert series.median_ppm2 == Decimal(median)
    assert series.p25_ppm2 == Decimal(p25)
    assert series.p75_ppm2 == Decimal(p75)
    assert series.min_ppm2 == Decimal(minimum)
    assert series.max_ppm2 == Decimal(maximum)
    assert series.range_kind == kind


def test_the_sensitivity_medians_are_four_distinct_values(params) -> None:
    """The canonical five give only two distinct medians and cannot exercise the
    report. This fixture gives four, and they fall monotonically."""
    report = flow_sensitivity(
        WINDOW_SENSITIVITY,
        as_of=AS_OF,
        windows=SENSITIVITY_WINDOWS,
        iqr_switch_n=params.aggregates.iqr_switch_n,
    )
    medians = [report[window].median_ppm2 for window in SENSITIVITY_WINDOWS]
    assert medians == [
        Decimal("140.00"),
        Decimal("100.00"),
        Decimal("80.00"),
        Decimal("60.00"),
    ]
    assert len(set(medians)) == 4


def test_the_sensitivity_stock_matches_the_widest_window(params) -> None:
    """Every listing is active, so stock equals the 180-day flow figure and the
    stock minus flow gap at 90 days is 20.00."""
    stock, flow = series_pair(WINDOW_SENSITIVITY, params)
    assert stock.n == 9
    assert stock.median_ppm2 == Decimal("60.00")
    assert flow.median_ppm2 == Decimal("80.00")
    assert stock.median_ppm2 - flow.median_ppm2 == Decimal("-20.00")
