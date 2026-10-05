"""
Minimal Alembic scaffold.

We start from db/schema.sql and evolve toward migrations later.
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config
fileConfig(config.config_file_name)

target_metadata = None


def _get_db_url() -> str:
    host = os.getenv("OPENDISCOURSE_DB_HOST", "127.0.0.1")
    port = os.getenv("OPENDISCOURSE_DB_PORT", "5432")
    name = os.getenv("OPENDISCOURSE_DB_NAME", "opendiscourse")
    user = os.getenv("OPENDISCOURSE_DB_USER", "opendiscourse")
    password = os.getenv("OPENDISCOURSE_DB_PASSWORD", "change_me")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{name}"


def run_migrations_offline() -> None:
    url = _get_db_url()
    context.configure(url=url, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = _get_db_url()
    connectable = engine_from_config(configuration, prefix="sqlalchemy.", poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
