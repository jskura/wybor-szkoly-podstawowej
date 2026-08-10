"""S15 — what `src/dzialki/legal/` is physically unable to say.

F16's detector (b). The badge names an act and a pre-emption holder, and neither
string exists anywhere in the package. A render helper cannot name the wrong
authority because it never holds an authority's name at all. The same rule keeps
the register-class symbols in the table and the thousands separator in
`config/params.yml`.

Every scan reads the syntax tree, never the file text, and skips docstrings. A
document that names `KOWR` to explain why the code may not is the opposite of an
occurrence. Each scan has a seeded companion, because a scan for absence passes
trivially when its pattern is wrong.
"""

from __future__ import annotations

import ast
import pathlib
import re

import pytest

pytestmark = [pytest.mark.architecture]

LEGAL = ("src", "dzialki", "legal")

# The 24 rows of `config/register_classes.yml`. A branch on any of them is how a
# wrong regime gets hardcoded and then outlives the table.
CLASS_SYMBOLS = frozenset(
    {
        "R",
        "S",
        "Ł",
        "Ps",
        "Br",
        "Wsr",
        "W",
        "Lzr",
        "Ls",
        "Lz",
        "B",
        "Ba",
        "Bi",
        "Bp",
        "Bz",
        "dr",
        "Tk",
        "Ti",
        "Tp",
        "Ws",
        "Wp",
        "Wm",
        "Tr",
        "N",
    }
)

# The four strings of the crossing table, plus the words a threshold would use.
FORBIDDEN_SUBSTRINGS = (
    "KOWR",
    "Lasy Państwowe",
    "Lasów Państwowych",
    "ustawa o lasach",
    "kształtowaniu ustroju rolnego",
    "hektar",
)
# A quantity in hectares, and any act-related date.
FORBIDDEN_PATTERNS = (
    re.compile(r"\d+\s*ha\b"),
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
)
# D125's separator lives in `config/params.yml`. A copy here would outlive it.
FORBIDDEN_CHARACTERS = ("\u00a0",)

SQL_TOKENS = ("SELECT ", "WHERE ", "INSERT ", "FROM ")
DATABASE_LIBRARIES = frozenset({"sqlalchemy", "psycopg", "geoalchemy2"})
CLOCK_CALLS = frozenset({"now", "utcnow", "today"})


def modules(repo_root: pathlib.Path) -> list[pathlib.Path]:
    found = sorted(repo_root.joinpath(*LEGAL).rglob("*.py"))
    assert found != []
    return found


def docstring_nodes(tree: ast.AST) -> set[int]:
    """Every string that documents rather than runs."""
    found: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            continue
        body = getattr(node, "body", [])
        if not body:
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            found.add(id(first.value))
    return found


def code_strings(source: str) -> list[tuple[int, str]]:
    """Every string constant the module executes, docstrings excluded."""
    tree = ast.parse(source)
    skip = docstring_nodes(tree)
    return [
        (node.lineno, node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in skip
    ]


def symbol_literals(source: str) -> list[tuple[int, str]]:
    return [
        (line, text) for line, text in code_strings(source) if text in CLASS_SYMBOLS
    ]


def legal_literals(source: str) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for line, text in code_strings(source):
        for forbidden in FORBIDDEN_SUBSTRINGS:
            if forbidden.lower() in text.lower():
                found.append((line, forbidden))
        for pattern in FORBIDDEN_PATTERNS:
            if pattern.search(text):
                found.append((line, pattern.pattern))
    return found


def separator_literals(source: str) -> list[tuple[int, str]]:
    return [
        (line, character)
        for line, text in code_strings(source)
        for character in FORBIDDEN_CHARACTERS
        if character in text
    ]


def imported_modules(source: str) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


# --- no class symbol -------------------------------------------------------


def test_the_legal_package_holds_no_register_class_symbol(
    repo_root: pathlib.Path,
) -> None:
    offenders = [
        f"{path.relative_to(repo_root)}:{line}: {text}"
        for path in modules(repo_root)
        for line, text in symbol_literals(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []


def test_the_symbol_scan_catches_a_real_occurrence(tmp_path: pathlib.Path) -> None:
    seeded = tmp_path / "seeded.py"
    seeded.write_text(
        '"""A module whose docstring names Ls and whose code branches on it."""\n'
        "def regime(symbol):\n"
        "    return 'forest' if symbol == 'Ls' else 'none'\n",
        encoding="utf-8",
    )
    assert symbol_literals(seeded.read_text(encoding="utf-8")) == [(3, "Ls")]


def test_the_symbol_scan_ignores_a_docstring(tmp_path: pathlib.Path) -> None:
    seeded = tmp_path / "seeded.py"
    seeded.write_text(
        '"""This module never branches on Ls, Lz or R."""\n',
        encoding="utf-8",
    )
    assert symbol_literals(seeded.read_text(encoding="utf-8")) == []


# --- no act, no holder, no threshold ---------------------------------------


def test_the_legal_package_names_no_act_holder_or_threshold(
    repo_root: pathlib.Path,
) -> None:
    """The badge renders both names from the record, so neither is in the code."""
    offenders = [
        f"{path.relative_to(repo_root)}:{line}: {text}"
        for path in modules(repo_root)
        for line, text in legal_literals(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []


def test_the_legal_literal_scan_catches_a_real_occurrence(
    tmp_path: pathlib.Path,
) -> None:
    seeded = tmp_path / "seeded.py"
    seeded.write_text(
        '"""A module that mentions KOWR and 5 ha in prose only."""\n'
        "HOLDER = 'KOWR'\n"
        "COPY = 'próg 5 ha od 2026-04-30'\n",
        encoding="utf-8",
    )
    assert legal_literals(seeded.read_text(encoding="utf-8")) == [
        (2, "KOWR"),
        (3, r"\d+\s*ha\b"),
        (3, r"\b\d{4}-\d{2}-\d{2}\b"),
    ]


# --- no ratified separator -------------------------------------------------


def test_the_legal_package_holds_no_thousands_separator(
    repo_root: pathlib.Path,
) -> None:
    """V65. The character is ratified, so it lives in `config/params.yml`."""
    offenders = [
        f"{path.relative_to(repo_root)}:{line}"
        for path in modules(repo_root)
        for line, _character in separator_literals(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []


def test_the_separator_scan_catches_a_real_occurrence(tmp_path: pathlib.Path) -> None:
    seeded = tmp_path / "seeded.py"
    seeded.write_text(
        'THOUSANDS_SEP = "\\u00a0"\n',
        encoding="utf-8",
    )
    assert separator_literals(seeded.read_text(encoding="utf-8")) == [(1, "\u00a0")]


# --- the badge is never a filter -------------------------------------------


def query_traces(source: str) -> list[str]:
    """SQL written the way this repository writes it, plus any database import.

    The match is case sensitive. `19` §2.2's prose says a class is absent *from*
    the table, and prose is not a query.
    """
    found: list[str] = []
    for line, text in code_strings(source):
        found.extend(f"{line}: {token}" for token in SQL_TOKENS if token in text)
    for module in imported_modules(source):
        if module.split(".")[0] in DATABASE_LIBRARIES or module.startswith(
            ("dzialki.db", "dzialki.ingest")
        ):
            found.append(module)
    return found


def test_the_legal_package_holds_no_query(repo_root: pathlib.Path) -> None:
    """D51 chose the badge over exclusion. A package with no query cannot filter."""
    offenders = [
        f"{path.relative_to(repo_root)}:{trace}"
        for path in modules(repo_root)
        for trace in query_traces(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []


def test_the_query_scan_catches_a_real_occurrence(tmp_path: pathlib.Path) -> None:
    seeded = tmp_path / "seeded.py"
    seeded.write_text(
        '"""A module that selects badged parcels out of a result set."""\n'
        "import sqlalchemy\n"
        "QUERY = 'SELECT id FROM parcel WHERE regime IS NULL'\n",
        encoding="utf-8",
    )
    assert query_traces(seeded.read_text(encoding="utf-8")) == [
        "3: SELECT ",
        "3: WHERE ",
        "3: FROM ",
        "sqlalchemy",
    ]


# --- the package reads its data, and decides nothing about the clock -------


def test_the_legal_package_reads_no_clock(repo_root: pathlib.Path) -> None:
    """A badge whose text depends on the day it ran cannot be asserted."""
    offenders: list[str] = []
    for path in modules(repo_root):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in CLOCK_CALLS
            ):
                offenders.append(f"{path.relative_to(repo_root)}:{node.lineno}")
    assert offenders == []
