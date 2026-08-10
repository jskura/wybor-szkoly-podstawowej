"""S15 — V63: the two badges never cross.

A missing badge is a gap. A badge naming the wrong act and the wrong authority is
a false statement that looks exactly as authoritative as a true one (F16). These
tests therefore outrank the presence tests.

Every scan here is a negative assertion, and a negative assertion passes
trivially against a page that renders nothing. `test_seeded_crossed_badge_is_caught`
wires a renderer wrong on purpose and proves each scan finds it.

The forest badge is blocked in the committed record (D122), so these tests run
against a fixture record that ratifies it. Scanning the blocked badge would prove
nothing at all.
"""

from __future__ import annotations

import datetime
import pathlib

import pytest
import yaml

from dzialki.config import load_params
from dzialki.legal import (
    PurchaseRestrictionRenderer,
    load_citations,
    load_register_classes,
)
from dzialki.render import Formatter

pytestmark = [pytest.mark.unit]

AS_OF = datetime.date(2026, 6, 1)
AREA_M2 = 3400

ALL_SYMBOLS = (
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
UNKNOWN_INPUTS = (None, "", "   ", "Xx")
NONE_SYMBOLS = (
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

# The four strings that must never cross, lower-cased for the scan.
FARMLAND_MARKS = ("kształtowaniu ustroju rolnego", "kowr")
FOREST_MARKS = ("o lasach", "lasy państwowe")

REASSURANCE_TOKENS = (
    "brak ograniczeń",
    "bez ograniczeń",
    "można kupić",
    "nie dotyczy",
    "nieograniczony",
    "dowolny nabywca",
)


def foreign_marks(text: str, regime: str) -> list[str]:
    """The other regime's act title and holder, found in this page."""
    lowered = text.lower()
    marks = FOREST_MARKS if regime == "agricultural" else FARMLAND_MARKS
    return [mark for mark in marks if mark in lowered]


def ratified_record(repo_root: pathlib.Path, tmp_path: pathlib.Path) -> pathlib.Path:
    raw = yaml.safe_load(
        (repo_root / "config" / "legal_citations.yml").read_text(encoding="utf-8")
    )
    for entry in raw["regimes"]:
        entry["identity_ratified"] = True
    target = tmp_path / "legal_citations.yml"
    target.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    return target


def build(repo_root, citations_path, cls=PurchaseRestrictionRenderer):
    params = load_params(repo_root / "config" / "params.yml")
    return cls(
        table=load_register_classes(repo_root / "config" / "register_classes.yml"),
        citations=load_citations(citations_path),
        formatter=Formatter(thousands_sep=params.surface.thousands_sep),
    )


class CrossedRenderer(PurchaseRestrictionRenderer):
    """Wired wrong on purpose: every badge reads the agricultural entry.

    This is the seed. It renders a forest title over the farmland act and the
    farmland holder, which is F16 exactly.
    """

    def citation_for(self, regime: str):
        return super().citation_for("agricultural")


@pytest.fixture()
def renderer(repo_root: pathlib.Path, tmp_path: pathlib.Path):
    return build(repo_root, ratified_record(repo_root, tmp_path))


@pytest.fixture()
def crossed(repo_root: pathlib.Path, tmp_path: pathlib.Path):
    return build(repo_root, ratified_record(repo_root, tmp_path), cls=CrossedRenderer)


def section(renderer, register_class):
    return renderer.section(
        register_class=register_class,
        area_m2=AREA_M2,
        area_source="register",
        as_of=AS_OF,
    )


# --- the crossings ---------------------------------------------------------


def test_the_forest_page_names_no_farmland_act_or_holder(renderer) -> None:
    found = section(renderer, "Ls")
    assert found.badge.regime == "forest"
    assert foreign_marks(found.text, "forest") == []


@pytest.mark.parametrize("symbol", ("R", "S", "Ł", "Ps", "Br", "Wsr", "W", "Lzr"))
def test_a_farmland_page_names_no_forest_act_or_holder(renderer, symbol) -> None:
    found = section(renderer, symbol)
    assert found.badge.regime == "agricultural"
    assert foreign_marks(found.text, "agricultural") == []


@pytest.mark.parametrize("value", (*ALL_SYMBOLS, *UNKNOWN_INPUTS))
def test_at_most_one_badge_appears_on_a_page(renderer, value) -> None:
    """One register class, one regime, one badge."""
    found = section(renderer, value)
    assert found.text.count("⚠") == (0 if found.badge is None else 1)
    assert found.text.count("Możliwe prawo pierwokupu") == (
        0 if found.badge is None else 1
    )


@pytest.mark.parametrize("value", (*ALL_SYMBOLS, *UNKNOWN_INPUTS))
def test_no_class_produces_a_reassurance_token(renderer, value) -> None:
    """28 renders, zero reassurances. A `none` row promises nothing either."""
    text = section(renderer, value).text.lower()
    assert [token for token in REASSURANCE_TOKENS if token in text] == []


@pytest.mark.parametrize("symbol", NONE_SYMBOLS)
def test_a_none_row_renders_neither_badge(renderer, symbol) -> None:
    found = section(renderer, symbol)
    assert found.badge is None
    assert found.text == ""


def test_swapping_the_regime_swaps_the_whole_badge(renderer) -> None:
    """Same area, same date. The title, the act and the holder all differ.

    Only the notary line is shared, and it is shared as one object.
    """
    forest = section(renderer, "Ls").badge
    farmland = section(renderer, "R").badge
    assert forest.lines[0] != farmland.lines[0]
    assert forest.lines[1] != farmland.lines[1]
    assert forest.lines[2] != farmland.lines[2]
    assert forest.lines[3] == farmland.lines[3]
    assert forest.lines[3] is farmland.lines[3]


def test_the_badge_never_filters_a_result_set(renderer) -> None:
    """D51 chose the badge over exclusion, for both regimes."""
    classes = ("R", "Ls", "B", "Xx")
    sections = [section(renderer, value) for value in classes]
    assert len(sections) == len(classes)
    assert [found.badge is not None for found in sections] == [
        True,
        True,
        False,
        False,
    ]


# --- the seed --------------------------------------------------------------


def test_seeded_crossed_badge_is_caught(crossed) -> None:
    """The scans above run against a renderer wired to the wrong record.

    Without this, every negative assertion could pass against an empty page.
    """
    found = section(crossed, "Ls")
    assert found.badge.lines[0] == "⚠ Grunt leśny — 3\u00a0400 m²"
    assert foreign_marks(found.text, "forest") == [
        "kształtowaniu ustroju rolnego",
        "kowr",
    ]


def test_the_seeded_renderer_also_breaks_the_swap_test(crossed) -> None:
    """The crossed renderer varies the title and keeps the farmland holder."""
    forest = section(crossed, "Ls").badge
    farmland = section(crossed, "R").badge
    assert forest.lines[0] != farmland.lines[0]
    assert "KOWR" in forest.lines[2]
    assert "KOWR" in farmland.lines[2]
