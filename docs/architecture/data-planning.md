# Data Models Plan: Overview

## Table of Contents
1. [Introduction](#introduction)
2. [Design Principles](#design-principles)
3. [Django App Structure](#django-app-structure)
4. [Entity Relationship Diagram](#entity-relationship-diagram)
5. [Entity Summary](#entity-summary)
6. [State Machines](#state-machines)
7. [Cross-Cutting Concerns](#cross-cutting-concerns)
8. [Migration Strategy](#migration-strategy)
9. [Phase 2: Organizations](#phase-2-organizations)
10. [Document Index](#document-index)

---

## Introduction

This document provides a comprehensive overview of the data model architecture for the Event Management Platform. The platform supports:

- **Attendees**: Users who register for events, receive certificates, and track CPD credits
- **Organizers**: Users who create events, manage attendance, and issue certificates
- **Events**: Virtual events with Zoom integration, attendance tracking, and certification
- **Certificates**: Verifiable credentials issued to attendees

### Scope

**Phase 1 (MVP)**:
- Individual attendee and organizer accounts
- Event creation with Zoom integration
- Registration and attendance tracking
- Certificate issuance and verification
- Contact management
- Subscription billing

**Phase 2 (Future)**:
- Organization layer (teams, shared resources)
- Role-based permissions within orgs
- Org-wide reporting and branding

---

## Design Principles

### 1. Primary Key Strategy

Every model uses a dual identifier approach:

| Type | Purpose | Implementation |
|------|---------|----------------|
| **Integer PK** | Internal joins, efficient indexing | `id` (auto-increment) |
| **UUID** | External APIs, URLs, no enumeration | `uuid` (indexed, unique) |

```python
# URLs use UUID
/events/550e8400-e29b-41d4-a716-446655440000/

# Internal queries use integer PK for performance
Event.objects.filter(owner_id=123)
```

### 2. Soft Deletes

Entities requiring audit trails or historical integrity use soft deletes:

| Soft Delete | Hard Delete |
|-------------|-------------|
| User (anonymize) | EventInvitation |
| Event | EventReminder |
| Certificate | Contact |
| CertificateTemplate | ContactList |
| Registration | CustomFieldResponse |
| | ZoomWebhookLog (retention) |
| | EmailLog (retention) |

### 3. Timestamps

Every model includes:
```python
created_at = models.DateTimeField(auto_now_add=True)
updated_at = models.DateTimeField(auto_now=True)
```

### 4. Email Handling

All emails are:
- Stored lowercase (canonicalized)
- Stripped of whitespace
- Validated for format

```python
# Custom email field ensures consistency
email = LowercaseEmailField(unique=True)
```

### 5. JSON Field Schemas

All JSONField usages have documented schemas with validation:

```python
field_positions = models.JSONField(
    default=dict,
    validators=[validate_field_positions_schema]
)
```

### 6. Denormalization Strategy

Denormalized counts are updated via:
- Django signals for simple cases
- Celery tasks for expensive computations
- Database triggers for critical consistency (optional)

Denormalized fields are marked with comments:
```python
# Denormalized: updated via signal on Contact save/delete
contact_count = models.PositiveIntegerField(default=0)
```

### 7. Encryption

Sensitive fields are encrypted at rest:
- OAuth tokens (access_token, refresh_token)
- API keys

Use `django-fernet-fields` or similar:
```python
from fernet_fields import EncryptedTextField
access_token = EncryptedTextField()
```

---

## Django App Structure

```
project/
├── config/                     # Project configuration
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   └── wsgi.py
│
├── apps/
│   ├── common/                 # Shared utilities
│   │   ├── models.py           # Base models, mixins
│   │   ├── fields.py           # Custom fields
│   │   ├── validators.py       # Shared validators
│   │   └── utils.py            # Helpers
│   │
│   ├── accounts/               # User management
│   │   ├── models.py           # User, ZoomConnection, UserSession
│   │   ├── managers.py         # Custom managers
│   │   ├── tokens.py           # Token generation
│   │   └── services.py         # Business logic
│   │
│   ├── events/                 # Event management
│   │   ├── models.py           # Event, EventCustomField, etc.
│   │   ├── state_machine.py    # Status transitions
│   │   └── services.py         # Business logic
│   │
│   ├── registrations/          # Registration & attendance
│   │   ├── models.py           # Registration, AttendanceRecord
│   │   ├── matching.py         # Attendance matching logic
│   │   └── services.py         # Business logic
│   │
│   ├── certificates/           # Certificate management
│   │   ├── models.py           # Certificate, CertificateTemplate
│   │   ├── generator.py        # PDF generation
│   │   └── services.py         # Business logic
│   │
│   ├── contacts/               # Contact management
│   │   ├── models.py           # ContactList, Contact, Tag
│   │   └── services.py         # Import/export logic
│   │
│   ├── integrations/           # External integrations
│   │   ├── models.py           # ZoomWebhookLog, EmailLog
│   │   ├── zoom/               # Zoom-specific code
│   │   │   ├── client.py       # API client
│   │   │   ├── webhooks.py     # Webhook handlers
│   │   │   └── attendance.py   # Attendance sync
│   │   └── email/              # Email service
│   │       ├── client.py       # Email provider client
│   │       └── templates.py    # Email template handling
│   │
│   ├── billing/                # Subscription & payments
│   │   ├── models.py           # Subscription, Invoice
│   │   └── services.py         # Stripe integration
│   │
│   └── learning/               # LMS features (optional)
│       ├── models.py           # Module, Content, Assignment, Submission
│       ├── progress.py         # Progress tracking logic
│       └── services.py         # Assignment review workflow
│
└── manage.py
```

---

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                     │
│                              ┌──────────────────┐                                   │
│                              │   Subscription   │                                   │
│                              └────────┬─────────┘                                   │
│                                       │ 1                                           │
│                                       │                                             │
│  ┌──────────────┐            ┌────────┴─────────┐          ┌──────────────────┐    │
│  │ UserSession  │ *        1 │       User       │ 1      * │  ContactList     │    │
│  └──────────────┴────────────┤                  ├──────────┴────────┬─────────┘    │
│                              │   (Attendee /    │                   │              │
│                              │    Organizer)    │                   │ 1            │
│  ┌──────────────┐            └──┬─────┬─────┬───┘                   ▼ *            │
│  │ ZoomConnect  │ 1          1  │     │     │              ┌──────────────────┐    │
│  └──────────────┴───────────────┘     │     │              │     Contact      │    │
│                                       │     │              └────────┬─────────┘    │
│                                       │     │                       │ *            │
│                    ┌──────────────────┘     └──────────┐            ▼ *            │
│                    │ 1                              1  │    ┌──────────────────┐    │
│                    ▼ *                                 ▼ *  │       Tag        │    │
│           ┌────────────────┐                  ┌────────────┐└──────────────────┘    │
│           │     Event      │                  │  Template  │                        │
│           └───┬──┬──┬──┬───┘                  │ (Certificate)                       │
│               │  │  │  │                      └──────┬─────┘                        │
│    ┌──────────┘  │  │  └────────────┐               │                              │
│    │             │  │               │               │ 1                            │
│    ▼ *           │  │               ▼ *             ▼ *                            │
│ ┌──────────┐     │  │         ┌───────────┐  ┌─────────────┐                       │
│ │Invitation│     │  │         │EventSessn │  │ Certificate │                       │
│ └──────────┘     │  │         └─────┬─────┘  └──────┬──────┘                       │
│                  │  │               │ 1             │                              │
│    ┌─────────────┘  └───────┐      ▼ *             │                              │
│    │                        │ ┌───────────┐        │                              │
│    ▼ *                      │ │ Attend.   │        │                              │
│ ┌──────────────┐            │ │  Record   │        │                              │
│ │ Registration ├────────────┼─┴───────────┘        │                              │
│ └──────┬───────┘            │       ▲              │                              │
│        │ 1                  │       │              │                              │
│        ▼ *                  │       │              │                              │
│ ┌──────────────┐            │ ┌─────┴──────┐       │                              │
│ │  Session     │◄───────────┼─┤   Zoom     │       │                              │
│ │  Attendance  │            │ │  Webhook   │◄──────┘                              │
│ └──────────────┘            │ └────────────┘                                      │
│                             │                                                     │
│                             │ ┌────────────┐                                      │
│                             └─┤  EmailLog  │                                      │
│                               └────────────┘                                      │
│                                                                                   │
└───────────────────────────────────────────────────────────────────────────────────┘
```

### Multi-Session Event Structure

```
Event (Course/Series)
├── EventSession 1 ──────┐
│   └── Zoom Meeting     │
├── EventSession 2 ──────┼──── AttendanceRecord ──┬── Registration
│   └── Zoom Meeting     │                        │
├── EventSession 3 ──────┤                        ├── SessionAttendance
│   └── Zoom Meeting     │                        │
└── EventSession 4 ──────┘                        └── Certificate
    └── Zoom Meeting
```

---

## Entity Summary

### Core Entities

| Entity | App | Purpose | Soft Delete |
|--------|-----|---------|-------------|
| User | accounts | Attendee/organizer accounts | Yes |
| ZoomConnection | accounts | Zoom OAuth tokens | No (cascade) |
| UserSession | accounts | Active login sessions | No |
| CPDRequirement | accounts | User CPD tracking requirements | No (cascade) |
| Event | events | Virtual events (single or multi-session) | Yes |
| EventSession | events | Individual session within an event | No (cascade) |
| EventCustomField | events | Custom registration fields | No (cascade) |
| EventStatusHistory | events | Event status audit trail | No |
| EventInvitation | events | Tracks invites sent | No |
| EventReminder | events | Scheduled reminders | No |
| Registration | registrations | Event registrations | Yes |
| SessionAttendance | registrations | Per-session attendance summary | No (cascade) |
| AttendanceRecord | registrations | Zoom attendance data | No (cascade) |
| CustomFieldResponse | registrations | Registration field values | No (cascade) |
| Certificate | certificates | Issued certificates | Yes |
| CertificateTemplate | certificates | Certificate designs | Yes |
| CertificateStatusHistory | certificates | Certificate audit trail | No |
| ContactList | contacts | Contact lists | No |
| Contact | contacts | Individual contacts | No |
| Tag | contacts | Contact categorization | No |
| ZoomWebhookLog | integrations | Zoom webhook events | No |
| EmailLog | integrations | Sent email tracking | No |
| ZoomRecording | integrations | Zoom cloud recordings | No (cascade) |
| ZoomRecordingFile | integrations | Recording files (video, audio, chat) | No (cascade) |
| RecordingView | integrations | Recording view tracking | No |
| Subscription | billing | User subscriptions | No |
| Invoice | billing | Payment records | No |
| EventModule | learning | Content modules/units | No (cascade) |
| ModuleContent | learning | Individual content items | No (cascade) |
| Assignment | learning | Assignments for review | No (cascade) |
| AssignmentSubmission | learning | Attendee submissions | No (cascade) |
| SubmissionReview | learning | Review audit trail | No |
| ContentProgress | learning | Content completion tracking | No |
| ModuleProgress | learning | Module completion tracking | No |

### Relationship Summary

| From | To | Type | On Delete |
|------|----|------|-----------|
| User | Subscription | 1:1 | CASCADE |
| User | ZoomConnection | 1:1 | CASCADE |
| User | UserSession | 1:N | CASCADE |
| User | CPDRequirement | 1:N | CASCADE |
| User | Event | 1:N | PROTECT |
| User | CertificateTemplate | 1:N | PROTECT |
| User | ContactList | 1:N | CASCADE |
| User | Registration | 1:N | SET_NULL |
| Event | EventSession | 1:N | CASCADE |
| Event | Registration | 1:N | CASCADE |
| Event | EventInvitation | 1:N | CASCADE |
| Event | EventCustomField | 1:N | CASCADE |
| Event | CertificateTemplate | N:1 | SET_NULL |
| EventSession | AttendanceRecord | 1:N | CASCADE |
| EventSession | SessionAttendance | 1:N | CASCADE |
| Registration | Certificate | 1:1 | PROTECT |
| Registration | AttendanceRecord | 1:N | CASCADE |
| Registration | SessionAttendance | 1:N | CASCADE |
| Registration | CustomFieldResponse | 1:N | CASCADE |
| Certificate | CertificateTemplate | N:1 | PROTECT |
| ContactList | Contact | 1:N | CASCADE |
| Contact | Tag | N:N | — |
| Event | ZoomRecording | 1:N | CASCADE |
| ZoomRecording | ZoomRecordingFile | 1:N | CASCADE |
| ZoomRecording | RecordingView | 1:N | CASCADE |
| Registration | RecordingView | 1:N | CASCADE |
| Event | EventModule | 1:N | CASCADE |
| EventModule | ModuleContent | 1:N | CASCADE |
| EventModule | Assignment | 1:N | CASCADE |
| Assignment | AssignmentSubmission | 1:N | CASCADE |
| Registration | AssignmentSubmission | 1:N | CASCADE |
| Registration | ContentProgress | 1:N | CASCADE |
| Registration | ModuleProgress | 1:N | CASCADE |
| Contact | User | N:1 | SET_NULL |

---

## State Machines

### Event Status

```
                        ┌─────────────────────────────────────────┐
                        │                                         │
                        ▼                                         │
┌────────┐  publish  ┌───────────┐  event starts  ┌──────┐       │
│ DRAFT  ├──────────▶│ PUBLISHED ├───────────────▶│ LIVE │       │
└────┬───┘           └─────┬─────┘                └──┬───┘       │
     │                     │                         │           │
     │ delete              │ cancel                  │ ends      │
     ▼                     ▼                         ▼           │
  [deleted]          ┌───────────┐             ┌───────────┐     │
                     │ CANCELLED │             │ COMPLETED │     │
                     └───────────┘             └─────┬─────┘     │
                                                     │           │
                                                     │ close     │
                                                     ▼           │
                                               ┌──────────┐      │
                                               │  CLOSED  │      │
                                               └──────────┘      │
                                                     │           │
                                                     │ reopen    │
                                                     └───────────┘
```

**Valid Transitions:**

| From | To | Trigger | Conditions |
|------|----|---------|------------|
| DRAFT | PUBLISHED | publish() | Required fields set, Zoom meeting created (if enabled) |
| DRAFT | [deleted] | delete() | No registrations |
| PUBLISHED | LIVE | auto/manual | Current time ≥ starts_at |
| PUBLISHED | CANCELLED | cancel() | Any time before event ends |
| LIVE | COMPLETED | auto/manual | Current time ≥ ends_at |
| LIVE | CANCELLED | cancel() | Emergency cancellation |
| COMPLETED | CLOSED | close() | All certificates issued or declined |
| CLOSED | COMPLETED | reopen() | Need to issue more certificates |

**Invalid Transitions:**
- CANCELLED → any (terminal state)
- COMPLETED → DRAFT (can't un-complete)
- CLOSED → DRAFT (can't un-close)

### Certificate Status

```
┌─────────┐  issue  ┌────────┐
│ [none]  ├────────▶│ ACTIVE │
└─────────┘         └───┬────┘
                        │
                        │ revoke
                        ▼
                   ┌─────────┐
                   │ REVOKED │
                   └─────────┘
```

**Valid Transitions:**

| From | To | Trigger | Conditions |
|------|----|---------|------------|
| [none] | ACTIVE | issue() | Registration exists, eligible, template set |
| ACTIVE | REVOKED | revoke() | Reason provided |

**Notes:**
- Revoked certificates cannot be reactivated (issue new certificate instead)
- Certificate data is immutable after issuance

### Registration Status

```
                     ┌────────────┐
          register   │            │  cancel
┌───────┬───────────▶│ CONFIRMED  ├──────────┐
│       │            │            │          │
│       │            └─────┬──────┘          │
│       │                  │                 ▼
│       │                  │           ┌───────────┐
│       │  promote         │           │ CANCELLED │
│       │     ┌────────────┘           └───────────┘
│       │     │
│       │     │  (if waitlist enabled and event full)
│       │     │
│       ▼     │
│  ┌──────────┴─┐
│  │ WAITLISTED │
│  └────────────┘
│
└──── (if event full and waitlist enabled)
```

### Assignment Submission Status

```
                                    ┌────────────────┐
            save draft              │                │
┌────────┬─────────────────────────▶│     DRAFT      │
│        │                          │                │
│        │                          └───────┬────────┘
│        │                                  │
│        │                                  │ submit
│        │                                  ▼
│        │                          ┌────────────────┐
│        │                          │   SUBMITTED    │
│        │                          └───────┬────────┘
│        │                                  │
│        │                                  │ start review
│        │                                  ▼
│        │                          ┌────────────────┐
│        │              ┌───────────│  UNDER_REVIEW  │───────────┐
│        │              │           └────────────────┘           │
│        │              │                                        │
│        │    request   │                                        │ complete
│        │    revision  │                                        │ review
│        │              ▼                                        ▼
│        │      ┌───────────────────┐                   ┌────────────────┐
│        └──────│REVISION_REQUESTED │                   │    REVIEWED    │
│               └───────────────────┘                   └───────┬────────┘
│                       │                                       │
│                       │ resubmit                              │
│                       └──────────────────────┐               │
│                                              │               │
│                                              ▼               ▼
│                                      ┌─────────────┐  ┌─────────────┐
│                                      │  APPROVED   │  │  REJECTED   │
│                                      └─────────────┘  └─────────────┘
```

---

## Cross-Cutting Concerns

### Cascading Behaviors

When entities are deleted (soft or hard), related entities are affected:

| Deleted Entity | Cascade Behavior |
|----------------|------------------|
| User (soft) | Events: PROTECTED (block deletion) |
| | Registrations: user FK set to NULL |
| | ContactLists: CASCADE (deleted) |
| | ZoomConnection: CASCADE |
| | Sessions: CASCADE |
| Event (soft) | Registrations: remain (for certificate access) |
| | Invitations: remain (historical) |
| | AttendanceRecords: remain |
| | Certificates: remain accessible |
| Registration (soft) | Certificate: PROTECTED (block deletion) |
| | AttendanceRecords: remain |
| | CustomFieldResponses: CASCADE |
| CertificateTemplate (soft) | Certificates: PROTECTED |
| | Events (default_template): SET_NULL |

### Audit Trail

Entities with full audit history:
- Event → EventStatusHistory
- Certificate → CertificateStatusHistory

All changes include:
- `changed_by` (User FK)
- `changed_at` (timestamp)
- `from_value` / `to_value`
- `reason` (optional note)

### Data Retention

| Entity | Retention Policy |
|--------|------------------|
| ZoomWebhookLog | 90 days (then hard delete) |
| EmailLog | 1 year (then hard delete) |
| UserSession | 30 days inactive (then hard delete) |
| AttendanceRecord | Indefinite (tied to certificates) |
| Soft-deleted entities | Indefinite (GDPR: anonymize on request) |

### GDPR Compliance

On user deletion request:
1. Soft delete user record
2. Anonymize PII fields:
   - `email` → `deleted-{uuid}@anonymized.local`
   - `full_name` → `Deleted User`
   - `professional_title`, `credentials`, `bio` → empty
3. Keep: certificates (historical record), attendance (anonymized)
4. Delete: sessions, password reset tokens

---

## Migration Strategy

### Initial Migration Order

```
1. common              # No dependencies
2. accounts            # User model
3. billing             # Depends on accounts
4. certificates        # CertificateTemplate (depends on accounts)
5. contacts            # Depends on accounts
6. events              # Depends on accounts, certificates
7. registrations       # Depends on accounts, events
8. learning            # Depends on events, registrations
9. certificates (2)    # Certificate model (depends on registrations)
10. integrations       # Depends on events
```

### Migration Best Practices

1. **Always create reverse migrations**
2. **Use RunPython for data migrations** (separate from schema)
3. **Test migrations on production data copy**
4. **Keep migrations atomic** (one logical change per migration)

### Data Migrations Needed

| Migration | Purpose |
|-----------|---------|
| Canonicalize emails | Lowercase all existing emails |
| Generate UUIDs | Backfill UUID for any imported records |
| Generate slugs | Auto-generate from titles |
| Generate verification codes | Create codes for existing certificates |

---

## Phase 2: Organizations

### New Entities

```python
# organizations/models.py

class Organization(SoftDeleteModel):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    logo_url = models.URLField(blank=True)
    primary_color = models.CharField(max_length=7, blank=True)
    
class OrganizationMembership(BaseModel):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20)  # admin, manager, member
    
    class Meta:
        unique_together = [['organization', 'user']]
```

### Modified Entities

Nullable org FKs added to:
- Event: `organization = FK(Organization, null=True)`
- CertificateTemplate: `organization = FK(Organization, null=True)`
- ContactList: `organization = FK(Organization, null=True)`

### Query Pattern Changes

```python
# Phase 1: User's templates
templates = CertificateTemplate.objects.filter(owner=user)

# Phase 2: User's templates + org templates
templates = CertificateTemplate.objects.filter(
    Q(owner=user) | Q(organization__memberships__user=user)
).distinct()
```

### Migration Path

1. Add `organizations` app with models
2. Add nullable FK fields to existing models
3. Existing data: `organization=None`
4. Org invitation flow populates FKs
5. Update all queries to include org context

---

## Document Index

| Document | Contents |
|----------|----------|
| [common.md](./common.md) | Base models, mixins, custom fields, validators |
| [accounts.md](./accounts.md) | User, ZoomConnection, UserSession |
| [events.md](./events.md) | Event, EventCustomField, EventInvitation, EventReminder, EventStatusHistory |
| [registrations.md](./registrations.md) | Registration, AttendanceRecord, CustomFieldResponse, matching algorithm |
| [certificates.md](./certificates.md) | Certificate, CertificateTemplate, CertificateStatusHistory |
| [contacts.md](./contacts.md) | ContactList, Contact, Tag |
| [integrations.md](./integrations.md) | ZoomWebhookLog, EmailLog |
| [billing.md](./billing.md) | Subscription, Invoice, PaymentMethod |
| [learning.md](./learning.md) | EventModule, ModuleContent, Assignment, AssignmentSubmission, Progress tracking |
| [multi_session_events.md](./multi_session_events.md) | EventSession, SessionAttendance, multi-session support |

---

## Appendix: Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Models | PascalCase, singular | `CertificateTemplate` |
| Tables | snake_case, plural | `certificate_templates` |
| Fields | snake_case | `created_at`, `zoom_meeting_id` |
| ForeignKey | singular, no `_id` suffix | `owner`, `event` |
| Related name | plural | `events`, `registrations` |
| Boolean fields | `is_*`, `has_*`, `can_*` | `is_active`, `has_password` |
| Datetime fields | `*_at` | `created_at`, `published_at` |
| Choice fields | Use TextChoices | `Status.DRAFT` |
