import pytest
import redis
from app.config import settings
from app.rate_limit import rate_limit
from fastapi import HTTPException


def _redis_reachable() -> bool:
    try:
        redis.from_url(settings.redis_url).ping()
        return True
    except redis.RedisError:
        return False


class _FakeRedis:
    def __init__(self):
        self.counts: dict[str, int] = {}

    def incr(self, key):
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    def expire(self, key, seconds):
        pass


class _FakeRequest:
    def __init__(self, ip):
        self.client = type("Client", (), {"host": ip})()


def test_allows_requests_under_the_limit(monkeypatch):
    import app.rate_limit as rate_limit_module

    monkeypatch.setattr(rate_limit_module, "_redis_conn", _FakeRedis())
    dependency = rate_limit("test", max_requests=3, window_seconds=60)
    request = _FakeRequest("1.2.3.4")

    dependency(request)
    dependency(request)
    dependency(request)  # exactly at the limit — still allowed


def test_blocks_requests_over_the_limit(monkeypatch):
    import app.rate_limit as rate_limit_module

    monkeypatch.setattr(rate_limit_module, "_redis_conn", _FakeRedis())
    dependency = rate_limit("test", max_requests=2, window_seconds=60)
    request = _FakeRequest("1.2.3.4")

    dependency(request)
    dependency(request)
    with pytest.raises(HTTPException) as exc_info:
        dependency(request)
    assert exc_info.value.status_code == 429


def test_different_ips_are_limited_independently(monkeypatch):
    import app.rate_limit as rate_limit_module

    monkeypatch.setattr(rate_limit_module, "_redis_conn", _FakeRedis())
    dependency = rate_limit("test", max_requests=1, window_seconds=60)

    dependency(_FakeRequest("1.1.1.1"))
    dependency(_FakeRequest("2.2.2.2"))  # different IP, own counter — not blocked


def test_fails_open_when_redis_is_unreachable(monkeypatch):
    import app.rate_limit as rate_limit_module
    import redis

    class _BrokenRedis:
        def incr(self, key):
            raise redis.exceptions.ConnectionError("redis is down")

    monkeypatch.setattr(rate_limit_module, "_redis_conn", _BrokenRedis())
    dependency = rate_limit("test", max_requests=1, window_seconds=60)

    dependency(_FakeRequest("1.2.3.4"))
    dependency(_FakeRequest("1.2.3.4"))  # would be blocked if Redis worked — must not raise


# These two exercise the real /auth/login route against the real
# Redis-backed limiter (not the fake above), to regression-test the
# conftest `_reset_rate_limits` autouse fixture: every starlette TestClient
# reports the same "testclient" host, so without that fixture resetting
# `ratelimit:*` before each test, the first test exhausting the real
# 10-requests/300s login limit would leak into the second and incorrectly
# 429 it. Skipped (not failed) when no Redis is reachable, matching the
# rate limiter's own fail-open behavior — there's nothing to regress on.
@pytest.mark.skipif(
    not _redis_reachable(), reason="no reachable Redis to test the real limiter against"
)
def test_login_rate_limit_exhausts_within_one_test(client):
    for _ in range(10):
        client.post("/auth/login", json={"email": "nobody@example.com", "password": "wrong"})
    response = client.post("/auth/login", json={"email": "nobody@example.com", "password": "wrong"})
    assert response.status_code == 429


@pytest.mark.skipif(
    not _redis_reachable(), reason="no reachable Redis to test the real limiter against"
)
def test_login_rate_limit_does_not_leak_into_the_next_test(client):
    response = client.post("/auth/login", json={"email": "nobody@example.com", "password": "wrong"})
    assert response.status_code == 401
