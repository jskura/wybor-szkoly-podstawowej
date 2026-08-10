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

# `16-repository-layout.md` §1, the v0 subset. `extract`, `dedup`, `enrich`,
# `model`, `api`, `digest` and `frontend` arrive with their own work items.
V0_PACKAGES = {
    "config",
    "db",
    "ingest",
    "normalize",
    "geo",
    "metrics",
    "valuation",
    "app",
    "ops",
}

# S4 adds teryt_bdl.yml (D97); S15 adds register_classes.yml (D117). Each stage
# edits this list on purpose.
TRACKED_CONFIG_FILES = [
    "config/anchors.example.yml",
    "config/params.yml",
    "config/sources.yml",
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
