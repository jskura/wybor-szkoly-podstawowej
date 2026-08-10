"""The register class to regime lookup.

The regime is data. This module reads ``config/register_classes.yml`` and holds
no class symbol of its own, so a symbol added to the table is covered on the day
it is added. A branch on a symbol is how a wrong regime gets hardcoded and then
outlives the table that was meant to govern it (D106, D117).

Matching is exact and case sensitive. A case-folded match would read `Br` as `BR`
and `dr` as `Dr`, and two of those pairs sit in different regimes.
"""

from __future__ import annotations

import dataclasses
import datetime
import pathlib

import yaml

from .errors import RegisterClassTableError, UnknownRegisterClass

# The three values the column accepts. A boolean held two, and the product has
# three outcomes: the farmland badge, the forest badge, and no badge.
REGIMES: tuple[str, ...] = ("agricultural", "forest", "none")

ROW_FIELDS: tuple[str, ...] = ("symbol", "name", "regime", "source")


@dataclasses.dataclass(frozen=True)
class RegisterClass:
    """One row of the table."""

    symbol: str
    name: str
    regime: str
    source: str


class RegisterClassTable:
    """A read-only symbol to regime lookup."""

    def __init__(
        self,
        rows: tuple[RegisterClass, ...],
        *,
        regulation: str,
        regulation_verified: bool,
        consolidated_text_date: datetime.date | None,
    ) -> None:
        self._rows = tuple(rows)
        self._by_symbol = {row.symbol: row for row in self._rows}
        self.regulation = regulation
        self.regulation_verified = regulation_verified
        self.consolidated_text_date = consolidated_text_date

    @property
    def rows(self) -> tuple[RegisterClass, ...]:
        """Every row, in file order."""
        return self._rows

    def get(self, symbol: object) -> RegisterClass | None:
        """The row, or ``None`` when the table does not carry the symbol."""
        if not isinstance(symbol, str):
            return None
        return self._by_symbol.get(symbol)

    def _row(self, symbol: str) -> RegisterClass:
        found = self.get(symbol)
        if found is None:
            raise UnknownRegisterClass(
                f"the register class {symbol!r} is absent from the table. "
                "Add it to config/register_classes.yml with its regime and its "
                "source. Do not infer the regime from the symbol."
            )
        return found

    def regime_of(self, symbol: str) -> str:
        return self._row(symbol).regime

    def name_of(self, symbol: str) -> str:
        return self._row(symbol).name

    def symbols(self) -> tuple[str, ...]:
        return tuple(row.symbol for row in self._rows)


def _as_date(value: object, path: pathlib.Path, field: str) -> datetime.date | None:
    if value is None:
        return None
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str):
        try:
            return datetime.date.fromisoformat(value)
        except ValueError as exc:
            raise RegisterClassTableError(f"{path}: {field} is not a date") from exc
    raise RegisterClassTableError(f"{path}: {field} is not a date")


def load_register_classes(path: pathlib.Path | str) -> RegisterClassTable:
    """Read the table from ``path``.

    Every row needs a symbol, a name, a regime and the document that decided the
    regime. A row without provenance fails the load, because a regime nobody can
    trace is a regime nobody can check.
    """
    path = pathlib.Path(path)
    if not path.exists():
        raise RegisterClassTableError(f"{path} is missing. The table is committed.")

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise RegisterClassTableError(f"{path} is not valid YAML: {exc}") from exc

    entries = raw.get("classes")
    if not isinstance(entries, list) or entries == []:
        raise RegisterClassTableError(f"{path}: `classes` must be a non-empty list")

    rows: list[RegisterClass] = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise RegisterClassTableError(f"{path}: every row must be a mapping")
        missing = [field for field in ROW_FIELDS if not entry.get(field)]
        if missing:
            raise RegisterClassTableError(
                f"{path}: the row {entry.get('symbol')!r} lacks {missing[0]}"
            )
        regime = entry["regime"]
        if regime not in REGIMES:
            raise RegisterClassTableError(
                f"{path}: the row {entry['symbol']!r} declares the regime "
                f"{regime!r}, which is outside {REGIMES}"
            )
        symbol = entry["symbol"]
        if symbol in seen:
            raise RegisterClassTableError(
                f"{path}: the symbol {symbol!r} appears twice, so its regime "
                "would depend on the row order"
            )
        seen.add(symbol)
        rows.append(
            RegisterClass(
                symbol=symbol,
                name=entry["name"],
                regime=regime,
                source=entry["source"],
            )
        )

    if "regulation" not in raw or "regulation_verified" not in raw:
        raise RegisterClassTableError(
            f"{path}: the file must state its regulation and whether anybody "
            "has checked it"
        )
    return RegisterClassTable(
        tuple(rows),
        regulation=raw["regulation"],
        regulation_verified=bool(raw["regulation_verified"]),
        consolidated_text_date=_as_date(
            raw.get("consolidated_text_date"), path, "consolidated_text_date"
        ),
    )
