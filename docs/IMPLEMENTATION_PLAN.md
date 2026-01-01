# Organization Workflows - Implementation Plan

## Backend Audit Summary

### What's Already Implemented ✅

1. **Email Infrastructure**
   - ✅ Email service configured (Mailgun for production, console for dev)
   - ✅ `EmailService` class exists in `integrations/services.py`
   - ✅ Template system with fallback to simple HTML
   - ✅ `EmailLog` model for tracking
   - ✅ Cloud tasks for async email sending
   - ✅ Email templates defined (but files may not exist)

2. **Invitation Backend**
   - ✅ `OrganizationMembership` model with invitation fields
   - ✅ `invitation_token`, `invited_at`, `invited_by` fields
   - ✅ `generate_invitation_token()` method
   - ✅ `accept_invitation()` method
   - ✅ `AcceptInvitationView` endpoint (`POST /api/organizations/accept-invite/{token}/`)
   - ✅ `invite_member` action in `OrganizationViewSet`
   - ✅ Proper email validation and user matching

3. **Billing & Subscription**
   - ✅ `OrganizationSubscription` model with seat tracking
   - ✅ Plan configuration (Free, Team, Business, Enterprise)
   - ✅ `can_add_organizer()` method
   - ✅ `check_event_limit()` and `check_course_limit()` methods
   - ✅ `update_seat_usage()` method
   - ✅ `increment_events()` and `increment_courses()` methods
   - ✅ Seat pricing and limits configured

4. **Event/Course Creation**
   - ✅ Event model has optional `organization` FK
   - ✅ Course model has required `organization` FK
   - ✅ `perform_create()` checks individual subscription limits
   - ✅ Organization context can be passed during creation

### What's Partially Implemented ⚠️

1. **Invitation Emails**
   - ⚠️ Email service exists but **NOT CALLED** in `invite_member` view
   - ⚠️ Line 152 in `organizations/views.py`: `# TODO: Send invitation email`
   - ⚠️ Email template `'organization_invitation'` not defined in `EmailService.TEMPLATES`

2. **Quota Enforcement**
   - ⚠️ Methods exist (`check_event_limit`, `check_course_limit`) but **NOT CALLED**
   - ⚠️ Event creation checks individual subscription, not organization subscription
   - ⚠️ Course creation doesn't check limits at all

3. **Seat Limit Enforcement**
   - ⚠️ `can_add_organizer()` exists but **NOT CHECKED** in `invite_member`
   - ⚠️ Can invite unlimited members regardless of plan

### What's Completely Missing ❌

1. **Frontend Pages**
   - ❌ Invitation acceptance page (`/accept-invite/{token}`)
   - ❌ Billing dashboard UI
   - ❌ Course catalog/browse page
   - ❌ Organization public profile pages

2. **Context Persistence**
   - ❌ Organization context not saved in localStorage
   - ❌ Context lost on page refresh

3. **Organization Branding**
   - ❌ Not applied to events/courses
   - ❌ No visual connection between org and content

---

## Implementation Plan

### Phase 1: Fix Invitation Workflow (P0 - Highest Priority)

#### 1.1 Backend: Send Invitation Emails

**File:** `backend/src/organizations/views.py`

**Changes Needed:**
```python
# In invite_member method, after line 150 (membership.generate_invitation_token())

# Add email template to integrations/services.py
# Then call:
from integrations.services import email_service
from django.conf import settings

email_service.send_email(
    template='organization_invitation',
    recipient=email,
    context={
        'invitee_email': email,
        'organization_name': organization.name,
        'inviter_name': request.user.full_name or request.user.email,
        'role': role,
        'invitation_url': f"{settings.SITE_URL}/accept-invite/{membership.invitation_token}",
    }
)
```

**New Email Template:**
- Add `'organization_invitation'` to `EmailService.TEMPLATES`
- Create `backend/src/integrations/templates/emails/organization_invitation.html`

**Status:** ⚠️ Email infrastructure exists, just need to wire it up (1-2 hours)

---

#### 1.2 Frontend: Build Invitation Acceptance Page

**File:** `frontend/src/pages/organizations/AcceptInvitationPage.tsx` (NEW)

**Route:** `/accept-invite/:token`

**Features:**
- Show organization name, logo, inviter
- Show role being offered
- Handle states:
  - Not logged in → redirect to login with return URL
  - Wrong email → show error
  - Already accepted → show message
  - Success → redirect to org dashboard

**API Call:**
```typescript
POST /api/organizations/accept-invite/{token}/
```

**Status:** ❌ Needs full implementation (4-6 hours)

---

#### 1.3 Email Template Creation

**Files to Create:**
- `backend/src/integrations/templates/emails/organization_invitation.html`
- `backend/src/integrations/templates/emails/organization_invitation.txt` (plain text fallback)

**Content:**
```html
<h2>You're invited to join {{organization_name}}</h2>
<p>{{inviter_name}} has invited you to join {{organization_name}} as a {{role}}.</p>
<a href="{{invitation_url}}">Accept Invitation</a>
```

**Status:** ❌ Template doesn't exist (1 hour)

---

### Phase 2: Fix Context Persistence (P0)

#### 2.1 Persist Organization Context

**File:** `frontend/src/contexts/OrganizationContext.tsx`

**Changes:**
```typescript
// Save to localStorage when org changes
useEffect(() => {
  if (currentOrg) {
    localStorage.setItem('current_org_slug', currentOrg.slug);
  } else {
    localStorage.removeItem('current_org_slug');
  }
}, [currentOrg]);

// Restore on mount
useEffect(() => {
  const savedSlug = localStorage.getItem('current_org_slug');
  if (savedSlug && organizations.length > 0) {
    const org = organizations.find(o => o.slug === savedSlug);
    if (org) setCurrentOrg(org);
  }
}, [organizations]);
```

**Status:** ⚠️ Simple fix (1 hour)

---

#### 2.2 URL-Based Context Detection

**File:** `frontend/src/contexts/OrganizationContext.tsx`

**Changes:**
- Detect `/org/{slug}` in URL
- Auto-set context from URL slug
- Keep context when navigating within org

**Status:** ⚠️ Needs implementation (2 hours)

---

### Phase 3: Enforce Seat and Quota Limits (P0)

#### 3.1 Backend: Enforce Seat Limits

**File:** `backend/src/organizations/views.py`

**Changes in `invite_member` method:**
```python
# After line 103 (permission check), add:

# Check if role is organizer-level
if role in ['owner', 'admin', 'manager']:
    subscription = organization.subscription
    if not subscription.can_add_organizer():
        return Response(
            {
                'error': {
                    'code': 'SEAT_LIMIT_REACHED',
                    'message': f'No available seats. Your plan includes {subscription.total_seats} organizer seats. Upgrade your plan or assign a "Member" role (free).',
                    'available_seats': subscription.available_seats,
                    'total_seats': subscription.total_seats,
                }
            },
            status=status.HTTP_402_PAYMENT_REQUIRED
        )
```

**Status:** ⚠️ Method exists, just need to call it (30 minutes)

---

#### 3.2 Backend: Enforce Event Quotas

**File:** `backend/src/events/views.py`

**Changes in `perform_create` method:**
```python
# Replace individual subscription check with organization check

# Get organization from request data or context
organization_uuid = self.request.data.get('organization')
if organization_uuid:
    from organizations.models import Organization
    organization = Organization.objects.get(uuid=organization_uuid)

    # Check event limit
    if not organization.subscription.check_event_limit():
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied(
            f"Event creation limit reached. Your plan allows {organization.subscription.config['events_per_month']} events per month."
        )

    # Increment counter
    organization.subscription.increment_events()
    serializer.save(owner=self.request.user, organization=organization)
else:
    # Individual event - use existing logic
    serializer.save(owner=self.request.user)
```

**Status:** ⚠️ Needs implementation (2 hours)

---

#### 3.3 Backend: Enforce Course Quotas

**File:** `backend/src/learning/views.py` (CourseViewSet)

**Changes in `perform_create`:**
```python
# Courses ALWAYS have organization
organization = serializer.validated_data['organization']

# Check course limit
if not organization.subscription.check_course_limit():
    from rest_framework.exceptions import PermissionDenied
    raise PermissionDenied(
        f"Course creation limit reached. Your plan allows {organization.subscription.config['courses_per_month']} courses per month."
    )

# Increment counter
organization.subscription.increment_courses()
serializer.save(created_by=self.request.user)
```

**Status:** ⚠️ Needs implementation (1 hour)

---

### Phase 4: Add Organization Selector to Event Creation (P1)

#### 4.1 Frontend: Organization Selector in Event Wizard

**File:** `frontend/src/components/events/wizard/steps/StepBasics.tsx` (or create new step)

**Add Field:**
```typescript
// If user belongs to organizations, show selector
{organizations.length > 0 && (
  <div className="space-y-2">
    <Label>Create event for</Label>
    <Select value={organizationUuid} onValueChange={setOrganizationUuid}>
      <SelectTrigger>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="">Personal Account</SelectItem>
        {organizations.map(org => (
          <SelectItem key={org.uuid} value={org.uuid}>
            {org.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  </div>
)}
```

**Pass to API:**
```typescript
const eventData = {
  ...formData,
  organization: organizationUuid || null,
};
```

**Status:** ❌ Needs implementation (3 hours)

---

#### 4.2 Backend: Accept Organization UUID

**File:** `backend/src/events/serializers.py`

**Changes in `EventCreateSerializer`:**
```python
organization = serializers.UUIDField(required=False, allow_null=True)

def create(self, validated_data):
    org_uuid = validated_data.pop('organization', None)
    if org_uuid:
        from organizations.models import Organization
        organization = Organization.objects.get(uuid=org_uuid)
        validated_data['organization'] = organization
    return super().create(validated_data)
```

**Status:** ⚠️ Field exists, just needs to be exposed in serializer (30 minutes)

---

### Phase 5: Build Course Catalog (P1)

#### 5.1 Frontend: Course Browse/Catalog Page

**File:** `frontend/src/pages/courses/CourseCatalogPage.tsx` (NEW)

**Route:** `/courses` or `/courses/browse`

**Features:**
- List all published courses
- Search and filter
- Organization branding on cards
- Enroll button
- "More from [Org]" sections

**API:** `GET /api/courses/?status=published`

**Status:** ❌ Needs full implementation (6-8 hours)

---

#### 5.2 Backend: Public Course Listing Endpoint

**File:** `backend/src/learning/views.py`

**Add:**
```python
@action(detail=False, methods=['get'], permission_classes=[AllowAny])
def public(self, request):
    """List published courses for public browsing."""
    courses = Course.objects.filter(
        status='published',
        is_public=True
    ).select_related('organization')

    serializer = CourseListSerializer(courses, many=True)
    return Response(serializer.data)
```

**Status:** ❌ Needs implementation (1 hour)

---

### Phase 6: Build Billing Dashboard (P1)

#### 6.1 Frontend: Billing Page

**File:** `frontend/src/pages/organizations/BillingPage.tsx` (NEW)

**Route:** `/org/{slug}/billing`

**Features:**
- Current plan display
- Seat usage (X / Y seats used)
- "Upgrade Plan" button
- Plan comparison table
- Add seats interface
- Billing history (if Stripe Customer Portal)

**Status:** ❌ Needs full implementation (8-10 hours)

---

#### 6.2 Backend: Plan Upgrade Endpoint

**File:** `backend/src/organizations/views.py`

**Add:**
```python
@action(detail=True, methods=['post'], url_path='billing/upgrade')
def upgrade_plan(self, request, pk=None):
    """Upgrade organization subscription plan."""
    organization = self.get_object()

    # Only owner can upgrade
    if not self.is_owner(request.user, organization):
        return Response({'error': 'Only owners can manage billing'},
                        status=status.HTTP_403_FORBIDDEN)

    new_plan = request.data.get('plan')
    # Create Stripe Checkout session
    # Update subscription
    # Return checkout URL
```

**Status:** ❌ Needs implementation with Stripe Checkout (6-8 hours)

---

### Phase 7: Organization Public Profiles (P1)

#### 7.1 Frontend: Organization Public Profile Page

**File:** `frontend/src/pages/organizations/OrgPublicProfilePage.tsx` (NEW)

**Route:** `/org/{slug}/public` or `/organizations/{slug}`

**Features:**
- Organization info (logo, description, website)
- Stats (members, events, courses)
- Upcoming events
- Available courses
- Contact button

**Permission:** Public (AllowAny)

**Status:** ❌ Needs full implementation (6-8 hours)

---

#### 7.2 Backend: Public Profile Endpoint

**File:** `backend/src/organizations/views.py`

**Add:**
```python
@action(detail=True, methods=['get'], permission_classes=[AllowAny], url_path='public')
def public_profile(self, request, pk=None):
    """Get public organization profile."""
    organization = self.get_object()

    # Only show verified organizations publicly?
    # Or show all?

    serializer = OrganizationPublicSerializer(organization)
    return Response(serializer.data)
```

**Status:** ❌ Needs implementation (2 hours)

---

### Phase 8: Apply Organization Branding (P2)

#### 8.1 Show Organization on Event/Course Cards

**Files:**
- `frontend/src/components/events/EventCard.tsx`
- `frontend/src/components/courses/CourseCard.tsx`

**Add:**
```typescript
{event.organization && (
  <div className="flex items-center gap-2 text-sm text-muted-foreground">
    <Building2 className="h-4 w-4" />
    <Link to={`/org/${event.organization.slug}/public`}>
      {event.organization.name}
    </Link>
  </div>
)}
```

**Status:** ⚠️ Simple addition (2 hours)

---

#### 8.2 Apply Branding to Public Pages

**Files:**
- `frontend/src/pages/public/EventRegistration.tsx`
- `frontend/src/pages/courses/PublicCourseDetailPage.tsx`

**Add:**
- Organization logo in header
- Organization colors as accents
- "Hosted by [Org]" section
- Link to org profile
- "More from [Org]" section

**Status:** ⚠️ Needs implementation (4 hours)

---

## Summary Timeline

### Week 1: Critical Fixes (P0)
- **Day 1-2:** Fix invitation emails (backend + templates) - 4 hours
- **Day 3-4:** Build invitation acceptance page - 6 hours
- **Day 5:** Persist organization context - 3 hours
- **Day 5:** Enforce seat limits - 1 hour

**Week 1 Total:** 14 hours

### Week 2: Quota Enforcement & Event Context (P0-P1)
- **Day 1:** Enforce event quotas - 2 hours
- **Day 1:** Enforce course quotas - 1 hour
- **Day 2-3:** Add org selector to event creation - 4 hours
- **Day 4-5:** Build course catalog - 8 hours

**Week 2 Total:** 15 hours

### Week 3: Billing & Public Profiles (P1)
- **Day 1-3:** Build billing dashboard - 10 hours
- **Day 4:** Backend plan upgrade endpoint - 8 hours
- **Day 5:** Organization public profiles - 8 hours

**Week 3 Total:** 26 hours

### Week 4: Polish & Branding (P2)
- **Day 1:** Show org on event/course cards - 2 hours
- **Day 2-3:** Apply branding to public pages - 4 hours
- **Day 4-5:** Testing, bug fixes, polish - 8 hours

**Week 4 Total:** 14 hours

---

## Total Estimated Effort: 69 hours (~2 weeks full-time)

---

## Quick Wins (Can Implement Today)

1. **Send invitation emails** - 2 hours
   - Wire up existing email service
   - Create simple template
   - Test in console backend

2. **Persist organization context** - 1 hour
   - Add localStorage save/restore
   - Test context survival across refresh

3. **Enforce seat limits** - 30 minutes
   - Add `can_add_organizer()` check
   - Return proper error

**Total Quick Wins: 3.5 hours**

These three fixes would immediately:
- ✅ Unblock team invitations
- ✅ Fix context persistence UX issue
- ✅ Protect business model with seat limits

---

## Technical Debt to Address

1. **Email Templates**
   - Currently using `_build_simple_html()` fallback
   - Should create proper HTML templates with branding

2. **Background Jobs**
   - Email sending should be async (use cloud tasks)
   - Seat count updates should be background jobs

3. **Frontend Organization Context**
   - Should use URL-based context, not just dropdown
   - Should show current context in breadcrumbs

4. **Quota Reset**
   - Monthly reset task exists but may not be scheduled
   - Need to verify cron/cloud scheduler setup

---

## Risk Assessment

### Low Risk (Safe to Implement)
- ✅ Send invitation emails (isolated change)
- ✅ Context persistence (frontend only)
- ✅ Seat limit enforcement (backend validation)
- ✅ Invitation acceptance page (new page, no side effects)

### Medium Risk (Needs Testing)
- ⚠️ Quota enforcement (could block users unexpectedly)
- ⚠️ Event organization selector (changes creation flow)
- ⚠️ Course catalog (new public-facing feature)

### High Risk (Requires Careful Planning)
- ⚠️ Billing dashboard with Stripe (payment integration)
- ⚠️ Plan upgrades (affects revenue)
- ⚠️ Public organization profiles (SEO, privacy considerations)

---

## Recommended Approach

**Immediate (This Week):**
1. Fix invitation emails
2. Build invitation acceptance page
3. Persist organization context
4. Enforce seat limits

**Next Week:**
5. Enforce quotas (with grace period)
6. Add org selector to events
7. Build course catalog

**Following Weeks:**
8. Billing dashboard
9. Public profiles
10. Branding polish

This approach prioritizes:
- Unblocking critical workflows first
- Building confidence with lower-risk changes
- Delivering value incrementally
