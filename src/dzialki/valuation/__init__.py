"""The comparable estimator and the valuation log.

The verdict comes from the comparable-set median and from nothing else. A feature
model may run alongside to say what each attribute is worth, clearly marked as a
model estimate, but it is structurally barred from producing the answer: the
verdict module imports no model, and an architecture test enforces that.
"""

from .comparables import (
    Candidate,
    ComparableSet,
    Subject,
    area_band,
    recency_cutoff,
    select_comparables,
)
from .estimator import ABOVE, BELOW, WITHIN, Absence, Estimate, estimate, verdict
from .log import LOG_COLUMNS, METHOD_VERSION, Exclusion, log_values, write_estimate

__all__ = [
    "ABOVE",
    "BELOW",
    "LOG_COLUMNS",
    "METHOD_VERSION",
    "WITHIN",
    "Absence",
    "Candidate",
    "ComparableSet",
    "Estimate",
    "Exclusion",
    "Subject",
    "area_band",
    "estimate",
    "log_values",
    "recency_cutoff",
    "select_comparables",
    "verdict",
    "write_estimate",
]
