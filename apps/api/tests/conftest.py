"""Test fixtures. Models use Postgres-specific types (UUID, JSONB, Enum), so
tests run against a real, throwaway Postgres database rather than sqlite —
created fresh each test session and dropped afterward, never touching the
dev database configured in .env.

Requires a reachable Postgres server (see README: docker compose up -d, or
a local install) using the same credentials as DATABASE_URL, just against
the "postgres" maintenance database to create/drop the test DB.
"""

import pytest
from app.config import settings
from app.db import Base
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

TEST_DB_NAME = "nobs_ai_test"


def _admin_url():
    return make_url(settings.database_url).set(database="postgres")


@pytest.fixture(scope="session")
def test_db_url():
    admin_engine = create_engine(_admin_url(), isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}"'))
        conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
    admin_engine.dispose()

    url = make_url(settings.database_url).set(database=TEST_DB_NAME)
    yield url

    admin_engine = create_engine(_admin_url(), isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}"'))
    admin_engine.dispose()


@pytest.fixture(scope="session")
def db_engine(test_db_url):
    from app import models  # noqa: F401 — registers all tables on Base.metadata

    engine = create_engine(test_db_url)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    """app/rate_limit.py keys its fixed-window counters by client IP, and
    every starlette TestClient reports the same host ("testclient") — so
    without this, signup/login tests sharing a pytest session share ONE
    counter across all of them and trip the real 429 after
    max_requests, regardless of which test is running. That's a test
    environment gap, not production behavior to change: production really
    is meant to rate-limit repeated requests from one IP. This only resets
    the counters between tests so each test starts with a clean window,
    the same way db_session's rollback keeps Postgres state from leaking
    between tests. Scoped to just the `ratelimit:*` keys it owns — never
    touches anything else that might live on the same Redis instance."""
    import redis
    from app.config import settings

    try:
        conn = redis.from_url(settings.redis_url)
        keys = list(conn.scan_iter("ratelimit:*"))
        if keys:
            conn.delete(*keys)
    except redis.RedisError:
        # No reachable Redis in this environment — the rate limiter itself
        # fails open in that case too, so there's nothing to reset.
        pass
    yield


@pytest.fixture
def db_session(db_engine) -> Session:
    """One test = one transaction, rolled back at the end, so tests don't
    leak state into each other without needing to truncate every table.

    autoflush=False matches app/db.py's real SessionLocal exactly — a
    default (autoflush=True) test session silently masked a real bug
    (pipeline.py's THUMBNAIL stage re-querying rows it had just db.add()'d
    in the same call, finding none under the real session's autoflush=False
    and uploading nothing) that every test here passed regardless, because
    the test session auto-flushed those pending inserts before the
    assertions' own queries ran — something production's session never
    does. Keep this matched to SessionLocal's settings going forward."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection, autoflush=False)()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session, monkeypatch):
    """TestClient wired to the transactional db_session instead of a real
    connection pool, with job enqueueing stubbed out — API tests shouldn't
    need Redis/a worker running to verify request/response behavior.

    Pre-authenticated as an admin user (matching the old implicit
    single-user semantics — Nobert is the primary/default user of the
    app), so existing tests didn't need to change when auth was added. Use
    the `client_as` fixture for a non-admin user."""
    from datetime import UTC, datetime, timedelta

    import app.routers.clips as clips_router
    import app.routers.videos as videos_router
    from app.auth.security import generate_session_token, hash_lookup_value, hash_password
    from app.config import settings
    from app.db import get_db
    from app.main import app
    from app.models.auth import AuthSession
    from app.models.enums import UserRole
    from app.models.user import User
    from fastapi.testclient import TestClient

    monkeypatch.setattr(settings, "secret_key", "test-secret-key")

    enqueued: list[dict] = []

    def fake_enqueue(video_id, run_research):
        enqueued.append({"video_id": video_id, "run_research": run_research})
        return "fake-job-id"

    monkeypatch.setattr(videos_router, "enqueue_pipeline_start", fake_enqueue)

    enqueued_clips: list[dict] = []

    def fake_enqueue_clip(source_video_id):
        enqueued_clips.append({"source_video_id": source_video_id})
        return "fake-clip-job-id"

    monkeypatch.setattr(clips_router, "enqueue_clip_pipeline_start", fake_enqueue_clip)

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    admin = User(
        email="nobert@local",
        display_name="Nobert",
        password_hash=hash_password("test-password"),
        role=UserRole.ADMIN,
    )
    db_session.add(admin)
    db_session.flush()
    token = generate_session_token()
    db_session.add(
        AuthSession(
            user_id=admin.id,
            token_hash=hash_lookup_value(token),
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
    )
    db_session.flush()

    test_client = TestClient(app, headers={"Authorization": f"Bearer {token}"})
    test_client.enqueued_jobs = enqueued  # type: ignore[attr-defined]
    test_client.enqueued_clip_jobs = enqueued_clips  # type: ignore[attr-defined]
    test_client.admin_user = admin  # type: ignore[attr-defined]

    yield test_client

    app.dependency_overrides.clear()
