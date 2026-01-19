# Backend Workflow Inventory (Audit Baseline)

This document enumerates **all user/system workflows** supported by the backend.
It is the baseline for a code-path audit and gap analysis.

Legend:
- **Actor**: who initiates the workflow (Attendee, Organizer, Admin, System)
- **Entry Points**: primary API endpoints or background triggers
- **Core Services**: key service modules involved

---

## 1) Authentication & Identity

### 1.1 Local signup (attendee)
- **Actor**: Attendee
- **Entry Points**: `POST /api/v1/auth/signup/`
- **Core Services**: `accounts.serializers.SignupSerializer`, `accounts.views.SignupView`
- **Notes**: email verification token issued; login blocked until verified.

### 1.2 Email verification
- **Actor**: Attendee
- **Entry Points**: `POST /api/v1/auth/verify-email/`
- **Core Services**: `accounts.views.EmailVerificationView`
- **Notes**: token consumed, user verified, JWT issued.

### 1.3 Login
- **Actor**: Attendee/Organizer
- **Entry Points**: `POST /api/v1/auth/token/`
- **Core Services**: `accounts.serializers.CustomTokenObtainPairSerializer`
- **Notes**: blocks unverified users.

### 1.4 Token refresh
- **Actor**: Attendee/Organizer
- **Entry Points**: `POST /api/v1/auth/token/refresh/`

### 1.5 Password reset request
- **Actor**: Attendee/Organizer
- **Entry Points**: `POST /api/v1/auth/password-reset/`

### 1.6 Password reset confirm
- **Actor**: Attendee/Organizer
- **Entry Points**: `POST /api/v1/auth/password-reset/confirm/`

### 1.7 Password change (logged in)
- **Actor**: Attendee/Organizer
- **Entry Points**: `POST /api/v1/auth/password-change/`

### 1.8 OAuth login (Google)
- **Actor**: Attendee/Organizer
- **Entry Points**: `GET /api/v1/auth/google/callback/`
- **Notes**: Account creation or linking.

---

## 2) User Profile & Account Management

### 2.1 View/update profile
- **Actor**: Attendee/Organizer
- **Entry Points**: `GET|PATCH /api/v1/users/me/`
- **Notes**: updates first/last name via `full_name` setter.

### 2.2 Organizer profile
- **Actor**: Organizer
- **Entry Points**: `GET|PATCH /api/v1/users/me/organizer-profile/`

### 2.3 Notification preferences
- **Actor**: Attendee/Organizer
- **Entry Points**: `GET|PATCH /api/v1/users/me/notifications/`

### 2.4 Sessions management
- **Actor**: Attendee/Organizer
- **Entry Points**: `GET /api/v1/users/me/sessions/`, `DELETE /api/v1/users/me/sessions/{uuid}/`, `POST /api/v1/users/me/sessions/logout-all/`

### 2.5 Account downgrade to attendee
- **Actor**: Organizer
- **Entry Points**: `POST /api/v1/users/me/downgrade/`
- **Notes**: cancels subscription immediately, requires no active events/courses.

### 2.6 Account deletion (GDPR)
- **Actor**: Attendee/Organizer
- **Entry Points**: `POST /api/v1/users/me/delete-account/`
- **Notes**: anonymization + soft delete.

### 2.7 Data export (GDPR)
- **Actor**: Attendee/Organizer
- **Entry Points**: `POST /api/v1/users/me/export-data/`

### 2.8 Public organizer profile
- **Actor**: Public
- **Entry Points**: `GET /api/v1/organizers/{uuid}/`

---

## 3) Subscription & Billing

### 3.1 View subscription
- **Actor**: Attendee/Organizer
- **Entry Points**: `GET /api/v1/subscription/`

### 3.2 Create/upgrade subscription
- **Actor**: Attendee/Organizer
- **Entry Points**: `POST /api/v1/subscription/`
- **Notes**: Stripe or local-only mode.

### 3.3 Update subscription plan
- **Actor**: Organizer
- **Entry Points**: `POST /api/v1/subscription/{uuid}/` (update)

### 3.4 Cancel subscription
- **Actor**: Organizer
- **Entry Points**: `POST /api/v1/subscription/cancel/`

### 3.5 Reactivate subscription
- **Actor**: Organizer
- **Entry Points**: `POST /api/v1/subscription/reactivate/`

### 3.6 Sync subscription from Stripe
- **Actor**: Organizer/System
- **Entry Points**: `POST /api/v1/subscription/sync/`

### 3.7 Confirm checkout session
- **Actor**: Organizer
- **Entry Points**: `POST /api/v1/subscription/confirm-checkout/`

### 3.8 Payment methods
- **Actor**: Organizer
- **Entry Points**: `GET|POST|DELETE /api/v1/payment-methods/`

### 3.9 Stripe webhooks
- **Actor**: System (Stripe)
- **Entry Points**: `POST /webhooks/stripe/`

### 3.10 Billing automation
- **Actor**: System
- **Entry Points**: scheduled tasks in `billing.tasks` (usage resets, trial expiry, notifications)

---

## 4) Events

### 4.1 Create event
- **Actor**: Organizer
- **Entry Points**: `POST /api/v1/events/`
- **Core Services**: `events.services.event_service.create_event` (capability + atomic increment)

### 4.2 Update event
- **Actor**: Organizer
- **Entry Points**: `PATCH /api/v1/events/{uuid}/`

### 4.3 Publish/Unpublish
- **Actor**: Organizer
- **Entry Points**: `POST /api/v1/events/{uuid}/publish/`

### 4.4 Upload featured image
- **Actor**: Organizer
- **Entry Points**: `POST /api/v1/events/{uuid}/upload-image/`

### 4.5 Event sessions (multi-session)
- **Actor**: Organizer
- **Entry Points**: `/api/v1/events/{event_uuid}/sessions/...`

### 4.6 Custom registration fields
- **Actor**: Organizer
- **Entry Points**: `/api/v1/events/{event_uuid}/custom-fields/...`

### 4.7 Public events list/detail
- **Actor**: Public
- **Entry Points**: `GET /api/v1/public/events/`, `GET /api/v1/public/events/{identifier}/`

---

## 5) Registrations & Attendance

### 5.1 Public registration
- **Actor**: Attendee/Guest
- **Entry Points**: `POST /api/v1/public/events/{event_id}/register/` (via registrations viewset)

### 5.2 Organizer registration management
- **Actor**: Organizer
- **Entry Points**: `/api/v1/events/{event_uuid}/registrations/` (list, bulk add, update, cancel)

### 5.3 Waitlist management
- **Actor**: Organizer/System
- **Entry Points**: `/api/v1/events/{event_uuid}/registrations/waitlist/...`

### 5.4 Attendance sync (Zoom)
- **Actor**: Organizer/System
- **Entry Points**: `POST /api/v1/events/{uuid}/sync_attendance/`

### 5.5 Attendance matching
- **Actor**: Organizer
- **Entry Points**: `/api/v1/events/{uuid}/unmatched_participants/`, `/api/v1/events/{uuid}/match_participant/`

### 5.6 Attendance overrides
- **Actor**: Organizer
- **Entry Points**: registration attendance override endpoints

---

## 6) Certificates

### 6.1 Manage certificate templates
- **Actor**: Organizer
- **Entry Points**: `/api/v1/certificate-templates/` (list/create/update/delete/upload/preview/set-default/available)

### 6.2 Issue certificates
- **Actor**: Organizer
- **Entry Points**: `/api/v1/events/{event_uuid}/certificates/issue/`

### 6.3 Revoke certificates
- **Actor**: Organizer
- **Entry Points**: `/api/v1/events/{event_uuid}/certificates/{uuid}/revoke/`

### 6.4 Attendee certificate access
- **Actor**: Attendee
- **Entry Points**: `/api/v1/certificates/` (my certificates)

### 6.5 Public verification
- **Actor**: Public
- **Entry Points**: `GET /api/v1/public/certificates/verify/{code}/`

---

## 7) Learning (LMS)

### 7.1 Create course
- **Actor**: LMS owner
- **Entry Points**: `POST /api/v1/courses/`

### 7.2 Course content (modules, content, assignments)
- **Actor**: Organizer/LMS owner
- **Entry Points**: `/api/v1/events/{event_uuid}/modules/...` and `/api/v1/courses/{course_uuid}/modules/...`

### 7.3 Course enrollments
- **Actor**: Attendee
- **Entry Points**: `/api/v1/enrollments/` + `/api/v1/enrollments/checkout/`

### 7.4 Course sessions (hybrid)
- **Actor**: LMS owner
- **Entry Points**: `/api/v1/courses/{course_uuid}/sessions/...`

### 7.5 Assignment submissions
- **Actor**: Attendee
- **Entry Points**: `/api/v1/submissions/` (my submissions)

### 7.6 Instructor grading
- **Actor**: LMS owner
- **Entry Points**: `/api/v1/courses/{course_uuid}/submissions/.../grade/`

### 7.7 Learning progress
- **Actor**: Attendee
- **Entry Points**: `/api/v1/learning/` (my learning)

---

## 8) Integrations (Zoom, Email, Recordings)

### 8.1 Zoom OAuth connect
- **Actor**: Organizer/LMS owner
- **Entry Points**: `/api/v1/integrations/zoom/initiate/`, `/api/v1/integrations/zoom/callback/`

### 8.2 Zoom status/disconnect
- **Actor**: Organizer/LMS owner
- **Entry Points**: `/api/v1/integrations/zoom/status/`, `/api/v1/integrations/zoom/disconnect/`

### 8.3 Zoom meetings list
- **Actor**: Organizer
- **Entry Points**: `/api/v1/integrations/zoom/meetings/`

### 8.4 Recordings
- **Actor**: Organizer
- **Entry Points**: `/api/v1/events/{event_uuid}/recordings/`

### 8.5 Email logs
- **Actor**: Organizer
- **Entry Points**: `/api/v1/events/{event_uuid}/emails/`

### 8.6 Zoom webhooks
- **Actor**: System (Zoom)
- **Entry Points**: webhook endpoints for meeting/participant events

---

## 9) Contacts & Marketing

### 9.1 Manage contacts
- **Actor**: Organizer
- **Entry Points**: `/api/v1/contacts/` (list/create/update/import)

### 9.2 Contact lists & tagging
- **Actor**: Organizer
- **Entry Points**: `/api/v1/contacts/lists/...`

---

## 10) Promo Codes

### 10.1 Create/manage promo codes
- **Actor**: Organizer
- **Entry Points**: `/api/v1/promo-codes/`

### 10.2 Apply promo code
- **Actor**: Attendee/Organizer
- **Entry Points**: registration/payment flows

---

## 11) Feedback

### 11.1 Submit feedback
- **Actor**: Attendee
- **Entry Points**: `/api/v1/feedback/`

---

## 12) Badges

### 12.1 Issue badges
- **Actor**: Organizer/System
- **Entry Points**: badge services & event completion hooks

---

## 13) Notifications & Audit

### 13.1 In-app notifications
- **Actor**: System
- **Entry Points**: `accounts.models.Notification`, tasks and webhook handlers

### 13.2 Audit log
- **Actor**: System/Admin
- **Entry Points**: `accounts.audit` logging

---

## 14) Admin Operations

### 14.1 Admin user creation
- **Actor**: Admin/System
- **Entry Points**: `manage.py create_admin`

### 14.2 Admin dashboards
- **Actor**: Admin
- **Entry Points**: Django admin for all models

---

## 15) System/Background Jobs

### 15.1 Usage reset
- **Actor**: System
- **Entry Points**: `billing.tasks.reset_subscription_usage`

### 15.2 Trial expiry
- **Actor**: System
- **Entry Points**: `billing.tasks.expire_trials`

### 15.3 Sync subscription
- **Actor**: System
- **Entry Points**: `billing.tasks.sync_stripe_subscription`

### 15.4 Zoom meeting creation
- **Actor**: System
- **Entry Points**: `learning.tasks.create_zoom_meeting_for_course/session`

### 15.5 Attendance sync
- **Actor**: System
- **Entry Points**: `events.tasks.sync_zoom_attendance`

---

## 16) Public Surfaces

### 16.1 Public event pages
- **Actor**: Public
- **Entry Points**: `GET /api/v1/public/events/...`

### 16.2 Public certificate verification
- **Actor**: Public
- **Entry Points**: `GET /api/v1/public/certificates/verify/{code}/`

---

## 17) Observability & Debugging

### 17.1 Debug session failure
- **Actor**: Admin/System
- **Entry Points**: `debug_session_failure.py` (manual)

