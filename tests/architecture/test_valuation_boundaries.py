"""The verdict comes from comparables and from nothing else.

A feature model may run alongside to say what each attribute is worth. It is
clearly marked as a model estimate and it is **structurally barred** from
producing the answer: the estimator imports no model, so deleting the model
package would leave this suite green except for feature-value tests.

Structural rather than procedural on purpose. "We agreed the model does not set
the verdict" survives until someone needs a number and the model has one.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

pytestmark = [pytest.mark.architecture]

# Packages a verdict must never depend on. `model` does not exist yet; naming it
# now means the day it arrives, this test already forbids the edge.
FORBIDDEN_IMPORTS = {"model", "hedonic", "sklearn", "statsmodels"}

VERDICT_MODULES = ("estimator.py", "comparables.py")


def _imported_names(path: pathlib.Path) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                found.add(node.module.split(".")[-1])
            found.update(alias.name for alias in node.names)
    return found


def test_the_verdict_path_imports_no_model(repo_root: pathlib.Path) -> None:
    valuation = repo_root / "src" / "dzialki" / "valuation"
    offenders: list[str] = []
    for name in VERDICT_MODULES:
        for imported in _imported_names(valuation / name):
            if imported in FORBIDDEN_IMPORTS:
                offenders.append(f"{name}: {imported}")
    assert offenders == []


def test_the_import_scan_catches_a_real_edge(tmp_path: pathlib.Path) -> None:
    """Non-vacuity companion. A scan over four small modules passes trivially."""
    seeded = tmp_path / "seeded.py"
    seeded.write_text("from ..model import predict_ppm2\n", encoding="utf-8")
    assert _imported_names(seeded) & FORBIDDEN_IMPORTS == {"model"}


def test_an_absence_has_no_numeric_price_attribute() -> None:
    """The type-level half of the same rule.

    A nullable price field on an absence is a field a caller renders after
    forgetting a check. There is nothing to reach for here.
    """
    import dataclasses

    from dzialki.valuation import Absence

    numeric = {"median", "low", "high", "median_ppm2", "price_pln", "estimate"}
    fields = {field.name for field in dataclasses.fields(Absence)}
    assert fields & numeric == set()
