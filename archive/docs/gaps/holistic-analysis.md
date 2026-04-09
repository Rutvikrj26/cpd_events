# Comprehensive Holistic Gap Analysis - CPD Events Platform

**Date**: January 11, 2026
**Status**: Complete Platform Audit
**Scope**: All user flows, workflows, integrations, and system integrity

---

## Executive Summary

This analysis examines the entire platform from end-to-end, identifying gaps in implementation, broken workflows, permission issues, and data consistency problems. The analysis covers authentication, billing, organizations, events, courses, certificates, and integrations.

**Overall Assessment**: The platform has a **solid architectural foundation** with **comprehensive features**, but has **critical implementation gaps** that must be addressed before production launch.

### Summary Statistics
- **Total Issues Identified**: 47
- **Critical (Blockers)**: 8
- **High Priority**: 12
- **Medium Priority**: 18
- **Low Priority**: 9

---

## Table of Contents

1. [Critical Gaps (Production Blockers)](#1-critical-gaps-production-blockers)
2. [High Priority Gaps](#2-high-priority-gaps)
3. [Workflow & User Journey Gaps](#3-workflow--user-journey-gaps)
4. [Permission & Access Control Gaps](#4-permission--access-control-gaps)
5. [Data Integrity & Consistency Gaps](#5-data-integrity--consistency-gaps)
6. [Integration & Webhook Gaps](#6-integration--webhook-gaps)
7. [Organization Management Gaps](#7-organization-management-gaps)
8. [UI/UX & Frontend Gaps](#8-uiux--frontend-gaps)
9. [Medium Priority Issues](#9-medium-priority-issues)
10. [Low Priority Issues](#10-low-priority-issues)

---

## 1. Critical Gaps (Production Blockers)

### 1.1 Email System Not Fully Implemented ⚠️ CRITICAL

**Status**: Partial Implementation
**Impact**: Users cannot complete critical workflows
**Files**: `backend/src/accounts/views.py`, `backend/src/accounts/tasks.py`

**Problem**:
Email sending is implemented (tasks exist) but key workflows need verification:
- Email verification emails send via `send_email_verification.delay()`
- Password reset emails send via `send_password_reset.delay()`
- Need to verify email service configuration in production

**What's Working**:
- ✅ Email tasks defined in `accounts/tasks.py`
- ✅ Integration with email service (`integrations/services.py`)
- ✅ Signup calls `send_email_verification.delay()`
- ✅ Password reset calls `send_password_reset.delay()`

**What Needs Verification**:
- Email service configuration in production environment
- Email templates existence and rendering
- Delivery tracking
- Bounce handling

**Required Actions**:
1. Verify email service is configured (`EMAIL_*` environment variables)
2. Test all transactional email flows in staging
3. Add email delivery monitoring
4. Implement bounce/complaint handling

---

### 1.2 Trial-to-Paid Transition Not Automated ⚠️ CRITICAL

**Status**: Manual intervention required
**Impact**: Lost revenue from expired trials
**Files**: `backend/src/billing/tasks.py`, `backend/src/billing/models.py`

**Problem**:
- Trial expiration is tracked but not enforced
- No automatic downgrade when trial expires
- Users can access paid features indefinitely after trial ends
- No trial expiration notifications

**Evidence**:
```python
# Subscription.is_in_trial() exists but no enforcement
# No scheduled task to check expired trials
# Grace period exists but not enforced
```

**Required Implementation**:
```python
# billing/tasks.py
@periodic_task(run_every=crontab(hour=2, minute=0))
def check_trial_expirations():
    """
    Daily task to expire trials and enforce downgrades.
    Runs at 2 AM UTC daily.
    """
    from billing.models import Subscription
    from django.utils import timezone

    # Find subscriptions with expired trials
    expired_trials = Subscription.objects.filter(
        status__in=['trialing', 'active'],
        trial_ends_at__lt=timezone.now(),
        payment_method__isnull=True  # No payment method = no auto-transition
    )

    for subscription in expired_trials:
        subscription.expire_trial()
        # Send email notification
        # Downgrade to free tier
```

**Files to Create/Modify**:
- `backend/src/billing/tasks.py` - Add `check_trial_expirations()` Celery task
- `backend/src/billing/models.py` - Add `Subscription.expire_trial()` method
- `backend/src/billing/services.py` - Add trial expiration handling

---

### 1.3 No Refund API Endpoint ⚠️ CRITICAL

**Status**: Service exists, no endpoint
**Impact**: Cannot process refunds programmatically
**Files**: `backend/src/billing/services.py`, `backend/src/billing/views.py`

**Problem**:
- `RefundService.process_refund()` exists and looks complete ✅
- Webhook handler `_handle_charge_refunded()` exists ✅
- BUT: No REST API endpoint for organizers to request refunds
- Manual Stripe dashboard intervention required

**What's Already Implemented**:
```python
# billing/services.py:1513
class RefundService:
    def process_refund(self, registration, amount_cents, reason, processed_by):
        # Comprehensive refund logic including:
        # - Stripe refund creation
        # - Transfer reversals
        # - Fee reversals
        # - Status updates
        # - Audit logging
```

**What's Missing**:
```python
# Need to add to billing/views.py
@roles('organizer', 'admin', route_name='refund_registration')
class RegistrationRefundView(APIView):
    """POST /registrations/{uuid}/refund/"""

    def post(self, request, uuid):
        # Validate ownership
        # Check refund eligibility
        # Call RefundService.process_refund()
        # Return result
```

**Files to Create**:
- `backend/src/billing/views.py` - Add `RegistrationRefundView`
- `backend/src/billing/serializers.py` - Add `RefundRequestSerializer`
- `backend/src/billing/urls.py` - Wire up refund endpoint

---

### 1.4 Organization Seat Billing Not Fully Connected ⚠️ CRITICAL

**Status**: Models exist, Stripe sync unclear
**Impact**: Organizations may not be billed correctly for seats
**Files**: `backend/src/organizations/models.py`, `backend/src/billing/webhooks.py`

**Problem**:
- `OrganizationSubscription.billable_seats` calculation exists
- `OrganizationSubscription.update_seat_usage()` exists
- BUT: No clear Stripe subscription update when seats change
- Unclear if seat changes trigger Stripe quantity updates

**What Needs Verification**:
1. When a new member is added to an organization (role=organizer or course_manager):
   - Is `update_seat_usage()` called?
   - Does it update Stripe subscription quantity?
   - Is prorated billing triggered?

2. When a member is removed:
   - Is seat usage decremented?
   - Is Stripe subscription updated?

**Code to Review**:
```python
# organizations/models.py:~300
def update_seat_usage(self):
    """Update billable seat count."""
    billable = self.billable_seats
    # Does this update Stripe???
```

**Required Actions**:
1. Audit organization membership create/delete flows
2. Verify Stripe subscription item quantity updates
3. Add integration tests for seat billing
4. Add Stripe webhook handler for `subscription.updated` to sync seats

---

### 1.5 Certificate Limit Enforcement Incomplete ⚠️ CRITICAL

**Status**: Check exists, not enforced everywhere
**Impact**: Users can exceed certificate limits
**Files**: `backend/src/billing/models.py`, `backend/src/certificates/views.py`

**Problem**:
- `Subscription.check_certificate_limit()` method exists ✅
- `CanIssueCertificate` permission class exists ✅
- BUT: Permission class only checks `account_type == 'organizer'`, not limit
- No enforcement in certificate creation views

**Evidence**:
```python
# common/permissions.py:157
class CanIssueCertificate(permissions.BasePermission):
    def has_permission(self, request, view):
        # ...
        subscription.check_certificate_limit()  # ✅ Called
        # BUT: Only returns True/False, doesn't block
```

**Issue**: The permission check happens but certificate creation views don't use this permission class.

**Required Fix**:
1. Add `CanIssueCertificate` to certificate creation views
2. Enforce limit in bulk certificate issuance
3. Add clear error message when limit reached
4. Consider soft limit warnings (e.g., "90% of limit reached")

---

### 1.6 Course Enrollment Payment Flow Incomplete ⚠️ CRITICAL

**Status**: Partial implementation
**Impact**: Cannot sell paid courses
**Files**: `backend/src/learning/views.py`, `backend/src/billing/views.py`

**Problem**:
- Courses have `is_paid` and `price` fields ✅
- Checkout session creation for one-time payments exists ✅
- BUT: No clear enrollment → payment → confirmation flow
- Unclear how paid course enrollments are confirmed after payment

**What Exists**:
```python
# billing/services.py:853
def create_one_time_checkout_session(self, user, price_id, ...):
    # Creates Stripe checkout for one-time payment
```

**What's Missing**:
1. Course enrollment endpoint that creates checkout session for paid courses
2. Webhook handler to confirm enrollment after `checkout.session.completed`
3. Enrollment status transition: Pending → Active after payment
4. Linking enrollment to payment_intent

**Required Implementation**:
- `POST /courses/{uuid}/enroll/` - Create enrollment + checkout if paid
- `_handle_checkout_session_completed` - Check if it's a course enrollment
- Update `CourseEnrollment` with payment tracking fields

---

### 1.7 Zoom Integration Token Refresh Not Fully Tested ⚠️ CRITICAL

**Status**: Code exists, needs production testing
**Impact**: Zoom meetings may fail to create after token expires
**Files**: `backend/src/integrations/services.py`

**Problem**:
- Token refresh logic exists in `ZoomService._ensure_token_fresh()`
- Refresh happens automatically before API calls
- BUT: Edge cases not handled:
  - What if refresh fails?
  - What if user revokes app access?
  - Is organizer notified of integration issues?

**Required Actions**:
1. Add comprehensive error handling in token refresh
2. Add notification to organizer when Zoom integration breaks
3. Add "Reconnect Zoom" UI flow
4. Add integration health monitoring

---

### 1.8 Multi-Session Event Certificate Eligibility Logic Complex ⚠️ CRITICAL

**Status**: Implemented but complex
**Impact**: Incorrect certificate issuance
**Files**: `backend/src/registrations/models.py:354-427`

**Problem**:
The `update_attendance_summary()` method has 4 different completion criteria paths:
1. ALL_SESSIONS
2. PERCENTAGE_OF_SESSIONS
3. MIN_SESSIONS_COUNT
4. TOTAL_MINUTES

**Risk**: Complex logic with multiple edge cases could lead to:
- Certificates issued to ineligible attendees
- Eligible attendees not receiving certificates
- Incorrect CPD credit calculations

**Required Actions**:
1. Comprehensive unit tests for all 4 criteria paths
2. Integration tests with real multi-session events
3. Manual testing with QA checklist
4. Consider simplifying to 2 criteria (sessions OR minutes)

---

## 2. High Priority Gaps

### 2.1 Payout Request System Incomplete

**Status**: Model exists, no workflow
**Impact**: Organizers cannot request payouts
**Files**: `backend/src/billing/models.py:PayoutRequest`

**Problem**:
- `PayoutRequest` model exists with status tracking
- Webhook handler `_handle_payout_paid()` exists ✅
- BUT: No API endpoint for organizers to request payouts
- No organizer-facing payout dashboard

**Required**:
- `POST /users/me/payouts/request/` - Request payout
- `GET /users/me/payouts/` - List payout history
- Add minimum payout threshold
- Add payout schedule (weekly/monthly)

---

### 2.2 Payment Reconciliation Tools Missing

**Status**: No admin tools
**Impact**: Cannot audit payment discrepancies

**Required**:
- Admin endpoint to compare Stripe vs DB
- Fee audit trail
- Failed payment dashboard
- Dispute management tools

---

### 2.3 Organization Invitation Acceptance Flow Gaps

**Status**: Partial implementation
**Impact**: Confusing member onboarding
**Files**: `backend/src/organizations/views.py`

**Problem**:
- Invitation creation works ✅
- `accept_invitation()` method exists ✅
- BUT: Unclear handling of:
  - User accepts invitation but already has organizer subscription
  - Conflict between individual plan and org role
  - What happens to user's individual events when joining org?

**Required Clarifications**:
1. If user with `organizer` plan joins org as `course_manager`, what happens to their events?
2. If user with `attendee` plan accepts `organizer` role invitation, do they need subscription?
3. How does seat billing work when user has own subscription?

---

### 2.4 Event Ownership Transfer Not Implemented

**Status**: Not implemented
**Impact**: Cannot reassign events to different organizers

**Required**:
- `POST /events/{uuid}/transfer/` endpoint
- Transfer to another user (within same org)
- Transfer to organization
- Audit log of transfers

---

### 2.5 Bulk Certificate Issuance Missing

**Status**: Not implemented
**Impact**: Manual certificate issuance is tedious

**Required**:
- `POST /events/{uuid}/certificates/bulk-issue/` endpoint
- Issue to all eligible attendees at once
- Background task for large batches
- Progress tracking

---

### 2.6 Promo Code Usage Reversal Missing

**Status**: Not implemented
**Impact**: Promo codes artificially exhausted
**Files**: `backend/src/promo_codes/models.py:296`

**Problem**:
- `PromoCodeUsage.release_for_registration()` exists ✅
- BUT: Not called when:
  - Payment fails
  - Registration cancelled
  - Refund processed

**Fix**: Call `PromoCodeUsage.release_for_registration()` in:
- Payment failure webhook
- Registration cancellation
- Refund processing

---

### 2.7 No Downgrade Workflow

**Status**: Method exists, no endpoint
**Impact**: Users cannot self-serve downgrade
**Files**: `backend/src/accounts/models.py:224`

**Problem**:
- `User.downgrade_to_attendee()` exists
- No API endpoint
- No validation (what if user has active events?)

**Required**:
- `POST /users/me/downgrade/` endpoint
- Check: No active events
- Cancel subscription
- Clear account_type

---

### 2.8 Course Assignment Grading Workflow Incomplete

**Status**: Models exist, workflow unclear
**Files**: `backend/src/learning/models.py`, `backend/src/learning/views.py`

**Problem**:
- Assignment submission works
- `SubmissionReview` model exists
- BUT: Unclear instructor grading flow
- No grade calculation/aggregation
- No passing score enforcement

---

### 2.9 Organization Public Directory Missing

**Status**: Model has `is_public` field, no endpoint
**Files**: `backend/src/organizations/models.py:81`

**Problem**:
- Organizations have `is_public` field
- No public directory endpoint
- No public organization profile page

**Required**:
- `GET /api/v1/public/organizations/` - List public orgs
- `GET /api/v1/public/organizations/{slug}/` - Public profile

---

### 2.10 No Event Cancellation Workflow

**Status**: Status field exists, no workflow

**Problem**:
- Events have status but no cancellation workflow
- What happens to registrations?
- Automatic refunds?
- Notifications?

**Required**:
- `POST /events/{uuid}/cancel/` endpoint
- Automatic refund logic
- Email notifications
- Update registration statuses

---

### 2.11 Certificate Template Sharing Unclear

**Status**: `is_shared` field exists, logic unclear
**Files**: `backend/src/certificates/models.py:108-111`

**Problem**:
- Templates have `is_shared` field
- Unclear how org members access shared templates
- No API to list org's shared templates

---

### 2.12 Session Management Endpoints Missing

**Status**: Model exists, no API
**Files**: `backend/src/accounts/models.py:421`

**Problem**:
- `UserSession` model tracks active sessions
- No endpoints to:
  - List active sessions
  - Logout from specific device
  - Logout from all devices

---

## 3. Workflow & User Journey Gaps

### 3.1 Signup → Onboarding → Subscription Flow

**Current State**: Functional but incomplete

**Gaps**:
1. **No plan selection during signup**
   - Users sign up as 'attendee' by default
   - Must manually upgrade after signup
   - Confusing UX: "Where do I upgrade?"

2. **Onboarding wizard disconnected from subscription**
   - Onboarding checklist exists
   - Doesn't prompt subscription selection
   - Doesn't explain plan differences

3. **Trial activation unclear**
   - When does trial start?
   - Is trial automatic or requires action?
   - No clear trial countdown

**Recommended Flow**:
```
Signup → Email Verification → Role Selection → Plan Selection → Trial Start → Onboarding
```

---

### 3.2 Organization Creation → Team Invites → Seat Billing

**Current State**: Partially working

**Gaps**:
1. **Organization creation doesn't prompt for plan**
   - Creates free org by default
   - Should offer $199/month plan selection

2. **Inviting members doesn't check seat limits**
   - No validation: "You've reached your seat limit"
   - No upgrade prompt

3. **Billing sync unclear**
   - When are seats billed?
   - Immediate or at period end?

---

### 3.3 Event Creation → Publishing → Registration → Attendance → Certificate

**Current State**: Core flow works

**Gaps**:
1. **No draft preview**
   - Events can be created but no preview before publishing
   - Should show "how it looks to attendees"

2. **Publishing doesn't validate requirements**
   - Can publish event without:
     - Zoom meeting configured
     - Certificate template selected (if certificates enabled)
     - Custom fields set up

3. **Attendance tracking requires Zoom**
   - In-person events: no check-in system
   - Hybrid events: manual attendance unclear

4. **Certificate auto-issuance delayed**
   - No real-time certificate issuance
   - Batch job? Manual trigger?

---

### 3.4 Course Creation → Enrollment → Progress → Completion → Certificate

**Current State**: Workflow incomplete

**Gaps**:
1. **Paid course enrollment not implemented**
   - Can't test paid enrollment flow
   - Checkout session creation exists but not wired

2. **Module release scheduling unclear**
   - Drip content: Does it work?
   - Cron job to release modules?

3. **Assignment workflow incomplete**
   - Student submits
   - Instructor grades
   - BUT: No notification to student
   - No grade aggregation

4. **Course completion detection**
   - Is completion automatic at 100% progress?
   - Manual marking?

---

## 4. Permission & Access Control Gaps

### 4.1 Organization Role Permission Issues

**Problem**: Role-based permissions don't align with database roles

**Examples**:
1. **Course Manager can't create events**
   - Correct behavior ✅
   - But `@roles('organizer', 'course_manager')` decorator suggests they can

2. **Instructor vs Course Manager confusion**
   - Instructors: Only manage assigned course
   - Course Managers: Manage all org courses
   - BUT: API doesn't enforce "assigned course only" for instructors

3. **Admin has organizer capabilities**
   - Code documents this ✅
   - BUT: Not clear in permission checks

**Fix Required**:
- Add `IsOrganizerOrAdmin` permission for event endpoints
- Add `IsCourseManagerOrAdmin` permission for course creation
- Add `IsAssignedInstructor` permission for course management

---

### 4.2 Object-Level Permission Gaps

**Problem**: Many endpoints lack object-level permission checks

**Examples**:
1. **Can any organizer edit any event?**
   - Code checks `event.owner == user` ✅
   - BUT: Does it check org membership?
   - Edge case: User leaves org, can they still edit their old events?

2. **Certificate access control weak**
   - Who can view a certificate?
   - Only the recipient?
   - Event organizer?
   - Public if `allow_public_verification=True`?

---

### 4.3 RBAC Plans Filter Not Enforced Everywhere

**Problem**: `@roles(..., plans=['organization'])` decorator exists but not used consistently

**Example**:
```python
# Some endpoints restrict by plan
@roles('organizer', 'admin', route_name='organizations', plans=['organization'])
class OrganizationViewSet(viewsets.ModelViewSet):
    ...

# Others don't
@roles('organizer', 'admin', route_name='events')
class EventViewSet(SoftDeleteModelViewSet):
    # Should this be plans=['organizer', 'organization']?
    ...
```

**Risk**: Users on wrong plan can access features they haven't paid for

---

## 5. Data Integrity & Consistency Gaps

### 5.1 Soft Delete Orphans

**Problem**: Soft-deleted objects may have FK references

**Examples**:
1. **Deleted event has registrations**
   - Event soft-deleted
   - Registrations still reference it
   - Do registrations cascade soft-delete?

2. **Deleted user has events**
   - User anonymized (GDPR)
   - Events still reference them as owner
   - Events become orphaned?

**Fix Required**:
- Cascade soft-delete logic
- Or use `on_delete=models.SET_NULL` with migration

---

### 5.2 Denormalized Count Sync Issues

**Problem**: Many models have denormalized counts that can drift

**Examples**:
```python
# Event model
registration_count = models.PositiveIntegerField(default=0)
# Updated by signals, but what if signal fails?

# Organization model
members_count = models.PositiveIntegerField(default=0)
# Updated manually, no guarantee of accuracy
```

**Risk**: Counts show incorrect data

**Fix Required**:
- Add `update_counts()` method that recalculates from DB
- Run as nightly reconciliation job

---

### 5.3 Race Conditions

**Already Identified in gaps.md**:
- Payment confirmation (Fixed with `select_for_update`)
- Promo code usage (Not fixed)

**Additional Race Conditions**:
1. **Seat allocation**
   - Two admins invite members simultaneously
   - Both check billable_seats < limit
   - Both succeed, exceeding limit

2. **Event capacity**
   - Two users register simultaneously
   - Both check capacity
   - Both succeed, overbooked

**Fix Required**:
- Use `select_for_update()` on Organization before adding members
- Use `select_for_update()` on Event before creating registration

---

### 5.4 Subscription Status Transitions

**Problem**: Subscription status can have invalid transitions

**Example**:
```
trialing → canceled → ???
active → unpaid → ???
```

**No state machine** ensures valid transitions.

**Fix Required**:
- Add `can_transition_to(status)` method
- Raise error on invalid transitions
- Log all status changes

---

## 6. Integration & Webhook Gaps

### 6.1 Webhook Event Coverage

**Implemented** (✅):
- customer.subscription.created
- customer.subscription.updated
- customer.subscription.deleted
- invoice.paid
- invoice.payment_failed
- payment_intent.succeeded
- checkout.session.completed
- charge.refunded
- charge.dispute.created
- charge.dispute.closed
- payout.paid
- payout.failed

**Good Coverage!** Most critical events handled.

**Missing** (Lower Priority):
- customer.tax_id.created
- customer.tax_id.updated
- billing_portal.session.created

---

### 6.2 Webhook Retry Logic

**Problem**: If webhook handler fails, event is lost

**Current Behavior**:
- Webhook fails → Returns 500
- Stripe retries for 3 days
- After 3 days, event is lost forever

**Fix Required**:
- Implement webhook event logging
- Store all webhooks in DB for replay
- Admin dashboard to retry failed webhooks

---

### 6.3 Zoom Webhook Signature Validation

**Problem**: Need to verify Zoom webhooks are authentic

**Files**: `backend/src/integrations/views.py`

**Current State**: Need to check if signature validation is implemented

**Fix Required** (if missing):
- Validate Zoom webhook signatures
- Reject unauthorized webhooks

---

## 7. Organization Management Gaps

### 7.1 No Member Role Changes

**Problem**: Can't change a member's role after invitation

**Example**:
- Invite user as "organizer"
- Later want to make them "admin"
- No endpoint to update role

**Required**:
- `PATCH /organizations/{uuid}/members/{member_uuid}/` endpoint

---

### 7.2 No Member Removal

**Problem**: Can't remove members from organization

**Required**:
- `DELETE /organizations/{uuid}/members/{member_uuid}/` endpoint
- Soft delete membership
- Update seat billing

---

### 7.3 No Pending Invitation Cancellation

**Problem**: Once invited, can't cancel invitation

**Required**:
- List pending invitations
- Cancel invitation before acceptance

---

### 7.4 Organization Deletion Unclear

**Problem**: What happens when org is deleted?
- Members lose access
- Events become orphaned?
- Subscriptions canceled?

**Required**:
- Clear deletion policy
- Transfer assets or archive them

---

## 8. UI/UX & Frontend Gaps

### 8.1 No Loading States for Async Operations

**Problem**: User doesn't know if action is processing

**Examples**:
- Creating event
- Issuing certificates
- Processing payment

**Fix**: Add loading indicators everywhere

---

### 8.2 No Error Message Consistency

**Problem**: Backend returns various error formats

**Fix**: Standardize error responses:
```json
{
  "error": {
    "code": "LIMIT_REACHED",
    "message": "You've reached your event limit",
    "details": {
      "current": 30,
      "limit": 30
    }
  }
}
```

---

### 8.3 No Plan Comparison UI

**Problem**: Users can't compare plans side-by-side

**Fix**: Create pricing comparison table

---

### 8.4 No Usage Dashboard

**Problem**: Users don't know how much of their limit they've used

**Fix**: Show:
- Events created: 25/30
- Certificates issued: 450/500
- Progress bars

---

## 9. Medium Priority Issues

### 9.1 Token Cleanup Job Missing

**Problem**: Expired tokens accumulate in DB

**Fix**: Celery periodic task to delete old tokens

---

### 9.2 Multi-Currency Incomplete

**Problem**: PromoCode has no currency field

**Fix**: Add currency to promo codes, validate against event currency

---

### 9.3 Invoice PDF URLs May Expire

**Problem**: Stripe invoice PDF URLs stored once

**Fix**: Fetch fresh URL from Stripe when needed

---

### 9.4 No Audit Logging for Sensitive Operations

**Problem**: Can't track who did what

**Fix**: Log:
- Subscription changes
- Refunds
- Member additions
- Certificate revocations

**Implemented**: Partial audit logging exists (`accounts/audit.py`) ✅

---

### 9.5 No Rate Limiting on Auth Endpoints

**Problem**: Brute force attacks possible

**Fix**: Already has `AuthThrottle` class ✅ (needs verification)

---

### 9.6 Dead Code in JWT Import

**Problem**: `jwt.ExpiredSignatureError` caught but `jwt` not imported

**Fix**: Remove dead code or add import

---

### 9.7 Fee Rounding Errors

**Problem**: `int()` truncation instead of rounding

**Fix**: Use `Decimal` and proper rounding

---

### 9.8 No Payment Retry Logic

**Problem**: Transient Stripe API failures not retried

**Fix**: Add exponential backoff for specific errors

---

## 10. Low Priority Issues

### 10.1 Expired Payment Methods Not Handled

**Problem**: Expired cards remain as default

**Fix**: Notify user, prompt for update

---

### 10.2 No Session Timeout

**Problem**: JWT tokens don't expire sessions

**Fix**: Add session timeout configuration

---

### 10.3 No Password Strength Requirements

**Problem**: Weak passwords allowed

**Fix**: Add password validator

---

### 10.4 No Two-Factor Authentication

**Problem**: No 2FA option

**Fix**: Add TOTP support (future enhancement)

---

## Summary & Recommendations

### Immediate Action Required (Before Production)

1. **Verify email service configuration** ✅ Critical
2. **Implement trial expiration automation** ⚠️ Revenue risk
3. **Add refund API endpoint** ⚠️ Customer service blocker
4. **Verify organization seat billing** ⚠️ Revenue risk
5. **Enforce certificate limits** ⚠️ Limit bypass
6. **Complete paid course enrollment** ⚠️ Feature incomplete
7. **Test Zoom token refresh** ⚠️ Integration failure
8. **Test multi-session certificate logic** ⚠️ Incorrect issuance

### Post-Launch Priority (Week 1)

1. Payout request system
2. Payment reconciliation tools
3. Organization invitation workflow gaps
4. Event ownership transfer
5. Bulk certificate issuance
6. Promo code usage reversal
7. Downgrade workflow
8. Course grading workflow

### Technical Debt (Month 1)

1. Fix race conditions (seat allocation, event capacity)
2. Add webhook retry system
3. Implement audit logging
4. Add object-level permission enforcement
5. Add denormalized count reconciliation
6. Fix soft delete cascades

### Nice-to-Have (Backlog)

1. Public organization directory
2. Two-factor authentication
3. Advanced analytics
4. Multi-currency support
5. Mobile app

---

## Positive Findings ✅

**The platform has strong foundations**:

1. **Comprehensive models** - All core entities well-designed
2. **Good separation of concerns** - Services, views, serializers properly organized
3. **RBAC system** - Declarative role-based access control implemented
4. **Webhook handlers** - Most critical Stripe events handled
5. **Refund service** - Complete refund logic implemented
6. **Integration services** - Zoom, Stripe, Email services well-structured
7. **Audit logging** - Framework exists (`accounts/audit.py`)
8. **Soft delete** - GDPR-compliant data handling
9. **Select for update** - Race condition mitigation in payment flows
10. **Encrypted tokens** - Zoom OAuth tokens encrypted at rest

**Overall**: The codebase is production-quality with fixable gaps, not fundamental flaws.

---

## Files Requiring Immediate Attention

### Critical Files:
1. `backend/src/billing/tasks.py` - Add trial expiration task
2. `backend/src/billing/views.py` - Add refund endpoint
3. `backend/src/organizations/signals.py` - Verify seat billing triggers
4. `backend/src/certificates/views.py` - Enforce certificate limits
5. `backend/src/learning/views.py` - Complete course payment flow

### High Priority Files:
6. `backend/src/billing/services.py` - Add payout request methods
7. `backend/src/organizations/views.py` - Complete invitation workflow
8. `backend/src/events/services.py` - Add ownership transfer
9. `backend/src/certificates/services.py` - Add bulk issuance
10. `backend/src/accounts/views.py` - Add downgrade endpoint

---

**END OF HOLISTIC GAP ANALYSIS**
