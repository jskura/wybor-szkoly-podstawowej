"""R1.11–R1.15 — the environment is the pinned one and the migrations are
reproducible. Discharges V65(B).

Every constraint test in work item 2 runs on top of this. If a migration can
apply twice differently, or cannot be undone, those tests measure a schema nobody
can rebuild.
"""

from __future__ import annotations

import os
import pathlib
import subprocess

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.needs_db]

POSTGIS_OWNED = {"spatial_ref_sys", "geography_columns", "geometry_columns"}


def _alembic(repo_root: pathlib.Path, url: str, *args: str) -> None:
    subprocess.run(
        ["alembic", *args],
        cwd=repo_root,
        check=True,
        env={**os.environ, "DZIALKI_DATABASE_URL": url},
    )


def _heads(repo_root: pathlib.Path, url: str) -> list[str]:
    output = subprocess.run(
        ["alembic", "heads"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "DZIALKI_DATABASE_URL": url},
    ).stdout
    return [line.split()[0] for line in output.splitlines() if line.strip()]


def test_database_is_postgres_16_with_postgis_3(conn) -> None:
    version = conn.execute(
        "SELECT current_setting('server_version_num')::int"
    ).fetchone()[0]
    assert 160000 <= version < 170000

    postgis = conn.execute("SELECT postgis_lib_version()").fetchone()[0]
    assert postgis.startswith("3.")

    extensions = {
        row[0] for row in conn.execute("SELECT extname FROM pg_extension").fetchall()
    }
    assert "postgis" in extensions


def test_migrations_apply_to_empty_database_and_leave_one_head(
    conn, repo_root: pathlib.Path, migrated_db: str
) -> None:
    rows = conn.execute("SELECT version_num FROM alembic_version").fetchall()
    assert len(rows) == 1

    heads = _heads(repo_root, migrated_db)
    # A branched history is a merge conflict waiting to happen in production.
    assert len(heads) == 1
    assert rows[0][0] == heads[0]


def test_migrations_are_idempotent(
    repo_root: pathlib.Path, migrated_db: str, schema_digest
) -> None:
    before = schema_digest()
    _alembic(repo_root, migrated_db, "upgrade", "head")
    assert schema_digest() == before


def test_downgrade_to_base_removes_every_project_table(
    repo_root: pathlib.Path, migrated_db: str
) -> None:
    import psycopg

    _alembic(repo_root, migrated_db, "downgrade", "base")
    try:
        with psycopg.connect(migrated_db) as connection:
            remaining = {
                row[0]
                for row in connection.execute(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public'"
                ).fetchall()
            }
        assert remaining - POSTGIS_OWNED == set()
    finally:
        _alembic(repo_root, migrated_db, "upgrade", "head")


def test_upgrade_downgrade_upgrade_restores_identical_schema(
    repo_root: pathlib.Path, migrated_db: str, schema_digest
) -> None:
    """The test that catches a downgrade dropping a column but not its index."""
    before = schema_digest()
    _alembic(repo_root, migrated_db, "downgrade", "base")
    _alembic(repo_root, migrated_db, "upgrade", "head")
    assert schema_digest() == before
