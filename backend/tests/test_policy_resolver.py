import pytest
from unittest.mock import MagicMock, patch
from policy_resolver import PolicyResolver, EffectiveLimit, SCOPE_PRECEDENCE
from models import RateLimitRequest


class TestScopePrecedence:
    """Test scope precedence ordering."""

    def test_scope_precedence_ordering(self):
        """Verify scope precedence values."""
        assert SCOPE_PRECEDENCE["USER_MODEL"] > SCOPE_PRECEDENCE["API_KEY"]
        assert SCOPE_PRECEDENCE["API_KEY"] > SCOPE_PRECEDENCE["TENANT"]
        assert SCOPE_PRECEDENCE["TENANT"] > SCOPE_PRECEDENCE["MODEL"]
        assert SCOPE_PRECEDENCE["MODEL"] > SCOPE_PRECEDENCE["MODEL_TIER"]
        assert SCOPE_PRECEDENCE["MODEL_TIER"] > SCOPE_PRECEDENCE["GLOBAL"]

    def test_user_model_most_specific(self):
        """Verify USER_MODEL has highest precedence."""
        assert SCOPE_PRECEDENCE["USER_MODEL"] == 6


class TestPolicyResolver:
    """Unit tests for PolicyResolver."""

    @pytest.fixture
    def mock_resolver(self):
        """Create resolver with mocked DB connection."""
        with patch('policy_resolver.psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn
            resolver = PolicyResolver("mock_dsn")
            return resolver, mock_conn

    def test_get_tenant_id_found(self, mock_resolver):
        """Test retrieving existing tenant ID."""
        resolver, mock_conn = mock_resolver
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (1,)
        
        with patch.object(resolver, '_fetch_one', return_value={'id': 1}):
            tenant_id = resolver._get_tenant_id("enterprise_co")
        
        assert tenant_id == 1

    def test_get_tenant_id_not_found(self, mock_resolver):
        """Test tenant not found returns None."""
        resolver, _ = mock_resolver
        with patch.object(resolver, '_fetch_one', return_value=None):
            tenant_id = resolver._get_tenant_id("nonexistent")
        
        assert tenant_id is None

    def test_get_tenant_id_none_input(self, mock_resolver):
        """Test None input returns None."""
        resolver, _ = mock_resolver
        tenant_id = resolver._get_tenant_id(None)
        assert tenant_id is None

    def test_redis_key_for_policy_global(self):
        """Test Redis key generation for GLOBAL scope."""
        policy = {"scope": "GLOBAL"}
        resolver = PolicyResolver.__new__(PolicyResolver)
        
        key = resolver._redis_key_for_policy(policy)
        assert key == "rl:global"

    def test_redis_key_for_policy_tenant(self):
        """Test Redis key generation for TENANT scope."""
        policy = {"scope": "TENANT", "tenant_id": 1}
        resolver = PolicyResolver.__new__(PolicyResolver)
        
        key = resolver._redis_key_for_policy(policy)
        assert key == "rl:tenant:1"

    def test_redis_key_for_policy_user_model(self):
        """Test Redis key generation for USER_MODEL scope."""
        policy = {"scope": "USER_MODEL", "user_id": 5, "model_id": 3}
        resolver = PolicyResolver.__new__(PolicyResolver)
        
        key = resolver._redis_key_for_policy(policy)
        assert key == "rl:user:5:model:3"

    def test_redis_key_for_policy_model_tier(self):
        """Test Redis key generation for MODEL_TIER scope."""
        policy = {"scope": "MODEL_TIER", "model_tier_id": 2}
        resolver = PolicyResolver.__new__(PolicyResolver)
        
        key = resolver._redis_key_for_policy(policy)
        assert key == "rl:modeltier:2"
