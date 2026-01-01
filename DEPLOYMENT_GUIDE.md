# Deployment & Setup Guide

This guide summarizes the steps to deploy the Accredit platform from scratch or perform updates. It highlights the manual steps remaining outside of the current `accredit` CLI automation.

## 🛠 Manual Components Checklist
Before running the automated tools, the following must be handled manually in the GCP/Firebase Consoles:

| Component | Responsibility | Manual Actions |
| :--- | :--- | :--- |
| **GCP Project** | Cloud Console | Create project, **Enable Billing**, and note the `Project ID`. |
| **Firebase** | Firebase Console | Link the GCP Project to Firebase, choose a plan (Blaze required), and create the Hosting site. |
| **Secrets** | Secret Manager | Manually add sensitive keys: `DJANGO_SECRET_KEY`, `STRIPE_KEYS`, `ZOOM_CREDENTIALS`. |
| **Domain DNS** | Cloud DNS / Registrar | Map custom domains (e.g., `api.accredit.store`) to Cloud Run and Firebase Hosting. |
| **Org Policies** | GCP Org Admin | Ensure **VPC Service Controls** or IAM policies don't block GCS bucket creation/access. |

---

## 🚀 TLDR: New Environment Setup
*Best for: First-time deployment in a new GCP project.*

1.  **Initialization**:
    ```bash
    accredit setup init  # Set your Project ID and Default Env
    accredit cloud bootstrap --env dev  # Enables APIs, creates AR repo & buckets
    ```
2.  **Secrets**:
    Populate the Secret Manager with the required runtime keys identified in `production.py`.
3.  **Deployment**:
    ```bash
    accredit cloud up --env dev --auto-approve
    ```
    *This will: Initialize/Apply Terraform, Build Backend (AR), Deploy to Cloud Run, and Deploy Frontend to Firebase.*
4.  **Post-Deploy**:
    Create a superuser to access the Django admin:
    ```bash
    accredit cloud backend shell  # Then run: python manage.py createsuperuser
    ```

---

## 🔄 TLDR: Updating a Setup
*Best for: Daily development and feature releases.*

1.  **Sync State** (if on a new machine):
    ```bash
    accredit cloud sync --env dev
    ```
2.  **Deploy Changes**:
    ```bash
    accredit cloud up --env dev --auto-approve
    ```
    *This automatically handles:*
    - **Terraform**: Infrastructure drift/updates.
    - **Migrations**: Automated during container startup via `entrypoint.sh`.
    - **Static Files**: Collected and served via Whitenoise.
    - **Frontend**: Incremental Firebase Hosting deployment.

---

> [!TIP]
> **Stability Note**: The backend is currently configured with **2GiB Memory** and **WEB_CONCURRENCY=1** to prevent OOM errors on Cloud Run's serverless nodes. Scaling is managed by Cloud Run adding more containers, not more processes per container.
