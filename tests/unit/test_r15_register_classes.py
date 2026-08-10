"""S15 — the register-class table, which decides the regime.

The table is data. No module under `src/dzialki/legal/` holds a class symbol, so
these tests are the only place a symbol appears outside the file itself.

`05` §10.1 and the test plan §5.1 fix the rows. D106 gives `Ls` the forest
regime, and D117 rules on `Lz` and `Lzr`.
"""

from __future__ import annotations

import pathlib

import pytest
import yaml

from dzialki.legal import (
    REGIMES,
    RegisterClassTableError,
    UnknownRegisterClass,
    load_register_classes,
)

pytestmark = [pytest.mark.unit]

TEST_PLAN_SOURCE = "docs/tdd/plans/05-feasibility-test-plan.md §5.1"
D117_SOURCE = "docs/19-legal-and-feasibility.md §2a.3 (D117)"

# The 24 rows of the test plan §5.1, in file order.
EXPECTED_SYMBOLS = (
    "R",
    "S",
    "Ł",
    "Ps",
    "Br",
    "Wsr",
    "W",
    "Lzr",
    "Ls",
    "Lz",
    "B",
    "Ba",
    "Bi",
    "Bp",
    "Bz",
    "dr",
    "Tk",
    "Ti",
    "Tp",
    "Ws",
    "Wp",
    "Wm",
    "Tr",
    "N",
)

# Each pair differs by one or two characters and falls in a different regime.
# D106 added `Ls`/`Lz`, which a `startswith("L")` implementation gets wrong.
ADVERSARIAL_PAIRS = (("B", "Br"), ("Ws", "Wsr"), ("Lz", "Lzr"), ("Ls", "Lz"))


@pytest.fixture()
def table_path(repo_root: pathlib.Path) -> pathlib.Path:
    return repo_root / "config" / "register_classes.yml"


@pytest.fixture()
def table(table_path: pathlib.Path):
    return load_register_classes(table_path)


def edited(path: pathlib.Path, tmp_path: pathlib.Path, edit) -> pathlib.Path:
    """The committed table with one row changed, written to a temporary file."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    edit(raw)
    target = tmp_path / "register_classes.yml"
    target.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    return target


# --- the rows --------------------------------------------------------------


def test_the_table_holds_exactly_the_documented_classes(table) -> None:
    """Equality, never containment. A class added later needs a decision."""
    assert tuple(row.symbol for row in table.rows) == EXPECTED_SYMBOLS


def test_the_regime_counts_match_the_document(table) -> None:
    """8 agricultural, 1 forest, 15 none — the test plan §5.1 counts them."""
    counted = {regime: 0 for regime in REGIMES}
    for row in table.rows:
        counted[row.regime] += 1
    assert counted == {"agricultural": 8, "forest": 1, "none": 15}


def test_the_three_declared_regimes_are_exactly_these(table) -> None:
    assert REGIMES == ("agricultural", "forest", "none")
    assert {row.regime for row in table.rows} == set(REGIMES)


def test_the_ruled_rows_carry_the_d117_source(table) -> None:
    """`Ls`, `Lz` and `Lzr` were ruled on, so they cite the ruling."""
    cited = {row.symbol: row.source for row in table.rows if row.source == D117_SOURCE}
    assert cited == {
        "Lzr": D117_SOURCE,
        "Ls": D117_SOURCE,
        "Lz": D117_SOURCE,
    }


def test_every_other_row_cites_the_test_plan(table) -> None:
    other = {row.symbol for row in table.rows if row.symbol not in {"Ls", "Lz", "Lzr"}}
    assert {row.symbol for row in table.rows if row.source == TEST_PLAN_SOURCE} == other


def test_the_forest_regime_holds_exactly_one_row(table) -> None:
    assert [row.symbol for row in table.rows if row.regime == "forest"] == ["Ls"]


def test_the_regulation_reference_is_recorded_as_unverified(table) -> None:
    """No document here names the EGiB classification regulation.

    A remembered number would look exactly like a checked one.
    """
    assert table.regulation == "⟨RECORD⟩"
    assert table.regulation_verified is False
    assert table.consolidated_text_date is None


def test_every_row_carries_a_name(table) -> None:
    assert [row.symbol for row in table.rows if not row.name] == []
    assert table.name_of("Ls") == "lasy"


# --- the load refuses the malformed ----------------------------------------


def test_a_typo_in_the_regime_column_fails_the_load(
    table_path: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    """`agricutural` must not read as "no regime"."""

    def typo(raw: dict) -> None:
        raw["classes"][0]["regime"] = "agricutural"

    with pytest.raises(RegisterClassTableError) as caught:
        load_register_classes(edited(table_path, tmp_path, typo))
    assert "agricutural" in str(caught.value)


def test_a_row_without_a_source_fails_the_load(
    table_path: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    def strip(raw: dict) -> None:
        del raw["classes"][0]["source"]

    with pytest.raises(RegisterClassTableError):
        load_register_classes(edited(table_path, tmp_path, strip))


def test_a_duplicate_symbol_fails_the_load(
    table_path: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    """Two rows for one symbol would make the regime depend on the row order."""

    def duplicate(raw: dict) -> None:
        raw["classes"].append(dict(raw["classes"][0]))

    with pytest.raises(RegisterClassTableError):
        load_register_classes(edited(table_path, tmp_path, duplicate))


def test_a_missing_file_fails_the_load(tmp_path: pathlib.Path) -> None:
    with pytest.raises(RegisterClassTableError):
        load_register_classes(tmp_path / "absent.yml")


# --- lookup ----------------------------------------------------------------


@pytest.mark.parametrize(("left", "right"), ADVERSARIAL_PAIRS)
def test_adversarial_class_pairs_do_not_share_a_regime(table, left, right) -> None:
    assert table.regime_of(left) != table.regime_of(right)


def test_the_ruled_pair_regimes_are_exactly_these(table) -> None:
    assert table.regime_of("Ls") == "forest"
    assert table.regime_of("Lz") == "none"
    assert table.regime_of("Lzr") == "agricultural"


def test_class_symbol_matching_is_case_sensitive(table) -> None:
    """A case-folded match would read `Br` as `BR` and `dr` as `Dr`."""
    assert table.regime_of("dr") == "none"
    assert table.get("DR") is None
    assert table.get("Dr") is None


def test_the_diacritic_symbol_round_trips(table) -> None:
    """`Ł` is U+0141. `L` is a different row, and it is absent."""
    assert table.regime_of("Ł") == "agricultural"
    assert table.name_of("Ł") == "łąki trwałe"
    assert table.get("L") is None


def test_regime_of_an_unknown_symbol_raises(table) -> None:
    """A lookup returning ``None`` invites a caller to treat it as "no regime"."""
    with pytest.raises(UnknownRegisterClass) as caught:
        table.regime_of("Xx")
    assert "Xx" in str(caught.value)
