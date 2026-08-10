"""The ratified parameters.

Every value the owner ratified lives in ``config/params.yml`` and nowhere else.
This module names the keys; it never carries a value. Nothing has a default,
because a default is a value in hiding — the application would start with a
number nobody chose and behave as though it had been decided.

The audit found nine documents hard-coding one unratified threshold. One file
makes a change one edit, and makes the current value readable without a search.
"""

from __future__ import annotations

import pathlib

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

from .errors import ConfigError, ParamsConfigMissing

COMMITTED_PATH = "config/params.yml"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Comparables(_Strict):
    """How a comparable set is chosen (D108, D109, D110)."""

    area_band_pct: int
    recency_months: int
    min_before_widening: int
    widening_ladder: list[str]


class Aggregates(_Strict):
    """Stock, flow and the spread rule (D67, D107)."""

    flow_window_days: int
    iqr_switch_n: int


class CountTolerance(_Strict):
    """D95 — the allowance is the larger of the two."""

    abs: int
    pct: int


class Validation(_Strict):
    """Area bands and the register-versus-advert conflict rule (O12, D81, D120)."""

    area_min_m2: int
    area_max_m2: int
    conflict_threshold_pct: int
    conflict_threshold_base: str


class Crawl(_Strict):
    """Politeness and agreement tolerances (D93, D94, D95, O42)."""

    fraction_tolerance_pln: int
    count_tolerance: CountTolerance
    retry_after_max_s: int
    default_rate_limit_rpm: int


class Feasibility(_Strict):
    """The good-neighbour radius and the coverage probe (D102, D103).

    Both are configurable because the labelled set has not arbitrated them yet,
    not because anyone may want to change them.
    """

    good_neighbour_radius_m: int
    coverage_probe_radius_m: int
    coverage_probe_min_buildings: int


class Surface(_Strict):
    """Presentation constants (D125)."""

    thousands_sep: str


class Params(_Strict):
    comparables: Comparables
    aggregates: Aggregates
    validation: Validation
    crawl: Crawl
    feasibility: Feasibility
    surface: Surface


def load_params(path: pathlib.Path | str) -> Params:
    """Read every ratified parameter from ``path``.

    Raises ``ConfigError`` naming the offending key and the file when anything is
    missing, mistyped, or unrecognised.
    """
    path = pathlib.Path(path)
    if not path.exists():
        raise ParamsConfigMissing(
            f"{path} is missing. {COMMITTED_PATH} is committed, so a checkout "
            "without it is broken rather than new."
        )

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path} is not valid YAML: {exc}") from exc

    try:
        return Params(**raw)
    except (TypeError, ValidationError) as exc:
        raise ConfigError(f"{path} is incomplete or invalid: {exc}") from exc
