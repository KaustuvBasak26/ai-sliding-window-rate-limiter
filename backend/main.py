# main.py
from pathlib import Path

from fastapi import Cookie, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import redis

from config import get_cors_origins, get_pg_dsn, get_redis_url, get_static_dir, resolve_static_file
from models import RateLimitRequest, RateLimitResponse
from rate_limiter import SlidingWindowRateLimiterTx
from policy_resolver import PolicyResolver, SCOPE_PRECEDENCE
from security import (
    SecurityHeadersMiddleware,
    check_login_rate_limit,
    clear_login_attempts,
    create_session_token,
    get_app_access_password,
    is_production,
    passwords_match,
    require_session,
    sanitize_cause,
    sanitize_fulfilled,
    SESSION_COOKIE,
    SESSION_MAX_AGE_SECONDS,
    verify_session,
)

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
    allow_headers=["Content-Type"],
)

redis_client = redis.from_url(get_redis_url(), decode_responses=False)
rate_limiter = SlidingWindowRateLimiterTx(redis_client)
policy_resolver = PolicyResolver(get_pg_dsn())


class LoginRequest(BaseModel):
    password: str


@app.get("/health")
def health():
    return {"status": "ok"}


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
    check_login_rate_limit(redis_client, client_ip)

    if not passwords_match(body.password, password):
        raise HTTPException(status_code=401, detail="Invalid access password")

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
    _: None = Depends(require_session),
):
    if not body.userId or not body.modelId:
        raise HTTPException(status_code=400, detail="userId and modelId are required")

    try:
        policies = policy_resolver.resolve(body)
    except Exception as e:
        detail = "Policy resolve error" if is_production() else f"Policy resolve error: {e}"
        raise HTTPException(status_code=500, detail=detail)

    evaluated = []
    for p in policies:
        allowed, count = rate_limiter.check_and_consume(
            key=p.key,
            window_seconds=p.window_seconds,
            limit=p.limit,
        )
        evaluated.append(
            {
                "policy": p,
                "allowed": allowed,
                "count": count,
            }
        )

    failures = [e for e in evaluated if not e["allowed"]]

    if failures:
        failures_sorted = sorted(
            failures,
            key=lambda x: SCOPE_PRECEDENCE.get(x["policy"].scope, 0),
            reverse=True,
        )
        f = failures_sorted[0]
        p = f["policy"]
        count = f["count"]
        cause = (
            f"{p.label} exceeded: {count}/{p.limit} in the last {p.window_seconds} seconds"
        )
        if not is_production():
            cause += f" (key={p.key})"

        if len(failures_sorted) > 1:
            other = []
            for o in failures_sorted[1:]:
                op = o["policy"]
                other.append(f"{op.label} ({o['count']}/{op.limit})")
            cause += "; also violated: " + ", ".join(other)

        if is_production():
            cause = sanitize_cause(cause)

        return RateLimitResponse(
            allowed=False,
            limit=p.limit,
            count=count,
            windowSeconds=p.window_seconds,
            cause=cause,
        )

    if not evaluated:
        raise HTTPException(status_code=500, detail="No policy resolved")

    allowed_entries = [e for e in evaluated if e["allowed"]]
    if not allowed_entries:
        raise HTTPException(status_code=500, detail="No allowed policies after evaluation")

    def _sort_key(entry):
        left = entry["policy"].limit - entry["count"]
        prec = SCOPE_PRECEDENCE.get(entry["policy"].scope, 0)
        return (left, -prec)

    allowed_entries.sort(key=_sort_key)
    primary_entry = allowed_entries[0]
    primary = primary_entry["policy"]
    primary_count = primary_entry["count"]

    fulfilled = [
        {
            "label": e["policy"].label,
            "key": e["policy"].key,
            "limit": e["policy"].limit,
            "count": e["count"],
            "windowSeconds": e["policy"].window_seconds,
        }
        for e in evaluated
        if e["allowed"]
    ]

    if is_production():
        fulfilled = sanitize_fulfilled(fulfilled)

    return RateLimitResponse(
        allowed=True,
        limit=primary.limit,
        count=primary_count,
        windowSeconds=primary.window_seconds,
        fulfilled=fulfilled,
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
