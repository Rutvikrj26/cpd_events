variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

variable "app_name" {
  description = "Application name"
  type        = string
  default     = "cpd-events"
}

# Database variables
variable "db_tier" {
  description = "Cloud SQL instance tier"
  type        = string
  default     = "db-f1-micro"
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "cpd_events"
}

variable "db_user" {
  description = "Database user"
  type        = string
  default     = "cpd_user"
}

variable "db_disk_size" {
  description = "Database disk size in GB"
  type        = number
  default     = 10
}

variable "db_high_availability" {
  description = "Enable high availability for database"
  type        = bool
  default     = false
}

variable "db_max_connections" {
  description = "Maximum database connections"
  type        = string
  default     = "100"
}

# Networking variables
variable "vpc_cidr" {
  description = "VPC CIDR range"
  type        = string
  default     = "10.0.0.0/24"
}

variable "vpc_connector_cidr" {
  description = "VPC connector CIDR range"
  type        = string
  default     = "10.8.0.0/28"
}

# Cloud Run variables
variable "backend_image" {
  description = "Backend Docker image"
  type        = string
  default     = "gcr.io/PROJECT_ID/cpd-backend:latest"
}

variable "cloud_run_cpu" {
  description = "Cloud Run CPU allocation"
  type        = string
  default     = "1"
}

variable "cloud_run_memory" {
  description = "Cloud Run memory allocation"
  type        = string
  default     = "1024Mi"
}

variable "cloud_run_concurrency" {
  description = "Cloud Run container concurrency"
  type        = number
  default     = 80
}

variable "cloud_run_timeout" {
  description = "Cloud Run request timeout in seconds"
  type        = number
  default     = 300
}

variable "min_instances" {
  description = "Minimum number of Cloud Run instances"
  type        = number
  default     = 0
}

variable "max_instances" {
  description = "Maximum number of Cloud Run instances"
  type        = number
  default     = 10
}

# Cloud Tasks variables
variable "task_queue_max_concurrent" {
  description = "Maximum concurrent task dispatches"
  type        = number
  default     = 100
}

variable "task_queue_max_rate" {
  description = "Maximum task dispatch rate per second"
  type        = number
  default     = 10
}

# Cloud Tasks behavior
variable "cloud_tasks_sync" {
  description = "Run Cloud Tasks synchronously (true for dev)"
  type        = bool
  default     = false
}

# Storage variables
variable "cors_origins" {
  description = "CORS allowed origins for storage buckets"
  type        = list(string)
  default     = ["*"]
}

# =============================================================================
# Application URLs
# =============================================================================

variable "site_url" {
  description = "Backend API URL (leave empty to use Cloud Run URL)"
  type        = string
  default     = ""
}

variable "frontend_url" {
  description = "Frontend application URL"
  type        = string
  default     = "https://app.accredit.store"
}

# =============================================================================
# Email Configuration
# =============================================================================

variable "default_from_email" {
  description = "Default sender email address"
  type        = string
  default     = "info@accredit.store"
}

variable "admin_email" {
  description = "Admin email for notifications"
  type        = string
  default     = "admin@accredit.store"
}

variable "smtp_server" {
  description = "SMTP relay host"
  type        = string
  default     = "smtp-relay.brevo.com"
}

variable "smtp_port" {
  description = "SMTP relay port"
  type        = number
  default     = 587
}

variable "server_email" {
  description = "Server email for error notifications"
  type        = string
  default     = "server@accredit.store"
}

variable "smtp_domain" {
  description = "SMTP provider sending domain"
  type        = string
  default     = ""
}

# =============================================================================
# Billing configuration (optional overrides)
# =============================================================================

variable "platform_fee_percent" {
  description = "Platform fee percentage for paid registrations"
  type        = number
  default     = 2.0
}

variable "ticketing_service_fee_percent_cad" {
  description = "Service fee percentage for CAD ticketing"
  type        = number
  default     = 3.5
}

variable "ticketing_service_fee_fixed_cad" {
  description = "Service fee fixed amount (CAD) per ticket"
  type        = number
  default     = 1.29
}

variable "ticketing_processing_fee_percent_cad" {
  description = "Processing fee percentage for CAD ticketing (applies to total order)"
  type        = number
  default     = 2.9
}

variable "ticketing_processing_fee_fixed_cad" {
  description = "Processing fee fixed amount (CAD) per order"
  type        = number
  default     = 0.0
}

variable "ticketing_service_fee_percent_usd" {
  description = "Service fee percentage for USD ticketing"
  type        = number
  default     = 3.7
}

variable "ticketing_service_fee_fixed_usd" {
  description = "Service fee fixed amount (USD) per ticket"
  type        = number
  default     = 1.79
}

variable "ticketing_processing_fee_percent_usd" {
  description = "Processing fee percentage for USD ticketing (applies to total order)"
  type        = number
  default     = 2.9
}

variable "ticketing_processing_fee_fixed_usd" {
  description = "Processing fee fixed amount (USD) per order"
  type        = number
  default     = 0.0
}

variable "billing_default_plan" {
  description = "Default subscription plan for new organizers"
  type        = string
  default     = "attendee"
}

# =============================================================================
# Frontend build-time variables (used by CLI deploy)
# =============================================================================

variable "frontend_google_maps_api_key" {
  description = "Google Maps API key for frontend build"
  type        = string
  default     = ""
}

variable "frontend_stripe_publishable_key" {
  description = "Stripe publishable key for frontend build"
  type        = string
  default     = ""
}

# Note: Frontend deployment is managed by CLI (accredit cloud frontend deploy)
# Frontend variables have been removed - use Firebase Hosting or GCS via CLI

# =============================================================================
# Domains
# =============================================================================

variable "domain_name" {
  description = "Apex domain (e.g. accredit.store). Used to build api/livekit subdomains."
  type        = string
  default     = "accredit.store"
}

variable "api_url" {
  description = "Public API URL (e.g. https://api.accredit.store). Used to wire the LiveKit webhook target. Leave as-is until the api subdomain is mapped to Cloud Run; then update."
  type        = string
  default     = "https://api.accredit.store"
}

variable "livekit_subdomain" {
  description = "Subdomain for the LiveKit signaling endpoint (joined with domain_name)"
  type        = string
  default     = "livekit"
}

# =============================================================================
# Recordings
# =============================================================================

variable "recordings_retention_days" {
  description = "Days to retain recording MP4s before lifecycle deletion"
  type        = number
  default     = 365
}

# =============================================================================
# Memorystore (Redis) — LiveKit psrpc bus
# =============================================================================

variable "redis_tier" {
  description = "Memorystore tier. BASIC is single-node (fine for psrpc). STANDARD_HA adds failover."
  type        = string
  default     = "BASIC"
}

variable "redis_memory_size_gb" {
  description = "Memorystore Redis memory size in GB"
  type        = number
  default     = 1
}

# =============================================================================
# LiveKit Server (GCE VM)
# =============================================================================

variable "livekit_zone" {
  description = "GCE zone for the LiveKit VM (must be in var.region)"
  type        = string
  default     = "us-central1-a"
}

variable "livekit_machine_type" {
  description = "GCE machine type for LiveKit. e2-standard-2 is the floor; bump to e2-standard-4+ for 50+ concurrent participants."
  type        = string
  default     = "e2-standard-2"
}

variable "livekit_disk_size" {
  description = "LiveKit VM boot disk size in GB"
  type        = number
  default     = 30
}

variable "livekit_image" {
  description = "GCE boot image for the LiveKit VM"
  type        = string
  default     = "debian-cloud/debian-12"
}

# =============================================================================
# LiveKit Egress (Cloud Run worker pool)
# =============================================================================

variable "egress_image" {
  description = "Container image for livekit-egress"
  type        = string
  default     = "livekit/egress:latest"
}

variable "egress_instance_count" {
  description = "Number of egress worker instances. Each instance handles ~1 active recording. Worker pools are manual-scale only."
  type        = number
  default     = 1
}

variable "egress_cpu" {
  description = "CPU for each egress instance. Headless Chromium needs ≥2 vCPU for smooth compositing."
  type        = string
  default     = "2"
}

variable "egress_memory" {
  description = "Memory for each egress instance. 4Gi minimum for Chromium."
  type        = string
  default     = "4Gi"
}
