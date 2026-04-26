# =============================================================================
# LiveKit Egress — Cloud Run v2 Worker Pool (google-beta provider).
#
# Worker pools are continuous-background-work units with no inbound URL,
# manually-scaled, designed for daemons that pull from queues. That maps
# exactly onto livekit-egress: it pulls jobs from LiveKit via redis psrpc,
# joins rooms as a participant, composites with headless Chromium, and
# writes MP4s to a filesystem path.
#
# Why a worker pool instead of a service:
#   - No HTTP ingress needed
#   - Long-running process (not request-response)
#   - GCS volume mount is supported, so we share /recordings with backend
#
# Network model:
#   - Direct VPC, egress = PRIVATE_RANGES_ONLY:
#       * Memorystore traffic (private IP)         → through VPC
#       * LiveKit signaling on livekit.<domain>    → public path (default)
#       * GCS API (fuse mount)                     → public Google network
#   - Outbound UDP for WebRTC media is via Cloud Run's default egress, not
#     through Direct VPC. This sidesteps any VPC UDP restrictions.
#
# IMPORTANT — verify before relying on this in prod:
#   1. Outbound UDP from Cloud Run to LiveKit's external IP works
#      (egress joins rooms as a WebRTC participant).
#   2. GCS-fuse write throughput keeps up with active recording bitrates.
#   If either fails, fall back to running egress on the LiveKit VM
#   (docker compose adding the egress + a local redis container) and
#   delete this resource.
# =============================================================================

# egress.yaml is sensitive (api_key + api_secret) and content-shaped, so it
# lives in Secret Manager and is mounted as a file. Upload via:
#   accredit cloud secrets upload --backend --env prod   (writes EGRESS_CONFIG_YAML)
#
# The body should look approximately like:
#   api_key: <livekit api key>
#   api_secret: <livekit api secret>
#   ws_url: wss://livekit.<your-domain>
#   redis:
#     address: <memorystore host>:<port>
#   file_output:
#     local: true
#     output_directory: /recordings
resource "google_cloud_run_v2_worker_pool" "livekit_egress" {
  provider = google-beta

  name     = "${local.app_name}-egress"
  location = var.region

  launch_stage = "BETA"

  scaling {
    scaling_mode          = "MANUAL"
    manual_instance_count = var.egress_instance_count
  }

  template {
    service_account = google_service_account.cloud_run.email

    vpc_access {
      egress = "PRIVATE_RANGES_ONLY"
      network_interfaces {
        network    = google_compute_network.vpc.id
        subnetwork = google_compute_subnetwork.subnet.id
      }
    }

    # Recordings — fuse-mounted writable. Backend mounts the same bucket
    # read-only at the same path.
    volumes {
      name = "recordings"
      gcs {
        bucket    = google_storage_bucket.recordings.name
        read_only = false
      }
    }

    # Egress config — full YAML body stored in Secret Manager, mounted as
    # a file at /etc/egress/egress.yaml. The container's CMD points at it.
    volumes {
      name = "egress-config"
      secret {
        secret = "${local.secret_prefix}_EGRESS_CONFIG_YAML"
        items {
          version = "latest"
          path    = "egress.yaml"
          mode    = "0444"
        }
      }
    }

    containers {
      # NOTE: var.egress_image defaults to livekit/egress:latest from Docker
      # Hub, which rate-limits unauthenticated pulls (100/6h per IP). Before
      # production load, mirror once to Artifact Registry and pin a version:
      #   gcloud artifacts docker tags add \
      #     livekit/egress:v1.x.y \
      #     <region>-docker.pkg.dev/<proj>/backend/egress:v1.x.y
      # then set var.egress_image to the AR path.
      image = var.egress_image

      # Egress reads its config from this env var pointing at the file.
      env {
        name  = "EGRESS_CONFIG_FILE"
        value = "/etc/egress/egress.yaml"
      }

      resources {
        limits = {
          cpu    = var.egress_cpu
          memory = var.egress_memory
        }
      }

      volume_mounts {
        name       = "recordings"
        mount_path = "/recordings"
      }

      volume_mounts {
        name       = "egress-config"
        mount_path = "/etc/egress"
      }
    }
  }

  depends_on = [
    google_project_service.required_apis,
    google_redis_instance.livekit_bus,
    google_storage_bucket.recordings,
  ]
}

output "egress_worker_pool_name" {
  description = "LiveKit egress Cloud Run worker pool name"
  value       = google_cloud_run_v2_worker_pool.livekit_egress.name
}
