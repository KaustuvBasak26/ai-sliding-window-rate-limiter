#!/usr/bin/env bash
set -euo pipefail

python -c "from security import validate_production_config; validate_production_config()"
python scripts/init_db.py
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
