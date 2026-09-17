import pytest
from app.rate_limit import rate_limit
from fastapi import HTTPException


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
