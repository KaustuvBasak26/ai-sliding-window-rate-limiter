#!/usr/bin/env bash
set -euo pipefail

python -c "from security import validate_production_config; validate_production_config()"

if [ "${STORAGE_MODE:-}" = "session" ]; then
  echo "Session storage mode — skipping Postgres migrations"
else
  python scripts/init_db.py
fi

exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
