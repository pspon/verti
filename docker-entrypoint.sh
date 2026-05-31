#!/usr/bin/env bash
set -euo pipefail

# Build the SQLite DB on the mounted volume from the bundled flat files.
# Idempotent: skips import if the database already contains data.
python -m verti.migrate

exec uvicorn web.main:app --host 0.0.0.0 --port "${PORT:-8080}"
