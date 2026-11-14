import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Commands that only run migration scripts and never compare the models with
# the database. Importing the whole app (settings + every model) for these is
# pure startup cost — and this runs on every boot of the hosted API, where the
# CPU is slow. Anything not listed (revision --autogenerate, check, ...) still
# loads the models exactly as before.
_FAST_COMMANDS = {"upgrade", "downgrade", "current", "heads", "history", "stamp"}


def _command_name() -> str | None:
    opts = getattr(config, "cmd_opts", None)
    cmd = getattr(opts, "cmd", None)
    return cmd[0].__name__ if cmd else None


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    from app.config import settings  # reads .env for local development

    return settings.database_url


def _target_metadata():
    if _command_name() in _FAST_COMMANDS:
        return None
    from app import models  # noqa: F401 — registers all model classes on Base
    from app.db import Base

    return Base.metadata


target_metadata = _target_metadata()


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # Built directly from the database URL, bypassing ConfigParser's
    # set_main_option/get_section round-trip — that path treats any literal
    # "%" in the URL (e.g. a password's URL-encoded "@" as "%40") as its own
    # interpolation syntax and raises ValueError.
    connectable = create_engine(_database_url(), poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
