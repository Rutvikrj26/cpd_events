terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 7.0"
    }
  }

  # GCS backend temporarily disabled due to VPC Service Controls
  # Uncomment when org policies allow, or migrate state later
  # backend "gcs" {
  #   bucket = "cpd-events-481919-terraform-state"
  #   prefix = "prod/state"
  # }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# google-beta is only used for resources not yet GA in the stable provider —
# notably google_cloud_run_v2_worker_pool (used for livekit-egress).
provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# Local variables
locals {
  app_name = "${var.app_name}-${var.environment}"
  labels = {
    environment = var.environment
    app         = var.app_name
    managed_by  = "terraform"
  }
}

# Enable required APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "run.googleapis.com",
    "sql-component.googleapis.com",
    "sqladmin.googleapis.com",
    "cloudtasks.googleapis.com",
    "cloudscheduler.googleapis.com",
    "artifactregistry.googleapis.com",
    "storage-api.googleapis.com",
    "secretmanager.googleapis.com",
    "compute.googleapis.com",
    "vpcaccess.googleapis.com",
    "servicenetworking.googleapis.com",
    "redis.googleapis.com",
    "identitytoolkit.googleapis.com",
    "firebase.googleapis.com",
    "iamcredentials.googleapis.com",
  ])

  service            = each.value
  disable_on_destroy = false
}

# Service Account for Cloud Run
resource "google_service_account" "cloud_run" {
  account_id   = "${local.app_name}-run"
  display_name = "Cloud Run Service Account for ${local.app_name}"
  description  = "Service account for Cloud Run to access GCP resources"
}

# IAM roles for Cloud Run service account.
# This SA is shared by the backend Cloud Run service AND the livekit-egress
# Cloud Run worker pool — they need the same access (GCS, Secret Manager).
# Diverge into separate SAs only if scope separation becomes a requirement.
resource "google_project_iam_member" "cloud_run_roles" {
  for_each = toset([
    "roles/cloudsql.client",
    "roles/cloudtasks.enqueuer",
    "roles/storage.objectAdmin",
    "roles/secretmanager.secretAccessor",
    # Sign GCS URLs and mint Firebase custom tokens without a key file.
    "roles/iam.serviceAccountTokenCreator",
    # Verify Firebase Auth ID tokens.
    "roles/firebase.viewer",
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.cloud_run.email}"
}

# Cloud SQL Instance
resource "google_sql_database_instance" "main" {
  name             = "${local.app_name}-db"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier              = var.db_tier
    availability_type = var.db_high_availability ? "REGIONAL" : "ZONAL"
    disk_size         = var.db_disk_size
    disk_type         = "PD_SSD"

    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      point_in_time_recovery_enabled = var.environment == "prod"
    }

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.vpc.id
      ssl_mode        = "ENCRYPTED_ONLY"
    }

    database_flags {
      name  = "max_connections"
      value = var.db_max_connections
    }
  }

  deletion_protection = var.environment == "prod"

  depends_on = [
    google_service_networking_connection.private_vpc_connection,
    google_project_service.required_apis,
  ]
}

# Database
resource "google_sql_database" "database" {
  name     = var.db_name
  instance = google_sql_database_instance.main.name
}

# Database user
resource "google_sql_user" "users" {
  name     = var.db_user
  instance = google_sql_database_instance.main.name
  password = random_password.db_password.result
}

# Random password for database
resource "random_password" "db_password" {
  length  = 32
  special = true
}

# Store DB password in Secret Manager
resource "google_secret_manager_secret" "db_password" {
  secret_id = "${local.app_name}-db-password"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "db_password" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = random_password.db_password.result
}

# =============================================================================
# Application Secrets (uploaded via CLI: accredit cloud secrets upload)
# These secrets are created by the CLI and referenced here by Cloud Run
# =============================================================================

locals {
  # Secret names follow the pattern: {ENV}_{KEY}
  # These must be uploaded before terraform apply using:
  #   accredit cloud secrets upload --backend --env <env>
  secret_prefix = upper(var.environment)

  # List of required secrets that must exist in Secret Manager
  required_secrets = [
    "DJANGO_SECRET_KEY",
    "ENCRYPTION_KEY",
    "STRIPE_SECRET_KEY",
    "STRIPE_PUBLISHABLE_KEY",
    "STRIPE_WEBHOOK_SECRET",
    # Zoom secrets are legacy (the platform uses LiveKit). Kept here because
    # the CLI's `accredit cloud secrets upload` walks this list; remove only
    # in coordination with a CLI change.
    "ZOOM_CLIENT_ID",
    "ZOOM_CLIENT_SECRET",
    "ZOOM_WEBHOOK_SECRET",
    "SMTP_API_KEY",
    "SMTP_LOGIN",
    "SMTP_PASSWORD",
    # LiveKit — the API key/secret are issued by you and shared by backend,
    # the LiveKit server itself, and livekit-egress. The webhook key is what
    # LiveKit signs outbound webhooks with; backend verifies against it.
    "LIVEKIT_API_KEY",
    "LIVEKIT_API_SECRET",
    "LIVEKIT_WEBHOOK_API_KEY",
    # Firebase Admin SDK service-account JSON — backend uses this to verify
    # Firebase ID tokens. Generate in Firebase console → Project Settings →
    # Service Accounts, paste full JSON content as the secret value.
    "FIREBASE_CREDENTIALS_JSON",
    # Full egress.yaml content, mounted as a file by the egress worker pool.
    "EGRESS_CONFIG_YAML",
  ]

  # Optional secrets (won't fail if missing)
  optional_secrets = [
    "SMTP_DOMAIN",
    "ZOOM_REDIRECT_URI",
    "SITE_URL",
    "FRONTEND_URL",
    "DEFAULT_FROM_EMAIL",
    "ADMIN_EMAIL",
  ]
}

# VPC Network
resource "google_compute_network" "vpc" {
  name                    = "${local.app_name}-vpc"
  auto_create_subnetworks = false
}

# Subnet
resource "google_compute_subnetwork" "subnet" {
  name          = "${local.app_name}-subnet"
  ip_cidr_range = var.vpc_cidr
  region        = var.region
  network       = google_compute_network.vpc.id

  private_ip_google_access = true
}

# Private VPC connection for Cloud SQL
resource "google_compute_global_address" "private_ip_address" {
  name          = "${local.app_name}-private-ip"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc.id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address.name]
}

# Serverless VPC Connector
resource "google_vpc_access_connector" "connector" {
  name          = "${local.app_name}-connector"
  region        = var.region
  network       = google_compute_network.vpc.name
  ip_cidr_range = var.vpc_connector_cidr

  depends_on = [google_project_service.required_apis]
}

# Cloud Storage Buckets
resource "google_storage_bucket" "media" {
  name          = "${var.project_id}-${local.app_name}-media"
  location      = var.region
  force_destroy = var.environment != "prod"

  uniform_bucket_level_access = true

  cors {
    origin          = var.cors_origins
    method          = ["GET", "HEAD", "PUT", "POST", "DELETE"]
    response_header = ["*"]
    max_age_seconds = 3600
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }
}

resource "google_storage_bucket" "certificates" {
  name          = "${var.project_id}-${local.app_name}-certificates"
  location      = var.region
  force_destroy = var.environment != "prod"

  uniform_bucket_level_access = true
}

# Cloud Tasks Queue
resource "google_cloud_tasks_queue" "default" {
  name     = "${local.app_name}-tasks"
  location = var.region

  rate_limits {
    max_concurrent_dispatches = var.task_queue_max_concurrent
    max_dispatches_per_second = var.task_queue_max_rate
  }

  retry_config {
    max_attempts       = 5
    max_retry_duration = "600s"
    min_backoff        = "1s"
    max_backoff        = "10s"
    max_doublings      = 3
  }
}

# =============================================================================
# Cron tick — Cloud Scheduler hits the backend every minute to fan out to
# periodic Cloud Tasks (reminder dispatch, scheduled email dispatch, etc.).
# Authorization is via a shared secret stored in Secret Manager and injected
# into both the Cloud Run service and the Scheduler job's HTTP target.
# =============================================================================

resource "random_password" "cron_shared_secret" {
  length  = 48
  special = false
}

resource "google_secret_manager_secret" "cron_shared_secret" {
  secret_id = "${local.app_name}-cron-shared-secret"

  replication {
    auto {}
  }

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "cron_shared_secret" {
  secret      = google_secret_manager_secret.cron_shared_secret.id
  secret_data = random_password.cron_shared_secret.result
}

resource "google_cloud_scheduler_job" "cron_tick" {
  name        = "${local.app_name}-cron-tick"
  description = "Periodic fan-out to /api/common/cron/tick/"
  schedule    = "* * * * *"
  region      = var.region
  time_zone   = "UTC"

  retry_config {
    retry_count          = 1
    min_backoff_duration = "10s"
    max_backoff_duration = "60s"
  }

  http_target {
    http_method = "POST"
    uri         = "${try(google_cloud_run_v2_service.backend.uri, "")}/api/common/cron/tick/"

    headers = {
      "Content-Type"  = "application/json"
      "Authorization" = "Bearer ${random_password.cron_shared_secret.result}"
    }

    body = base64encode("{}")
  }

  depends_on = [
    google_project_service.required_apis,
    google_cloud_run_v2_service.backend,
  ]
}

# Cloud Run v2 Service — backend API.
#
# Migrated from google_cloud_run_service (v1) to google_cloud_run_v2_service
# in order to use first-class GCS volume mounts (the recordings bucket is
# fuse-mounted at /recordings so the streaming endpoint can read MP4s the
# egress worker pool wrote).
resource "google_cloud_run_v2_service" "backend" {
  name     = local.app_name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.cloud_run.email
    timeout         = "${var.cloud_run_timeout}s"

    max_instance_request_concurrency = var.cloud_run_concurrency

    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    vpc_access {
      connector = google_vpc_access_connector.connector.id
      egress    = "PRIVATE_RANGES_ONLY"
    }

    # Cloud SQL socket — exposed at /cloudsql/<connection_name> inside the
    # container without a volume mount, via the cloudsql_instances setting.
    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [google_sql_database_instance.main.connection_name]
      }
    }

    # Recordings bucket — fuse-mounted read-only. The egress worker pool
    # writes here; backend streams MP4s by reading from the same path.
    volumes {
      name = "recordings"
      gcs {
        bucket    = google_storage_bucket.recordings.name
        read_only = true
      }
    }

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/backend/cpd-backend:latest"

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = var.cloud_run_cpu
          memory = var.cloud_run_memory
        }
        cpu_idle          = true
        startup_cpu_boost = true
      }

      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }

      volume_mounts {
        name       = "recordings"
        mount_path = "/recordings"
      }

      env {
        name  = "DJANGO_SETTINGS_MODULE"
        value = "config.settings.production"
      }

      env {
        name  = "ALLOWED_HOSTS"
        value = "*"
      }

      env {
        name  = "DB_HOST"
        value = "/cloudsql/${google_sql_database_instance.main.connection_name}"
      }

      env {
        name  = "DB_NAME"
        value = google_sql_database.database.name
      }

      env {
        name  = "DB_USER"
        value = google_sql_user.users.name
      }

      env {
        name = "DB_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.db_password.secret_id
            version = "latest"
          }
        }
      }

      env {
        name  = "GCS_BUCKET_NAME"
        value = google_storage_bucket.media.name
      }

      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }

      env {
        name  = "GCP_LOCATION"
        value = var.region
      }

      env {
        name  = "GCP_QUEUE_NAME"
        value = google_cloud_tasks_queue.default.name
      }

      env {
        name  = "GCP_SA_EMAIL"
        value = google_service_account.cloud_run.email
      }

      env {
        name  = "CLOUD_TASKS_SYNC"
        value = tostring(var.cloud_tasks_sync)
      }

      env {
        name = "CRON_SHARED_SECRET"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.cron_shared_secret.secret_id
            version = "latest"
          }
        }
      }

      env {
        name  = "CORS_ALLOWED_ORIGINS"
        value = join(",", var.cors_origins)
      }

      env {
        name  = "WEB_CONCURRENCY"
        value = "1"
      }

      # ===============================================================
      # Recording storage — fuse mount path shared with egress.
      # ===============================================================
      env {
        name  = "RECORDING_STORAGE_DIR"
        value = "/recordings"
      }

      # ===============================================================
      # LiveKit — the backend mints participant tokens (uses key/secret),
      # browsers connect to LIVEKIT_WS_URL (public TLS), and the backend
      # talks server-side to LIVEKIT_HOST. LiveKit posts webhooks back
      # to /api/v1/webhooks/video/ signed with LIVEKIT_WEBHOOK_API_KEY.
      # ===============================================================
      env {
        name  = "LIVEKIT_HOST"
        value = "https://${var.livekit_subdomain}.${var.domain_name}"
      }

      env {
        name  = "LIVEKIT_WS_URL"
        value = "wss://${var.livekit_subdomain}.${var.domain_name}"
      }

      env {
        name = "LIVEKIT_API_KEY"
        value_source {
          secret_key_ref {
            secret  = "${local.secret_prefix}_LIVEKIT_API_KEY"
            version = "latest"
          }
        }
      }

      env {
        name = "LIVEKIT_API_SECRET"
        value_source {
          secret_key_ref {
            secret  = "${local.secret_prefix}_LIVEKIT_API_SECRET"
            version = "latest"
          }
        }
      }

      env {
        name = "LIVEKIT_WEBHOOK_API_KEY"
        value_source {
          secret_key_ref {
            secret  = "${local.secret_prefix}_LIVEKIT_WEBHOOK_API_KEY"
            version = "latest"
          }
        }
      }

      # ===============================================================
      # Firebase Auth — backend verifies ID tokens via Admin SDK.
      # FIREBASE_CREDENTIALS_JSON holds the service-account JSON content.
      # ===============================================================
      env {
        name  = "FIREBASE_PROJECT_ID"
        value = var.project_id
      }

      env {
        name = "FIREBASE_CREDENTIALS_JSON"
        value_source {
          secret_key_ref {
            secret  = "${local.secret_prefix}_FIREBASE_CREDENTIALS_JSON"
            version = "latest"
          }
        }
      }

      # ===============================================================
      # Application Secrets from Secret Manager
      # Upload with: accredit cloud secrets upload --backend --env prod
      # ===============================================================

      # Django Core
      env {
        name = "DJANGO_SECRET_KEY"
        value_source {
          secret_key_ref {
            secret  = "${local.secret_prefix}_DJANGO_SECRET_KEY"
            version = "latest"
          }
        }
      }

      env {
        name = "ENCRYPTION_KEY"
        value_source {
          secret_key_ref {
            secret  = "${local.secret_prefix}_ENCRYPTION_KEY"
            version = "latest"
          }
        }
      }

      # Stripe
      env {
        name = "STRIPE_SECRET_KEY"
        value_source {
          secret_key_ref {
            secret  = "${local.secret_prefix}_STRIPE_SECRET_KEY"
            version = "latest"
          }
        }
      }

      env {
        name = "STRIPE_PUBLISHABLE_KEY"
        value_source {
          secret_key_ref {
            secret  = "${local.secret_prefix}_STRIPE_PUBLISHABLE_KEY"
            version = "latest"
          }
        }
      }

      env {
        name = "STRIPE_WEBHOOK_SECRET"
        value_source {
          secret_key_ref {
            secret  = "${local.secret_prefix}_STRIPE_WEBHOOK_SECRET"
            version = "latest"
          }
        }
      }

      # Zoom (legacy — see comment on local.required_secrets)
      env {
        name = "ZOOM_CLIENT_ID"
        value_source {
          secret_key_ref {
            secret  = "${local.secret_prefix}_ZOOM_CLIENT_ID"
            version = "latest"
          }
        }
      }

      env {
        name = "ZOOM_CLIENT_SECRET"
        value_source {
          secret_key_ref {
            secret  = "${local.secret_prefix}_ZOOM_CLIENT_SECRET"
            version = "latest"
          }
        }
      }

      env {
        name = "ZOOM_WEBHOOK_SECRET"
        value_source {
          secret_key_ref {
            secret  = "${local.secret_prefix}_ZOOM_WEBHOOK_SECRET"
            version = "latest"
          }
        }
      }

      # SMTP provider
      env {
        name = "SMTP_API_KEY"
        value_source {
          secret_key_ref {
            secret  = "${local.secret_prefix}_SMTP_API_KEY"
            version = "latest"
          }
        }
      }

      env {
        name = "SMTP_LOGIN"
        value_source {
          secret_key_ref {
            secret  = "${local.secret_prefix}_SMTP_LOGIN"
            version = "latest"
          }
        }
      }

      env {
        name = "SMTP_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = "${local.secret_prefix}_SMTP_PASSWORD"
            version = "latest"
          }
        }
      }

      # Static config (not secrets, but needed)
      env {
        name  = "SMTP_SERVER"
        value = var.smtp_server
      }

      env {
        name  = "SMTP_PORT"
        value = tostring(var.smtp_port)
      }

      env {
        name  = "SMTP_DOMAIN"
        value = var.smtp_domain
      }

      env {
        name  = "DEFAULT_FROM_EMAIL"
        value = var.default_from_email
      }

      env {
        name  = "SERVER_EMAIL"
        value = var.server_email
      }

      env {
        name  = "ADMIN_EMAIL"
        value = var.admin_email
      }

      env {
        name  = "PLATFORM_FEE_PERCENT"
        value = tostring(var.platform_fee_percent)
      }

      env {
        name  = "TICKETING_SERVICE_FEE_PERCENT_CAD"
        value = tostring(var.ticketing_service_fee_percent_cad)
      }

      env {
        name  = "TICKETING_SERVICE_FEE_FIXED_CAD"
        value = tostring(var.ticketing_service_fee_fixed_cad)
      }

      env {
        name  = "TICKETING_PROCESSING_FEE_PERCENT_CAD"
        value = tostring(var.ticketing_processing_fee_percent_cad)
      }

      env {
        name  = "TICKETING_PROCESSING_FEE_FIXED_CAD"
        value = tostring(var.ticketing_processing_fee_fixed_cad)
      }

      env {
        name  = "TICKETING_SERVICE_FEE_PERCENT_USD"
        value = tostring(var.ticketing_service_fee_percent_usd)
      }

      env {
        name  = "TICKETING_SERVICE_FEE_FIXED_USD"
        value = tostring(var.ticketing_service_fee_fixed_usd)
      }

      env {
        name  = "TICKETING_PROCESSING_FEE_PERCENT_USD"
        value = tostring(var.ticketing_processing_fee_percent_usd)
      }

      env {
        name  = "TICKETING_PROCESSING_FEE_FIXED_USD"
        value = tostring(var.ticketing_processing_fee_fixed_usd)
      }

      env {
        name  = "BILLING_DEFAULT_PLAN"
        value = var.billing_default_plan
      }

      # URLs - using Cloud Run URL or custom domain
      env {
        name  = "SITE_URL"
        value = var.site_url != "" ? var.site_url : "https://${local.app_name}-${var.project_id}.${var.region}.run.app"
      }

      env {
        name  = "FRONTEND_URL"
        value = var.frontend_url
      }

      env {
        name  = "ZOOM_REDIRECT_URI"
        value = "${var.frontend_url}/integrations/zoom/callback"
      }
    }

    labels = local.labels
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [google_project_service.required_apis]
}

# Allow unauthenticated access (API is public)
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  name     = google_cloud_run_v2_service.backend.name
  location = google_cloud_run_v2_service.backend.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# =============================================================================
# State Storage Buckets
# =============================================================================

# Terraform State Storage Bucket (for remote state)
# Artifact Registry Repository
resource "google_artifact_registry_repository" "backend" {
  location      = var.region
  repository_id = "backend"
  description   = "Docker repository for Backend"
  format        = "DOCKER"
}

# Terraform State Bucket
resource "google_storage_bucket" "terraform_state" {
  name          = "${var.project_id}-terraform-state"
  location      = var.region
  force_destroy = false

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      num_newer_versions = 5
    }
    action {
      type = "Delete"
    }
  }

  uniform_bucket_level_access = true
}

# CLI Deployment State Bucket (for accredit sync)
resource "google_storage_bucket" "deployment_state" {
  name          = "${var.project_id}-deployment-state"
  location      = var.region
  force_destroy = var.environment != "prod"

  versioning {
    enabled = true
  }

  uniform_bucket_level_access = true
}

# =============================================================================
# Outputs
# =============================================================================

# Project & Region (required for CLI sync)
output "project_id" {
  description = "GCP Project ID"
  value       = var.project_id
}

output "region" {
  description = "GCP Region"
  value       = var.region
}

# Backend
output "backend_url" {
  value       = try(google_cloud_run_v2_service.backend.uri, "")
  description = "URL of the backend Cloud Run service"
}

output "cloud_run_url" {
  value       = try(google_cloud_run_v2_service.backend.uri, "")
  description = "URL of the Cloud Run service"
}

output "database_connection_name" {
  description = "Cloud SQL connection name"
  value       = google_sql_database_instance.main.connection_name
}

# Storage
output "media_bucket_name" {
  description = "Media storage bucket name"
  value       = google_storage_bucket.media.name
}

output "certificates_bucket_name" {
  description = "Certificates storage bucket name"
  value       = google_storage_bucket.certificates.name
}

output "terraform_state_bucket" {
  description = "Terraform state bucket name"
  value       = google_storage_bucket.terraform_state.name
}

output "deployment_state_bucket" {
  description = "CLI deployment state bucket name"
  value       = google_storage_bucket.deployment_state.name
}

output "frontend_env" {
  description = "Frontend build-time environment variables"
  value = {
    VITE_GOOGLE_MAPS_API_KEY    = var.frontend_google_maps_api_key
    VITE_STRIPE_PUBLISHABLE_KEY = var.frontend_stripe_publishable_key
  }
}
