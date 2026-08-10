"""R8 block B — price per square metre, and the fixed area bands (D48).

An off-by-one at a band edge moves observations between aggregates silently, and
a gap in the ladder drops a whole size segment. Both are invisible in the output,
so both get a test.
"""

from __future__ import annotations

import pathlib
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st
from test_r8_fixtures import observation, warsaw

from dzialki.config import load_params
from dzialki.metrics import AREA_BANDS, band_for

pytestmark = [pytest.mark.unit]


def test_price_per_m2_is_price_divided_by_area() -> None:
    """The aggregate layer consumes an already-normalised area (V10, V28)."""
    row = observation(
        "B1", area_m2="2500", price_pln="300000", first_seen=warsaw(2026, 7, 1)
    )
    assert row.price_per_m2 == 120.00


@pytest.mark.parametrize(
    "area,label",
    [
        (Decimal("799.99"), "<800"),
        (Decimal(800), "800-1500"),
        (Decimal("1499.99"), "800-1500"),
        (Decimal(1500), "1500-3000"),
        (Decimal("2999.99"), "1500-3000"),
        (Decimal(3000), "3000-10000"),
        (Decimal("9999.99"), "3000-10000"),
        (Decimal(10000), ">10000"),
    ],
)
def test_band_boundaries_are_lower_inclusive(area: Decimal, label: str) -> None:
    assert band_for(area) == label


def test_the_band_ladder_is_ordered_and_named_once() -> None:
    assert [band.label for band in AREA_BANDS] == [
        "<800",
        "800-1500",
        "1500-3000",
        "3000-10000",
        ">10000",
    ]


@pytest.mark.property
@given(area=st.integers(min_value=300, max_value=200_000))
def test_every_area_in_the_validity_range_lands_in_exactly_one_band(
    area: int,
) -> None:
    """A gap in the ladder silently drops a whole size segment."""
    label = band_for(Decimal(area))
    matches = [band for band in AREA_BANDS if band.label == label]
    assert len(matches) == 1
    assert sum(1 for band in AREA_BANDS if band.holds(Decimal(area))) == 1


def test_the_property_range_is_the_ratified_validity_range(
    repo_root: pathlib.Path,
) -> None:
    """The bounds above are the ratified ones (O12), not numbers a test chose."""
    params = load_params(repo_root / "config" / "params.yml")
    assert band_for(Decimal(params.validation.area_min_m2)) == "<800"
    assert band_for(Decimal(params.validation.area_max_m2)) == ">10000"


def test_an_area_of_zero_is_an_error() -> None:
    """A plot with no area has no price per square metre either."""
    with pytest.raises(ValueError):
        band_for(Decimal(0))
