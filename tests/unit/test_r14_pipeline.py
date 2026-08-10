"""R14 — the whole chain over the synthetic scene, parcel by parcel.

Eleven subject parcels, eleven expected verdicts, each pinned to the test plan's
§1.5 table. The scene is the reason the expected values are exact: every shape
is an axis-aligned rectangle, so a reader can re-derive any number here.

**This is not V60.** The scene tests that the code computes what it claims to
compute. V60 tests that what it computes is true of the world, and that needs the
20-parcel hand-labelled set, which does not exist. The two are different
questions and only the second one is the acceptance gate.
"""

from __future__ import annotations

import datetime
import pathlib

import pytest
import yaml

pytestmark = [pytest.mark.unit]

RUN_DATE = datetime.date(2026, 8, 8)

# Two rows of the register-class table, quoted from the test plan §5.1. The full
# table is `config/register_classes.yml`, which stage S15 owns.
REGIME_BY_CLASS = {"B": "none", "R": "agricultural"}

# The verdicts the test plan declares for the eleven subjects, with the reason
# codes this implementation attaches to them.
EXPECTED = {
    "P1": ("likely", ("good_neighbour_satisfied",)),
    "P2": ("unlikely", ("no_neighbour_within_radius", "road_status_unknown")),
    "P3": (
        "unlikely",
        (
            "no_neighbour_within_radius",
            "road_status_unknown",
            "dedesignation_required",
        ),
    ),
    "P4": ("unknown", ("building_data_unavailable",)),
    "P5": ("uncertain", ("good_neighbour_satisfied", "capped_by_protection")),
    "P6": ("uncertain", ("dedesignation_required",)),
    "P7": ("uncertain", ("neighbour_on_different_road",)),
    "P8": ("unknown", ("coverage_unproven",)),
    "P9": ("uncertain", ("capped_by_coverage_absent",)),
    "P10": ("unknown", ("coverage_unproven",)),
    "P11": ("uncertain", ("good_neighbour_satisfied", "capped_by_osm_source")),
    "P12": ("unknown", ("coverage_unproven",)),
}


@pytest.fixture
def scene(repo_root: pathlib.Path) -> dict:
    path = repo_root / "tests" / "fixtures" / "synthetic" / "wz_scene.yml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def assess(scene: dict, subject: str, *, radius_m: int | None = None):
    """Run the whole chain for one subject parcel, in the scene's parameters."""
    from dzialki.enrich.geometry import PLANAR_SRID, Rectangle
    from dzialki.enrich.settings import WzParameters
    from dzialki.enrich.wz.neighbour import Building
    from dzialki.enrich.wz.pipeline import ParcelScene, assess_parcel
    from dzialki.enrich.wz.road import RoadParcel

    as_of = datetime.date.fromisoformat(scene["as_of"])
    working = scene["working_parameters"]
    parameters = WzParameters(
        good_neighbour_radius_m=radius_m or working["good_neighbour_radius_m"],
        coverage_probe_radius_m=working["coverage_probe_radius_m"],
        coverage_probe_min_buildings=working["coverage_probe_min_buildings"],
        coverage_max_age_days=working["coverage_max_age_days"],
    )

    def rectangle(row):
        return Rectangle(*row["rectangle"], srid=PLANAR_SRID)

    row = next(item for item in scene["subjects"] if item["id"] == subject)
    unit = next(item for item in scene["units"] if item["teryt"] == row["teryt_gmina"])

    from dzialki.enrich.coverage import CoverageRecord

    return assess_parcel(
        ParcelScene(
            parcel=rectangle(
                next(item for item in scene["parcels"] if item["id"] == subject)
            ),
            land_use_class=row["land_use_class"],
            buildings=tuple(
                Building(
                    identifier=item["id"],
                    rectangle=rectangle(item),
                    source=item["source"],
                    as_of=as_of,
                )
                for item in scene["buildings"]
            ),
            neighbour_parcels=tuple(
                rectangle(item) for item in scene["parcels"] if item["id"] != subject
            ),
            roads=tuple(
                RoadParcel(
                    identifier=item["id"],
                    rectangle=rectangle(item),
                    register_class=item["register_class"],
                    osm_highway_class=item["osm_highway_class"],
                    ownership_confirmed=item["ownership_confirmed"],
                    as_of=as_of,
                )
                for item in scene["roads"]
            ),
            protected_areas=tuple(
                (item["kind"], rectangle(item)) for item in scene["protected_areas"]
            ),
            coverage_record=CoverageRecord(
                teryt_gmina=unit["teryt"],
                source=unit["coverage"]["source"],
                has_coverage=unit["coverage"]["has_coverage"],
                checked_at=datetime.date.fromisoformat(unit["coverage"]["checked_at"]),
            ),
        ),
        as_of=RUN_DATE,
        parameters=parameters,
        regime_by_class=REGIME_BY_CLASS,
    )


@pytest.mark.parametrize("subject", sorted(EXPECTED))
def test_every_subject_parcel_gets_its_declared_verdict(
    scene: dict, subject: str
) -> None:
    expected_verdict, expected_reasons = EXPECTED[subject]
    result = assess(scene, subject)
    assert result.verdict == expected_verdict
    assert result.reason_codes == expected_reasons
    assert result.reason_code == expected_reasons[0]


def test_the_only_likely_parcel_rests_on_the_road_proxy(scene: dict) -> None:
    """D114. P1's road evidence is register class `dr` plus an OSM highway
    class, never ownership, so the verdict renders the proxy disclaimer."""
    from dzialki.enrich.wz.wording import ROAD_CONFIRMED_WORDING, ROAD_PROXY_DISCLAIMER

    result = assess(scene, "P1")
    assert result.verdict == "likely"
    assert result.road_status == "public_by_proxy"

    lines = result.render().lines
    assert ROAD_PROXY_DISCLAIMER in lines
    assert ROAD_CONFIRMED_WORDING not in "\n".join(lines)


def test_no_parcel_with_missing_building_data_is_unlikely(scene: dict) -> None:
    """V60's headline falsifier, run over every subject in the scene."""
    for subject in EXPECTED:
        result = assess(scene, subject)
        if result.coverage_value == "absent":
            assert result.verdict != "unlikely", subject


def test_every_unlikely_verdict_names_its_coverage_source(scene: dict) -> None:
    """The schema's `unlikely_requires_coverage`, asserted before the insert."""
    unlikely = [
        subject for subject in EXPECTED if assess(scene, subject).verdict == "unlikely"
    ]
    assert unlikely == ["P2", "P3"]
    for subject in unlikely:
        assert assess(scene, subject).coverage_source == "egib"


def test_the_isolated_parcel_and_the_unmapped_one_are_geometrically_alike(
    scene: dict,
) -> None:
    """P3 and P4 both have zero buildings within the radius. Only the gmina's
    coverage record separates them, and reading them the same way is F14."""
    isolated = assess(scene, "P3")
    unmapped = assess(scene, "P4")

    assert isolated.neighbour_value == "absent"
    assert unmapped.neighbour_value == "unknown"
    assert (isolated.verdict, unmapped.verdict) == ("unlikely", "unknown")


def test_the_protected_parcel_records_both_regimes_separately(scene: dict) -> None:
    """The park and its buffer zone are different regimes. An implementation
    that merges the layers produces one 3 600 m² overlap and fails here."""
    result = assess(scene, "P5")
    assert result.protection == (
        ("landscape_park", 1_800.0),
        ("landscape_park_buffer", 1_800.0),
    )


def test_the_stale_record_moves_the_verdict_and_not_only_its_confidence(
    scene: dict,
) -> None:
    """M0 runs before the table, not after it.

    A stale record must be able to turn `unlikely` into `unknown`, which a
    post-hoc cap could not do, because caps never touch `unlikely`.
    """
    result = assess(scene, "P9")
    assert result.coverage_value == "absent"
    assert result.coverage_reason_code == "coverage_record_stale"
    assert result.verdict == "uncertain"
    assert result.reason_codes == ("capped_by_coverage_absent",)


def test_changing_the_configured_radius_changes_a_verdict(scene: dict) -> None:
    """D102's behavioural half, at the composite seam rather than the signal.

    P2's two neighbours sit at exactly 300.000 m. At the scene's 100 m radius the
    verdict is `unlikely`; at 350 m the same parcel is `likely`. An
    implementation holding its own copy of the radius would answer the same twice.
    """
    assert assess(scene, "P2").verdict == "unlikely"
    assert assess(scene, "P2", radius_m=350).verdict == "likely"
