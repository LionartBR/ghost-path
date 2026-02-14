#!/bin/sh
# Entrypoint — waits for PostgreSQL before running migrations and starting uvicorn.
# Railway doesn't have Docker Compose's depends_on healthcheck, so we retry.

set -e

MAX_RETRIES=30
RETRY_INTERVAL=2
RETRIES=0

echo "Waiting for database to be ready..."

while [ $RETRIES -lt $MAX_RETRIES ]; do
    if python -c "
import os, sys, socket
url = os.environ.get('DATABASE_URL', '')
if not url:
    sys.exit(1)
parts = url.split('@')[-1].split('/')[0]
host = parts.split(':')[0]
port = int(parts.split(':')[1]) if ':' in parts else 5432
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(3)
s.connect((host, port))
s.close()
" 2>/dev/null; then
        echo "Database is ready!"
        break
    fi
    RETRIES=$((RETRIES + 1))
    echo "Database not ready yet (attempt $RETRIES/$MAX_RETRIES). Retrying in ${RETRY_INTERVAL}s..."
    sleep $RETRY_INTERVAL
done

if [ $RETRIES -eq $MAX_RETRIES ]; then
    echo "ERROR: Could not connect to database after $MAX_RETRIES attempts."
    exit 1
fi

echo "Running database migrations..."
alembic upgrade head

echo "Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
