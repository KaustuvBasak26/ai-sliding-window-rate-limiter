import time

from memory_rate_limiter import InMemorySlidingWindowRateLimiter


def test_allows_requests_under_limit():
    limiter = InMemorySlidingWindowRateLimiter()
    allowed, count = limiter.check_and_consume("key", window_seconds=60, limit=3)
    assert allowed is True
    assert count == 1


def test_blocks_when_limit_reached():
    limiter = InMemorySlidingWindowRateLimiter()
    for _ in range(3):
        allowed, _ = limiter.check_and_consume("key", window_seconds=60, limit=3)
        assert allowed is True

    allowed, count = limiter.check_and_consume("key", window_seconds=60, limit=3)
    assert allowed is False
    assert count == 3


def test_keys_are_isolated():
    limiter = InMemorySlidingWindowRateLimiter()
    limiter.check_and_consume("a", window_seconds=60, limit=1)
    allowed, count = limiter.check_and_consume("b", window_seconds=60, limit=1)
    assert allowed is True
    assert count == 1
