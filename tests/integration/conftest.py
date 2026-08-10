"""Database fixtures. Nothing outside this file opens a connection."""

from __future__ import annotations

import hashlib
import os
import pathlib
import re
import subprocess
from collections.abc import Iterator
from urllib.parse import urlsplit

import pytest

psycopg = pytest.importorskip("psycopg", reason="psycopg is not installed")

# Lines pg_dump emits that carry no schema meaning. Comparing digests without
# stripping them would report a difference for a changed dump timestamp.
_NOISE = re.compile(r"^(--|SET |SELECT pg_catalog\.set_config)")


@pytest.fixture(scope="session")
def test_database_url() -> str:
    url = os.environ.get("DZIALKI_TEST_DATABASE_URL")
    if not url:
        pytest.skip("DZIALKI_TEST_DATABASE_URL is not set")
    name = urlsplit(url).path.lstrip("/")
    # The suite drops and recreates this database. Pointing it at a real one
    # would destroy data, so the name must say it is disposable.
    assert name.endswith("_test"), f"refusing to run against {name!r}"
    return url


@pytest.fixture(scope="session")
def migrated_db(test_database_url: str, repo_root: pathlib.Path) -> str:
    """A database built only by the migrations.

    Never from model metadata: a schema the test helper builds would let a
    migration bug pass every constraint test that runs on top of it.
    """
    url = urlsplit(test_database_url)
    name = url.path.lstrip("/")
    admin = test_database_url.replace(f"/{name}", "/postgres")

    with psycopg.connect(admin, autocommit=True) as conn:
        conn.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        conn.execute(f'CREATE DATABASE "{name}"')

    subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=repo_root,
        check=True,
        env={**os.environ, "DZIALKI_DATABASE_URL": test_database_url},
    )
    return test_database_url


@pytest.fixture
def conn(migrated_db: str) -> Iterator[psycopg.Connection]:
    with psycopg.connect(migrated_db, autocommit=False) as connection:
        connection.execute("SET TIME ZONE 'UTC'")
        yield connection
        connection.rollback()


@pytest.fixture
def schema_digest(migrated_db: str):
    """SHA-256 over a normalized ``pg_dump --schema-only``."""

    def digest() -> str:
        dump = subprocess.run(
            [
                "pg_dump",
                "--schema-only",
                "--no-owner",
                "--no-privileges",
                migrated_db,
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        lines = sorted(
            line
            for line in dump.splitlines()
            if line.strip() and not _NOISE.match(line)
        )
        return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()

    return digest
