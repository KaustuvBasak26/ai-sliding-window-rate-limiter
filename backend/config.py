import os
from pathlib import Path
from urllib.parse import unquote, urlparse

from security import is_production


def normalize_pg_dsn(dsn: str) -> str:
    """Convert a postgres:// or postgresql:// URL to a psycopg2 DSN."""
    if dsn.startswith("postgres://"):
        dsn = dsn.replace("postgres://", "postgresql://", 1)

    if dsn.startswith("postgresql://"):
        parsed = urlparse(dsn)
        dbname = parsed.path.lstrip("/")
        password = unquote(parsed.password or "")
        port = parsed.port or 5432
        parts = [
            f"dbname={dbname}",
            f"user={parsed.username}",
            f"password={password}",
            f"host={parsed.hostname}",
            f"port={port}",
        ]
        if parsed.hostname and parsed.hostname not in ("localhost", "127.0.0.1"):
            parts.append("sslmode=require")
        return " ".join(parts)

    return dsn


def get_pg_dsn() -> str:
    default = (
        "dbname=rate_limiter user=postgres password=postgres "
        "host=localhost port=5432"
    )
    raw = os.getenv("DATABASE_URL") or os.getenv("RL_PG_DSN") or default
    return normalize_pg_dsn(raw)


def use_session_storage() -> bool:
    mode = os.getenv("STORAGE_MODE", "").lower()
    if mode == "session":
        return True
    if mode in ("postgres", "persistent"):
        return False
    if os.getenv("RENDER", "").lower() == "true" and not os.getenv("DATABASE_URL"):
        return True
    return False


def get_redis_url() -> str:
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")


def get_cors_origins() -> list[str]:
    if is_production():
        return []

    raw = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://localhost:3000",
    )
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def get_static_dir() -> str | None:
    explicit = os.getenv("STATIC_DIR")
    if explicit:
        return explicit
    default = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "frontend",
        "dist",
    )
    return default if os.path.isdir(default) else None


def resolve_static_file(static_dir: str, relative_path: str) -> Path | None:
    base = Path(static_dir).resolve()
    target = (base / relative_path).resolve()
    if base not in target.parents and target != base:
        return None
    return target if target.is_file() else None
