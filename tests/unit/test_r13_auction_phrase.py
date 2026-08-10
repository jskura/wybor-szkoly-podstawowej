"""S13 — the *cena wywoławcza* clause, tested before any page is recorded.

The Code of Civil Procedure fixes the wording, so these phrases are ours to
write. The document each sits in is not, which is why extraction — which element
holds the sentence — waits on the host robots evidence and this does not.

Every expected value comes from the test plan. Where the plan marks a value, the
comment says which decision fixed it.
"""

from __future__ import annotations

import pathlib
from decimal import Decimal
from fractions import Fraction

import pytest

from dzialki.config import load_params
from dzialki.ingest.official.auction_phrase import (
    PriceMissing,
    parse_amount,
    parse_clause,
)

pytestmark = [pytest.mark.unit]


@pytest.fixture
def tolerance(repo_root: pathlib.Path) -> Decimal:
    """D94 — one złoty. Notices round to the whole złoty, so an exact
    comparison would flag every correctly rounded notice."""
    params = load_params(repo_root / "config" / "params.yml")
    return Decimal(params.crawl.fraction_tolerance_pln)


@pytest.fixture
def phrases(fixtures_dir: pathlib.Path) -> pathlib.Path:
    return fixtures_dir / "phrases"


def read(phrases: pathlib.Path, name: str) -> str:
    return (phrases / name).read_text(encoding="utf-8").strip()


# --- amounts ---------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        "nbsp.txt",
        "narrow-nbsp.txt",
        "ascii-space.txt",
        "dot-thousands.txt",
        "no-separator.txt",
        "spelled-currency.txt",
        "pln.txt",
    ],
)
def test_every_amount_form_reads_the_same_number(phrases, name) -> None:
    """Three different spaces, a dot, no separator, two currency words.

    A notice is typeset by whoever typed it. Reading one form and missing
    another loses whole auctions rather than failing loudly.
    """
    text = read(phrases / "amounts", name)
    assert parse_amount(text[text.index("wynosi") :]) == Decimal("90000.00")


# --- the clause ------------------------------------------------------------


def test_a_first_auction_at_three_quarters(phrases, tolerance) -> None:
    clause = parse_clause(
        read(phrases, "first-auction-3-4.txt"), tolerance_pln=tolerance
    )
    assert clause.price_pln == Decimal("90000.00")
    assert clause.valuation_pln == Decimal("120000.00")
    assert clause.statutory_fraction == Fraction(3, 4)
    assert clause.auction_round == 1
    assert clause.fraction_consistent is True
    assert clause.flags == ()


def test_a_second_auction_at_two_thirds(phrases, tolerance) -> None:
    clause = parse_clause(
        read(phrases, "second-auction-2-3.txt"), tolerance_pln=tolerance
    )
    assert clause.price_pln == Decimal("80000.00")
    assert clause.statutory_fraction == Fraction(2, 3)
    assert clause.auction_round == 2
    assert clause.fraction_consistent is True


def test_a_rounded_price_within_a_zloty_is_consistent(phrases, tolerance) -> None:
    """Two thirds of 130 000 is 86 666,67. The notice says 86 667,00.

    The gap is 33 groszy, and the notice is right — it rounded. D94's tolerance
    exists for exactly this line.
    """
    clause = parse_clause(
        read(phrases, "second-auction-rounded.txt"), tolerance_pln=tolerance
    )
    assert clause.price_pln == Decimal("86667.00")
    assert clause.valuation_pln == Decimal("130000.00")
    assert clause.fraction_consistent is True
    assert clause.flags == ()


def test_a_fraction_in_words_is_read(phrases, tolerance) -> None:
    clause = parse_clause(
        read(phrases, "fraction-in-words.txt"), tolerance_pln=tolerance
    )
    assert clause.statutory_fraction == Fraction(3, 4)
    assert clause.auction_round == 1
    # No valuation stated, so consistency is unknown — which is not False.
    assert clause.fraction_consistent is None


@pytest.mark.parametrize(
    "name,expected",
    [
        ("fraction-in-percent.txt", Fraction(3, 4)),
        ("fraction-percent-approx.txt", Fraction(2, 3)),
    ],
)
def test_a_statutory_percentage_maps_to_its_fraction(
    phrases, tolerance, name, expected
) -> None:
    clause = parse_clause(read(phrases, name), tolerance_pln=tolerance)
    assert clause.statutory_fraction == expected


def test_an_unexpected_percentage_is_flagged_not_converted(phrases, tolerance) -> None:
    """Eighty percent is not a fraction the statute names.

    Converting it would claim we read a clause we did not recognise.
    """
    clause = parse_clause(
        read(phrases, "fraction-percent-unknown.txt"), tolerance_pln=tolerance
    )
    assert clause.statutory_fraction is None
    assert clause.auction_round is None
    assert clause.flags == ("fraction_unrecognised",)


def test_a_missing_fraction_is_never_defaulted(phrases, tolerance) -> None:
    """Three quarters is the commonest first-auction fraction, and that is
    exactly why assuming it is dangerous: once stored, an assumed fraction is
    indistinguishable from a read one."""
    clause = parse_clause(
        read(phrases, "valuation-no-fraction.txt"), tolerance_pln=tolerance
    )
    assert clause.statutory_fraction is None
    assert clause.auction_round is None
    assert clause.fraction_consistent is None


def test_a_real_mismatch_keeps_both_numbers(phrases, tolerance) -> None:
    """Three quarters of 130 000 is 97 500; the notice says 90 000.

    Neither number is corrected. Recomputing one would replace a figure a court
    published with a figure we preferred, and the disagreement is the finding.
    """
    clause = parse_clause(
        read(phrases, "inconsistent-fraction.txt"), tolerance_pln=tolerance
    )
    assert clause.price_pln == Decimal("90000.00")
    assert clause.valuation_pln == Decimal("130000.00")
    assert clause.fraction_consistent is False
    assert clause.flags == ("fraction_mismatch",)


def test_a_stated_round_disagreeing_with_its_fraction_claims_neither(
    phrases, tolerance
) -> None:
    clause = parse_clause(
        read(phrases, "round-fraction-conflict.txt"), tolerance_pln=tolerance
    )
    assert clause.statutory_fraction == Fraction(3, 4)
    assert clause.auction_round is None
    assert clause.flags == ("round_fraction_conflict",)


def test_a_parcel_number_is_not_a_fraction(phrases, tolerance) -> None:
    """The trap that matters most.

    `działka nr 123/4` reads as a fraction to any pattern that does not require
    the words making it one. A plot identifier would become a price rule, and
    the resulting opening price would look entirely plausible.
    """
    clause = parse_clause(
        read(phrases, "parcel-number-trap.txt"), tolerance_pln=tolerance
    )
    assert clause.price_pln == Decimal("90000.00")
    assert clause.statutory_fraction is None
    assert clause.flags == ()


def test_a_notice_with_no_price_is_quarantined(phrases, tolerance) -> None:
    with pytest.raises(PriceMissing):
        parse_clause(read(phrases, "no-price.txt"), tolerance_pln=tolerance)


def test_the_tolerance_comes_from_configuration(
    phrases, repo_root: pathlib.Path
) -> None:
    """Non-vacuity companion for the rounded case.

    At a zero tolerance the same phrase must fail. Without this, the rounded
    test would pass against a comparison that ignores the tolerance entirely.
    """
    clause = parse_clause(
        read(phrases, "second-auction-rounded.txt"), tolerance_pln=Decimal(0)
    )
    assert clause.fraction_consistent is False
    assert "fraction_mismatch" in clause.flags
