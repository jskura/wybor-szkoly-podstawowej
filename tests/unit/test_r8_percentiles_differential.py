"""R8 §4 — the percentile function against an independent reference (V48).

The reference is `numpy.percentile(..., method="linear")`. numpy is a test-only
dependency: an architecture test below asserts `src/dzialki/metrics/` never
imports it, so the reference stays independent of the code it checks.

A differential suite can stop comparing anything without failing. F6 is the
negative control that catches that.
"""

from __future__ import annotations

import ast
import math
import pathlib
from decimal import ROUND_HALF_UP, Decimal

import numpy
import pytest
from hypothesis import given
from hypothesis import strategies as st

from dzialki.metrics import percentiles, round_for_storage

pytestmark = [pytest.mark.unit]

# §4.1. Every row was computed by hand from the R-7 definition and confirmed
# against numpy. The `why` column of the plan is the comment beside each row.
REFERENCE = [
    ([118.0], 118.0, 118.0, 118.0),  # degenerate
    ([100.0, 200.0], 125.0, 150.0, 175.0),  # smallest interpolating case
    ([96.0, 126.0, 150.0], 111.0, 126.0, 138.0),  # odd, median is an element
    ([61.0, 96.0, 140.0, 240.0], 87.25, 118.0, 165.0),  # spread switch, below
    ([96.0, 110.0, 126.0, 140.0, 150.0], 110.0, 126.0, 140.0),  # switch, above
    ([96.0, 110.0, 126.0, 140.0, 150.0, 5000.0], 114.0, 133.0, 147.5),  # outlier
    ([1.0, 2.0, 3.0, 4.0], 1.75, 2.5, 3.25),  # the convention canary
    ([100.0, 100.0, 100.0, 100.0], 100.0, 100.0, 100.0),  # all ties
    ([50.0, 100.0, 100.0, 100.0, 250.0], 100.0, 100.0, 100.0),  # heavy ties
    ([50.0, 100.0, 100.0, 250.0], 87.5, 100.0, 137.5),  # ties across quartiles
    ([61.0, 96.0, 140.0, 150.0, 240.0], 96.0, 140.0, 150.0),  # D2's fixture
    ([float(v) for v in range(10, 101, 10)], 32.5, 55.0, 77.5),
    ([float(v) for v in range(1, 101)], 25.75, 50.5, 75.25),
]

CLOSE = {"rel_tol": 1e-12, "abs_tol": 1e-9}


def _reference(values: list[float]) -> tuple[float, float, float]:
    p25, median, p75 = numpy.percentile(values, [25, 50, 75], method="linear")
    # The two reference functions agree to within a unit in the last place, not
    # bit for bit: `numpy.median` averages the two middle values while
    # `numpy.percentile` interpolates from one end. Comparing them exactly would
    # fail on the reference rather than on the code under test.
    assert math.isclose(float(median), float(numpy.median(values)), **CLOSE)
    return float(p25), float(median), float(p75)


def _agrees(values: list[float]) -> None:
    ours = percentiles(values)
    p25, median, p75 = _reference(values)
    assert math.isclose(ours.p25, p25, **CLOSE)
    assert math.isclose(ours.median, median, **CLOSE)
    assert math.isclose(ours.p75, p75, **CLOSE)


@pytest.mark.property
@given(
    st.lists(
        st.floats(
            min_value=1, max_value=100_000, allow_nan=False, allow_infinity=False
        ),
        min_size=1,
        max_size=500,
    )
)
def test_matches_numpy_on_random_arrays(values: list[float]) -> None:
    _agrees(values)


@pytest.mark.property
@given(
    st.lists(
        st.floats(
            min_value=1, max_value=100_000, allow_nan=False, allow_infinity=False
        ),
        min_size=2,
        max_size=500,
    ).filter(lambda drawn: len(drawn) % 2 == 0)
)
def test_matches_numpy_on_even_length_arrays(values: list[float]) -> None:
    """Even lengths are where the middle-element bug lives, and a random-length
    strategy under-samples them."""
    _agrees(values)


@pytest.mark.property
@given(
    st.lists(
        st.sampled_from([50.0, 100.0, 100.0, 100.0, 250.0]), min_size=1, max_size=200
    )
)
def test_matches_numpy_under_heavy_ties(values: list[float]) -> None:
    """Interpolating between two identical values makes a rank-based and an
    interpolating convention agree, which hides a definition error."""
    _agrees(values)


@pytest.mark.parametrize("values,p25,median,p75", REFERENCE)
def test_matches_numpy_on_the_named_arrays(
    values: list[float], p25: float, median: float, p75: float
) -> None:
    _agrees(values)
    # And the hand-computed values themselves, so the test fails if numpy and
    # our code ever agree on something the plan does not state.
    ours = percentiles(values)
    assert ours.p25 == p25
    assert ours.median == median
    assert ours.p75 == p75


@pytest.mark.parametrize("values,p25,median,p75", REFERENCE)
def test_rounded_output_matches_the_rounded_reference_exactly(
    values: list[float], p25: float, median: float, p75: float
) -> None:
    """`Decimal` equality, not `isclose`.

    A rounding-mode difference is invisible to `isclose` and visible to every
    reader of the map.
    """
    ours = percentiles(values)
    for got, expected in (
        (ours.p25, p25),
        (ours.median, median),
        (ours.p75, p75),
    ):
        assert round_for_storage(got) == Decimal(str(expected)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )


def test_a_zero_width_iqr_sits_beside_a_stored_min_max() -> None:
    """Row 9 of §4.1. At n=5 the switch chooses the IQR, which is zero-width on
    data spanning 50 to 250. Rule 7 needs the min–max to stay stored."""
    result = percentiles([50.0, 100.0, 100.0, 100.0, 250.0])
    assert result.p25 == 100.0
    assert result.p75 == 100.0
    assert result.minimum == 50.0
    assert result.maximum == 250.0


def _nearest_rank(values: list[float], quantile: float) -> float:
    """A deliberately wrong convention, defined here so nothing imports it."""
    ordered = sorted(values)
    index = math.ceil(quantile * len(ordered)) - 1
    return ordered[max(index, 0)]


def test_the_reference_disagrees_with_a_deliberately_wrong_convention() -> None:
    """The negative control. If this passes vacuously the suite compares nothing."""
    values = [1.0, 2.0, 3.0, 4.0]
    p25, _median, p75 = _reference(values)
    assert _nearest_rank(values, 0.25) != p25
    assert _nearest_rank(values, 0.75) != p75
    assert (_nearest_rank(values, 0.25), _nearest_rank(values, 0.75)) == (1.0, 3.0)


@pytest.mark.architecture
def test_the_metrics_package_never_imports_the_reference(
    repo_root: pathlib.Path,
) -> None:
    """A reference the code under test imports is not a reference."""
    offenders: list[str] = []
    for path in (repo_root / "src" / "dzialki" / "metrics").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                if name.split(".")[0] in {"numpy", "pandas", "statistics", "scipy"}:
                    offenders.append(f"{path.relative_to(repo_root)}: {name}")
    assert offenders == []
