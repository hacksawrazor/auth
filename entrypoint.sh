#!/bin/bash
# Docker entrypoint script for PyAuthService
# Handles migrations and container startup

set -e

echo "🐳 PyAuthService - Starting..."

# Run migrations
echo "🔄 Running database migrations..."
python manage.py migrate --noinput

# Collect static files (if needed)
echo "📦 Collecting static files..."
python manage.py collectstatic --noinput

# Create superuser only once (always runs if first time, marker persists)
# Uses /app/db/.admin_created so it survives container restarts via existing DB volume
if [ ! -f /app/db/.admin_created ]; then
  python manage.py shell << 'END'
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin')
    print("✅ Superuser 'admin' created")
    with open('/app/db/.admin_created', 'w') as f:
        f.write('1')
else:
    print("ℹ️ Superuser 'admin' already exists")
END
  echo "✅ Superuser creation process complete"
else
  echo "✅ Superuser 'admin' already exists (marker file: /app/db/.admin_created)"
fi

echo "🚀 Starting PyAuthService..."

# Execute the main command
exec "$@"