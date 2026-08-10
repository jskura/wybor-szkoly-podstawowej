"""R14 — what the enrich package may not do, and the seeds that prove it.

`src/dzialki/enrich/` is pure. It opens no socket, reads no clock and holds no
database session. Everything it needs — the configuration, the run date, the
building geometry — arrives as an argument. That is what lets a test about a
stale coverage record run without freezing time globally.

Three of these tests scan for absence. A scan for absence passes trivially when
its pattern is wrong, so each one has a companion that seeds a real occurrence
and proves the scan finds it.

The scans read the parse tree, never the source text. A text scan matches its own
explanatory prose, and a scan that reports itself trains a reader to ignore it.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

pytestmark = [pytest.mark.architecture]

ENRICH = ("src", "dzialki", "enrich")

FORBIDDEN_IMPORTS = {
    "streamlit",
    "requests",
    "httpx",
    "urllib3",
    "aiohttp",
    "psycopg",
    "sqlalchemy",
    "geoalchemy2",
    "alembic",
    "random",
    "socket",
}

# Reading the clock inside the assessment makes the verdict depend on the day it
# ran, and the staleness rule is exactly what that would hide.
FORBIDDEN_CALLS = {"now", "utcnow", "today", "monotonic", "perf_counter"}


def modules(repo_root: pathlib.Path) -> list[pathlib.Path]:
    found = sorted(repo_root.joinpath(*ENRICH).rglob("*.py"))
    assert found, "the enrich package holds no modules"
    return found


def parsed(path: pathlib.Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def imported_modules(tree: ast.Module) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module.split(".")[0])
    return found


def called_attributes(tree: ast.Module) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                found.add(node.func.attr)
            elif isinstance(node.func, ast.Name):
                found.add(node.func.id)
    return found


def literals(tree: ast.Module) -> list[object]:
    """Every literal that is not a docstring."""
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)):
            first = node.body[0] if node.body else None
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                docstrings.add(id(first.value))
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and id(node) not in docstrings
    ]


# --- imports --------------------------------------------------------------


def test_enrich_imports_nothing_that_reaches_outside_the_process(
    repo_root: pathlib.Path,
) -> None:
    offenders: list[str] = []
    for path in modules(repo_root):
        for name in imported_modules(parsed(path)) & FORBIDDEN_IMPORTS:
            offenders.append(f"{path.relative_to(repo_root)}: {name}")
    assert offenders == []


def test_the_import_scan_finds_a_seeded_import() -> None:
    tree = ast.parse("import psycopg\n")
    assert imported_modules(tree) & FORBIDDEN_IMPORTS == {"psycopg"}


def test_enrich_never_reads_the_clock(repo_root: pathlib.Path) -> None:
    offenders: list[str] = []
    for path in modules(repo_root):
        for name in called_attributes(parsed(path)) & FORBIDDEN_CALLS:
            offenders.append(f"{path.relative_to(repo_root)}: {name}")
    assert offenders == []


def test_the_clock_scan_finds_a_seeded_call() -> None:
    tree = ast.parse("import datetime\nx = datetime.date.today()\n")
    assert called_attributes(tree) & FORBIDDEN_CALLS == {"today"}


# --- no ratified value is copied into the code ---------------------------


def test_no_configured_distance_appears_as_a_literal_in_enrich(
    repo_root: pathlib.Path,
) -> None:
    """FR-75, narrowed to the two values that could plausibly be copied.

    The minimum building count is left out on purpose. It is a small integer,
    and a scan that flags every 3 in the package reports tuple sizes and trains
    a reader to ignore it. `test_changing_the_minimum_count_changes_the_answer`
    covers the same failure behaviourally, which is the stronger half anyway.
    """
    from dzialki.config import load_params

    shipped = load_params(repo_root / "config" / "params.yml").feasibility
    forbidden = {
        shipped.good_neighbour_radius_m,
        shipped.coverage_probe_radius_m,
    }
    assert forbidden == {100, 500}

    offenders: list[str] = []
    for path in modules(repo_root):
        for value in literals(parsed(path)):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            if value in forbidden:
                offenders.append(f"{path.relative_to(repo_root)}: {value}")
    assert offenders == []


def test_the_literal_scan_finds_a_seeded_radius() -> None:
    tree = ast.parse(
        '"""A docstring naming 100 metres, which must not match."""\nRADIUS = 100\n'
    )
    numbers = [value for value in literals(tree) if isinstance(value, int)]
    assert numbers == [100]

    prose_only = ast.parse('"""A docstring naming 100 metres, and nothing else."""\n')
    assert [value for value in literals(prose_only) if isinstance(value, int)] == []


# --- the parameters are read, so the file is not documentation -----------


def test_every_feasibility_parameter_is_read_by_this_package(
    repo_root: pathlib.Path,
) -> None:
    """The other half of FR-75. A key nobody reads is a key something copied."""
    from dzialki.config.params import Feasibility

    source = "\n".join(path.read_text(encoding="utf-8") for path in modules(repo_root))
    unread = sorted(key for key in Feasibility.model_fields if f".{key}" not in source)
    assert unread == []


def test_the_stage_deleted_its_rows_from_the_pending_map(
    repo_root: pathlib.Path,
) -> None:
    """S14 is the stage that reads these three keys, so its rows must go.

    The map is read as data, not as file text: the same file names the keys in
    its parametrised startup test, and a text scan would match those and report a
    row that is not there.
    """
    import ast

    source = (repo_root / "tests" / "unit" / "test_r1_configuration.py").read_text(
        encoding="utf-8"
    )
    pending: dict[str, str] = {}
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "PENDING_STAGES"
            for target in node.targets
        ):
            pending = ast.literal_eval(node.value)
    assert pending, "PENDING_STAGES is not in the configuration test any more"
    assert [key for key in pending if key.startswith("feasibility.")] == []


# --- the enrich package is a declared v0 package -------------------------


@pytest.mark.unit
def test_enrich_is_importable_as_a_package() -> None:
    import dzialki.enrich
    import dzialki.enrich.wz

    assert dzialki.enrich.__name__ == "dzialki.enrich"
    assert dzialki.enrich.wz.__name__ == "dzialki.enrich.wz"
