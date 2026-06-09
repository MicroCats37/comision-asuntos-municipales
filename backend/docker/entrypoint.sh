#!/bin/bash
set -e

echo "Waiting for database to be ready..."
# Wait for db to be truly ready using env vars (DB_*)
until uv run python -c "import psycopg2; psycopg2.connect(host='${DB_HOST:-db}', user='${DB_USER:-cam_user}', password='${DB_PASSWORD:-changeme}', dbname='${DB_NAME:-cam_db}')" 2>/dev/null; do
    echo "Database is unavailable - sleeping"
    sleep 2
done

echo "Database is ready!"

echo "Running migrations..."
uv run python manage.py migrate --noinput

echo "Collecting static files..."
# Fix ownership of staticfiles volume (may have been created by root in previous runs)
chown -R appuser:appuser /app/staticfiles 2>/dev/null || true
uv run python manage.py collectstatic --noinput

echo "Starting server..."
# Use gosu to run gunicorn as non-root appuser for security
exec gosu appuser uv run gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2
