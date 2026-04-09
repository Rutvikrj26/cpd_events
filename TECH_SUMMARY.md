# Accredit — Technical Summary

> Generated from code analysis, April 2026. For historical docs see `archive/`.

## What Is This

A single-tenant, self-hosted CPD (Continuing Professional Development) event and learning management platform for educational hubs. Each deployment serves one organization with complete data sovereignty. Features: events, LMS courses, certificate generation, CPD tracking, built-in video conferencing. Payments via Stripe.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18.2, TypeScript 5.2, Vite 5, Tailwind CSS, Radix UI (shadcn/ui) |
| Backend | Django 6.0, Django REST Framework 3.15, PostgreSQL 15+ |
| Auth | JWT (SimpleJWT), Google OAuth |
| Payments | Stripe (subscriptions, checkout, Connect for payouts, tax) |
| Video | LiveKit (self-hosted, open-source, bundled in Docker Compose) |
| Email | Brevo via django-anymail |
| Async tasks | Google Cloud Tasks |
| Storage | Google Cloud Storage |
| Hosting | Google Cloud Run (serverless), Cloud SQL |
| IaC | Terraform (dev/prod environments) |
| Containers | Docker, Docker Compose (local dev) |

---

## Backend — 13 Django Apps (`backend/src/`)

| App | What It Does | Key Models |
|-----|-------------|------------|
| **accounts** | User auth, profiles, OAuth, email verification, CPD tracking, GDPR deletion, audit logs | User, UserSession, CPDRequirement, Notification, AuditLog |
| **events** | Event lifecycle (draft > published > live > completed > closed), multi-session, speakers, custom fields | Event, EventSession, Speaker, EventCustomField |
| **registrations** | Registration flow, Stripe payments, waitlist, guest registration, attendance reconciliation | Registration, AttendanceRecord, CustomFieldResponse |
| **certificates** | PDF certificate generation from templates, field positioning, public verification | CertificateTemplate, Certificate, CertificateStatusHistory |
| **billing** | Stripe subscriptions, checkout, invoices, payment methods, payouts, DB-driven pricing | Subscription, StripeProduct, StripePrice, Invoice, PaymentMethod, Payout |
| **learning** | Full LMS — courses, modules (video/doc/quiz/text), assignments, grading, progress, hybrid sessions | Course, EventModule, ModuleContent, Assignment, AssignmentSubmission, CourseEnrollment, CourseSession |
| **organizations** | Multi-tenant teams, member invitations, role-based access, org-level billing | Organization, OrganizationMembership, OrganizationSubscription |
| **contacts** | CRM-style contact management, lists, tags, bulk import/export | ContactList, Contact, Tag |
| **badges** | Badge template design and issuance | BadgeTemplate, IssuedBadge |
| **feedback** | Post-event feedback with ratings | EventFeedback |
| **promo_codes** | Discount codes (percentage/fixed), usage limits | PromoCode, PromoCodeUsage |
| **integrations** | LiveKit webhooks, video recording sync, email delivery logging | VideoWebhookLog, VideoRecording, EmailLog |
| **common** | Shared infrastructure — base models (UUID, soft-delete), RBAC, permissions, pagination, GCS storage, Cloud Tasks | BaseModel, SoftDeleteModel |

### RBAC System

- Decorator-based: `@roles('organizer', 'admin', route_name='...', plans=['organization'])`
- Plan hierarchy: attendee (0) < organizer/lms (1) < organization (2)
- Backend generates a **manifest** (`/api/v1/auth/manifest/`) sent to frontend with allowed routes and features
- Account types: ATTENDEE, ORGANIZER, COURSE_MANAGER, ADMIN
- Organization roles: admin, organizer, course_manager, instructor

### API Structure

All endpoints under `/api/v1/`. Public endpoints at `/api/v1/public/`. Stripe webhooks at `/webhooks/stripe/`.

---

## Frontend — React SPA (`frontend/src/`)

### Architecture

- **State**: AuthContext (JWT + manifest-driven feature flags) + OrganizationContext (org selection, role checks)
- **API client**: Axios with Bearer token interceptor, error formatting
- **UI library**: 50+ shadcn/ui components (Radix primitives + Tailwind)
- **Routing**: React Router with role-based protected routes

### Pages by Area

**Auth** — Login, Signup, Email verification, Password reset, Google OAuth callback

**Attendee** — Dashboard (stats, upcoming events, recent certs), Event discovery, My courses, Course player, Certificates, CPD tracking, Badges

**Organizer** — Dashboard, Event CRUD (5-step wizard), Event management, Contacts CRM (import/export/tags), Certificate templates, Badge designer, Video room management, Reports/analytics

**Organization** — Dashboard, Settings, Team management (invitations, roles), Billing (seat management), Course management (create/edit with modules, sessions, assignments, announcements), Onboarding wizard

**Public** — Landing, Pricing, Features, FAQ, About, Contact, Terms/Privacy/Cookies, Event discovery, Course catalog, Organization directory, Certificate/badge verification

**Billing** — Stripe checkout, Subscription management, Invoices

### API Modules (16)

accounts, auth, badges, billing, certificates, contacts, courses, cpd, events, feedback, integrations, learning, notifications, organizations, payouts, promo-codes, registrations, reports

---

## Infrastructure

### Local Dev (Docker Compose)

- PostgreSQL 16 (port 5432)
- GCP Cloud Tasks emulator (port 8123)
- GCS emulator (port 4443)
- Django backend (port 8000)

### Production (GCP)

- Cloud Run (serverless containers)
- Cloud SQL (PostgreSQL)
- Cloud Storage (media, certificates)
- Terraform for provisioning (dev + prod environments)

### CLI Tool (`cli/`)

Custom Python CLI for setup, local dev, Docker operations, and cloud deployment.

---

## Current Status (as of commit c704bd0)

### What's Production-Ready

All 13 backend apps have full implementations — models, serializers, views, services. All frontend pages have real API integration, no placeholders. Key flows working:

- User auth (email + Google OAuth + JWT refresh)
- Event lifecycle with multi-session support
- Registration with Stripe payments, tax, promo codes
- Certificate PDF generation and public verification
- Full LMS (courses, modules, assignments, grading, progress)
- Billing (subscriptions, invoices, Stripe Connect payouts)
- Contacts CRM with bulk operations
- Badge design and issuance
- LiveKit video conferencing with automatic attendance tracking

### What's In Progress

**Organization integration** — the active work area:
- New ADMIN account type added
- `OrganizationLinkingService` links organizers to orgs, upgrades account type, cancels individual subscription
- Auto-downgrade signal when user loses last admin role
- Frontend `AuthenticatedRoot` wrapper added
- ~15 test files updated but need verification

### Recent Changes

- **✅ Migrated from Zoom to LiveKit** — Now using self-hosted LiveKit for video conferencing with webhook-based attendance tracking. Eliminates OAuth complexity and external API dependencies.

---

## Database

46 migration files across all apps. Schema is mature and stable — the only recent migration adds the ADMIN account type.

---

## Testing

- **Backend**: pytest with Factory Boy fixtures (`conftest.py`: 15K lines, `factories.py`: 12K lines). 50+ test files.
- **Frontend**: Vitest for unit tests, Playwright for E2E (auth, attendee, organizer, event creation flows).
