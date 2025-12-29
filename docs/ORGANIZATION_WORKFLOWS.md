# Organization Workflows - Complete Documentation

## Overview

This document maps out the complete user workflows for organization accounts in the CPD Events platform, differentiating them from regular organizer accounts.

---

## Account Types Comparison

### Regular Organizer Account
- **Individual user** with account_type = 'organizer'
- Can create and manage **events**
- Can create **certificate templates**
- Has individual Stripe Connect account for payments
- **Cannot create courses** (courses are organization-only)
- **Cannot create an organization** (can only be invited to join)
- Uses personal branding and settings
- Limited to individual operations

### Organization Account
- **Multi-user entity** with team collaboration
- Owned by an **Organization** model (not a single user)
- Members have **roles**: owner, admin, manager, member
- Can create and manage **courses** (organization-exclusive feature)
- Can create and manage **events** (owned by organization)
- Has organization-level Stripe Connect account
- Per-seat subscription billing
- Shared branding, templates, contacts, and assets
- Team management and role-based permissions

---

## Organization Workflows

### 1. Creating an Organization Account

#### Path A: Fresh Organization Creation
**User Journey:**
1. User is a regular organizer (or any authenticated user)
2. Navigates to `/organizations/new`
3. Fills out organization creation form:
   - Organization name (required)
   - Description
   - Website
   - Contact email
   - Branding (logo, colors)
4. Clicks "Create Organization"
5. Backend creates:
   - `Organization` model instance
   - `OrganizationMembership` with role='owner' for creator
   - `OrganizationSubscription` (default: free plan)
6. User is redirected to `/org/{slug}` (organization dashboard)
7. Creator becomes **owner** of the organization

**Backend Endpoints:**
- `POST /api/organizations/` - Create new organization
- Uses `OrganizationCreateSerializer`

**Key Files:**
- Backend: `backend/src/organizations/views.py:OrganizationViewSet.create()`
- Backend: `backend/src/organizations/serializers.py:OrganizationCreateSerializer`
- Frontend: `frontend/src/pages/organizations/CreateOrganizationPage.tsx`

---

#### Path B: Upgrade from Individual Organizer (Data Transfer)
**User Journey:**
1. User is an **existing organizer** with events/templates
2. Navigates to `/organizations/new?from=account`
3. Sees preview of data that will be transferred:
   - Number of events
   - Number of certificate templates
4. Provides organization name
5. Clicks "Create Organization" (transfers data)
6. Backend creates:
   - `Organization` using organizer's profile data
   - `OrganizationMembership` with role='owner', `linked_from_individual=True`
   - Transfers all events where `organization=null` to new org
   - Transfers all certificate templates where `organization=null` to new org
   - `OrganizationSubscription` (default: free plan)
7. User's events and templates now belong to the organization
8. User retains individual organizer account but becomes organization owner

**Backend Endpoints:**
- `GET /api/organizations/create-from-account/` - Preview linkable data
- `POST /api/organizations/create-from-account/` - Create org from account
- Uses `OrganizationLinkingService.create_org_from_organizer()`

**Key Files:**
- Backend: `backend/src/organizations/views.py:CreateOrgFromAccountView`
- Backend: `backend/src/organizations/services.py:OrganizationLinkingService`
- Frontend: `frontend/src/pages/organizations/CreateOrganizationPage.tsx` (with `?from=account`)

---

### 2. Organization Admin Account Setup

When an organization is created, the **creator automatically becomes the owner** (the admin account).

**Owner Capabilities:**
- Full control over organization
- Manage billing and subscriptions
- Invite/remove members
- Assign roles
- Delete organization
- Create events and courses
- Configure Stripe Connect
- Access all organization assets

**Initial Setup Tasks:**
1. Configure organization profile (branding, contact info)
2. Set up Stripe Connect for payments (if using paid features)
3. Invite team members
4. Create first course or event
5. Configure billing plan if needed

---

### 3. Team Member Management Workflows

#### Inviting a Team Member

**User Journey (Admin/Owner):**
1. Navigate to `/org/{slug}/team`
2. Click "Invite Member"
3. Fill out invitation form:
   - Email address
   - Role (owner, admin, manager, member)
   - Job title (optional)
4. Click "Send Invitation"
5. Backend creates:
   - `OrganizationMembership` with `is_active=False` (pending)
   - Generates `invitation_token`
   - TODO: Send invitation email (not implemented yet)
6. Invitation appears in team list as "Pending"

**Backend Endpoints:**
- `POST /api/organizations/{uuid}/members/invite/`

**Key Files:**
- Backend: `backend/src/organizations/views.py:OrganizationViewSet.invite_member()`
- Frontend: `frontend/src/pages/organizations/TeamManagementPage.tsx`

---

#### Accepting an Invitation

**User Journey (Invitee):**
1. User receives invitation email (TODO: not implemented)
2. Clicks invitation link with token
3. Redirected to `/accept-invite/{token}`
4. If logged in with matching email:
   - Membership is activated
   - User joins organization with assigned role
5. If not logged in or wrong email:
   - Prompted to log in with correct email
6. Redirected to organization dashboard

**Backend Endpoints:**
- `POST /api/organizations/accept-invite/{token}/`

**Key Files:**
- Backend: `backend/src/organizations/views.py:AcceptInvitationView`
- Frontend: TODO - invitation acceptance page not created yet

---

#### Linking an Existing Organizer to Organization

**User Journey (Admin/Owner):**
1. An existing organizer wants to join the organization
2. Admin navigates to organization settings or team page
3. Clicks "Link Organizer" (or organizer uses "Link to Organization")
4. Backend:
   - Creates `OrganizationMembership` with `linked_from_individual=True`
   - Transfers organizer's events/templates to organization
   - Marks membership as linked
5. Organizer can now create content under organization
6. Organizer retains individual account but works within org context

**Backend Endpoints:**
- `POST /api/organizations/{uuid}/link-organizer/`

**Key Files:**
- Backend: `backend/src/organizations/views.py:OrganizationViewSet.link_organizer()`
- Backend: `backend/src/organizations/services.py:OrganizationLinkingService.link_organizer_to_org()`
- Frontend: TODO - Not fully implemented in UI

---

#### Role Management

**Roles and Hierarchy:**
1. **Owner** (highest)
   - Full control, billing, can delete org
   - Can manage all members
   - Cannot remove self if last owner

2. **Admin**
   - Manage members, events, courses, templates
   - Cannot manage billing or delete org
   - Can create content

3. **Manager**
   - Create/edit events and courses
   - Cannot manage members
   - Can view reports

4. **Member** (lowest)
   - View-only access
   - Can complete assigned tasks
   - Free (doesn't count toward billable seats)

**Updating Member Roles:**
- Admin/Owner can change any member's role (except their own)
- Backend: `PATCH /api/organizations/{uuid}/members/{member_uuid}/`
- Frontend: `TeamManagementPage.tsx`

**Removing Members:**
- Admin/Owner can remove members
- Cannot remove self
- Cannot remove last owner
- Backend: `DELETE /api/organizations/{uuid}/members/{member_uuid}/remove/`

---

### 4. Creating Organization Content

#### Creating a Course (Organization-Only Feature)

**Prerequisites:**
- User must be in organization context
- User must have manager+ role
- Organization must have available course quota (based on plan)

**User Journey:**
1. Navigate to `/org/{slug}/courses`
2. Click "Create Course"
3. Fill out course creation form:
   - Title, slug, description
   - CPD credits and type
   - Pricing (free or paid)
   - Enrollment settings
   - Certificate template (optional)
4. Click "Create Course"
5. Backend creates `Course` with `organization` FK
6. User is redirected to course management page
7. Can add modules, content, assignments

**Backend Endpoints:**
- `POST /api/courses/` - Create course
- `GET /api/courses/` - List organization's courses
- `GET /api/courses/{uuid}/` - Course details

**Key Files:**
- Backend: `backend/src/learning/models.py:Course` (organization FK required)
- Backend: `backend/src/learning/views.py:CourseViewSet`
- Frontend: `frontend/src/pages/organizations/courses/CreateCoursePage.tsx`

**Important Notes:**
- **Courses REQUIRE organization ownership** - individual organizers cannot create courses
- Course model has `organization = ForeignKey('organizations.Organization', on_delete=CASCADE)`
- This is a key differentiator between organization and individual organizer accounts

---

#### Creating an Event (Can be Individual or Organization)

**Organization Context:**
1. Navigate to `/org/{slug}` or organizer dashboard
2. Click "Create Event"
3. Fill out event form
4. Backend creates `Event` with:
   - `owner` = current user
   - `organization` = current organization (if in org context)
   - OR `organization = null` (if individual organizer)
5. Event appears in organization's event list or individual's event list

**Backend Endpoints:**
- `POST /api/events/`

**Key Files:**
- Backend: `backend/src/events/models.py:Event` (has optional organization FK)
- Frontend: Event creation wizard

**Important Notes:**
- Events can be created by **both** individual organizers and organizations
- Event model has `organization = ForeignKey(..., null=True)` - optional
- If created in org context, organization owns the event
- If created by individual, organizer owns the event

---

### 5. Using Organization Assets

**Shared Assets:**
1. **Certificate Templates**
   - Organization can create shared templates
   - All members can use organization templates
   - Templates owned by organization appear in dropdown

2. **Contacts**
   - Shared contact database
   - All members can access organization contacts
   - Useful for inviting speakers, attendees

3. **Branding**
   - Organization logo, colors used in:
     - Event pages
     - Course pages
     - Certificates
     - Email communications

4. **Stripe Connect**
   - Organization-level payment account
   - Revenue from events/courses goes to organization
   - Managed by owner/admin

**Accessing Assets:**
- Members see organization assets when working in org context
- Context switching via organization selector in UI
- Frontend uses `OrganizationContext` to track current org

---

### 6. Billing and Subscriptions

#### Subscription Plans

**Free Plan:**
- 1 organizer seat
- 2 events per month
- 1 course per month
- 50 attendees per event

**Team Plan:**
- 5 included seats
- $49/additional seat
- Unlimited events and courses

**Business Plan:**
- 15 included seats
- $45/additional seat
- Unlimited events and courses

**Enterprise Plan:**
- 50 included seats
- $40/additional seat
- Unlimited events and courses

**Seat Counting:**
- Only organizer roles (owner, admin, manager) count toward seats
- Member role is free and unlimited
- Subscription tracks `active_organizer_seats`

**Upgrading Plans:**
- Owner navigates to organization settings > billing
- Selects new plan
- TODO: Stripe integration for plan changes (not fully implemented)

---

#### Stripe Connect Setup

**User Journey (Owner/Admin):**
1. Navigate to `/org/{slug}/settings`
2. Go to "Payments" tab
3. Click "Connect Stripe"
4. Backend:
   - Creates Stripe Connect account if not exists
   - Generates onboarding link
   - Returns URL to frontend
5. User redirected to Stripe onboarding
6. Completes Stripe onboarding
7. Redirected back to organization settings
8. `stripe_charges_enabled` becomes true
9. Organization can now accept payments for events/courses

**Backend Endpoints:**
- `POST /api/organizations/{uuid}/stripe/connect/` - Initiate onboarding
- `GET /api/organizations/{uuid}/stripe/status/` - Check status

**Key Files:**
- Backend: `backend/src/organizations/views.py:OrganizationViewSet.stripe_connect()`
- Backend: `backend/src/billing/services.py:stripe_connect_service`
- Frontend: `frontend/src/components/organizations/StripeConnectSettings.tsx`

---

### 7. Organization Dashboard and Navigation

#### Organization Dashboard (`/org/{slug}`)

**Displays:**
- Organization overview
- Team member count
- Event count
- Course count
- Recent activity
- Quick actions

**Tabs:**
- Overview
- Team Members
- Courses
- Settings
- Subscription (if owner)

**Key Files:**
- Frontend: `frontend/src/pages/organizations/OrganizationDashboard.tsx`
- Frontend: `frontend/src/contexts/OrganizationContext.tsx`

---

#### Organization Switcher

**Functionality:**
- User can be member of multiple organizations
- Dropdown in sidebar to switch between:
  - Personal account (individual organizer)
  - Organization 1
  - Organization 2
  - etc.
- Switching changes context for all operations
- Current organization stored in `OrganizationContext`

**Key Files:**
- Frontend: `frontend/src/components/organizations/OrganizationSwitcher.tsx`
- Frontend: `frontend/src/contexts/OrganizationContext.tsx`

---

## Key Differences: Organization vs Individual Organizer

| Feature | Individual Organizer | Organization |
|---------|---------------------|--------------|
| **Account Type** | User with account_type='organizer' | Organization model with members |
| **Can Create Courses** | ❌ No | ✅ Yes (organization-only) |
| **Can Create Events** | ✅ Yes (personal) | ✅ Yes (organization-owned) |
| **Team Collaboration** | ❌ No | ✅ Yes (multi-user with roles) |
| **Billing** | Individual billing | Per-seat subscription |
| **Stripe Connect** | Personal account | Organization account |
| **Shared Assets** | ❌ No | ✅ Yes (templates, contacts, branding) |
| **Create Organization** | ❌ Cannot create | Only owners can manage |
| **Join Organization** | ✅ Can be invited | N/A (organizations invite users) |
| **Role-Based Access** | N/A | Owner, Admin, Manager, Member |

---

## Implementation Gaps and TODOs

### Backend Gaps:
1. ❌ **Email Sending** - Invitation emails not implemented
2. ❌ **Stripe Subscription Management** - Plan upgrades not fully integrated
3. ❌ **Organization Verification** - `is_verified` flag not being set
4. ⚠️ **Seat Limit Enforcement** - Not enforced during member creation
5. ⚠️ **Event/Course Quotas** - Not enforced during creation
6. ❌ **Billing Period Reset** - Usage counters not reset automatically

### Frontend Gaps:
1. ❌ **Invitation Acceptance Page** - No UI for accepting invitations
2. ❌ **Link Organizer Flow** - UI not fully implemented
3. ❌ **Billing Portal** - No customer portal for managing subscriptions
4. ⚠️ **Plan Upgrade Flow** - Limited UI for changing plans
5. ❌ **Organization Onboarding** - No guided setup for new organizations
6. ⚠️ **Course Management UI** - Basic UI exists but incomplete
7. ❌ **Organization Analytics** - No reporting dashboard

### Integration Gaps:
1. ❌ **Email Service** - No email provider configured
2. ⚠️ **Stripe Webhooks** - Limited webhook handling for organizations
3. ❌ **Background Tasks** - No task queue for async operations (seat updates, etc.)

---

## Workflow Clarifications for Development

### When a Regular Organizer Joins an Organization:

**What Happens:**
1. Organizer receives invitation
2. Accepts invitation → `OrganizationMembership` created
3. Organizer gains access to organization
4. **Organizer retains individual account** (can still create personal events)
5. When working in org context, creates org content
6. Can switch between personal and org contexts

**What Does NOT Happen:**
1. Individual account is NOT deleted
2. Personal events are NOT automatically transferred
3. Organizer can still work independently
4. Two separate contexts: personal and organizational

### When Creating Organization from Organizer Account:

**What Happens:**
1. New `Organization` created
2. Organizer becomes owner
3. Existing events/templates transferred to organization
4. Organizer retains individual account
5. Can switch between personal account and organization

**What Does NOT Happen:**
1. Individual organizer account is NOT deleted
2. User doesn't "become" the organization
3. Can still create personal content outside org

---

## Recommended User Workflows

### For Individual Organizers:
1. Start as individual organizer
2. Create personal events
3. When ready to scale:
   - Create organization from account (transfers data)
   - Invite team members
   - Start creating courses (org-only feature)

### For Organizations:
1. Admin creates organization account
2. Sets up billing and Stripe Connect
3. Invites team members with appropriate roles
4. Team collaborates on:
   - Events (organization-owned)
   - Courses (organization-only)
   - Shared templates and contacts

### For Team Members:
1. Receive invitation from organization admin
2. Accept invitation
3. Access organization dashboard
4. Create content based on role:
   - Manager: Create events and courses
   - Admin: Manage team and content
   - Member: View and participate

---

## Technical Implementation Notes

### Backend Models:
- `Organization` - Main organization entity
- `OrganizationMembership` - User-org relationship with roles
- `OrganizationSubscription` - Billing and seat management
- `Course` - **Requires organization** (not nullable FK)
- `Event` - **Optional organization** (nullable FK)
- `CertificateTemplate` - Optional organization (nullable FK)

### Frontend Contexts:
- `AuthContext` - User authentication
- `OrganizationContext` - Current organization state
  - Tracks current org
  - Provides role-checking helpers
  - Manages organization switching

### Routing:
- `/organizations` - List user's organizations
- `/organizations/new` - Create organization
- `/org/{slug}` - Organization dashboard
- `/org/{slug}/team` - Team management
- `/org/{slug}/courses` - Course management
- `/org/{slug}/settings` - Organization settings

---

## Conclusion

Organizations provide a **multi-user, team-based platform** for managing events and courses at scale. The key distinction is:

- **Individual Organizers**: Solo operators who create events
- **Organizations**: Teams that collaborate on events AND courses (courses are organization-exclusive)

Users can operate in **both contexts**: maintaining a personal organizer account while also being part of one or more organizations. The organization switcher allows seamless context switching.

The main workflow gaps are around **invitation emails**, **billing integration**, and **onboarding UX** - these need to be prioritized for a complete organization experience.
