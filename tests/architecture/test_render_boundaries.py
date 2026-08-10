"""The boundary that makes every honesty rule testable without a browser.

`src/dzialki/render/` is pure. It imports no Streamlit, opens no file, holds
no database session and reads no clock. Everything it needs — the configuration,
the formatter and `now` — arrives as an argument. That is what lets a test about
staleness run without freezing time globally, and a test about the flow window
run at two windows in one process.

Three of these tests scan for absence. A scan for absence passes trivially when
its pattern is wrong, so each one has a companion that seeds a real occurrence
and proves the scan finds it.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

pytestmark = [pytest.mark.architecture]

RENDER = ("src", "dzialki", "render")

# The shell draws the tree. Nothing under `render/` may reach any of these.
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

# Reading the clock inside a renderer makes the output depend on the day it ran.
FORBIDDEN_CALLS = {"now", "utcnow", "today", "monotonic", "perf_counter"}
FORBIDDEN_NAMES = {"open", "input", "print"}

# D107 fixes the shipped flow window at 90 days. V62's failure is two call sites
# holding two windows, so the scan proves the number lives in configuration.
WINDOW_LENGTHS = {30, 60, 90, 180}


def render_root(repo_root: pathlib.Path) -> pathlib.Path:
    return repo_root.joinpath(*RENDER)


def modules(repo_root: pathlib.Path) -> list[pathlib.Path]:
    found = sorted(render_root(repo_root).rglob("*.py"))
    assert found, "the render package holds no modules"
    return found


def imported_modules(source: str) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


def clock_and_io_calls(source: str) -> list[tuple[int, str]]:
    """Every call that would make a renderer read the world.

    This reads the syntax tree, not the text. A docstring that names
    `date.today` is a warning to the reader, not a call.
    """
    found: list[tuple[int, str]] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Attribute) and node.func.attr in FORBIDDEN_CALLS:
            found.append((node.lineno, node.func.attr))
        elif isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_NAMES:
            found.append((node.lineno, node.func.id))
    return found


def integer_literals(source: str) -> list[tuple[int, int]]:
    found: list[tuple[int, int]] = []
    for node in ast.walk(ast.parse(source)):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, int)
            and not isinstance(node.value, bool)
        ):
            found.append((node.lineno, node.value))
    return found


# --- the import boundary ---------------------------------------------------


def test_no_render_module_imports_streamlit_or_any_other_outside_world(
    repo_root: pathlib.Path,
) -> None:
    offenders: list[str] = []
    for path in modules(repo_root):
        for module in imported_modules(path.read_text(encoding="utf-8")):
            if module.split(".")[0] in FORBIDDEN_IMPORTS:
                offenders.append(f"{path.relative_to(repo_root)}: {module}")
    assert offenders == []


def test_the_import_scan_catches_a_real_occurrence(tmp_path: pathlib.Path) -> None:
    seeded = tmp_path / "seeded.py"
    seeded.write_text(
        '"""A module that says the word streamlit in prose only."""\n'
        "import streamlit as st\n",
        encoding="utf-8",
    )
    found = {
        module
        for module in imported_modules(seeded.read_text(encoding="utf-8"))
        if module.split(".")[0] in FORBIDDEN_IMPORTS
    }
    assert found == {"streamlit"}


def test_no_render_module_imports_the_database_or_the_ingest_packages(
    repo_root: pathlib.Path,
) -> None:
    """A renderer that can query is a renderer that cannot be tested offline."""
    offenders: list[str] = []
    for path in modules(repo_root):
        for module in imported_modules(path.read_text(encoding="utf-8")):
            if module.startswith(("dzialki.db", "dzialki.ingest", "dzialki.model")):
                offenders.append(f"{path.relative_to(repo_root)}: {module}")
    assert offenders == []


# --- the clock and the filesystem ------------------------------------------


def test_no_render_module_reads_the_clock_or_opens_a_file(
    repo_root: pathlib.Path,
) -> None:
    offenders: list[str] = []
    for path in modules(repo_root):
        for line, name in clock_and_io_calls(path.read_text(encoding="utf-8")):
            offenders.append(f"{path.relative_to(repo_root)}:{line}: {name}")
    assert offenders == []


def test_the_clock_scan_catches_a_real_occurrence(tmp_path: pathlib.Path) -> None:
    """The seeded module is code, not a comment, so it also proves the scan is
    not disabled by reading the syntax tree instead of the text."""
    seeded = tmp_path / "seeded.py"
    seeded.write_text(
        '"""A module that mentions datetime.date.today in prose only."""\n'
        "import datetime\n"
        "\n"
        "def stamp():\n"
        "    handle = open('x')\n"
        "    return datetime.date.today(), handle\n",
        encoding="utf-8",
    )
    assert clock_and_io_calls(seeded.read_text(encoding="utf-8")) == [
        (5, "open"),
        (6, "today"),
    ]


def test_the_clock_scan_ignores_a_docstring_that_names_the_call(
    tmp_path: pathlib.Path,
) -> None:
    """This scan has already cost three red runs elsewhere in the repository.
    A document saying "we never call date.today" is the opposite of a call."""
    seeded = tmp_path / "seeded.py"
    seeded.write_text(
        '"""This module never calls date.today() or open()."""\n'
        "MESSAGE = 'nothing here calls datetime.now()'\n",
        encoding="utf-8",
    )
    assert clock_and_io_calls(seeded.read_text(encoding="utf-8")) == []


# --- the flow window lives in configuration --------------------------------


def test_no_render_module_holds_a_literal_window_length(
    repo_root: pathlib.Path,
) -> None:
    offenders: list[str] = []
    for path in modules(repo_root):
        for line, value in integer_literals(path.read_text(encoding="utf-8")):
            if value in WINDOW_LENGTHS:
                offenders.append(f"{path.relative_to(repo_root)}:{line}: {value}")
    assert offenders == []


def test_the_window_scan_catches_a_real_occurrence(tmp_path: pathlib.Path) -> None:
    seeded = tmp_path / "seeded.py"
    seeded.write_text(
        '"""A module whose docstring says 90 days and whose code says it too."""\n'
        "FLOW_WINDOW_DAYS = 90\n",
        encoding="utf-8",
    )
    found = [
        value
        for _line, value in integer_literals(seeded.read_text(encoding="utf-8"))
        if value in WINDOW_LENGTHS
    ]
    assert found == [90]


# --- the shape of a builder ------------------------------------------------


def test_every_component_builder_returns_a_render_node(
    repo_root: pathlib.Path,
) -> None:
    """A helper that returns a string cannot be swept, because a sweep walks a
    tree. The annotation is what makes the sweep's coverage checkable."""
    unannotated: list[str] = []
    for path in modules(repo_root):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef):
                continue
            if not node.name.startswith("render_"):
                continue
            if not node.args.args or node.args.args[0].arg != "payload":
                continue
            returned = ast.unparse(node.returns) if node.returns else ""
            if returned != "RenderNode":
                unannotated.append(f"{path.relative_to(repo_root)}: {node.name}")
    assert unannotated == []


def test_render_is_a_sibling_of_the_shell_not_a_child(
    repo_root: pathlib.Path,
) -> None:
    """`render/` sits beside `app/`, never inside it.

    Nested, the pure layer would live inside the impure one and every rule
    above would read as a rule the shell imposes on part of itself. The
    implementation plan puts them side by side for exactly this reason, and the
    package first landed in the wrong place, so the test states it.
    """
    package = repo_root / "src" / "dzialki"
    assert (package / "render" / "__init__.py").exists()
    assert not (package / "app" / "render").exists()


def test_the_shell_package_holds_no_module_yet(repo_root: pathlib.Path) -> None:
    """The adapter is the only module permitted to import Streamlit, and it
    arrives with its own work item. Until then the boundary is trivially held,
    and this test says so rather than leaving the reader to infer it."""
    app = repo_root / "src" / "dzialki" / "app"
    packages = sorted(
        child.name
        for child in app.iterdir()
        if child.is_dir() and (child / "__init__.py").exists()
    )
    assert packages == []
