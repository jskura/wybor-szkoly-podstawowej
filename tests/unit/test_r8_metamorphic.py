"""R8 §5 — the metamorphic suite, with a non-vacuity companion for each relation.

There is no ground truth for a land price, so these tests relate one output to
another instead of to an oracle. That is also their weakness: a relation between
outputs can hold trivially. Every relation below therefore ships with a companion
that runs the same assertion block against a deliberately broken builder and
asserts the block raises.

M4 (dedup) and M5/M6 (the comparable filters) are not here. Dedup is S7's work
item and comparable selection is S9's; this stage computes over the set it is
handed.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import pathlib
from decimal import Decimal

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from test_r8_fixtures import (
    AS_OF,
    C1,
    C2,
    C3,
    C4,
    C5,
    CANONICAL,
    OUTLIER,
    Z1,
    Z2,
    shift_months,
)

from dzialki.config import load_params
from dzialki.metrics import (
    Observation,
    aggregate,
    in_flow_window,
    round_for_storage,
    stock_and_flow,
)

pytestmark = [pytest.mark.unit]


@pytest.fixture(scope="module")
def params(repo_root: pathlib.Path):
    return load_params(repo_root / "config" / "params.yml")


def build(observations, params, *, as_of=AS_OF):
    """The comparable-set view. One set, both series."""
    return stock_and_flow(
        observations,
        as_of=as_of,
        flow_window_days=params.aggregates.flow_window_days,
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


def median_of(observations, params) -> Decimal:
    return build(observations, params)[0].median_ppm2


def blind_median(observations, params) -> Decimal:
    """A price-blind builder. Its ppm2 ignores the price entirely."""
    values = sorted(float(row.area_m2) / 100 for row in observations)
    middle = len(values) // 2
    if len(values) % 2:
        return round_for_storage(values[middle])
    return round_for_storage((values[middle - 1] + values[middle]) / 2)


# --- M1 · doubling every price doubles the median exactly -----------------


def double_prices(observations) -> list[Observation]:
    return [
        dataclasses.replace(row, price_pln=row.price_pln * 2) for row in observations
    ]


def _m1_relation(observations, doubled, median) -> None:
    assert median(doubled) == median(observations) * 2


def test_doubling_every_price_doubles_the_median_exactly(params) -> None:
    doubled = double_prices(CANONICAL)
    stock, _flow = build(doubled, params)
    # Exact equality, not `isclose`. Doubling is exact in binary at these sizes.
    assert stock.median_ppm2 == Decimal("252.00")
    assert stock.p25_ppm2 == Decimal("220.00")
    assert stock.p75_ppm2 == Decimal("280.00")
    assert stock.min_ppm2 == Decimal("192.00")
    assert stock.max_ppm2 == Decimal("300.00")
    assert stock.n == 5
    assert stock.range_kind == "iqr"
    _m1_relation(CANONICAL, doubled, lambda rows: median_of(rows, params))


def test_m1_is_not_vacuous(params) -> None:
    """A price-blind builder satisfies nothing and would still look tested."""
    doubled = double_prices(CANONICAL)
    assert blind_median(CANONICAL, params) == Decimal("30.00")
    assert blind_median(doubled, params) == Decimal("30.00")
    with pytest.raises(AssertionError):
        _m1_relation(CANONICAL, doubled, lambda rows: blind_median(rows, params))


# --- M2 · scaling price and area together leaves ppm2 unchanged -----------


def scale_both(observations, factor: int) -> list[Observation]:
    return [
        dataclasses.replace(
            row, price_pln=row.price_pln * factor, area_m2=row.area_m2 * factor
        )
        for row in observations
    ]


def scale_price_only(observations, factor: int) -> list[Observation]:
    return [
        dataclasses.replace(row, price_pln=row.price_pln * factor)
        for row in observations
    ]


def _m2_relation(baseline, scaled) -> None:
    assert scaled == baseline


def test_scaling_price_and_area_together_leaves_price_per_m2_unchanged(
    params,
) -> None:
    """The subject scales with the set, so the comparable window scales too and
    all five rows stay in."""
    baseline = build(CANONICAL, params)
    scaled = build(scale_both(CANONICAL, 10), params)
    _m2_relation(baseline, scaled)
    assert scaled[0].median_ppm2 == Decimal("126.00")
    assert scaled[1].median_ppm2 == Decimal("118.00")


def test_scaling_collapses_the_banded_rows_into_one_band(params) -> None:
    """The D66 view needs its own assertion. The scaled rows all land in
    `>10000`, so two bands become one and there is no baseline row to compare."""
    rows = banded(scale_both(CANONICAL, 10), params)
    assert {row.area_band for row in rows} == {">10000"}
    assert len(rows) == 2

    stock = pick(rows, series_kind="stock")
    assert stock.n == 5
    assert stock.median_ppm2 == Decimal("126.00")
    assert stock.p25_ppm2 == Decimal("110.00")
    assert stock.p75_ppm2 == Decimal("140.00")
    assert stock.range_kind == "iqr"

    flow = pick(rows, series_kind="flow")
    assert flow.n == 4
    assert flow.median_ppm2 == Decimal("118.00")
    assert flow.p25_ppm2 == Decimal("106.50")
    assert flow.p75_ppm2 == Decimal("129.50")
    assert flow.range_kind == "min_max"


def test_m2_is_not_vacuous(params) -> None:
    """The trap the relation exists for: scaling one and not the other."""
    baseline = build(CANONICAL, params)
    price_only = build(scale_price_only(CANONICAL, 10), params)
    assert price_only[0].median_ppm2 == Decimal("1260.00")
    with pytest.raises(AssertionError):
        _m2_relation(baseline, price_only)


# --- M3 · permuting input order changes nothing ---------------------------


def _m3_relation(baseline, permuted) -> None:
    assert permuted == baseline


def test_permuting_input_order_changes_nothing(params) -> None:
    baseline = sorted(banded(CANONICAL, params), key=lambda row: row.key)
    permuted = sorted(banded([C4, C1, C5, C2, C3], params), key=lambda row: row.key)
    # Full dataclass equality, not just the median. This catches order
    # dependence in grouping and in tie-breaking.
    _m3_relation(baseline, permuted)


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(order=st.permutations(CANONICAL))
def test_any_permutation_gives_the_same_rows(params, order) -> None:
    baseline = sorted(banded(CANONICAL, params), key=lambda row: row.key)
    assert sorted(banded(list(order), params), key=lambda row: row.key) == baseline


def test_m3_is_not_vacuous(params) -> None:
    """A builder that reads the middle of the *unsorted* list returns 150.00 on
    this permutation. The reversed permutation would return 126.00 and let the
    companion pass vacuously, so it is not the one used."""
    permutation = [C4, C1, C5, C2, C3]

    def unsorted_middle(observations) -> Decimal:
        values = [row.price_per_m2 for row in observations]
        return round_for_storage(values[len(values) // 2])

    assert unsorted_middle(permutation) == Decimal("150.00")
    assert unsorted_middle(CANONICAL) == Decimal("126.00")
    with pytest.raises(AssertionError):
        _m3_relation(
            unsorted_middle(CANONICAL),
            unsorted_middle(permutation),
        )


# --- M7 · shifting the observations and the window together ---------------


def shift_all(observations, months: int) -> list[Observation]:
    return [
        dataclasses.replace(
            row,
            first_seen=shift_months(row.first_seen, months),
            observed_at=shift_months(row.observed_at, months),
        )
        for row in observations
    ]


def _m7_relation(baseline, shifted) -> None:
    assert [row.median_ppm2 for row in shifted] == [row.median_ppm2 for row in baseline]
    assert [row.n for row in shifted] == [row.n for row in baseline]


def test_shifting_observations_and_the_window_together_changes_nothing(
    params,
) -> None:
    """A calendar month is 30 or 31 days while the window is a fixed 90, so the
    invariance holds only because no row sits within a month of the cutoff. C1 is
    the closest: 41 days inside before the shift and 40 days after."""
    baseline = build(CANONICAL, params)
    shifted = build(shift_all(CANONICAL, 1), params, as_of=dt.date(2026, 9, 8))
    _m7_relation(baseline, shifted)
    assert shifted[0].median_ppm2 == Decimal("126.00")
    assert shifted[1].median_ppm2 == Decimal("118.00")
    assert shifted[0].median_ppm2 - shifted[1].median_ppm2 == Decimal("8.00")

    rows = banded(shift_all(CANONICAL, 1), params, as_of=dt.date(2026, 9, 8))
    assert {row.month for row in rows} == {dt.date(2026, 9, 1)}
    assert pick(rows, area_band="3000-10000", series_kind="stock").median_ppm2 == (
        Decimal("140.00")
    )
    assert pick(rows, area_band="3000-10000", series_kind="flow").median_ppm2 == (
        Decimal("133.00")
    )


def test_m7_is_not_vacuous(params) -> None:
    """Shift the observations by one month and the valuation date by three. C1
    then drops out of flow. Both dates stay in the past, so the input is legal.

    The plan gives p25 111.00 and p75 138.00 here. Those belong to
    [96, 126, 150], not to this set. R-7 over [110, 126, 140] gives 118.00 and
    133.00. §3.2's 30-day row carries the same copy error.
    """
    baseline = build(CANONICAL, params)
    shifted = build(shift_all(CANONICAL, 1), params, as_of=dt.date(2026, 11, 8))
    flow = shifted[1]
    assert flow.n == 3
    assert flow.median_ppm2 == Decimal("126.00")
    assert flow.p25_ppm2 == Decimal("118.00")
    assert flow.p75_ppm2 == Decimal("133.00")
    assert flow.min_ppm2 == Decimal("110.00")
    assert flow.max_ppm2 == Decimal("140.00")
    assert flow.range_kind == "min_max"
    with pytest.raises(AssertionError):
        _m7_relation(baseline, shifted)


def test_a_month_boundary_follows_the_warsaw_calendar(params) -> None:
    """F10. Both instants fall on 30 June in UTC. Only the Warsaw calendar
    separates them."""
    rows = banded([Z1, Z2], params)
    june = pick(rows, month=dt.date(2026, 6, 1), series_kind="stock")
    july = pick(rows, month=dt.date(2026, 7, 1), series_kind="stock")
    assert june.n == 1
    assert june.median_ppm2 == Decimal("100.00")
    assert july.n == 1
    assert july.median_ppm2 == Decimal("200.00")
    # A UTC bucket puts both in June: n 2, median 150.00, and July absent.
    assert Decimal("150.00") not in {row.median_ppm2 for row in rows}


def test_the_month_boundary_pair_survives_a_shift(params) -> None:
    rows = banded(shift_all([Z1, Z2], 1), params, as_of=dt.date(2026, 9, 8))
    months = {row.month for row in rows}
    assert months == {dt.date(2026, 7, 1), dt.date(2026, 8, 1)}
    assert pick(rows, month=dt.date(2026, 7, 1), series_kind="stock").median_ppm2 == (
        Decimal("100.00")
    )
    assert pick(rows, month=dt.date(2026, 8, 1), series_kind="stock").median_ppm2 == (
        Decimal("200.00")
    )


# --- M8 · a far outlier moves the median little and the mean a lot --------


def _m8_relation(published: Decimal) -> None:
    assert published == Decimal("133.00")


def test_a_far_outlier_moves_the_median_little_and_the_mean_a_lot(params) -> None:
    stock, _flow = build([*CANONICAL, OUTLIER], params)
    assert stock.n == 6
    assert stock.median_ppm2 == Decimal("133.00")
    assert stock.p25_ppm2 == Decimal("114.00")
    assert stock.p75_ppm2 == Decimal("147.50")
    assert stock.min_ppm2 == Decimal("96.00")
    assert stock.max_ppm2 == Decimal("5000.00")
    assert stock.range_kind == "iqr"

    baseline, _ = build(CANONICAL, params)
    # The median moves 7.00. The mean moves 812.60.
    assert stock.median_ppm2 - baseline.median_ppm2 == Decimal("7.00")
    assert baseline.mean_ppm2 == Decimal("124.40")
    assert stock.mean_ppm2 - baseline.mean_ppm2 == Decimal("812.60")

    _m8_relation(stock.median_ppm2)
    # The published figure is the median. The mean appears in no displayed field.
    displayed = {
        stock.median_ppm2,
        stock.p25_ppm2,
        stock.p75_ppm2,
        stock.min_ppm2,
        stock.low,
        stock.high,
    }
    assert Decimal("937.00") not in displayed


def test_m8_is_not_vacuous(params) -> None:
    """Two parts. The mean proves the outlier entered the set; without it, a
    filter that quietly dropped it would make the claim trivially true."""
    stock, _flow = build([*CANONICAL, OUTLIER], params)
    assert stock.mean_ppm2 == Decimal("937.00")
    with pytest.raises(AssertionError):
        _m8_relation(stock.mean_ppm2)


def test_the_far_outlier_is_reachable(params) -> None:
    """M8 rests on the outlier passing every filter this stage applies."""
    assert OUTLIER.price_per_m2 == 5000.0
    stock, flow = build([*CANONICAL, OUTLIER], params)
    assert stock.max_ppm2 == Decimal("5000.00")
    assert flow.max_ppm2 == Decimal("5000.00")


def test_c5_is_the_only_row_outside_the_flow_window(params) -> None:
    """Named here because every gap in this module rests on it."""
    window = params.aggregates.flow_window_days
    membership = {
        row.listing_id: in_flow_window(row, as_of=AS_OF, flow_window_days=window)
        for row in CANONICAL
    }
    assert membership == {"C1": True, "C2": True, "C3": True, "C4": True, "C5": False}
