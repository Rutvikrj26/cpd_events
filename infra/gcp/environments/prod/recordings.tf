# =============================================================================
# Recordings bucket
#
# Egress (Cloud Run worker pool) writes MP4 recordings here. Backend Cloud Run
# service mounts the same bucket read-only at /recordings to stream them back
# to authorized users. Both sides go through GCS-fuse so the in-container
# filesystem path matches what the existing code already expects in dev.
#
# Object lifecycle is tighter here than the media bucket since recordings can
# get large. Tune `recordings_retention_days` to match retention policy.
# =============================================================================

resource "google_storage_bucket" "recordings" {
  name          = "${var.project_id}-${local.app_name}-recordings"
  location      = var.region
  force_destroy = var.environment != "prod"

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = var.recordings_retention_days
    }
    action {
      type = "Delete"
    }
  }

  # Keep older versions briefly so an accidental overwrite is recoverable.
  lifecycle_rule {
    condition {
      num_newer_versions = 2
    }
    action {
      type = "Delete"
    }
  }
}

# The Cloud Run service account is shared by backend + egress worker pool;
# storage.objectAdmin (granted in main.tf) already covers read+write access
# to all project buckets. No bucket-level IAM needed unless we ever split
# the SAs.

output "recordings_bucket_name" {
  description = "Recordings storage bucket name"
  value       = google_storage_bucket.recordings.name
}
