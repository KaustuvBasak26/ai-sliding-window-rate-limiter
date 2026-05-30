import hashlib
import hmac
import os
import threading
import time
from typing import Optional

from fastapi import Cookie, HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

SESSION_COOKIE = "rl_session"
SESSION_MAX_AGE_SECONDS = 86400
LOGIN_ATTEMPT_LIMIT = 10
LOGIN_ATTEMPT_WINDOW_SECONDS = 300
_login_attempts: dict[str, tuple[int, float]] = {}
_login_attempts_lock = threading.Lock()


def is_production() -> bool:
    env = os.getenv("ENV", "").lower()
    if env == "production":
        return True
    return os.getenv("RENDER", "").lower() == "true"


def get_app_access_password() -> Optional[str]:
    password = os.getenv("APP_ACCESS_PASSWORD")
    return password if password else None


def get_session_secret() -> str:
    secret = os.getenv("SESSION_SECRET") or get_app_access_password()
    if secret:
        return secret
    return "dev-session-secret"


def validate_production_config() -> None:
    """Optional sanity checks for production deploy. Public demo needs no secrets."""
    return


def create_session_token() -> str:
    expires_at = int(time.time()) + SESSION_MAX_AGE_SECONDS
    payload = str(expires_at)
    signature = hmac.new(
        get_session_secret().encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload}.{signature}"


def verify_session(token: Optional[str]) -> bool:
    if not token or "." not in token:
        return False

    expires_raw, signature = token.split(".", 1)
    try:
        expires_at = int(expires_raw)
    except ValueError:
        return False

    if expires_at < int(time.time()):
        return False

    expected = hmac.new(
        get_session_secret().encode(),
        expires_raw.encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(signature, expected)


def passwords_match(provided: str, expected: str) -> bool:
    return hmac.compare_digest(provided.encode(), expected.encode())


def require_session(session: Optional[str] = Cookie(None, alias=SESSION_COOKIE)) -> None:
    if not get_app_access_password():
        return
    if not verify_session(session):
        raise HTTPException(status_code=401, detail="Authentication required")


def check_login_rate_limit(redis_client, client_ip: str) -> None:
    if not is_production():
        return

    if redis_client is not None:
        key = f"rl:login_attempts:{client_ip}"
        attempts = redis_client.incr(key)
        if attempts == 1:
            redis_client.expire(key, LOGIN_ATTEMPT_WINDOW_SECONDS)
        if int(attempts) > LOGIN_ATTEMPT_LIMIT:
            raise HTTPException(
                status_code=429,
                detail="Too many login attempts. Try again later.",
            )
        return

    now = time.time()
    with _login_attempts_lock:
        count, window_start = _login_attempts.get(client_ip, (0, now))
        if now - window_start > LOGIN_ATTEMPT_WINDOW_SECONDS:
            count, window_start = 0, now
        count += 1
        _login_attempts[client_ip] = (count, window_start)
        if count > LOGIN_ATTEMPT_LIMIT:
            raise HTTPException(
                status_code=429,
                detail="Too many login attempts. Try again later.",
            )


def clear_login_attempts(redis_client, client_ip: str) -> None:
    if not is_production():
        return
    if redis_client is not None:
        redis_client.delete(f"rl:login_attempts:{client_ip}")
        return
    with _login_attempts_lock:
        _login_attempts.pop(client_ip, None)


def sanitize_cause(cause: str) -> str:
    if "(key=" in cause:
        return cause.split("(key=")[0].rstrip()
    return cause


def sanitize_fulfilled(fulfilled: list[dict]) -> list[dict]:
    return [
        {
            "label": item["label"],
            "limit": item["limit"],
            "count": item["count"],
            "windowSeconds": item["windowSeconds"],
        }
        for item in fulfilled
    ]


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), interest-cohort=()"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        if is_production():
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"
        return response
