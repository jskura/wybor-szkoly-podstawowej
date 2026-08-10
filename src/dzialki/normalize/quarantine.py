"""Why a record cannot become a listing, in a closed vocabulary.

Quarantined and flagged are different states, and conflating them is the
failure this module exists to prevent. A quarantined record has no usable price
or area at all, so it can produce no zł/m² figure. A flagged record has both
and falls outside the validity band; it stays visible (`bands.py`).

Quarantining out-of-band records would amputate farmland from the corpus while
the total quarantine rate still looked healthy. That is F12 by another route.

The vocabulary is closed and the strings are frozen because V50 groups on them
in SQL and compares each reason against its own rolling baseline. Free text
makes a per-reason rate uncomputable, and a catch-all member hides the reason
that is moving.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .units import AreaFailure, PriceFailure

_REQUIRED_LISTING_REF = ("source", "external_id", "url", "raw_document_hash")


class QuarantineReason(str, Enum):
    """Thirteen members, none conditional.

    There is no `price_ambiguous_magnitude`: D80 parses `250 tys.` and
    `1,2 mln`, so no input produces it. There is no `out_of_band`, no `other`
    and no `suspicious`.
    """

    PRICE_MISSING = "price_missing"
    PRICE_PLACEHOLDER = "price_placeholder"
    PRICE_NON_POSITIVE = "price_non_positive"
    PRICE_NOT_A_TOTAL = "price_not_a_total"
    PRICE_UNSUPPORTED_CURRENCY = "price_unsupported_currency"
    AREA_MISSING = "area_missing"
    AREA_NO_UNIT = "area_no_unit"
    AREA_NO_VALUE = "area_no_value"
    AREA_UNIT_UNKNOWN = "area_unit_unknown"
    AREA_NON_POSITIVE = "area_non_positive"
    AREA_AMBIGUOUS_SEPARATOR = "area_ambiguous_separator"
    AREA_NOT_SINGLE_VALUED = "area_not_single_valued"
    AREA_CONFLICTING_STATEMENTS = "area_conflicting_statements"


# Total and injective: every parse failure has one reason, and no two share one.
_REASONS: dict[PriceFailure | AreaFailure, QuarantineReason] = {
    PriceFailure.ABSENT: QuarantineReason.PRICE_MISSING,
    PriceFailure.PLACEHOLDER: QuarantineReason.PRICE_PLACEHOLDER,
    PriceFailure.NON_POSITIVE: QuarantineReason.PRICE_NON_POSITIVE,
    PriceFailure.NOT_A_TOTAL: QuarantineReason.PRICE_NOT_A_TOTAL,
    PriceFailure.UNSUPPORTED_CURRENCY: QuarantineReason.PRICE_UNSUPPORTED_CURRENCY,
    AreaFailure.ABSENT: QuarantineReason.AREA_MISSING,
    AreaFailure.NO_UNIT: QuarantineReason.AREA_NO_UNIT,
    AreaFailure.NO_VALUE: QuarantineReason.AREA_NO_VALUE,
    AreaFailure.UNKNOWN_UNIT: QuarantineReason.AREA_UNIT_UNKNOWN,
    AreaFailure.NON_POSITIVE: QuarantineReason.AREA_NON_POSITIVE,
    AreaFailure.AMBIGUOUS_SEPARATOR: QuarantineReason.AREA_AMBIGUOUS_SEPARATOR,
    AreaFailure.NOT_SINGLE_VALUED: QuarantineReason.AREA_NOT_SINGLE_VALUED,
    AreaFailure.CONFLICTING_STATEMENTS: QuarantineReason.AREA_CONFLICTING_STATEMENTS,
}


def reason_for(failure: object) -> QuarantineReason:
    """The reason for one parse failure.

    An unmapped failure raises. A default would turn a new failure class into a
    silent misclassification, and V50 would watch the wrong rate.
    """
    try:
        return _REASONS[failure]  # type: ignore[index]
    except (KeyError, TypeError):
        raise ValueError(f"{failure!r} has no quarantine reason") from None


@dataclass(frozen=True)
class QuarantinedRecord:
    """One record that cannot become a listing, and the way back to its payload.

    `reason` is a constructor argument, never a field set afterwards. A record
    that reaches the writer without one would be a row V50 cannot count, and the
    column is NOT NULL, so the run would crash instead.
    """

    reason: QuarantineReason
    listing_ref: dict[str, str]

    def __post_init__(self) -> None:
        if not isinstance(self.reason, QuarantineReason):
            # ValueError, not TypeError: the caller handles one exception for
            # every way a record can fail to carry its reason.
            raise ValueError(  # noqa: TRY004
                f"reason must be a QuarantineReason, not {self.reason!r}"
            )
        missing = [key for key in _REQUIRED_LISTING_REF if key not in self.listing_ref]
        if missing:
            # FR-72 — a fixed parser re-derives the record from `raw_document`.
            # A quarantined record with no route back is a lost record.
            raise ValueError(f"listing_ref is missing {missing}")
