"""Source registry loading.

Every default here fails closed. A source arrives disabled, with no robots
evidence, and at the slowest rate limit. Getting this backwards is the failure
V14 exists to prevent: a connector that starts fetching because somebody forgot
to say it should not.

The rate limit itself is not written here. It lives in ``config/params.yml``
(FR-75) and the caller passes it in, so the number has one home rather than one
in the loader and another in a migration.
"""

from __future__ import annotations

import pathlib
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

from .errors import ConfigError

SourceKind = Literal["portal", "registry", "api"]


class Source(BaseModel):
    """One place the pipeline may fetch from."""

    model_config = ConfigDict(extra="forbid")

    name: str
    kind: SourceKind
    base_url: str | None = None
    enabled: bool = False
    robots_ok: bool = False
    rate_limit_rpm: int


def load_sources(
    path: pathlib.Path | str, *, default_rate_limit_rpm: int
) -> dict[str, Source]:
    """Read the source registry from ``path``, keyed by name.

    ``default_rate_limit_rpm`` is required, not optional. A source that states no
    limit gets the slow one, and the caller reads that number from the parameter
    file rather than the loader inventing it.
    """
    path = pathlib.Path(path)
    if not path.exists():
        raise ConfigError(f"{path} is missing. The source registry is committed.")

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path} is not valid YAML: {exc}") from exc

    entries = raw.get("sources")
    if not isinstance(entries, list) or not entries:
        raise ConfigError(f"{path} declares no sources under the 'sources' key")

    sources: dict[str, Source] = {}
    for entry in entries:
        try:
            source = Source(**{"rate_limit_rpm": default_rate_limit_rpm, **entry})
        except (TypeError, ValidationError) as exc:
            name = entry.get("name", "<unnamed>") if isinstance(entry, dict) else entry
            kind = entry.get("kind") if isinstance(entry, dict) else None
            raise ConfigError(
                f"{path}: source {name!r} has an invalid 'kind' of {kind!r} "
                f"or another invalid field: {exc}"
            ) from exc
        if source.name in sources:
            raise ConfigError(f"{path}: source {source.name!r} is declared twice")
        sources[source.name] = source
    return sources
