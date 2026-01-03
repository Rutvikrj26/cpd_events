# Comprehensive Audit: User Registration, Subscription, Billing & Money Management

**Audit Date**: January 2026
**Scope**: Full payment and account lifecycle analysis

---

## Executive Summary

This audit covers the entire payment and account lifecycle including user registration, subscription management, billing, and money flows. The system has solid foundational architecture but has **critical gaps** that must be addressed before production.

**Total Gaps Identified**: 22
- Critical: 5
- High Priority: 5
- Medium Priority: 8
- Low Priority: 4

---

## CRITICAL GAPS (Must Fix Before Production)

### 1. REFUND PROCESSING - MISSING ENTIRELY

**Status**: Model exists (`PaymentStatus.REFUNDED`), but NO implementation

**What's Missing**:
- No refund API endpoint (`/registrations/{uuid}/refund/`)
- No `RefundService` class
- No refund webhook handlers (`charge.refunded`)
- No refund reconciliation (platform fee recovery, organizer transfer reversal)
- No refund audit trail

**Business Impact**:
- Cannot process refunds programmatically
- Manual Stripe dashboard intervention required for every refund
- No tracking of refund reasons or patterns
- Platform fees lost on refunds (not recovered)
- Organizer transfers not reversed on refunds

**Technical Details**:
The `Registration` model has `PaymentStatus.REFUNDED` as an option, but there's no code path to set this status. When a refund is processed manually in Stripe:
1. The database remains out of sync
2. No webhook catches the `charge.refunded` event
3. Application fees paid to platform are not recovered
4. Transfers to organizer Connect accounts are not reversed

**Files to Create/Modify**:
| File | Action | Description |
|------|--------|-------------|
| `backend/src/billing/models.py` | Add | `RefundRecord` model to track refunds |
| `backend/src/billing/services.py` | Add | `RefundService` class with `process_refund()` method |
| `backend/src/billing/views.py` | Add | `POST /registrations/{uuid}/refund/` endpoint |
| `backend/src/billing/webhooks.py` | Add | `charge.refunded` webhook handler |

**Implementation Notes**:
```python
# Refund flow should:
# 1. Validate refund eligibility (time limits, event status)
# 2. Calculate refund amount (full vs partial)
# 3. Process refund via Stripe API
# 4. Recover application fee if applicable
# 5. Reverse transfer to organizer if applicable
# 6. Update registration status
# 7. Send confirmation email
# 8. Log for audit trail
```

---

### 2. PAYOUT PROCESSING - MISSING ENTIRELY

**Status**: Connect account creation works, but NO payout initiation

**What's Missing**:
- No `request_payout()` method in `StripeConnectService`
- No payout API endpoint for organizers
- No transfer tracking in database
- No validation that transfers succeeded
- No payout reconciliation or reporting
- No payout scheduling system

**Business Impact**:
- Platform cannot programmatically send earnings to organizers
- Manual Stripe dashboard required for every payout
- No visibility into transfer status
- Organizers cannot request or track payouts
- No financial reconciliation possible

**Technical Details**:
The `StripeConnectService` creates Connect accounts and can process destination charges, but:
1. No method to initiate payouts from Connect account balances
2. No tracking of which payments have been transferred
3. No organizer-facing dashboard for earnings
4. No batch payout capability

**Files to Create/Modify**:
| File | Action | Description |
|------|--------|-------------|
| `backend/src/billing/models.py` | Add | `Transfer` model (platform → organizer transfers) |
| `backend/src/billing/models.py` | Add | `Payout` model (Connect account → bank) |
| `backend/src/billing/services.py` | Add | `request_payout()`, `get_balance()`, `list_transfers()` |
| `backend/src/billing/views.py` | Add | Organizer payout endpoints |

**Implementation Notes**:
```python
# Payout flow should support:
# 1. Manual payout requests from organizers
# 2. Automatic payouts on schedule (weekly/monthly)
# 3. Minimum payout thresholds
# 4. Payout holds for disputes/chargebacks
# 5. Transfer tracking and reconciliation
```

---

### 3. PAYMENT RECONCILIATION - MISSING ENTIRELY

**Status**: No audit tools exist

**What's Missing**:
- No admin endpoint to list/compare payments between Stripe and database
- No fee audit trail (application fees not tracked in DB)
- No transfer reconciliation
- No failed payment dashboard
- No dispute/chargeback resolution tools
- No financial reporting endpoints

**Business Impact**:
- Cannot audit payments for discrepancies
- Hidden fee leakage possible
- Disputes cannot be tracked or resolved
- No visibility into failed payments
- Financial reporting requires manual Stripe export

**Technical Details**:
There's no mechanism to:
1. Compare Stripe records with database records
2. Identify missing webhook events
3. Track application fees collected
4. Generate financial reports
5. Handle chargebacks/disputes

**Files to Create**:
| File | Action | Description |
|------|--------|-------------|
| `backend/src/billing/admin_views.py` | Create | Reconciliation endpoints |
| `backend/src/billing/models.py` | Add | `ApplicationFee` model |
| `backend/src/billing/models.py` | Add | `Dispute` model |
| `backend/src/billing/management/commands/` | Create | Reconciliation commands |

---

### 4. EMAIL SENDING - NOT IMPLEMENTED

**Status**: Email flows exist but sending is commented out/stubbed

**What's Missing**:
- Email verification emails not actually sent
- Password reset emails not actually sent
- Registration confirmation emails not sent
- Subscription change notifications not sent
- Code contains comments like: `"In production: send_password_reset_email.delay(user.id)"`

**Business Impact**:
- Users cannot verify their email addresses
- Users cannot reset passwords via email
- No transactional email communication
- Poor user experience and trust

**Technical Details**:
The authentication flows create tokens but never send emails:
- `accounts/views.py` - Password reset generates token but doesn't email it
- `accounts/views.py` - Email verification creates token but doesn't send verification link
- No Celery tasks configured for async email sending
- No email templates exist

**Files to Modify**:
| File | Action | Description |
|------|--------|-------------|
| `backend/src/accounts/views.py` | Modify | Implement actual email sending |
| `backend/src/accounts/tasks.py` | Create | Celery tasks for async emails |
| `backend/src/templates/emails/` | Create | Email templates |
| `backend/src/config/settings/` | Modify | Email backend configuration |

**Required Email Types**:
1. Email verification
2. Password reset
3. Registration confirmation
4. Subscription activated
5. Subscription cancelled
6. Payment failed
7. Refund processed
8. Payout completed

---

### 5. TRIAL-TO-PAID TRANSITION GAPS

**Status**: Trial expiry tracked but no automatic actions

**What's Missing**:
- No automatic status change when trial expires
- No payment method required during trial signup
- Grace period logic exists in model but not enforced in API
- Users can remain in trial state indefinitely without paying
- No trial expiration notifications

**Business Impact**:
- Lost revenue from unconverted trials
- Unclear subscription state for organizers
- Features may remain accessible after trial ends
- No prompting users to add payment method

**Technical Details**:
- `Subscription.trial_end` field exists and is set
- `Subscription.is_in_trial()` method exists
- BUT: No scheduled task checks for expired trials
- BUT: No enforcement in feature access checks
- BUT: No automatic downgrade when trial expires

**Location**:
- `backend/src/billing/models.py` - Subscription model
- `backend/src/billing/tasks.py` - No trial expiration task

**Files to Modify**:
| File | Action | Description |
|------|--------|-------------|
| `backend/src/billing/tasks.py` | Add | `check_trial_expirations()` Celery beat task |
| `backend/src/billing/models.py` | Add | `expire_trial()` method |
| `backend/src/billing/services.py` | Add | Trial expiration handling |

---

## HIGH PRIORITY GAPS

### 6. Race Conditions in Payment Processing

**Location**: `backend/src/registrations/services.py:122-123`, `backend/src/billing/webhooks.py:334`

**Issue**:
Multiple confirmation paths exist (sync endpoint + webhook) with minimal conflict detection. Two concurrent requests could both attempt to update the same registration.

**Scenario**:
1. User returns from Stripe checkout
2. Frontend calls sync confirmation endpoint
3. Simultaneously, webhook arrives from Stripe
4. Both processes read registration as `PENDING`
5. Both processes update to `PAID`
6. Double-processing could occur

**Fix**:
Add consistent database-level locking using `select_for_update()`:
```python
with transaction.atomic():
    registration = Registration.objects.select_for_update().get(uuid=uuid)
    if registration.payment_status == Registration.PaymentStatus.PAID:
        return  # Already processed
    # Process payment...
```

---

### 7. Promo Code Race Conditions

**Location**: `backend/src/promo_codes/services.py:206`

**Issue**:
`current_uses` field incremented non-atomically. Concurrent uses can exceed the `max_uses` limit.

**Scenario**:
1. Promo code has `max_uses=10`, `current_uses=9`
2. Two users apply code simultaneously
3. Both read `current_uses=9`
4. Both see `9 < 10`, so code is valid
5. Both increment to `current_uses=10`
6. Result: Code used 11 times, limit exceeded

**Fix**:
Use Django's `F()` expression for atomic increment:
```python
from django.db.models import F

PromoCode.objects.filter(pk=promo_code.pk, current_uses__lt=F('max_uses')).update(
    current_uses=F('current_uses') + 1
)
# Check if update succeeded (affected 1 row)
```

---

### 8. Missing Webhook Handlers

**Location**: `backend/src/billing/webhooks.py`

**Missing Handlers**:

| Event | Purpose | Impact of Missing |
|-------|---------|-------------------|
| `charge.refunded` | Sync refund status | Refunds not reflected in DB |
| `charge.dispute.created` | Handle chargebacks | Disputes invisible to platform |
| `charge.dispute.closed` | Resolve disputes | No dispute resolution tracking |
| `customer.updated` | Sync customer info | Customer data drift |
| `account.external_account.created` | Track bank accounts | Connect account incomplete |
| `account.external_account.deleted` | Track bank removal | Stale bank account data |
| `payout.paid` | Confirm payouts | No payout confirmation |
| `payout.failed` | Handle payout failures | Failed payouts undetected |

---

### 9. Usage Counter Reset Logic Issues

**Location**: `backend/src/billing/webhooks.py:210`, `backend/src/billing/tasks.py:15-29`

**Issue**:
Conflicting reset mechanisms exist:
1. Reset triggered on `invoice.paid` webhook (correct approach)
2. Monthly Celery task also resets counters (conflict potential)
3. `current_period_start/end` never updated during reset

**Problems**:
- Double-reset could occur
- Period dates don't match actual billing cycle
- Race condition between webhook and task

**Fix**:
- Remove monthly reset task
- Rely only on `invoice.paid` webhook for reset
- Update period dates from Stripe subscription data

---

### 10. Missing Downgrade Endpoint

**Location**: `backend/src/accounts/models.py:224`

**Issue**:
`User.downgrade_to_attendee()` model method exists but no API endpoint calls it.

**Current State**:
- Method exists: Sets `account_type = 'attendee'`
- No view/endpoint exposed
- Frontend has no way to trigger downgrade

**Fix**:
Add `POST /api/v1/users/me/downgrade/` view that:
1. Validates user has no active paid features
2. Cancels subscription if active
3. Calls `downgrade_to_attendee()`
4. Returns updated user profile

---

## MEDIUM PRIORITY GAPS

### 11. Dead Code - JWT Import

**Location**: `backend/src/accounts/views.py:166`

**Issue**:
`jwt.ExpiredSignatureError` is caught in exception handler, but `jwt` module is never imported. This is dead code that will never execute.

**Fix**: Either remove the dead exception handling or add the import if JWT validation is intended.

---

### 12. Session Management Incomplete

**Location**: `backend/src/accounts/models.py:421`

**Issue**:
`UserSession` model exists to track active sessions, but no endpoints exist for:
- Listing active sessions (`GET /users/me/sessions/`)
- Logout from specific device (`DELETE /users/me/sessions/{id}/`)
- Logout from all devices (`POST /users/me/sessions/logout-all/`)

**Impact**: Users cannot manage their active sessions or secure their account after device loss.

---

### 13. Inconsistent Login Recording

**Location**: `backend/src/accounts/views.py`

**Issue**:
`User.record_login()` is called only in the Zoom OAuth flow, not in standard JWT login. Session tracking is incomplete.

**Fix**: Call `record_login()` in the standard login view after successful authentication.

---

### 14. Fee Calculation Rounding Errors

**Location**: `backend/src/billing/services.py:944`

**Issue**:
Application fee calculation uses `int()` truncation instead of proper rounding:
```python
application_fee = int(amount * 0.05)  # Loses fractional cents
```

**Fix**:
```python
application_fee = round(amount * Decimal('0.05'))
```

---

### 15. No Payment Retry Logic

**Location**: `backend/src/billing/services.py`

**Issue**:
`create_payment_intent()` and `create_subscription()` have no retry logic for transient Stripe API failures.

**Fix**: Add exponential backoff retry for specific error codes (rate limits, network errors).

---

### 16. Expired Payment Methods Not Handled

**Location**: `backend/src/billing/models.py:390-396`

**Issue**:
`PaymentMethod.is_expired` property correctly identifies expired cards, but:
- Expired cards remain set as default
- No notification to user about expiring cards
- No automatic removal or default reassignment

---

### 17. Promo Code Usage Not Reversed on Failed Payment

**Location**: `backend/src/promo_codes/services.py`, `backend/src/registrations/services.py`

**Issue**:
Promo code `current_uses` is incremented when applied, but not decremented when:
- Payment fails
- Registration is cancelled
- Checkout is abandoned

**Impact**: Usage limits become artificially exhausted.

---

### 18. Certificate Limits Not Enforced

**Location**: `backend/src/billing/models.py`

**Issue**:
`Subscription.check_certificate_limit()` method exists, but no API enforces it when creating certificates.

---

## LOW PRIORITY GAPS

### 19. No Token Cleanup

**Issue**: Expired password reset tokens and email verification tokens persist in the database indefinitely.

**Fix**: Add a scheduled task to delete tokens older than their expiry time.

---

### 20. Multi-Currency Incomplete

**Issue**:
- `Event` model has a `currency` field
- `PromoCode` model has no currency field
- Discount calculations may be incorrect for non-USD events

---

### 21. Invoice PDF URLs May Expire

**Issue**:
Stripe-hosted invoice PDF URLs are stored once and never refreshed. URLs may expire over time.

**Fix**: Fetch fresh URL from Stripe API when user requests invoice download.

---

### 22. No Audit Logging

**Issue**:
No logging for sensitive operations:
- Subscription status changes
- Account type upgrades/downgrades
- Payment method changes
- Refund processing
- Admin actions

---

## IMPLEMENTATION PRIORITY ORDER

### Phase 1: Critical (Before Production)
1. Implement refund processing
2. Implement payout processing
3. Fix race conditions (payment confirmation, promo codes)
4. Implement email sending

### Phase 2: High Priority (First Week Post-Launch)
5. Add missing webhook handlers
6. Fix trial-to-paid transition
7. Add reconciliation tools
8. Add downgrade endpoint

### Phase 3: Medium Priority (First Month)
9. Fix usage counter reset logic
10. Add session management endpoints
11. Fix fee rounding
12. Add payment retry logic
13. Handle expired payment methods

### Phase 4: Low Priority (Backlog)
14. Token cleanup job
15. Multi-currency support
16. Invoice URL refresh
17. Audit logging

---

## Files Summary

### Files to Create

| File | Purpose |
|------|---------|
| `backend/src/billing/models.py` additions | RefundRecord, Transfer, Payout, ApplicationFee, Dispute models |
| `backend/src/billing/services.py` additions | RefundService, payout methods |
| `backend/src/billing/admin_views.py` | Reconciliation and admin endpoints |
| `backend/src/accounts/tasks.py` | Email sending Celery tasks |
| `backend/src/templates/emails/` | Email templates |

### Files to Modify

| File | Changes |
|------|---------|
| `backend/src/billing/webhooks.py` | Add refund, dispute, account handlers |
| `backend/src/billing/views.py` | Add refund, payout endpoints |
| `backend/src/billing/services.py` | Fix race conditions, add retries |
| `backend/src/billing/tasks.py` | Add trial expiration task |
| `backend/src/accounts/views.py` | Add email sending, fix JWT dead code, add downgrade endpoint |
| `backend/src/registrations/services.py` | Fix race conditions with select_for_update |
| `backend/src/promo_codes/services.py` | Atomic counter increment with F() |

---

## Security Observations

### Positive Findings
- Webhook signature validation present and correctly implemented
- Atomic transactions for most subscription updates
- Zoom OAuth tokens encrypted at rest
- Soft delete with GDPR-compliant anonymization
- Email addresses normalized (case-insensitive, trimmed)
- UUID used for public-facing IDs (not sequential integers)

### Security Concerns
- Password reset tokens stored in plaintext (should be hashed)
- No audit logging for sensitive operations
- Dead code suggests incomplete refactoring
- No rate limiting on password reset endpoint

---

## Recommended Next Steps

**Decision Required**: Which critical gaps to address first?

- **Option A: Refunds + Payouts** - Complete the money flow
- **Option B: Email sending + Trial transitions** - Improve user experience
- **Option C: Race conditions + Webhooks** - Ensure data integrity

Choose based on your launch timeline and risk tolerance.
