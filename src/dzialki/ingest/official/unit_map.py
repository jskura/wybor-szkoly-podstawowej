"""The TERYT to BDL unit-id mapping (D97).

Data, never derivation. A BDL unit id looks like a padded TERYT code, so the
obvious implementation is a slice and a pad. That implementation is wrong
wherever the pattern does not hold, and its failure mode is the worst kind: it
produces a well-formed id for a different place, so the pipeline fetches a real
series for the wrong powiat and every check downstream passes.

The map therefore refuses to be helpful. An unmapped code raises rather than
falling back, and an unverified file raises rather than serving entries nobody
has checked.
"""

from __future__ import annotations

import pathlib

import yaml

from dzialki.config.errors import ConfigError


class UnmappedUnit(KeyError):
    """No BDL unit id is recorded for this TERYT code.

    Deliberately not a lookup that returns ``None``. A caller who forgets to
    check ``None`` builds a URL with the word "None" in it and gets a 404, which
    reads as "the source is down" rather than "we never mapped this unit".
    """


class UnitMapUnverified(ConfigError):
    """The mapping exists but nobody has checked it against the register.

    Serving unverified entries would give a price series for a place we cannot
    prove we asked about.
    """


class UnitMap:
    """A read-only TERYT to BDL unit-id lookup."""

    def __init__(self, powiats: dict[str, str], *, evidence: str | None) -> None:
        self._powiats = dict(powiats)
        self.evidence = evidence

    def __getitem__(self, teryt: str) -> str:
        try:
            return self._powiats[teryt]
        except KeyError as exc:
            raise UnmappedUnit(
                f"no BDL unit id recorded for TERYT {teryt!r}. "
                "Add it to config/teryt_bdl.yml from the BDL unit register. "
                "Do not derive it from the TERYT code."
            ) from exc

    def __contains__(self, teryt: object) -> bool:
        return teryt in self._powiats

    def __len__(self) -> int:
        return len(self._powiats)

    def codes(self) -> list[str]:
        return sorted(self._powiats)


def load_unit_map(path: pathlib.Path | str) -> UnitMap:
    """Read the mapping from ``path``.

    Raises ``UnitMapUnverified`` while `verified` is false, which is how the
    committed empty map stops the GUS connector from running against codes
    nobody has recorded.
    """
    path = pathlib.Path(path)
    if not path.exists():
        raise ConfigError(f"{path} is missing. The unit map is committed.")

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path} is not valid YAML: {exc}") from exc

    if not raw.get("verified"):
        raise UnitMapUnverified(
            f"{path} is not verified against the BDL unit register. "
            "Fill `powiats`, record the evidence path, and set `verified: true` "
            "in the same commit."
        )

    powiats = raw.get("powiats") or {}
    if not isinstance(powiats, dict):
        raise ConfigError(f"{path}: `powiats` must be a mapping")
    return UnitMap(powiats, evidence=raw.get("evidence"))
