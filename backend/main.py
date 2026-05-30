# main.py
from pathlib import Path

from fastapi import Cookie, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import (
    get_cors_origins,
    get_pg_dsn,
    get_redis_url,
    get_static_dir,
    resolve_static_file,
    use_session_storage,
)
from models import RateLimitRequest, RateLimitResponse
from policy_resolver import PolicyResolver
from rate_limit_handler import evaluate_rate_limit
from rate_limiter import SlidingWindowRateLimiterTx
from security import (
    SESSION_COOKIE,
    SESSION_MAX_AGE_SECONDS,
    SecurityHeadersMiddleware,
    check_login_rate_limit,
    clear_login_attempts,
    create_session_token,
    get_app_access_password,
    is_production,
    passwords_match,
    require_session,
    verify_session,
)
from session_store import SessionStore

app = FastAPI(
    title="AI Rate Limiter Demo",
    docs_url=None if is_production() else "/docs",
    redoc_url=None if is_production() else "/redoc",
    openapi_url=None if is_production() else "/openapi.json",
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Demo-Session"],
)

session_store = None
redis_client = None
rate_limiter = None
policy_resolver = None


def get_session_store() -> SessionStore:
    global session_store
    if session_store is None:
        session_store = SessionStore()
    return session_store


def _init_persistent_backend() -> None:
    global redis_client, rate_limiter, policy_resolver
    if policy_resolver is not None:
        return
    import redis

    redis_client = redis.from_url(get_redis_url(), decode_responses=False)
    rate_limiter = SlidingWindowRateLimiterTx(redis_client)
    policy_resolver = PolicyResolver(get_pg_dsn())


def _get_demo_session_id(request: Request) -> str:
    header = request.headers.get("X-Demo-Session")
    if not header:
        raise HTTPException(
            status_code=400,
            detail="X-Demo-Session header is required in session storage mode",
        )
    try:
        return get_session_store().validate_session_id(header)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _get_backend(request: Request):
    if use_session_storage():
        demo_session = get_session_store().get(_get_demo_session_id(request))
        return demo_session.resolver, demo_session.limiter

    _init_persistent_backend()
    return policy_resolver, rate_limiter


class LoginRequest(BaseModel):
    password: str


@app.get("/health")
def health():
    payload = {"status": "ok", "storage": "session" if use_session_storage() else "postgres"}
    if use_session_storage():
        payload["activeSessions"] = get_session_store().active_count()
    return payload


@app.get("/auth/status")
def auth_status(rl_session: str | None = Cookie(None, alias=SESSION_COOKIE)):
    protected = bool(get_app_access_password())
    authenticated = verify_session(rl_session) if protected else True
    return {"protected": protected, "authenticated": authenticated}


@app.post("/auth/login")
def login(body: LoginRequest, request: Request):
    password = get_app_access_password()
    if not password:
        return {"ok": True}

    client_ip = request.client.host if request.client else "unknown"
    if use_session_storage():
        check_login_rate_limit(None, client_ip)
    else:
        _init_persistent_backend()
        check_login_rate_limit(redis_client, client_ip)

    if not passwords_match(body.password, password):
        raise HTTPException(status_code=401, detail="Invalid access password")

    if use_session_storage():
        clear_login_attempts(None, client_ip)
    else:
        clear_login_attempts(redis_client, client_ip)

    response = JSONResponse({"ok": True})
    response.set_cookie(
        key=SESSION_COOKIE,
        value=create_session_token(),
        httponly=True,
        secure=is_production(),
        samesite="lax",
        max_age=SESSION_MAX_AGE_SECONDS,
    )
    return response


@app.post("/auth/logout")
def logout():
    response = JSONResponse({"ok": True})
    response.delete_cookie(
        key=SESSION_COOKIE,
        httponly=True,
        secure=is_production(),
        samesite="lax",
    )
    return response


@app.post("/rate-limit/check", response_model=RateLimitResponse)
def check_rate_limit(
    body: RateLimitRequest,
    request: Request,
    _: None = Depends(require_session),
):
    if not body.userId or not body.modelId:
        raise HTTPException(status_code=400, detail="userId and modelId are required")

    resolver, limiter = _get_backend(request)
    return evaluate_rate_limit(
        body,
        resolver,
        limiter,
        scope_keys_by_request=use_session_storage(),
    )


static_dir = get_static_dir()
if static_dir:
    assets_dir = Path(static_dir) / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/")
    def serve_index():
        index = resolve_static_file(static_dir, "index.html")
        if index:
            return FileResponse(index)
        raise HTTPException(status_code=404)

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        if full_path.startswith(("rate-limit", "auth", "health", "docs", "openapi", "redoc")):
            raise HTTPException(status_code=404)

        static_file = resolve_static_file(static_dir, full_path)
        if static_file:
            return FileResponse(static_file)

        index = resolve_static_file(static_dir, "index.html")
        if index:
            return FileResponse(index)

        raise HTTPException(status_code=404)
