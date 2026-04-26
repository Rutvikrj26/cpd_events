# =============================================================================
# Firebase Auth (Identity Platform)
#
# Identity Platform is the Google Cloud surface that backs Firebase Auth.
# Enabling it here gives you the Auth tenant. Provider configuration
# (Email/Password, Google, etc.) is most ergonomic in the Firebase console
# — terraform `google_identity_platform_*_config` resources exist but flip
# easily out of sync with manual changes. Recommend enabling IdP here, then
# configuring providers via console.
#
# After apply:
#   1. Visit Firebase console → "Add Firebase to GCP project" (one-time).
#   2. Enable sign-in providers (email/password + any social).
#   3. Project Settings → Service Accounts → "Generate new private key".
#   4. Upload the JSON content as the FIREBASE_CREDENTIALS_JSON secret:
#        accredit cloud secrets upload --backend --env prod
# =============================================================================

# google_identity_platform_config is a project-level singleton. If you enable
# Identity Platform / Firebase Auth via the console BEFORE the first
# `terraform apply`, this resource will fail with "already exists" and you'll
# need to import:
#   terraform import google_identity_platform_config.default <project_id>
# Cleanest path: run `terraform apply` first, then visit Firebase console to
# add the project + enable providers.
resource "google_identity_platform_config" "default" {
  project = var.project_id

  # Hard-block sign-ups at the IdP layer. The app gates registration via
  # invite codes (REGISTRATION_MODE=invite_only), so anonymous self-signup
  # at the Firebase layer is unnecessary surface area.
  sign_in {
    allow_duplicate_emails = false

    email {
      enabled           = true
      password_required = true
    }
  }

  depends_on = [
    google_project_service.required_apis,
  ]
}
