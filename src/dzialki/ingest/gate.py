"""The gate every connector passes before it fetches anything.

One place decides whether a source may be crawled, so the answer cannot differ
between six connectors. The rules are the ones D92 and D73 fixed, restated here
as code rather than as a paragraph somebody remembers.

A source is fetchable only when **recorded evidence** says its robots.txt was
read, and that evidence is a file with a date, not a boolean somebody set. The
evidence path lives in the source registry; a source claiming permission with no
evidence file is refused, because "we checked" and "somebody ticked a box" look
identical once stored.
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass

from .base import RobotsEvidenceMissing
from .robots import RobotsPolicy


@dataclass(frozen=True)
class Evidence:
    """A recorded reading of one host's robots.txt."""

    host: str
    read_at: str
    verbatim: str
    path: pathlib.Path


def load_evidence(directory: pathlib.Path, host: str) -> Evidence:
    """Read the recorded robots.txt for ``host``.

    Raises ``RobotsEvidenceMissing`` when no file exists. The message names the
    directory and the procedure, because the reader is being asked to do a
    task, not to debug a path.
    """
    path = directory / f"{host}.txt"
    if not path.exists():
        raise RobotsEvidenceMissing(
            f"no recorded robots.txt for {host}. Open https://{host}/robots.txt, "
            f"save the verbatim text and the date to {path}, then re-run. "
            "A missing file is not permission (D92)."
        )
    text = path.read_text(encoding="utf-8")
    first, _, rest = text.partition("\n")
    if not first.startswith("# read_at:"):
        raise RobotsEvidenceMissing(
            f"{path} has no `# read_at:` line. Evidence without a date cannot "
            "say whether it describes the file as it is now."
        )
    return Evidence(
        host=host,
        read_at=first.removeprefix("# read_at:").strip(),
        verbatim=rest,
        path=path,
    )


def may_fetch(policy: RobotsPolicy, path: str) -> bool:
    """Whether one path may be fetched under ``policy``.

    A thin wrapper on purpose: every connector asks this question here, so a
    connector cannot answer it for itself.
    """
    return policy.allows(path)


@dataclass(frozen=True)
class CrawlMode:
    """What a partial permission leaves us able to do.

    A portal that allows its search pages and disallows its detail pages is not
    a refusal. It is a smaller product: counts and locations without the
    per-listing attributes. `list_only` records that honestly rather than
    silently emitting records whose fields were never fetched.
    """

    name: str
    detail_permitted: bool


FULL = CrawlMode(name="full", detail_permitted=True)
LIST_ONLY = CrawlMode(name="list_only", detail_permitted=False)
REFUSED = CrawlMode(name="refused", detail_permitted=False)


def mode_for(policy: RobotsPolicy, *, list_path: str, detail_path: str) -> CrawlMode:
    """Decide the crawl mode from what the policy permits."""
    if not policy.allows(list_path):
        return REFUSED
    return FULL if policy.allows(detail_path) else LIST_ONLY
