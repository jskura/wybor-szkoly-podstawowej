"""R1.1–R1.3 — the package exists, holds exactly the v0 modules, and git tracks
exactly the expected configuration files.

These are structural preconditions. Until they pass, no later test can be red for
the right reason.
"""

from __future__ import annotations

import importlib
import pathlib
import subprocess

import pytest

pytestmark = [pytest.mark.unit]

# `16-repository-layout.md` §1, the v0 subset. `extract`, `model`, `api`,
# `digest` and `frontend` arrive with their own work items.
V0_PACKAGES = {
    "config",
    "db",
    "ingest",
    "normalize",
    "dedup",
    "geo",
    "metrics",
    "valuation",
    # S14. Parcels, buildings and the WZ good-neighbour test. It computes
    # verdicts and never fetches: the ingest packages hand it geometry.
    "enrich",
    # `render` is pure and returns a node tree; `app` maps that tree to
    # Streamlit. They are siblings so the boundary between them is real.
    "render",
    "app",
    "ops",
    # S15. The purchase-restriction badges, their register-class table and their
    # citation record. A sibling of `render` because refusing to render
    # unratified legal content is a decision, not a presentation rule.
    "legal",
}

# Each stage edits this list on purpose, which is the point of asserting
# equality rather than containment.
TRACKED_CONFIG_FILES = [
    "config/anchors.example.yml",
    "config/legal_citations.yml",
    "config/params.yml",
    "config/register_classes.yml",
    "config/sources.yml",
    "config/teryt_bdl.yml",
]


def test_package_version_is_declared() -> None:
    import dzialki

    assert dzialki.__version__ == "0.0.0"


def test_v0_package_directories_exist_and_are_importable() -> None:
    import dzialki

    root = pathlib.Path(dzialki.__file__).parent
    on_disk = {
        child.name
        for child in root.iterdir()
        if child.is_dir() and (child / "__init__.py").exists()
    }
    assert on_disk == V0_PACKAGES

    for name in sorted(V0_PACKAGES):
        importlib.import_module(f"dzialki.{name}")


def test_git_tracks_exactly_the_expected_config_files(
    repo_root: pathlib.Path,
) -> None:
    listed = subprocess.run(
        ["git", "ls-files", "config/"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    assert sorted(listed) == TRACKED_CONFIG_FILES
