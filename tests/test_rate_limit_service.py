from types import SimpleNamespace

from app.services import rate_limit_service


class FakeRedisClient:
    def __init__(self) -> None:
        self.values: dict[str, int] = {}
        self.expirations: dict[str, int] = {}

    def incr(self, key: str) -> int:
        self.values[key] = self.values.get(key, 0) + 1
        return self.values[key]

    def ttl(self, key: str) -> int:
        return self.expirations.get(key, -1)

    def expire(self, key: str, seconds: int) -> bool:
        self.expirations[key] = seconds
        return True


def test_enforce_rate_limit_sets_expiry(monkeypatch) -> None:
    fake_redis = FakeRedisClient()
    monkeypatch.setattr(rate_limit_service.settings, "download_request_rate_limit", 2)
    monkeypatch.setattr(
        rate_limit_service.settings,
        "download_request_rate_window_seconds",
        60,
    )

    state = rate_limit_service.enforce_rate_limit(
        identifier="127.0.0.1",
        scope="downloads",
        redis_client=fake_redis,
    )

    assert state.allowed is True
    assert state.remaining == 1
    assert fake_redis.expirations["rate_limit:downloads:127.0.0.1"] == 60


def test_enforce_rate_limit_raises_when_limit_exceeded(monkeypatch) -> None:
    fake_redis = FakeRedisClient()
    monkeypatch.setattr(rate_limit_service.settings, "download_request_rate_limit", 1)
    monkeypatch.setattr(
        rate_limit_service.settings,
        "download_request_rate_window_seconds",
        45,
    )

    rate_limit_service.enforce_rate_limit(
        identifier="127.0.0.1",
        scope="downloads",
        redis_client=fake_redis,
    )

    try:
        rate_limit_service.enforce_rate_limit(
            identifier="127.0.0.1",
            scope="downloads",
            redis_client=fake_redis,
        )
    except rate_limit_service.RateLimitExceededError as exc:
        assert exc.retry_after_seconds == 45
    else:  # pragma: no cover - test guvencesi
        raise AssertionError("RateLimitExceededError bekleniyordu.")


def test_resolve_request_identifier_prefers_forwarded_for() -> None:
    request = SimpleNamespace(
        headers={"x-forwarded-for": "198.51.100.10, 10.0.0.1"},
        client=SimpleNamespace(host="127.0.0.1"),
    )

    assert rate_limit_service._resolve_request_identifier(request) == "198.51.100.10"
