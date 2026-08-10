"""Fetching. The three-stage connector contract, and the only HTTP client."""

from .base import (
    Connector,
    FetchResult,
    RawPayload,
    RobotsEvidenceMissing,
    SourceUnavailable,
)

__all__ = [
    "Connector",
    "FetchResult",
    "RawPayload",
    "RobotsEvidenceMissing",
    "SourceUnavailable",
]
