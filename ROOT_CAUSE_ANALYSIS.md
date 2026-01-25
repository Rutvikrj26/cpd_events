# Root Cause Analysis: Missing Navigation Items for Attendees

**Date:** 2026-01-23
**Severity:** 🔴 CRITICAL
**User Affected:** speaker.guest@example.com (and all attendees without subscriptions)

---

## 🎯 Problem Statement

Attendee users (including speaker.guest@example.com) only see "Dashboard" and "Profile" in navigation. They should see:
- ✅ Dashboard
- ❌ Browse Events (MISSING!)
- ❌ Browse Courses (MISSING!)
- ❌ My Registrations (MISSING!)
- ❌ My Certificates (MISSING!)
- ❌ My Badges (MISSING!)
- ❌ CPD Tracking (MISSING!)

This makes the application **UNUSABLE** for attendees - they can't access any of their core features!

---

## 🔬 Root Cause Investigation

### Issue #1: Missing Subscription in Fixtures

**File:** `/backend/scripts/generate_fixtures.py`

**Problem:** Only users 2 and 3 have subscriptions created. Users 4, 5, 6 (attendees and speaker.guest) have NO subscriptions:

```python
# Lines 142-171
# Subscriptions
billing.append({
    "model": "billing.subscription",
    "pk": 1,
    "fields": {
        "user": 2,  # organizer.pro@example.com
        "plan": "pro",
        "status": "active",
        ...
    }
})
billing.append({
    "model": "billing.subscription",
    "pk": 2,
    "fields": {
        "user": 3,  # organizer.basic@example.com
        "plan": "attendee",  # Wait, this is wrong too!
        "status": "active",
        ...
    }
})

# Users 4, 5, 6 (attendees) - NO SUBSCRIPTIONS!
```

**Impact:** Without a subscription:
- `capability_service.get_access_status(user)` returns minimal access
- Manifest returns only base routes
- Frontend doesn't show most navigation items

---

### Issue #2: Backend/Frontend Route Identifier Mismatch

**Backend:** `/backend/src/accounts/views.py:37-94`

Returns route **PATHS**:
```python
routes = [
    "/dashboard",
    "/profile",
    "/settings",
    "/events",  # This is a PATH
    "/certificates",
    "/cpd",
]
```

**Frontend:** `/frontend/src/components/layout/Sidebar.tsx:78-99`

Expects route **IDENTIFIERS**:
```typescript
const navItems: NavItemConfig[] = [
    { routeKey: 'dashboard', ... },
    { routeKey: 'browse_events', ... },  // This is an IDENTIFIER
    { routeKey: 'browse_courses', ... },
    { routeKey: 'registrations', ... },
    { routeKey: 'certificates', ... },
    { routeKey: 'badges', ... },
    { routeKey: 'cpd_tracking', ... },
];
```

**Frontend Check:** `/frontend/src/contexts/AuthContext.tsx:54-57`

```typescript
const hasRoute = (routeKey: string): boolean => {
    if (!manifest) return false;
    return manifest.routes.includes(routeKey);  // Checks if "browse_events" is in ["/dashboard", "/events", ...]
};
```

**Result:** Frontend checks if "browse_events" is in ["/dashboard", "/profile", "/events", ...] - **NEVER MATCHES!**

---

### Issue #3: Missing Route Definitions for Attendee Features

**Backend manifest** (lines 46-53) provides:
- `/events` - Generic "view events" path
- `/certificates` - Generic "view certificates" path
- `/cpd` - CPD tracking path

**Missing identifiers for:**
- `browse_events` - Browse events as attendee
- `browse_courses` - Browse courses
- `registrations` - My registrations
- `badges` - My badges
- `cpd_tracking` - CPD tracking (has path but wrong identifier)

---

### Issue #4: Incorrect Plan in Fixtures

**Line 166** of `generate_fixtures.py`:
```python
billing.append({
    "model": "billing.subscription",
    "pk": 2,
    "fields": {
        "user": 3,  # organizer.basic@example.com
        "plan": "attendee",  # ❌ WRONG! This should be "organizer"!
        ...
    }
})
```

User 3 is `organizer.basic@example.com` but has `plan="attendee"`. This is confusing and incorrect.

---

## 🔍 Why Speaker.Guest Sees Nothing

1. **No subscription** → `capability_service.get_access_status(user)` returns no plan
2. **Backend returns** minimal manifest: `{routes: ["/dashboard", "/profile", "/settings", "/events", "/certificates", "/cpd"], features: {...}}`
3. **Frontend checks** if `'browse_events'` is in `["/dashboard", "/profile", ...]` → **FALSE**
4. **Sidebar filters out** all nav items that fail `hasRoute()` check
5. **Only items that pass** are those in the hardcoded bypass list (now only `dashboard` and `profile` after our refactor)

---

## ✅ The Complete Fix

### Fix #1: Add Attendee Subscriptions to Fixtures

**File:** `/backend/scripts/generate_fixtures.py`

**After line 171, add:**

```python
# Attendee subscriptions (users 4, 5, 6)
for user_pk in [4, 5, 6]:
    pk = user_pk - 1  # subscription pks 3, 4, 5
    billing.append({
        "model": "billing.subscription",
        "pk": pk,
        "fields": {
            "uuid": get_uuid(f"sub_{pk}"),
            "user": user_pk,
            "plan": "attendee",
            "status": "active",
            "created_at": get_date(-30),
            "updated_at": get_date()
        }
    })
```

**Also fix user 3's subscription:**

```python
# Line 166 - change from "attendee" to "organizer"
billing.append({
    "model": "billing.subscription",
    "pk": 2,
    "fields": {
        "uuid": get_uuid("sub_2"),
        "user": 3,
        "plan": "organizer",  # ✅ FIXED: was "attendee"
        "status": "active",
        "created_at": get_date(-30),
        "updated_at": get_date()
    }
})
```

---

### Fix #2: Add Missing Route Identifiers to Backend Manifest

**File:** `/backend/src/accounts/views.py`

**Update `get_allowed_routes_for_user()` function (lines 37-94):**

```python
def get_allowed_routes_for_user(user) -> list[str]:
    """
    Get list of allowed routes for a user based on their subscription.

    Returns route identifiers (not paths) that match frontend routeKey values.
    """
    from billing.capability_service import capability_service

    # Base routes available to all authenticated users
    routes = [
        "dashboard",          # Changed from "/dashboard"
        "profile",            # Changed from "/profile"
        "settings",           # Changed from "/settings"
    ]

    # Get user's access status to determine plan
    access_status = capability_service.get_access_status(user)
    plan = (access_status.plan or "").lower()

    # Attendee routes (for attendee plan and users without subscriptions)
    if plan == "attendee" or not access_status.has_active_subscription:
        routes.extend([
            "browse_events",      # Browse events as attendee
            "browse_courses",     # Browse courses
            "registrations",      # My event registrations
            "certificates",       # My earned certificates
            "badges",             # My earned badges
            "cpd_tracking",       # CPD tracking
        ])

    # Organizer routes
    if capability_service.can_create_events(user):
        routes.extend([
            "my_events",                # My Events (organizer view)
            "create_events",            # Create new events
            "creator_certificates",     # Organizer certificates
            "event_badges",             # Event badges
            "zoom_meetings",            # Zoom integration
            "contacts",                 # Contact management
            "subscriptions",            # Billing
        ])

    # Course Manager routes
    if capability_service.can_create_courses(user):
        routes.extend([
            "browse_courses",           # Browse courses (as learner)
            "courses",                  # Manage courses
            "create_courses",           # Create new courses
            "course_certificates",      # Course certificates
            "subscriptions",            # Billing (if not already added)
        ])

    # Staff-only routes
    if user.is_staff:
        routes.extend([
            "admin",
            "admin_users",
            "admin_subscriptions",
        ])

    return sorted(set(routes))
```

---

### Fix #3: Add Missing Feature Flags

**File:** `/backend/src/accounts/views.py`

**Update `get_features_for_user()` function (lines 97-126) to add:**

```python
def get_features_for_user(user) -> dict:
    """
    Get feature flags for a user based on their subscription.
    """
    from billing.capability_service import capability_service

    access_status = capability_service.get_access_status(user)
    plan_key = (access_status.plan or "").lower()

    return {
        # Core capabilities
        "create_events": capability_service.can_create_events(user),
        "create_courses": capability_service.can_create_courses(user),
        "issue_certificates": capability_service.can_issue_certificates(user),

        # Attendee features (ADD THESE)
        "browse_events": True,  # All users can browse
        "browse_courses": True,  # All users can browse
        "view_own_certificates": True,  # All users can view their certs
        "view_badges": True,  # All users can view badges
        "view_cpd": True,  # All users can track CPD

        # Subscription status
        "has_active_subscription": access_status.is_active,
        "is_trialing": access_status.is_trialing,
        "is_trial_expired": access_status.is_trial_expired,
        "is_in_grace_period": access_status.is_in_grace_period,
        "is_access_blocked": access_status.is_access_blocked,

        # Plan info
        "plan": access_status.plan,
        "has_payment_method": access_status.has_payment_method,

        # Billing access (ADD THIS)
        "view_billing": capability_service.can_create_events(user) or
                        capability_service.can_create_courses(user),

        # Premium features
        "zoom_integration": capability_service.can_create_events(user),
        "custom_branding": plan_key == "pro",
        "api_access": plan_key == "pro",
        "white_label": plan_key == "pro",

        # Organization features
        "can_create_organization": plan_key in ["pro", "organizer", "lms"],
        "can_join_organization": True,  # All users can join orgs
    }
```

---

### Fix #4: Regenerate and Load Fixtures

```bash
cd /home/beyonder/projects/cpd_events/backend
python3 scripts/generate_fixtures.py
cd src
python3 manage.py loaddata accounts billing assets events learning
```

---

## 🧪 Testing Plan

### Test 1: Verify Fixtures
```bash
cd /home/beyonder/projects/cpd_events/backend/src
python3 manage.py shell -c "
from apps.accounts.models import User
from apps.billing.models import Subscription

for user in User.objects.filter(pk__in=[4,5,6]):
    sub = Subscription.objects.filter(user=user).first()
    print(f'{user.email}: {sub.plan if sub else \"NO SUBSCRIPTION\"}'
)
"
```

Expected output:
```
attendee.engaged@example.com: attendee
attendee.casual@example.com: attendee
speaker.guest@example.com: attendee
```

### Test 2: Verify Manifest API
```bash
# Login as speaker.guest
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"speaker.guest@example.com","password":"demo123"}' \
  | jq '.access_token'

# Get manifest
curl -X GET http://localhost:8000/api/v1/auth/manifest/ \
  -H "Authorization: Bearer <token>" \
  | jq '.routes'
```

Expected output:
```json
[
  "badges",
  "browse_courses",
  "browse_events",
  "certificates",
  "cpd_tracking",
  "dashboard",
  "profile",
  "registrations",
  "settings"
]
```

### Test 3: Frontend Navigation

1. Login as speaker.guest@example.com
2. Check sidebar navigation shows:
   - ✅ Dashboard
   - ✅ Browse Events
   - ✅ Browse Courses
   - ✅ My Registrations
   - ✅ My Certificates
   - ✅ My Badges
   - ✅ CPD Tracking
   - ✅ Profile

---

## 📊 Impact Analysis

### Users Affected
- **speaker.guest@example.com** (pk=6) - Alan Grant
- **attendee.engaged@example.com** (pk=4) - Alice Active
- **attendee.casual@example.com** (pk=5) - Bob Basic

### Features Broken
- ❌ Cannot browse events
- ❌ Cannot browse courses
- ❌ Cannot view registrations
- ❌ Cannot view certificates
- ❌ Cannot view badges
- ❌ Cannot track CPD

**Severity:** CRITICAL - Core attendee functionality completely broken

---

## 🔄 Additional Issues Found

### Issue: Organization Invitations Endpoint Missing

**File:** `/frontend/src/components/PendingInvitationsBanner.tsx:26`

**Problem:** Calls `/api/v1/organizations/my-invitations/` which doesn't exist in backend

**Status:** Error toasts suppressed with client.ts fix (added to SILENT_ERROR_ENDPOINTS)

**TODO:** Either:
1. Implement the backend endpoint `/api/v1/organizations/my-invitations/`
2. Remove PendingInvitationsBanner component if feature not needed

---

## 📝 Summary

**3 Critical Issues Identified:**

1. ✅ **Fixtures incomplete** - Attendees have no subscriptions
2. ✅ **Backend/Frontend mismatch** - Routes use paths vs identifiers
3. ✅ **Missing route definitions** - Attendee features not in manifest

**1 Medium Issue:**

4. ⏳ **Missing API endpoint** - Organization invitations not implemented

**Total Files to Modify:** 2
- `/backend/scripts/generate_fixtures.py` - Add attendee subscriptions
- `/backend/src/accounts/views.py` - Fix route identifiers and add missing routes

**Estimated Fix Time:** 2-3 hours (including testing)

**Priority:** 🔴 CRITICAL - Deploy ASAP

---

## 🎭 About "speaker.guest"

**Q: Is speaker.guest a special role?**

**A: NO.** Despite the confusing name, speaker.guest is just a regular attendee:
- pk=6
- email: speaker.guest@example.com
- name: Alan Grant
- organization: Paleontology Dept
- is_staff: False
- is_superuser: False
- **No special permissions**

The name "speaker.guest" is misleading - it's likely meant to represent an attendee who might be invited as a speaker to events, but has no special backend role or permissions beyond a regular attendee.

**Recommendation:** Consider renaming to `attendee.speaker@example.com` for clarity.

---

**End of Analysis**
