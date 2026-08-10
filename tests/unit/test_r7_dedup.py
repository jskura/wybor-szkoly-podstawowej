"""S7 — exact dedup, and the two directions it gets wrong.

v0 under-merges by design and over-merges in one known case. Both are tested,
because a matcher whose misses are undocumented is a matcher nobody can improve
deliberately.
"""

from __future__ import annotations

import itertools
from decimal import Decimal

import pytest

from dzialki.dedup import (
    ACCEPTED_FALSE_MERGE_CAVEAT,
    MATCH_KEY_FIELDS,
    Listing,
    deduplicate,
)

pytestmark = [pytest.mark.unit]


def listing(
    *,
    source_id: int = 1,
    external_id: str = "a",
    first_seen_at: str = "2026-08-01T09:00:00Z",
    area_m2: str = "1200.00",
    price_pln: str = "250000.00",
    teryt_gmina: str = "1015042",
    asset_class: str = "land_building",
) -> Listing:
    return Listing(
        source_id=source_id,
        external_id=external_id,
        first_seen_at=first_seen_at,
        area_m2=Decimal(area_m2),
        price_pln=Decimal(price_pln),
        teryt_gmina=teryt_gmina,
        asset_class=asset_class,
    )


# --- the key itself --------------------------------------------------------


def test_the_match_key_is_exactly_the_four_named_fields() -> None:
    """D78 made this a quadruple. A fifth field needs a decision, not a commit."""
    assert MATCH_KEY_FIELDS == (
        "area_m2",
        "price_pln",
        "teryt_gmina",
        "asset_class",
    )


# --- exact matches collapse ------------------------------------------------


def test_a_cross_source_exact_match_collapses() -> None:
    result = deduplicate(
        [listing(source_id=1, external_id="a"), listing(source_id=2, external_id="b")]
    )
    assert len(result.clusters) == 1
    assert result.clusters[0].duplicate_count == 2


def test_duplicate_count_reflects_cluster_size() -> None:
    result = deduplicate([listing(external_id=name) for name in ("a", "b", "c")])
    assert result.clusters[0].duplicate_count == 3


def test_the_canonical_record_does_not_depend_on_input_order() -> None:
    """D84 is a total order. Without the tie-breaks, two records first seen in
    the same second would swap between runs for no visible reason."""
    members = [
        listing(source_id=2, external_id="b", first_seen_at="2026-08-01T09:00:00Z"),
        listing(source_id=1, external_id="c", first_seen_at="2026-08-01T09:00:00Z"),
        listing(source_id=3, external_id="a", first_seen_at="2026-07-30T09:00:00Z"),
    ]
    canonicals = {
        deduplicate(list(order)).clusters[0].canonical.external_id
        for order in itertools.permutations(members)
    }
    assert canonicals == {"a"}


def test_a_singleton_still_gets_a_cluster() -> None:
    """No special case, so no later code has to remember there is one."""
    result = deduplicate([listing()])
    assert len(result.clusters) == 1
    assert result.clusters[0].duplicate_count == 1


def test_both_counts_are_reported_side_by_side() -> None:
    """F3's detector. More data looks like better data, so neither number
    travels alone."""
    listings = [listing(external_id=str(n)) for n in range(3)]
    listings += [listing(external_id=f"x{n}", area_m2=str(1000 + n)) for n in range(7)]
    result = deduplicate(listings)
    assert result.n_before == 10
    assert result.n_after == 8


# --- near-duplicates must not merge ----------------------------------------


@pytest.mark.parametrize(
    "field,value",
    [
        # Two agencies, one plot. v0 correctly MISSES this. The test asserts a
        # known miss so a future matcher flips it deliberately.
        ("price_pln", "255000.00"),
        ("area_m2", "1205.00"),
        ("teryt_gmina", "1015052"),
        ("asset_class", "land_agricultural"),
    ],
)
def test_a_near_duplicate_does_not_merge(field, value) -> None:
    other = listing(external_id="b", **{field: value})
    result = deduplicate([listing(external_id="a"), other])
    assert len(result.clusters) == 2
    assert [cluster.duplicate_count for cluster in result.clusters] == [1, 1]


def test_two_neighbouring_plots_with_different_prices_stay_apart() -> None:
    result = deduplicate(
        [
            listing(external_id="a", price_pln="250000.00"),
            listing(external_id="b", price_pln="260000.00"),
        ]
    )
    assert len(result.clusters) == 2


# --- the merge D78 accepts -------------------------------------------------


def test_an_identical_round_pair_merges_and_this_is_the_accepted_loss() -> None:
    """Two genuinely different plots, both 1000 m² at 100 000 zł, one gmina.

    D78 chose the four-field key over a round-number guard and accepted this.
    The test records the loss rather than leaving it to be discovered.
    """
    result = deduplicate(
        [
            listing(external_id="a", area_m2="1000.00", price_pln="100000.00"),
            listing(external_id="b", area_m2="1000.00", price_pln="100000.00"),
        ]
    )
    assert len(result.clusters) == 1
    assert result.clusters[0].duplicate_count == 2


def test_every_run_states_the_accepted_false_merge_risk() -> None:
    """A rate nobody measured must not be implied to be zero."""
    result = deduplicate([listing()])
    assert ACCEPTED_FALSE_MERGE_CAVEAT in result.caveats
    assert "unknown" in ACCEPTED_FALSE_MERGE_CAVEAT
