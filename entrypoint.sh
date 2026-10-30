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
