#!/usr/bin/env bash
# Render build script (runs with cwd = backend when rootDir is set).
set -euo pipefail

echo "==> Installing Python dependencies"
pip install -r requirements.txt

echo "==> Building frontend"
cd ../frontend
npm ci
npm run build

if [ ! -f dist/index.html ]; then
  echo "Frontend build failed: dist/index.html not found" >&2
  exit 1
fi

echo "==> Frontend build OK ($(wc -c < dist/index.html) bytes index.html)"
