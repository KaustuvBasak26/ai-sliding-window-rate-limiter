import time
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from config import resolve_static_file
from security import (
    LOGIN_ATTEMPT_LIMIT,
    check_login_rate_limit,
    create_session_token,
    passwords_match,
    sanitize_fulfilled,
    validate_production_config,
    verify_session,
)


def test_passwords_match_uses_constant_time_compare():
    assert passwords_match("secret", "secret") is True
    assert passwords_match("secret", "wrong") is False


def test_session_token_expires(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    token = create_session_token()
    assert verify_session(token) is True

    expires_raw = token.split(".", 1)[0]
    expired_token = f"{int(expires_raw) - 10}.{token.split('.', 1)[1]}"
    assert verify_session(expired_token) is False


def test_session_token_rejects_tampering(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    token = create_session_token()
    assert verify_session(f"{token}tampered") is False


def test_sanitize_fulfilled_removes_internal_keys():
    sanitized = sanitize_fulfilled(
        [
            {
                "label": "TENANT",
                "key": "rl:tenant:1",
                "limit": 10,
                "count": 1,
                "windowSeconds": 3600,
            }
        ]
    )
    assert "key" not in sanitized[0]


def test_validate_production_config_allows_public_deploy(monkeypatch):
    monkeypatch.setenv("ENV", "production")
    monkeypatch.delenv("APP_ACCESS_PASSWORD", raising=False)
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    validate_production_config()


def test_check_login_rate_limit_blocks_without_redis(monkeypatch):
    monkeypatch.setenv("ENV", "production")

    for _ in range(LOGIN_ATTEMPT_LIMIT):
        check_login_rate_limit(None, "127.0.0.1")

    with pytest.raises(HTTPException) as exc:
        check_login_rate_limit(None, "127.0.0.1")

    assert exc.value.status_code == 429


def test_check_login_rate_limit_blocks_with_redis(monkeypatch):
    monkeypatch.setenv("ENV", "production")
    redis_client = MagicMock()
    redis_client.incr.return_value = LOGIN_ATTEMPT_LIMIT + 1

    with pytest.raises(HTTPException) as exc:
        check_login_rate_limit(redis_client, "127.0.0.1")

    assert exc.value.status_code == 429


def test_resolve_static_file_blocks_traversal(tmp_path):
    static_dir = tmp_path / "dist"
    static_dir.mkdir()
    safe_file = static_dir / "index.html"
    safe_file.write_text("<html></html>", encoding="utf-8")

    resolved = resolve_static_file(str(static_dir), "index.html")
    assert resolved == safe_file.resolve()

    blocked = resolve_static_file(str(static_dir), "../outside.txt")
    assert blocked is None
