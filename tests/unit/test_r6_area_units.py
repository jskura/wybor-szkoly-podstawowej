"""S6 §1 — every Polish area form parses to its exact value, or fails by name.

F1 is the fatal silent failure of this project: an `ar` read as a square metre
is a 100-fold error that looks entirely ordinary on the page. So every row here
pins the exact `Decimal`, the unit, the confidence and the approximation marker.
A row that asserted "not None" would pass against the bug.

The inputs are Python literals with explicit escapes. U+00A0 and U+202F are
invisible in a diff, and an editor normalises them away.
"""

from __future__ import annotations

import re
from decimal import Decimal

import pytest

from dzialki.normalize.units import (
    AR_IN_M2,
    BARE_A_KEYWORD_WINDOW,
    BARE_A_KEYWORDS,
    HA_IN_M2,
    UNIT_LEXICON,
    UNSUPPORTED_UNIT_LEXICON,
    AreaFailure,
    AreaParse,
    parse_area,
)

pytestmark = [pytest.mark.unit]

STRUCTURED = "structured"
TITLE = "title"
BODY = "body"

# (case_id, text, field, m2, unit, confidence, is_approximate)
SQUARE_METRES = [
    ("m2_plain", "1200 m²", STRUCTURED, "1200", "m2", "high", False),
    ("m2_thousands_space", "1 200 m²", STRUCTURED, "1200", "m2", "high", False),
    ("m2_thousands_nbsp", "1\u00a0200 m²", STRUCTURED, "1200", "m2", "high", False),
    (
        "m2_thousands_narrow_nbsp",
        "1\u202f200 m²",
        STRUCTURED,
        "1200",
        "m2",
        "high",
        False,
    ),
    (
        "m2_thousands_thin_space",
        "1\u2009200 m²",
        STRUCTURED,
        "1200",
        "m2",
        "high",
        False,
    ),
    ("m2_no_space", "1200m²", STRUCTURED, "1200", "m2", "high", False),
    ("m2_ascii_2", "1200 m2", STRUCTURED, "1200", "m2", "high", False),
    ("m2_ascii_caret", "1200 m^2", STRUCTURED, "1200", "m2", "high", False),
    ("m2_upper", "1200 M2", STRUCTURED, "1200", "m2", "high", False),
    ("m2_mkw", "1200 mkw", STRUCTURED, "1200", "m2", "high", False),
    ("m2_mkw_dotted", "1200 mkw.", STRUCTURED, "1200", "m2", "high", False),
    ("m2_m_kw_dotted", "1200 m kw.", STRUCTURED, "1200", "m2", "high", False),
    (
        "m2_words",
        "1200 metrów kwadratowych",
        STRUCTURED,
        "1200",
        "m2",
        "high",
        False,
    ),
    (
        "m2_words_no_diacritic",
        "1200 metrow kwadratowych",
        STRUCTURED,
        "1200",
        "m2",
        "high",
        False,
    ),
    ("m2_decimal_comma", "1 200,50 m²", STRUCTURED, "1200.50", "m2", "high", False),
    (
        "m2_decimal_comma_nbsp",
        "1\u00a0200,50 m²",
        STRUCTURED,
        "1200.50",
        "m2",
        "high",
        False,
    ),
    (
        "m2_decimal_comma_no_thousands",
        "1200,50 m²",
        STRUCTURED,
        "1200.50",
        "m2",
        "high",
        False,
    ),
    (
        "m2_trailing_zero_kept",
        "1200,00 m²",
        STRUCTURED,
        "1200.00",
        "m2",
        "high",
        False,
    ),
    ("m2_large_valid", "150 000 m²", STRUCTURED, "150000", "m2", "high", False),
    (
        "m2_two_groups_nbsp",
        "1\u00a0250\u00a0000 m²",
        STRUCTURED,
        "1250000",
        "m2",
        "high",
        False,
    ),
    (
        "m2_label_prefix",
        "Powierzchnia: 1200 m²",
        STRUCTURED,
        "1200",
        "m2",
        "high",
        False,
    ),
    ("m2_label_abbrev", "pow. 1 200 m²", STRUCTURED, "1200", "m2", "high", False),
    (
        "m2_with_price_in_string",
        "Sprzedam działkę 1200 m² za 250 000 zł",
        BODY,
        "1200",
        "m2",
        "high",
        False,
    ),
    ("m2_below_band", "250 m²", STRUCTURED, "250", "m2", "high", False),
    ("m2_at_lower_band", "300 m²", STRUCTURED, "300", "m2", "high", False),
]

ARES = [
    ("ar_arow", "12 arów", STRUCTURED, "1200", "ar", "high", False),
    ("ar_arow_no_diacritic", "12 arow", STRUCTURED, "1200", "ar", "high", False),
    ("ar_ary", "12 ary", STRUCTURED, "1200", "ar", "high", False),
    ("ar_ara", "1,5 ara", STRUCTURED, "150", "ar", "high", False),
    ("ar_singular", "1 ar", STRUCTURED, "100", "ar", "high", False),
    ("ar_dotted", "12 ar.", STRUCTURED, "1200", "ar", "high", False),
    ("ar_decimal_comma", "12,5 ara", STRUCTURED, "1250", "ar", "high", False),
    ("ar_nbsp", "12\u00a0arów", STRUCTURED, "1200", "ar", "high", False),
    ("ar_upper", "12 ARÓW", STRUCTURED, "1200", "ar", "high", False),
    ("ar_fraction_small", "0,5 ara", STRUCTURED, "50", "ar", "high", False),
    ("ar_three_digit", "120 arów", STRUCTURED, "12000", "ar", "high", False),
]

# D86 — the bare `a` is also the Polish conjunction, so it parses only where the
# field or a nearby keyword says the text is about an area.
BARE_A = [
    ("ar_abbrev_spaced", "12 a", STRUCTURED, "1200", "ar", "low", False),
    ("ar_abbrev_glued", "12a", STRUCTURED, "1200", "ar", "low", False),
    ("ar_abbrev_glued_decimal", "12,5a", STRUCTURED, "1250", "ar", "low", False),
    ("ar_abbrev_title", "Działka 12a Radzymin", TITLE, "1200", "ar", "low", False),
    (
        "ar_abbrev_body_near_keyword",
        "Ładna działka 12 a, media w drodze",
        BODY,
        "1200",
        "ar",
        "low",
        False,
    ),
]

HECTARES = [
    ("ha_decimal_comma", "0,12 ha", STRUCTURED, "1200", "ha", "high", False),
    ("ha_half", "0,5 ha", STRUCTURED, "5000", "ha", "high", False),
    ("ha_one_and_half", "1,5 ha", STRUCTURED, "15000", "ha", "high", False),
    ("ha_integer", "12 ha", STRUCTURED, "120000", "ha", "high", False),
    ("ha_one", "1 ha", STRUCTURED, "10000", "ha", "high", False),
    ("ha_word", "2 hektary", STRUCTURED, "20000", "ha", "high", False),
    ("ha_word_genitive", "5 hektarów", STRUCTURED, "50000", "ha", "high", False),
    # Two derived rows. `test_every_supported_unit_token_has_a_case` demands one
    # case per token, and Polish adverts drop the diacritic on `hektarów` as
    # often as on `arów`.
    (
        "ha_word_genitive_no_diacritic",
        "5 hektarow",
        STRUCTURED,
        "50000",
        "ha",
        "high",
        False,
    ),
    ("ha_word_singular", "1 hektar", STRUCTURED, "10000", "ha", "high", False),
    (
        "ha_word_singular_genitive",
        "0,5 hektara",
        STRUCTURED,
        "5000",
        "ha",
        "high",
        False,
    ),
    ("ha_register_four_dp", "0,2500 ha", STRUCTURED, "2500", "ha", "high", False),
    (
        "ha_register_four_dp_large",
        "1,0374 ha",
        STRUCTURED,
        "10374",
        "ha",
        "high",
        False,
    ),
    ("ha_above_band", "25 ha", STRUCTURED, "250000", "ha", "high", False),
    ("ha_at_upper_band", "20 ha", STRUCTURED, "200000", "ha", "high", False),
]

APPROXIMATE = [
    ("approx_ok_m2", "ok. 1200 m²", BODY, "1200", "m2", "low", True),
    ("approx_okolo_ar", "około 12 arów", BODY, "1200", "ar", "low", True),
    ("approx_tilde", "~1200 m²", BODY, "1200", "m2", "low", True),
    ("approx_ca", "ca 0,12 ha", BODY, "1200", "ha", "low", True),
]

# D79's one carve-out, and D90's compound and restated forms.
CARVE_OUT_AND_COMPOUND = [
    ("dot_1_2500_ha", "1.2500 ha", STRUCTURED, "12500", "ha", "low", False),
    ("dot_0_2500_ha", "0.2500 ha", STRUCTURED, "2500", "ha", "low", False),
    ("compound_ha_ar", "1 ha 25 a", STRUCTURED, "12500", "ha", "low", False),
    ("compound_ha_ar_m2", "1 ha 25 a 30 m²", STRUCTURED, "12530", "ha", "low", False),
    ("compound_ar_m2", "12 a 30 m²", STRUCTURED, "1230", "ar", "low", False),
    (
        "restated_agreeing",
        "1200 m² (12 arów)",
        STRUCTURED,
        "1200",
        "m2",
        "high",
        False,
    ),
    (
        "restated_agreeing_reverse",
        "12 arów (1200 m²)",
        STRUCTURED,
        "1200",
        "ar",
        "high",
        False,
    ),
]

SUCCESS_CASES = (
    SQUARE_METRES + ARES + BARE_A + HECTARES + APPROXIMATE + CARVE_OUT_AND_COMPOUND
)

# (case_id, text, field, failure)
FAILURE_CASES = [
    # §1.5 — the dot (D79) and the range (D82).
    ("dot_1200_m2", "1.200 m²", STRUCTURED, AreaFailure.AMBIGUOUS_SEPARATOR),
    ("dot_0_12_ha", "0.12 ha", STRUCTURED, AreaFailure.AMBIGUOUS_SEPARATOR),
    ("dot_12_5_ara", "12.5 ara", STRUCTURED, AreaFailure.AMBIGUOUS_SEPARATOR),
    ("dot_1_250_000_m2", "1.250.000 m²", STRUCTURED, AreaFailure.AMBIGUOUS_SEPARATOR),
    ("dot_three_digit_ha", "1.250 ha", STRUCTURED, AreaFailure.AMBIGUOUS_SEPARATOR),
    ("dot_five_digit_ha", "1.25000 ha", STRUCTURED, AreaFailure.AMBIGUOUS_SEPARATOR),
    ("dot_four_digit_m2", "1.2500 m²", STRUCTURED, AreaFailure.AMBIGUOUS_SEPARATOR),
    ("range_hyphen", "1200-1500 m²", STRUCTURED, AreaFailure.NOT_SINGLE_VALUED),
    ("range_en_dash", "1200–1500 m²", STRUCTURED, AreaFailure.NOT_SINGLE_VALUED),
    ("range_words", "od 1200 do 1500 m²", STRUCTURED, AreaFailure.NOT_SINGLE_VALUED),
    ("range_od", "od 1200 m²", STRUCTURED, AreaFailure.NOT_SINGLE_VALUED),
    # §1.6 — a field that disagrees with itself (D90).
    (
        "restated_disagreeing",
        "1200 m² (15 arów)",
        STRUCTURED,
        AreaFailure.CONFLICTING_STATEMENTS,
    ),
    (
        "restated_disagreeing_100x",
        "1200 m² (12 ha)",
        STRUCTURED,
        AreaFailure.CONFLICTING_STATEMENTS,
    ),
    # §1.3 — the bare `a` outside its window.
    (
        "ar_abbrev_body_prose",
        "Dojazd 12 a nawet 15 minut do centrum",
        BODY,
        AreaFailure.ABSENT,
    ),
    (
        "ar_abbrev_body_far_from_keyword",
        "Powierzchnia opisana niżej. " + "x" * 60 + "12 a",
        BODY,
        AreaFailure.ABSENT,
    ),
    # §1.7 — text that must not parse.
    ("bare_number", "1200", STRUCTURED, AreaFailure.NO_UNIT),
    ("bare_decimal", "1200,50", STRUCTURED, AreaFailure.NO_UNIT),
    ("empty", "", STRUCTURED, AreaFailure.ABSENT),
    ("whitespace", "   ", STRUCTURED, AreaFailure.ABSENT),
    ("nbsp_only", "\u00a0\u00a0", STRUCTURED, AreaFailure.ABSENT),
    ("em_dash", "—", STRUCTURED, AreaFailure.ABSENT),
    ("hyphen", "-", STRUCTURED, AreaFailure.ABSENT),
    ("brak_danych", "brak danych", STRUCTURED, AreaFailure.ABSENT),
    ("nie_podano", "nie podano", STRUCTURED, AreaFailure.ABSENT),
    ("unit_without_number", "m²", STRUCTURED, AreaFailure.NO_VALUE),
    ("unit_without_number_ar", "arów", STRUCTURED, AreaFailure.NO_VALUE),
    ("unknown_unit_morgow", "12 morgów", STRUCTURED, AreaFailure.UNKNOWN_UNIT),
    (
        "unknown_unit_morgow_no_diacritic",
        "12 morgow",
        STRUCTURED,
        AreaFailure.UNKNOWN_UNIT,
    ),
    ("unknown_unit_morg", "12 mórg", STRUCTURED, AreaFailure.UNKNOWN_UNIT),
    ("unknown_unit_morga", "1 morga", STRUCTURED, AreaFailure.UNKNOWN_UNIT),
    ("unknown_unit_morgi", "3 morgi", STRUCTURED, AreaFailure.UNKNOWN_UNIT),
    ("unknown_unit_akry", "3 akry", STRUCTURED, AreaFailure.UNKNOWN_UNIT),
    ("unknown_unit_akr", "1 akr", STRUCTURED, AreaFailure.UNKNOWN_UNIT),
    ("unknown_unit_akrow", "3 akrów", STRUCTURED, AreaFailure.UNKNOWN_UNIT),
    (
        "unknown_unit_akrow_no_diacritic",
        "3 akrow",
        STRUCTURED,
        AreaFailure.UNKNOWN_UNIT,
    ),
    ("unknown_unit_sqft", "12000 sq ft", STRUCTURED, AreaFailure.UNKNOWN_UNIT),
    ("unknown_unit_sqft_glued", "12000 sqft", STRUCTURED, AreaFailure.UNKNOWN_UNIT),
    ("zero_m2", "0 m²", STRUCTURED, AreaFailure.NON_POSITIVE),
    ("zero_ha", "0,00 ha", STRUCTURED, AreaFailure.NON_POSITIVE),
    ("negative_m2", "-500 m²", STRUCTURED, AreaFailure.NON_POSITIVE),
    ("price_only", "250 000 zł", STRUCTURED, AreaFailure.ABSENT),
    ("price_per_m2_only", "200 zł/m²", STRUCTURED, AreaFailure.ABSENT),
    ("phone_number", "tel. 601 200 300", BODY, AreaFailure.ABSENT),
    ("phone_number_grouped", "kontakt: 601-200-300", BODY, AreaFailure.ABSENT),
    ("postcode", "05-200 Wołomin", BODY, AreaFailure.ABSENT),
    ("year", "rok budowy 1998", BODY, AreaFailure.ABSENT),
    ("rooms", "3 pokoje", BODY, AreaFailure.ABSENT),
    ("distance_km", "1200 m od jeziora", BODY, AreaFailure.ABSENT),
    ("plot_number", "działka nr 1200/3", BODY, AreaFailure.ABSENT),
    (
        "price_placeholder_in_area_field",
        "Zapytaj o cenę",
        STRUCTURED,
        AreaFailure.ABSENT,
    ),
    ("category_text", "działka budowlana", STRUCTURED, AreaFailure.ABSENT),
    ("html_entity_noise", "&nbsp;", STRUCTURED, AreaFailure.ABSENT),
]


def _ids(cases: list[tuple]) -> list[str]:
    return [case[0] for case in cases]


@pytest.mark.parametrize(
    "text,field,m2,unit,confidence,approximate",
    [case[1:] for case in SUCCESS_CASES],
    ids=_ids(SUCCESS_CASES),
)
def test_parse_area_exact(
    text: str,
    field: str,
    m2: str,
    unit: str,
    confidence: str,
    approximate: bool,
) -> None:
    result = parse_area(text, field)
    assert result.m2 == Decimal(m2)
    assert result.unit == unit
    assert result.confidence == confidence
    assert result.is_approximate is approximate
    assert result.failure is None


@pytest.mark.parametrize(
    "text,field,failure",
    [case[1:] for case in FAILURE_CASES],
    ids=_ids(FAILURE_CASES),
)
def test_parse_area_failure(text: str, field: str, failure: AreaFailure) -> None:
    result = parse_area(text, field)
    assert result.m2 is None
    assert result.unit is None
    assert result.confidence == "unknown"
    assert result.failure is failure


@pytest.mark.parametrize(
    "text,field", [case[1:3] for case in SUCCESS_CASES], ids=_ids(SUCCESS_CASES)
)
def test_parse_area_returns_decimal_not_float(text: str, field: str) -> None:
    """A binary float reintroduces the drift the NUMERIC(12,2) columns avoid."""
    assert isinstance(parse_area(text, field).m2, Decimal)


@pytest.mark.parametrize(
    "text,field",
    [case[1:3] for case in SUCCESS_CASES + FAILURE_CASES],
    ids=_ids(SUCCESS_CASES + FAILURE_CASES),
)
def test_parse_area_never_returns_a_value_with_a_failure(text: str, field: str) -> None:
    result = parse_area(text, field)
    assert (result.m2 is None) != (result.failure is None)


def test_the_value_and_failure_check_catches_a_record_that_holds_both() -> None:
    """Non-vacuity companion for the invariant above.

    The invariant would pass trivially if `AreaParse` could not hold both
    states at once. It can, so the check reads the fields it claims to read.
    """
    both = AreaParse(
        m2=Decimal(1200),
        unit="m2",
        is_approximate=False,
        confidence="high",
        failure=AreaFailure.NO_UNIT,
    )
    assert ((both.m2 is None) != (both.failure is None)) is False


@pytest.mark.parametrize(
    "text,field",
    [case[1:3] for case in SUCCESS_CASES + FAILURE_CASES],
    ids=_ids(SUCCESS_CASES + FAILURE_CASES),
)
def test_confidence_is_unknown_iff_parse_failed(text: str, field: str) -> None:
    result = parse_area(text, field)
    assert (result.confidence == "unknown") == (result.m2 is None)


def test_no_case_id_is_duplicated() -> None:
    """A duplicated id drops a case from the run and no test fails."""
    ids = _ids(SUCCESS_CASES) + _ids(FAILURE_CASES)
    assert len(ids) == len(set(ids))


def _joined(cases: list[tuple]) -> str:
    text = " ".join(case[1].lower() for case in cases)
    for space in ("\u00a0", "\u202f", "\u2009"):
        text = text.replace(space, " ")
    return text


def test_every_supported_unit_token_has_a_case() -> None:
    """The lexicon and the table stay in step mechanically, not by review."""
    inputs = _joined(SUCCESS_CASES)
    missing = [
        token
        for token in UNIT_LEXICON
        if re.search(rf"(?<![\w²^]){re.escape(token)}(?![\w²^])", inputs) is None
    ]
    assert missing == []


def test_every_unknown_unit_token_has_a_case() -> None:
    inputs = _joined(FAILURE_CASES)
    missing = [
        token
        for token in UNSUPPORTED_UNIT_LEXICON
        if re.search(rf"(?<!\w){re.escape(token)}(?!\w)", inputs) is None
    ]
    assert missing == []


def test_ar_and_ha_multipliers_are_exactly_100_and_10000() -> None:
    """The assertion a transposed-constant mutant dies on."""
    assert AR_IN_M2 == Decimal(100)
    assert HA_IN_M2 == Decimal(10000)
    assert HA_IN_M2 == AR_IN_M2 * AR_IN_M2


def test_m2_trailing_zero_keeps_its_scale() -> None:
    """`Decimal("1200.00") == Decimal("1200")`, so the scale needs its own check.

    The column is NUMERIC(12,2) and the scale is part of the stated value.
    """
    result = parse_area("1200,00 m²", STRUCTURED)
    assert result.m2 == Decimal("1200.00")
    assert result.m2.as_tuple().exponent == -2


# --- D79, the dot ---------------------------------------------------------


def test_dot_carve_out_requires_four_digits_and_ha() -> None:
    """Both edges of the carve-out, asserted together.

    A carve-out written loosely swallows the ambiguous class it was carved out
    of.
    """
    assert parse_area("1.250 ha", STRUCTURED).failure is AreaFailure.AMBIGUOUS_SEPARATOR
    assert (
        parse_area("1.25000 ha", STRUCTURED).failure is AreaFailure.AMBIGUOUS_SEPARATOR
    )
    assert (
        parse_area("1.2500 m²", STRUCTURED).failure is AreaFailure.AMBIGUOUS_SEPARATOR
    )
    assert parse_area("1.2500 ha", STRUCTURED).m2 == Decimal(12500)


def test_dot_carve_out_confidence_is_low() -> None:
    """The route is a carve-out, never an explicit unambiguous token."""
    assert parse_area("1.2500 ha", STRUCTURED).confidence == "low"


# --- D82, the range -------------------------------------------------------


def test_range_returns_one_failure_not_two_values() -> None:
    """`"1200-1500"` reads as a range to a person and as two numbers to a regex.

    The parser must never return 1200 and 1500 as two parses of one field.
    """
    result = parse_area("1200-1500 m²", STRUCTURED)
    assert isinstance(result, AreaParse)
    assert result.m2 is None
    assert result.failure is AreaFailure.NOT_SINGLE_VALUED


# --- D90, compound and restated forms -------------------------------------


def test_compound_sums_rather_than_taking_the_first_value() -> None:
    """D90 supersedes the first-value rule, which read this as 10 000 m².

    That rule made the area 20% low and every zł/m² figure from it 25% high.
    The superseded reading is named here so it cannot come back quietly.
    """
    result = parse_area("1 ha 25 a", STRUCTURED)
    assert result.m2 == Decimal(12500)
    assert result.m2 != Decimal(10000)


def test_the_compound_check_fails_against_a_first_value_parser() -> None:
    """Non-vacuity companion for the test above.

    The stub is the superseded rule: it reads the first statement and stops.
    The assertion above must fail against it, or it proves nothing.
    """
    first_statement = re.match(r"[0-9]+ (?:ha|a|m²)", "1 ha 25 a").group(0)
    first_value = parse_area(first_statement, STRUCTURED).m2
    assert first_value == Decimal(10000)
    assert first_value != Decimal(12500)


def test_compound_unit_is_the_largest_unit_present() -> None:
    """`unit` records how the advert stated the area; `m2` carries the value."""
    assert parse_area("1 ha 25 a", STRUCTURED).unit == "ha"
    assert parse_area("12 a 30 m²", STRUCTURED).unit == "ar"


def test_agreeing_restatement_keeps_high_confidence() -> None:
    """A restatement that agrees is corroboration, so it is not demoted."""
    assert parse_area("1200 m² (12 arów)", STRUCTURED).confidence == "high"


def test_restatement_is_not_summed() -> None:
    """One area stated twice is 1200 m², never 2400 m².

    This kills the mutant that sums every multi-unit string.
    """
    result = parse_area("1200 m² (12 arów)", STRUCTURED)
    assert result.m2 == Decimal(1200)
    assert result.m2 != Decimal(2400)


# --- D86, the bare `a` ----------------------------------------------------


def test_parse_area_field_argument_is_required() -> None:
    """A default field picks the most permissive reading for the least
    trustworthy text."""
    with pytest.raises(TypeError):
        parse_area("12 a")  # type: ignore[call-arg]


def test_parse_area_rejects_an_unknown_field() -> None:
    with pytest.raises(ValueError):
        parse_area("12 a", "description")


def test_bare_a_needs_a_field_or_a_nearby_keyword() -> None:
    assert parse_area("12 a", STRUCTURED).m2 == Decimal(1200)
    assert parse_area("Działka 12a Radzymin", TITLE).m2 == Decimal(1200)
    assert parse_area("Ładna działka 12 a, media w drodze", BODY).m2 == Decimal(1200)
    assert parse_area("Dojazd 12 a nawet 15 minut do centrum", BODY).m2 is None


def test_bare_a_window_is_exactly_forty_characters() -> None:
    """The window is a named constant, and both of its sides are asserted."""
    assert BARE_A_KEYWORD_WINDOW == 40
    inside = "powierzchnia" + "x" * BARE_A_KEYWORD_WINDOW + "12 a"
    outside = "powierzchnia" + "x" * (BARE_A_KEYWORD_WINDOW + 1) + "12 a"
    assert parse_area(inside, BODY).m2 == Decimal(1200)
    assert parse_area(outside, BODY).m2 is None


def test_bare_a_keyword_list_is_the_decided_list() -> None:
    """Adding a keyword changes what parses, so it needs its own decision."""
    assert BARE_A_KEYWORDS == ("powierzchnia", "pow.", "działka", "grunt")


def test_a_supported_unit_needs_no_keyword_in_body_prose() -> None:
    """The D86 gate applies to the bare `a` alone.

    Without this test the gate could be widened to every unit and every test
    above would still pass.
    """
    assert parse_area("Dojazd 12 arów nawet 15 minut", BODY).m2 == Decimal(1200)


# --- D83, the approximation marker ----------------------------------------


def test_parse_area_marks_approximate() -> None:
    result = parse_area("ok. 1200 m²", BODY)
    assert result.m2 == Decimal(1200)
    assert result.is_approximate is True
    assert result.confidence == "low"


# --- totality -------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "",
        " ",
        "\u00a0",
        "m",
        "a",
        "ha",
        "((",
        "1,,2 m²",
        "1 200 200 200 m²",
        "12 a 12 a 12 a",
        "1200 m² (",
        "-",
        "--",
        "1-",
        "ok.",
        "~",
        "0",
        "0,0,0 ha",
        "12 ha 12 ha",
        "𝟙𝟚𝟘𝟘 m²",
        "1200 m² 1200 m²",
    ],
)
def test_parse_area_is_total(text: str) -> None:
    """A crash stops a whole crawl; a named failure quarantines one record."""
    result = parse_area(text, BODY)
    assert (result.m2 is None) != (result.failure is None)
    if result.failure is not None:
        assert result.failure in AreaFailure
