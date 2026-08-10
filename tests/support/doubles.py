"""Test doubles for the ingest layer.

The harness is the point. Politeness over 500 requests cannot be asserted against
a real clock, so the clock is controlled and every sleep is recorded rather than
taken.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FakeClock:
    """A clock the test drives.

    ``sleep`` records the request and advances time. No test ever waits.
    """

    now: float = 0.0
    sleeps: list[float] = field(default_factory=list)

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


@dataclass(frozen=True)
class Call:
    at: float
    method: str
    host: str
    path: str


@dataclass
class RecordingTransport:
    """Returns queued responses and records every call.

    Recording the call *time* is what lets a test assert the minimum interval
    rather than the mean. A mean hides a burst; a minimum does not.
    """

    clock: FakeClock
    responses: list[tuple[int, str, dict]] = field(default_factory=list)
    calls: list[Call] = field(default_factory=list)

    def get(self, host: str, path: str) -> tuple[int, str, dict]:
        self.calls.append(
            Call(at=self.clock.monotonic(), method="GET", host=host, path=path)
        )
        if not self.responses:
            return 200, "", {}
        if len(self.responses) == 1:
            return self.responses[0]
        return self.responses.pop(0)
