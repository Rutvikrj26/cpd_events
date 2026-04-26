# =============================================================================
# LiveKit Server (GCE VM)
#
# WebRTC ingress requires a public IP and persistent UDP/TCP — Cloud Run
# can't host this. A single VM is enough until concurrent room count
# justifies horizontal scale (LiveKit supports clustering via redis once
# multi-node).
#
# This VM only runs livekit-server. Egress runs on a Cloud Run worker pool
# (worker_pool_egress.tf). Redis is Memorystore (memorystore.tf).
#
# TLS termination: caddy on the same host gets a Let's Encrypt cert for
# livekit.<domain> automatically and proxies wss://...:443 → ws://...:7880.
# WebRTC media flows direct on UDP 50000-60000 and TCP 7881 (no proxy).
# =============================================================================

resource "google_service_account" "livekit" {
  account_id   = "${local.app_name}-livekit"
  display_name = "LiveKit Server VM"
  description  = "Service account for the LiveKit GCE VM (config fetch from Secret Manager)"
}

# The VM only needs to read its own LiveKit secrets — not the full set.
resource "google_secret_manager_secret_iam_member" "livekit_api_key" {
  secret_id = "${local.secret_prefix}_LIVEKIT_API_KEY"
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.livekit.email}"
}

resource "google_secret_manager_secret_iam_member" "livekit_api_secret" {
  secret_id = "${local.secret_prefix}_LIVEKIT_API_SECRET"
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.livekit.email}"
}

resource "google_secret_manager_secret_iam_member" "livekit_webhook_key" {
  secret_id = "${local.secret_prefix}_LIVEKIT_WEBHOOK_API_KEY"
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.livekit.email}"
}

# Static external IP — referenced by the DNS A record for livekit.<domain>.
resource "google_compute_address" "livekit" {
  name   = "${local.app_name}-livekit-ip"
  region = var.region
}

# Public ingress: WebRTC TCP/UDP + TLS-terminated WebSocket signaling.
resource "google_compute_firewall" "livekit_public" {
  name    = "${local.app_name}-livekit-public"
  network = google_compute_network.vpc.name

  # 443: caddy (wss signaling), 80: caddy (ACME HTTP challenge)
  # 7881: WebRTC TCP fallback (LiveKit binds direct, not behind caddy)
  allow {
    protocol = "tcp"
    ports    = ["80", "443", "7881"]
  }

  # WebRTC media UDP range. Width matters: too narrow caps concurrent
  # participants; 10000 ports is generous for a single node.
  allow {
    protocol = "udp"
    ports    = ["50000-60000"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["livekit"]
}

# Internal ingress: allow the egress worker pool's Direct VPC traffic to
# reach LiveKit's signaling port for the rare case egress connects via
# private IP. Default route for egress is still public.
resource "google_compute_firewall" "livekit_internal" {
  name    = "${local.app_name}-livekit-internal"
  network = google_compute_network.vpc.name

  allow {
    protocol = "tcp"
    ports    = ["7880", "7881"]
  }

  allow {
    protocol = "udp"
    ports    = ["50000-60000"]
  }

  source_ranges = [var.vpc_cidr]
  target_tags   = ["livekit"]
}

# Startup script — installs docker + caddy + gcloud, fetches secrets, writes
# configs, launches livekit-server. Caddy auto-renews TLS for livekit.<domain>
# via Let's Encrypt (HTTP-01 challenge on :80, serves wss on :443).
#
# Pre-installs note: Debian 12 base image ships with NEITHER gcloud nor caddy.
# Both are added from their official apt repos. Docker comes from Docker's
# official repo (newer than debian.org's docker.io).
locals {
  livekit_startup_script = <<-EOT
    #!/usr/bin/env bash
    set -euxo pipefail

    export DEBIAN_FRONTEND=noninteractive

    # Base packages we need to add the third-party apt repos.
    apt-get update
    apt-get install -y curl ca-certificates gnupg lsb-release jq apt-transport-https \
      debian-keyring debian-archive-keyring

    # --- Google Cloud CLI (for Secret Manager fetch) -----------------------
    curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg \
      | gpg --dearmor -o /usr/share/keyrings/cloud-google-archive-keyring.gpg
    echo "deb [signed-by=/usr/share/keyrings/cloud-google-archive-keyring.gpg] https://packages.cloud.google.com/apt cloud-sdk main" \
      > /etc/apt/sources.list.d/google-cloud-sdk.list

    # --- Caddy (TLS + reverse proxy for wss://) ---------------------------
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
      | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
      > /etc/apt/sources.list.d/caddy-stable.list

    # --- Docker (official) ------------------------------------------------
    curl -fsSL https://download.docker.com/linux/debian/gpg \
      | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo "deb [signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" \
      > /etc/apt/sources.list.d/docker.list

    apt-get update
    apt-get install -y google-cloud-cli caddy docker-ce docker-ce-cli containerd.io

    # --- Fetch LiveKit secrets via VM service account --------------------
    LIVEKIT_API_KEY=$(gcloud secrets versions access latest --secret=${local.secret_prefix}_LIVEKIT_API_KEY)
    LIVEKIT_API_SECRET=$(gcloud secrets versions access latest --secret=${local.secret_prefix}_LIVEKIT_API_SECRET)
    LIVEKIT_WEBHOOK_API_KEY=$(gcloud secrets versions access latest --secret=${local.secret_prefix}_LIVEKIT_WEBHOOK_API_KEY)

    REDIS_HOST=${google_redis_instance.livekit_bus.host}
    REDIS_PORT=${google_redis_instance.livekit_bus.port}
    EXTERNAL_IP=${google_compute_address.livekit.address}

    # --- LiveKit config ---------------------------------------------------
    mkdir -p /etc/livekit
    cat > /etc/livekit/livekit.yaml <<YAML
    port: 7880
    bind_addresses:
      - "0.0.0.0"
    rtc:
      tcp_port: 7881
      port_range_start: 50000
      port_range_end: 60000
      use_external_ip: true
      external_ip: "$${EXTERNAL_IP}"
    keys:
      $${LIVEKIT_API_KEY}: $${LIVEKIT_API_SECRET}
    redis:
      address: "$${REDIS_HOST}:$${REDIS_PORT}"
    logging:
      level: info
    webhook:
      api_key: $${LIVEKIT_WEBHOOK_API_KEY}
      urls:
        - ${var.api_url}/api/v1/webhooks/video/
    YAML

    # --- Caddyfile (write before starting caddy) -------------------------
    cat > /etc/caddy/Caddyfile <<CADDY
    ${var.livekit_subdomain}.${var.domain_name} {
      reverse_proxy localhost:7880
    }
    CADDY

    # --- Start services ---------------------------------------------------
    systemctl enable --now docker
    systemctl enable --now caddy

    # Pull and start LiveKit. host networking so WebRTC ports map directly.
    docker pull livekit/livekit-server:latest
    docker run -d --restart unless-stopped \
      --name livekit \
      --network host \
      -v /etc/livekit/livekit.yaml:/etc/livekit.yaml:ro \
      livekit/livekit-server:latest \
      --config /etc/livekit.yaml --bind 0.0.0.0
  EOT
}

resource "google_compute_instance" "livekit" {
  name         = "${local.app_name}-livekit"
  machine_type = var.livekit_machine_type
  zone         = var.livekit_zone

  tags = ["livekit"]

  boot_disk {
    initialize_params {
      image = var.livekit_image
      size  = var.livekit_disk_size
      type  = "pd-balanced"
    }
  }

  network_interface {
    network    = google_compute_network.vpc.id
    subnetwork = google_compute_subnetwork.subnet.id

    access_config {
      nat_ip = google_compute_address.livekit.address
    }
  }

  service_account {
    email  = google_service_account.livekit.email
    scopes = ["cloud-platform"]
  }

  metadata = {
    enable-oslogin = "TRUE"
  }

  metadata_startup_script = local.livekit_startup_script

  allow_stopping_for_update = true

  depends_on = [
    google_redis_instance.livekit_bus,
    google_secret_manager_secret_iam_member.livekit_api_key,
    google_secret_manager_secret_iam_member.livekit_api_secret,
    google_secret_manager_secret_iam_member.livekit_webhook_key,
  ]
}

output "livekit_external_ip" {
  description = "LiveKit VM static external IP (point livekit.<domain> A record here)"
  value       = google_compute_address.livekit.address
}

output "livekit_internal_ip" {
  description = "LiveKit VM private IP (used by egress worker pool)"
  value       = google_compute_instance.livekit.network_interface[0].network_ip
}
