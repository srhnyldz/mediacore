from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request
from redis import Redis

from app.core.config import settings
from app.services.redis_client import get_redis_client


class RateLimitExceededError(Exception):
    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__(
            f"Rate limit exceeded. Retry after {retry_after_seconds} seconds."
        )


@dataclass(slots=True)
class RateLimitState:
    allowed: bool
    remaining: int
    retry_after_seconds: int


def enforce_download_rate_limit(
    request: Request,
    redis_client: Redis | None = None,
) -> RateLimitState:
    client = redis_client or get_redis_client()
    identifier = _resolve_request_identifier(request)
    return enforce_rate_limit(
        identifier=identifier,
        scope="downloads",
        redis_client=client,
    )


def enforce_rate_limit(
    identifier: str,
    scope: str,
    redis_client: Redis,
) -> RateLimitState:
    limit = settings.download_request_rate_limit
    window_seconds = settings.download_request_rate_window_seconds

    if limit <= 0 or window_seconds <= 0:
        return RateLimitState(allowed=True, remaining=limit, retry_after_seconds=0)

    key = f"rate_limit:{scope}:{identifier}"
    current_count = int(redis_client.incr(key))
    ttl_seconds = int(redis_client.ttl(key))

    if current_count == 1 or ttl_seconds < 0:
        redis_client.expire(key, window_seconds)
        ttl_seconds = window_seconds

    remaining = max(0, limit - current_count)
    if current_count > limit:
        raise RateLimitExceededError(retry_after_seconds=max(1, ttl_seconds))

    return RateLimitState(
        allowed=True,
        remaining=remaining,
        retry_after_seconds=max(0, ttl_seconds),
    )


def _resolve_request_identifier(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    client_host = request.client.host if request.client else None
    return client_host or "unknown"
