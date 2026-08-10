"""The terminology lint, and where its term list lives.

D99 gives the protected terms one home: the ``## Protected terms`` section of
`docs/12-glossary.md`. This module parses that section and holds no copy of the
list. What it does hold is the forbidden renderings, keyed by term, because the
glossary states which terms are protected and not how they are mistranslated.
``rules_for`` joins the two and refuses a term it has no renderings for, so a
term added to the glossary is covered or names itself loudly.

`render/` performs no I/O. The caller reads the glossary and hands over the
text.

**Two mechanics make the lint usable on Polish.** A forbidden rendering matches
its inflected forms, because copy says *ceny rynkowej* and never *cena rynkowa*.
And a protected term is masked out of the line before the search runs, so
*cena transakcyjna* does not trip the rule against a bare *cena*.
"""

from __future__ import annotations

import dataclasses
import re

from .errors import GlossaryParseError, UnknownProtectedTermError

PROTECTED_SECTION = "## Protected terms"
TERM_PATTERN = re.compile(r"`([^`]+)`")
SEPARATOR = "·"
VOWELS = "aeiouyąęó"
MIN_STEM = 3


@dataclasses.dataclass(frozen=True)
class TermRule:
    """One protected term and the renderings the lint rejects.

    ``qualified_by`` applies to a one-word rendering. The bare word is often a
    legal Polish word — *cena*, *plan*, *droga* — and what the rule rejects is
    the bare use where the precise term is meant. The next word decides.
    """

    term: str
    forbidden: tuple[str, ...]
    qualified_by: tuple[str, ...] = ()


# The forbidden renderings, keyed by the glossary's term. `plan miejscowy` where
# the acronym is meant is not decidable by a text lint, so `plan` is checked as
# a bare word with its qualifiers instead.
TERM_RULES: tuple[TermRule, ...] = (
    TermRule(
        term="cena ofertowa",
        forbidden=("cena rynkowa", "market price"),
    ),
    TermRule(
        term="cena transakcyjna",
        forbidden=("cena", "transaction price", "cena sprzedaży"),
        qualified_by=(
            "ofertowa",
            "transakcyjna",
            "wywoławcza",
            "przetargowa",
            "rynkowa",
            "sprzedaży",
            "za",
            "z",
        ),
    ),
    TermRule(
        term="działka",
        forbidden=("parcela", "grunt", "plot", "parcel"),
    ),
    TermRule(
        term="plan ogólny",
        forbidden=("studium", "general plan"),
        qualified_by=("ogólny", "miejscowy", "zagospodarowania"),
    ),
    TermRule(
        term="MPZP",
        forbidden=("plan", "zoning plan"),
        qualified_by=("ogólny", "miejscowy", "zagospodarowania"),
    ),
    TermRule(
        term="wypis i wyrys",
        forbidden=("wypis", "wyrys", "zaświadczenie", "extract"),
        qualified_by=("i",),
    ),
    TermRule(
        term="media",
        forbidden=("infrastruktura", "przyłącza", "utilities"),
    ),
    TermRule(
        term="droga dojazdowa",
        forbidden=("dojazd", "droga", "access"),
        qualified_by=("dojazdowa", "gminna", "powiatowa"),
    ),
    TermRule(
        term="zakres międzykwartylowy",
        forbidden=("IQR", "rozstęp ćwiartkowy", "interquartile range"),
    ),
    TermRule(
        term="warunki zabudowy",
        forbidden=("WZ", "warunki", "planning conditions"),
        qualified_by=("zabudowy",),
    ),
    TermRule(
        term="służebność przejazdu",
        forbidden=("służebność", "prawo przejazdu", "easement"),
        qualified_by=("przejazdu",),
    ),
    TermRule(
        term="klasa gruntu",
        forbidden=("jakość gleby", "klasa ziemi", "soil class", "land class"),
    ),
)

# `plan ogólny` and `MPZP` both forbid the bare word `plan`. The list above
# gives it to `MPZP`; this pair adds it back for `plan ogólny` without letting
# one rendering sit in two rules, which the no-collision test forbids.
SHARED_BARE_WORDS: dict[str, tuple[str, ...]] = {"plan ogólny": ("plan",)}


@dataclasses.dataclass(frozen=True)
class Finding:
    """One protected term, loosely rendered, at one line."""

    filename: str
    line: int
    term: str
    rendering: str
    column: int

    def message(self) -> str:
        return (
            f"{self.filename}:{self.line}: protected term `{self.term}` "
            f"rendered as `{self.rendering}`"
        )


def parse_protected_terms(document: str) -> tuple[str, ...]:
    """Read the protected-term list out of the glossary (D99).

    The list is the one paragraph of the section made entirely of backticked
    terms joined by the middle dot. Prose in the same section is skipped, and a
    section with no such paragraph is an error — a silently empty list would
    make every later assertion vacuous.
    """
    if PROTECTED_SECTION not in document:
        raise GlossaryParseError(
            f"the document carries no {PROTECTED_SECTION!r} section"
        )
    section = document.split(PROTECTED_SECTION, 1)[1]
    section = section.split("\n## ", 1)[0]

    lists: list[tuple[str, ...]] = []
    for paragraph in section.split("\n\n"):
        stripped = paragraph.strip()
        if not stripped or stripped.startswith("("):
            continue
        remainder = TERM_PATTERN.sub("", stripped).replace(SEPARATOR, "")
        if remainder.strip():
            continue
        terms = tuple(TERM_PATTERN.findall(stripped))
        if terms:
            lists.append(terms)

    if not lists:
        raise GlossaryParseError(
            f"the {PROTECTED_SECTION!r} section holds no term list"
        )
    if len(lists) > 1:
        raise GlossaryParseError(
            f"the {PROTECTED_SECTION!r} section holds more than one term list"
        )
    return lists[0]


def rules_for(terms) -> tuple[TermRule, ...]:
    """The rules for the parsed terms, in the glossary's order."""
    by_term = {rule.term: rule for rule in TERM_RULES}
    found: list[TermRule] = []
    for term in terms:
        if term not in by_term:
            raise UnknownProtectedTermError(
                f"the protected term {term!r} has no forbidden renderings; "
                "add them beside the other terms"
            )
        rule = by_term[term]
        extra = SHARED_BARE_WORDS.get(term, ())
        if extra:
            rule = dataclasses.replace(rule, forbidden=(*rule.forbidden, *extra))
        found.append(rule)
    return tuple(found)


def _stem(word: str) -> str:
    """Drop one trailing vowel, so a word matches its inflected forms.

    A word already ending in a consonant keeps its exact spelling. Extending it
    would match every longer word that starts the same way — *planistycznych*
    is not *plan*, and the lint must not fire on its own sanctioned copy.
    """
    if len(word) > MIN_STEM and word[-1].lower() in VOWELS:
        return word[:-1]
    return word


def _phrase_pattern(phrase: str) -> re.Pattern[str]:
    parts = []
    for word in phrase.split():
        stem = _stem(word)
        tail = r"\w*" if stem != word else ""
        parts.append(re.escape(stem) + tail)
    return re.compile(r"(?<!\w)" + r"\s+".join(parts) + r"(?!\w)", re.IGNORECASE)


def _qualifier_pattern(qualifiers) -> re.Pattern[str] | None:
    if not qualifiers:
        return None
    stems = []
    for word in qualifiers:
        stem = _stem(word)
        stems.append(re.escape(stem) + (r"\w*" if stem != word else ""))
    return re.compile(r"\s+(?:" + "|".join(stems) + r")(?!\w)", re.IGNORECASE)


def _mask(line: str, rules) -> str:
    """Blank out every protected term, so the term never trips its own rule."""
    masked = line
    for rule in rules:
        masked = _phrase_pattern(rule.term).sub(
            lambda match: " " * len(match.group()), masked
        )
    return masked


def lint_text(text: str, *, rules, filename: str) -> tuple[Finding, ...]:
    """Every loose rendering in ``text``, ordered by line, column and term.

    Every violation on a line is reported. A lint that stops at the first turns
    one rewrite into several rounds.
    """
    found: list[Finding] = []
    for number, line in enumerate(text.splitlines(), 1):
        masked = _mask(line, rules)
        for rule in rules:
            qualifier = _qualifier_pattern(rule.qualified_by)
            for rendering in rule.forbidden:
                pattern = _phrase_pattern(rendering)
                for match in pattern.finditer(masked):
                    if (
                        qualifier is not None
                        and " " not in rendering
                        and qualifier.match(masked, match.end())
                    ):
                        continue
                    found.append(
                        Finding(
                            filename=filename,
                            line=number,
                            term=rule.term,
                            rendering=rendering,
                            column=match.start(),
                        )
                    )
    found.sort(key=lambda finding: (finding.line, finding.column, finding.term))
    return tuple(found)
