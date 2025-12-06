import pytest
from unittest.mock import Mock, MagicMock
import redis
from fastapi.testclient import TestClient
import sys
import os

# Add parent directory to path so we can import main modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app, rate_limiter, policy_resolver
from rate_limiter import SlidingWindowRateLimiterTx
from models import RateLimitRequest


@pytest.fixture
def redis_mock():
    """Mock Redis client."""
    mock = MagicMock(spec=redis.Redis)
    return mock


@pytest.fixture
def rate_limiter_instance(redis_mock):
    """Create a rate limiter with mocked Redis."""
    return SlidingWindowRateLimiterTx(redis_mock)


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def sample_request():
    """Sample rate limit request."""
    return RateLimitRequest(
        userId="test-user",
        modelId="gpt-4o",
        tenantId="test-tenant",
        modelTier="premium"
    )


@pytest.fixture
def mock_policies():
    """Sample policies for testing."""
    from policy_resolver import EffectiveLimit
    return [
        EffectiveLimit(
            key="rl:user:test-user:model:gpt-4o",
            window_seconds=3600,
            limit=100,
            label="USER_MODEL",
            scope="USER_MODEL"
        ),
        EffectiveLimit(
            key="rl:tenant:test-tenant",
            window_seconds=3600,
            limit=500,
            label="TENANT",
            scope="TENANT"
        ),
    ]
