"""Anchor loading.

This module holds no coordinate and no address. Every value comes from the YAML
file the caller names. R1.6 parses this file and fails on any float inside
Poland's bounding box or any address-shaped string, so a hardcoded fallback
cannot be added later without the suite noticing.
"""

from __future__ import annotations

import pathlib

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

from .errors import AnchorConfigMissing, ConfigError

EXAMPLE_PATH = "config/anchors.example.yml"


class Anchor(BaseModel):
    """One place the owner cares about, and the centre of one 25 km ring.

    ``street`` and ``house_number`` are optional because the example file carries
    neither. In a real ``anchors.yml`` they are the values V7(b) scans git
    history for.
    """

    model_config = ConfigDict(extra="forbid")

    label: str
    lat: float
    lon: float
    street: str | None = None
    house_number: str | None = None


def load_anchors(path: pathlib.Path | str) -> dict[str, Anchor]:
    """Read anchors from ``path``.

    Raises ``AnchorConfigMissing`` when the file is absent, naming the example
    file so the reader knows what to copy. Never returns a default: an anchor the
    owner did not choose would silently move both rings.
    """
    path = pathlib.Path(path)
    if not path.exists():
        raise AnchorConfigMissing(
            f"{path} is missing. Copy {EXAMPLE_PATH} to config/anchors.yml "
            "and fill in the real values. The file stays gitignored."
        )

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path} is not valid YAML: {exc}") from exc

    entries = raw.get("anchors")
    if not isinstance(entries, dict) or not entries:
        raise ConfigError(f"{path} declares no anchors under the 'anchors' key")

    anchors: dict[str, Anchor] = {}
    for key, value in entries.items():
        try:
            anchors[key] = Anchor(**value)
        except (TypeError, ValidationError) as exc:
            raise ConfigError(f"{path}: anchor {key!r} is invalid: {exc}") from exc
    return anchors
