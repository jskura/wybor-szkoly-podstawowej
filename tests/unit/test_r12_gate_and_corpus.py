"""S12 in part — the gate and the corpus check, both testable with no portal.

Neither needs a recorded page. The gate decides from a policy object and an
evidence file; the corpus check is arithmetic on two counts. What waits on the
robots reading is extraction — which element on which page holds which field —
and none of that is here.
"""

from __future__ import annotations

import pathlib

import pytest

from dzialki.ingest import RobotsEvidenceMissing, robots
from dzialki.ingest.corpus import allowance_for, check, parse_stated_total
from dzialki.ingest.gate import LIST_ONLY, REFUSED, load_evidence, mode_for

pytestmark = [pytest.mark.unit]

AGENT = "dzialki"


# --- the gate --------------------------------------------------------------


def test_a_source_with_no_recorded_evidence_is_refused(tmp_path: pathlib.Path) -> None:
    """A missing file is not permission (D92), and the error is a task."""
    with pytest.raises(RobotsEvidenceMissing) as caught:
        load_evidence(tmp_path, "example.invalid")
    message = str(caught.value)
    assert "example.invalid" in message
    assert "robots.txt" in message


def test_evidence_without_a_date_is_refused(tmp_path: pathlib.Path) -> None:
    """Undated evidence cannot say whether it describes the file as it is now."""
    (tmp_path / "example.invalid.txt").write_text(
        "User-agent: *\nDisallow:\n", encoding="utf-8"
    )
    with pytest.raises(RobotsEvidenceMissing) as caught:
        load_evidence(tmp_path, "example.invalid")
    assert "read_at" in str(caught.value)


def test_dated_evidence_is_read_back_with_its_text(tmp_path: pathlib.Path) -> None:
    (tmp_path / "example.invalid.txt").write_text(
        "# read_at: 2026-08-10\nUser-agent: *\nDisallow: /oferta/\n", encoding="utf-8"
    )
    evidence = load_evidence(tmp_path, "example.invalid")
    assert evidence.read_at == "2026-08-10"
    assert "Disallow: /oferta/" in evidence.verbatim


def test_a_disallowed_list_path_refuses_the_whole_source() -> None:
    policy = robots.parse("User-agent: *\nDisallow: /\n", user_agent=AGENT)
    assert mode_for(policy, list_path="/szukaj", detail_path="/oferta/1") is REFUSED


def test_a_permitted_list_with_a_disallowed_detail_is_list_only() -> None:
    """Partial permission is a smaller product, not a refusal.

    Counts and locations without per-listing attributes. Recording the mode
    stops us emitting records whose fields were never fetched.
    """
    policy = robots.parse(
        "User-agent: *\nAllow: /szukaj\nDisallow: /oferta/\n", user_agent=AGENT
    )
    mode = mode_for(policy, list_path="/szukaj", detail_path="/oferta/1")
    assert mode is LIST_ONLY
    assert mode.detail_permitted is False


def test_a_missing_robots_file_refuses_even_the_list_path() -> None:
    assert (
        mode_for(robots.missing(), list_path="/szukaj", detail_path="/o/1") is REFUSED
    )


# --- the corpus check ------------------------------------------------------


@pytest.mark.parametrize(
    "text,value,approximate",
    [
        ("Znaleziono 1 234 ogłoszenia", 1234, False),
        ("Znaleziono około 1 200 ogłoszeń", 1200, True),
        ("ponad 500 ofert", 500, True),
        ("~ 90 wyników", 90, True),
    ],
)
def test_a_stated_total_carries_whether_the_page_hedged_it(
    text, value, approximate
) -> None:
    stated = parse_stated_total(text)
    assert stated.value == value
    assert stated.approximate is approximate


@pytest.mark.parametrize(
    "stated,expected",
    [
        (20, 3),  # 2% of 20 is 0.4 — under one listing, so the floor wins
        (150, 3),  # 2% of 150 is 3 — the two arms are equal here
        (151, 4),  # 2% of 151 rounds up to 4 — the percentage takes over
        (1000, 20),
    ],
)
def test_the_allowance_is_the_larger_of_the_two_arms(stated, expected) -> None:
    """D95. The crossing point is asserted from both sides.

    A percentage alone would set an allowance below one listing on a small
    query, and an allowance under one listing can never be met.
    """
    assert allowance_for(stated, abs_listings=3, pct=2) == expected


def test_a_corpus_inside_the_allowance_agrees() -> None:
    result = check(collected=147, stated_text="150 ofert", abs_listings=3, pct=2)
    assert result.agrees is True
    assert result.blocking is False


def test_a_corpus_outside_the_allowance_blocks() -> None:
    """Half a market collected silently is medians that look healthy."""
    result = check(collected=600, stated_text="1 200 ofert", abs_listings=3, pct=2)
    assert result.agrees is False
    assert result.blocking is True
    assert result.reason == "corpus disagrees with the stated total"


def test_an_approximate_total_reports_but_never_blocks() -> None:
    """D96. A source saying "about 1 200" has not promised 1 200, and an alarm
    that cries wolf trains the reader to ignore it."""
    result = check(
        collected=600, stated_text="około 1 200 ofert", abs_listings=3, pct=2
    )
    assert result.agrees is False
    assert result.blocking is False
    assert result.reason == "stated total is approximate — reported only"


def test_an_exact_total_still_blocks_so_the_hedge_rule_is_not_a_blanket_pass() -> None:
    """Non-vacuity companion for the rule above.

    Without it, an implementation that never blocks would pass every test in
    this section.
    """
    hedged = check(collected=1, stated_text="około 1 000", abs_listings=3, pct=2)
    exact = check(collected=1, stated_text="1 000", abs_listings=3, pct=2)
    assert hedged.blocking is False
    assert exact.blocking is True
