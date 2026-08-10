"""S10.3 — Polish formatting, asserted on codepoints.

Every space that separates a digit group from another digit group, and every
space that separates a number from its unit, is U+00A0. D125 ratified that one
character, so the formatter reads it from ``config/params.yml`` and holds no
copy. A space and a no-break space look identical in a file, which is why these
tests compare escapes rather than appearance.
"""

from __future__ import annotations

import ast
import datetime
import pathlib
from decimal import Decimal

import pytest

from dzialki.render.format import Formatter

pytestmark = [pytest.mark.unit]

NBSP = "\u00a0"


@pytest.fixture
def formatter(repo_root: pathlib.Path) -> Formatter:
    from dzialki.config import load_params

    params = load_params(repo_root / "config" / "params.yml")
    return Formatter(thousands_sep=params.surface.thousands_sep)


# --- D125, the separator ---------------------------------------------------


def test_the_thousands_separator_is_a_non_breaking_space(formatter: Formatter) -> None:
    out = formatter.format_int(1234567)
    assert out == f"1{NBSP}234{NBSP}567"
    assert out == "1\u00a0234\u00a0567"
    for forbidden in ("\u0020", "\u202f", "\u2009", ",", ".", "'"):
        assert forbidden not in out


def test_the_separator_comes_from_the_parameter_file_not_from_the_code() -> None:
    """Falsified by a formatter that ignores its argument and emits U+00A0."""
    seeded = Formatter(thousands_sep="_")
    assert seeded.format_int(1234567) == "1_234_567"
    assert seeded.format_area(3200) == "3_200_m²"


def test_no_render_module_holds_the_separator_as_a_literal(
    repo_root: pathlib.Path,
) -> None:
    """D125 says one hashed constant. A second copy in the source would not
    follow a change to the file, and is invisible on screen."""
    from dzialki.config import load_params

    separator = load_params(repo_root / "config" / "params.yml").surface.thousands_sep
    offenders: list[str] = []
    render = repo_root / "src" / "dzialki" / "app" / "render"
    for path in sorted(render.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            literal = isinstance(node, ast.Constant) and isinstance(node.value, str)
            if literal and separator in node.value:
                offenders.append(f"{path.relative_to(repo_root)}:{node.lineno}")
    assert offenders == []


# --- integers and decimals -------------------------------------------------


@pytest.mark.parametrize(
    "value,expected",
    [
        (0, "0"),
        (999, "999"),
        (1000, "1 000"),
        (3200, "3 200"),
        (12345, "12 345"),
        (454400, "454 400"),
        (1234567, "1 234 567"),
        (-1234, "-1 234"),
    ],
)
def test_integers_group_in_threes(formatter: Formatter, value, expected) -> None:
    assert formatter.format_int(value) == expected


def test_the_negative_sign_is_a_hyphen_minus(formatter: Formatter) -> None:
    assert formatter.format_int(-1234)[0] == "-"
    assert "−" not in formatter.format_int(-1234)


@pytest.mark.parametrize(
    "value,places,expected",
    [
        (Decimal("118.5"), 1, "118,5"),
        (Decimal("0.381"), 1, "0,4"),
        (Decimal("1234.56"), 2, "1 234,56"),
        (Decimal(104), 1, "104,0"),
    ],
)
def test_the_decimal_separator_is_a_comma(
    formatter: Formatter, value, places, expected
) -> None:
    assert formatter.format_decimal(value, places) == expected


def test_a_decimal_never_renders_in_the_english_form(formatter: Formatter) -> None:
    """V37's named falsifier, asserted as an inequality so a locale-derived
    implementation fails loudly rather than passing on a lucky machine."""
    assert formatter.format_decimal(Decimal("1234.56"), 2) != "1,234.56"


# --- prices, areas, ranges -------------------------------------------------


@pytest.mark.parametrize(
    "value,expected",
    [
        (Decimal(142), "142 zł/m²"),
        (Decimal("142.4999"), "142 zł/m²"),
        (Decimal("142.5"), "143 zł/m²"),
        (Decimal(1180), "1 180 zł/m²"),
    ],
)
def test_the_price_unit_carries_a_superscript_two(
    formatter: Formatter, value, expected
) -> None:
    rendered = formatter.format_ppm2(value)
    assert rendered == expected
    assert "²" in rendered
    for forbidden in ("zl/m2", "PLN/m2", "zł/m2", "zł / m²", "PLN/m²", "m^2"):
        assert forbidden not in rendered


def test_rounding_is_half_up_and_creates_no_false_precision(
    formatter: Formatter,
) -> None:
    assert formatter.format_ppm2(Decimal("142.4999")) == "142 zł/m²"
    assert formatter.format_ppm2(Decimal("142.5")) == "143 zł/m²"


@pytest.mark.parametrize(
    "call,value,expected",
    [
        ("format_pln", 454400, "454 400 zł"),
        ("format_area", 3200, "3 200 m²"),
        ("format_area", 1200, "1 200 m²"),
    ],
)
def test_money_and_area_separate_the_unit_with_the_same_no_break_space(
    formatter: Formatter, call, value, expected
) -> None:
    assert getattr(formatter, call)(value) == expected


@pytest.mark.parametrize(
    "low,high,expected",
    [
        (Decimal(96), Decimal(141), "96–141"),
        (Decimal(1600), Decimal(4800), "1 600–4 800"),
        (Decimal(61), Decimal(240), "61–240"),
    ],
)
def test_a_range_is_joined_by_an_en_dash(
    formatter: Formatter, low, high, expected
) -> None:
    rendered = formatter.format_range(low, high)
    assert rendered == expected
    assert "–" in rendered
    assert "—" not in rendered
    assert "-" not in rendered


def test_a_ratio_renders_with_one_decimal(formatter: Formatter) -> None:
    assert formatter.format_ratio(Decimal("0.3814")) == "0,4"
    assert formatter.format_ratio(Decimal("1.5169")) == "1,5"


# --- dates and quarters ----------------------------------------------------


@pytest.mark.parametrize(
    "value,expected",
    [
        (datetime.date(2026, 8, 1), "01.08.2026"),
        (datetime.date(2026, 8, 8), "08.08.2026"),
        (datetime.date(2026, 7, 27), "27.07.2026"),
        (datetime.date(2025, 12, 31), "31.12.2025"),
    ],
)
def test_dates_render_day_month_year_zero_padded(
    formatter: Formatter, value, expected
) -> None:
    assert formatter.format_date(value) == expected


def test_quarters_render_as_gus_labels(formatter: Formatter) -> None:
    assert formatter.format_quarter(2025, 4) == "2025Q4"
    assert formatter.format_source_quarter("gus_bdl", 2025, 4) == "GUS 2025Q4"


def test_an_unknown_source_keeps_its_own_name_in_the_quarter_label(
    formatter: Formatter,
) -> None:
    assert formatter.format_source_quarter("portal_a", 2025, 4) == "portal_a 2025Q4"


# --- plurals and locale ----------------------------------------------------


@pytest.mark.parametrize(
    "days,expected",
    [
        (1, "1 dnia"),
        (2, "2 dni"),
        (12, "12 dni"),
        (220, "220 dni"),
    ],
)
def test_the_day_count_takes_the_polish_genitive(
    formatter: Formatter, days, expected
) -> None:
    assert formatter.format_days(days) == expected


@pytest.mark.parametrize(
    "count,expected",
    [
        (1, "1 oferta"),
        (2, "2 oferty"),
        (5, "5 ofert"),
        (12, "12 ofert"),
        (22, "22 oferty"),
        (23, "23 oferty"),
        (25, "25 ofert"),
    ],
)
def test_the_offer_count_takes_the_polish_plural(
    formatter: Formatter, count, expected
) -> None:
    assert formatter.format_offers(count) == expected


def test_formatting_is_locale_independent(formatter: Formatter) -> None:
    """Nothing reads the process locale, so the output cannot follow the host."""
    import locale

    rendered = []
    for name in ("C", "C.UTF-8"):
        try:
            locale.setlocale(locale.LC_ALL, name)
        except locale.Error:
            continue
        rendered.append(
            (
                formatter.format_int(1234567),
                formatter.format_decimal(Decimal("1234.56"), 2),
                formatter.format_date(datetime.date(2026, 8, 1)),
            )
        )
    locale.setlocale(locale.LC_ALL, "C")
    assert len(set(rendered)) == 1
    assert rendered[0] == ("1 234 567", "1 234,56", "01.08.2026")
