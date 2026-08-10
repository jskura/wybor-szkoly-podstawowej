"""The synthetic fixtures every R8 test reads, and the arithmetic they rest on.

`plans/04-aggregates-test-plan.md` §8 asks each fixture to carry its constructed
answer. The tests below are that answer: they assert every price per square metre
this stage depends on, so a later edit to a row cannot move an expected median
without a failure that names the row.

The plan puts these rows under `tests/fixtures/synthetic/`. That directory belongs
to another work item, so the rows live here instead. Nothing else changes: the
values are the plan's values.

The plan also asks for `TERYT_GMINA_A` to come from the V30 known-answer fixture.
That fixture does not exist yet, so the two codes below are synthetic and carry the
`99` prefix the schema tests already use for made-up units.
"""

from __future__ import annotations

import calendar
import datetime as dt
import zoneinfo
from decimal import Decimal

import pytest

from dzialki.metrics import Observation

pytestmark = [pytest.mark.unit]

WARSAW = zoneinfo.ZoneInfo("Europe/Warsaw")

AS_OF = dt.date(2026, 8, 8)
MONTH = dt.date(2026, 8, 1)

TERYT_GMINA_A = "9901011"
TERYT_GMINA_B = "9901022"
TERYT_GMINA_C = "9901033"

# `budowlana` in the plan. The enum member is `land_building`.
ASSET_CLASS = "land_building"
SOURCE_ID = 1


def warsaw(year: int, month: int, day: int, hour: int = 12, minute: int = 0):
    """A local timestamp. Storage is UTC; the month bucket is the Warsaw one."""
    return dt.datetime(year, month, day, hour, minute, tzinfo=WARSAW)


def shift_months(moment, months: int):
    """Move a date or a timestamp forward by whole calendar months.

    Used by M7, which shifts every observation and the window together. A
    calendar month is 30 or 31 days while the flow window is a fixed 90, so the
    shift is the transform and the invariance is the claim.
    """
    total = moment.month - 1 + months
    year = moment.year + total // 12
    month = total % 12 + 1
    day = min(moment.day, calendar.monthrange(year, month)[1])
    return moment.replace(year=year, month=month, day=day)


def observation(
    listing_id: str,
    *,
    area_m2: str,
    price_pln: str,
    first_seen,
    observed_at=None,
    teryt_unit: str = TERYT_GMINA_A,
    buildability: str = "buildable",
    price_type: str = "offering",
    price_kind: str = "asking",
    active: bool = True,
    source_id: int = SOURCE_ID,
) -> Observation:
    return Observation(
        listing_id=listing_id,
        teryt_unit=teryt_unit,
        unit_level="gmina",
        asset_class=ASSET_CLASS,
        buildability=buildability,
        price_type=price_type,
        price_kind=price_kind,
        area_m2=Decimal(area_m2),
        price_pln=Decimal(price_pln),
        first_seen=first_seen,
        observed_at=observed_at if observed_at is not None else warsaw(2026, 8, 8),
        active=active,
        source_id=source_id,
    )


# --- §1.1 the canonical five ----------------------------------------------
#
# C5 is the stale overpriced listing and it is deliberately the maximum of the
# set. A stale listing that was cheap would bias stock downwards and every test
# below would assert the opposite of the real failure mode.

C1 = observation(
    "C1", area_m2="2000", price_pln="192000", first_seen=warsaw(2026, 6, 20)
)
C2 = observation(
    "C2", area_m2="2500", price_pln="275000", first_seen=warsaw(2026, 7, 11)
)
C3 = observation(
    "C3", area_m2="3000", price_pln="378000", first_seen=warsaw(2026, 7, 30)
)
C4 = observation(
    "C4", area_m2="3600", price_pln="504000", first_seen=warsaw(2026, 8, 4)
)
C5 = observation(
    "C5", area_m2="4400", price_pln="660000", first_seen=warsaw(2025, 4, 2)
)

CANONICAL = [C1, C2, C3, C4, C5]

# The comparable window of a 3 000 m² subject is [1500, 4500] and admits all
# five, so the estimator view is the whole list. Selecting it is S9's work; this
# stage only computes over the set it is handed.
CANONICAL_PPM2 = [96.0, 110.0, 126.0, 140.0, 150.0]
CANONICAL_FLOW_PPM2 = [96.0, 110.0, 126.0, 140.0]

# --- §1.5 the decoys -------------------------------------------------------

D1 = observation("D1", area_m2="1400", price_pln="42000", first_seen=warsaw(2026, 7, 1))
D2 = observation(
    "D2", area_m2="4600", price_pln="1840000", first_seen=warsaw(2026, 7, 1)
)
D3 = observation(
    "D3",
    area_m2="3000",
    price_pln="36000",
    first_seen=warsaw(2026, 7, 1),
    buildability="agricultural",
)
D4 = observation(
    "D4",
    area_m2="3000",
    price_pln="180000",
    first_seen=warsaw(2026, 7, 1),
    buildability="unknown",
)
D5 = observation(
    "D5",
    area_m2="3000",
    price_pln="210000",
    first_seen=warsaw(2026, 7, 1),
    price_type="sales",
    price_kind="transaction",
)
D6 = observation(
    "D6",
    area_m2="3000",
    price_pln="1200000",
    first_seen=warsaw(2024, 12, 10),
    observed_at=warsaw(2025, 1, 15),
    active=False,
)
D7 = observation(
    "D7",
    area_m2="3000",
    price_pln="120000",
    first_seen=warsaw(2026, 7, 1),
    price_kind="auction_start",
)
D8 = observation(
    "D8",
    area_m2="3000",
    price_pln="1200000",
    first_seen=warsaw(2026, 7, 1),
    teryt_unit=TERYT_GMINA_B,
)

# M8's far outlier. It passes every filter by design, so the median moving little
# is a property of the median and not of a filter that quietly dropped it.
OUTLIER = observation(
    "O1", area_m2="3000", price_pln="15000000", first_seen=warsaw(2026, 7, 15)
)

# --- §1.6 the spread-switch reference values ------------------------------

SPREAD_N1 = [118.0]
SPREAD_N3 = [96.0, 126.0, 150.0]
SPREAD_N4 = [61.0, 96.0, 140.0, 240.0]
SPREAD_N5 = [61.0, 96.0, 140.0, 150.0, 240.0]
SPREAD_N10 = [float(value) for value in range(10, 101, 10)]
SPREAD_N100 = [float(value) for value in range(1, 101)]

# §6.5. GUS publishes a central value and no spread (D69). 130.00 is deliberately
# no value in §1.1, so an offering figure leaking into it is visible.
GUS_MEDIAN = Decimal("130.00")
GUS_N = 37

# --- §3.3 the window-sensitivity fixture ----------------------------------
#
# One gmina, one area band, nine months. The canonical five give only two
# distinct medians across the four windows and cannot exercise the report.

WINDOW_SENSITIVITY = [
    observation(
        "W1", area_m2="3000", price_pln="300000", first_seen=warsaw(2026, 8, 1)
    ),
    observation(
        "W2", area_m2="3000", price_pln="420000", first_seen=warsaw(2026, 7, 20)
    ),
    observation(
        "W3", area_m2="3000", price_pln="540000", first_seen=warsaw(2026, 7, 10)
    ),
    observation(
        "W4", area_m2="3000", price_pln="180000", first_seen=warsaw(2026, 6, 20)
    ),
    observation(
        "W5", area_m2="3000", price_pln="240000", first_seen=warsaw(2026, 6, 15)
    ),
    observation(
        "W6", area_m2="3000", price_pln="120000", first_seen=warsaw(2026, 5, 20)
    ),
    observation(
        "W7", area_m2="3000", price_pln="60000", first_seen=warsaw(2026, 5, 15)
    ),
    observation("W8", area_m2="3000", price_pln="30000", first_seen=warsaw(2026, 3, 1)),
    observation(
        "W9", area_m2="3000", price_pln="36000", first_seen=warsaw(2026, 2, 15)
    ),
]

# --- §6.1 the price-separation fixture ------------------------------------
#
# Every offering row is 200.00 and every sales row is 100.00, so both aggregates
# are zero-width and the blended 150.00 cannot arise by coincidence.

PRICE_SEPARATION = [
    observation(
        f"O{index}",
        area_m2=str(area),
        price_pln=str(area * 200),
        first_seen=warsaw(2026, 7, 1),
    )
    for index, area in enumerate([1600, 1700, 1800, 1900, 2000], start=1)
] + [
    observation(
        f"S{index}",
        area_m2=str(area),
        price_pln=str(area * 100),
        first_seen=warsaw(2026, 7, 1),
        price_type="sales",
        price_kind="transaction",
    )
    for index, area in enumerate([2100, 2200, 2300, 2400, 2500], start=1)
]

# --- M7's month-boundary pair ----------------------------------------------
#
# The plan states these as `first_seen`. The month bucket follows `observed_at`,
# so both columns carry the same instant here and the case reads the same either
# way.

Z1 = observation(
    "Z1",
    area_m2="3000",
    price_pln="300000",
    first_seen=warsaw(2026, 6, 30, 23, 30),
    observed_at=warsaw(2026, 6, 30, 23, 30),
)
Z2 = observation(
    "Z2",
    area_m2="3000",
    price_pln="600000",
    first_seen=warsaw(2026, 7, 1, 0, 30),
    observed_at=warsaw(2026, 7, 1, 0, 30),
)


# --- the fixtures assert their own arithmetic ------------------------------


@pytest.mark.parametrize(
    "row,expected",
    [
        (C1, 96.0),
        (C2, 110.0),
        (C3, 126.0),
        (C4, 140.0),
        (C5, 150.0),
    ],
)
def test_every_canonical_price_per_m2_is_exact(
    row: Observation, expected: float
) -> None:
    """No repeating decimal enters the fixture, so every statistic below is exact."""
    assert row.price_per_m2 == expected


@pytest.mark.parametrize(
    "row,expected",
    [
        (D1, 30.0),
        (D2, 400.0),
        (D3, 12.0),
        (D4, 60.0),
        (D5, 70.0),
        (D6, 400.0),
        (D7, 40.0),
        (D8, 400.0),
        (OUTLIER, 5000.0),
    ],
)
def test_every_decoy_price_per_m2_is_exact(row: Observation, expected: float) -> None:
    assert row.price_per_m2 == expected


def test_the_stale_listing_is_the_maximum_of_the_canonical_set() -> None:
    """The direction of the stock/flow bias, pinned in the fixture itself."""
    assert C5.price_per_m2 == max(row.price_per_m2 for row in CANONICAL)


def test_the_stale_listing_is_493_days_older_than_the_valuation_date() -> None:
    """Pass 2 defect P1-2 corrected 494 to 493. The fixture states the count."""
    assert (AS_OF - C5.first_seen.date()).days == 493


def test_the_window_sensitivity_rows_are_exact() -> None:
    assert [row.price_per_m2 for row in WINDOW_SENSITIVITY] == [
        100.0,
        140.0,
        180.0,
        60.0,
        80.0,
        40.0,
        20.0,
        10.0,
        12.0,
    ]


def test_the_price_separation_rows_carry_two_flat_levels() -> None:
    offering = [
        row.price_per_m2 for row in PRICE_SEPARATION if row.price_type == "offering"
    ]
    sales = [row.price_per_m2 for row in PRICE_SEPARATION if row.price_type == "sales"]
    assert offering == [200.0] * 5
    assert sales == [100.0] * 5


def test_shift_months_moves_a_whole_calendar_month() -> None:
    """M7's transform, checked before M7 rests on it."""
    assert shift_months(dt.date(2026, 8, 8), 1) == dt.date(2026, 9, 8)
    assert shift_months(dt.date(2026, 8, 8), 3) == dt.date(2026, 11, 8)
    assert shift_months(dt.date(2025, 4, 2), 1) == dt.date(2025, 5, 2)
    # December rolls the year, and a short month clamps the day.
    assert shift_months(dt.date(2026, 12, 31), 1) == dt.date(2027, 1, 31)
    assert shift_months(dt.date(2026, 1, 31), 1) == dt.date(2026, 2, 28)
