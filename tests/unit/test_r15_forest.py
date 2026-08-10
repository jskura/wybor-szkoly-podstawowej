"""S15 — the forest badge, which refuses to render today.

FR-73, V63 and D122. `19` §2a marks all three forest claims `‡` unverified, so
the act title and the pre-emption holder rest on nobody's reading. A badge that
names the wrong authority is worse than no badge, because the reader telephones
the wrong office and believes the matter checked.

The record therefore refuses to serve the forest regime, the same way the unit
map refuses to serve unverified entries. The tests below prove the refusal, and
then prove the badge itself against a fixture record that declares the claims
ratified. When the owner reads the act, one flag in the committed file releases
the badge and every test here already covers it.
"""

from __future__ import annotations

import datetime
import hashlib
import pathlib

import pytest
import yaml

from dzialki.config import load_params
from dzialki.legal import (
    BADGE_NOTARY_LINE,
    NOTARY_LINE,
    BadgeCopyUnratified,
    CitationRecordError,
    PurchaseRestrictionRenderer,
    ThresholdCopyUnwritten,
    load_citations,
    load_register_classes,
)
from dzialki.render import Formatter

pytestmark = [pytest.mark.unit]

AS_OF = datetime.date(2026, 6, 1)
AREA_M2 = 3400
CERTAINTY_TOKENS = (
    "nie możesz kupić",
    "zakaz nabycia",
    "na pewno",
    "wymagana zgoda",
    "nie kupisz",
)
EXPIRY_KEYS = ("expires_at", "max_age_days", "citation_max_age_days")


def committed(repo_root: pathlib.Path) -> pathlib.Path:
    return repo_root / "config" / "legal_citations.yml"


def rewritten(repo_root: pathlib.Path, tmp_path: pathlib.Path, edit) -> pathlib.Path:
    """The committed record with one edit, written to a temporary file."""
    raw = yaml.safe_load(committed(repo_root).read_text(encoding="utf-8"))
    edit(raw)
    target = tmp_path / "legal_citations.yml"
    target.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    return target


def ratify_forest(raw: dict) -> None:
    """What the owner does after reading the act (D122)."""
    for entry in raw["regimes"]:
        if entry["regime"] == "forest":
            entry["identity_ratified"] = True


def build(repo_root: pathlib.Path, citations_path: pathlib.Path):
    params = load_params(repo_root / "config" / "params.yml")
    return PurchaseRestrictionRenderer(
        table=load_register_classes(repo_root / "config" / "register_classes.yml"),
        citations=load_citations(citations_path),
        formatter=Formatter(thousands_sep=params.surface.thousands_sep),
    )


@pytest.fixture()
def ratified(repo_root: pathlib.Path, tmp_path: pathlib.Path):
    """A renderer whose forest claims the owner has ratified."""
    return build(repo_root, rewritten(repo_root, tmp_path, ratify_forest))


@pytest.fixture()
def shipped(repo_root: pathlib.Path):
    """The renderer the application builds today."""
    return build(repo_root, committed(repo_root))


def forest_badge(renderer):
    return renderer.section(
        register_class="Ls",
        area_m2=AREA_M2,
        area_source="register",
        as_of=AS_OF,
    ).badge


# --- the refusal -----------------------------------------------------------


def test_the_committed_record_refuses_the_forest_regime(
    repo_root: pathlib.Path,
) -> None:
    record = load_citations(committed(repo_root))
    with pytest.raises(BadgeCopyUnratified) as caught:
        record.for_regime("forest")
    message = str(caught.value)
    assert "forest" in message
    assert "D122" in message
    assert "config/legal_citations.yml" in message


def test_the_forest_badge_refuses_to_render(shipped) -> None:
    """`Ls` is a forest row, and the forest badge stays blocked (D122, doc 23)."""
    with pytest.raises(BadgeCopyUnratified):
        forest_badge(shipped)


def test_the_farmland_regime_is_ratified_and_renders(repo_root: pathlib.Path) -> None:
    """The contrast that makes the refusal a decision rather than a defect.

    `19` §2.2 carries the farmland copy and D51 ratified it. `19` §2a carries
    the forest copy and nobody has ratified it.
    """
    record = load_citations(committed(repo_root))
    assert record.is_ratified("agricultural") is True
    assert record.is_ratified("forest") is False
    assert record.for_regime("agricultural").act_title == (
        "ustawa o kształtowaniu ustroju rolnego"
    )


def test_every_forest_claim_is_marked_unverified(repo_root: pathlib.Path) -> None:
    """`verified_at: null` on all three, each with a note saying the act is unread."""
    record = load_citations(committed(repo_root))
    claims = record.claims("forest")
    assert tuple(claim.claim_id for claim in claims) == (
        "las_act_title",
        "las_preemption_holder",
        "las_preemption_scope",
    )
    assert [claim.claim_id for claim in claims if claim.verified_at is not None] == []
    assert [
        claim.claim_id for claim in claims if "‡" not in claim.verification_note
    ] == []


def test_no_claim_invents_an_isap_identifier(repo_root: pathlib.Path) -> None:
    """A remembered identifier would look exactly like a checked one."""
    record = load_citations(committed(repo_root))
    for regime in record.regimes:
        for claim in record.claims(regime):
            assert claim.consolidated_text_id == "⟨RECORD⟩"
            assert claim.dziennik_ustaw_reference == "⟨RECORD⟩"
            assert claim.text_as_of is None


def test_the_record_declares_no_expiry(repo_root: pathlib.Path) -> None:
    """D104 removed the clock. A quiet config addition must not bring it back."""
    raw = yaml.safe_load(committed(repo_root).read_text(encoding="utf-8"))

    def keys(node) -> list[str]:
        if isinstance(node, dict):
            return [key for key in node] + [
                found for value in node.values() for found in keys(value)
            ]
        if isinstance(node, list):
            return [found for value in node for found in keys(value)]
        return []

    assert [key for key in keys(raw) if key in EXPIRY_KEYS] == []


def test_an_expiry_key_fails_the_load(
    repo_root: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    """The seeded companion. Without it the scan above could be vacuous."""

    def add_expiry(raw: dict) -> None:
        raw["regimes"][0]["claims"][0]["max_age_days"] = 365

    with pytest.raises(CitationRecordError) as caught:
        load_citations(rewritten(repo_root, tmp_path, add_expiry))
    assert "max_age_days" in str(caught.value)


# --- the badge, once the claims are ratified -------------------------------


def test_the_forest_badge_renders_all_four_lines(ratified) -> None:
    assert forest_badge(ratified).lines == (
        "⚠ Grunt leśny — 3\u00a0400 m²",
        "Możliwe ograniczenia w nabyciu (ustawa o lasach)",
        "Możliwe prawo pierwokupu (Lasy Państwowe)",
        "→ sprawdź u notariusza przed ofertą",
    )


def test_the_forest_badge_carries_the_forest_regime(ratified) -> None:
    assert forest_badge(ratified).regime == "forest"


def test_the_act_and_the_holder_come_from_the_record(
    repo_root: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    """Change the record, and the rendered lines change with it.

    A hardcoded act title passes the render above and fails here. That is the
    whole defence against F16.
    """

    def substitute(raw: dict) -> None:
        ratify_forest(raw)
        for entry in raw["regimes"]:
            if entry["regime"] == "forest":
                entry["act_title"] = "ustawa testowa"
                entry["preemption_holder"] = "Zarząd Testowy"

    renderer = build(repo_root, rewritten(repo_root, tmp_path, substitute))
    assert forest_badge(renderer).lines[1:3] == (
        "Możliwe ograniczenia w nabyciu (ustawa testowa)",
        "Możliwe prawo pierwokupu (Zarząd Testowy)",
    )


def test_the_forest_badge_states_possibility_never_certainty(ratified) -> None:
    lines = forest_badge(ratified).lines
    text = "\n".join(lines).lower()
    assert "możliwe ograniczenia" in text
    assert "możliwe prawo pierwokupu" in text
    assert [token for token in CERTAINTY_TOKENS if token in text] == []


def test_the_forest_badge_directs_to_a_notary(ratified) -> None:
    badge = forest_badge(ratified)
    assert badge.lines[3] is NOTARY_LINE
    assert BADGE_NOTARY_LINE in badge.lines[3]


def test_the_forest_badge_shows_the_area_and_its_source(ratified) -> None:
    badge = forest_badge(ratified)
    assert badge.area_m2 == AREA_M2
    assert badge.area_source == "register"
    assert badge.as_of == AS_OF


def test_the_forest_badge_uses_the_ratified_separator(ratified, repo_root) -> None:
    params = load_params(repo_root / "config" / "params.yml")
    assert forest_badge(ratified).lines[0] == (
        f"⚠ Grunt leśny — 3{params.surface.thousands_sep}400 m²"
    )


def test_the_forest_badge_makes_no_numeric_claim(ratified) -> None:
    """Degraded is the only form either regime may render (O40)."""
    badge = forest_badge(ratified)
    assert badge.degraded is True
    assert [
        character
        for line in badge.lines[1:]
        for character in line
        if character.isdigit()
    ] == []


def test_the_rendered_forest_title_matches_its_hash(ratified) -> None:
    """The test plan §5.5 hashes the template. This hashes what a reader sees,
    separator and all, so a change to either shows up as a changed hash."""
    lines = forest_badge(ratified).lines
    assert hashlib.sha256(lines[0].encode("utf-8")).hexdigest() == (
        "4b3acc2f27e3fa82475ca05e93a030cb0ea5d4ce8c22414a76470f9e82074c39"
    )


# --- a verified threshold has no copy yet ----------------------------------


def test_a_verified_threshold_refuses_to_render_rather_than_invent_copy(
    repo_root: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    """No document states the sentence a verified threshold would render.

    Rendering nothing would drop a fact the owner had just checked. Inventing
    the sentence would write legal copy nobody ratified. The badge refuses and
    says which claim did it.
    """

    def verify_threshold(raw: dict) -> None:
        for entry in raw["regimes"]:
            if entry["regime"] == "agricultural":
                claim = entry["claims"][0]
                claim["verified_at"] = "2026-05-04"
                claim["verified_by"] = "owner"
                claim["text_as_of"] = "2026-04-30"

    renderer = build(repo_root, rewritten(repo_root, tmp_path, verify_threshold))
    with pytest.raises(ThresholdCopyUnwritten) as caught:
        renderer.section(
            register_class="R",
            area_m2=AREA_M2,
            area_source="register",
            as_of=AS_OF,
        )
    assert "ukur_consent_threshold_ha" in str(caught.value)


def test_a_verification_older_than_the_text_fails_the_load(
    repo_root: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    """X5. A verification against an older text proves nothing about this one."""

    def backdate(raw: dict) -> None:
        claim = raw["regimes"][0]["claims"][0]
        claim["verified_at"] = "2026-03-01"
        claim["text_as_of"] = "2026-04-30"

    with pytest.raises(CitationRecordError) as caught:
        load_citations(rewritten(repo_root, tmp_path, backdate))
    assert "ukur_consent_threshold_ha" in str(caught.value)
