#!/bin/bash
set -e

echo "Starting Entrypoint Script..."

# Collect static files (again at runtime to ensure everything is there, though usually build-time is enough)
echo "Collecting static files..."
python src/manage.py collectstatic --noinput --settings=config.settings.production

# Make migrations (if any missed)
echo "Checking for model changes (makemigrations)..."
python src/manage.py makemigrations --noinput --settings=config.settings.production

# Apply database migrations
echo "Applying database migrations..."
python src/manage.py migrate --noinput --settings=config.settings.production

# Start Gunicorn
echo "Starting Gunicorn with ${WEB_CONCURRENCY:-1} worker(s)..."
exec gunicorn --chdir src --bind 0.0.0.0:${PORT:-8080} --workers ${WEB_CONCURRENCY:-1} --timeout 120 --access-logfile - --error-logfile - config.wsgi:application
