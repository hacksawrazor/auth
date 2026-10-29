#!/bin/bash
# Docker entrypoint script for PyAuthService
# Handles migrations and container startup

set -e

echo "🐳 PyAuthService - Starting..."

# Wait for PostgreSQL only when it is the selected database engine.
if [ "${DB_ENGINE:-postgresql}" != "sqlite3" ] && [ -n "${POSTGRES_HOST:-}" ]; then
  echo "⏳ Waiting for database at ${POSTGRES_HOST}:${POSTGRES_PORT:-5432}..."
  while ! nc -z "${POSTGRES_HOST}" "${POSTGRES_PORT:-5432}" 2>/dev/null && \
        ! python -c "import socket; s = socket.socket(); s.settimeout(1); s.connect(('${POSTGRES_HOST}', int('${POSTGRES_PORT:-5432}'))); s.close()" 2>/dev/null; do
    sleep 1
  done
  echo "✅ Database is ready"
else
  echo "📁 PostgreSQL is not selected or POSTGRES_HOST is not set; skipping database readiness wait."
fi

# Run migrations
echo "🔄 Running database migrations..."
python manage.py migrate --noinput

# Collect static files (if needed)
echo "📦 Collecting static files..."
python manage.py collectstatic --noinput

# Create superuser if it doesn't exist (optional, for development)
if [ "$DEBUG" = "True" ]; then
  python manage.py shell << END
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin')
    print("✅ Superuser 'admin' created (use in development only!)")
else:
    print("✅ Superuser already exists")
END
fi

echo "🚀 Starting PyAuthService..."

# Execute the main command
exec "$@"
