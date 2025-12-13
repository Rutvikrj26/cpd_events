# Architectural Review: Platform Completeness & Logical Flow Analysis

## Executive Summary

This document provides a comprehensive review comparing the **Platform Screens Architecture**, **User Workflows**, and **Data Models** to identify gaps, inconsistencies, and missing elements. Issues are categorized by severity and type.

**Review Scope:**
- Platform Screens Architecture v2 (1,276 lines)
- Platform User Workflows
- Data Models (10 documents, 355KB)

---

## Issue Categories

| Severity | Description |
|----------|-------------|
| 🔴 **Critical** | Blocking issues - screens reference missing data models or vice versa |
| 🟠 **High** | Significant gaps that will cause implementation confusion |
| 🟡 **Medium** | Missing features or inconsistencies that need resolution |
| 🟢 **Low** | Nice-to-have improvements or documentation clarifications |

---

## 🔴 Critical Issues

### C1. Missing Screens for LMS/Learning Features

**Problem:** Data models include comprehensive LMS features (learning.md - 51KB), but Platform Screens has **zero screens** for:

| Missing Screen | Data Model Support |
|----------------|-------------------|
| Module list/management | EventModule ✓ |
| Content viewer | ModuleContent ✓ |
| Content upload/editor | ModuleContent ✓ |
| Assignment list (organizer) | Assignment ✓ |
| Assignment detail/submission | AssignmentSubmission ✓ |
| Assignment grading interface | SubmissionReview ✓ |
| Attendee learning progress | ContentProgress, ModuleProgress ✓ |
| Module drip settings | release_type, release_at ✓ |

**Impact:** Development team has no UI specification for ~30% of data model features.

**Resolution Required:**
1. Add "Learning" or "Modules" tab to Event Detail (organizer)
2. Add Module/Content management screens
3. Add Assignment creation and grading screens
4. Add Attendee-side learning dashboard with progress

---

### C2. Missing Screens for Recording Playback

**Problem:** Data models include ZoomRecording, ZoomRecordingFile, RecordingView, but screens don't show:

| Missing Screen | Purpose |
|----------------|---------|
| Recording list (event detail tab) | Organizer manages recordings |
| Recording settings | Access level, publish/unpublish |
| Recording viewer (attendee) | Watch recordings |
| Recording analytics | View counts, completion |

**Impact:** Zoom recording feature is fully modeled but has no UI path.

**Resolution Required:**
1. Add "Recordings" tab to Event Detail (organizer)
2. Add Recording access screen for attendees (possibly under "Past Events" or event detail)
3. Define recording player component

---

### C3. Missing Screens for Multi-Session Events

**Problem:** Data models include EventSession, SessionAttendance (multi_session_events.md - 37KB), but screens only show single-event paradigm.

| Missing Screen | Purpose |
|----------------|---------|
| Multi-session event creation | Add multiple sessions with dates/times |
| Session list within event | Manage individual sessions |
| Per-session attendance | Track attendance per session |
| Aggregate attendance view | Overall course completion |

**Impact:** Course/series events cannot be created through UI.

**Resolution Required:**
1. Add session management to Event creation
2. Add Sessions tab to Event Detail
3. Update Attendance tab for multi-session aggregation

---

### C4. Waitlist Management UI Missing

**Problem:** Data models support waitlist (Registration.status = WAITLISTED, waitlist_position, waitlist_enabled on Event), but screens only mention "Join Waitlist" button without:

| Missing Element | Purpose |
|-----------------|---------|
| Waitlist tab/section in Registrations | View waitlisted attendees |
| Waitlist position display | Attendee sees their position |
| Manual promotion action | Organizer promotes from waitlist |
| Auto-promotion settings | Configure automatic promotion |

**Resolution Required:**
1. Add waitlist view to Registrations tab
2. Add attendee-facing waitlist position display
3. Add promotion actions (manual and automatic settings)

---

## 🟠 High Priority Issues

### H1. CPD Tracking Dashboard Incomplete

**Screens Specification (line 407-419):**
```
CPD Tracking URL: /cpd
- Period Selector
- Summary Cards per CPD type
- Progress Bars (if annual requirements set)
- Export CPD Report
```

**Data Model Gap:**
- No model for **CPD Requirements** (annual targets by profession)
- No model for **CPD Period** configuration
- User model has no fields for profession/licensing body

**Resolution Required:**
1. Add `UserCPDRequirement` model or extend User profile:
   ```python
   class UserCPDRequirement(BaseModel):
       user = FK(User)
       cpd_type = CharField()  # CME, CLE, CPE
       annual_requirement = DecimalField()
       period_start_month = IntegerField()  # 1-12
   ```
2. Or document that progress bars are Phase 2

---

### H2. Event Type/Category Not in Data Model

**Screens Specification (line 474):**
```
Event Type: Dropdown | Required | Webinar, Workshop, Course, Other
```

**Data Model Gap:**
- Event model has no `event_type` or `category` field

**Resolution Required:**
Add to Event model:
```python
class EventType(models.TextChoices):
    WEBINAR = 'webinar', 'Webinar'
    WORKSHOP = 'workshop', 'Workshop'
    COURSE = 'course', 'Course'
    CONFERENCE = 'conference', 'Conference'
    OTHER = 'other', 'Other'

event_type = models.CharField(max_length=20, choices=EventType.choices)
```

---

### H3. Public Event Discovery Missing

**Workflow Gap:**
- Attendee workflow includes "Browse Events"
- Screens show "Browse Events" CTA in empty states
- No actual event discovery/search screen defined

**Data Model Support:**
- Event.visibility field exists (PUBLIC, UNLISTED, PRIVATE)
- No Event.is_featured or discovery-related fields

**Resolution Required:**
1. Add Public Events Browse screen specification:
   - URL: `/events/browse` or `/discover`
   - Filters: Date, CPD type, Organizer
   - Search functionality
2. Add to Event model:
   ```python
   is_featured = models.BooleanField(default=False)
   category = models.CharField(...)  # For filtering
   ```

---

### H4. Organizer Public Profile Missing

**Screens mention (line 119):**
```
Organizer: Name, profile link (if public)
```

**Data Model Gap:**
- User has `is_public_profile` concept but no dedicated organizer profile fields
- No OrganizerProfile model for:
  - Logo
  - Bio/description
  - Website
  - Social links
  - Event listing

**Resolution Required:**
1. Extend User model or create OrganizerProfile:
   ```python
   organizer_logo_url = models.URLField(blank=True)
   organizer_bio = models.TextField(blank=True, max_length=2000)
   organizer_website = models.URLField(blank=True)
   ```
2. Add Organizer Public Profile screen spec

---

### H5. Template Versioning Not Reflected in UI

**Data Model (certificates.md):**
- CertificateTemplate has versioning system
- `version`, `original_template`, `is_latest_version`, `create_new_version()`

**Screens Gap:**
- Template Editor shows no version management
- No way to view template history
- No indication when editing creates new version

**Resolution Required:**
Add to Template Editor:
- Version indicator: "Version 3 (current)"
- "View Version History" action
- Warning when editing template in use: "This will create a new version"

---

### H6. Contact Professional Fields Missing from Data Model

**Screens - Contact List CSV Import (line 755):**
```
Expected columns: email (required), name (optional)
```

**Data Model (contacts.md):**
```python
full_name = CharField()
professional_title = CharField()
organization_name = CharField()
phone = CharField()
```

**Inconsistency:**
- Screens underspecify CSV import columns
- Data model supports rich contact data

**Resolution Required:**
Update screen spec for CSV import to include:
- email (required)
- full_name / name
- professional_title / title
- organization_name / organization / company
- phone
- tags (comma-separated)

---

### H7. Email Template Customization Missing

**Screens - Email Templates (line 1042-1057):**
Lists email types but no customization UI.

**Data Model Gap:**
- No EmailTemplate model for organizer customization
- EmailLog tracks sends but not templates

**Question:** Can organizers customize email content?

**Resolution Required:**
Either:
1. Add EmailTemplate model and management screens
2. Or document that emails are system-controlled (Phase 2 for customization)

---

### H8. Notification Preferences vs. EventReminder Mismatch

**Screens - Notification Preferences (line 831-844):**
```
Event reminders: 24hr before, 1hr before (toggles)
```

**Data Model (EventReminder):**
- Supports flexible reminder scheduling
- `reminder_type`, `scheduled_for`, `send_hours_before`
- Implies organizer controls reminders per event

**Inconsistency:**
- Screen shows user-controlled global preferences
- Data model shows organizer-controlled per-event reminders

**Resolution Required:**
Clarify:
1. Are reminders opt-in by attendee (notification preferences)?
2. Or controlled by organizer per event?
3. Or both (organizer sets, attendee can disable)?

Update screens and/or data model to match chosen approach.

---

## 🟡 Medium Priority Issues

### M1. Certificate Privacy Toggle Location

**Screens (line 403):**
```
Privacy Setting: Toggle "Allow public verification" (if configurable per certificate)
```

**Data Model (registrations.md):**
```python
# On Registration model
allow_public_verification = models.BooleanField(default=True)
```

**Inconsistency:**
- Screen shows toggle on Certificate Detail (attendee view)
- Data model has field on Registration, not Certificate

**Resolution Required:**
Either:
1. Move field to Certificate model: `allow_public_verification`
2. Or clarify screen shows "Your default for future certificates" and links to registration

---

### M2. Missing "Duplicate Event" Data Support

**Screens (line 566):**
```
More Menu: Duplicate, Share, Cancel Event
```

**Data Model Gap:**
- No `duplicate()` method documented on Event
- No `duplicated_from` FK for tracking copies

**Resolution Required:**
Add to Event model:
```python
duplicated_from = models.ForeignKey(
    'self', null=True, blank=True,
    on_delete=models.SET_NULL,
    related_name='duplicates'
)

def duplicate(self, new_title=None, new_date=None):
    """Create a copy of this event as a draft."""
    pass
```

---

### M3. Reports Screen Lacks Data Model Support

**Screens - Reports (line 761-771):**
```
Summary Cards: Events held, Total attendees, Certificates issued, Avg attendance rate
Charts: Attendance over time, CPD credits by type
Export: CSV, PDF report
```

**Data Model Gap:**
- No pre-aggregated stats tables
- No ReportSnapshot or similar for performance

**Consideration:**
For MVP, queries can compute on-demand. For scale:
```python
class OrganizerStats(BaseModel):
    """Daily/weekly aggregated statistics."""
    user = FK(User)
    period_date = DateField()
    period_type = CharField()  # 'daily', 'weekly', 'monthly'
    events_count = IntegerField()
    registrations_count = IntegerField()
    certificates_count = IntegerField()
    # ...
```

---

### M4. Live Event Monitor Data Flow Undefined

**Screens (line 669-681):**
```
Live Event Monitor: Real-time join/leave feed, currently in meeting counter
```

**Data Model Gap:**
- AttendanceRecord tracks join/leave times
- No real-time streaming mechanism defined

**Resolution Required:**
Document technical approach:
- WebSocket connection for live updates?
- Polling interval?
- Redis pub/sub for attendance events?

---

### M5. Two-Factor Authentication Mentioned but Not Modeled

**Screens (line 811):**
```
Two-Factor Auth: Setup/manage 2FA (future)
```

**Data Model Gap:**
- No 2FA fields on User model
- No TOTPDevice or BackupCode models

**Resolution Required:**
Either:
1. Remove from screens (clearly Phase 2)
2. Or add placeholder models:
   ```python
   totp_secret = EncryptedCharField(blank=True)
   totp_enabled = BooleanField(default=False)
   backup_codes = JSONField(default=list)
   ```

---

### M6. Account Downgrade Logic Missing

**Screens (line 856):**
```
Downgrade: (Organizers) Revert to attendee
```

**Data Model/Business Logic Gap:**
- What happens to organizer's events?
- What happens to issued certificates?
- What happens to subscription?

**Resolution Required:**
Document downgrade rules:
1. Existing events remain accessible (read-only)?
2. Or must transfer ownership?
3. Or must delete/cancel all events?
4. Subscription cancelled with downgrade?

---

### M7. Accreditation Notes Not in Certificate Data

**Screens (line 516):**
```
Accreditation Note: Text | No | e.g., "Accredited by XYZ Board"
```

**Data Model:**
- Event has no `accreditation_note` field
- Certificate.certificate_data could include it, but not documented

**Resolution Required:**
Add to Event model:
```python
accreditation_body = models.CharField(max_length=200, blank=True)
accreditation_note = models.TextField(blank=True, max_length=500)
```

---

### M8. Custom Field Builder Not Specified

**Screens (line 508):**
```
Custom Fields: Builder | No | Add custom registration questions
```

**Data Model:**
- EventCustomField model exists
- Supports TEXT, TEXTAREA, SELECT, CHECKBOX, DATE, NUMBER, FILE

**Screen Gap:**
- No detailed spec for Custom Field Builder UI
- How to add options for SELECT type?
- Validation rules UI?

**Resolution Required:**
Add Custom Field Builder modal specification:
- Field type selector
- Options list for SELECT
- Required toggle
- Placeholder text
- Order management (drag to reorder)

---

### M9. In-Meeting Message Feature Referenced

**Screens (line 679):**
```
Quick Actions: Send in-meeting message (future), end tracking
```

**Data Model Gap:**
- No model for in-meeting messages
- Zoom API integration not documented

**Resolution Required:**
Either:
1. Remove from screens (clearly Phase 2)
2. Or document Zoom chat integration approach

---

### M10. Export Data Feature Needs Spec

**Screens (line 854):**
```
Export Data: "Download all my data" — GDPR compliance
```

**Data Model Gap:**
- No export job tracking model
- No specification of what's included

**Resolution Required:**
Document export contents:
- User profile
- All registrations
- All certificates (PDFs?)
- All events created (if organizer)
- Attendance records
- Format: ZIP with JSON + PDFs

---

## 🟢 Low Priority Issues

### L1. Calendar View Not in Data Model

**Screens (line 457-460):**
```
Calendar View: Monthly calendar with event dots
```

No data model issue - purely UI feature. Low priority to spec.

---

### L2. Profile Photo Storage Not Specified

**Screens (line 795):**
```
Profile Photo: Upload | Crop tool
```

**Data Model:**
- User.profile_photo_url exists
- Storage backend (GCS, S3) not specified

Low priority - implementation detail.

---

### L3. Drag-Drop Future Feature

**Screens (line 460):**
```
Drag to create (future)
```

Acknowledged as future - no action needed.

---

### L4. Apple Wallet / Google Pay Pass

**Screens (line 1237):**
```
Add to Wallet: Apple Wallet / Google Pay pass (future)
```

Acknowledged as future - no data model needed yet.

---

### L5. Push Notifications Model Missing

**Screens (line 1239):**
```
Push Notifications: Event reminders, certificate issued
```

**Data Model Gap:**
- No device token storage
- No notification preferences for push

Lower priority - likely Phase 2 with mobile apps.

---

## Logical Flow Issues

### F1. Registration → Certificate Flow Gap

**Workflow:**
```
Attendee attends → Attendance tracked → Certificate eligible → Certificate issued
```

**Gap in Screens:**
- Attendee event detail (past) shows "Certificate Status" but no "Request Certificate" action
- What if auto-issue is off and organizer delays?

**Resolution:**
1. Add "Your Certificate" section to attendee's past event view
2. States: "Pending" (eligible, not issued), "Issued" (view/download), "Not Eligible"

---

### F2. Guest → Account Linking Unclear

**Workflow:**
```
Guest registers → Attends → Gets certificate email → Signs up with same email → Certificates linked
```

**Screen Gap:**
- No screen showing "We found certificates for your email" on first login
- No explicit linking confirmation

**Resolution:**
Add to onboarding:
```
We found 3 certificates!
─────────────────────────
These certificates were issued to your email before you signed up.
They've been added to your dashboard.

[View Certificates]
```

---

### F3. Zoom Disconnection Impact Unclear

**Workflow:**
- Organizer connects Zoom → Creates events → Zoom token expires → ?

**Screen Gap (line 825):**
```
Error: "Connection expired" — "Reconnect"
```

**Business Logic Gap:**
- What happens to scheduled events with expired token?
- Can meeting still work?
- Are webhooks affected?

**Resolution:**
Document error handling:
1. Surface warning on dashboard: "Zoom connection expired - X events affected"
2. Events remain but may not sync attendance
3. Reconnect refreshes tokens for future events

---

### F4. Certificate Revocation Flow Incomplete

**Screens (line 1107-1118):**
```
Revoke Certificate Modal with reason
```

**Data Model:**
- Certificate.status = REVOKED
- CertificateStatusHistory tracks change

**Gap:**
- Attendee notification not specified in EmailLog types
- Attendee-facing "revoked certificate" view not specified

**Resolution:**
1. Add `CERTIFICATE_REVOKED` to EmailLog.EmailType
2. Add revoked state to attendee certificate detail:
   ```
   ⚠ This certificate has been revoked
   Reason: [organizer's reason]
   Revoked on: [date]
   ```

---

### F5. Subscription Expiry Handling Missing

**Billing Models:**
- Subscription with status PAST_DUE, CANCELED
- Stripe webhooks for payment failure

**Screen Gap:**
- No specification for degraded experience when subscription lapses
- Dashboard when account is past due?

**Resolution:**
Document degraded states:
1. PAST_DUE: Banner "Payment failed - update payment method"
2. CANCELLED: Read-only access to past events, no new creation
3. Grace period rules?

---

## Data Model Internal Issues

### D1. PaymentMethod Missing from Screens

**Data Model (billing.md):**
- PaymentMethod model with card details, is_default

**Screen Specification (line 887-894):**
- Shows single "Current Method" only
- No multi-card management

**Resolution:**
Either:
1. Remove multi-card support from model (simplify)
2. Or add card management UI to screens

---

### D2. Contact Source Tracking Inconsistent

**Data Model (contacts.md):**
```python
source = models.CharField()  # 'manual', 'csv', 'registration'
added_from_event = models.ForeignKey('events.Event')
```

**Screen Gap:**
- Contact import doesn't set source
- No UI to filter by source

Low priority but should be consistent.

---

### D3. EventInvitation vs Contact Relationship

**Data Models:**
- Contact model exists with engagement tracking
- EventInvitation model exists separately

**Gap:**
- No clear link: does EventInvitation reference Contact?
- Or is it email-only?

**Current Model:**
```python
# EventInvitation
email = LowercaseEmailField()
contact = models.ForeignKey(Contact, null=True)  # Optional
```

**Resolution:**
Clarify in invitation flow:
1. Invite from contact list → EventInvitation.contact = Contact instance
2. Manual email entry → EventInvitation.contact = None

---

## Missing API Endpoints

The data models reference API endpoints in some places but there's no comprehensive API specification. Consider adding:

| Endpoint Group | Priority |
|----------------|----------|
| Auth (login, signup, verify, reset) | High |
| Events CRUD | High |
| Registrations | High |
| Certificates | High |
| Contacts | Medium |
| Recordings | Medium |
| Learning/Modules | Medium |
| Billing/Subscription | Medium |
| Webhooks (Zoom, Stripe) | High |

---

## Summary & Recommendations

### Critical Path Items (Must fix before development)

1. **Add LMS screens** - 30% of data models have no UI spec
2. **Add Recording screens** - Complete feature with no UI
3. **Add Multi-session event screens** - Data model ready, no UI
4. **Add Waitlist management screens** - Partially specified

### High Priority (Fix in current sprint)

5. Add Event Type to data model
6. Add Event Discovery screen
7. Clarify notification preferences vs EventReminder relationship
8. Document CPD requirements approach (Phase 1 or 2)

### Documentation Needed

9. API endpoint specification
10. Real-time updates technical approach (WebSockets/polling)
11. Account downgrade business rules
12. GDPR export specification

### Recommended Next Steps

1. **Conduct screen design session** for LMS, Recordings, Multi-session
2. **Update Event model** with missing fields (event_type, accreditation)
3. **Create API specification document**
4. **Review with stakeholders**: Which features are Phase 1 vs Phase 2?

---

## Appendix: Cross-Reference Matrix

| Feature | Screens | Workflows | Data Model | Status |
|---------|---------|-----------|------------|--------|
| User signup/login | ✅ | ✅ | ✅ | Complete |
| Event creation | ✅ | ✅ | ✅ | Complete |
| Registration | ✅ | ✅ | ✅ | Complete |
| Attendance tracking | ✅ | ✅ | ✅ | Complete |
| Certificate issuance | ✅ | ✅ | ✅ | Complete |
| Certificate verification | ✅ | ✅ | ✅ | Complete |
| Contact management | ✅ | ✅ | ✅ | Complete |
| Template management | ✅ | ✅ | ✅ | Complete |
| Subscription billing | ✅ | ⚠️ | ✅ | Workflow gaps |
| Zoom integration | ✅ | ✅ | ✅ | Complete |
| Waitlist | ⚠️ | ⚠️ | ✅ | Screen gaps |
| Multi-session events | ❌ | ❌ | ✅ | **Missing screens** |
| LMS/Learning | ❌ | ❌ | ✅ | **Missing screens** |
| Recordings | ❌ | ❌ | ✅ | **Missing screens** |
| Event discovery | ❌ | ⚠️ | ⚠️ | **Missing screens** |
| Organizer profile | ❌ | ❌ | ⚠️ | Missing all |
| Reports/Analytics | ⚠️ | ⚠️ | ❌ | Model gaps |
| Email customization | ❌ | ❌ | ❌ | Not planned |
| 2FA | ⚠️ (future) | ❌ | ❌ | Phase 2 |
| Push notifications | ⚠️ (future) | ❌ | ❌ | Phase 2 |

**Legend:**
- ✅ Complete/Specified
- ⚠️ Partial/Gaps
- ❌ Missing
