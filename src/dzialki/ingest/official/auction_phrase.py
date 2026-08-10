"""The *cena wywoławcza* clause, parsed.

The wording is fixed by the Code of Civil Procedure, not by any website. That is
why this parser can be written and tested before anyone records a single auction
page: the sentence is ours to reason about, while the document it sits in is not.
The same phrases serve both auction sources (D111), because the statute words the
clause identically in each.

**Nothing here is corrected.** When a stated price and a stated valuation
disagree with the stated fraction, both numbers are kept and the record is
flagged. Recomputing one from the other would replace a number a court published
with a number we preferred, and the disagreement is itself the finding.

**Nothing here is defaulted.** A notice stating a price and a valuation but no
fraction does not become three quarters, even though three quarters is the
commonest first-auction fraction. An assumed fraction is indistinguishable from a
read one once it is stored.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal
from fractions import Fraction

# The statute's own fractions. A percentage outside this map is recorded as
# unrecognised rather than converted, because an unexpected percentage means the
# clause is not the one we think we are reading.
PERCENT_TO_FRACTION: dict[Decimal, Fraction] = {
    Decimal(75): Fraction(3, 4),
    Decimal("66.67"): Fraction(2, 3),
    Decimal("66.66"): Fraction(2, 3),
}

WORDED_FRACTION: dict[str, Fraction] = {
    "trzy czwarte": Fraction(3, 4),
    "dwie trzecie": Fraction(2, 3),
}

# Which auction round each fraction implies. First auctions open at three
# quarters, second at two thirds.
ROUND_FOR_FRACTION: dict[Fraction, int] = {
    Fraction(3, 4): 1,
    Fraction(2, 3): 2,
}

SECOND_AUCTION_WORDS = ("druga licytacja", "drugiej licytacji")

# Any space Polish typography uses as a thousands separator, plus the dot form.
_SPACES = "   "
_AMOUNT = re.compile(
    r"(?P<value>\d[\d" + _SPACES + r"\.]*(?:,\d{1,2})?)\s*(?:zł|złotych|PLN)"
)

# A fraction must sit next to the words that make it one. `123/4` in "działka
# nr 123/4" is a parcel number, and reading it as a fraction would turn a plot
# identifier into a price rule.
_FRACTION = re.compile(
    r"(?P<num>\d{1,2})\s*/\s*(?P<den>\d{1,2})\s+(?:sumy|części)", re.IGNORECASE
)
_PERCENT = re.compile(r"(?P<value>\d{1,3}(?:,\d{1,2})?)\s*%\s*sumy", re.IGNORECASE)

_PRICE_CLAUSE = re.compile(r"cena\s+wywoławcza", re.IGNORECASE)
_VALUATION_CLAUSE = re.compile(r"suma\s+oszacowania", re.IGNORECASE)


class PriceMissing(ValueError):
    """The notice states no opening price. Quarantined, never assumed."""


@dataclass(frozen=True)
class AuctionClause:
    price_pln: Decimal
    valuation_pln: Decimal | None
    statutory_fraction: Fraction | None
    auction_round: int | None
    # None means "we cannot tell", which is not the same as False. Only a stated
    # price and a stated valuation together can disagree.
    fraction_consistent: bool | None
    flags: tuple[str, ...] = field(default=())


def parse_amount(text: str) -> Decimal:
    """Read the first złoty amount in ``text``."""
    found = _AMOUNT.search(text)
    if not found:
        raise PriceMissing("no amount in the phrase")
    raw = found.group("value")
    for space in _SPACES:
        raw = raw.replace(space, "")
    raw = raw.replace(".", "").replace(",", ".")
    return Decimal(raw).quantize(Decimal("0.01"))


def _amount_after(text: str, clause: re.Pattern[str]) -> Decimal | None:
    found = clause.search(text)
    if not found:
        return None
    try:
        return parse_amount(text[found.end() :])
    except PriceMissing:
        return None


def _fraction(text: str) -> tuple[Fraction | None, list[str]]:
    flags: list[str] = []

    found = _FRACTION.search(text)
    if found:
        return Fraction(int(found.group("num")), int(found.group("den"))), flags

    lowered = text.lower()
    for words, value in WORDED_FRACTION.items():
        if words in lowered:
            return value, flags

    found = _PERCENT.search(text)
    if found:
        percent = Decimal(found.group("value").replace(",", "."))
        if percent in PERCENT_TO_FRACTION:
            return PERCENT_TO_FRACTION[percent], flags
        flags.append("fraction_unrecognised")
    return None, flags


def parse_clause(text: str, *, tolerance_pln: Decimal) -> AuctionClause:
    """Read one *cena wywoławcza* clause.

    ``tolerance_pln`` comes from configuration (D94). Notices round to the whole
    złoty, so an exact comparison would flag every correctly rounded notice.
    """
    price = _amount_after(text, _PRICE_CLAUSE)
    if price is None:
        raise PriceMissing("the notice states no opening price")

    valuation = _amount_after(text, _VALUATION_CLAUSE)
    fraction, flags = _fraction(text)

    stated_round: int | None = None
    if any(words in text.lower() for words in SECOND_AUCTION_WORDS):
        stated_round = 2

    implied_round = ROUND_FOR_FRACTION.get(fraction) if fraction else None
    auction_round = implied_round
    if stated_round is not None and implied_round is not None:
        if stated_round != implied_round:
            # The notice says one thing and its own arithmetic says another. We
            # report the disagreement and claim neither round.
            flags.append("round_fraction_conflict")
            auction_round = None
    elif stated_round is not None:
        auction_round = stated_round
    elif implied_round is None and fraction is None and stated_round is None:
        auction_round = None

    consistent: bool | None = None
    if fraction is not None and valuation is not None:
        expected = (Decimal(fraction.numerator) * valuation) / Decimal(
            fraction.denominator
        )
        consistent = abs(expected - price) <= tolerance_pln
        if not consistent:
            flags.append("fraction_mismatch")

    return AuctionClause(
        price_pln=price,
        valuation_pln=valuation,
        statutory_fraction=fraction,
        auction_round=auction_round,
        fraction_consistent=consistent,
        flags=tuple(flags),
    )
