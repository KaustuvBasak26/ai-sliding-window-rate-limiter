import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def session_client(monkeypatch):
    monkeypatch.setenv("STORAGE_MODE", "session")
    with patch("psycopg2.connect", return_value=MagicMock()):
        from main import app

        return TestClient(app)


class TestSessionStorageMode:
    def test_health_reports_session_storage(self, session_client, monkeypatch):
        monkeypatch.setenv("STORAGE_MODE", "session")
        response = session_client.get("/health")
        assert response.status_code == 200
        assert response.json()["storage"] == "session"

    def test_missing_session_header_is_rejected(self, session_client, monkeypatch):
        monkeypatch.setenv("STORAGE_MODE", "session")
        response = session_client.post(
            "/rate-limit/check",
            json={
                "userId": "ent-user-1",
                "modelId": "gpt-4o",
                "tenantId": "enterprise_co",
                "modelTier": "premium",
            },
        )
        assert response.status_code == 400

    def test_fresh_session_starts_at_zero(self, session_client, monkeypatch):
        monkeypatch.setenv("STORAGE_MODE", "session")
        session_id = str(uuid.uuid4())
        payload = {
            "userId": "ent-user-1",
            "modelId": "gpt-4o",
            "tenantId": "enterprise_co",
            "modelTier": "premium",
        }
        headers = {"X-Demo-Session": session_id}

        first = session_client.post("/rate-limit/check", json=payload, headers=headers)
        assert first.status_code == 200
        assert first.json()["count"] == 1

        second = session_client.post("/rate-limit/check", json=payload, headers=headers)
        assert second.status_code == 200
        assert second.json()["count"] == 2

    def test_new_session_resets_counters(self, session_client, monkeypatch):
        monkeypatch.setenv("STORAGE_MODE", "session")
        payload = {
            "userId": "ent-user-1",
            "modelId": "gpt-4o",
            "tenantId": "enterprise_co",
            "modelTier": "premium",
        }

        session_a = str(uuid.uuid4())
        session_b = str(uuid.uuid4())

        session_client.post(
            "/rate-limit/check",
            json=payload,
            headers={"X-Demo-Session": session_a},
        )
        session_client.post(
            "/rate-limit/check",
            json=payload,
            headers={"X-Demo-Session": session_a},
        )

        reset = session_client.post(
            "/rate-limit/check",
            json=payload,
            headers={"X-Demo-Session": session_b},
        )
        assert reset.status_code == 200
        assert reset.json()["count"] == 1

    def test_strict_user_model_policy_in_session(self, session_client, monkeypatch):
        monkeypatch.setenv("STORAGE_MODE", "session")
        session_id = str(uuid.uuid4())
        headers = {"X-Demo-Session": session_id}
        payload = {
            "userId": "ent-user-2",
            "modelId": "gpt-4o",
            "tenantId": "enterprise_co",
            "modelTier": "premium",
        }

        for _ in range(10):
            response = session_client.post("/rate-limit/check", json=payload, headers=headers)
            assert response.status_code == 200
            assert response.json()["allowed"] is True

        blocked = session_client.post("/rate-limit/check", json=payload, headers=headers)
        assert blocked.status_code == 200
        assert blocked.json()["allowed"] is False

    def test_different_request_contexts_have_isolated_counters(
        self, session_client, monkeypatch
    ):
        monkeypatch.setenv("STORAGE_MODE", "session")
        session_id = str(uuid.uuid4())
        headers = {"X-Demo-Session": session_id}

        free_payload = {
            "userId": "free-user-1",
            "modelId": "tiny-model",
            "tenantId": "free_co",
            "modelTier": "free",
        }
        for _ in range(10):
            response = session_client.post(
                "/rate-limit/check", json=free_payload, headers=headers
            )
            assert response.status_code == 200
            assert response.json()["allowed"] is True

        blocked = session_client.post(
            "/rate-limit/check", json=free_payload, headers=headers
        )
        assert blocked.json()["allowed"] is False
        assert blocked.json()["count"] == 10

        changed_payload = {
            "userId": "free-user-2",
            "modelId": "tiny-model2",
            "tenantId": "free_co2",
            "modelTier": "free",
        }
        fresh = session_client.post(
            "/rate-limit/check", json=changed_payload, headers=headers
        )
        assert fresh.status_code == 200
        assert fresh.json()["allowed"] is True
        assert fresh.json()["count"] == 1
        assert fresh.json()["contextMatch"]["tenantMatched"] is False
        assert fresh.json()["contextMatch"]["userMatched"] is False
        assert fresh.json()["contextMatch"]["modelMatched"] is False
        assert fresh.json()["contextMatch"]["tierMatched"] is True
