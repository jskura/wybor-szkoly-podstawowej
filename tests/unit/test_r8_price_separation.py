"""R8 §6 — offering and sales never mix, and neither do the price kinds.

Rule 6 makes both price types first-class. The gap between them is a product
feature. A blended median is not a compromise between the two; it is a number
that describes no market at all.

`price_kind` is the finer axis inside `offering` (D65, D68). An auction starting
price is a statutory floor, not an ask. Blending the two drags every median down
and reads as a market move.
"""

from __future__ import annotations

import ast
import dataclasses
import pathlib
from decimal import Decimal

import pytest
from test_r8_fixtures import AS_OF, CANONICAL, D7, PRICE_SEPARATION

from dzialki.config import load_params
from dzialki.metrics import GroupKey, aggregate

pytestmark = [pytest.mark.unit]

# `15` §9, quoted. `unit_level` is not in the key, because `teryt_unit`
# determines it.
D66_KEY = (
    "teryt_unit",
    "month",
    "asset_class",
    "buildability",
    "price_type",
    "price_kind",
    "series_kind",
    "area_band",
)


@pytest.fixture(scope="module")
def params(repo_root: pathlib.Path):
    return load_params(repo_root / "config" / "params.yml")


def run(observations, params):
    return aggregate(
        observations,
        as_of=AS_OF,
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


def every_number(value) -> list[Decimal]:
    """Every `Decimal` anywhere inside a returned object."""
    if isinstance(value, Decimal):
        return [value]
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return every_number(dataclasses.asdict(value))
    if isinstance(value, dict):
        return [found for item in value.values() for found in every_number(item)]
    if isinstance(value, (list, tuple, set)):
        return [found for item in value for found in every_number(item)]
    return []


# --- P1 · offering and sales, nothing between -----------------------------


def test_offering_and_sales_produce_separate_aggregates_and_nothing_between(
    params,
) -> None:
    rows = run(PRICE_SEPARATION, params)

    offering = pick(rows, price_type="offering", series_kind="stock")
    assert offering.n == 5
    assert offering.median_ppm2 == Decimal("200.00")
    assert offering.price_kind == "asking"

    sales = pick(rows, price_type="sales", series_kind="stock")
    assert sales.n == 5
    assert sales.median_ppm2 == Decimal("100.00")
    assert sales.price_kind == "transaction"

    # Both aggregates are deliberately zero-width, so 150.00 cannot arise by
    # coincidence from either. It is the median of the blended ten.
    numbers = [found for row in rows for found in every_number(row)]
    assert Decimal("150.00") not in numbers
    assert set(numbers) == {Decimal("200.00"), Decimal("100.00")}


def test_a_blended_set_would_have_produced_the_forbidden_value() -> None:
    """Non-vacuity. The scan above means nothing unless 150.00 is reachable."""
    from dzialki.metrics import percentiles

    blended = [row.price_per_m2 for row in PRICE_SEPARATION]
    assert percentiles(blended).median == 150.0
    assert percentiles(blended).n == 10


# --- P2 · the key makes the separation structural -------------------------


@pytest.mark.architecture
def test_the_aggregation_key_includes_price_type_and_price_kind(params) -> None:
    """Making the separation structural is cheaper than testing for it forever."""
    rows = run(PRICE_SEPARATION, params)
    assert GroupKey._fields == D66_KEY
    assert rows[0].key == tuple(getattr(rows[0], name) for name in D66_KEY)

    offering = pick(rows, price_type="offering", series_kind="stock")
    sales = pick(rows, price_type="sales", series_kind="stock")
    assert offering.key != sales.key


@pytest.mark.architecture
def test_no_code_path_substitutes_one_price_type_for_the_other(
    repo_root: pathlib.Path,
) -> None:
    """A fallback argument is the shape this failure takes when it is written on
    purpose. Scanning for it costs one test and closes the obvious door.

    `valuation/` carries the other half of this rule and is S9's work item.
    """
    offenders: list[str] = []
    for path in (repo_root / "src" / "dzialki" / "metrics").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                names = [
                    argument.arg
                    for argument in [
                        *node.args.args,
                        *node.args.kwonlyargs,
                        *node.args.posonlyargs,
                    ]
                ]
                offenders.extend(
                    f"{path.relative_to(repo_root)}:{node.lineno}: {name}"
                    for name in names
                    if "fallback" in name
                )
            if isinstance(node, ast.Constant) and node.value in {"offering", "sales"}:
                offenders.append(f"{path.relative_to(repo_root)}:{node.lineno}")
    assert offenders == []


# --- P5 · auction prices do not move the asking median --------------------


def test_auction_prices_do_not_move_the_asking_median(params) -> None:
    with_auction = run([*CANONICAL, D7], params)
    without = run(CANONICAL, params)

    asking = [row for row in with_auction if row.price_kind == "asking"]
    assert asking == without
    assert sum(row.n for row in asking if row.series_kind == "stock") == 5

    auction = pick(with_auction, price_kind="auction_start", series_kind="stock")
    assert auction.n == 1
    assert auction.median_ppm2 == Decimal("40.00")
    assert auction.range_kind == "min_max"
    assert auction.low == Decimal("40.00")
    assert auction.high == Decimal("40.00")

    # The blended set is [40, 96, 110, 126, 140, 150]: median 118.00, min 40.00.
    for row in asking:
        assert row.median_ppm2 != Decimal("118.00")
        assert row.min_ppm2 != Decimal("40.00")


def test_the_auction_decoy_would_be_visible_if_it_leaked() -> None:
    """Non-vacuity. D7 is 3 000 m², so it lands in the same band as C3 and C4."""
    from dzialki.metrics import band_for, percentiles

    assert band_for(D7.area_m2) == "3000-10000"
    leaked = percentiles([40.0, 126.0, 140.0, 150.0])
    assert leaked.median == 133.0
    assert leaked.minimum == 40.0
