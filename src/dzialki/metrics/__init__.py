"""Aggregates, stock and flow.

The numeric core. Percentiles over prices per square metre, the fixed area bands
those percentiles are grouped by, the spread that travels beside every figure,
and the writer that puts the result into `metric_unit_month`.

Two rules shape every module here. Rule 7: no figure leaves without its sample
size, its spread and its provenance. D67: the sample-size threshold and the flow
window are parameters read from `config/params.yml`, never constants in this
package. Both are enforced by tests rather than left to memory.

Comparable selection and the estimator are the next work item and are not here.
This package computes over the set it is handed.
"""

from .aggregate import (
    Aggregate,
    GroupKey,
    Observation,
    Series,
    aggregate,
    flow_sensitivity,
    headline,
    in_flow_window,
    stock_and_flow,
)
from .bands import AREA_BANDS, AreaBand, band_for
from .percentiles import (
    PERCENTILE_METHOD,
    Percentiles,
    percentiles,
    quantile,
    round_for_storage,
)
from .spread import (
    IQR,
    MIN_MAX,
    RANGE_KINDS,
    UNAVAILABLE,
    Spread,
    range_kind_for,
    spread_from_central_value,
    spread_from_values,
)
from .writer import METRIC_COLUMNS, write_aggregates

__all__ = [
    "AREA_BANDS",
    "IQR",
    "METRIC_COLUMNS",
    "MIN_MAX",
    "PERCENTILE_METHOD",
    "RANGE_KINDS",
    "UNAVAILABLE",
    "Aggregate",
    "AreaBand",
    "GroupKey",
    "Observation",
    "Percentiles",
    "Series",
    "Spread",
    "aggregate",
    "band_for",
    "flow_sensitivity",
    "headline",
    "in_flow_window",
    "percentiles",
    "quantile",
    "range_kind_for",
    "round_for_storage",
    "spread_from_central_value",
    "spread_from_values",
    "stock_and_flow",
    "write_aggregates",
]
