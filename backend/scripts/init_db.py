#!/usr/bin/env python3
"""Apply SQL migrations when the database has not been initialized."""

from pathlib import Path
import sys
import time

import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import get_pg_dsn


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
MIGRATION_FILES = [
    "001_create_types_and_tables.sql",
    "002_seed_demo_data.sql",
]
MAX_CONNECT_ATTEMPTS = 10
CONNECT_RETRY_SECONDS = 3


def database_is_initialized(conn) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = 'rate_limit_policy'
            )
            """
        )
        return bool(cur.fetchone()[0])


def run_migration(conn, migration_path: Path) -> None:
    sql = migration_path.read_text(encoding="utf-8")
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    print(f"Applied migration: {migration_path.name}")


def connect_with_retry(dsn: str):
    last_error = None
    for attempt in range(1, MAX_CONNECT_ATTEMPTS + 1):
        try:
            return psycopg2.connect(dsn)
        except psycopg2.OperationalError as exc:
            last_error = exc
            if attempt == MAX_CONNECT_ATTEMPTS:
                break
            print(
                f"Database not ready (attempt {attempt}/{MAX_CONNECT_ATTEMPTS}); "
                f"retrying in {CONNECT_RETRY_SECONDS}s..."
            )
            time.sleep(CONNECT_RETRY_SECONDS)

    raise last_error


def main() -> None:
    dsn = get_pg_dsn()
    conn = connect_with_retry(dsn)
    try:
        if database_is_initialized(conn):
            print("Database already initialized; skipping migrations.")
            return

        for filename in MIGRATION_FILES:
            migration_path = MIGRATIONS_DIR / filename
            if not migration_path.exists():
                raise FileNotFoundError(f"Missing migration file: {migration_path}")
            run_migration(conn, migration_path)

        print("Database initialization complete.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
