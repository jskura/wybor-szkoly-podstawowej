"""R14 — the composite. A rule table of 54 cells, never a score.

`3 (neighbour) × 3 (shares_road) × 3 (landuse) × 2 (coverage) = 54`. No cell is
omitted, no cell falls through to a default, and the key set is asserted equal to
the cross-product — not a superset, not a subset.

A weighted score would let two weak positives outvote a missing-data `unknown`.
The static check below forbids one.
"""

from __future__ import annotations

import ast
import itertools
import pathlib

import pytest

pytestmark = [pytest.mark.unit]


def axes():
    from dzialki.enrich.wz.table import (
        COVERAGE_VALUES,
        LANDUSE_VALUES,
        NEIGHBOUR_VALUES,
        SHARES_ROAD_VALUES,
    )

    return (NEIGHBOUR_VALUES, SHARES_ROAD_VALUES, LANDUSE_VALUES, COVERAGE_VALUES)


def cross_product():
    return set(itertools.product(*axes()))


# --- the table itself -----------------------------------------------------


def test_the_four_axes_carry_exactly_the_declared_values() -> None:
    neighbour, shares_road, landuse, coverage = axes()
    assert neighbour == ("present", "absent", "unknown")
    assert shares_road == ("true", "false", "unknown")
    assert landuse == ("not_required", "required", "unknown")
    assert coverage == ("present", "absent")


def test_no_input_combination_produces_a_verdict_outside_the_table() -> None:
    """Equality, so a missing cell and an invented one both fail."""
    from dzialki.enrich.wz.table import TRUTH_TABLE, VERDICTS

    assert set(TRUTH_TABLE) == cross_product()
    assert len(TRUTH_TABLE) == 54
    assert VERDICTS == ("likely", "uncertain", "unlikely", "unknown")
    for cell in TRUTH_TABLE.values():
        assert cell.verdict in VERDICTS


def test_every_cell_is_numbered_once_from_one_to_fifty_four() -> None:
    """The numbering matches the test plan's blocks, so a reader can find a row."""
    from dzialki.enrich.wz.table import TRUTH_TABLE

    numbers = sorted(cell.number for cell in TRUTH_TABLE.values())
    assert numbers == list(range(1, 55))


def test_the_verdict_distribution_is_the_declared_one() -> None:
    """`likely` is one cell in fifty-four. If a change makes it two, this test
    fails and somebody has to say why in writing."""
    from dzialki.enrich.wz.table import TRUTH_TABLE

    counts: dict[str, int] = {}
    for cell in TRUTH_TABLE.values():
        counts[cell.verdict] = counts.get(cell.verdict, 0) + 1
    assert counts == {"likely": 1, "uncertain": 17, "unlikely": 9, "unknown": 27}


def test_likely_occupies_exactly_one_cell_of_fifty_four() -> None:
    from dzialki.enrich.wz.table import TRUTH_TABLE

    likely = [key for key, cell in TRUTH_TABLE.items() if cell.verdict == "likely"]
    assert likely == [("present", "true", "not_required", "present")]


def test_every_cell_carries_at_least_one_reason() -> None:
    """`reason_code` is NOT NULL in the schema: every verdict carries its reason,
    not only `unknown`. A cell whose reason comes from the coverage probe
    declares that instead of leaving the tuple empty."""
    from dzialki.enrich.wz.table import TRUTH_TABLE

    for key, cell in TRUTH_TABLE.items():
        assert cell.reasons or cell.reason_from_coverage, key


def test_only_the_absent_neighbour_and_absent_coverage_block_defers_its_reason() -> (
    None
):
    from dzialki.enrich.wz.table import TRUTH_TABLE

    deferred = {key for key, cell in TRUTH_TABLE.items() if cell.reason_from_coverage}
    assert deferred == {
        ("absent", shares_road, landuse, "absent")
        for shares_road in ("true", "false", "unknown")
        for landuse in ("not_required", "required", "unknown")
    }
    assert len(deferred) == 9


def test_an_unknown_neighbour_signal_is_absorbing() -> None:
    """Eighteen cells, one verdict, two reason codes.

    "The map does not exist" and "the map exists and we failed to read it" call
    for different operator actions and different sentences. A single code across
    both would pass every verdict test and still be wrong.
    """
    from dzialki.enrich.wz.table import TRUTH_TABLE

    populated = set()
    unavailable = set()
    for key, cell in TRUTH_TABLE.items():
        if key[0] != "unknown":
            continue
        assert cell.verdict == "unknown", key
        (populated if key[3] == "present" else unavailable).add(cell.reasons)

    assert populated == {("building_query_failed",)}
    assert unavailable == {("building_data_unavailable",)}


def test_unlikely_appears_only_where_coverage_is_present() -> None:
    """The rule the whole stage exists for, restated at the table seam."""
    from dzialki.enrich.wz.table import TRUTH_TABLE

    unlikely = {key for key, cell in TRUTH_TABLE.items() if cell.verdict == "unlikely"}
    assert unlikely == {
        ("absent", shares_road, landuse, "present")
        for shares_road in ("true", "false", "unknown")
        for landuse in ("not_required", "required", "unknown")
    }


def test_the_whole_absent_neighbour_block_is_unlikely_whatever_the_other_axes_say() -> (
    None
):
    """The good-neighbour condition has demonstrably failed. Road and land use
    can add obstacles, never remove this one. Making the verdict depend on them
    here would be a weighted score wearing a rule table's clothes."""
    from dzialki.enrich.wz.table import TRUTH_TABLE

    verdicts = {
        TRUTH_TABLE[("absent", shares_road, landuse, "present")].verdict
        for shares_road in ("true", "false", "unknown")
        for landuse in ("not_required", "required", "unknown")
    }
    assert verdicts == {"unlikely"}


@pytest.mark.parametrize(
    "key,expected_verdict,expected_reasons",
    [
        (
            ("present", "true", "not_required", "present"),
            "likely",
            ("good_neighbour_satisfied",),
        ),
        (
            ("present", "true", "required", "present"),
            "uncertain",
            ("dedesignation_required",),
        ),
        (
            ("present", "false", "unknown", "present"),
            "uncertain",
            ("neighbour_on_different_road", "landuse_unknown"),
        ),
        (
            ("present", "true", "not_required", "absent"),
            "uncertain",
            ("capped_by_coverage_absent",),
        ),
        (
            ("absent", "unknown", "required", "present"),
            "unlikely",
            (
                "no_neighbour_within_radius",
                "road_status_unknown",
                "dedesignation_required",
            ),
        ),
    ],
)
def test_named_cells_carry_the_declared_reasons(
    key, expected_verdict: str, expected_reasons: tuple[str, ...]
) -> None:
    from dzialki.enrich.wz.table import TRUTH_TABLE

    cell = TRUTH_TABLE[key]
    assert cell.verdict == expected_verdict
    assert cell.reasons == expected_reasons


# --- the caps -------------------------------------------------------------


def test_a_cap_only_ever_touches_likely() -> None:
    from dzialki.enrich.wz.composite import cap

    assert cap("likely") == "uncertain"
    assert cap("uncertain") == "uncertain"
    assert cap("unlikely") == "unlikely"
    assert cap("unknown") == "unknown"


def test_protected_overlap_alone_never_produces_unlikely() -> None:
    """Protection changes the procedure. It does not forbid building, and
    claiming otherwise is exactly the overreach `19` §1.2 rules out."""
    from dzialki.enrich.wz.composite import cap
    from dzialki.enrich.wz.table import TRUTH_TABLE

    for cell in TRUTH_TABLE.values():
        before, after = cell.verdict, cap(cell.verdict)
        assert (before, after) in {
            ("likely", "uncertain"),
            ("uncertain", "uncertain"),
            ("unlikely", "unlikely"),
            ("unknown", "unknown"),
        }


def test_the_caps_commute_and_are_idempotent() -> None:
    """A `min()` over a scale is not the same as a chain of `if` statements, and
    this is where the difference would show."""
    from dzialki.enrich.wz.composite import apply_caps
    from dzialki.enrich.wz.table import TRUTH_TABLE

    for cell in TRUTH_TABLE.values():
        for osm, protected in itertools.product((False, True), repeat=2):
            osm_first = apply_caps(
                apply_caps(cell.verdict, osm_source=osm, protected=False)[0],
                osm_source=False,
                protected=protected,
            )[0]
            protection_first = apply_caps(
                apply_caps(cell.verdict, osm_source=False, protected=protected)[0],
                osm_source=osm,
                protected=False,
            )[0]
            together = apply_caps(cell.verdict, osm_source=osm, protected=protected)[0]
            assert osm_first == protection_first == together
            # Idempotent: applying the same cap twice changes nothing.
            assert apply_caps(together, osm_source=osm, protected=protected)[0] == (
                together
            )


def test_no_modifier_ever_raises_a_verdict() -> None:
    from dzialki.enrich.wz.composite import OPTIMISM, apply_caps
    from dzialki.enrich.wz.table import TRUTH_TABLE

    for cell in TRUTH_TABLE.values():
        for osm in (False, True):
            for protected in (False, True):
                result, _reasons = apply_caps(
                    cell.verdict, osm_source=osm, protected=protected
                )
                assert OPTIMISM[result] <= OPTIMISM[cell.verdict]


def test_the_cap_reasons_name_which_cap_fired() -> None:
    from dzialki.enrich.wz.composite import apply_caps

    assert apply_caps("likely", osm_source=True, protected=False) == (
        "uncertain",
        ("capped_by_osm_source",),
    )
    assert apply_caps("likely", osm_source=False, protected=True) == (
        "uncertain",
        ("capped_by_protection",),
    )
    assert apply_caps("likely", osm_source=True, protected=True) == (
        "uncertain",
        ("capped_by_osm_source", "capped_by_protection"),
    )
    assert apply_caps("unlikely", osm_source=True, protected=True) == (
        "unlikely",
        (),
    )


# --- metamorphic properties ----------------------------------------------


def test_the_verdict_is_independent_of_the_axis_evaluation_order() -> None:
    """54 cells × 4! orders. The table is a lookup, so this must hold."""
    from dzialki.enrich.wz.table import lookup

    for key in cross_product():
        neighbour, shares_road, landuse, coverage = key
        by_name = {
            "neighbour": neighbour,
            "shares_road": shares_road,
            "landuse": landuse,
            "coverage": coverage,
        }
        verdicts = set()
        for order in itertools.permutations(by_name):
            verdicts.add(lookup(**{name: by_name[name] for name in order}).verdict)
        assert len(verdicts) == 1


def test_adding_evidence_never_returns_the_verdict_to_unknown() -> None:
    """36 transitions. Replacing an `unknown` neighbour with a real observation
    never puts us back where we started."""
    from dzialki.enrich.wz.table import TRUTH_TABLE

    transitions = 0
    for key, cell in TRUTH_TABLE.items():
        if key[0] != "unknown":
            continue
        assert cell.verdict == "unknown"
        for replacement in ("present", "absent"):
            after = TRUTH_TABLE[(replacement, *key[1:])]
            transitions += 1
            if key[3] == "present":
                assert after.verdict != "unknown"
    assert transitions == 36


def test_removing_coverage_always_moves_unlikely_to_unknown() -> None:
    """Nine transitions, all to `unknown`, none to `uncertain` or `likely`."""
    from dzialki.enrich.wz.table import TRUTH_TABLE

    moved = 0
    for key, cell in TRUTH_TABLE.items():
        if cell.verdict != "unlikely":
            continue
        after = TRUTH_TABLE[(*key[:3], "absent")]
        assert after.verdict == "unknown", key
        moved += 1
    assert moved == 9


def test_a_composite_that_ignores_coverage_fails_the_third_property() -> None:
    """The non-vacuity companion.

    A deliberately broken table that drops the coverage axis passes order
    independence and monotonicity, and fails coverage removal. Without this
    seed, the property above could hold for a table that never consults
    coverage at all.
    """
    from dzialki.enrich.wz.table import TRUTH_TABLE

    broken = {key: TRUTH_TABLE[(*key[:3], "present")] for key in cross_product()}

    # It still passes the first two properties.
    assert set(broken) == cross_product()
    for key in cross_product():
        if key[0] == "unknown" and key[3] == "present":
            assert broken[key].verdict == "unknown"

    # And it fails the third.
    survivors = [
        key
        for key, cell in broken.items()
        if cell.verdict == "unlikely" and key[3] == "absent"
    ]
    assert len(survivors) == 9


# --- no numeric weights ---------------------------------------------------


def _numeric_constants(source: str) -> list[float]:
    """Every numeric literal in the code, ignoring docstrings.

    Reading source text would match this docstring. Reading the parse tree does
    not, and a scan that flags its own explanation trains a reader to ignore it.
    """
    tree = ast.parse(source)
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)):
            first = node.body[0] if node.body else None
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                docstrings.add(id(first.value))

    found: list[float] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and id(node) not in docstrings
            and isinstance(node.value, (int, float))
            and not isinstance(node.value, bool)
        ):
            found.append(node.value)
    return found


def test_the_composite_contains_no_numeric_weights(repo_root: pathlib.Path) -> None:
    """A weighted score would let two weak positives outvote a missing-data
    `unknown`. The table has no arithmetic in it at all."""
    source = (
        repo_root / "src" / "dzialki" / "enrich" / "wz" / "composite.py"
    ).read_text(encoding="utf-8")

    assert [
        value for value in _numeric_constants(source) if isinstance(value, float)
    ] == []
    assert "sum(" not in source


def test_the_weight_scan_finds_a_seeded_weight() -> None:
    """The non-vacuity companion. A scan for absence passes trivially when its
    pattern is wrong."""
    seeded = '"""A docstring naming 0.75 so the scan cannot match its own prose."""\nWEIGHT = 0.75\n'
    assert 0.75 in _numeric_constants(seeded)
    assert _numeric_constants('"""0.75 in prose only."""\n') == []
