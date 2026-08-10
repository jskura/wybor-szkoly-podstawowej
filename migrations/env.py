"""Alembic environment.

The URL comes from the settings object, so an unset ``DZIALKI_DATABASE_URL``
fails loudly here rather than connecting to something convenient.
"""

from __future__ import annotations

from alembic import context
from sqlalchemy import engine_from_config, pool

from dzialki.config import Settings
from dzialki.db.url import sqlalchemy_url

config = context.config
config.set_main_option("sqlalchemy.url", sqlalchemy_url(Settings().database_url))

# No model metadata. Migrations are written by hand, and the test suite builds
# its database only from them (V65(B)). Autogenerate against metadata would let
# a migration bug hide behind a schema the helper built.
target_metadata = None


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
