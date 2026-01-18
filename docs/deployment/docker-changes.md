# Docker Configuration Changes Summary

## Changes Made

### ✅ Removed Redis
- **Reason**: Redis was configured but never used in Django settings
- **Impact**: No caching or session storage configured - safe to remove
- Removed from both `docker-compose.yml` and `docker-compose.prod.yml`
- Cleaned up Redis volume definitions

### ✅ Added GCP Cloud Tasks Emulator
- **Image**: `ghcr.io/aertje/cloud-tasks-emulator:latest`
- **Port**: 8123
- **Purpose**: Local emulator for async job processing
- **Features**:
  - Emulates GCP Cloud Tasks API
  - Allows testing task queuing locally
  - No need for actual GCP credentials in development

### ✅ Added GCP Cloud Storage Emulator
- **Image**: `fsouza/fake-gcs-server:latest`
- **Port**: 4443
- **Purpose**: Local emulator for file storage (certificates, media)
- **Features**:
  - Emulates Google Cloud Storage API
  - Stores files in Docker volume
  - Compatible with google-cloud-storage Python client

### ✅ Removed/Commented Out Nginx
- **Reason**: Typically handled by cloud load balancers in production
- **Status**: Commented out in production docker-compose
- **Note**: Can be re-enabled if needed for self-hosted deployments

### ✅ Updated Django Settings
- Added `CLOUD_TASKS_EMULATOR_HOST` environment variable
- Added `GCS_EMULATOR_HOST` environment variable
- Modified `common/cloud_tasks.py` to detect and use emulator
- Modified `common/storage.py` to detect and use emulator

### ✅ Created Helper Script
- **File**: `backend/scripts/init_gcs_emulator.py`
- **Purpose**: Initialize the GCS bucket in the emulator
- **Usage**: Run after `docker-compose up` to create required bucket

---

## New Container Architecture

### Development (3 containers)
```
┌─────────────────────┐
│   PostgreSQL        │  Port 5432
│   (postgres:16)     │
└─────────────────────┘

┌─────────────────────┐
│  Cloud Tasks        │  Port 8123
│   Emulator          │
└─────────────────────┘

┌─────────────────────┐
│  Cloud Storage      │  Port 4443
│   Emulator          │
└─────────────────────┘

┌─────────────────────┐
│  Django Backend     │  Port 8000
│   (Development)     │
└─────────────────────┘
```

### Production (2 containers)
```
┌─────────────────────┐
│   PostgreSQL        │  Internal
│   (postgres:16)     │
└─────────────────────┘

┌─────────────────────┐
│  Django Backend     │  Exposed via
│   (Gunicorn)        │  Cloud Run/LB
└─────────────────────┘

External Services:
- GCP Cloud Tasks (managed)
- GCP Cloud Storage (managed)
- Stripe API
- Zoom API
```

---

## Quick Start Guide

### 1. Start Services
```bash
docker-compose up --build
```

### 2. Initialize GCS Emulator
```bash
docker-compose exec backend python scripts/init_gcs_emulator.py
```

### 3. Run Migrations
```bash
docker-compose exec backend python src/manage.py migrate
```

### 4. Create Superuser
```bash
docker-compose exec backend python src/manage.py createsuperuser
```

### 5. Access Application
- API: http://localhost:8000
- Admin: http://localhost:8000/admin
- Docs: http://localhost:8000/api/docs/

---

## Environment Variables

### Development (Automatic)
```bash
# Database
DB_HOST=db
DB_PORT=5432

# GCP Emulators
CLOUD_TASKS_EMULATOR_HOST=cloud-tasks-emulator:8123
GCS_EMULATOR_HOST=http://gcs-emulator:4443
GCS_BUCKET_NAME=cpd-events-local
```

### Production (Required)
```bash
# Use real GCP services
GCP_PROJECT_ID=your-project
GCP_LOCATION=us-central1
GCP_QUEUE_NAME=default
GCS_BUCKET_NAME=your-bucket-name
GCP_SA_EMAIL=service-account@project.iam.gserviceaccount.com
```

---

## Testing the Emulators

### Test Cloud Tasks Emulator
```bash
# Check health
curl http://localhost:8123/health

# In Django, tasks will queue to the emulator
# Example: send_certificate_email.delay(cert_id)
```

### Test Cloud Storage Emulator
```bash
# List buckets
curl http://localhost:4443/storage/v1/b

# Upload test file
curl -X POST http://localhost:4443/upload/storage/v1/b/cpd-events-local/o \
  -H "Content-Type: application/octet-stream" \
  --data-binary "@test.pdf"
```

---

## Benefits

✅ **No Redis overhead** - Removed unused service
✅ **Full local testing** - GCP services work offline
✅ **Cost savings** - No GCP API calls in development
✅ **Faster development** - No network latency to real GCP
✅ **Simplified setup** - One `docker-compose up` command
✅ **Parity with production** - Same APIs, same behavior

---

## Migration Notes

### Before
- Redis container (unused)
- Tasks ran synchronously in DEBUG mode
- Files saved to local MEDIA_ROOT

### After
- Cloud Tasks emulator (tasks queue properly)
- Cloud Storage emulator (files in emulated GCS)
- Production-like behavior in development

---

## Troubleshooting

### GCS bucket not found
```bash
# Re-run initialization
docker-compose exec backend python scripts/init_gcs_emulator.py
```

### Tasks not executing
```bash
# Check emulator logs
docker-compose logs cloud-tasks-emulator

# Verify environment variable
docker-compose exec backend env | grep CLOUD_TASKS
```

### Emulator connection refused
```bash
# Restart containers
docker-compose restart cloud-tasks-emulator gcs-emulator
```

---

## References

- [Cloud Tasks Emulator](https://github.com/aertje/cloud-tasks-emulator)
- [fake-gcs-server](https://github.com/fsouza/fake-gcs-server)
- [GCP Storage Emulator Docs](https://github.com/fsouza/fake-gcs-server#usage)
