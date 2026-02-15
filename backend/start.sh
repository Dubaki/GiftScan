#!/usr/bin/env bash
# Start script for Render.com

set -o errexit

echo "Starting GiftScan API..."

# Run migrations on startup (in case of new deployments)
echo "Applying database migrations..."
alembic upgrade head

echo "Starting uvicorn server on port $PORT..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
