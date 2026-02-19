#!/bin/bash
set -e

echo "Waiting for PostgreSQL to be ready..."
until python -c "
import psycopg2, os, sys
try:
    conn = psycopg2.connect(
        dbname=os.environ.get('POSTGRES_DB', 'support_tickets'),
        user=os.environ.get('POSTGRES_USER', 'postgres'),
        password=os.environ.get('POSTGRES_PASSWORD', 'postgres'),
        host=os.environ.get('POSTGRES_HOST', 'db'),
        port=os.environ.get('POSTGRES_PORT', '5432'),
    )
    conn.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
"; do
  echo "PostgreSQL not ready — retrying in 2 seconds..."
  sleep 2
done

echo "PostgreSQL is ready."

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting Gunicorn..."
exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 2 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
