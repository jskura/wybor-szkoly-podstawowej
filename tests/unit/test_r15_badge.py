"""S15 — the farmland badge, the unknown class, and the silence of `none`.

FR-66 and V61. The badge states a possibility, names its act and its holder from
the citation record, and points at a notary. It never states a certainty, and it
never reassures.

Three rules carry most of the value here:

* an unknown class gets no badge **and** no reassurance (`19` §2.2);
* a `none` row makes no statement about acquisition at all;
* every number the badge renders comes from the citation record, and the badge
  renders none today because nobody has read the act (O40).
"""

from __future__ import annotations

import datetime
import hashlib
import pathlib
import unicodedata

import pytest

from dzialki.config import load_params
from dzialki.legal import (
    BADGE_NOTARY_LINE,
    NOTARY_LINE,
    NOTARY_LINE_PREFIX,
    PREEMPTION_TEMPLATES,
    RESTRICTION_TEMPLATE,
    TITLE_TEMPLATES,
    UNKNOWN_CLASS_STATEMENT,
    UNRECOGNISED_CLASS_ALARM,
    PurchaseRestrictionRenderer,
    load_citations,
    load_register_classes,
)
from dzialki.render import Formatter

pytestmark = [pytest.mark.unit]

AS_OF = datetime.date(2026, 6, 1)
AREA_M2 = 3400

AGRICULTURAL_SYMBOLS = ("R", "S", "Ł", "Ps", "Br", "Wsr", "W", "Lzr")
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
UNKNOWN_INPUTS = (None, "", "   ", "Xx")

# V61's falsifier is a plot *presented* as unrestricted.
REASSURANCE_TOKENS = (
    "brak ograniczeń",
    "bez ograniczeń",
    "można kupić",
    "nie dotyczy",
    "nieograniczony",
    "dowolny nabywca",
)
# The determination is the notary's, so the badge never states one.
CERTAINTY_TOKENS = (
    "nie możesz kupić",
    "zakaz nabycia",
    "na pewno",
    "wymagana zgoda",
    "nie kupisz",
)

# The test plan §5.2 hashes the ratified farmland copy, §5.5 the forest copy.
EXPECTED_HASHES = {
    "title_agricultural": (
        "f6ddd11d7ad020f1509361e52677b12fa936e6f1c4cd645759e02bda287dcc57"
    ),
    "title_forest": (
        "526e84e072ae623ee43f0a94b901d9ebbf47698314376c3c9abe9d66c17add17"
    ),
    "restriction": ("6aedb1a06c033cc2811427a3d51a983b86217b462d3fa070cf40fca726d3100a"),
    "preemption_agricultural": (
        "554773c115e5c160143e377a7610bccb7d1ee47808113ae1b9e95dddaf492fd3"
    ),
    "preemption_forest": (
        "ee6c0a0abe1d49e4bfaaebd7af0742278602b83cff010a4ad94da893ecb3c7b4"
    ),
    "notary": "796cb396bf0f8f2a7430520e01d408ea0bc9ad122c39d432a86d498edcd82e8d",
    "unknown_statement": (
        "44a2cf6f752eef52f84c0768b9ee4311a43381a11389e79a6d41da1ce94186ce"
    ),
}

# The rendered farmland lines 2 and 3, which `19` §2.2 ratified.
RENDERED_HASHES = {
    "restriction": ("6dd9a9476cab18c009b6004531c9ca45739d46ffd264d68f0dc1cbf22b1d6c7a"),
    "preemption": ("f20864d3363a915dae82c08bb2dc0e8f436340dfd6f139aec40329520752a73f"),
}


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@pytest.fixture()
def renderer(repo_root: pathlib.Path) -> PurchaseRestrictionRenderer:
    """The renderer the application builds, from the committed records."""
    params = load_params(repo_root / "config" / "params.yml")
    return PurchaseRestrictionRenderer(
        table=load_register_classes(repo_root / "config" / "register_classes.yml"),
        citations=load_citations(repo_root / "config" / "legal_citations.yml"),
        formatter=Formatter(thousands_sep=params.surface.thousands_sep),
    )


def section(renderer, register_class, area_m2=AREA_M2):
    return renderer.section(
        register_class=register_class,
        area_m2=area_m2,
        area_source="register",
        as_of=AS_OF,
    )


# --- the copy, by hash -----------------------------------------------------


def test_every_declared_constant_matches_its_documented_hash() -> None:
    """One constant per line, hashed, so an edit shows up as a changed hash."""
    assert (
        digest(TITLE_TEMPLATES["agricultural"]) == EXPECTED_HASHES["title_agricultural"]
    )
    assert digest(TITLE_TEMPLATES["forest"]) == EXPECTED_HASHES["title_forest"]
    assert digest(RESTRICTION_TEMPLATE) == EXPECTED_HASHES["restriction"]
    assert (
        digest(PREEMPTION_TEMPLATES["agricultural"])
        == EXPECTED_HASHES["preemption_agricultural"]
    )
    assert (
        digest(PREEMPTION_TEMPLATES["forest"]) == EXPECTED_HASHES["preemption_forest"]
    )
    assert digest(BADGE_NOTARY_LINE) == EXPECTED_HASHES["notary"]
    assert digest(UNKNOWN_CLASS_STATEMENT) == EXPECTED_HASHES["unknown_statement"]


def test_every_declared_constant_is_nfc_and_uses_the_documented_code_points() -> None:
    """§4.3's homoglyph guard. A Cyrillic `а` would pass a reading and fail here."""
    for text in (*TITLE_TEMPLATES.values(), RESTRICTION_TEMPLATE, BADGE_NOTARY_LINE):
        assert unicodedata.normalize("NFC", text) == text
    for text in TITLE_TEMPLATES.values():
        assert text[0] == "⚠"
        assert "—" in text
        assert "–" not in text


def test_the_notary_line_is_one_object(renderer) -> None:
    """Identity, not equality. The forest badge reuses this same object (V63)."""
    farmland = section(renderer, "R").badge
    assert farmland.lines[3] is NOTARY_LINE
    assert NOTARY_LINE == NOTARY_LINE_PREFIX + BADGE_NOTARY_LINE


# --- the farmland badge ----------------------------------------------------


def test_the_farmland_badge_renders_all_four_lines(renderer) -> None:
    badge = section(renderer, "R").badge
    assert badge.lines == (
        "⚠ Grunt rolny — 3\u00a0400 m²",
        "Możliwe ograniczenia w nabyciu (ustawa o kształtowaniu ustroju rolnego)",
        "Możliwe prawo pierwokupu KOWR",
        "→ sprawdź u notariusza przed ofertą",
    )
    assert badge.regime == "agricultural"


def test_the_rendered_farmland_lines_match_the_ratified_hashes(renderer) -> None:
    """`19` §2.2 ratified lines 2 and 3. The record must render them exactly."""
    badge = section(renderer, "R").badge
    assert digest(badge.lines[1]) == RENDERED_HASHES["restriction"]
    assert digest(badge.lines[2]) == RENDERED_HASHES["preemption"]


@pytest.mark.parametrize("symbol", AGRICULTURAL_SYMBOLS)
def test_every_agricultural_class_produces_the_farmland_badge(renderer, symbol) -> None:
    badge = section(renderer, symbol).badge
    assert badge.regime == "agricultural"
    assert badge.lines == section(renderer, "R").badge.lines


def test_the_badge_names_the_holder_the_record_carries(renderer, repo_root) -> None:
    """Two places hold the name, so a test holds them together."""
    citations = load_citations(repo_root / "config" / "legal_citations.yml")
    entry = citations.for_regime("agricultural")
    badge = section(renderer, "R").badge
    assert entry.preemption_holder == "KOWR"
    assert badge.lines[2] == "Możliwe prawo pierwokupu " + entry.preemption_holder
    assert badge.lines[1] == "Możliwe ograniczenia w nabyciu (" + entry.act_title + ")"


def test_the_badge_states_possibility_never_certainty(renderer) -> None:
    text = section(renderer, "R").text.lower()
    assert "możliwe ograniczenia" in text
    assert "możliwe prawo pierwokupu" in text
    assert [token for token in CERTAINTY_TOKENS if token in text] == []


def test_the_badge_directs_to_a_notary(renderer) -> None:
    assert BADGE_NOTARY_LINE in section(renderer, "R").text


def test_the_badge_shows_the_area_and_its_source(renderer) -> None:
    """Rule 7 and V28. The figure carries where it came from and when."""
    badge = section(renderer, "R").badge
    assert badge.area_m2 == AREA_M2
    assert badge.area_source == "register"
    assert badge.as_of == AS_OF


def test_the_badge_follows_the_register_not_the_advert(renderer) -> None:
    """FR-48, V25. The advert's word is not evidence."""
    building_advert = renderer.section(
        register_class="R",
        area_m2=AREA_M2,
        area_source="register",
        as_of=AS_OF,
        advert_claim="działka budowlana",
    )
    farm_advert = renderer.section(
        register_class="B",
        area_m2=AREA_M2,
        area_source="register",
        as_of=AS_OF,
        advert_claim="rolna",
    )
    assert building_advert.badge.regime == "agricultural"
    assert farm_advert.badge is None


def test_the_badge_renders_at_both_ends_of_the_d48_band(renderer) -> None:
    """2 000 m² and 4 000 m² differ in legal consequence and not in copy.

    The badge makes no numeric claim, so its text must not vary with the size.
    """
    small = section(renderer, "R", area_m2=2000).badge
    large = section(renderer, "R", area_m2=4000).badge
    assert small.lines[0] == "⚠ Grunt rolny — 2\u00a0000 m²"
    assert large.lines[0] == "⚠ Grunt rolny — 4\u00a0000 m²"
    assert small.lines[1:] == large.lines[1:]


# --- the degraded form, which is the only form that ships today ------------


def test_the_badge_makes_no_threshold_claim_while_the_act_is_unread(
    renderer,
) -> None:
    """No digit outside the area figure. Every claim carries `verified_at: null`."""
    badge = section(renderer, "R").badge
    assert badge.degraded is True
    digits = [
        character
        for line in badge.lines[1:]
        for character in line
        if character.isdigit()
    ]
    assert digits == []
    assert [line for line in badge.lines if "ha" in line.split()] == []


def test_the_degraded_badge_keeps_its_warning(renderer) -> None:
    """A degraded badge loses the threshold sentence and nothing else."""
    badge = section(renderer, "R").badge
    assert len(badge.lines) == 4
    assert badge.lines[3] == NOTARY_LINE_PREFIX + BADGE_NOTARY_LINE


# --- the unknown class -----------------------------------------------------


@pytest.mark.parametrize("value", UNKNOWN_INPUTS)
def test_an_unknown_class_produces_no_badge(renderer, value) -> None:
    assert section(renderer, value).badge is None


@pytest.mark.parametrize("value", UNKNOWN_INPUTS)
def test_an_unknown_class_says_so(renderer, value) -> None:
    assert section(renderer, value).statement == UNKNOWN_CLASS_STATEMENT
    assert UNKNOWN_CLASS_STATEMENT in section(renderer, value).text


@pytest.mark.parametrize("value", UNKNOWN_INPUTS)
def test_an_unknown_class_page_carries_no_reassurance(renderer, value) -> None:
    text = section(renderer, value).text.lower()
    assert [token for token in REASSURANCE_TOKENS if token in text] == []


def test_an_unrecognised_symbol_alarms_and_a_missing_one_does_not(renderer) -> None:
    """FR-49. A missing value is a known state; an unrecognised one is a surprise."""
    alarm = section(renderer, "Xx").alarm
    assert alarm is not None
    assert alarm.code == UNRECOGNISED_CLASS_ALARM
    assert alarm.symbol == "Xx"
    assert [
        value
        for value in (None, "", "   ")
        if section(renderer, value).alarm is not None
    ] == []


def test_the_alarm_stays_out_of_the_page(renderer) -> None:
    """The alarm is addressed to the operator, never to the buyer."""
    assert "Xx" not in section(renderer, "Xx").text


# --- the `none` regime says nothing ----------------------------------------


@pytest.mark.parametrize("symbol", NONE_SYMBOLS)
def test_a_none_row_makes_no_statement_about_acquisition(renderer, symbol) -> None:
    """Absence of a badge is not a statement, and must not be dressed as one."""
    found = section(renderer, symbol)
    assert found.badge is None
    assert found.statement is None
    assert found.text == ""


# --- the separator ---------------------------------------------------------


def test_the_area_uses_the_ratified_separator(renderer, repo_root) -> None:
    """D125. The character lives in `config/params.yml` and nowhere else."""
    params = load_params(repo_root / "config" / "params.yml")
    badge = section(renderer, "R").badge
    assert params.surface.thousands_sep == "\u00a0"
    assert badge.lines[0] == f"⚠ Grunt rolny — 3{params.surface.thousands_sep}400 m²"
    assert "3 400" not in badge.lines[0]
    assert "3,400" not in badge.lines[0]
    assert "3.400" not in badge.lines[0]


def test_the_separator_is_read_from_the_file_not_from_the_module(
    repo_root: pathlib.Path,
) -> None:
    """Change the file, and the rendered number changes with it."""
    table = load_register_classes(repo_root / "config" / "register_classes.yml")
    citations = load_citations(repo_root / "config" / "legal_citations.yml")
    other = PurchaseRestrictionRenderer(
        table=table, citations=citations, formatter=Formatter(thousands_sep="_")
    )
    badge = other.section(
        register_class="R", area_m2=AREA_M2, area_source="register", as_of=AS_OF
    ).badge
    assert badge.lines[0] == "⚠ Grunt rolny — 3_400 m²"
