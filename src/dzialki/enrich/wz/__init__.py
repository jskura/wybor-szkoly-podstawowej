"""The WZ good-neighbour test (D50, FR-65).

Where no plan covers a parcel, building normally needs a *decyzja o warunkach
zabudowy*. The central condition is *dobre sąsiedztwo*: at least one neighbouring
plot reachable from the same public road is already developed.

This package computes an indication of that condition and never a prediction. A
WZ decision depends on the gmina's interpretation, on the planner's analysis, on
protected-area rules and on the neighbours. We cannot predict the outcome, and
nothing here may imply we can.
"""

from __future__ import annotations

from .composite import apply_caps, cap
from .table import TRUTH_TABLE, VERDICTS, lookup

__all__ = ["TRUTH_TABLE", "VERDICTS", "apply_caps", "cap", "lookup"]
