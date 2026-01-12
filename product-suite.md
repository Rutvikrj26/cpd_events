# CPD Events Product Suite

This document summarizes the product suite and the feature sets exposed across subscription plans, based on the current codebase and pricing pages.

## Product Suite Overview

### Organization & Team Management
- Multi-tenant organizations as the core workspace.
- Four organization roles with distinct capabilities:
  - **Admin**: Full organizer + course manager capabilities, manages billing (1 included in $199/mo base)
  - **Organizer**: Create events, manage registrations ($129/seat or self-paid)
  - **Course Manager**: Create all courses, manage enrollments ($129/seat)
  - **Instructor**: Manage only assigned course (unlimited, free)
- Team collaboration with invitations and seat management.
- Organization branding (logos, colors, slugs/domains).

### Event Management
- Event creation wizard with scheduling and ticketing.
- Multi-session events and hybrid/virtual support.
- Zoom integration for meetings/webinars with attendance tracking.
- Automatic recording ingestion with visibility controls.
- Post-event feedback surveys.

### Learning Management System (LMS)
- Self-paced and hybrid courses.
- Modules with release schedules (immediate, scheduled, relative, prerequisite).
- Content types: video, documents, rich text, quizzes, external links.
- Progress tracking at content, module, and course levels.
- Assignments with draft/review/grade workflows and rubric support.

### Certificates & Compliance
- Certificate template builder with drag-and-drop fields.
- Automated issuance on event attendance or course completion.
- Manual issuance overrides.
- Public verification pages and QR codes.
- Immutable snapshots of attendee data at issuance time.
- CPD credit tracking and reporting.

### Commerce & Billing
- Stripe subscriptions with trials, upgrades, and downgrades.
- Stripe Connect for organizer payouts.
- Ticketing with paid vs free events and promo codes.
- Capacity management and attendance limits.

### CRM & Communications
- Centralized contacts across events.
- Segmentation via lists/tags and engagement history.
- Transactional and engagement email notifications with delivery tracking.

### Integrations
- Zoom (webhooks, attendance, recordings).
- Stripe (payments, subscriptions, Connect onboarding).
- File storage for resources and generated PDFs.

## Plans and Features

Plan naming in the running app uses these plan IDs:
- attendee
- organizer
- lms
- organization

Legacy marketing names (starter/professional/premium/team) have been moved to `docs/legacy`; the active plan IDs above drive enforcement and access. Where limits are driven by Stripe products, the database values override the defaults below.

### Attendee (Free)
- Browse and register for events.
- Track attendance and CPD history.
- Download earned certificates.
- Manage profile and receive notifications.

Limits (default):
- Events per month: 0
- Courses per month: 0
- Certificates per month: 0
- Max attendees per event: 0

### Organizer
- Create and manage events.
- Zoom integration for virtual events.
- Custom certificate templates.
- Priority email support.

Limits (default):
- Events per month: 30
- Certificates per month: 500
- Max attendees per event: 500
- Courses per month: 0

### LMS
- Create and manage courses.
- Self-paced course builder.
- Course certificates.
- Learner progress tracking.
- Priority email support.

Limits (default):
- Courses per month: 30
- Certificates per month: 500
- Events per month: 0
- Max attendees per event: 0

### Organization ($199/month base)

**Base Plan Includes:**
- 1 Admin (has full organizer + course manager capabilities)
- Unlimited events
- Unlimited courses
- Unlimited certificates
- Max 2,000 attendees per event
- Unlimited Course Instructors (free)

**Additional Seats:**
- **Organizers**: Require organizer subscription ($129/seat if org-paid, or organizer pays themselves)
- **Course Managers**: $129/seat/month (can create and manage all courses)
- **Instructors**: FREE and unlimited (can only manage their assigned course)

**Features:**
- Multi-user team access and collaboration
- Organization branding (logo, colors, custom domain/slug)
- White-label options
- API access
- Team collaboration tools
- Shared certificate templates
- Dedicated account management
- Priority support

**Role Capabilities:**
- **Admin**: Full organizer capabilities (create events) + full course manager capabilities (create courses) + manage organization settings, billing, and team members
- **Organizer**: Create and manage events, manage contacts, access event registrations
- **Course Manager**: Create and manage all organization courses, manage enrollments, grade assignments
- **Instructor**: Manage only assigned course, view enrollments, grade assignments for their course

## Notes
- Feature lists in the pricing UI are built from StripeProduct features when available, otherwise they fall back to the defaults listed above.
- Legacy tier names are archived under `docs/legacy` only; active plan IDs remain organizer/lms/organization/attendee.
