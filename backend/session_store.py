import os
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException

from memory_rate_limiter import InMemorySlidingWindowRateLimiter
from sqlite_policy_resolver import SqlitePolicyResolver

SQLITE_INIT = Path(__file__).resolve().parent / "migrations" / "sqlite_init.sql"
SESSION_IDLE_SECONDS = int(os.getenv("SESSION_IDLE_SECONDS", "3600"))
MAX_ACTIVE_SESSIONS = int(os.getenv("MAX_DEMO_SESSIONS", "200"))


@dataclass
class DemoSession:
    resolver: SqlitePolicyResolver
    limiter: InMemorySlidingWindowRateLimiter
    last_access: float
    conn: sqlite3.Connection


class SessionStore:
    """One ephemeral SQLite DB + in-memory counters per browser session id."""

    def __init__(self):
        self._sessions: dict[str, DemoSession] = {}
        self._lock = threading.Lock()
        self._init_sql = SQLITE_INIT.read_text(encoding="utf-8")

    @staticmethod
    def validate_session_id(session_id: str) -> str:
        try:
            parsed = uuid.UUID(session_id)
        except ValueError as exc:
            raise ValueError("Invalid demo session id") from exc
        return str(parsed)

    def active_count(self) -> int:
        with self._lock:
            return len(self._sessions)

    def get(self, session_id: str) -> DemoSession:
        session_id = self.validate_session_id(session_id)

        with self._lock:
            self._cleanup_idle_sessions_locked()
            session = self._sessions.get(session_id)
            if session is None:
                self._evict_oldest_if_full_locked()
                session = self._create_session_locked()
                self._sessions[session_id] = session
            session.last_access = time.time()
            return session

    def _create_session_locked(self) -> DemoSession:
        conn = sqlite3.connect(":memory:", check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.executescript(self._init_sql)
        return DemoSession(
            resolver=SqlitePolicyResolver(conn),
            limiter=InMemorySlidingWindowRateLimiter(),
            last_access=time.time(),
            conn=conn,
        )

    def _evict_oldest_if_full_locked(self) -> None:
        if len(self._sessions) < MAX_ACTIVE_SESSIONS:
            return
        oldest_id = min(self._sessions, key=lambda sid: self._sessions[sid].last_access)
        self._close_session_by_id_locked(oldest_id)

    def _close_session_by_id_locked(self, session_id: str) -> None:
        session = self._sessions.pop(session_id, None)
        if session is not None:
            session.conn.close()

    def _cleanup_idle_sessions_locked(self) -> None:
        cutoff = time.time() - SESSION_IDLE_SECONDS
        stale = [
            session_id
            for session_id, session in self._sessions.items()
            if session.last_access < cutoff
        ]
        for session_id in stale:
            self._close_session_by_id_locked(session_id)
