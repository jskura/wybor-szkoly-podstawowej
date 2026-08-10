"""S6 §4 — the validity band flags a record. It never drops one.

FR-12 as amended by O12 carries area [300, 200 000] m² and price
[1, 100 000] PLN/m², inclusive at both ends. A record outside the band stays
visible and carries its flag (D85, rule 7).

The 25 ha farmland row is the case O12 was closed for. If the band drops it, a
whole legitimate segment — the product's own subject — disappears.
"""

from __future__ import annotations

import pathlib
from decimal import Decimal

import pytest

from dzialki.config import load_params
from dzialki.normalize.bands import Bands, Flag, band_flags, price_per_m2

pytestmark = [pytest.mark.unit]


@pytest.fixture(scope="module")
def bands(repo_root: pathlib.Path) -> Bands:
    return Bands.from_params(load_params(repo_root / "config" / "params.yml"))


# (row, area_m2, price_per_m2, flags)
BAND_ROWS = [
    ("B1", "299.99", "200.00", {Flag.AREA_BELOW_BAND}),
    ("B2", "300.00", "200.00", set()),
    ("B3", "300.01", "200.00", set()),
    ("B4", "199999.99", "3.00", set()),
    ("B5", "200000.00", "3.00", set()),
    ("B6", "200000.01", "3.00", {Flag.AREA_ABOVE_BAND}),
    ("B7a", "1000.00", "0.99", {Flag.PRICE_BELOW_BAND}),
    ("B7b", "1000.00", "1.00", set()),
    ("B7c", "1000.00", "1.01", set()),
    ("B8a", "1000.00", "99999.99", set()),
    ("B8b", "1000.00", "100000.00", set()),
    ("B8c", "1000.00", "100000.01", {Flag.PRICE_ABOVE_BAND}),
    ("B9", "250000.00", "3.00", {Flag.AREA_ABOVE_BAND}),
    ("B10", "250.00", "400.00", {Flag.AREA_BELOW_BAND}),
    ("B11", "200000.01", "0.50", {Flag.AREA_ABOVE_BAND, Flag.PRICE_BELOW_BAND}),
]


@pytest.mark.parametrize(
    "area,quotient,flags",
    [row[1:] for row in BAND_ROWS],
    ids=[row[0] for row in BAND_ROWS],
)
def test_band_flags_exact(
    bands: Bands, area: str, quotient: str, flags: set[Flag]
) -> None:
    assert band_flags(Decimal(area), Decimal(quotient), bands=bands) == frozenset(flags)


def test_band_constants_match_amended_fr12(bands: Bands) -> None:
    assert bands.area == (Decimal(300), Decimal(200000))
    assert bands.price_per_m2 == (Decimal(1), Decimal(100000))


def test_superseded_band_values_are_not_in_band_constants(bands: Bands) -> None:
    """V10's prose carried 100–500 000 m² before O12 amended it.

    A constant copied from that prose quietly discards 20–50 ha farmland, which
    is the exact outcome O12 was closed to prevent.
    """
    assert bands.area != (Decimal(100), Decimal(500000))
    assert bands.area[0] != Decimal(100)
    assert bands.area[1] != Decimal(500000)


def test_the_superseded_value_check_catches_the_stale_band() -> None:
    """Non-vacuity companion for the scan above.

    A check for absence proves nothing until a real occurrence trips it.
    """
    stale = Bands(
        area=(Decimal(100), Decimal(500000)),
        price_per_m2=(Decimal(1), Decimal(100000)),
    )
    assert (stale.area[0] != Decimal(100)) is False
    assert band_flags(Decimal(250000), Decimal("3.00"), bands=stale) == frozenset()


def test_the_band_comes_from_the_ratified_file(
    repo_root: pathlib.Path, bands: Bands
) -> None:
    """V65 — the area band lives in `config/params.yml`, not in the code."""
    params = load_params(repo_root / "config" / "params.yml")
    assert bands.area == (
        Decimal(params.validation.area_min_m2),
        Decimal(params.validation.area_max_m2),
    )


def test_band_check_is_inclusive_at_all_four_edges(bands: Bands) -> None:
    """One statement, so a `<` to `<=` mutant at any edge dies here."""
    assert band_flags(Decimal("300.00"), Decimal("200.00"), bands=bands) == frozenset()
    assert band_flags(Decimal("200000.00"), Decimal("3.00"), bands=bands) == frozenset()
    assert band_flags(Decimal("1000.00"), Decimal("1.00"), bands=bands) == frozenset()
    assert (
        band_flags(Decimal("1000.00"), Decimal("100000.00"), bands=bands) == frozenset()
    )


def test_band_flags_returns_a_frozenset(bands: Bands) -> None:
    """A caller cannot mutate the answer into agreement."""
    flags = band_flags(Decimal("200000.01"), Decimal("0.50"), bands=bands)
    assert isinstance(flags, frozenset)
    assert flags == frozenset({Flag.AREA_ABOVE_BAND, Flag.PRICE_BELOW_BAND})


def test_no_band_flag_implies_an_empty_frozenset(bands: Bands) -> None:
    """A `None` return makes `if flags:` and `if flags is not None:` disagree."""
    flags = band_flags(Decimal("300.00"), Decimal("200.00"), bands=bands)
    assert flags == frozenset()
    assert flags is not None


def test_both_edges_can_be_violated_at_once(bands: Bands) -> None:
    """B11 — a frozenset of two, not the first flag found."""
    flags = band_flags(Decimal("200000.01"), Decimal("0.50"), bands=bands)
    assert len(flags) == 2


def test_out_of_band_area_is_flagged_not_dropped(bands: Bands) -> None:
    """B9, the O12 case: 25 ha farmland at 3 zł/m².

    `band_flags` returns a flag. It has no way to drop a record, and that is
    the point of the split between flagging and quarantine.
    """
    flags = band_flags(Decimal("250000.00"), Decimal("3.00"), bands=bands)
    assert flags == frozenset({Flag.AREA_ABOVE_BAND})


def test_band_flags_raises_on_a_non_positive_area(bands: Bands) -> None:
    """B13 — a zero area is quarantined upstream as `area_non_positive`.

    `band_flags` refuses it rather than dividing by it.
    """
    with pytest.raises(ValueError):
        band_flags(Decimal(0), Decimal("200.00"), bands=bands)
    with pytest.raises(ValueError):
        band_flags(Decimal(-1), Decimal("200.00"), bands=bands)


# --- D88, the exact quotient ----------------------------------------------


def test_price_per_m2_is_the_exact_quotient() -> None:
    """300 000,01 / 3,00 is 100 000,00333…, not 100 000,00."""
    quotient = price_per_m2(Decimal("300000.01"), Decimal("3.00"))
    assert quotient > Decimal(100000)
    assert quotient.quantize(Decimal("0.01")) == Decimal("100000.00")


def test_band_check_reads_the_exact_quotient(bands: Bands) -> None:
    """B12 — the record sits on the edge once stored, and is above it in truth."""
    exact = price_per_m2(Decimal("300000.01"), Decimal("3.00"))
    assert band_flags(Decimal("3.00"), exact, bands=bands) == frozenset(
        {Flag.PRICE_ABOVE_BAND, Flag.AREA_BELOW_BAND}
    )


def test_band_check_does_not_read_the_rounded_value(bands: Bands) -> None:
    """The same input quantised to NUMERIC(12,2) is inside the band.

    An implementation that reads the stored column fails this test.
    """
    stored = price_per_m2(Decimal("300000.01"), Decimal("3.00")).quantize(
        Decimal("0.01")
    )
    assert Flag.PRICE_ABOVE_BAND not in band_flags(Decimal("3.00"), stored, bands=bands)


def test_price_per_m2_refuses_a_non_positive_area() -> None:
    with pytest.raises(ValueError):
        price_per_m2(Decimal(250000), Decimal(0))


def test_price_per_m2_returns_decimal_not_float() -> None:
    assert isinstance(price_per_m2(Decimal(240000), Decimal(1200)), Decimal)
    assert price_per_m2(Decimal(240000), Decimal(1200)) == Decimal(200)


def test_scaling_price_and_area_together_leaves_price_per_m2_unchanged() -> None:
    """The F1-adjacent metamorphic check, stated on the quotient itself."""
    base = price_per_m2(Decimal(240000), Decimal(1200))
    scaled = price_per_m2(Decimal(2400000), Decimal(12000))
    assert base == scaled


def test_band_flags_is_monotone_in_area(bands: Bands) -> None:
    """Above the edge, every larger area is flagged. No interior hole."""
    for area in ("200000.01", "250000", "500000", "1000000"):
        assert Flag.AREA_ABOVE_BAND in band_flags(
            Decimal(area), Decimal("3.00"), bands=bands
        )


def test_the_monotonicity_check_catches_a_one_sided_band() -> None:
    """Non-vacuity companion: a band that checks only the lower edge."""
    one_sided = Bands(
        area=(Decimal(300), Decimal(100000000)),
        price_per_m2=(Decimal(1), Decimal(100000)),
    )
    assert Flag.AREA_ABOVE_BAND not in band_flags(
        Decimal(250000), Decimal("3.00"), bands=one_sided
    )
