from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

# pool_recycle: Supabase drops idle SSL connections; recycling every 5 min
# stops the worker from reusing a dead one mid-job (that's what left videos stuck).
# TCP keepalives stop the network from silently dropping an idle connection.
#
# prepare_threshold=None: Supabase's connection string for this app goes
# through Supavisor/PgBouncer in transaction mode, which does NOT support
# server-side prepared statements (each transaction can land on a different
# real Postgres backend) — see Supabase's own docs: "Transaction mode does
# not support prepared statements... turn off prepared statements for your
# connection library." Without this, psycopg3 auto-prepares a statement
# after running the same query 5 times on one connection object, and the
# NEXT time the pooler happens to route that connection to a different
# backend, that backend has never heard of "_pg3_0" —
# psycopg.errors.InvalidSqlStatementName: prepared statement "_pg3_0" does
# not exist. Hit for the first time on a video_generation-stage query that
# re-fetched the same Video row enough times in one run to cross that
# threshold; every later run was always one unlucky pooler hop away from
# the same crash regardless of query shape.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
        "prepare_threshold": None,
    },
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
