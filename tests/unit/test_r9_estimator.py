"""S9 — the comparable estimator, its absences, and its verdict.

The canonical set is five observations at 96, 110, 126, 140 and 150 złotych per
square metre in one gmina. Every test below either uses it or perturbs it by one
thing, so a failure names the filter that broke.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from dzialki.config import load_params
from dzialki.valuation import (
    Absence,
    Candidate,
    Estimate,
    Subject,
    area_band,
    estimate,
    recency_cutoff,
    select_comparables,
    verdict,
)

pytestmark = [pytest.mark.unit]

AS_OF = dt.date(2026, 8, 8)
GMINA_A = "9901011"
GMINA_B = "9902011"


@pytest.fixture(scope="module")
def params(request):
    return load_params(request.config.rootpath / "config" / "params.yml")


def candidate(
    listing_id: int,
    ppm2: str,
    *,
    area_m2: str = "3000.00",
    teryt: str = GMINA_A,
    buildability: str = "buildable",
    asset_class: str = "land_building",
    observed_at: dt.date = dt.date(2026, 7, 1),
    price_kind: str = "asking",
) -> Candidate:
    return Candidate(
        listing_id=listing_id,
        area_m2=Decimal(area_m2),
        teryt_gmina=teryt,
        asset_class=asset_class,
        buildability=buildability,
        price_per_m2=Decimal(ppm2),
        observed_at=observed_at,
        price_kind=price_kind,
    )


CANONICAL = [
    candidate(1, "96.00"),
    candidate(2, "110.00"),
    candidate(3, "126.00"),
    candidate(4, "140.00"),
    candidate(5, "150.00"),
]

SUBJECT = Subject(
    area_m2=Decimal("3000.00"),
    teryt_gmina=GMINA_A,
    asset_class="land_building",
    buildability="buildable",
)


def run(candidates, params, subject=SUBJECT, as_of=AS_OF):
    chosen = select_comparables(
        subject,
        candidates,
        as_of=as_of,
        band_pct=params.comparables.area_band_pct,
        recency_months=params.comparables.recency_months,
    )
    return estimate(
        chosen,
        as_of=as_of,
        price_type="offering",
        price_kind="asking",
        iqr_switch_n=params.aggregates.iqr_switch_n,
        min_before_widening=params.comparables.min_before_widening,
    )


# --- the canonical estimate ------------------------------------------------


def test_the_canonical_estimate_pins_every_field(params) -> None:
    result = run(CANONICAL, params)
    assert isinstance(result, Estimate)
    assert result.n == 5
    assert result.median == Decimal("126.00")
    assert result.low == Decimal("110.00")
    assert result.high == Decimal("140.00")
    assert result.basis == "gmina"
    assert result.widening_step == "gmina"
    assert result.range_kind == "iqr"
    assert result.below_min_comparables is False


def test_an_estimate_never_carries_a_bare_median(params) -> None:
    """D42. Every field the reader needs to judge the median is required."""
    result = run(CANONICAL, params)
    for name in ("low", "median", "high", "n", "basis", "widening_step"):
        assert getattr(result, name) is not None, name
    assert result.low < result.median < result.high


# --- the band --------------------------------------------------------------


def test_the_area_band_is_fifty_percent_and_inclusive(params) -> None:
    low, high = area_band(Decimal("3000.00"), band_pct=params.comparables.area_band_pct)
    assert (low, high) == (Decimal("1500.00"), Decimal("4500.00"))


@pytest.mark.parametrize(
    "area,inside",
    [
        ("1500.00", True),
        ("4500.00", True),
        ("1499.99", False),
        ("4500.01", False),
    ],
)
def test_the_band_bounds_are_inclusive(params, area, inside) -> None:
    result = run([candidate(9, "200.00", area_m2=area)], params)
    assert isinstance(result, Estimate) is inside


# --- what must never be relaxed -------------------------------------------


def test_buildability_is_matched_exactly_and_never_relaxed(params) -> None:
    """Relaxing this is the easiest way to find more comparables and the fastest
    way to make the number meaningless."""
    decoys = [
        candidate(6, "12.00", buildability="agricultural"),
        candidate(7, "60.00", buildability="unknown"),
    ]
    with_decoys = run(CANONICAL + decoys, params)
    clean = run(CANONICAL, params)
    assert with_decoys == clean


def test_an_unknown_subject_draws_only_on_unknown_candidates(params) -> None:
    subject = Subject(
        area_m2=Decimal("3000.00"),
        teryt_gmina=GMINA_A,
        asset_class="land_building",
        buildability="unknown",
    )
    result = run(
        CANONICAL + [candidate(7, "60.00", buildability="unknown")],
        params,
        subject=subject,
    )
    assert isinstance(result, Estimate)
    assert result.n == 1
    assert result.median == Decimal("60.00")


def test_an_observation_outside_the_recency_window_is_excluded(params) -> None:
    """The decoy passes every other filter, so recency is the only thing that
    can drop it. Both leak values are named so the mutant has a killer."""
    decoy = candidate(6, "400.00", observed_at=dt.date(2025, 1, 15))
    result = run(CANONICAL + [decoy], params)
    assert result.n == 5
    assert result.median == Decimal("126.00")
    assert result.high == Decimal("140.00")

    # Companion: widen the window and the decoy arrives, which proves the
    # exclusion is the twelve-month rule and not an accident of another filter.
    widened = select_comparables(
        SUBJECT,
        CANONICAL + [decoy],
        as_of=AS_OF,
        band_pct=params.comparables.area_band_pct,
        recency_months=24,
    )
    assert widened.n == 6


def test_the_recency_cutoff_walks_whole_months(params) -> None:
    """Twelve times thirty days is eleven months and twenty-five days, which
    would drop a week of observations every year."""
    assert recency_cutoff(dt.date(2026, 8, 8), months=12) == dt.date(2025, 8, 8)
    assert recency_cutoff(dt.date(2026, 1, 31), months=12) == dt.date(2025, 1, 28)


def test_a_different_gmina_is_never_borrowed_from(params) -> None:
    subject = Subject(
        area_m2=Decimal("3000.00"),
        teryt_gmina=GMINA_B,
        asset_class="land_building",
        buildability="buildable",
    )
    result = run(CANONICAL, params, subject=subject)
    assert isinstance(result, Absence)


# --- absence ---------------------------------------------------------------


def test_no_comparables_returns_an_absence_with_no_number(params) -> None:
    """The load-bearing part: gmina A's median appears nowhere in the result.

    A number borrowed from somewhere else, unlabelled, is worse than no number.
    """
    subject = Subject(
        area_m2=Decimal("3000.00"),
        teryt_gmina=GMINA_B,
        asset_class="land_building",
        buildability="buildable",
    )
    result = run(CANONICAL, params, subject=subject)
    assert isinstance(result, Absence)
    assert not isinstance(result, Estimate)
    assert result.reason == "no_comparables"
    assert result.n == 0
    # No price attribute exists to reach for, so a caller cannot render an
    # absence as a price by forgetting a check.
    for name in ("median", "low", "high", "median_ppm2"):
        assert not hasattr(result, name), name
    assert "126" not in repr(result)


# --- a thin set ------------------------------------------------------------


def test_a_thin_set_still_returns_an_estimate_and_says_it_is_thin(params) -> None:
    """D109 set the minimum at three and recorded the cost. The answer to a thin
    set is the `n` and the range beside it, not suppression."""
    result = run([candidate(1, "110.00"), candidate(2, "140.00")], params)
    assert result.n == 2
    assert result.median == Decimal("125.00")
    assert result.range_kind == "min_max"
    assert result.low == Decimal("110.00")
    assert result.high == Decimal("140.00")
    assert result.below_min_comparables is True
    assert result.widening_step == "gmina"


# --- the verdict -----------------------------------------------------------


@pytest.mark.parametrize(
    "observed,expected",
    [
        ("142.00", "above"),
        ("126.00", "within"),
        ("100.00", "below"),
        ("110.00", "within"),  # inclusive lower bound
        ("140.00", "within"),  # inclusive upper bound
    ],
)
def test_the_verdict_is_relative_to_the_range(params, observed, expected) -> None:
    result = run(CANONICAL, params)
    assert verdict(Decimal(observed), result) == expected


def test_the_verdict_carries_no_percentage_off_the_median(params) -> None:
    """FR-38. A percentage implies the median is where the price ought to be.
    It is not: it is the middle of a spread that is often wide."""
    result = run(CANONICAL, params)
    for name in dir(result):
        assert "pct" not in name.lower(), name
        assert "percent" not in name.lower(), name
        assert "deviation" not in name.lower(), name


# --- excluding a comparable ------------------------------------------------


def test_excluding_a_comparable_recomputes_the_estimate(params) -> None:
    """V51c. The comparable set *is* the estimate, so a reader's judgement that
    one does not belong improves the answer directly."""
    before = run(CANONICAL, params)
    after = run([c for c in CANONICAL if c.listing_id != 1], params)
    assert after.n == 4
    assert after.median == Decimal("133.00")
    assert after.range_kind == "min_max"
    assert after.low == Decimal("110.00")
    assert after.high == Decimal("150.00")
    assert after.median - before.median == Decimal("7.00")
