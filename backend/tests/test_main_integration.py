import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from policy_resolver import EffectiveLimit


class TestRateLimitCheckEndpoint:
    """Integration tests for /rate-limit/check endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from main import app
        return TestClient(app)

    def test_check_rate_limit_missing_userid(self, client):
        """Test request with missing userId."""
        response = client.post(
            "/rate-limit/check",
            json={"modelId": "gpt-4o"}
        )
        
        # FastAPI returns 422 for validation errors
        assert response.status_code == 422

    def test_check_rate_limit_missing_modelid(self, client):
        """Test request with missing modelId."""
        response = client.post(
            "/rate-limit/check",
            json={"userId": "test-user"}
        )
        
        assert response.status_code == 422

    def test_check_rate_limit_allowed(self, client):
        """Test successful rate limit check (allowed)."""
        with patch('main.policy_resolver.resolve') as mock_resolve, \
             patch('main.rate_limiter.check_and_consume') as mock_consume:
            
            # Mock policy resolution
            mock_resolve.return_value = [
                EffectiveLimit(
                    key="rl:test",
                    window_seconds=3600,
                    limit=100,
                    label="TEST",
                    scope="GLOBAL"
                )
            ]
            
            # Mock rate limiter returning allowed
            mock_consume.return_value = (True, 1)
            
            response = client.post(
                "/rate-limit/check",
                json={
                    "userId": "test-user",
                    "modelId": "gpt-4o",
                    "tenantId": "test-tenant",
                    "modelTier": "premium"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["allowed"] is True
            assert data["count"] >= 0
            assert data["limit"] > 0

    def test_check_rate_limit_blocked(self, client):
        """Test rate limit check (blocked)."""
        with patch('main.policy_resolver.resolve') as mock_resolve, \
             patch('main.rate_limiter.check_and_consume') as mock_consume:
            
            mock_resolve.return_value = [
                EffectiveLimit(
                    key="rl:test",
                    window_seconds=3600,
                    limit=10,
                    label="TEST_LIMIT",
                    scope="MODEL_TIER"
                )
            ]
            
            # Mock rate limiter returning blocked
            mock_consume.return_value = (False, 11)
            
            response = client.post(
                "/rate-limit/check",
                json={
                    "userId": "test-user",
                    "modelId": "gpt-4o",
                    "tenantId": "test-tenant",
                    "modelTier": "free"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["allowed"] is False
            assert data["cause"] is not None
            assert "exceeded" in data["cause"].lower()

    def test_check_rate_limit_multiple_policies(self, client):
        """Test with multiple policies (all passing)."""
        with patch('main.policy_resolver.resolve') as mock_resolve, \
             patch('main.rate_limiter.check_and_consume') as mock_consume:
            
            mock_resolve.return_value = [
                EffectiveLimit(
                    key="rl:user:1:model:1",
                    window_seconds=3600,
                    limit=100,
                    label="USER_MODEL",
                    scope="USER_MODEL"
                ),
                EffectiveLimit(
                    key="rl:tenant:1",
                    window_seconds=3600,
                    limit=500,
                    label="TENANT",
                    scope="TENANT"
                ),
            ]
            
            # All policies pass
            mock_consume.side_effect = [(True, 10), (True, 50)]
            
            response = client.post(
                "/rate-limit/check",
                json={
                    "userId": "user-1",
                    "modelId": "gpt-4o",
                    "tenantId": "tenant-1",
                    "modelTier": "premium"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["allowed"] is True
            # Should have fulfilled policies
            assert "fulfilled" in data
            assert len(data["fulfilled"]) > 0

    def test_health_endpoint(self, client):
        """Test /health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestPolicySelection:
    """Test primary policy selection logic."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from main import app
        return TestClient(app)

    def test_primary_policy_minimum_left_capacity(self, client):
        """Test that primary policy is selected by minimum remaining capacity."""
        with patch('main.policy_resolver.resolve') as mock_resolve, \
             patch('main.rate_limiter.check_and_consume') as mock_consume:
            
            # Two policies: one with 10 left, one with 100 left
            # The one with 10 left should be primary (tighter constraint)
            mock_resolve.return_value = [
                EffectiveLimit(
                    key="rl:tier:premium",
                    window_seconds=3600,
                    limit=100,
                    label="PREMIUM_TIER",
                    scope="MODEL_TIER"
                ),
                EffectiveLimit(
                    key="rl:tenant:ent",
                    window_seconds=3600,
                    limit=50,
                    label="TENANT",
                    scope="TENANT"
                ),
            ]
            
            # Tier has 90 left (100-10), Tenant has 10 left (50-40)
            mock_consume.side_effect = [(True, 10), (True, 40)]
            
            response = client.post(
                "/rate-limit/check",
                json={
                    "userId": "user-1",
                    "modelId": "gpt-4o",
                    "tenantId": "ent",
                    "modelTier": "premium"
                }
            )
            
            data = response.json()
            # Primary should be TENANT (minimum left=10)
            assert data["limit"] == 50
            assert data["count"] == 40
