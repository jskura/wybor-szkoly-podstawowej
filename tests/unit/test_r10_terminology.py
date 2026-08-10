"""S10.17 — the terminology lint, and where its term list lives.

D99 gives the protected terms one home: the `## Protected terms` section of
`docs/12-glossary.md`. The lint parses that section and holds no copy, so adding
a term to the glossary reaches the lint with no code change. What the lint does
hold is the table of forbidden renderings, keyed by term — and a test asserts
that key set equals the parsed list, so the two cannot drift apart.

The parser lives in `render/`, which performs no I/O. The caller reads the file
and hands over the text.
"""

from __future__ import annotations

import pathlib

import pytest

from dzialki.render.errors import GlossaryParseError, UnknownProtectedTermError
from dzialki.render.terminology import (
    TERM_RULES,
    lint_text,
    parse_protected_terms,
    rules_for,
)

pytestmark = [pytest.mark.unit]

GLOSSARY_TERMS = (
    "cena ofertowa",
    "cena transakcyjna",
    "działka",
    "plan ogólny",
    "MPZP",
    "wypis i wyrys",
    "media",
    "droga dojazdowa",
    "zakres międzykwartylowy",
    "warunki zabudowy",
    "służebność przejazdu",
    "klasa gruntu",
)


@pytest.fixture
def glossary(repo_root: pathlib.Path) -> str:
    return (repo_root / "docs" / "12-glossary.md").read_text(encoding="utf-8")


# --- D99, one home for the list -------------------------------------------


def test_the_protected_list_is_read_from_the_glossary(glossary: str) -> None:
    assert parse_protected_terms(glossary) == GLOSSARY_TERMS


def test_the_glossary_lists_twelve_terms(glossary: str) -> None:
    """D118 added the last two. Twelve is the count the test plan states."""
    assert len(parse_protected_terms(glossary)) == 12


def test_the_forbidden_rendering_table_matches_the_glossary_column(
    glossary: str,
) -> None:
    """The device that stops the table becoming a second copy of the list."""
    assert tuple(rule.term for rule in TERM_RULES) == parse_protected_terms(glossary)


def test_a_term_in_the_glossary_with_no_rule_is_named_loudly(glossary: str) -> None:
    """Adding a term to the glossary must not silently go unchecked."""
    with pytest.raises(UnknownProtectedTermError) as caught:
        rules_for((*GLOSSARY_TERMS, "rękojmia"))
    assert "rękojmia" in str(caught.value)


def test_no_two_terms_forbid_the_same_rendering() -> None:
    """`droga dojazdowa` and `służebność przejazdu` share the concept of access.
    A shared forbidden rendering would fire the lint on correct copy."""
    seen: dict[str, str] = {}
    for rule in TERM_RULES:
        for rendering in rule.forbidden:
            assert rendering not in seen, (rendering, rule.term, seen.get(rendering))
            seen[rendering] = rule.term


def test_a_document_with_no_term_list_is_a_parse_error() -> None:
    """A silent empty list would make every later assertion vacuous."""
    with pytest.raises(GlossaryParseError):
        parse_protected_terms("# Glossary\n\n## Protected terms (D99)\n\nProse only.\n")


def test_a_document_with_no_protected_section_is_a_parse_error() -> None:
    with pytest.raises(GlossaryParseError):
        parse_protected_terms("# Glossary\n\n## Prices\n\n`cena ofertowa`\n")


# --- the seeded violations -------------------------------------------------


def test_the_lint_flags_the_seeded_line_exactly(glossary: str) -> None:
    rules = rules_for(parse_protected_terms(glossary))
    seeded = (
        "Mediana ceny rynkowej dla tej parceli to 118 zł/m² — sprawdź plan w gminie."
    )
    findings = lint_text(seeded, rules=rules, filename="bad_terms.py")
    assert [finding.message() for finding in findings] == [
        "bad_terms.py:1: protected term `cena ofertowa` rendered as `cena rynkowa`",
        "bad_terms.py:1: protected term `działka` rendered as `parcela`",
        "bad_terms.py:1: protected term `MPZP` rendered as `plan`",
        "bad_terms.py:1: protected term `plan ogólny` rendered as `plan`",
    ]


def test_the_lint_reports_every_violation_on_a_line(glossary: str) -> None:
    """Three findings on one line is the point. A lint that stops at the first
    turns a rewrite into several rounds."""
    rules = rules_for(parse_protected_terms(glossary))
    seeded = (
        "Mediana ceny rynkowej dla tej parceli to 118 zł/m² — sprawdź plan w gminie."
    )
    findings = lint_text(seeded, rules=rules, filename="bad_terms.py")
    assert len(findings) == 4
    assert {finding.line for finding in findings} == {1}


@pytest.mark.parametrize(
    "line,term",
    [
        ("cena rynkowa 118 zł/m²", "cena ofertowa"),
        ("mediana ceny w tej gminie to 104 zł/m²", "cena transakcyjna"),
        ("Ta parcela ma 3 200 m²", "działka"),
        ("Poproś o wypis w urzędzie gminy", "wypis i wyrys"),
        ("Przyłącza w granicy działki", "media"),
        ("Dojazd drogą gruntową", "droga dojazdowa"),
        ("IQR 96–141", "zakres międzykwartylowy"),
        ("Działka z WZ", "warunki zabudowy"),
        ("Prawo przejazdu przez sąsiednią działkę", "służebność przejazdu"),
        ("Jakość gleby klasy V", "klasa gruntu"),
    ],
)
def test_each_seeded_line_names_its_term(glossary: str, line: str, term: str) -> None:
    rules = rules_for(parse_protected_terms(glossary))
    findings = lint_text(line, rules=rules, filename="bad_terms.py")
    assert term in {finding.term for finding in findings}, [
        finding.message() for finding in findings
    ]


def test_an_english_price_phrase_is_flagged(glossary: str) -> None:
    rules = rules_for(parse_protected_terms(glossary))
    findings = lint_text(
        "market price 118 PLN/m2", rules=rules, filename="bad_terms.py"
    )
    assert [finding.rendering for finding in findings] == ["market price"]


def test_the_lint_finds_the_line_number(glossary: str) -> None:
    rules = rules_for(parse_protected_terms(glossary))
    findings = lint_text(
        "cena ofertowa 118 zł/m²\nTa parcela ma 3 200 m²\n",
        rules=rules,
        filename="bad_terms.py",
    )
    assert [(finding.line, finding.term) for finding in findings] == [(2, "działka")]


# --- the bare-word rule and its qualifiers --------------------------------


@pytest.mark.parametrize(
    "line",
    [
        "cena ofertowa",
        "cena transakcyjna",
        "cena wywoławcza",
        "cena przetargowa",
        "Cena z ogłoszenia: 454 400 zł",
        "Ceny transakcyjne · powiat skierniewicki · GUS 2025Q4",
        "gdyby ta działka miała plan miejscowy, porównania byłyby inne",
        "plan ogólny gminy",
        "wypis i wyrys",
        "droga dojazdowa",
    ],
)
def test_a_qualified_use_of_a_bare_word_is_legal(glossary: str, line: str) -> None:
    """`cena` and `plan` are legal words. What the lint rejects is the bare use
    where the qualified term is meant, so the rule reads the next word."""
    rules = rules_for(parse_protected_terms(glossary))
    assert lint_text(line, rules=rules, filename="ui.py") == ()


def test_the_bare_word_rule_matches_polish_inflection(glossary: str) -> None:
    """`cena rynkowa` appears in copy as `ceny rynkowej`. A literal match would
    find nothing and the lint would pass by doing nothing."""
    rules = rules_for(parse_protected_terms(glossary))
    findings = lint_text("Mediana ceny rynkowej", rules=rules, filename="ui.py")
    assert [finding.rendering for finding in findings] == ["cena rynkowa"]


def test_a_longer_word_that_merely_starts_with_a_protected_word_is_left_alone(
    glossary: str,
) -> None:
    """`planistycznych` is not `plan`, and `gruntu` is not `grunt`. Without this
    the lint fires on its own sanctioned copy."""
    rules = rules_for(parse_protected_terms(glossary))
    for line in (
        "brak danych planistycznych — sprawdź w gminie",
        "brak danych o klasie gruntu — sprawdź w gminie",
    ):
        assert lint_text(line, rules=rules, filename="ui.py") == (), line
