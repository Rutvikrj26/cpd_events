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
  default     = "dev"
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

# Storage variables
variable "cors_origins" {
  description = "CORS allowed origins for storage buckets"
  type        = list(string)
  default     = ["*"]
}

# Note: Frontend deployment is managed by CLI (accredit cloud frontend deploy)
# Frontend variables have been removed - use Firebase Hosting or GCS via CLI
