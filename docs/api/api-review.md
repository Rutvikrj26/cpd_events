# DRF API Specification Review

## Executive Summary

After reviewing the API specification against the data models and platform intent, I've identified **23 issues** across 4 severity levels. The specification provides a solid foundation but has significant gaps in critical platform features.

| Severity | Count | Description |
|----------|-------|-------------|
| 🔴 Critical | 5 | Missing entire API sections for defined models |
| 🟠 High | 8 | Model/serializer field mismatches, missing endpoints |
| 🟡 Medium | 7 | Missing features, inconsistencies |
| 🟢 Low | 3 | Minor improvements, polish |

---

## 🔴 Critical Issues

### C1. Missing Learning API Entirely

**Data Model:** `/data-models/learning.md` (1,712 lines, 51KB)

Defines comprehensive LMS models:
- `EventModule` — content modules with release scheduling
- `ModuleContent` — video, documents, links, text, audio, slides, quiz, recording
- `Assignment` — submissions, rubrics, grading
- `AssignmentSubmission` — student work
- `ModuleProgress` — completion tracking
- `AssignmentGrade` — scores and feedback

**API Spec:** Only mentions "learning.urls" in URL config but no actual Learning API section.

**Impact:** Entire LMS functionality has no API endpoints defined.

**Required Endpoints:**
```
GET/POST   /api/v1/events/{uuid}/modules/
GET/PATCH  /api/v1/events/{uuid}/modules/{uuid}/
POST       /api/v1/events/{uuid}/modules/reorder/
GET/POST   /api/v1/modules/{uuid}/content/
GET/PATCH  /api/v1/modules/{uuid}/content/{uuid}/
GET/POST   /api/v1/events/{uuid}/assignments/
GET/PATCH  /api/v1/events/{uuid}/assignments/{uuid}/
POST       /api/v1/assignments/{uuid}/submissions/
GET/PATCH  /api/v1/submissions/{uuid}/
POST       /api/v1/submissions/{uuid}/grade/
GET        /api/v1/users/me/learning-progress/
GET        /api/v1/registrations/{uuid}/module-progress/
```

---

### C2. Missing Multi-Session Events API

**Data Model:** `/data-models/multi_session_events.md` (1,195 lines, 37KB)

Defines:
- `EventSession` — individual sessions within an event
- `SessionAttendance` — per-session attendance tracking
- Aggregate attendance calculation across sessions

**API Spec:** No mention of EventSession or multi-session handling.

**Impact:** Platform cannot support courses, series, or conferences.

**Required Endpoints:**
```
GET/POST   /api/v1/events/{uuid}/sessions/
GET/PATCH  /api/v1/events/{uuid}/sessions/{uuid}/
POST       /api/v1/events/{uuid}/sessions/{uuid}/start/
POST       /api/v1/events/{uuid}/sessions/{uuid}/complete/
GET        /api/v1/events/{uuid}/aggregate-attendance/
GET        /api/v1/registrations/{uuid}/session-attendance/
```

---

### C3. Missing Recordings API

**Data Model:** `/data-models/integrations.md` defines:
- `ZoomRecording` — recording metadata, status, access control
- `ZoomRecordingFile` — individual files (video, audio, transcript, chat)
- `RecordingAccess` — access control and tracking

**API Spec:** Webhook handler references `recordings.models` but no Recordings API section.

**Impact:** Organizers cannot manage recordings; attendees cannot view them.

**Required Endpoints:**
```
GET        /api/v1/events/{uuid}/recordings/
GET/PATCH  /api/v1/events/{uuid}/recordings/{uuid}/
POST       /api/v1/events/{uuid}/recordings/{uuid}/publish/
POST       /api/v1/events/{uuid}/recordings/{uuid}/unpublish/
GET        /api/v1/recordings/{uuid}/files/
GET        /api/v1/recordings/{uuid}/analytics/
GET        /api/v1/users/me/recordings/
GET        /api/v1/recordings/{uuid}/stream/  (signed URL)
```

---

### C4. Registration Model Field Mismatches

**Data Model:** Registration has these fields:
```python
email = LowercaseEmailField()
full_name = models.CharField()
professional_title = models.CharField()
organization_name = models.CharField()
first_join_at = models.DateTimeField()
last_leave_at = models.DateTimeField()
total_attendance_minutes = models.PositiveIntegerField()
attendance_eligible = models.BooleanField()
attendance_override = models.BooleanField()
attendance_override_by = models.ForeignKey()
attendance_override_reason = models.TextField()
promoted_from_waitlist_at = models.DateTimeField()
```

**API Spec Serializer uses:**
```python
# WRONG field names
guest_email, guest_name  # Should be: email, full_name
join_time, leave_time    # Should be: first_join_at, last_leave_at
attendance_percent       # Model uses: total_attendance_minutes + attendance_eligible
waitlisted_at, promoted_at  # Model uses: promoted_from_waitlist_at
```

**Impact:** Serializers won't work with actual model fields.

---

### C5. Missing Guest Registration to Account Linking

**Data Model:** Registration doc explicitly states:
```
Lifecycle:
    Guest registers → Registration(user=None, email=X)
    Guest creates account → Registration.user = new_user (matched by email)
```

**API Spec:** No endpoint for:
- Linking existing registrations when user creates account
- Finding registrations by email during signup
- Transferring guest registrations to new account

**Required Endpoints:**
```
POST /api/v1/auth/signup/  (should auto-link registrations)
GET  /api/v1/users/me/link-registrations/  (find and link orphaned)
```

---

## 🟠 High Priority Issues

### H1. Certificate Template Versioning Not Exposed

**Data Model:** CertificateTemplate has:
```python
version = models.PositiveIntegerField(default=1)
is_latest_version = models.BooleanField(default=True)
original_template = models.ForeignKey('self')  # Version chain
```

**API Spec:** Has `/versions/` action but update serializer doesn't properly handle version creation logic.

**Fix:** UpdateSerializer.update() should check `instance.certificates.exists()` before creating new version.

---

### H2. Event Serializer Missing Multi-Session Fields

**Data Model:** Event has:
```python
is_multi_session = models.BooleanField(default=False)
completion_type = models.CharField()  # minimum_sessions, percentage, all_required
minimum_sessions_required = models.PositiveIntegerField()
minimum_attendance_percent_total = models.PositiveIntegerField()
required_sessions = models.ManyToManyField('EventSession')
```

**API Spec:** EventDetailSerializer missing all multi-session fields.

---

### H3. Missing Attendance Override Endpoint

**Data Model:** Registration supports manual attendance override:
```python
attendance_override = models.BooleanField()
attendance_override_by = models.ForeignKey()
attendance_override_reason = models.TextField()
```

**API Spec:** AttendanceUpdateSerializer only has `attended` and `attendance_percent`, missing override fields.

**Fix:** Add dedicated override endpoint:
```
POST /api/v1/events/{uuid}/registrations/{uuid}/override-attendance/
{
    "eligible": true,
    "reason": "Technical difficulties during live stream"
}
```

---

### H4. Missing Discount Code Handling

**Data Model:** Registration has:
```python
discount_code_used = models.CharField()  # Referenced but not defined
```

Events should have discount codes, but no DiscountCode model or API exists.

**Required:** Either remove reference or add DiscountCode model + API.

---

### H5. CPDRequirement Serializer Using String Model Reference

**API Spec:**
```python
class Meta:
    model = 'accounts.CPDRequirement'  # WRONG - string reference
```

**Fix:** Should use proper import:
```python
from accounts.models import CPDRequirement
class Meta:
    model = CPDRequirement
```

---

### H6. Missing GDPR Data Export Endpoint

**Platform Requirement:** Users can export their data (GDPR compliance).

**API Spec:** No endpoint for data export.

**Required:**
```
POST /api/v1/users/me/export-data/
GET  /api/v1/users/me/export-data/{request_uuid}/status/
GET  /api/v1/users/me/export-data/{request_uuid}/download/
```

---

### H7. Missing Account Deletion/Anonymization Endpoint

**Data Model:** User.anonymize() method exists.

**API Spec:** No endpoint to trigger it.

**Required:**
```
POST /api/v1/users/me/delete-account/
{
    "password": "confirmation",
    "reason": "optional feedback"
}
```

---

### H8. Webhook Signature Verification Incomplete

**API Spec:** Zoom webhook verification:
```python
message = f"v0:{timestamp}:{request.body.decode()}"
```

**Issue:** Zoom uses different signature format. Should verify against:
```python
message = f"v0:{timestamp}:{json.dumps(request.data, separators=(',', ':'))}"
```

Also missing URL validation challenge response for Zoom webhook registration.

---

## 🟡 Medium Priority Issues

### M1. Missing Event Slug Uniqueness Scope

**Data Model:** Slug is unique per owner:
```python
class Meta:
    constraints = [
        models.UniqueConstraint(fields=['owner', 'slug'], name='unique_owner_slug')
    ]
```

**API Spec:** EventCreateSerializer doesn't handle slug generation or uniqueness validation.

---

### M2. Contact Model Field Mismatch

**Data Model:** Contact uses:
```python
email = LowercaseEmailField()
name = models.CharField()  # Not full_name
title = models.CharField()  # Not professional_title
organization = models.CharField()  # Not organization_name
```

**API Spec:** ContactSerializer uses different field names.

---

### M3. Missing Waitlist Auto-Promotion Setting

**Data Model:** Event should have:
```python
waitlist_auto_promote = models.BooleanField(default=True)
```

**API Spec:** No field in EventCreateSerializer for auto-promotion control.

---

### M4. Invoice Serializer Missing Stripe ID

**Data Model:** Invoice likely has `stripe_invoice_id` for Stripe sync.

**API Spec:** InvoiceSerializer doesn't include it (may be intentional for security, but organizers may need it for support).

---

### M5. Missing Pagination for Nested Resources

**API Spec:** EventReminderViewSet, EventInvitationViewSet don't specify pagination.

**Issue:** Large invitation lists (500+) will timeout without pagination.

**Fix:** Add `pagination_class = StandardPagination` to nested viewsets.

---

### M6. Missing Rate Limiting on Bulk Operations

**API Spec:** Bulk endpoints like:
- `POST /events/{uuid}/invitations/` (up to 500 emails)
- `POST /events/{uuid}/registrations/` (bulk add)
- `PATCH /events/{uuid}/registrations/bulk-attendance/`

Have no throttling. Could be abused.

**Fix:** Add custom throttle class for bulk operations.

---

### M7. Certificate PDF URL Security

**API Spec:** MyCertificateSerializer exposes `pdf_url` directly.

**Issue:** If URL is public cloud storage URL, anyone with URL can download.

**Fix:** Should generate signed URL with expiration, as done in download action.

---

## 🟢 Low Priority Issues

### L1. Inconsistent Serializer Naming

**Pattern inconsistency:**
- `EventListSerializer` / `EventDetailSerializer` ✓
- `RegistrationListSerializer` / `RegistrationDetailSerializer` ✓
- `ContactSerializer` (no List/Detail distinction) ✗
- `CertificateListSerializer` / `CertificateDetailSerializer` ✓

**Fix:** Add `ContactListSerializer` for list views.

---

### L2. Missing OpenAPI Schema Decorators

**API Spec:** Custom actions like `@action` methods lack `@extend_schema` decorators from drf-spectacular.

**Impact:** Auto-generated API docs will have incomplete information.

**Fix:** Add schema decorators:
```python
from drf_spectacular.utils import extend_schema, OpenApiParameter

@extend_schema(
    summary="Publish event",
    responses={200: EventDetailSerializer}
)
@action(detail=True, methods=['post'])
def publish(self, request, uuid=None):
    ...
```

---

### L3. Missing Service Layer References

**API Spec:** References services that don't exist in spec:
- `zoom_service.create_meeting_for_event()`
- `zoom_service.complete_oauth()`
- `certificate_service.issue_bulk()`
- `stripe_service.create_subscription()`
- `storage_service.upload_template()`

**Impact:** Developers won't know service method signatures.

**Suggestion:** Add Services Specification document or inline signatures.

---

## Recommendations Summary

### Immediate Actions (Before Development)

1. **Add Learning API section** — Critical for LMS functionality
2. **Add Multi-Session Events API section** — Critical for courses/conferences
3. **Add Recordings API section** — Critical for post-event value
4. **Fix Registration serializer field names** — Will cause immediate errors
5. **Fix model string references** — Will cause import errors

### Before MVP

6. Add GDPR export/delete endpoints
7. Add attendance override endpoint
8. Fix webhook signature verification
9. Add pagination to nested viewsets
10. Add bulk operation throttling

### Before Production

11. Add OpenAPI schema decorators
12. Create Services specification
13. Add signed URL generation for all file access
14. Validate all field names against models
15. Add integration tests for all endpoints

---

## Cross-Reference Matrix

| Data Model | API Coverage | Status |
|------------|--------------|--------|
| User | ✅ Complete | Good |
| ZoomConnection | ✅ Complete | Good |
| UserSession | ✅ Complete | Good |
| CPDRequirement | ⚠️ Partial | Fix model reference |
| Event | ⚠️ Partial | Missing multi-session fields |
| EventSession | ❌ Missing | Critical gap |
| EventCustomField | ✅ Complete | Good |
| EventReminder | ✅ Complete | Good |
| EventInvitation | ✅ Complete | Good |
| Registration | ⚠️ Partial | Field name mismatches |
| AttendanceRecord | ⚠️ Partial | Missing in serializer |
| Certificate | ✅ Complete | Good |
| CertificateTemplate | ⚠️ Partial | Versioning logic incomplete |
| ContactList | ✅ Complete | Good |
| Contact | ⚠️ Partial | Field name mismatches |
| Subscription | ✅ Complete | Good |
| Invoice | ✅ Complete | Good |
| PaymentMethod | ✅ Complete | Good |
| EventModule | ❌ Missing | Critical gap |
| ModuleContent | ❌ Missing | Critical gap |
| Assignment | ❌ Missing | Critical gap |
| AssignmentSubmission | ❌ Missing | Critical gap |
| ZoomRecording | ❌ Missing | Critical gap |
| ZoomRecordingFile | ❌ Missing | Critical gap |

---

## Conclusion

The API specification provides a **70% complete** foundation. The core authentication, events, registrations, certificates, billing, and contacts APIs are well-structured with proper DRF patterns.

However, **three major platform features** (Learning/LMS, Multi-Session Events, Recordings) have comprehensive data models but **zero API coverage**. These must be added before the specification can guide development.

Additionally, several serializers have **field name mismatches** with the actual models that will cause immediate runtime errors.

**Recommended next step:** Fix critical issues C1-C5 before proceeding with development.
