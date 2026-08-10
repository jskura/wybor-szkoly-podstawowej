"""Work item 4, test 3.1b — the BDL unit id is recorded, never derived (D97).

The failure this guards against is not a crash. String surgery on a TERYT code
produces a well-formed unit id for a different powiat, so the pipeline fetches a
genuine price series for the wrong place and every downstream check passes. The
map is wrong and the data looks healthy.
"""

from __future__ import annotations

import ast
import pathlib

import pytest
import yaml

from dzialki.ingest.official import (
    UnitMapUnverified,
    UnmappedUnit,
    load_unit_map,
)

pytestmark = [pytest.mark.unit]

# Operations that turn one code into another. Any of these applied to a TERYT
# code inside the GUS connector is the derivation D97 forbids.
STRING_SURGERY = {"zfill", "ljust", "rjust", "pad"}


def test_the_committed_map_refuses_until_it_is_verified(
    repo_root: pathlib.Path,
) -> None:
    """The map ships empty on purpose.

    Its powiat list needs the boundary clip nobody has run, and its unit ids need
    the BDL register nobody has read. Plausible codes written from memory would
    be worse than none: an empty map stops the connector, a wrong one produces a
    price series for the wrong place.
    """
    with pytest.raises(UnitMapUnverified) as caught:
        load_unit_map(repo_root / "config" / "teryt_bdl.yml")
    assert "teryt_bdl.yml" in str(caught.value)
    assert "verified" in str(caught.value)


def test_the_committed_map_contains_no_invented_codes(
    repo_root: pathlib.Path,
) -> None:
    """A guard against a future good intention.

    Filling this map from memory rather than from the register is the exact
    fabrication the assumption audit found elsewhere in this project.
    """
    raw = yaml.safe_load(
        (repo_root / "config" / "teryt_bdl.yml").read_text(encoding="utf-8")
    )
    assert raw["verified"] is False
    assert raw["powiats"] == {}


def test_a_verified_map_is_read_back_exactly(tmp_path: pathlib.Path) -> None:
    written = tmp_path / "teryt_bdl.yml"
    written.write_text(
        "verified: true\n"
        "verified_at: 2026-08-10\n"
        "evidence: docs/evidence/bdl/units_2026-08-10.json\n"
        "powiats:\n"
        '  "1415": "011415000000"\n',
        encoding="utf-8",
    )
    unit_map = load_unit_map(written)
    assert unit_map["1415"] == "011415000000"
    assert unit_map.codes() == ["1415"]
    assert unit_map.evidence == "docs/evidence/bdl/units_2026-08-10.json"


def test_an_unmapped_teryt_raises_rather_than_returning_nothing(
    tmp_path: pathlib.Path,
) -> None:
    """A ``None`` here becomes the word "None" in a URL and a 404 downstream,
    which reads as "the source is down" rather than "we never mapped this"."""
    written = tmp_path / "teryt_bdl.yml"
    written.write_text(
        'verified: true\npowiats:\n  "1415": "011415000000"\n', encoding="utf-8"
    )
    unit_map = load_unit_map(written)
    with pytest.raises(UnmappedUnit) as caught:
        unit_map["9999"]
    assert "9999" in str(caught.value)
    assert "teryt_bdl.yml" in str(caught.value)


@pytest.mark.architecture
def test_no_unit_id_is_built_by_string_operations(repo_root: pathlib.Path) -> None:
    """D97 as a scan. The rule survives only if something checks it."""
    official = repo_root / "src" / "dzialki" / "ingest" / "official"
    offenders: list[str] = []
    for path in official.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Attribute) and node.attr in STRING_SURGERY:
                offenders.append(f"{path.relative_to(repo_root)}:{node.lineno}")
    assert offenders == []


def test_the_string_surgery_scan_catches_a_real_occurrence(
    tmp_path: pathlib.Path,
) -> None:
    """Non-vacuity companion. A scan over a small package passes trivially."""
    seeded = tmp_path / "seeded.py"
    seeded.write_text('unit_id = "01" + teryt.zfill(4) + "000000"\n', encoding="utf-8")
    found = [
        node.attr
        for node in ast.walk(ast.parse(seeded.read_text(encoding="utf-8")))
        if isinstance(node, ast.Attribute) and node.attr in STRING_SURGERY
    ]
    assert found == ["zfill"]
