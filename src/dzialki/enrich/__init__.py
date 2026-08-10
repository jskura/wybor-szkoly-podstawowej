"""Enrichment: what we can say about a parcel beyond what the advert says.

Stage S14 fills this package with the WZ good-neighbour test. Everything here is
pure. It takes geometry, a coverage record and a run date as arguments, and it
returns a verdict with the evidence that produced it. It fetches nothing and
reads no clock, so the same inputs give the same answer on any day.
"""

from __future__ import annotations

from .coverage import CoverageProbe, CoverageRecord, coverage_probe
from .settings import WzParameters, wz_parameters

__all__ = [
    "CoverageProbe",
    "CoverageRecord",
    "WzParameters",
    "coverage_probe",
    "wz_parameters",
]
