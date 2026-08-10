"""S6 §3 — register beats advert, and the disagreement is kept, not discarded.

FR-15 is an authority rule, not a vote. Three advert sources agreeing against
the register do not outweigh it.

D81 sets the conflict threshold at more than 5%. D120 makes the register area
the denominator, so an advert 5% under and one 5% over are measured against the
same figure.
"""

from __future__ import annotations

import pathlib
from decimal import Decimal

import pytest

from dzialki.config import load_params
from dzialki.normalize.area_authority import (
    AUTHORITY_ORDER,
    ConflictRule,
    NoAreaStated,
    resolve_area,
)
from dzialki.normalize.units import AreaFailure, parse_area

pytestmark = [pytest.mark.unit]


@pytest.fixture(scope="module")
def rule(repo_root: pathlib.Path) -> ConflictRule:
    return ConflictRule.from_params(load_params(repo_root / "config" / "params.yml"))


def _d(value: str | None) -> Decimal | None:
    return None if value is None else Decimal(value)


# (test_id, register, structured, body, title, winner, source, conflict)
AUTHORITY_CASES = [
    ("register_beats_structured", "1450", "1200", None, None, "1450", "register", True),
    ("register_beats_body", "1450", None, "1200", None, "1450", "register", True),
    ("register_beats_title", "1450", None, None, "1200", "1450", "register", True),
    # 4.17% — inside the 5% threshold, so the winner changes and the flag does
    # not.
    (
        "structured_beats_body",
        None,
        "1200",
        "1150",
        None,
        "1200",
        "structured",
        False,
    ),
    (
        "structured_beats_body_conflicting",
        None,
        "1200",
        "1100",
        None,
        "1200",
        "structured",
        True,
    ),
    (
        "structured_beats_title",
        None,
        "1200",
        None,
        "1000",
        "1200",
        "structured",
        True,
    ),
    ("body_beats_title", None, None, "1150", "1000", "1150", "body", True),
    ("all_four_disagree", "1450", "1200", "1150", "1000", "1450", "register", True),
    ("all_four_agree", "1200", "1200", "1200", "1200", "1200", "register", False),
    ("register_only", "1450", None, None, None, "1450", "register", False),
    ("structured_only", None, "1200", None, None, "1200", "structured", False),
    ("body_only", None, None, "1150", None, "1150", "body", False),
    ("title_only", None, None, None, "1000", "1000", "title", False),
    (
        "lower_sources_agree_against_register",
        "1450",
        "1200",
        "1200",
        "1200",
        "1450",
        "register",
        True,
    ),
    # 0.009% — precision is not authority, and it is not a conflict either.
    (
        "precision_is_not_authority",
        "1450",
        "1449.87",
        None,
        None,
        "1450",
        "register",
        False,
    ),
    (
        "gap_between_present_sources",
        "1450",
        None,
        None,
        "1000",
        "1450",
        "register",
        True,
    ),
]


@pytest.mark.parametrize(
    "register,structured,body,title,winner,source,conflict",
    [case[1:] for case in AUTHORITY_CASES],
    ids=[case[0] for case in AUTHORITY_CASES],
)
def test_resolve_area_authority_order(
    rule: ConflictRule,
    register: str | None,
    structured: str | None,
    body: str | None,
    title: str | None,
    winner: str,
    source: str,
    conflict: bool,
) -> None:
    resolved = resolve_area(
        _d(register), _d(structured), _d(body), _d(title), rule=rule
    )
    assert resolved.m2 == Decimal(winner)
    assert resolved.source == source
    assert resolved.conflict is conflict


def test_authority_order_is_register_structured_body_title() -> None:
    """The order is the DDL's CHECK list, most authoritative first."""
    assert AUTHORITY_ORDER == ("register", "structured", "body", "title")


def test_no_area_anywhere_raises_the_area_missing_failure(rule: ConflictRule) -> None:
    with pytest.raises(NoAreaStated) as caught:
        resolve_area(None, None, None, None, rule=rule)
    assert caught.value.failure is AreaFailure.ABSENT


def test_resolution_never_averages(rule: ConflictRule) -> None:
    """The winner equals one of the inputs exactly. No derived value."""
    for case in AUTHORITY_CASES:
        register, structured, body, title = (_d(value) for value in case[1:5])
        resolved = resolve_area(register, structured, body, title, rule=rule)
        stated = [value for value in (register, structured, body, title) if value]
        assert resolved.m2 in stated, case[0]


def test_candidates_retains_every_stated_value(rule: ConflictRule) -> None:
    """Rule 7 — we record which source won and what the loser said."""
    resolved = resolve_area(Decimal(1450), Decimal(1200), None, None, rule=rule)
    assert resolved.candidates == {
        "register": Decimal(1450),
        "structured": Decimal(1200),
        "body": None,
        "title": None,
    }


def test_area_source_is_a_member_of_the_check_constraint(rule: ConflictRule) -> None:
    for case in AUTHORITY_CASES:
        register, structured, body, title = (_d(value) for value in case[1:5])
        resolved = resolve_area(register, structured, body, title, rule=rule)
        assert resolved.source in AUTHORITY_ORDER, case[0]


def test_unparseable_source_is_skipped_not_fatal(rule: ConflictRule) -> None:
    """A body that says "12 morgów" costs its own candidate, not the record."""
    body = parse_area("12 morgów", "body")
    resolved = resolve_area(None, Decimal(1200), body, None, rule=rule)
    assert resolved.m2 == Decimal(1200)
    assert resolved.source == "structured"
    assert resolved.candidates["body"] is None


def test_confidence_of_the_winner_is_carried(rule: ConflictRule) -> None:
    """A low-confidence value that wins keeps its confidence (D87)."""
    title = parse_area("ok. 1000 m²", "title")
    resolved = resolve_area(None, None, None, title, rule=rule)
    assert resolved.m2 == Decimal(1000)
    assert resolved.confidence == "low"


def test_a_title_value_is_low_confidence_even_when_stated_plainly(
    rule: ConflictRule,
) -> None:
    """The title is the least trustworthy field, so winning from it is a lossy
    route (§1 confidence taxonomy)."""
    title = parse_area("1000 m²", "title")
    assert title.confidence == "high"
    assert resolve_area(None, None, None, title, rule=rule).confidence == "low"


# --- D81 and D120, the threshold ------------------------------------------

# Every row states register 1200, so the denominator is fixed at 1200.
# (case_id, structured, conflict)
THRESHOLD_CASES = [
    ("well_inside", "1210.00", False),  # 0.83%
    ("just_inside", "1259.99", False),  # 4.9992%
    ("on_the_boundary", "1260.00", False),  # exactly 5%, inclusive
    ("just_outside", "1260.01", True),  # 5.0008%
    ("well_outside", "1450.00", True),  # 20.8%
    ("exactly_equal", "1200.00", False),  # 0%
    ("rounding_only", "1199.99", False),  # 0.0008%
    ("below_by_more_than_five", "1139.99", True),  # 5.0008% on the low side
]


@pytest.mark.parametrize(
    "structured,conflict",
    [case[1:] for case in THRESHOLD_CASES],
    ids=[case[0] for case in THRESHOLD_CASES],
)
def test_conflict_threshold_boundary(
    rule: ConflictRule, structured: str, conflict: bool
) -> None:
    resolved = resolve_area(Decimal(1200), Decimal(structured), None, None, rule=rule)
    assert resolved.conflict is conflict


def test_below_by_more_than_five_checks_the_low_side(rule: ConflictRule) -> None:
    """A rule written as `(advert - register) / register > 0.05` flags nothing
    when the advert understates the area."""
    resolved = resolve_area(Decimal(1200), Decimal("1139.99"), None, None, rule=rule)
    assert resolved.conflict is True


def test_conflict_threshold_is_five_percent_not_two(rule: ConflictRule) -> None:
    """The superseded value is named so a constant copied from an old draft
    fails at once."""
    assert rule.threshold == Decimal("0.05")
    assert rule.threshold != Decimal("0.02")
    two_percent = resolve_area(Decimal(1200), Decimal("1224.00"), None, None, rule=rule)
    assert two_percent.conflict is False


def test_the_threshold_comes_from_the_ratified_file(
    repo_root: pathlib.Path, rule: ConflictRule
) -> None:
    """V65 — the number lives in `config/params.yml` and nowhere else."""
    params = load_params(repo_root / "config" / "params.yml")
    assert params.validation.conflict_threshold_pct == 5
    assert rule.threshold * Decimal(100) == params.validation.conflict_threshold_pct
    assert rule.base == params.validation.conflict_threshold_base == "register"


def test_conflict_threshold_is_relative_not_absolute(rule: ConflictRule) -> None:
    """The same gap flags on a small plot and does not on a large one.

    An absolute threshold makes every hectare-scale plot conflict. The gap is
    100 m², not the 60 m² the plan's prose names: 60 m² on 1200 m² is exactly
    5%, which D81 leaves unflagged. The contradiction is reported, not settled
    here.
    """
    small = resolve_area(Decimal(1200), Decimal(1300), None, None, rule=rule)
    large = resolve_area(Decimal(200000), Decimal(200100), None, None, rule=rule)
    assert small.conflict is True
    assert large.conflict is False


def test_conflict_threshold_denominator_is_the_register_area(
    rule: ConflictRule,
) -> None:
    """D120. At the boundary the base changes the verdict.

    1260.01 is 5.0008% of the register's 1200 and 4.76% of itself. Dividing by
    the advert value would leave this record unflagged.
    """
    assert rule.base == "register"
    resolved = resolve_area(Decimal(1200), Decimal("1260.01"), None, None, rule=rule)
    assert resolved.conflict is True
    assert (Decimal("60.01") / Decimal("1260.01")) < rule.threshold


def test_conflict_threshold_is_symmetric(rule: ConflictRule) -> None:
    """The verdict does not depend on which value the implementation divides by.

    1200 against 1450 clears the threshold in both directions; 1200 against
    1230 stays inside it in both.
    """
    assert (
        resolve_area(Decimal(1200), Decimal(1450), None, None, rule=rule).conflict
        is True
    )
    assert (
        resolve_area(Decimal(1450), Decimal(1200), None, None, rule=rule).conflict
        is True
    )
    assert (
        resolve_area(Decimal(1200), Decimal(1230), None, None, rule=rule).conflict
        is False
    )
    assert (
        resolve_area(Decimal(1230), Decimal(1200), None, None, rule=rule).conflict
        is False
    )


def test_conflict_is_set_by_any_lower_source_not_only_the_next_one(
    rule: ConflictRule,
) -> None:
    """A title that disagrees flags, even when the body agrees with the winner."""
    resolved = resolve_area(
        Decimal(1200), Decimal(1200), Decimal(1200), Decimal(1000), rule=rule
    )
    assert resolved.conflict is True
