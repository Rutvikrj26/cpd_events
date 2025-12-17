# Service Layer Documentation

This document describes the service layer architecture of the CPD Events platform. Services encapsulate business logic and external integrations, keeping views and models lean.

## Overview

Services are implemented as singleton instances where appropriate, or as standalone classes for specific domains. They handle:
- External API integrations (Zoom, Stripe)
- Complex business logic (Certificate generation, Event duplication)
- Asynchronous tasks helpers (Email sending, Webhook processing)

## Service Modules

### 1. Accounts Service (`accounts.services`)

#### `ZoomService`
Handles OAuth integration with Zoom for user accounts.

**Key Responsibilities:**
- OAuth flow initiation (`initiate_oauth`) and completion (`complete_oauth`).
- Token management: secure storage, refresh (`refresh_tokens`), and revocation (`disconnect`).
- Fetching user profile information from Zoom.

---

### 2. Billing Service (`billing.services`)

#### `StripeService`
Manages all interactions with the Stripe API.

**Key Responsibilities:**
- **Customer Management**: Creating and updating Stripe customers (`create_customer`).
- **Subscriptions**: Creating (`create_subscription`), canceling (`cancel_subscription`), and reactivating (`reactivate_subscription`) subscriptions.
- **Payment Methods**: Attaching and detaching payment methods (`attach_payment_method`).
- **Checkout & Portal**: Generating sessions for Checkout (`create_checkout_session`) and the Customer Portal (`create_portal_session`).

---

### 3. Certificates Service (`certificates.services`)

#### `CertificateService`
Handles the generation, storage, and issuance of CPD certificates.

**Key Responsibilities:**
- **Generation**: Rendering certificates using ReportLab (`generate_pdf`, `_render_pdf`).
- **Storage**: Uploading generated PDFs to GCS/S3 (`upload_pdf`) and generating signed URLs (`get_pdf_url`).
- **Issuance**: Individual (`issue_certificate`) and bulk issuance (`issue_bulk`) logic.
- **Delivery**: Sending certificate emails to attendees (`send_certificate_email`).

---

### 4. Events Service (`events.services`)

#### `ZoomMeetingService`
Manages the lifecycle of Zoom meetings associated with events.

**Key Responsibilities:**
- **Meeting Management**: Creating (`create_meeting`), updating (`update_meeting`), and deleting (`delete_meeting`) meetings on Zoom.
- **Authentication**: Using the event owner's Zoom credentials.

#### `EventService`
Handles high-level event operations.

**Key Responsibilities:**
- **Duplication**: Deep copying of events, including modules, assignments, and settings (`duplicate_event`).
- **Cancellation**: Cancelling events and notifying registrants (`cancel_event`).

---

### 5. Integrations Service (`integrations.services`)

#### `EmailService`
A unified interface for sending transactional emails.

**Key Responsibilities:**
- **Sending**: sending templated individual (`send_email`) and bulk emails (`send_bulk_emails`).
- **Templates**: Manages mapping of logical template names to file paths.

#### `WebhookProcessor`
Processes incoming webhooks from external providers (mainly Zoom).

**Key Responsibilities:**
- **Zoom Events**: Handling `meeting.ended`, `recording.completed`, and participant events.
- **Data Consistency**: Updating local models based on external state changes.

#### `AttendanceMatcher`
Correlates Zoom participant data with event registrations.

**Key Responsibilities:**
- **Matching**: `match_attendance` links Zoom `user_email` or name to `Registration` records to mark attendance automatically.
