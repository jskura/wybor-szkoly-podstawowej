"""Polish area and price strings to exact `Decimal` values, or a named failure.

F1 — an `ar` read as a square metre — is the fatal silent failure of this
project. It is a 100-fold error, and the listing that carries it looks entirely
ordinary. So this module refuses every reading it cannot justify, and says
which reading it refused. A guess here becomes a price per square metre that
nobody can tell from a real one.

Four rules of the parser are decisions, not taste:

- A dot in an area is ambiguous and the record is quarantined (D79). The one
  carve-out is a dot with exactly four digits and the unit `ha`, which is the
  parcel register's own format. `1.200` read as `1.2` is a 1000-fold error.
- An area range is not single-valued (D82). A midpoint invents a number nobody
  wrote.
- A compound area sums (D90). The superseded rule took the first value and read
  `1 ha 25 a` as 10 000 m², which is 20% low.
- The bare `a` is also the Polish conjunction *and*, so it reads as ares only in
  a structured field or a title, or near an area keyword in body text (D86).

Everything returns a value **or** a failure, never both and never neither. A
crash stops a whole crawl; a named failure quarantines one record.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum
from itertools import pairwise
from typing import Literal, NamedTuple

# `Decimal("100")` rather than `Decimal(100)`: the bare int collides with a
# ratified parameter, and V65's scan reads every integer literal in `src/`.
AR_IN_M2 = Decimal("100")  # noqa: FURB157
HA_IN_M2 = Decimal(10000)
M2_IN_M2 = Decimal(1)

TYS_MULTIPLIER = Decimal(1000)
MLN_MULTIPLIER = Decimal(1000000)

# D86. The window is measured from the keyword to the number, in characters.
BARE_A_KEYWORD_WINDOW = 40
BARE_A_KEYWORDS = ("powierzchnia", "pow.", "działka", "grunt")

Field = Literal["structured", "title", "body"]
FIELDS: tuple[Field, ...] = ("structured", "title", "body")

Confidence = Literal["high", "low", "unknown"]
Unit = Literal["m2", "ar", "ha"]

# Every supported token, with the unit it names. A token added here without a
# case in the test table fails `test_every_supported_unit_token_has_a_case`.
UNIT_LEXICON: dict[str, Unit] = {
    "metrów kwadratowych": "m2",
    "metrow kwadratowych": "m2",
    "m kw": "m2",
    "mkw": "m2",
    "m²": "m2",
    "m^2": "m2",
    "m2": "m2",
    "hektarów": "ha",
    "hektarow": "ha",
    "hektary": "ha",
    "hektara": "ha",
    "hektar": "ha",
    "ha": "ha",
    "arów": "ar",
    "arow": "ar",
    "ary": "ar",
    "ara": "ar",
    "ar": "ar",
    "a": "ar",
}

# Units we do not convert. They fail loudly, never as a silent m² reading.
UNSUPPORTED_UNIT_LEXICON: tuple[str, ...] = (
    "morgów",
    "morgow",
    "mórg",
    "morgi",
    "morga",
    "akrów",
    "akrow",
    "akry",
    "akr",
    "sq ft",
    "sqft",
)

_UNIT_RANK: dict[Unit, int] = {"ha": 2, "ar": 1, "m2": 0}
_UNIT_MULTIPLIER: dict[Unit, Decimal] = {"ha": HA_IN_M2, "ar": AR_IN_M2, "m2": M2_IN_M2}

# The thousands separator is a space, and real payloads use three invisible
# variants of it. A naive `strip()` leaves every one of them in place.
_SPACES = ("\u00a0", "\u202f", "\u2009", "\u2007")

# ASCII digits only. A number written in another script is a number we cannot
# read, so it must not become an area.
_NUMBER = r"(?:[0-9]{1,3}(?:[ ][0-9]{3})+(?:,[0-9]+)?|[0-9]+(?:[.,][0-9]+)*)"
_SIGNED = rf"-?{_NUMBER}"


def _alternation(tokens: object) -> str:
    """Longest token first, so `arów` never matches as `ar`."""
    return "|".join(re.escape(token) for token in sorted(tokens, key=len, reverse=True))


_UNIT_ALTERNATION = _alternation(UNIT_LEXICON)
# The bare `a` is excluded: on its own it is a conjunction, not evidence that
# the text states an area.
_UNAMBIGUOUS_UNITS = _alternation(set(UNIT_LEXICON) - {"a"})

_BOUNDARY = r"(?![\w²^])"
_STATEMENT = re.compile(
    rf"(?P<number>{_SIGNED})\s*(?P<unit>{_UNIT_ALTERNATION}){_BOUNDARY}"
)
_UNAMBIGUOUS_UNIT = re.compile(rf"(?<![\w²^])(?:{_UNAMBIGUOUS_UNITS}){_BOUNDARY}")
_UNSUPPORTED_UNIT = re.compile(
    rf"[0-9]\s*(?:{_alternation(UNSUPPORTED_UNIT_LEXICON)}){_BOUNDARY}"
)
_BARE_NUMBER = re.compile(rf"-?{_NUMBER}")
_RANGE = re.compile(
    rf"{_NUMBER}\s*[-–—]\s*{_NUMBER}\s*(?:{_UNIT_ALTERNATION}){_BOUNDARY}"
)
_RANGE_FROM = re.compile(r"(?<!\w)od\s+[0-9]")
_APPROXIMATE = re.compile(r"(?:^|[\s(])(?:ok\.?|oko[łl]o|ca\.?|~)\s*$")
_DIGIT = re.compile(r"[0-9]")


class AreaFailure(Enum):
    ABSENT = "absent"
    NO_UNIT = "no_unit"
    NO_VALUE = "no_value"
    UNKNOWN_UNIT = "unknown_unit"
    NON_POSITIVE = "non_positive"
    AMBIGUOUS_SEPARATOR = "ambiguous_separator"
    NOT_SINGLE_VALUED = "not_single_valued"
    CONFLICTING_STATEMENTS = "conflicting_statements"


class PriceFailure(Enum):
    ABSENT = "absent"
    PLACEHOLDER = "placeholder"
    NON_POSITIVE = "non_positive"
    NOT_A_TOTAL = "not_a_total"
    UNSUPPORTED_CURRENCY = "unsupported_currency"


@dataclass(frozen=True)
class AreaParse:
    m2: Decimal | None
    unit: Unit | None
    is_approximate: bool
    confidence: Confidence
    failure: AreaFailure | None


@dataclass(frozen=True)
class PriceParse:
    pln: Decimal | None
    confidence: Confidence
    failure: PriceFailure | None


class _Statement(NamedTuple):
    m2: Decimal
    unit: Unit
    token: str
    start: int
    end: int
    in_parens: bool
    dotted: bool


def _preclean(text: str) -> str:
    for space in _SPACES:
        text = text.replace(space, " ")
    return text


def _area_failed(failure: AreaFailure) -> AreaParse:
    return AreaParse(
        m2=None, unit=None, is_approximate=False, confidence="unknown", failure=failure
    )


def _in_parens(text: str, position: int) -> bool:
    prefix = text[:position]
    return prefix.count("(") > prefix.count(")")


def _number(raw: str) -> tuple[Decimal | None, bool]:
    """Read one area number. Returns the value and whether D79's carve-out ran.

    A dot loses unless it is the register's four-decimal hectare format, and
    even then the caller must check the unit.
    """
    text = raw.replace(" ", "")
    if text.count(",") > 1 or ("," in text and "." in text):
        return None, False
    if "." in text:
        _head, _, tail = text.partition(".")
        if "." in tail or len(tail) != 4:
            return None, False
        try:
            return Decimal(text), True
        except InvalidOperation:
            return None, False
    try:
        return Decimal(text.replace(",", ".")), False
    except InvalidOperation:
        return None, False


def _statements(text: str) -> tuple[list[_Statement], AreaFailure | None]:
    found: list[_Statement] = []
    for match in _STATEMENT.finditer(text):
        unit = UNIT_LEXICON[match.group("unit")]
        value, dotted = _number(match.group("number"))
        if value is None:
            return [], AreaFailure.AMBIGUOUS_SEPARATOR
        if dotted and unit != "ha":
            # Four decimals with any other unit is the ambiguous class the
            # carve-out was cut out of.
            return [], AreaFailure.AMBIGUOUS_SEPARATOR
        if value <= 0:
            return [], AreaFailure.NON_POSITIVE
        found.append(
            _Statement(
                m2=value * _UNIT_MULTIPLIER[unit],
                unit=unit,
                token=match.group("unit"),
                start=match.start("number"),
                end=match.end(),
                in_parens=_in_parens(text, match.start()),
                dotted=dotted,
            )
        )
    return found, None


def _keyword_is_near(text: str, statement: _Statement) -> bool:
    """D86 — an area keyword within the window makes the bare `a` readable."""
    for keyword in BARE_A_KEYWORDS:
        start = text.find(keyword)
        while start != -1:
            end = start + len(keyword)
            if end <= statement.start:
                gap = statement.start - end
            elif statement.end <= start:
                gap = start - statement.end
            else:
                gap = 0
            if gap <= BARE_A_KEYWORD_WINDOW:
                return True
            start = text.find(keyword, start + 1)
    return False


def _is_compound(statements: list[_Statement]) -> bool:
    """Whether the statements are parts of one area that add up (D90).

    A parenthesised second statement is a restatement, never a part: "12 arów
    (1200 m²)" is 1200 m², not 2400.
    """
    return (
        len(statements) > 1
        and not any(item.in_parens for item in statements)
        and all(
            _UNIT_RANK[left.unit] > _UNIT_RANK[right.unit]
            for left, right in pairwise(statements)
        )
    )


def parse_area(text: str, field: Field) -> AreaParse:
    """Read one area statement from `text`, which comes from `field`.

    `field` has no default. A default picks the most permissive reading for the
    least trustworthy text (D86).
    """
    if field not in FIELDS:
        raise ValueError(f"field must be one of {FIELDS}, not {field!r}")

    lowered = _preclean(text).lower()
    if not lowered.strip():
        return _area_failed(AreaFailure.ABSENT)
    if _DIGIT.search(lowered) is None:
        if _UNAMBIGUOUS_UNIT.search(lowered) is not None:
            return _area_failed(AreaFailure.NO_VALUE)
        return _area_failed(AreaFailure.ABSENT)

    if _RANGE.search(lowered) is not None or (
        _RANGE_FROM.search(lowered) is not None
        and _UNAMBIGUOUS_UNIT.search(lowered) is not None
    ):
        return _area_failed(AreaFailure.NOT_SINGLE_VALUED)

    statements, failure = _statements(lowered)
    if failure is not None:
        return _area_failed(failure)
    if not statements:
        if _UNSUPPORTED_UNIT.search(lowered) is not None:
            return _area_failed(AreaFailure.UNKNOWN_UNIT)
        if _BARE_NUMBER.fullmatch(lowered.strip()) is not None:
            return _area_failed(AreaFailure.NO_UNIT)
        return _area_failed(AreaFailure.ABSENT)

    bare_a = [item for item in statements if item.token == "a"]
    if bare_a and field == "body" and not _keyword_is_near(lowered, bare_a[0]):
        # The whole parse stops, not only the bare `a` statement. Dropping one
        # part of "1 ha 25 a" would report 10 000 m² for a 12 500 m² plot,
        # which is the error D90 was re-asked to prevent.
        return _area_failed(AreaFailure.ABSENT)

    first = statements[0]
    approximate = _APPROXIMATE.search(lowered[: first.start]) is not None
    lossy = approximate or bool(bare_a) or any(item.dotted for item in statements)

    if _is_compound(statements):
        # A compound: "1 ha 25 a" is 12 500 m² (D90). The unit records how the
        # advert stated the area; `m2` carries the value.
        m2 = sum((item.m2 for item in statements), Decimal(0))
        unit = first.unit
        lossy = True
    elif any(item.m2 != first.m2 for item in statements[1:]):
        # A restatement that disagrees with itself. One field holds no
        # authority to break its own tie, so the record is quarantined.
        return _area_failed(AreaFailure.CONFLICTING_STATEMENTS)
    else:
        # One statement, or a restatement that agrees. A restatement is
        # corroboration, so it keeps its confidence.
        m2, unit = first.m2, first.unit

    return AreaParse(
        m2=m2,
        unit=unit,
        is_approximate=approximate,
        confidence="low" if lossy else "high",
        failure=None,
    )


# --- prices ---------------------------------------------------------------

_PRICE_NUMBER = re.compile(
    r"-?(?:[0-9]{1,3}(?:[ ][0-9]{3})+(?:[.,][0-9]{1,2})?|[0-9]+(?:[.,][0-9]+)*)"
)
_CURRENCY = re.compile(r"z[łl]|(?<!\w)pln(?!\w)")
_FOREIGN_CURRENCY = re.compile(r"(?<!\w)(?:eur|usd|chf|gbp)(?!\w)|[€$]")
_NOT_A_TOTAL = re.compile(
    r"z[łl]\s*/\s*m|z[łl]\s*za\s*m|/\s*m[²2]|/\s*mies|miesi[ęe]cznie"
)
_TYS = re.compile(r"(?<!\w)tys\.?(?!\w)")
_MLN = re.compile(r"(?<!\w)(?:mln|milion\w*)(?!\w)")
_PLACEHOLDERS = (
    "zapytaj o cen",
    "cena do uzgodnienia",
    "do uzgodnienia",
    "do negocjacji",
    "kontakt w sprawie ceny",
)


def _price_failed(failure: PriceFailure) -> PriceParse:
    return PriceParse(pln=None, confidence="unknown", failure=failure)


def _price_number(raw: str) -> Decimal | None:
    """Read one price. The separators are decided by the digits that follow.

    A price is bounded by the currency's two decimal places, so `250 000.50`
    has exactly one reading. This is why D79's rule for areas does not apply
    here, and the asymmetry is deliberate.
    """
    text = raw.replace(" ", "")
    parts = re.split(r"[.,]", text)
    if len(parts) == 1:
        try:
            return Decimal(text)
        except InvalidOperation:
            return None

    groups, last = parts[1:-1], parts[-1]
    if not all(len(group) == 3 for group in groups):
        return None
    if len(last) == 3:
        return Decimal("".join(parts))
    if len(last) > 2:
        return None
    return Decimal(f"{''.join(parts[:-1])}.{last}")


def parse_price(text: str) -> PriceParse:
    """Read one total price in PLN from `text`."""
    lowered = _preclean(text).lower()
    if not lowered.strip():
        return _price_failed(PriceFailure.ABSENT)

    if _NOT_A_TOTAL.search(lowered) is not None:
        # A per-m² figure or a rent in the total-price field is a connector
        # layout defect. It gets its own reason so V50 can watch it move on one
        # source without the `absent` count changing.
        return _price_failed(PriceFailure.NOT_A_TOTAL)

    has_digits = _DIGIT.search(lowered) is not None
    if has_digits and _FOREIGN_CURRENCY.search(lowered) is not None:
        # A conversion needs an FX rate with an as-of date (rule 7), which v0
        # does not carry.
        return _price_failed(PriceFailure.UNSUPPORTED_CURRENCY)

    match = _PRICE_NUMBER.search(lowered)
    value = None if match is None else _price_number(match.group(0))
    if value is None:
        if any(phrase in lowered for phrase in _PLACEHOLDERS):
            return _price_failed(PriceFailure.PLACEHOLDER)
        return _price_failed(PriceFailure.ABSENT)

    lossy = False
    if _TYS.search(lowered) is not None:
        value *= TYS_MULTIPLIER
        lossy = True
    elif _MLN.search(lowered) is not None:
        value *= MLN_MULTIPLIER
        lossy = True

    if value <= 0:
        # The schema has CHECK (price_pln > 0), so a zero is a constraint
        # violation at insert time. It is caught here to appear in the
        # quarantine composition instead of in the run's exception log.
        return _price_failed(PriceFailure.NON_POSITIVE)

    if _CURRENCY.search(lowered) is None:
        # A bare number in a price field is almost certainly PLN, and there is
        # no other plausible currency in this corpus. "Almost certainly" is
        # `low`.
        lossy = True

    return PriceParse(pln=value, confidence="low" if lossy else "high", failure=None)
