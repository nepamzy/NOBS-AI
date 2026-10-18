from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

# pool_recycle: Supabase drops idle SSL connections; recycling every 5 min
# stops the worker from reusing a dead one mid-job (that's what left videos stuck).
# TCP keepalives stop the network from silently dropping an idle connection.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
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
