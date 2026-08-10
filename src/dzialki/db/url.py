"""One place that knows which driver SQLAlchemy should use.

``DZIALKI_DATABASE_URL`` holds a plain ``postgresql://`` URL, because psycopg,
``psql`` and ``pg_dump`` all read that form. SQLAlchemy reads the same form as a
request for psycopg2, which this project does not install. The conversion lives
here so the environment variable stays one string that every tool accepts.
"""

from __future__ import annotations

PLAIN_PREFIX = "postgresql://"
DRIVER_PREFIX = "postgresql+psycopg://"


def sqlalchemy_url(database_url: str) -> str:
    """Return ``database_url`` with the psycopg 3 driver named explicitly."""
    if database_url.startswith(DRIVER_PREFIX):
        return database_url
    if database_url.startswith(PLAIN_PREFIX):
        return DRIVER_PREFIX + database_url[len(PLAIN_PREFIX) :]
    return database_url
