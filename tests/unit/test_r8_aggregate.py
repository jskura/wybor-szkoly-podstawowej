"""R8 block C — the aggregate object and the key it is grouped by.

Rule 7 made structural. A bare number must be unconstructible, not merely
untested, so `Spread` has no defaults and nothing crosses the module boundary
without its sample size, its spread and its provenance.

The grouping key is D66's: teryt, month, asset class, buildability, price type,
price kind, series kind and area band. Drop any one of them and two rows that
mean different things collide.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import pathlib
from decimal import Decimal

import pytest
from test_r8_fixtures import (
    AS_OF,
    CANONICAL,
    MONTH,
    TERYT_GMINA_A,
    TERYT_GMINA_B,
    observation,
    warsaw,
)

from dzialki.config import load_params
from dzialki.metrics import Aggregate, Observation, Series, Spread, aggregate

pytestmark = [pytest.mark.unit]


@pytest.fixture(scope="module")
def params(repo_root: pathlib.Path):
    return load_params(repo_root / "config" / "params.yml")


def run(observations, params, *, as_of=AS_OF) -> list[Aggregate]:
    return aggregate(
        observations,
        as_of=as_of,
        flow_window_days=params.aggregates.flow_window_days,
        iqr_switch_n=params.aggregates.iqr_switch_n,
    )


def pick(aggregates: list[Aggregate], **criteria) -> Aggregate:
    """The one aggregate matching every criterion. Two matches is a key defect."""
    found = [
        row
        for row in aggregates
        if all(getattr(row, name) == value for name, value in criteria.items())
    ]
    assert len(found) == 1, f"{len(found)} rows match {criteria}"
    return found[0]


# --- C1 · a bare number is unconstructible --------------------------------


@pytest.mark.architecture
def test_an_aggregate_cannot_be_constructed_without_n_and_spread() -> None:
    with pytest.raises(TypeError):
        Aggregate(median_ppm2=Decimal("118.00"))  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        Spread(median_ppm2=Decimal("118.00"))  # type: ignore[call-arg]


@pytest.mark.architecture
@pytest.mark.parametrize(
    "cls,names",
    [
        (
            Spread,
            [
                "n",
                "median_ppm2",
                "p25_ppm2",
                "p75_ppm2",
                "min_ppm2",
                "max_ppm2",
                "mean_ppm2",
                "range_kind",
            ],
        ),
        (Series, ["series_kind", "flow_window_days", "spread"]),
        (
            Aggregate,
            [
                "teryt_unit",
                "unit_level",
                "month",
                "asset_class",
                "buildability",
                "price_type",
                "price_kind",
                "area_band",
                "series",
                "as_of",
                "source_ids",
            ],
        ),
    ],
)
def test_no_field_carries_a_default(cls, names: list[str]) -> None:
    """A default is a value nobody chose, arriving as though someone had."""
    fields = {field.name: field for field in dataclasses.fields(cls)}
    assert sorted(fields) == sorted(names)
    for field in fields.values():
        assert field.default is dataclasses.MISSING
        assert field.default_factory is dataclasses.MISSING


# --- C2 · provenance ------------------------------------------------------


def test_every_aggregate_carries_full_provenance(params) -> None:
    """Rule 7, V5. Source, as-of date and sample size travel with the number."""
    for row in run(CANONICAL, params):
        assert row.as_of == AS_OF
        assert row.source_ids == (1,)
        assert row.price_type == "offering"
        assert row.price_kind == "asking"
        assert row.series_kind in {"stock", "flow"}
        assert row.n >= 1
        assert row.month == MONTH
        assert row.unit_level == "gmina"


def test_source_ids_are_the_distinct_sources_in_order(params) -> None:
    rows = run(
        [
            CANONICAL[0],
            dataclasses.replace(CANONICAL[1], source_id=4),
            dataclasses.replace(CANONICAL[2], source_id=4),
        ],
        params,
    )
    assert pick(rows, area_band="1500-3000", series_kind="stock").source_ids == (1, 4)
    assert pick(rows, area_band="3000-10000", series_kind="stock").source_ids == (4,)


# --- C3 · the grouping key ------------------------------------------------


def test_aggregate_groups_by_gmina_and_band(params) -> None:
    """An implementation grouping by gmina alone produces one row per gmina."""
    elsewhere = observation(
        "B1",
        area_m2="2000",
        price_pln="600000",
        first_seen=warsaw(2026, 7, 1),
        teryt_unit=TERYT_GMINA_B,
    )
    rows = run([*CANONICAL, elsewhere], params)

    keys = [row.key for row in rows]
    assert len(keys) == len(set(keys))

    band = pick(
        rows,
        teryt_unit=TERYT_GMINA_A,
        area_band="1500-3000",
        series_kind="stock",
    )
    # C1 at 2 000 m² and C2 at 2 500 m². Bands are lower-inclusive, so C3 at
    # exactly 3 000 m² belongs to `3000-10000`.
    assert band.n == 2
    assert band.median_ppm2 == Decimal("103.00")

    in_gmina_a = [
        value
        for row in rows
        if row.teryt_unit == TERYT_GMINA_A
        for value in (
            row.median_ppm2,
            row.p25_ppm2,
            row.p75_ppm2,
            row.min_ppm2,
            row.max_ppm2,
        )
    ]
    assert Decimal("300.00") not in in_gmina_a


def test_the_grouping_key_is_exactly_the_d66_key(params) -> None:
    rows = run(CANONICAL, params)
    assert pick(rows, area_band="1500-3000", series_kind="stock").key == (
        TERYT_GMINA_A,
        MONTH,
        "land_building",
        "buildable",
        "offering",
        "asking",
        "stock",
        "1500-3000",
    )


def test_the_result_is_ordered_by_key(params) -> None:
    """A stable order makes two runs comparable and a diff readable."""
    rows = run(CANONICAL, params)
    assert [row.key for row in rows] == sorted(row.key for row in rows)


# --- C4 · absence is absence ----------------------------------------------


def test_an_empty_group_produces_no_row_rather_than_a_zero(params) -> None:
    rows = run(CANONICAL, params)
    bands = {row.area_band for row in rows}
    assert bands == {"1500-3000", "3000-10000"}
    assert "<800" not in bands
    for row in rows:
        assert row.n > 0
        assert row.median_ppm2 != Decimal("0.00")
        assert row.median_ppm2 is not None


def test_no_observations_produce_no_rows(params) -> None:
    assert run([], params) == []


def test_an_inactive_listing_leaves_the_stock_pool(params) -> None:
    """Stock is what is on the market at `as_of`, not what ever was."""
    withdrawn = dataclasses.replace(CANONICAL[4], active=False)
    rows = run([*CANONICAL[:4], withdrawn], params)
    band = pick(rows, area_band="3000-10000", series_kind="stock")
    assert band.n == 2
    assert band.median_ppm2 == Decimal("133.00")


# --- the four `metric_unit_month` rows of §1.3 ----------------------------


@pytest.mark.parametrize(
    "band,series,n,median,p25,p75,minimum,maximum,kind,low,high",
    [
        (
            "1500-3000",
            "stock",
            2,
            "103.00",
            "99.50",
            "106.50",
            "96.00",
            "110.00",
            "min_max",
            "96.00",
            "110.00",
        ),
        (
            "1500-3000",
            "flow",
            2,
            "103.00",
            "99.50",
            "106.50",
            "96.00",
            "110.00",
            "min_max",
            "96.00",
            "110.00",
        ),
        (
            "3000-10000",
            "stock",
            3,
            "140.00",
            "133.00",
            "145.00",
            "126.00",
            "150.00",
            "min_max",
            "126.00",
            "150.00",
        ),
        (
            "3000-10000",
            "flow",
            2,
            "133.00",
            "129.50",
            "136.50",
            "126.00",
            "140.00",
            "min_max",
            "126.00",
            "140.00",
        ),
    ],
)
def test_the_canonical_five_produce_exactly_four_rows(
    params,
    band: str,
    series: str,
    n: int,
    median: str,
    p25: str,
    p75: str,
    minimum: str,
    maximum: str,
    kind: str,
    low: str,
    high: str,
) -> None:
    """The D66-keyed view. Five observations, two bands, two series, four rows."""
    rows = run(CANONICAL, params)
    assert len(rows) == 4
    row = pick(rows, area_band=band, series_kind=series)
    assert row.n == n
    assert row.median_ppm2 == Decimal(median)
    assert row.p25_ppm2 == Decimal(p25)
    assert row.p75_ppm2 == Decimal(p75)
    assert row.min_ppm2 == Decimal(minimum)
    assert row.max_ppm2 == Decimal(maximum)
    assert row.range_kind == kind
    assert row.low == Decimal(low)
    assert row.high == Decimal(high)


def test_the_month_bucket_follows_the_warsaw_calendar(params) -> None:
    """`08` §6. A UTC bucket puts a late-evening June observation in July."""
    late_june = observation(
        "Z",
        area_m2="3000",
        price_pln="300000",
        first_seen=warsaw(2026, 6, 30, 23, 30),
        observed_at=warsaw(2026, 6, 30, 23, 30),
    )
    assert late_june.observed_at.astimezone(dt.UTC).month == 6
    assert late_june.observed_at.astimezone(dt.UTC).day == 30
    rows = run([late_june], params, as_of=dt.date(2026, 8, 8))
    assert {row.month for row in rows} == {dt.date(2026, 6, 1)}


def test_nothing_crosses_the_module_boundary_without_its_label(params) -> None:
    """V45 (c). Every returned value is an `Aggregate`, never a bare spread."""
    rows = run(CANONICAL, params)
    assert rows
    for row in rows:
        assert isinstance(row, Aggregate)
        assert isinstance(row.series, Series)
        assert isinstance(row.series.spread, Spread)
        assert not isinstance(row, (Spread, Series))


def test_an_observation_is_frozen(params) -> None:
    """The aggregate reads its input. It must not be able to edit it."""
    with pytest.raises(dataclasses.FrozenInstanceError):
        CANONICAL[0].area_m2 = Decimal(1)  # type: ignore[misc]
    assert isinstance(CANONICAL[0], Observation)
