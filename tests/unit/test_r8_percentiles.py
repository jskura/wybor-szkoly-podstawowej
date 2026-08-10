"""R8 block A — the percentile function and the one rounding boundary.

F11 is the silent-failure mode these tests exist for: percentile conventions
differ, and picking one by accident produces slightly wrong ranges forever.
A5 writes the convention down. A7 writes the rounding down.

`percentiles()` returns unrounded floats so §4's differential test can compare
against numpy. `round_for_storage` is the single place a figure becomes a stored
`NUMERIC(12,2)`.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from dzialki.metrics import PERCENTILE_METHOD, percentiles, round_for_storage

pytestmark = [pytest.mark.unit]


def test_percentiles_of_five_pins_every_statistic() -> None:
    result = percentiles([96, 110, 126, 140, 150])
    # Five assertions, not one on a tuple, so a failure names the statistic.
    assert result.median == 126.00
    assert result.p25 == 110.00
    assert result.p75 == 140.00
    assert result.minimum == 96.00
    assert result.maximum == 150.00
    assert result.n == 5


def test_percentiles_of_even_length_interpolates() -> None:
    """An implementation returning a middle element returns 96 or 140 here."""
    result = percentiles([61, 96, 140, 240])
    assert result.median == 118.00
    assert result.p25 == 87.25
    assert result.p75 == 165.00
    assert result.minimum == 61.00
    assert result.maximum == 240.00


def test_percentiles_of_one() -> None:
    """A degenerate range is still a range (V4). This must not raise."""
    result = percentiles([118])
    assert result.median == 118.00
    assert result.p25 == 118.00
    assert result.p75 == 118.00
    assert result.minimum == 118.00
    assert result.maximum == 118.00
    assert result.n == 1


def test_percentiles_of_two() -> None:
    result = percentiles([100, 200])
    assert result.median == 150.00
    assert result.p25 == 125.00
    assert result.p75 == 175.00


def test_percentile_convention_is_linear_r7() -> None:
    """The canary. It pins the convention, not an implementation accident."""
    result = percentiles([1, 2, 3, 4])
    assert result.p25 == 1.75
    assert result.p75 == 3.25
    assert result.p25 != 1.0  # lower
    assert result.p25 != 1.5  # midpoint
    assert result.p25 != 2.0  # nearest, and higher
    assert PERCENTILE_METHOD == "linear"


def test_the_arithmetic_mean_is_computed_and_kept_apart() -> None:
    """FR-24 stores the mean. M8 pins that it is never the displayed figure."""
    assert percentiles([96, 110, 126, 140, 150]).mean == 124.40


def test_percentiles_of_nothing_is_an_error() -> None:
    """Absence of data is absence. A zero here would reach the map as a price."""
    with pytest.raises(ValueError):
        percentiles([])


@pytest.mark.property
@given(st.lists(st.floats(1, 100_000), min_size=1, max_size=500))
def test_p25_never_exceeds_median_never_exceeds_p75(values: list[float]) -> None:
    """A partial kill for the p25/p75 swap mutant. A5 is the full kill."""
    result = percentiles(values)
    assert result.minimum <= result.p25
    assert result.p25 <= result.median
    assert result.median <= result.p75
    assert result.p75 <= result.maximum


# --- A7 · rounding, once, on storage --------------------------------------


@pytest.mark.parametrize(
    "value,expected,wrong_mode",
    [
        # Exactly representable, so the conversion path cannot affect them.
        # These pin the rounding mode.
        (1.125, Decimal("1.13"), Decimal("1.12")),
        (0.125, Decimal("0.13"), Decimal("0.12")),
        # Not representable. `Decimal(1.005)` is 1.00499999... and ROUND_HALF_UP
        # then gives 1.00. These pin the conversion path through `str`.
        (1.005, Decimal("1.01"), Decimal("1.00")),
        (2.675, Decimal("2.68"), Decimal("2.67")),
    ],
)
def test_storage_rounds_half_up_through_a_string(
    value: float, expected: Decimal, wrong_mode: Decimal
) -> None:
    assert round_for_storage(value) == expected
    assert round_for_storage(value) != wrong_mode


def test_percentiles_stay_unrounded_for_the_differential_test() -> None:
    """Rounding inside `percentiles` would hide a convention error from numpy."""
    result = percentiles([1.005, 1.005])
    assert result.median == 1.005
    assert round_for_storage(result.median) == Decimal("1.01")
