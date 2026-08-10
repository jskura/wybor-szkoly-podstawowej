"""Shared fixtures. Nothing here opens a database connection."""

from __future__ import annotations

import pathlib
import subprocess

import pytest


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


@pytest.fixture(scope="session")
def repo_root() -> pathlib.Path:
    """The git top level.

    Read from git, not from ``__file__`` arithmetic, which breaks when pytest
    runs with a different rootdir.
    """
    return pathlib.Path(_git("rev-parse", "--show-toplevel"))


@pytest.fixture(scope="session")
def fixtures_dir(repo_root: pathlib.Path) -> pathlib.Path:
    return repo_root / "tests" / "fixtures"


@pytest.fixture(scope="session")
def poland_bbox() -> tuple[float, float, float, float]:
    """``(min_lon, min_lat, max_lon, max_lat)``.

    The single definition. R1.5 and R1.6 both read it; two copies would drift.
    """
    return (14.0, 49.0, 24.2, 55.0)


@pytest.fixture(scope="session")
def git_is_shallow() -> bool:
    return _git("rev-parse", "--is-shallow-repository") == "true"
