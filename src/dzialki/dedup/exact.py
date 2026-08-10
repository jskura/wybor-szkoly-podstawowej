"""Dedup at v0 strength: exact matching, and honesty about what it misses.

The match key is `(area_m2, price_pln, teryt_gmina, asset_class)` (D78). It is a
quadruple. `zoning_claim` and `seller_contact_hash` are not in it — the first is
free text, the second is the same person selling two different plots.

**What this deliberately cannot do.** Two agencies listing one plot at 250 000
and 255 000 złotych stay two records. The full matcher — geohash, title shingles,
image hashes, a scored labelled set — is out of v0 scope, so v0 under-merges.
Under-merging inflates the count; it does not invent a price.

**What it gets wrong in the other direction.** Two genuinely different 1 000 m²
plots at 100 000 złotych in one gmina merge into one. D78 accepted that,
knowingly. The residual false-merge rate is unknown, and every run says so
rather than implying it is zero.

Both counts travel together. More data looks like better data, so a caller sees
`n_before` and `n_after` side by side and never one alone.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

# D78. The order is part of the contract: a test asserts these four fields, in
# this order, so a fifth cannot be added without a decision.
MATCH_KEY_FIELDS = ("area_m2", "price_pln", "teryt_gmina", "asset_class")

ACCEPTED_FALSE_MERGE_CAVEAT = (
    "Dedup is exact-match only (D78). Two different plots with the same area, "
    "price, gmina and asset class merge into one. The residual false-merge rate "
    "is unknown and is not estimated."
)


@dataclass(frozen=True)
class Listing:
    """The fields dedup reads. Not the whole listing row."""

    source_id: int
    external_id: str
    first_seen_at: str
    area_m2: Decimal
    price_pln: Decimal
    teryt_gmina: str
    asset_class: str


@dataclass(frozen=True)
class Cluster:
    canonical: Listing
    members: tuple[Listing, ...]

    @property
    def duplicate_count(self) -> int:
        return len(self.members)


@dataclass(frozen=True)
class DedupResult:
    clusters: tuple[Cluster, ...]
    n_before: int
    n_after: int
    caveats: tuple[str, ...] = field(default=(ACCEPTED_FALSE_MERGE_CAVEAT,))


def match_key(listing: Listing) -> tuple:
    return tuple(getattr(listing, name) for name in MATCH_KEY_FIELDS)


def _canonical_order(listing: Listing) -> tuple:
    """D84. A total order, so the canonical record survives a re-run.

    Earliest first seen, then lowest source, then lowest external id. Without
    the last two, two records first seen in the same second would swap places
    between runs and the canonical listing would move for no visible reason.
    """
    return (listing.first_seen_at, listing.source_id, listing.external_id)


def deduplicate(listings: list[Listing]) -> DedupResult:
    """Collapse exact matches into clusters.

    A singleton gets a cluster too. Special-casing it would leave later code
    remembering which listings have a cluster and which do not.
    """
    grouped: dict[tuple, list[Listing]] = {}
    for listing in listings:
        grouped.setdefault(match_key(listing), []).append(listing)

    clusters = []
    for key in sorted(grouped, key=lambda k: tuple(str(part) for part in k)):
        members = sorted(grouped[key], key=_canonical_order)
        clusters.append(Cluster(canonical=members[0], members=tuple(members)))

    return DedupResult(
        clusters=tuple(clusters),
        n_before=len(listings),
        n_after=len(clusters),
    )
