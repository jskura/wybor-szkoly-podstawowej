"""The connector contract: fetch, parse, emit.

Three stages, and the middle one is **pure**. `parse` takes bytes and returns
records; it opens no socket and reads no clock. That is what makes every parser
testable against a recorded payload, and what makes a re-parse of stored raw
documents produce the same answer years later (V42).

The suite enforces the purity: a test runs `parse` with the socket module
patched to raise. A parser that reaches out fails, rather than passing on a
machine that happens to have network.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class SourceUnavailable(Exception):
    """The source could not be fetched within the run's budget.

    Raised rather than returning partial data. The pipeline leaves yesterday's
    rows in place, because a partial day published as a full one looks like a
    market that moved.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class RobotsEvidenceMissing(Exception):
    """No robots.txt was served and no recorded evidence exists.

    D92: a missing file is not permission. This stops the run rather than
    defaulting either way.
    """


@dataclass(frozen=True)
class RawPayload:
    """What `fetch` returns and `parse` consumes."""

    url: str
    fetched_at: str
    content: bytes
    content_hash: str


@dataclass(frozen=True)
class FetchResult:
    payloads: tuple[RawPayload, ...]
    published: bool
    reason: str | None = None


class Connector(Protocol):
    """Every source implements exactly this.

    One shape for six sources means the runner, the alarms and the coverage view
    each have one code path rather than six.
    """

    name: str

    def fetch(self) -> FetchResult:
        """Talk to the network. The only stage allowed to."""
        ...

    def parse(self, payload: RawPayload) -> list[dict]:
        """Turn bytes into records. Pure: no socket, no clock, no database."""
        ...

    def emit(self, records: list[dict]) -> int:
        """Write records. Returns the number written."""
        ...
