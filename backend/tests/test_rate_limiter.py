import pytest
from unittest.mock import MagicMock
from rate_limiter import SlidingWindowRateLimiterTx


class TestSlidingWindowRateLimiter:
    """Unit tests for SlidingWindowRateLimiterTx."""

    def test_check_and_consume_allowed_when_under_limit(self, redis_mock):
        """Test that request is allowed when under limit."""
        # Mock zcard to return values less than limit
        redis_mock.zcard.return_value = 5
        redis_mock.zadd.return_value = 1
        
        limiter = SlidingWindowRateLimiterTx(redis_mock)
        allowed, count = limiter.check_and_consume(
            key="rl:test",
            window_seconds=3600,
            limit=100
        )
        
        assert allowed is True
        assert count >= 0

    def test_check_and_consume_returns_tuple(self, redis_mock):
        """Test that check_and_consume returns a tuple of (allowed, count)."""
        redis_mock.zcard.return_value = 50
        redis_mock.zadd.return_value = 1
        
        limiter = SlidingWindowRateLimiterTx(redis_mock)
        result = limiter.check_and_consume(
            key="rl:test",
            window_seconds=3600,
            limit=100
        )
        
        # Should return a tuple with two elements
        assert isinstance(result, tuple)
        assert len(result) == 2
        allowed, count = result
        assert isinstance(allowed, bool)
        assert isinstance(count, int)

    def test_check_and_consume_with_zero_count(self, redis_mock):
        """Test behavior with zero count in window."""
        redis_mock.zcard.return_value = 0
        redis_mock.zadd.return_value = 1
        
        limiter = SlidingWindowRateLimiterTx(redis_mock)
        allowed, count = limiter.check_and_consume(
            key="rl:test",
            window_seconds=3600,
            limit=100
        )
        
        # First request should be allowed
        assert allowed is True
        assert count >= 0

    def test_check_and_consume_with_high_count(self, redis_mock):
        """Test behavior with count well over limit."""
        redis_mock.zcard.return_value = 150
        redis_mock.zadd.return_value = 1
        
        limiter = SlidingWindowRateLimiterTx(redis_mock)
        allowed, count = limiter.check_and_consume(
            key="rl:test",
            window_seconds=3600,
            limit=100
        )
        
        # Should return a valid result even with high count
        assert isinstance(allowed, bool)
        assert isinstance(count, int)

    def test_check_and_consume_handles_redis_error(self, redis_mock):
        """Test graceful handling of Redis errors."""
        redis_mock.zcard.side_effect = Exception("Redis connection error")
        
        limiter = SlidingWindowRateLimiterTx(redis_mock)
        allowed, count = limiter.check_and_consume(
            key="rl:test",
            window_seconds=3600,
            limit=100
        )
        
        # Should return a tuple result even on error
        assert isinstance(allowed, bool)
        assert isinstance(count, int)
