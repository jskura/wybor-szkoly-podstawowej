"""R1.9, R1.10 and R1.16–R1.20 — configuration loads, or refuses to start.

R1.16–R1.20 discharge V65(A): every ratified parameter lives in one file, none of
them appears as a literal in the code, and a missing key is an error rather than a
silent default.
"""

from __future__ import annotations

import ast
import pathlib
import re

import pytest
import yaml

pytestmark = [pytest.mark.unit]

DECISION_MARKER = re.compile(r"#\s*(D\d{1,3}|O\d{1,2})\b")


def test_settings_require_explicit_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from dzialki.config import ConfigError, Settings

    monkeypatch.delenv("DZIALKI_DATABASE_URL", raising=False)
    with pytest.raises(ConfigError):
        Settings()

    monkeypatch.setenv("DZIALKI_DATABASE_URL", "postgresql://u:p@h:5432/db")
    assert Settings().database_url == "postgresql://u:p@h:5432/db"


def test_sources_config_defaults_are_fail_closed(repo_root: pathlib.Path) -> None:
    """A source that defaults to enabled with no robots evidence is the failure
    V14 exists to prevent. The defaults are decided here, not in the connector."""
    from dzialki.config import load_params, load_sources

    params = load_params(repo_root / "config" / "params.yml")
    sources = load_sources(
        repo_root / "config" / "sources.yml",
        default_rate_limit_rpm=params.crawl.default_rate_limit_rpm,
    )
    minimal = sources["minimal_registry"]
    assert minimal.enabled is False
    assert minimal.robots_ok is False
    assert minimal.rate_limit_rpm == params.crawl.default_rate_limit_rpm
    assert params.crawl.default_rate_limit_rpm == 5


def test_unknown_source_kind_is_rejected_by_name(tmp_path: pathlib.Path) -> None:
    from dzialki.config import ConfigError, load_sources

    bad = tmp_path / "sources.yml"
    bad.write_text(
        "sources:\n  - name: portal_x\n    kind: scraper\n", encoding="utf-8"
    )
    with pytest.raises(ConfigError) as caught:
        load_sources(bad, default_rate_limit_rpm=5)
    assert "kind" in str(caught.value)
    assert "scraper" in str(caught.value)


# --- V65(A) — the parameter file ------------------------------------------


def test_params_file_loads_every_ratified_parameter(
    repo_root: pathlib.Path,
) -> None:
    from dzialki.config import load_params

    params = load_params(repo_root / "config" / "params.yml")
    assert params.comparables.area_band_pct == 50
    assert params.comparables.recency_months == 12
    assert params.comparables.min_before_widening == 3
    assert params.aggregates.flow_window_days == 90
    assert params.aggregates.iqr_switch_n == 5
    assert params.validation.conflict_threshold_pct == 5
    assert params.validation.conflict_threshold_base == "register"
    assert params.crawl.retry_after_max_s == 3600
    assert params.feasibility.good_neighbour_radius_m == 100
    assert params.surface.thousands_sep == " "


def test_every_params_key_carries_a_decision_number(
    repo_root: pathlib.Path,
) -> None:
    """A parameter with no decision number is one nobody ratified."""
    text = (repo_root / "config" / "params.yml").read_text(encoding="utf-8")
    known = set(
        re.findall(
            r"^\| \*{0,2}(D\d{1,3}|O\d{1,2})\b",
            (repo_root / "docs" / "00-decisions.md").read_text(encoding="utf-8"),
            re.MULTILINE,
        )
    )
    # O20-O24 are recorded as one ranged row, so the per-row scan misses them.
    known |= {f"O{n}" for n in range(20, 25)}

    undocumented: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.endswith(":"):  # a section header carries no value
            continue
        found = DECISION_MARKER.search(line)
        if found is None:
            undocumented.append(stripped)
        else:
            assert found.group(1) in known, f"{found.group(1)} is not in the log"
    assert undocumented == []


def test_missing_params_file_raises_named_actionable_error(
    tmp_path: pathlib.Path,
) -> None:
    from dzialki.config import ParamsConfigMissing, load_params

    with pytest.raises(ParamsConfigMissing) as caught:
        load_params(tmp_path / "absent.yml")
    assert "config/params.yml" in str(caught.value)


@pytest.mark.parametrize(
    "section,key",
    [
        ("comparables", "area_band_pct"),
        ("aggregates", "flow_window_days"),
        ("validation", "conflict_threshold_pct"),
        ("crawl", "retry_after_max_s"),
        ("crawl", "default_rate_limit_rpm"),
        ("feasibility", "good_neighbour_radius_m"),
        ("surface", "thousands_sep"),
    ],
)
def test_removing_any_key_refuses_to_start(
    repo_root: pathlib.Path, tmp_path: pathlib.Path, section: str, key: str
) -> None:
    """Proves there is no silent built-in default behind the file."""
    from dzialki.config import ConfigError, load_params

    data = yaml.safe_load(
        (repo_root / "config" / "params.yml").read_text(encoding="utf-8")
    )
    del data[section][key]
    truncated = tmp_path / "params.yml"
    truncated.write_text(yaml.safe_dump(data), encoding="utf-8")

    with pytest.raises(ConfigError) as caught:
        load_params(truncated)
    message = str(caught.value)
    assert key in message
    assert "params.yml" in message


def test_malformed_params_file_names_the_file(tmp_path: pathlib.Path) -> None:
    from dzialki.config import ConfigError, load_params

    broken = tmp_path / "params.yml"
    broken.write_text("comparables: [unclosed\n", encoding="utf-8")
    with pytest.raises(ConfigError) as caught:
        load_params(broken)
    assert "params.yml" in str(caught.value)


@pytest.mark.architecture
def test_no_ratified_value_appears_as_a_literal_in_the_source(
    repo_root: pathlib.Path,
) -> None:
    """The test that catches a parameter copied out of the file and into code.

    The value set is deliberately narrow. It first held every ratified number,
    including 12 and 100, and flagged `month += 12` and `Decimal(100)` in a date
    helper and a percentage conversion. Months per year and parts per hundred are
    universal constants, not copies of a recency window or a search radius, so a
    scan that reports them trains a reader to ignore it.

    Narrowing the values alone would weaken the rule, so
    `test_every_ratified_parameter_is_read_somewhere` below covers the same
    failure from the other side: a copied value orphans its configuration key,
    and an orphaned key is easy to spot and impossible to argue with.
    """
    from dzialki.config import load_params

    params = load_params(repo_root / "config" / "params.yml")
    forbidden = {
        params.aggregates.flow_window_days,
        params.validation.area_min_m2,
        params.validation.area_max_m2,
        params.validation.price_per_m2_max_pln,
        params.crawl.retry_after_max_s,
        params.feasibility.coverage_probe_radius_m,
    }
    exempt = {repo_root / "src" / "dzialki" / "config" / "params.py"}

    offenders: list[str] = []
    for path in (repo_root / "src").rglob("*.py"):
        if path in exempt:
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (
                isinstance(node, ast.Constant)
                and not isinstance(node.value, bool)
                and node.value in forbidden
            ):
                offenders.append(f"{path.relative_to(repo_root)}:{node.lineno}")
    assert offenders == []


# Parameters whose consumer has not been built yet. Each names the stage that
# will read it. The mapping exists so an unread key is a scheduled gap rather
# than an unnoticed one.
PENDING_STAGES = {
    "comparables.recency_months": "S9 — the pipeline that calls the estimator",
    "comparables.min_before_widening": "S9 — the widening ladder",
    "comparables.widening_ladder": "S9 — the widening ladder (and O41)",
    # The phrase parser takes the tolerance as an argument and the test
    # supplies it. The connector that would read the key is still S13 work,
    # so the key stays pending: a test reading it is not a consumer.
    "crawl.fraction_tolerance_pln": "S13 — the auction connector",
    "crawl.count_tolerance": "S12 — the portal corpus check",
    "crawl.retry_after_max_s": "S12 — the crawl runner",
    "crawl.default_rate_limit_rpm": "S12 — the crawl runner",
}


@pytest.mark.architecture
def test_every_ratified_parameter_is_read_somewhere(
    repo_root: pathlib.Path,
) -> None:
    """A parameter nobody reads is a parameter something else has copied.

    This is the half of FR-75 the value scan cannot cover. Changing a key here
    must change behaviour; if the code holds its own copy, the key goes unread
    and the file becomes documentation of a value the program ignores.
    """
    from dzialki.config import Params

    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (repo_root / "src").rglob("*.py")
        if path.name != "params.py"
    )

    unread = sorted(
        f"{section_name}.{key}"
        for section_name, section in Params.model_fields.items()
        for key in section.annotation.model_fields
        if f".{key}" not in source
    )
    # Equality, not containment. A key whose stage lands starts being read, this
    # test fails, and its row has to be deleted deliberately. Containment would
    # let the list rot into a permanent excuse.
    assert unread == sorted(PENDING_STAGES)
