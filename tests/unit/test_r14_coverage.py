"""R14 — the coverage probe (D103), which decides whether we looked.

The control radius and the minimum building count separate *genuinely isolated*
from *not mapped*. Set them wrong and the code produces the exact error the
`unknown` verdict exists to prevent: a count too low turns a blank map into
`unlikely` and states a fact about the world that nobody observed.

Both values are configuration and the 20-parcel labelled set arbitrates them.
That set does not exist, so nothing here asserts the shipped values are right.
It asserts they are read, and that the probe's own logic is not degenerate.
"""

from __future__ import annotations

import datetime
import pathlib

import pytest

pytestmark = [pytest.mark.unit]

RUN_DATE = datetime.date(2026, 8, 8)


def parameters(
    *,
    radius_m: int = 100,
    probe_radius_m: int = 2_000,
    min_buildings: int = 5,
    max_age_days: int = 90,
):
    from dzialki.enrich.settings import WzParameters

    return WzParameters(
        good_neighbour_radius_m=radius_m,
        coverage_probe_radius_m=probe_radius_m,
        coverage_probe_min_buildings=min_buildings,
        coverage_max_age_days=max_age_days,
    )


def record(
    *, source: str = "egib", has_coverage: bool = True, checked: str = "2026-08-01"
):
    from dzialki.enrich.coverage import CoverageRecord

    return CoverageRecord(
        teryt_gmina="999901",
        source=source,
        has_coverage=has_coverage,
        checked_at=datetime.date.fromisoformat(checked),
    )


def probe(coverage_record, *, count: int, neighbour_found: bool, params=None):
    from dzialki.enrich.coverage import coverage_probe

    return coverage_probe(
        coverage_record,
        buildings_in_probe_radius=count,
        neighbour_found=neighbour_found,
        as_of=RUN_DATE,
        parameters=params or parameters(),
    )


# --- the parameters come from configuration, not from the code ------------


def test_the_probe_parameters_are_read_from_the_ratified_file(
    repo_root: pathlib.Path,
) -> None:
    """D102 and D103. One configured value, no per-call-site literal."""
    from dzialki.config import load_params
    from dzialki.enrich.settings import wz_parameters

    shipped = load_params(repo_root / "config" / "params.yml").feasibility
    built = wz_parameters(shipped, coverage_max_age_days=90)

    assert built.good_neighbour_radius_m == shipped.good_neighbour_radius_m
    assert built.coverage_probe_radius_m == shipped.coverage_probe_radius_m
    assert built.coverage_probe_min_buildings == shipped.coverage_probe_min_buildings
    assert built.coverage_max_age_days == 90


def test_the_coverage_max_age_has_no_ratified_value_and_must_be_supplied(
    repo_root: pathlib.Path,
) -> None:
    """A finding, kept in the suite so it cannot be forgotten.

    `config/params.yml` carries no coverage max age, so the probe cannot read
    one. It takes the value as an argument with no default: a default here would
    be a number nobody chose, deciding when evidence goes stale. The key needs a
    decision and a row in the file.
    """
    from dzialki.config import load_params
    from dzialki.config.params import Feasibility
    from dzialki.enrich.settings import wz_parameters

    shipped = load_params(repo_root / "config" / "params.yml").feasibility
    assert set(Feasibility.model_fields) == {
        "good_neighbour_radius_m",
        "coverage_probe_radius_m",
        "coverage_probe_min_buildings",
    }

    with pytest.raises(TypeError):
        wz_parameters(shipped)  # type: ignore[call-arg]


# --- the five outcomes ----------------------------------------------------


def test_a_neighbour_found_proves_coverage_without_a_count() -> None:
    """A building geometry from this place is the map being populated here."""
    result = probe(record(), count=0, neighbour_found=True)
    assert result.value == "present"
    assert result.reason_code == "coverage_confirmed_by_neighbour"
    assert result.source == "egib"
    assert result.observation_count == 0


def test_a_control_count_at_the_minimum_proves_coverage() -> None:
    """`>=`, not `>`. A mutant weakening this is a release blocker."""
    result = probe(record(), count=5, neighbour_found=False)
    assert result.value == "present"
    assert result.reason_code == "coverage_confirmed_by_control_count"
    assert result.observation_count == 5


def test_a_control_count_one_below_the_minimum_is_unproven() -> None:
    result = probe(record(), count=4, neighbour_found=False)
    assert result.value == "absent"
    assert result.reason_code == "coverage_unproven"
    assert result.source is None


def test_a_gmina_with_no_building_layer_is_data_unavailable() -> None:
    result = probe(
        record(source="none", has_coverage=False), count=0, neighbour_found=False
    )
    assert result.value == "absent"
    assert result.reason_code == "building_data_unavailable"


def test_a_missing_record_is_data_unavailable() -> None:
    result = probe(None, count=99, neighbour_found=True)
    assert result.value == "absent"
    assert result.reason_code == "building_data_unavailable"
    assert result.observation_count == 99


def test_a_stale_record_cannot_support_coverage() -> None:
    """The fixture's stale case, SYNTH-D, checked on 2025-01-01.

    The map underneath a coverage record does change, so the record goes stale
    even though D104 removed the *legal* citation clock. The test plan says 585
    days between 2025-01-01 and 2026-08-08. The count is 584.
    """
    result = probe(record(checked="2025-01-01"), count=99, neighbour_found=True)
    assert result.value == "absent"
    assert result.reason_code == "coverage_record_stale"
    assert result.age_days == 584


def test_a_record_exactly_at_the_maximum_age_is_still_fresh() -> None:
    """The boundary, asserted rather than assumed. 2026-05-10 is 90 days back."""
    result = probe(record(checked="2026-05-10"), count=0, neighbour_found=True)
    assert result.age_days == 90
    assert result.value == "present"


def test_a_record_one_day_past_the_maximum_age_is_stale() -> None:
    result = probe(record(checked="2026-05-09"), count=0, neighbour_found=True)
    assert result.age_days == 91
    assert result.value == "absent"
    assert result.reason_code == "coverage_record_stale"


# --- rule 7: the evidence carries its own provenance ----------------------


def test_the_probe_carries_source_as_of_and_observation_count() -> None:
    result = probe(record(), count=7, neighbour_found=False)
    assert result.source == "egib"
    assert result.as_of == datetime.date(2026, 8, 1)
    assert result.observation_count == 7
    assert result.probe_radius_m == 2_000
    assert result.min_buildings == 5


def test_an_absent_probe_names_no_source() -> None:
    """`unlikely_requires_coverage` reads this field. An absent probe that still
    named a source would let the constraint pass on evidence we do not hold."""
    result = probe(record(), count=0, neighbour_found=False)
    assert result.value == "absent"
    assert result.source is None
    assert result.as_of is None


# --- changing the configuration changes the answer ------------------------


def test_changing_the_minimum_count_changes_the_answer() -> None:
    """The behavioural half of D103. A code-held copy would ignore this."""
    at_five = probe(record(), count=4, neighbour_found=False)
    at_four = probe(
        record(), count=4, neighbour_found=False, params=parameters(min_buildings=4)
    )
    assert at_five.value == "absent"
    assert at_four.value == "present"


def test_changing_the_maximum_age_changes_the_answer() -> None:
    fresh = probe(
        record(checked="2025-01-01"),
        count=9,
        neighbour_found=False,
        params=parameters(max_age_days=600),
    )
    stale = probe(record(checked="2025-01-01"), count=9, neighbour_found=False)
    assert fresh.value == "present"
    assert stale.value == "absent"


def test_every_declared_reason_code_is_reachable() -> None:
    """A vocabulary with an unreachable member is a vocabulary that lies."""
    from dzialki.enrich.coverage import COVERAGE_REASON_CODES

    reached = {
        probe(record(), count=0, neighbour_found=True).reason_code,
        probe(record(), count=5, neighbour_found=False).reason_code,
        probe(record(), count=0, neighbour_found=False).reason_code,
        probe(
            record(has_coverage=False, source="none"), count=0, neighbour_found=False
        ).reason_code,
        probe(record(checked="2025-01-01"), count=9, neighbour_found=True).reason_code,
    }
    assert reached == set(COVERAGE_REASON_CODES)
