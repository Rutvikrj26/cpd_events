# =============================================================================
# Memorystore (Redis) — LiveKit psrpc message bus.
#
# Sole purpose: shuttle psrpc messages between livekit-server (on the GCE VM)
# and livekit-egress (Cloud Run worker pool). Not used by the Django app.
#
# BASIC tier (single-node, no failover) is fine — losing the redis briefly
# means in-flight egress jobs fail and clients retry. We're not storing
# durable state in here. Bump to STANDARD_HA only if recording reliability
# becomes a hard requirement.
# =============================================================================

resource "google_redis_instance" "livekit_bus" {
  name           = "${local.app_name}-livekit-bus"
  region         = var.region
  tier           = var.redis_tier
  memory_size_gb = var.redis_memory_size_gb
  redis_version  = "REDIS_7_2"

  # Same VPC as the LiveKit VM and the egress worker pool. Reuses the
  # private-services peering created for Cloud SQL.
  authorized_network      = google_compute_network.vpc.id
  connect_mode            = "PRIVATE_SERVICE_ACCESS"
  reserved_ip_range       = google_compute_global_address.private_ip_address.name
  transit_encryption_mode = "DISABLED"

  redis_configs = {
    # LiveKit egress + signaling are pubsub heavy. Allow keys to evict under
    # memory pressure rather than rejecting writes.
    maxmemory-policy = "allkeys-lru"
  }

  depends_on = [
    google_service_networking_connection.private_vpc_connection,
    google_project_service.required_apis,
  ]
}

output "redis_host" {
  description = "Memorystore Redis private IP (used by LiveKit + egress)"
  value       = google_redis_instance.livekit_bus.host
}

output "redis_port" {
  description = "Memorystore Redis port"
  value       = google_redis_instance.livekit_bus.port
}
