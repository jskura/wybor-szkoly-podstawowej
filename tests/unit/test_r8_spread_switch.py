"""R8 block D — which range the interface shows, and why it is never suppressed.

Rule 7 is *always show, always flag*. Below the threshold the spread shows as
min–max, at and above it as an interquartile range. Nothing is hidden at any
sample size, and a source that publishes no spread says so in words (D69).

D67 put the threshold in configuration. These tests read it from there, so
changing it stays one edit rather than an audit of every call site.
"""

from __future__ import annotations

import ast
import dataclasses
import pathlib
from decimal import Decimal

import pytest
from test_r8_fixtures import (
    GUS_MEDIAN,
    GUS_N,
    SPREAD_N1,
    SPREAD_N3,
    SPREAD_N4,
    SPREAD_N5,
    SPREAD_N10,
    SPREAD_N100,
)

from dzialki.config import load_params
from dzialki.metrics import (
    range_kind_for,
    spread_from_central_value,
    spread_from_values,
)

pytestmark = [pytest.mark.unit]

# Words that would mean the figure was withheld. D5 scans for all three.
SUPPRESSION_WORDS = ["insufficient", "brak danych", "—"]


@pytest.fixture(scope="module")
def switch_n(repo_root: pathlib.Path) -> int:
    return load_params(repo_root / "config" / "params.yml").aggregates.iqr_switch_n


def test_spread_is_min_max_below_the_threshold(switch_n: int) -> None:
    """`CLAUDE.md` rule 7's own example: median 118, range 61-240, n=4."""
    spread = spread_from_values(SPREAD_N4, iqr_switch_n=switch_n)
    assert spread.range_kind == "min_max"
    assert spread.low == Decimal("61.00")
    assert spread.high == Decimal("240.00")
    assert spread.median_ppm2 == Decimal("118.00")
    assert spread.n == 4
    # All four percentile columns stay stored. Only the displayed range switches.
    assert spread.p25_ppm2 == Decimal("87.25")
    assert spread.p75_ppm2 == Decimal("165.00")
    assert spread.min_ppm2 == Decimal("61.00")
    assert spread.max_ppm2 == Decimal("240.00")


def test_spread_is_iqr_at_and_above_the_threshold(switch_n: int) -> None:
    """A `>` in place of `>=` gives min_max here. This is the boundary kill."""
    spread = spread_from_values(SPREAD_N5, iqr_switch_n=switch_n)
    assert spread.range_kind == "iqr"
    assert spread.median_ppm2 == Decimal("140.00")
    assert spread.low == Decimal("96.00")
    assert spread.high == Decimal("150.00")
    assert spread.n == 5


def test_the_switch_reads_the_threshold_from_configuration(switch_n: int) -> None:
    """D67. The same four values answer differently under a different threshold."""
    assert range_kind_for(4, iqr_switch_n=switch_n) == "min_max"
    assert range_kind_for(4, iqr_switch_n=3) == "iqr"
    assert range_kind_for(3, iqr_switch_n=3) == "iqr"
    assert range_kind_for(2, iqr_switch_n=3) == "min_max"

    lowered = spread_from_values(SPREAD_N4, iqr_switch_n=3)
    assert lowered.range_kind == "iqr"
    assert lowered.low == Decimal("87.25")
    assert lowered.high == Decimal("165.00")


@pytest.mark.architecture
def test_no_call_site_holds_a_copy_of_the_threshold(
    repo_root: pathlib.Path, switch_n: int
) -> None:
    """A copy of the number would not follow a change to the file that holds it."""
    params = load_params(repo_root / "config" / "params.yml")
    forbidden = {switch_n, params.aggregates.flow_window_days}
    offenders: list[str] = []
    for path in (repo_root / "src" / "dzialki" / "metrics").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (
                isinstance(node, ast.Constant)
                and not isinstance(node.value, bool)
                and node.value in forbidden
            ):
                offenders.append(f"{path.relative_to(repo_root)}:{node.lineno}")
    assert offenders == []


@pytest.mark.parametrize(
    "values,n,median,kind,low,high",
    [
        (SPREAD_N1, 1, "118.00", "min_max", "118.00", "118.00"),
        (SPREAD_N3, 3, "126.00", "min_max", "96.00", "150.00"),
        (SPREAD_N4, 4, "118.00", "min_max", "61.00", "240.00"),
        (SPREAD_N5, 5, "140.00", "iqr", "96.00", "150.00"),
        (SPREAD_N10, 10, "55.00", "iqr", "32.50", "77.50"),
        (SPREAD_N100, 100, "50.50", "iqr", "25.75", "75.25"),
    ],
)
def test_no_aggregate_is_ever_suppressed(
    switch_n: int,
    values: list[float],
    n: int,
    median: str,
    kind: str,
    low: str,
    high: str,
) -> None:
    """V4 (a) verbatim. Six sample sizes, all six shown."""
    spread = spread_from_values(values, iqr_switch_n=switch_n)
    assert spread.n == n
    assert spread.median_ppm2 == Decimal(median)
    assert spread.range_kind == kind
    assert spread.low == Decimal(low)
    assert spread.high == Decimal(high)

    serialized = str(dataclasses.asdict(spread)).lower()
    for word in SUPPRESSION_WORDS:
        assert word not in serialized


def test_the_suppression_scan_catches_a_real_occurrence() -> None:
    """Non-vacuity companion. A scan for absence passes when it reads nothing."""
    seeded = str({"median_ppm2": "brak danych"}).lower()
    assert [word for word in SUPPRESSION_WORDS if word in seeded] == ["brak danych"]


def test_the_sample_size_is_a_separate_field_the_label_can_print(
    switch_n: int,
) -> None:
    """D113 fades a thin tile and puts the count on the label. The count must be
    reachable without parsing the median."""
    spread = spread_from_values(SPREAD_N3, iqr_switch_n=switch_n)
    assert dataclasses.asdict(spread)["n"] == 3


def test_a_source_with_no_spread_gives_range_kind_unavailable() -> None:
    """D69. GUS publishes a central value and no percentiles.

    Rule 7 says show the absence. Raising on correct data is not rule 7, and a
    dropped field is not rule 7 either.
    """
    spread = spread_from_central_value(GUS_MEDIAN, n=GUS_N)
    assert spread.range_kind == "unavailable"
    assert spread.median_ppm2 == Decimal("130.00")
    assert spread.n == 37
    assert spread.low is None
    assert spread.high is None
    assert spread.p25_ppm2 is None
    assert spread.p75_ppm2 is None
    assert spread.min_ppm2 is None
    assert spread.max_ppm2 is None
    # The field is present rather than dropped. A missing field reads as a bug
    # in the reader, not as an absent spread at the source.
    assert "range_kind" in dataclasses.asdict(spread)
    assert "low" in spread.as_displayed()


def test_an_unavailable_spread_never_invents_a_number() -> None:
    """Half a spread looks like a range and is not."""
    spread = spread_from_central_value(GUS_MEDIAN, n=GUS_N)
    bounds = [spread.p25_ppm2, spread.p75_ppm2, spread.min_ppm2, spread.max_ppm2]
    assert bounds == [None, None, None, None]


def test_a_spread_of_no_observations_is_an_error(switch_n: int) -> None:
    """C4's rule at the spread layer: absence of data is absence, never zero."""
    with pytest.raises(ValueError):
        spread_from_values([], iqr_switch_n=switch_n)
