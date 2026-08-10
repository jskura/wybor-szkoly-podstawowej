"""Collapsing duplicate listings, at v0 strength only."""

from .exact import (
    ACCEPTED_FALSE_MERGE_CAVEAT,
    MATCH_KEY_FIELDS,
    Cluster,
    DedupResult,
    Listing,
    deduplicate,
    match_key,
)

__all__ = [
    "ACCEPTED_FALSE_MERGE_CAVEAT",
    "MATCH_KEY_FIELDS",
    "Cluster",
    "DedupResult",
    "Listing",
    "deduplicate",
    "match_key",
]
