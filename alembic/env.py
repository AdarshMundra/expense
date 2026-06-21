from __future__ import annotations

import asyncio
import re
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

from app.database.base import Base
from app.database import models  # noqa: F401 - ensures models are registered
from app.config import settings

config = context.config


def _clean_pg_url(url: str) -> tuple[str, dict]:
    """Strip asyncpg-incompatible query params and return (clean_url, connect_args)."""
    connect_args: dict = {}
    if "sslmode=require" in url or "sslmode=prefer" in url:
        connect_args["ssl"] = True
    clean = re.sub(r"[?&]sslmode=[^&]*", "", url)
    clean = re.sub(r"[?&]channel_binding=[^&]*", "", clean)
    clean = re.sub(r"\?$", "", clean)
    return clean, connect_args

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    clean_url, connect_args = _clean_pg_url(settings.database_url)
    connectable = create_async_engine(
        clean_url,
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
