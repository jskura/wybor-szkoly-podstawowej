"""D123 — a parcel that straddles a gmina boundary gets one owner, always.

The 40/20 case exercises the majority rule. The 50/50 case exercises the tie
rule, which had none until D123 and was therefore whatever the row order
happened to be.
"""

from __future__ import annotations

import pytest

from dzialki.geo import owning_gmina
from dzialki.geo.straddle import GminaShare

pytestmark = [pytest.mark.unit]


def test_the_larger_share_wins() -> None:
    result = owning_gmina(
        [GminaShare("1465011", 2000.0), GminaShare("1401011", 1000.0)]
    )
    assert result.teryt == "1465011"
    assert result.was_tie is False


def test_an_exact_tie_goes_to_the_lowest_teryt() -> None:
    result = owning_gmina(
        [GminaShare("1465011", 1500.0), GminaShare("1401011", 1500.0)]
    )
    assert result.teryt == "1401011"
    assert result.was_tie is True


def test_a_tie_is_reported_so_the_page_can_say_so() -> None:
    """The tie-break decides the number. It must not hide the straddle."""
    result = owning_gmina(
        [GminaShare("1465011", 1500.0), GminaShare("1401011", 1500.0)]
    )
    assert [share.teryt for share in result.shares] == ["1401011", "1465011"]


def test_the_answer_does_not_depend_on_input_order() -> None:
    """A rule that is not a total order gives a different answer on a re-run."""
    shares = [GminaShare("1465011", 1500.0), GminaShare("1401011", 1500.0)]
    assert owning_gmina(shares).teryt == owning_gmina(list(reversed(shares))).teryt


def test_a_parcel_overlapping_no_gmina_is_an_error() -> None:
    """Returning a default here would bury a geometry problem in a price."""
    with pytest.raises(ValueError):
        owning_gmina([])
