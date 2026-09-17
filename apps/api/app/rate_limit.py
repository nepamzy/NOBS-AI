"""Fixed-window rate limiting on the same Redis instance RQ already uses —
a real, free hardening step against login/signup brute-forcing and
runaway LLM cost from chat abuse. Not a full WAF/firewall (that would be
Cloudflare or similar, in front of the domain — a separate, optional
step) but a genuinely useful first layer that costs nothing extra.

Fails OPEN (lets the request through) if Redis itself is unreachable —
a rate limiter should never be the reason the whole API goes down.
"""

import redis
from fastapi import HTTPException, Request

from app.config import settings

_redis_conn = redis.from_url(settings.redis_url)


def rate_limit(key_prefix: str, max_requests: int, window_seconds: int):
    """FastAPI dependency factory. Keyed by client IP — good enough to stop
    a single brute-force script without needing the user to be authenticated
    yet (login/signup happen before that's possible)."""

    def dependency(request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        key = f"ratelimit:{key_prefix}:{client_ip}"
        try:
            count = _redis_conn.incr(key)
            if count == 1:
                _redis_conn.expire(key, window_seconds)
        except redis.RedisError:
            return
        if count > max_requests:
            raise HTTPException(
                status_code=429,
                detail="Too many requests — wait a bit before trying again.",
            )

    return dependency
