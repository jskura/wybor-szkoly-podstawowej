"""S15 — the re-verification prompt (FR-74, V64, D104, D105, D116).

D104 removed the expiry, and on its own that leaves nothing to tell us the law
moved. D105 supplies the missing half: the first badge of a regime in a session
asks the operator to check that regime's act.

The prompt is a task addressed to the operator. It is not a warning to the buyer
about the plot, and it never gates the badge — a gate would rebuild the expiry
D104 removed.

D116 makes it once per **regime**, not once per session. The two acts change
independently, so a check on one cannot stand for the other.
"""

from __future__ import annotations

import datetime
import hashlib
import pathlib

import pytest
import yaml

from dzialki.config import load_params
from dzialki.legal import (
    NEVER_VERIFIED,
    REVERIFY_PROMPT_TEMPLATE,
    PurchaseRestrictionRenderer,
    ReverificationSession,
    load_citations,
    load_register_classes,
)
from dzialki.render import Formatter

pytestmark = [pytest.mark.unit]

AS_OF = datetime.date(2026, 6, 1)
AREA_M2 = 3400
PROMPT_TEMPLATE_HASH = (
    "12ae7b7d7f06c199a29c6de360443e90b7e08ce244fb0cb0f946eff58acfb9af"
)


def ratified_record(repo_root: pathlib.Path, tmp_path: pathlib.Path) -> pathlib.Path:
    """Both regimes ratified. The forest prompt cannot fire while `Ls` is blocked."""
    raw = yaml.safe_load(
        (repo_root / "config" / "legal_citations.yml").read_text(encoding="utf-8")
    )
    for entry in raw["regimes"]:
        entry["identity_ratified"] = True
    target = tmp_path / "legal_citations.yml"
    target.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    return target


@pytest.fixture()
def formatter(repo_root: pathlib.Path) -> Formatter:
    params = load_params(repo_root / "config" / "params.yml")
    return Formatter(thousands_sep=params.surface.thousands_sep)


@pytest.fixture()
def renderer(repo_root: pathlib.Path, tmp_path: pathlib.Path, formatter: Formatter):
    return PurchaseRestrictionRenderer(
        table=load_register_classes(repo_root / "config" / "register_classes.yml"),
        citations=load_citations(ratified_record(repo_root, tmp_path)),
        formatter=formatter,
    )


def section(renderer, register_class, session=None):
    return renderer.section(
        register_class=register_class,
        area_m2=AREA_M2,
        area_source="register",
        as_of=AS_OF,
        session=session,
    )


def prompts(renderer, session, *classes) -> list[str]:
    return [
        found.prompt
        for found in (section(renderer, value, session) for value in classes)
        if found.prompt is not None
    ]


# --- the constant ----------------------------------------------------------


def test_the_prompt_text_comes_from_one_declared_constant() -> None:
    assert (
        hashlib.sha256(REVERIFY_PROMPT_TEMPLATE.encode("utf-8")).hexdigest()
        == PROMPT_TEMPLATE_HASH
    )
    assert NEVER_VERIFIED == "nigdy"


# --- once per regime, per session ------------------------------------------


def test_the_first_badge_in_a_session_prompts(renderer, formatter) -> None:
    assert len(prompts(renderer, ReverificationSession(formatter=formatter), "R")) == 1


def test_two_farmland_badges_in_one_session_show_one_prompt(
    renderer, formatter
) -> None:
    """A prompt on every badge trains the reader to dismiss it."""
    session = ReverificationSession(formatter=formatter)
    assert len(prompts(renderer, session, "R", "S")) == 1


def test_a_second_regime_in_the_same_session_shows_its_own_prompt(
    renderer, formatter
) -> None:
    """D116. Two acts, two prompts, each naming its own act."""
    session = ReverificationSession(formatter=formatter)
    shown = prompts(renderer, session, "R", "Ls")
    assert len(shown) == 2
    assert "ustawa o kształtowaniu ustroju rolnego" in shown[0]
    assert "ustawa o lasach" in shown[1]
    assert "ustawa o lasach" not in shown[0]
    assert "kształtowaniu ustroju rolnego" not in shown[1]


def test_the_forest_prompt_names_the_forest_act(renderer, formatter) -> None:
    """F16 wearing a different hat: a prompt that always names one act."""
    session = ReverificationSession(formatter=formatter)
    shown = prompts(renderer, session, "Ls")
    assert shown == [
        (
            "Przepisy mogły się zmienić — sprawdź ustawa o lasach; "
            "ostatnia weryfikacja nigdy"
        )
    ]


def test_a_new_session_prompts_again(renderer, formatter) -> None:
    """The counter lives in the session, never in a module global."""
    first = prompts(renderer, ReverificationSession(formatter=formatter), "R")
    second = prompts(renderer, ReverificationSession(formatter=formatter), "R")
    assert len(first) == 1
    assert first == second


def test_a_session_with_no_badge_never_prompts(renderer, formatter) -> None:
    """D105's whole economy: no badge, no standing cost."""
    session = ReverificationSession(formatter=formatter)
    assert prompts(renderer, session, "B", "dr", "Xx", None) == []


def test_the_prompt_names_the_act_and_the_last_verification_date(
    renderer, formatter
) -> None:
    """`verified_at: null` renders `nigdy`, never an empty slot."""
    session = ReverificationSession(formatter=formatter)
    shown = prompts(renderer, session, "R")
    assert shown == [
        (
            "Przepisy mogły się zmienić — sprawdź ustawa o kształtowaniu ustroju "
            "rolnego; ostatnia weryfikacja nigdy"
        )
    ]


def test_a_verified_date_reaches_the_prompt_and_gates_nothing(
    repo_root: pathlib.Path, tmp_path: pathlib.Path, formatter: Formatter
) -> None:
    """D104. A 2019 date renders and fails nothing."""
    raw = yaml.safe_load(
        (repo_root / "config" / "legal_citations.yml").read_text(encoding="utf-8")
    )
    for entry in raw["regimes"]:
        if entry["regime"] == "agricultural":
            for claim in entry["claims"]:
                claim["verified_at"] = "2019-01-01"
                claim["verified_by"] = "owner"
                claim["kind"] = "scope"
    target = tmp_path / "aged.yml"
    target.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")

    renderer = PurchaseRestrictionRenderer(
        table=load_register_classes(repo_root / "config" / "register_classes.yml"),
        citations=load_citations(target),
        formatter=formatter,
    )
    session = ReverificationSession(formatter=formatter)
    found = section(renderer, "R", session)
    assert found.badge is not None
    assert found.prompt is not None
    assert found.prompt.endswith("ostatnia weryfikacja 01.01.2019")


# --- the prompt is never a gate --------------------------------------------


def test_the_prompt_never_blocks_the_badge(renderer, formatter) -> None:
    """Rendered with a session, without one, and after the prompt is spent."""
    session = ReverificationSession(formatter=formatter)
    with_session = section(renderer, "R", session).badge
    spent = section(renderer, "R", session).badge
    without = section(renderer, "R").badge
    assert with_session.lines == without.lines
    assert spent.lines == without.lines


# --- the seed --------------------------------------------------------------


class ForgetfulSession(ReverificationSession):
    """Wired wrong on purpose: it prompts on every badge."""

    def prompt_for(self, citation) -> str | None:
        self._prompted = set()
        return super().prompt_for(citation)


def test_seeded_per_badge_prompt_is_caught(renderer, formatter) -> None:
    """Without this, a counter reset would pass the once-per-session test."""
    session = ForgetfulSession(formatter=formatter)
    assert len(prompts(renderer, session, "R", "S")) == 2
