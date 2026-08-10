"""The valuation log. Written with the estimate, never after it.

A comparable set cannot be reconstructed later. Listings change price, go
inactive and disappear, so an estimate made in August is unexplainable in
December unless the set that produced it was written down at the time. Scoring
without it can say a prediction was wrong; it cannot say why.

That is why the log ships in the same work item as the estimator rather than in
a later one. Every estimate writes a row from the first estimate onward.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .estimator import Estimate

METHOD_VERSION = "v0.1-comparable-median"

LOG_COLUMNS = (
    "subject_kind",
    "listing_id",
    "parcel_id",
    "teryt_unit",
    "features",
    "price_type",
    "estimate_low",
    "estimate_median",
    "estimate_high",
    "range_kind",
    "n_comparables",
    "widening_step",
    "comparable_ids",
    "method_version",
    "observed_ppm2",
)

INSERT = (
    f"INSERT INTO valuation_log ({', '.join(LOG_COLUMNS)}) "
    f"VALUES ({', '.join(['%s'] * len(LOG_COLUMNS))}) RETURNING id"
)


@dataclass(frozen=True)
class Exclusion:
    """A comparable the reader said does not belong (V51c).

    The reader may not be able to price a plot, but can see that a comparable
    sits on a main road while theirs is in forest. Because the comparable set
    *is* the estimate, that judgement improves the answer directly — so it is
    recorded with the delta it caused rather than applied silently.
    """

    valuation_id: int
    excluded_listing_id: int
    median_before: Decimal
    median_after: Decimal

    @property
    def delta(self) -> Decimal:
        return self.median_after - self.median_before


def log_values(
    est: Estimate,
    *,
    subject_kind: str,
    teryt_unit: str,
    features: str,
    listing_id: int | None = None,
    parcel_id: int | None = None,
    observed_ppm2: Decimal | None = None,
) -> tuple:
    """The estimate as one row, in `LOG_COLUMNS` order."""
    return (
        subject_kind,
        listing_id,
        parcel_id,
        teryt_unit,
        features,
        est.price_type,
        est.low,
        est.median,
        est.high,
        est.range_kind,
        est.n,
        est.widening_step,
        list(est.comparable_ids),
        METHOD_VERSION,
        observed_ppm2,
    )


def write_estimate(conn, est: Estimate, **fields) -> int:
    """Insert one estimate and return its log id."""
    return conn.execute(INSERT, log_values(est, **fields)).fetchone()[0]
