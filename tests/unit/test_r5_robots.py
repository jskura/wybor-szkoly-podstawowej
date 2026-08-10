"""Work item 5 §2.1 — robots.txt, tested with the network unreachable.

These fixtures are hand-written on purpose. We are testing our parser, not any
portal's file. The real files, when someone records them, live in
`docs/evidence/robots/` with their date and their verbatim text.

The two D92 rules are stated in separate tests. Reading one off the other is how
a deliberate asymmetry quietly becomes a symmetry.
"""

from __future__ import annotations

import pathlib

import pytest

from dzialki.ingest import robots

pytestmark = [pytest.mark.unit]

AGENT = "dzialki"


@pytest.fixture
def robots_dir(fixtures_dir: pathlib.Path) -> pathlib.Path:
    return fixtures_dir / "robots"


def _policy(robots_dir: pathlib.Path, name: str, agent: str = AGENT):
    text = (robots_dir / name).read_text(encoding="utf-8")
    return robots.parse(text, user_agent=agent)


def test_a_disallowed_path_is_refused(robots_dir) -> None:
    policy = _policy(robots_dir, "disallow-oferta.txt")
    assert policy.allows("/oferta/123") is False
    assert policy.allows("/szukaj?q=dzialka") is True


def test_an_agent_specific_group_beats_the_wildcard(robots_dir) -> None:
    assert _policy(robots_dir, "agent-specific.txt").allows("/szukaj") is True
    assert (
        _policy(robots_dir, "agent-specific.txt", agent="other").allows("/szukaj")
        is False
    )


def test_a_missing_file_is_not_permission() -> None:
    """D92 part 1, our own rule, stricter than the RFC.

    A 404 means we do not know. Not knowing is not consent.
    """
    policy = robots.missing()
    assert policy.state == "unknown"
    assert policy.allows("/szukaj") is False
    assert policy.allows("/oferta/1") is False


def test_a_served_file_with_no_matching_group_allows(robots_dir) -> None:
    """D92 part 2, RFC 9309. Stated on its own, never read off the rule above.

    The warning matters: it lets a caller tell "allowed because the file says so"
    from "allowed because nothing in the file applied to us".
    """
    for name in ("no-group.txt", "other-agent-only.txt"):
        policy = _policy(robots_dir, name)
        assert policy.state == "allow_all", name
        assert policy.allows("/szukaj?q=x") is True, name
        assert policy.allows("/oferta/1") is True, name
        assert policy.warnings == ["no_matching_group"], name


def test_the_two_rules_are_not_derived_from_each_other() -> None:
    """The non-vacuity companion for the pair above.

    If one rule were implemented in terms of the other, these two states would
    coincide and both tests above would still pass.
    """
    assert robots.missing().state != robots.parse("", user_agent=AGENT).state


def test_a_failing_robots_endpoint_is_not_an_open_door() -> None:
    policy = robots.unavailable()
    assert policy.allows("/szukaj") is False
    assert "robots_unavailable" in policy.warnings


def test_an_empty_disallow_forbids_nothing(robots_dir) -> None:
    """RFC 9309: `Disallow:` with no value is the explicit opposite of `/`."""
    policy = robots.parse("User-agent: *\nDisallow:\n", user_agent=AGENT)
    assert policy.allows("/anything") is True


def test_the_longest_matching_rule_wins(robots_dir) -> None:
    policy = robots.parse(
        "User-agent: *\nDisallow: /oferta/\nAllow: /oferta/publiczne/\n",
        user_agent=AGENT,
    )
    assert policy.allows("/oferta/123") is False
    assert policy.allows("/oferta/publiczne/1") is True
