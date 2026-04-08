from functools import lru_cache

import redis
from redis import Redis

from app.core.config import settings


@lru_cache(maxsize=1)
def get_redis_client() -> Redis:
    # API katmani ve operasyon servisleri ayni Redis ayarlariyla calisir.
    return redis.Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=settings.redis_socket_timeout_seconds,
        socket_timeout=settings.redis_socket_timeout_seconds,
        health_check_interval=30,
    )
