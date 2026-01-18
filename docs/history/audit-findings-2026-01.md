# Comprehensive Audit Findings & Action Plan

## Issue 1: Duplicate Profile Pages (/profile vs /settings)

### Current State
- **Two routes exist**: `/profile` and `/settings`
- `/profile` (ProfilePage.tsx): Simple billing-focused view with payment methods and subscription
- `/settings` (ProfileSettings.tsx): Comprehensive tabbed view with General, Billing, Security, Notifications

### Navigation References to /profile
1. `PublicLayout.tsx:164` - User dropdown menu in public pages
2. `AttendeeDashboard.tsx:68` - "View Profile" button
3. `OnboardingChecklist.tsx:66` - "Complete Profile" task

### Action Plan
- ✅ Keep `/settings` route (has all functionality)
- ✅ Delete `/profile` route from App.tsx
- ✅ Delete `ProfilePage.tsx` file
- ✅ Update all references to `/profile` → `/settings`

---

## Issue 2: Pricing Rules Inconsistency

### Current State
**Main Pricing Page** (`PricingPage.tsx`):
- Fetches from `getPublicPricing()` API
- Source: Backend StripeProduct models (database)
- Shows monthly/annual pricing dynamically

**Upgrade Modal** (in `BillingPage.tsx`):
- Fetches from same `getPublicPricing()` API
- **SAME SOURCE**: Both use backend as source of truth ✅

### Pricing Calculation Issue
- Monthly price: Direct from `prices.find(p => p.billing_interval === 'month')`
- Annual price: Shows monthly equivalent but **may not be calculating discount correctly**

### Action Plan
- ✅ Verify both pages use identical pricing display logic
- ✅ Add annual discount calculation (e.g., save 20% with annual billing)
- ✅ Ensure price formatting is consistent

---

## Issue 3: Billing Page Opens When Billing Already Setup

### Current State
**Billing page opens in these scenarios**:
1. Direct navigation to `/billing`
2. "View Plans" from TrialStatusBanner
3. "Change Plan" button in BillingPage itself
4. Checkout success redirect: `/billing?checkout=success`

**Problem**: No conditional logic prevents accessing billing page when billing is complete

### Expected Behavior
- If user has active payment method AND active subscription → Don't force to billing page
- Trial banner should check `subscription.has_payment_method` before prompting

### Action Plan
- ✅ Update TrialStatusBanner to check payment method status
- ✅ Show "Setup Billing" only when `subscription.has_payment_method === false`
- ✅ If payment method exists, show "View Billing" instead

---

## Issue 4: Credit Card Not Showing in Settings

### Current State
**ProfilePage.tsx** (soon to be deleted):
- Fetches payment methods via `getPaymentMethods()` API
- Displays card list with details

**ProfileSettings.tsx Billing Tab**:
- **ALSO fetches from `getPaymentMethods()` API** ✅
- **Should be working** - likely a rendering issue

### Investigation Needed
- Check if Billing tab is properly fetching on mount
- Verify payment methods are being saved correctly

### Action Plan
- ✅ Verify getPaymentMethods() is called in Billing tab useEffect
- ✅ Check PaymentMethodModal is saving correctly
- ✅ Test full flow: Add card → Verify appears in both places

---

## Issue 5: Organization Creation Page Access

### Current State
**Backend Permission**:
- `createOrganization()` endpoint: `IsAuthenticated` only
- **ANY authenticated user can create organization** (becomes owner)

**Frontend Route**:
- `/organizations/create` in App.tsx
- No conditional rendering based on existing organization

### Problem
- If user already has organizer account (which can be upgraded to org)
- Or if user is already member of an organization
- They can still access organization creation page

### Backend Source of Truth
- Backend RBAC manifest does NOT restrict organization creation
- Feature flag `create_events` is organizer-specific
- **No `create_organization` feature flag exists**

### Action Plan
- ✅ Add backend check: If user is already organization owner/admin, prevent new org creation
- ✅ Add feature flag `can_create_organization` to manifest
- ✅ Frontend: Check flag before showing "Create Organization" button/route
- ✅ Show appropriate message: "You're already part of an organization"

---

## Issue 6: Onboarding Banner Zoom Link Goes to /settings

### Current State
**OnboardingChecklist.tsx**:
- Line 79: Zoom connect task links to `/settings`
- Expected: Should link to `/zoom` or specific Zoom management page

**Actual Zoom Management**:
- Route exists: `/settings` renders `ZoomManagement.tsx`
- But this is confusing - Zoom management deserves dedicated route

### Routes in App.tsx
- No dedicated `/zoom` route exists
- Zoom management is embedded in settings

### Action Plan
- ✅ **Option A**: Create dedicated `/zoom` route → ZoomManagement component
- ✅ **Option B**: Keep in settings but fix onboarding link description
- **Recommendation**: Keep embedded in settings (user expects integrations there)
- ✅ Update onboarding task to say "Connect Zoom in Settings"

---

## Issue 7: Route Access Control Audit

### Findings

**Backend is Source of Truth** ✅

**RBAC System** (`common/rbac.py`):
- Decorator `@roles()` registers routes with required roles
- `RoleBasedPermission` class enforces on DRF viewsets
- Manifest endpoint returns user's allowed routes and features

**Frontend AuthContext**:
- Fetches manifest from `/auth/manifest/`
- Provides `hasRoute()` and `hasFeature()` helpers
- **Used for UI-level decisions only**

**ProtectedRoute Component**:
- Only checks `isAuthenticated` flag
- Does NOT check manifest routes
- **Gap**: Should optionally check manifest for route-specific access

### Current Protection Levels

1. **Authentication-only** (ProtectedRoute):
   - All dashboard routes under `/dashboard/*`
   - Profile, settings, billing, events

2. **Backend API-level**:
   - Viewsets enforce permissions via DRF permission classes
   - QuerySet filtering (e.g., user's organizations only)

3. **UI-level** (Manifest):
   - Sidebar conditionally shows nav items
   - Feature-specific buttons (e.g., "Create Event")

### Gaps Identified

1. **No frontend route-level manifest checking**
   - User can manually navigate to `/organizations/create` even if not allowed
   - Backend will reject API call, but UI shows

2. **Inconsistent use of manifest checks**
   - Some components check `hasFeature()`
   - Others check `account_type` directly
   - Should standardize on manifest

3. **Missing feature flags**:
   - No `can_create_organization` flag
   - No `can_access_billing` flag
   - No `can_manage_integrations` flag

### Action Plan
- ✅ Add missing feature flags to backend manifest
- ✅ Update ProtectedRoute to support `requiredRoute` prop
- ✅ Add route checks to sensitive pages (org creation, billing)
- ✅ Standardize feature flag usage across components

---

## Full Migration Plan

### Phase 1: Profile/Settings Consolidation
1. Update all `/profile` links to `/settings`
2. Remove `/profile` route from App.tsx
3. Delete ProfilePage.tsx file
4. Verify all functionality preserved in ProfileSettings.tsx

### Phase 2: Billing/Pricing Synchronization
1. Verify both pages use same pricing source
2. Add payment method status checks to TrialStatusBanner
3. Test billing page logic with various subscription states

### Phase 3: Organization Access Control
1. Add `can_create_organization` feature flag to backend
2. Update organization creation view to check existing memberships
3. Add frontend manifest check before showing org creation

### Phase 4: Navigation & Routing Fixes
1. Update Zoom onboarding task link (keep /settings, update description)
2. Add manifest-based route protection to ProtectedRoute
3. Standardize feature flag usage

### Phase 5: Testing & Verification
1. Test attendee account: No org creation, no event creation
2. Test organizer account: Can create events, proper billing access
3. Test org member: Access to org, proper role-based actions
4. Verify all removed routes return 404 or redirect

---

## Files to Modify

### Delete
- ✅ `/frontend/src/pages/profile/ProfilePage.tsx`

### Update
- ✅ `/frontend/src/App.tsx` - Remove /profile route
- ✅ `/frontend/src/components/layout/PublicLayout.tsx` - Change /profile → /settings
- ✅ `/frontend/src/pages/dashboard/attendee/AttendeeDashboard.tsx` - Change /profile → /settings
- ✅ `/frontend/src/components/onboarding/OnboardingChecklist.tsx` - Change /profile → /settings
- ✅ `/frontend/src/components/billing/TrialStatusBanner.tsx` - Add payment method check
- ✅ `/backend/src/common/rbac.py` - Add can_create_organization feature
- ✅ `/backend/src/organizations/views.py` - Add org creation check
- ✅ `/frontend/src/components/layout/ProtectedRoute.tsx` - Add manifest route checking

---

## Expected Outcomes

1. **Single source of truth for user settings**: `/settings` only
2. **Consistent pricing display**: Main page and upgrade modal match
3. **Smart billing prompts**: Only show when billing actually needs setup
4. **Proper access control**: Backend manifest controls who sees what
5. **Clear navigation**: Onboarding links make sense
6. **No dead routes**: All references updated, no 404s
