#!/usr/bin/env bash
# Runs from repo root on Render (no rootDir). Also works locally from backend/.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FRONTEND_DIR="$REPO_ROOT/frontend"

echo "==> Installing Python dependencies"
cd "$SCRIPT_DIR"
pip install -r requirements.txt

echo "==> Building frontend"
cd "$FRONTEND_DIR"
npm ci
npm run build

if [ ! -f "$FRONTEND_DIR/dist/index.html" ]; then
  echo "Frontend build failed: frontend/dist/index.html not found" >&2
  exit 1
fi

echo "==> Frontend build OK ($(wc -c < "$FRONTEND_DIR/dist/index.html") bytes index.html)"
