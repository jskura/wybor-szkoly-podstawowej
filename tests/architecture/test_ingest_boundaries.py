"""The boundaries that make the connector contract worth having.

Two rules, both enforced by reading the source rather than by trusting it.

Only the HTTP client may import an HTTP library. A parser that fetches is a
parser that cannot be re-run against a stored payload, and re-parsing stored
payloads is the whole reason raw documents are kept (V42).

No code path exists for defeating an anti-bot measure (D73). This is a scan for
absence, so it is worth stating what makes it non-vacuous: the seeded test below
proves the scan catches a real occurrence.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

pytestmark = [pytest.mark.architecture]

HTTP_LIBRARIES = {"httpx", "requests", "urllib3", "aiohttp", "http.client"}
HTTP_CLIENT = "http.py"

# D73. Each of these names a way of pretending to be someone else, or of
# defeating a measure a site put up on purpose.
FORBIDDEN = [
    "captcha",
    "undetected",
    "stealth",
    "selenium",
    "playwright",
    "set_cookie",
    "rotate_user_agent",
    "proxy_pool",
]


def _imports(path: pathlib.Path) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


def test_only_the_http_client_imports_an_http_library(
    repo_root: pathlib.Path,
) -> None:
    offenders: list[str] = []
    for path in (repo_root / "src" / "dzialki").rglob("*.py"):
        if path.name == HTTP_CLIENT:
            continue
        for module in _imports(path):
            root = module.split(".")[0]
            if root in HTTP_LIBRARIES or module in HTTP_LIBRARIES:
                offenders.append(f"{path.relative_to(repo_root)}: {module}")
    assert offenders == []


def _code_identifiers(path: pathlib.Path) -> list[tuple[int, str]]:
    """Every name and string literal in the module, excluding docstrings.

    The scan must read code, not prose. `robots.py` explains D73 in its
    docstring and names the techniques it refuses to implement; a document
    saying "we do not defeat CAPTCHAs" is the opposite of a violation.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstrings = {
        id(node.body[0].value)
        for node in ast.walk(tree)
        if isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        )
        and node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and isinstance(node.body[0].value.value, str)
    }

    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            found.append((node.lineno, node.id))
        elif isinstance(node, ast.Attribute):
            found.append((node.lineno, node.attr))
        elif isinstance(node, ast.Import):
            found.extend((node.lineno, alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.append((node.lineno, node.module))
        elif (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstrings
        ):
            found.append((node.lineno, node.value))
    return found


def test_no_evasion_code_path_exists(repo_root: pathlib.Path) -> None:
    """D73 as a test, not a promise.

    Refusing to evade is a decision that survives only if something checks. A
    sentence in a document does not stop a helper being added in six months.
    """
    hits: list[str] = []
    for path in (repo_root / "src" / "dzialki" / "ingest").rglob("*.py"):
        for number, identifier in _code_identifiers(path):
            for name in FORBIDDEN:
                if name in identifier.lower():
                    hits.append(f"{path.relative_to(repo_root)}:{number}: {name}")
    assert hits == []


def test_the_evasion_scan_catches_a_real_occurrence(tmp_path: pathlib.Path) -> None:
    """Non-vacuity companion.

    A scan for absence passes trivially when its pattern is wrong or the code it
    reads is empty. The seeded module is real code, not a comment, so it also
    proves the docstring exclusion above did not disable the scan.
    """
    seeded = tmp_path / "seeded.py"
    seeded.write_text(
        '"""A module that defeats a captcha, described in prose only."""\n'
        "driver = undetected_chromedriver.Chrome()\n",
        encoding="utf-8",
    )
    hits = [
        name
        for _line, identifier in _code_identifiers(seeded)
        for name in FORBIDDEN
        if name in identifier.lower()
    ]
    assert hits == ["undetected"]


def test_parse_is_pure_under_a_blocked_socket(monkeypatch) -> None:
    """The contract's middle stage opens no socket.

    Enforced by breaking sockets rather than by reading the code, because a
    parser can reach the network through a dependency the import scan misses.
    """
    import socket

    def refuse(*args, **kwargs):
        raise AssertionError("parse must not open a socket")

    monkeypatch.setattr(socket, "socket", refuse)

    from dzialki.ingest import robots

    policy = robots.parse("User-agent: *\nDisallow: /oferta/\n", user_agent="dzialki")
    assert policy.allows("/oferta/1") is False
