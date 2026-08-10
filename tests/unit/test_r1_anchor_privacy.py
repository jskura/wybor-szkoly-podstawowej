"""R1.4–R1.8 — the anchor addresses stay out of the repository.

This file discharges V7. The addresses are the owner's home and a second place
they care about; a leak is not recoverable by deleting a file, because git keeps
history.
"""

from __future__ import annotations

import ast
import pathlib
import re
import subprocess

import pytest

pytestmark = [pytest.mark.unit]

HOUSE_NUMBER = re.compile(r"\d+\s*[A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż]")


def _run(args: list[str], cwd: pathlib.Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True)


def test_anchors_yml_is_gitignored(repo_root: pathlib.Path) -> None:
    ignored = _run(["git", "check-ignore", "-q", "config/anchors.yml"], repo_root)
    assert ignored.returncode == 0

    # A .gitignore rule can exist and still be wrong — unanchored, or negated
    # later in the file. Only a real file proves the rule bites.
    target = repo_root / "config" / "anchors.yml"
    pre_existing = target.exists()
    if not pre_existing:
        target.write_text("anchors: {}\n", encoding="utf-8")
    try:
        status = _run(["git", "status", "--porcelain"], repo_root)
        assert "anchors.yml" not in status.stdout
    finally:
        if not pre_existing:
            target.unlink()


def test_anchors_example_contains_only_placeholders(
    repo_root: pathlib.Path,
    poland_bbox: tuple[float, float, float, float],
) -> None:
    from dzialki.config import load_anchors

    anchors = load_anchors(repo_root / "config" / "anchors.example.yml")
    assert sorted(anchors) == ["A", "B"]
    assert anchors["A"].label == "PLACEHOLDER_ANCHOR_A"
    assert anchors["A"].lat == 0.0
    assert anchors["A"].lon == 0.0

    min_lon, min_lat, max_lon, max_lat = poland_bbox
    for anchor in anchors.values():
        # A renamed label would defeat a label-only check. A real coordinate
        # committed by accident still fails here.
        assert re.search(r"\d", anchor.label) is None
        inside = (
            min_lon <= anchor.lon <= max_lon and min_lat <= anchor.lat <= max_lat
        )
        assert not inside


def test_anchor_loader_contains_no_coordinate_literals(
    repo_root: pathlib.Path,
    poland_bbox: tuple[float, float, float, float],
) -> None:
    """Forbid the *shape* of the violation, so it survives a refactor."""
    source = (repo_root / "src" / "dzialki" / "config" / "anchors.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    min_lon, min_lat, max_lon, max_lat = poland_bbox

    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant):
            continue
        if isinstance(node.value, float):
            in_lon = min_lon <= node.value <= max_lon
            in_lat = min_lat <= node.value <= max_lat
            assert not (in_lon or in_lat), f"coordinate-shaped literal {node.value}"
        if isinstance(node.value, str):
            assert HOUSE_NUMBER.search(node.value) is None, (
                f"address-shaped literal {node.value!r}"
            )


def test_missing_anchors_config_raises_named_actionable_error(
    tmp_path: pathlib.Path,
) -> None:
    from dzialki.config import AnchorConfigMissing, load_anchors

    with pytest.raises(AnchorConfigMissing) as caught:
        load_anchors(tmp_path / "absent.yml")

    assert "config/anchors.example.yml" in str(caught.value)
    # A bare OS error is not actionable: it says a path is missing, not what to do.
    assert not issubclass(AnchorConfigMissing, OSError)


@pytest.mark.needs_local_secrets
@pytest.mark.needs_git_history
def test_anchor_addresses_absent_from_working_tree_and_history(
    repo_root: pathlib.Path,
    git_is_shallow: bool,
) -> None:
    """V7(b). Runs as a pre-push hook, never in CI (D124).

    Putting the addresses into CI so CI can prove they are absent from the
    repository defeats the point. The hook reads them from the gitignored file.
    """
    anchors_yml = repo_root / "config" / "anchors.yml"
    if not anchors_yml.exists():
        pytest.skip("config/anchors.yml absent — V7(b) not exercised")
    if git_is_shallow:
        pytest.skip("shallow clone — V7(b) history scan not exercised")

    from dzialki.config import load_anchors

    anchors = load_anchors(anchors_yml)
    secrets = [
        value
        for anchor in anchors.values()
        for value in (anchor.street, anchor.house_number)
        if value
    ]
    assert secrets, "anchors.yml carries no address to scan for"

    for secret in secrets:
        tree = _run(["git", "grep", "-F", "--", secret], repo_root)
        assert tree.returncode == 1, f"{secret!r} is in the working tree"

        history = _run(
            ["git", "log", "-p", "--all", "--format=%H", "-S", secret], repo_root
        )
        assert history.stdout.strip() == "", f"{secret!r} is in git history"
