"""S6 §2 — Polish price forms parse to an exact PLN total, or fail by name.

A placeholder is not a price. A rent is not a price. A per-m² figure in the
total-price field is a connector layout defect, and it gets its own failure so
V50's per-reason rates can show it spiking on one source.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from dzialki.normalize.units import (
    MLN_MULTIPLIER,
    TYS_MULTIPLIER,
    PriceFailure,
    PriceParse,
    parse_price,
)

pytestmark = [pytest.mark.unit]

# (case_id, text, pln, confidence)
PRICE_CASES = [
    ("plain_zl", "250 000 zł", "250000", "high"),
    ("nbsp_zl", "250\u00a0000 zł", "250000", "high"),
    ("narrow_nbsp_zl", "250\u202f000 zł", "250000", "high"),
    ("zl_no_diacritic", "250 000 zl", "250000", "high"),
    ("pln_suffix", "1 250 000 PLN", "1250000", "high"),
    ("pln_lower", "1 250 000 pln", "1250000", "high"),
    ("grosze", "250 000,50 zł", "250000.50", "high"),
    ("grosze_dot", "250 000.50 zł", "250000.50", "high"),
    ("no_currency", "250000", "250000", "low"),
    ("negotiable_suffix", "250 000 zł do negocjacji", "250000", "high"),
    ("negotiable_abbrev", "250 000 zł (do neg.)", "250000", "high"),
    ("label_prefix", "Cena: 250 000 zł", "250000", "high"),
    ("glued", "250000zł", "250000", "high"),
    ("tys", "250 tys. zł", "250000", "low"),
    ("tys_no_dot", "250 tys zł", "250000", "low"),
    ("mln", "1,2 mln zł", "1200000", "low"),
    ("mln_word", "1,2 miliona zł", "1200000", "low"),
]

# (case_id, text, failure)
PRICE_FAILURE_CASES = [
    ("placeholder_ask", "Zapytaj o cenę", PriceFailure.PLACEHOLDER),
    ("placeholder_ask_lower", "zapytaj o cenę", PriceFailure.PLACEHOLDER),
    ("placeholder_ask_no_diacritic", "zapytaj o cene", PriceFailure.PLACEHOLDER),
    ("placeholder_agree", "cena do uzgodnienia", PriceFailure.PLACEHOLDER),
    ("placeholder_negotiate", "do negocjacji", PriceFailure.PLACEHOLDER),
    ("placeholder_contact", "kontakt w sprawie ceny", PriceFailure.PLACEHOLDER),
    ("placeholder_dash", "—", PriceFailure.ABSENT),
    ("empty", "", PriceFailure.ABSENT),
    ("whitespace", "    ", PriceFailure.ABSENT),
    ("zero", "0 zł", PriceFailure.NON_POSITIVE),
    ("zero_decimal", "0,00 zł", PriceFailure.NON_POSITIVE),
    ("negative", "-1000 zł", PriceFailure.NON_POSITIVE),
    ("per_m2_only", "200 zł/m²", PriceFailure.NOT_A_TOTAL),
    ("per_m2_only_words", "200 zł za m²", PriceFailure.NOT_A_TOTAL),
    ("rent", "2 500 zł/mies.", PriceFailure.NOT_A_TOTAL),
    ("foreign_currency", "60 000 EUR", PriceFailure.UNSUPPORTED_CURRENCY),
    ("text_only", "okazja!", PriceFailure.ABSENT),
]


def _ids(cases: list[tuple]) -> list[str]:
    return [case[0] for case in cases]


@pytest.mark.parametrize(
    "text,pln,confidence", [case[1:] for case in PRICE_CASES], ids=_ids(PRICE_CASES)
)
def test_parse_price_exact(text: str, pln: str, confidence: str) -> None:
    result = parse_price(text)
    assert result.pln == Decimal(pln)
    assert result.confidence == confidence
    assert result.failure is None


@pytest.mark.parametrize(
    "text,failure",
    [case[1:] for case in PRICE_FAILURE_CASES],
    ids=_ids(PRICE_FAILURE_CASES),
)
def test_parse_price_placeholder_is_not_a_price(
    text: str, failure: PriceFailure
) -> None:
    result = parse_price(text)
    assert result.pln is None
    assert result.confidence == "unknown"
    assert result.failure is failure


@pytest.mark.parametrize(
    "text", [case[1] for case in PRICE_CASES], ids=_ids(PRICE_CASES)
)
def test_parse_price_returns_decimal_not_float(text: str) -> None:
    assert isinstance(parse_price(text).pln, Decimal)


@pytest.mark.parametrize(
    "text",
    [case[1] for case in PRICE_CASES + PRICE_FAILURE_CASES],
    ids=_ids(PRICE_CASES + PRICE_FAILURE_CASES),
)
def test_parse_price_never_returns_a_value_with_a_failure(text: str) -> None:
    result = parse_price(text)
    assert (result.pln is None) != (result.failure is None)


def test_the_value_and_failure_check_catches_a_record_that_holds_both() -> None:
    """Non-vacuity companion for the invariant above."""
    both = PriceParse(
        pln=Decimal(250000), confidence="high", failure=PriceFailure.ABSENT
    )
    assert ((both.pln is None) != (both.failure is None)) is False


def test_grosze_keep_their_scale() -> None:
    """`price_pln` is NUMERIC(12,2); the two decimal places are part of it."""
    assert parse_price("250 000,50 zł").pln.as_tuple().exponent == -2


def test_magnitude_multipliers_are_named_constants() -> None:
    assert TYS_MULTIPLIER == Decimal(1000)
    assert MLN_MULTIPLIER == Decimal(1000000)


def test_magnitude_abbreviation_is_never_high_confidence() -> None:
    """The multiplier is inferred from an abbreviation, not read from digits."""
    for text in ("250 tys. zł", "250 tys zł", "1,2 mln zł", "1,2 miliona zł"):
        assert parse_price(text).confidence == "low", text


def test_a_negotiable_suffix_does_not_hide_a_stated_price() -> None:
    """`"do negocjacji"` alone is a placeholder, but it never wins over digits.

    The placeholder check runs after the value search, so a stated price with a
    negotiable suffix keeps its number.
    """
    assert parse_price("250 000 zł do negocjacji").pln == Decimal(250000)
    assert parse_price("do negocjacji").failure is PriceFailure.PLACEHOLDER


def test_price_dot_and_area_dot_are_treated_differently() -> None:
    """The asymmetry with D79 is deliberate.

    A price is bounded by the currency's two decimal places, so `250 000.50`
    has one reading. `"1.200 m²"` has two readings 1000 times apart.
    """
    from dzialki.normalize.units import AreaFailure, parse_area

    assert parse_price("250 000.50 zł").pln == Decimal("250000.50")
    assert (
        parse_area("1.200 m²", "structured").failure is AreaFailure.AMBIGUOUS_SEPARATOR
    )


def test_zero_is_separated_from_the_placeholders() -> None:
    """The schema has CHECK (price_pln > 0), so a zero would crash at insert.

    It is caught here with its own reason, so it appears in the quarantine
    composition instead of in the run's exception log.
    """
    assert parse_price("0 zł").failure is PriceFailure.NON_POSITIVE
    assert parse_price("0 zł").failure is not PriceFailure.PLACEHOLDER


@pytest.mark.parametrize(
    "text",
    [
        "",
        " ",
        "zł",
        "zł zł",
        "0",
        "-",
        "1,,2 zł",
        "250 000 zł 300 000 zł",
        "1.2.3.4 zł",
        "𝟚𝟝𝟘 zł",
        "250 tys. mln zł",
        "EUR",
        "/m²",
    ],
)
def test_parse_price_is_total(text: str) -> None:
    result = parse_price(text)
    assert (result.pln is None) != (result.failure is None)
    if result.failure is not None:
        assert result.failure in PriceFailure
