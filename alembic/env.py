"""
Alembic migration environment.

Reads DB URL from FormNest settings and configures migration targets.
For online migrations the synchronous ``postgresql://`` driver is used
(alembic does not support asyncpg).  Set DATABASE_URL or the individual
POSTGRES_* variables in your .env before running ``alembic upgrade head``.
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from server.core.config import settings

# Import all models so that Base.metadata is populated for --autogenerate
from server.models import *  # noqa: F401, F403
from server.models.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Resolve the database URL from application settings and convert to a
# synchronous driver URL that Alembic's engine_from_config can use.
db_url = settings.DATABASE_URL
if not db_url:
    raise RuntimeError(
        "DATABASE_URL is not configured. "
        "Set DATABASE_URL (or POSTGRES_* vars) in your .env file before running Alembic."
    )
# Alembic requires the synchronous psycopg2/psycopg driver — strip asyncpg.
if "asyncpg" in db_url:
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
# Strip sslmode= query parameter that psycopg2 passes as a connect_arg instead.
if "sslmode=" in db_url:
    import re
    db_url = re.sub(r"([?&])sslmode=[^&]*(&|$)", r"\1", db_url)
    db_url = db_url.rstrip("?&")

config.set_main_option("sqlalchemy.url", db_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — generates SQL without a DB connection."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode — connects to DB."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
