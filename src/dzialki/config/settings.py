"""Runtime settings, read from the environment.

The database URL has no default. A fallback to a local database would let the
test suite point at the wrong place and report every constraint test as passing
against a schema nobody meant to build.
"""

from __future__ import annotations

import os

from .errors import ConfigError

ENV_DATABASE_URL = "DZIALKI_DATABASE_URL"


class Settings:
    """Everything the application reads from the environment."""

    def __init__(self) -> None:
        url = os.environ.get(ENV_DATABASE_URL)
        if not url:
            raise ConfigError(
                f"{ENV_DATABASE_URL} is not set. There is no default: a fallback "
                "would let the application connect to the wrong database and "
                "still look healthy."
            )
        self.database_url = url
