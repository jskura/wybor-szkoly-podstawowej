"""robots.txt parsing, and the two rules that are deliberately asymmetric.

**A served file with no matching group is an allow** (D92, RFC 9309). The
standard says a file that parses to no applicable group permits access.

**A missing file is not permission** (D92, our own rule, stricter than the RFC).
A 404 means we do not know, and not knowing is not consent. The run stops unless
recorded evidence in `docs/evidence/robots/` says otherwise.

The two rules are stated separately here and tested separately, because reading
one off the other is how an asymmetry quietly becomes a symmetry.

Nothing in this module evades anything (D73). There is no user-agent rotation, no
proxy pool and no CAPTCHA handling. If we ever decide to fetch despite a
disallow, that is recorded openly with FR-2 amended, not hidden behind a header.
"""

from __future__ import annotations

import urllib.parse
from dataclasses import dataclass, field

ALLOW_ALL = "allow_all"
RULES = "rules"
UNKNOWN = "unknown"
UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class Rule:
    allow: bool
    path: str

    @property
    def specificity(self) -> int:
        # RFC 9309: the longest matching path wins, and Allow wins a tie.
        return len(self.path)


@dataclass
class RobotsPolicy:
    """What one host's robots.txt permits for one user agent."""

    state: str
    rules: list[Rule] = field(default_factory=list)
    crawl_delay_s: float | None = None
    warnings: list[str] = field(default_factory=list)

    def allows(self, path: str) -> bool:
        """Whether ``path`` may be fetched."""
        if self.state == UNKNOWN:
            # A missing file is not permission. The caller stops; this answer
            # exists so a caller that ignores `state` still fails closed.
            return False
        if self.state == UNAVAILABLE:
            # A robots endpoint returning 5xx must not read as an open door.
            return False
        if self.state == ALLOW_ALL:
            return True

        target = urllib.parse.urlsplit(path).path or "/"
        best: Rule | None = None
        for rule in self.rules:
            if not target.startswith(rule.path):
                continue
            if (
                best is None
                or rule.specificity > best.specificity
                or rule.specificity == best.specificity
                and rule.allow
            ):
                best = rule
        return True if best is None else best.allow


def parse(text: str, *, user_agent: str) -> RobotsPolicy:
    """Parse a served robots.txt for ``user_agent``.

    A specific group beats the wildcard group. If neither matches, the file
    permits everything and says so in a warning, so a caller can tell "allowed
    because the file said so" from "allowed because nothing applied".
    """
    groups: dict[str, list[tuple[str, str]]] = {}
    current: list[str] = []
    starting_group = False

    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        field_name, _, value = line.partition(":")
        field_name = field_name.strip().lower()
        value = value.strip()

        if field_name == "user-agent":
            if not starting_group:
                current = []
                starting_group = True
            current.append(value.lower())
            groups.setdefault(value.lower(), [])
        elif field_name in {"allow", "disallow", "crawl-delay"}:
            starting_group = False
            for agent in current:
                groups[agent].append((field_name, value))

    agent = user_agent.lower()
    chosen = groups.get(agent)
    warnings: list[str] = []
    if chosen is None:
        chosen = groups.get("*")
    if chosen is None:
        warnings.append("no_matching_group")
        return RobotsPolicy(state=ALLOW_ALL, warnings=warnings)

    rules: list[Rule] = []
    delay: float | None = None
    for field_name, value in chosen:
        if field_name == "crawl-delay":
            try:
                delay = float(value)
            except ValueError:
                warnings.append("crawl_delay_unparseable")
        elif field_name == "disallow":
            # An empty Disallow means "nothing is disallowed" (RFC 9309).
            if value:
                rules.append(Rule(allow=False, path=value))
        else:
            rules.append(Rule(allow=True, path=value))

    if not rules and delay is None:
        warnings.append("no_matching_group")
        return RobotsPolicy(state=ALLOW_ALL, warnings=warnings)

    return RobotsPolicy(
        state=RULES, rules=rules, crawl_delay_s=delay, warnings=warnings
    )


def missing() -> RobotsPolicy:
    """The policy for a 404. Not permission (D92 part 1)."""
    return RobotsPolicy(state=UNKNOWN, warnings=["robots_missing"])


def unavailable() -> RobotsPolicy:
    """The policy for a 5xx. A failing endpoint is not an open door."""
    return RobotsPolicy(state=UNAVAILABLE, warnings=["robots_unavailable"])
