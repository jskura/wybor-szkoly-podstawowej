"""S6 §6 — a quarantined record always says why, in a closed vocabulary.

Quarantined and flagged are different states. A quarantined record has no
usable price or area at all, so it cannot produce a zł/m² figure. A flagged
record has both and falls outside the validity band; it stays visible (§4).

Conflating the two is the failure this module exists to prevent. Quarantining
out-of-band records would amputate farmland from the corpus while the total
quarantine rate looked healthy.

V50 groups on `reason` in SQL, so the vocabulary is closed and the strings are
frozen. Free text makes a per-reason rate uncomputable.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from dzialki.normalize.bands import Bands, Flag, band_flags
from dzialki.normalize.quarantine import (
    QuarantinedRecord,
    QuarantineReason,
    reason_for,
)
from dzialki.normalize.units import AreaFailure, PriceFailure, parse_area, parse_price

pytestmark = [pytest.mark.unit]

# §6 of the test plan, verbatim. Renaming a string breaks V50's rolling
# baseline, so the list is frozen here and a rename must be a deliberate
# migration.
REASON_STRINGS = [
    "price_missing",
    "price_placeholder",
    "price_non_positive",
    "price_not_a_total",
    "price_unsupported_currency",
    "area_missing",
    "area_no_unit",
    "area_no_value",
    "area_unit_unknown",
    "area_non_positive",
    "area_ambiguous_separator",
    "area_not_single_valued",
    "area_conflicting_statements",
]

# The input that produces each reason, so no member is dead code.
# (reason, kind, text, field)
PRODUCING_INPUTS = [
    (QuarantineReason.PRICE_MISSING, "price", "", None),
    (QuarantineReason.PRICE_PLACEHOLDER, "price", "Zapytaj o cenę", None),
    (QuarantineReason.PRICE_NON_POSITIVE, "price", "0 zł", None),
    (QuarantineReason.PRICE_NOT_A_TOTAL, "price", "200 zł/m²", None),
    (QuarantineReason.PRICE_UNSUPPORTED_CURRENCY, "price", "60 000 EUR", None),
    (QuarantineReason.AREA_MISSING, "area", "brak danych", "structured"),
    (QuarantineReason.AREA_NO_UNIT, "area", "1200", "structured"),
    (QuarantineReason.AREA_NO_VALUE, "area", "m²", "structured"),
    (QuarantineReason.AREA_UNIT_UNKNOWN, "area", "12 morgów", "structured"),
    (QuarantineReason.AREA_NON_POSITIVE, "area", "0 m²", "structured"),
    (QuarantineReason.AREA_AMBIGUOUS_SEPARATOR, "area", "1.200 m²", "structured"),
    (QuarantineReason.AREA_NOT_SINGLE_VALUED, "area", "1200-1500 m²", "structured"),
    (
        QuarantineReason.AREA_CONFLICTING_STATEMENTS,
        "area",
        "1200 m² (15 arów)",
        "structured",
    ),
]

LISTING_REF = {
    "source": "otodom",
    "external_id": "OD-4471",
    "url": "https://example.invalid/oferta/OD-4471",
    "raw_document_hash": "sha256:0f1e2d3c",
}


def test_the_vocabulary_is_exactly_thirteen_members() -> None:
    """D80 parses the magnitude abbreviations, so there is no
    `PRICE_AMBIGUOUS_MAGNITUDE`. A member no input can produce is dead code."""
    assert len(QuarantineReason) == len(REASON_STRINGS)


def test_reason_strings_are_stable() -> None:
    assert [reason.value for reason in QuarantineReason] == REASON_STRINGS


def test_no_reason_string_contains_uppercase_or_spaces() -> None:
    """The strings are grouped on in SQL, exactly as written."""
    for reason in QuarantineReason:
        assert reason.value == reason.value.lower()
        assert " " not in reason.value


def test_the_vocabulary_holds_no_catch_all() -> None:
    """A free-text or catch-all reason makes V50's per-reason rates useless.

    There is no `out_of_band` either: an out-of-band record is flagged and kept.
    """
    for absent in ("other", "unknown", "suspicious", "implausible", "out_of_band"):
        assert absent not in {reason.value for reason in QuarantineReason}


@pytest.mark.parametrize(
    "reason,kind,text,field",
    PRODUCING_INPUTS,
    ids=[case[0].value for case in PRODUCING_INPUTS],
)
def test_every_reason_has_a_producing_input(
    reason: QuarantineReason, kind: str, text: str, field: str | None
) -> None:
    """Every member is reachable from a real input, not only from the enum."""
    if kind == "price":
        failure = parse_price(text).failure
    else:
        failure = parse_area(text, field).failure
    assert failure is not None
    assert reason_for(failure) is reason


def test_every_parse_failure_maps_to_exactly_one_reason() -> None:
    """The map is total and injective."""
    failures = list(AreaFailure) + list(PriceFailure)
    reasons = [reason_for(failure) for failure in failures]
    assert len(reasons) == len(set(reasons))
    assert set(reasons) == set(QuarantineReason)


def test_an_unmapped_failure_raises_rather_than_defaulting() -> None:
    """A default reason turns a new failure into a silent misclassification."""
    with pytest.raises(ValueError):
        reason_for("area_something_new")


def test_quarantining_without_a_reason_raises() -> None:
    """The reason is a constructor argument, never a field set afterwards."""
    with pytest.raises(ValueError):
        QuarantinedRecord(reason=None, listing_ref=LISTING_REF)


def test_a_free_text_reason_is_rejected() -> None:
    with pytest.raises(ValueError):
        QuarantinedRecord(reason="looked odd", listing_ref=LISTING_REF)


def test_every_quarantined_record_has_a_non_null_reason() -> None:
    for reason in QuarantineReason:
        record = QuarantinedRecord(reason=reason, listing_ref=LISTING_REF)
        assert record.reason is not None
        assert record.reason.value != ""
        assert record.reason in QuarantineReason


def test_quarantined_record_retains_its_listing_ref() -> None:
    """FR-72 — a fixed parser must be able to re-derive the record."""
    record = QuarantinedRecord(
        reason=QuarantineReason.AREA_NO_UNIT, listing_ref=LISTING_REF
    )
    assert record.listing_ref == LISTING_REF


@pytest.mark.parametrize(
    "missing", ["source", "external_id", "url", "raw_document_hash"]
)
def test_a_listing_ref_without_its_provenance_is_rejected(missing: str) -> None:
    """A quarantined record with no way back to the payload is a lost record."""
    incomplete = {key: value for key, value in LISTING_REF.items() if key != missing}
    with pytest.raises(ValueError):
        QuarantinedRecord(reason=QuarantineReason.AREA_NO_UNIT, listing_ref=incomplete)


def test_out_of_band_is_not_quarantined() -> None:
    """B9 from the other side. The 25 ha record parses, so nothing quarantines it.

    Asserted here as well as in the band tests, deliberately: the two states are
    decided in two places and both must agree.
    """
    area = parse_area("25 ha", "structured")
    price = parse_price("750 000 zł")
    assert area.failure is None
    assert price.failure is None

    bands = Bands(
        area=(Decimal(300), Decimal(200000)),
        price_per_m2=(Decimal(1), Decimal(100000)),
    )
    flags = band_flags(area.m2, price.pln / area.m2, bands=bands)
    assert flags == frozenset({Flag.AREA_ABOVE_BAND})


def test_a_flag_is_never_a_quarantine_reason() -> None:
    """The two vocabularies do not overlap, so no code can route one to the
    other."""
    flag_names = {flag.value for flag in Flag}
    reason_names = {reason.value for reason in QuarantineReason}
    assert flag_names & reason_names == set()
