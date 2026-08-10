"""Work item 5 §2.2 — politeness, asserted rather than assumed.

Every assertion here is on the **minimum** interval, never the mean. A mean of
6.7 seconds is consistent with fifty requests in one second followed by a long
pause, which is exactly the behaviour a rate limit exists to prevent.
"""

from __future__ import annotations

import pytest
from tests.support import FakeClock, RecordingTransport

from dzialki.ingest.ratelimit import (
    RateLimiter,
    backoff_seconds,
    honour_retry_after,
)

pytestmark = [pytest.mark.unit]

RPM = 9
MINIMUM_S = 60 / RPM  # 6.666…


def test_the_minimum_interval_holds_over_500_requests() -> None:
    clock = FakeClock()
    transport = RecordingTransport(clock=clock)
    limiter = RateLimiter(clock=clock)

    for _ in range(500):
        limiter.wait("example.invalid", interval_s=MINIMUM_S)
        transport.get("example.invalid", "/szukaj")

    assert len(transport.calls) == 500
    gaps = [
        transport.calls[i + 1].at - transport.calls[i].at
        for i in range(len(transport.calls) - 1)
    ]
    assert min(gaps) >= MINIMUM_S - 1e-9


def test_the_limit_is_per_host_not_global() -> None:
    """A global limiter would slow every source because one is slow, and would
    let one host be hit at the combined rate of all of them."""
    clock = FakeClock()
    transport = RecordingTransport(clock=clock)
    limiter = RateLimiter(clock=clock)

    hosts = ["a.invalid", "b.invalid"]
    for index in range(100):
        host = hosts[index % 2]
        limiter.wait(host, interval_s=MINIMUM_S)
        transport.get(host, "/szukaj")

    for host in hosts:
        times = [call.at for call in transport.calls if call.host == host]
        gaps = [times[i + 1] - times[i] for i in range(len(times) - 1)]
        assert min(gaps) >= MINIMUM_S - 1e-9

    # Half the wall clock a global limiter would have needed, because the two
    # hosts wait in parallel rather than in turn.
    global_equivalent = MINIMUM_S * 99
    assert clock.now < global_equivalent * 0.6


@pytest.mark.parametrize(
    "crawl_delay,expected",
    [
        (20.0, 20.0),  # theirs is stricter
        (2.0, MINIMUM_S),  # ours is stricter, ours wins
        (None, MINIMUM_S),
    ],
)
def test_the_stricter_of_the_two_limits_applies(crawl_delay, expected) -> None:
    """A host's Crawl-delay states a ceiling on politeness, not a floor."""
    actual = RateLimiter.interval_s(rate_limit_rpm=RPM, crawl_delay_s=crawl_delay)
    assert actual == pytest.approx(expected, abs=1e-3)


def test_backoff_doubles() -> None:
    assert [backoff_seconds(n) for n in range(4)] == [1.0, 2.0, 4.0, 8.0]


def test_a_retry_after_inside_the_budget_is_honoured() -> None:
    seconds, reason = honour_retry_after(3600, max_s=3600)
    assert seconds == 3600
    assert reason is None


def test_a_retry_after_beyond_the_budget_ends_the_run() -> None:
    """D93. A crawl held open for a day cannot be told apart from a hang, and
    yesterday's rows are better than a partial day published as a full one."""
    seconds, reason = honour_retry_after(3601, max_s=3600)
    assert seconds is None
    assert reason == "retry_after_exceeds_budget"


def test_a_backoff_never_shortens_the_interval() -> None:
    """The politeness budget already owed must survive a shorter backoff."""
    clock = FakeClock()
    limiter = RateLimiter(clock=clock)

    limiter.wait("example.invalid", interval_s=120.0)
    limiter.defer("example.invalid", 1.0)  # a much shorter backoff

    limiter.wait("example.invalid", interval_s=MINIMUM_S)
    assert clock.sleeps == [pytest.approx(120.0)]
