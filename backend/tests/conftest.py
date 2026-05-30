import os
import sys
from unittest.mock import MagicMock, patch

import pytest
import redis
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

with patch("psycopg2.connect", return_value=MagicMock()):
    from main import app, rate_limiter, policy_resolver

from rate_limiter import SlidingWindowRateLimiterTx
from models import RateLimitRequest


@pytest.fixture
def redis_mock():
    mock = MagicMock(spec=redis.Redis)
    return mock


@pytest.fixture
def rate_limiter_instance(redis_mock):
    return SlidingWindowRateLimiterTx(redis_mock)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_request():
    return RateLimitRequest(
        userId="test-user",
        modelId="gpt-4o",
        tenantId="test-tenant",
        modelTier="premium",
    )


@pytest.fixture
def mock_policies():
    from policy_resolver import EffectiveLimit

    return [
        EffectiveLimit(
            key="rl:user:test-user:model:gpt-4o",
            window_seconds=3600,
            limit=100,
            label="USER_MODEL",
            scope="USER_MODEL",
        ),
        EffectiveLimit(
            key="rl:tenant:test-tenant",
            window_seconds=3600,
            limit=500,
            label="TENANT",
            scope="TENANT",
        ),
    ]
