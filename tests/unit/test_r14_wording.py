"""R14 — the verdict wording, and V66's two road wordings.

`likely` is the dangerous answer. It is the one that would make somebody spend
money, so it carries the heaviest warning, not the lightest. The disclaimer is
one constant and one object, and the byte comparison below is what stops anyone
softening one copy of it later.

V66 adds the second rule. A `likely` verdict resting on the D114 proxy must read
differently from one resting on confirmed ownership, and the two wordings are
asserted unequal by hash so neither can drift into the other.

**The proxy copy is not ratified.** O39 is open: nobody has written the Polish
for it. The strings in `wording.py` are a proposal, and the hashes here make an
edit visible as a changed hash instead of a silent rewrite.
"""

from __future__ import annotations

import hashlib
import unicodedata

import pytest

pytestmark = [pytest.mark.unit]

# The two ratified strings, from `19` §1.2 by way of the test plan §4.1. The
# hashes are of the UTF-8 bytes in NFC, with U+2014 EM DASH and U+0020 around it.
DISCLAIMER_SHA256 = "fa229e39d1be60a4761d4b3997e0063602d99003062ca570b2ce07a15a537d5a"
UNLIKELY_SHA256 = "42683c4e1f3d9c712e5529866a461830d5dfb774d9bd55b49acd13285daae88f"

VERDICT_EVIDENCE = {
    "checked_at": "2026-08-01",
    "radius_m": 100,
    "distance_m": 30.0,
    "neighbour_count": 1,
    "source": "egib",
    "as_of": "2026-08-08",
}


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def render(verdict: str, *, reason_code: str = "good_neighbour_satisfied", **extra):
    from dzialki.enrich.wz.wording import render_feasibility

    payload = {**VERDICT_EVIDENCE, **extra}
    return render_feasibility(verdict=verdict, reason_code=reason_code, **payload)


# --- the ratified constants ----------------------------------------------


def test_the_disclaimer_is_the_ratified_string(repo_root) -> None:
    from dzialki.enrich.wz.wording import WZ_DISCLAIMER

    assert WZ_DISCLAIMER == "wstępna ocena — nie jest to gwarancja wydania WZ"
    assert len(WZ_DISCLAIMER) == 48
    assert len(WZ_DISCLAIMER.encode("utf-8")) == 51
    assert digest(WZ_DISCLAIMER) == DISCLAIMER_SHA256


def test_the_unlikely_template_is_the_ratified_string() -> None:
    from dzialki.enrich.wz.wording import WZ_UNLIKELY_TEMPLATE

    assert (
        WZ_UNLIKELY_TEMPLATE
        == "brak spełnienia warunku dobrego sąsiedztwa w promieniu {radius} m"
    )
    assert digest(WZ_UNLIKELY_TEMPLATE) == UNLIKELY_SHA256


def test_the_declared_characters_are_the_ones_written() -> None:
    """The realistic way this erodes is a typographic fix, not a deletion.

    An en dash, a hyphen, a no-break space or a decomposed ogonek all render
    identically and hash differently.
    """
    from dzialki.enrich.wz.wording import WZ_DISCLAIMER

    assert unicodedata.normalize("NFC", WZ_DISCLAIMER) == WZ_DISCLAIMER
    assert "—" in WZ_DISCLAIMER
    assert not any(char in WZ_DISCLAIMER for char in ("-", "–", " ", "−"))


# --- every verdict carries the same disclaimer ---------------------------


@pytest.mark.parametrize(
    "verdict,reason_code",
    [
        ("likely", "good_neighbour_satisfied"),
        ("uncertain", "dedesignation_required"),
        ("unlikely", "no_neighbour_within_radius"),
        ("unknown", "building_data_unavailable"),
        ("unknown", "coverage_unproven"),
        ("unknown", "coverage_record_stale"),
        ("unknown", "building_query_failed"),
    ],
)
def test_every_verdict_renders_with_the_disclaimer(
    verdict: str, reason_code: str
) -> None:
    from dzialki.enrich.wz.wording import WZ_DISCLAIMER

    rendered = render(verdict, reason_code=reason_code)
    assert rendered.disclaimer is WZ_DISCLAIMER
    assert WZ_DISCLAIMER in rendered.lines


def test_the_likely_disclaimer_is_byte_identical_to_the_unlikely_one() -> None:
    """Bytes, not strings. Two strings equal under `==` can differ in encoded
    form after a normalisation pass, and two visually identical strings can
    differ in bytes."""
    from dzialki.enrich.wz.wording import WZ_DISCLAIMER

    optimistic = render("likely").disclaimer
    pessimistic = render(
        "unlikely", reason_code="no_neighbour_within_radius"
    ).disclaimer

    assert optimistic.encode("utf-8") == pessimistic.encode("utf-8")
    assert digest(optimistic) == DISCLAIMER_SHA256
    assert optimistic is WZ_DISCLAIMER


def test_likely_is_not_rendered_with_affirmative_wording() -> None:
    """The forbidden set is scanned on every line except the disclaimer.

    The test plan lists `gwarancja wydania` among the forbidden tokens, and the
    ratified disclaimer contains it: *nie jest to gwarancja wydania WZ*. Scanning
    the whole page would fail correct copy. The disclaimer is asserted byte-equal
    elsewhere, so excluding it here loses nothing.
    """
    from dzialki.enrich.wz.wording import WZ_DISCLAIMER

    rendered = render("likely")
    text = "\n".join(line for line in rendered.lines if line != WZ_DISCLAIMER).lower()
    for forbidden in (
        "można budować",
        "zgoda",
        "gwarancja wydania",
        "spełnia warunki",
        "bez przeszkód",
        "✓",
    ):
        assert forbidden not in text


def test_unlikely_is_phrased_as_an_observation() -> None:
    rendered = render("unlikely", reason_code="no_neighbour_within_radius")
    text = "\n".join(rendered.lines)
    assert "brak spełnienia warunku dobrego sąsiedztwa w promieniu 100 m" in text
    for forbidden in ("nie można budować", "odmowa", "nie da się", "niemożliwe"):
        assert forbidden not in text.lower()


def test_the_radius_in_the_string_is_the_radius_that_was_used() -> None:
    """A hardcoded 100 in the template passes the first and fails the second."""
    first = render("unlikely", reason_code="no_neighbour_within_radius", radius_m=100)
    second = render("unlikely", reason_code="no_neighbour_within_radius", radius_m=150)
    assert "w promieniu 100 m" in "\n".join(first.lines)
    assert "w promieniu 150 m" in "\n".join(second.lines)


def test_unknown_renders_explicit_text_and_names_which_unknown() -> None:
    from dzialki.enrich.wz.wording import UNKNOWN_LINES

    assert set(UNKNOWN_LINES) == {
        "building_data_unavailable",
        "coverage_unproven",
        "coverage_record_stale",
        "building_query_failed",
    }
    for reason, template in UNKNOWN_LINES.items():
        rendered = render("unknown", reason_code=reason)
        assert template.format(checked_at="2026-08-01") in rendered.lines
        assert rendered.lines[0] != ""


def test_the_verdict_renders_with_n_source_and_as_of() -> None:
    """Rule 7. The verdict is an aggregate of evidence and is shown like one."""
    text = "\n".join(render("likely").lines)
    assert "n = 1" in text
    assert "egib" in text
    assert "2026-08-08" in text
    assert "100 m" in text


# --- V66: the two road wordings -------------------------------------------


def test_the_proxy_wording_and_the_confirmed_wording_differ_by_hash() -> None:
    """V66(b). Neither can drift into the other."""
    from dzialki.enrich.wz.wording import (
        ROAD_CONFIRMED_WORDING,
        ROAD_PROXY_DISCLAIMER,
    )

    assert ROAD_CONFIRMED_WORDING != ROAD_PROXY_DISCLAIMER
    assert digest(ROAD_CONFIRMED_WORDING) != digest(ROAD_PROXY_DISCLAIMER)
    # Pinned, so an edit to either string shows up as a changed hash rather than
    # a silent rewrite. Both are proposals: O39 has not been answered.
    assert digest(ROAD_CONFIRMED_WORDING) == (
        "60c66dd8d7ec33c01d0a14b343e21b3c8d3ea4720c33bba17b5aa558f3c520b3"
    )
    assert digest(ROAD_PROXY_DISCLAIMER) == (
        "a4b3bff5be26b8a5c212c1dec3be1bdb9dd3091f1223ebd000d598d30c53bab2"
    )


def test_a_likely_verdict_from_the_proxy_renders_its_own_disclaimer() -> None:
    """V66(a). The disclaimer and the marker naming the evidence."""
    from dzialki.enrich.wz.wording import (
        ROAD_CONFIRMED_WORDING,
        ROAD_PROXY_DISCLAIMER,
    )

    rendered = render(
        "likely",
        road_status="public_by_proxy",
        register_class="dr",
        osm_highway_class="residential",
    )
    text = "\n".join(rendered.lines)

    assert ROAD_PROXY_DISCLAIMER in rendered.lines
    assert rendered.evidence_marker == (
        "przesłanka drogi publicznej: klasa użytku dr, klasa drogi OSM residential"
    )
    assert rendered.evidence_marker in rendered.lines
    assert ROAD_CONFIRMED_WORDING not in text


def test_a_likely_verdict_from_confirmed_ownership_uses_the_other_wording() -> None:
    from dzialki.enrich.wz.wording import (
        ROAD_CONFIRMED_WORDING,
        ROAD_PROXY_DISCLAIMER,
    )

    rendered = render(
        "likely",
        road_status="public_confirmed",
        register_class="dr",
        osm_highway_class="residential",
    )
    assert ROAD_CONFIRMED_WORDING in rendered.lines
    assert ROAD_PROXY_DISCLAIMER not in "\n".join(rendered.lines)
    assert rendered.evidence_marker is None


def test_the_proxy_verdict_still_carries_the_ordinary_disclaimer() -> None:
    """The proxy wording is additional. It never replaces the WZ disclaimer."""
    from dzialki.enrich.wz.wording import WZ_DISCLAIMER

    rendered = render(
        "likely",
        road_status="public_by_proxy",
        register_class="dr",
        osm_highway_class="residential",
    )
    assert rendered.disclaimer is WZ_DISCLAIMER
    assert WZ_DISCLAIMER in rendered.lines


def test_a_crossed_road_wording_is_caught(repo_root) -> None:
    """V66(c), the non-vacuity companion.

    The scans above are negative assertions, and a negative assertion passes
    trivially against a page that renders no road wording at all. This seeds the
    exact defect — a proxy verdict rendered with the confirmed wording — and
    asserts the check finds it.
    """
    from dzialki.enrich.wz.wording import (
        ROAD_CONFIRMED_WORDING,
        CrossedRoadWording,
        check_road_wording,
    )

    honest = render(
        "likely",
        road_status="public_by_proxy",
        register_class="dr",
        osm_highway_class="residential",
    )
    check_road_wording(honest.lines, road_status="public_by_proxy")

    seeded = (*honest.lines, ROAD_CONFIRMED_WORDING)
    with pytest.raises(CrossedRoadWording) as caught:
        check_road_wording(seeded, road_status="public_by_proxy")
    assert "public_by_proxy" in str(caught.value)


def test_a_road_of_unknown_status_states_neither_wording() -> None:
    from dzialki.enrich.wz.wording import (
        ROAD_CONFIRMED_WORDING,
        ROAD_PROXY_DISCLAIMER,
    )

    rendered = render(
        "uncertain", reason_code="road_status_unknown", road_status="unknown"
    )
    text = "\n".join(rendered.lines)
    assert ROAD_CONFIRMED_WORDING not in text
    assert ROAD_PROXY_DISCLAIMER not in text
    assert rendered.evidence_marker is None


def test_the_proxy_copy_is_marked_unratified() -> None:
    """O39 is open. The module says so, so nobody ships it believing otherwise."""
    from dzialki.enrich.wz import wording

    assert "O39" in wording.__doc__
    assert wording.ROAD_COPY_IS_RATIFIED is False
