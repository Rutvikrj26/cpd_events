# Docker Setup for CPD Events Platform

This document explains how to run the CPD Events backend using Docker.

**📁 Location**: All Docker Compose files are now in the `cli/` directory for centralized deployment management.

## Prerequisites

- Docker Desktop installed (Mac/Windows) or Docker Engine (Linux)
- Docker Compose v2.0 or higher
- Make (optional, for convenience commands)

## Quick Start - Development

### 1. Navigate to the CLI directory

```bash
cd cli
```

### 2. Build and start all services

```bash
docker-compose up --build
```

This will start:
- PostgreSQL database on port 5432
- GCP Cloud Tasks Emulator on port 8123
- GCP Cloud Storage Emulator on port 4443
- Django backend on port 8000

### 2. Access the application

- API: http://localhost:8000
- Admin panel: http://localhost:8000/admin
- API documentation: http://localhost:8000/api/docs/

### 3. Initialize GCS emulator bucket

```bash
docker-compose exec backend python scripts/init_gcs_emulator.py
```

### 4. Run migrations

```bash
docker-compose exec backend python src/manage.py migrate
```

### 5. Create a superuser

```bash
docker-compose exec backend python src/manage.py createsuperuser
```

### 6. Stop services

```bash
docker-compose down
```

To stop and remove all data:
```bash
docker-compose down -v
```

## Development Workflow

### Attach to running container for debugging

```bash
docker-compose exec backend bash
```

### View logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
```

### Run Django management commands

```bash
# Make migrations
docker-compose exec backend python src/manage.py makemigrations

# Run migrations
docker-compose exec backend python src/manage.py migrate

# Create superuser
docker-compose exec backend python src/manage.py createsuperuser

# Collect static files
docker-compose exec backend python src/manage.py collectstatic --noinput

# Run shell
docker-compose exec backend python src/manage.py shell
```

### Run tests

```bash
docker-compose exec backend pytest
```

### Install new dependencies

After updating `pyproject.toml`:

```bash
docker-compose build backend
docker-compose up -d backend
```

## Production Deployment

### 1. Create a production environment file

Copy and configure your production environment variables:

```bash
cp backend/.env.example .env.production
```

Edit `.env.production` with your production values.

### 2. Build production image

```bash
docker-compose -f docker-compose.prod.yml build
```

### 3. Start production services

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### 4. Run migrations

```bash
docker-compose -f docker-compose.prod.yml exec backend python src/manage.py migrate
```

### 5. Collect static files

```bash
docker-compose -f docker-compose.prod.yml exec backend python src/manage.py collectstatic --noinput
```

## Local Development Services

### GCP Emulators

The development setup includes local emulators for GCP services:

#### Cloud Tasks Emulator
- **Image**: `ghcr.io/aertje/cloud-tasks-emulator`
- **Port**: 8123
- **Purpose**: Emulates GCP Cloud Tasks for async job processing
- **Usage**: Tasks are queued and executed asynchronously just like in production

#### Cloud Storage Emulator (fake-gcs-server)
- **Image**: `fsouza/fake-gcs-server`
- **Port**: 4443
- **Purpose**: Emulates Google Cloud Storage for file uploads
- **Bucket**: `cpd-events-local`
- **Usage**: Certificate PDFs, media files are stored in the emulator

**Note**: You must run `python scripts/init_gcs_emulator.py` after starting containers to create the bucket.

### Environment Variables for Emulators

The following environment variables are automatically set in development:

```bash
CLOUD_TASKS_EMULATOR_HOST=cloud-tasks-emulator:8123
GCS_EMULATOR_HOST=http://gcs-emulator:4443
GCS_BUCKET_NAME=cpd-events-local
```

## Docker Architecture

### Multi-Stage Build

The Dockerfile uses multi-stage builds for optimization:

1. **base**: Python 3.13 with system dependencies
2. **dependencies**: Installs Python packages
3. **development**: Development image with all dev dependencies
4. **production**: Optimized production image with gunicorn

### Build Targets

#### Development
```bash
docker build --target development -t cpd-backend:dev ./backend
```

#### Production
```bash
docker build --target production -t cpd-backend:prod ./backend
```

## Environment Variables

### Required for Production

```bash
# Django
DJANGO_SECRET_KEY=your-secret-key
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database
DB_NAME=cpd_events
DB_USER=cpd_user
DB_PASSWORD=your-secure-password
DB_HOST=db
DB_PORT=5432

# Email (Mailgun)
MAILGUN_SMTP_LOGIN=postmaster@your-domain.mailgun.org
MAILGUN_SMTP_PASSWORD=your-mailgun-password
MAILGUN_API_KEY=your-api-key
MAILGUN_DOMAIN=your-domain.mailgun.org
DEFAULT_FROM_EMAIL=info@accredit.store

# Stripe
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_PUBLISHABLE_KEY=pk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
STRIPE_PRICE_ORGANIZER=price_xxx
STRIPE_PRICE_ORGANIZATION=price_xxx

# Zoom
ZOOM_CLIENT_ID=your-zoom-client-id
ZOOM_CLIENT_SECRET=your-zoom-client-secret
ZOOM_WEBHOOK_SECRET=your-webhook-secret

# GCP
GCP_PROJECT_ID=your-project
GCP_LOCATION=us-central1
GCS_BUCKET_NAME=your-bucket
```

## Troubleshooting

### Container won't start

Check logs:
```bash
docker-compose logs backend
```

### Database connection errors

Ensure database is healthy:
```bash
docker-compose ps
```

Restart database:
```bash
docker-compose restart db
```

### Permission errors with volumes

On Linux, you may need to fix permissions:
```bash
sudo chown -R $USER:$USER ./backend/staticfiles ./backend/mediafiles
```

### Reset everything

```bash
docker-compose down -v
docker-compose up --build
docker-compose exec backend python scripts/init_gcs_emulator.py
docker-compose exec backend python src/manage.py migrate
```

### Access GCP emulator UIs

```bash
# Cloud Tasks emulator (basic HTTP API)
curl http://localhost:8123/health

# GCS emulator (list buckets)
curl http://localhost:4443/storage/v1/b
```

## Performance Tips

### Use BuildKit for faster builds

```bash
export DOCKER_BUILDKIT=1
docker-compose build
```

### Prune unused images

```bash
docker system prune -a
```

### Monitor resource usage

```bash
docker stats
```

## Security Best Practices

1. **Never commit `.env` files** - Use `.env.example` as template
2. **Use secrets management** in production (AWS Secrets Manager, GCP Secret Manager)
3. **Run as non-root user** (already configured in production Dockerfile)
4. **Keep images updated** - Regularly rebuild with latest base images
5. **Scan for vulnerabilities**:
   ```bash
   docker scan cpd-backend:prod
   ```

## CI/CD Integration

### GitHub Actions Example

```yaml
- name: Build Docker image
  run: docker build -t cpd-backend:${{ github.sha }} ./backend

- name: Push to registry
  run: |
    echo ${{ secrets.DOCKER_PASSWORD }} | docker login -u ${{ secrets.DOCKER_USERNAME }} --password-stdin
    docker push cpd-backend:${{ github.sha }}
```

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Django Deployment Checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)
