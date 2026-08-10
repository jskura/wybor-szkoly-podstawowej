"""Per-host rate limiting and backoff.

Per host, not global. A global limiter would slow every source because one is
slow, and would let one host be hit at the combined rate of all of them.

The clock is injected. A test that waits in real time cannot assert a 500-request
politeness budget, so it would assert something weaker instead.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

SECONDS_PER_MINUTE = 60


class Clock:
    """The real clock. Tests pass a fake one."""

    def monotonic(self) -> float:
        return time.monotonic()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


@dataclass
class RateLimiter:
    """Holds a minimum interval between requests to each host.

    ``crawl_delay_s`` from robots.txt applies when it is **stricter** than our
    configured limit. When ours is stricter, ours wins: the host's file states a
    ceiling on politeness, not a floor.
    """

    clock: Clock
    _next_slot: dict[str, float] = field(default_factory=dict)

    @staticmethod
    def interval_s(*, rate_limit_rpm: int, crawl_delay_s: float | None) -> float:
        ours = SECONDS_PER_MINUTE / rate_limit_rpm
        if crawl_delay_s is None:
            return ours
        return max(ours, crawl_delay_s)

    def wait(self, host: str, *, interval_s: float) -> None:
        now = self.clock.monotonic()
        earliest = self._next_slot.get(host, now)
        if earliest > now:
            self.clock.sleep(earliest - now)
            now = self.clock.monotonic()
        self._next_slot[host] = now + interval_s

    def defer(self, host: str, seconds: float) -> None:
        """Push a host's next slot out by ``seconds``, never pulling it in.

        Called after a backoff. Using ``max`` means a backoff can only make the
        limiter more patient — a shorter backoff must not reset an interval the
        politeness budget already owes.
        """
        now = self.clock.monotonic()
        self._next_slot[host] = max(self._next_slot.get(host, now), now + seconds)


@dataclass(frozen=True)
class BackoffPlan:
    """What to do about a 429 or a 5xx."""

    sleeps: tuple[float, ...]
    give_up_reason: str | None = None


def backoff_seconds(attempt: int) -> float:
    """1, 2, 4, 8 … — doubling from the first retry."""
    return float(2**attempt)


def honour_retry_after(
    retry_after_s: float, *, max_s: int
) -> tuple[float | None, str | None]:
    """Decide whether a ``Retry-After`` fits inside the run's budget (D93).

    A crawl held open for a day cannot be told apart from a hang, and a partial
    day published as a full one is worse than yesterday's data left in place. So
    beyond the budget the run ends and publishes nothing.
    """
    if retry_after_s > max_s:
        return None, "retry_after_exceeds_budget"
    return retry_after_s, None
