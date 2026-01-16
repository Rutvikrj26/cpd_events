# CPD Events - Signup Workflows Documentation

This document provides comprehensive documentation of the signup workflows for different user types on the CPD Events platform, covering both the user-facing experience and the backend processing.

---

## Table of Contents

1. [Overview](#overview)
2. [User Types & Account Types](#user-types--account-types)
3. [Individual Signup Workflows](#individual-signup-workflows)
   - [Attendee Signup](#1-attendee-signup)
   - [Organizer Signup](#2-organizer-signup)
   - [Course Manager (LMS) Signup](#3-course-manager-lms-signup)
4. [Alternative Authentication Methods](#alternative-authentication-methods)
   - [Zoom SSO Login](#zoom-sso-login)
5. [Organization Member Signup](#organization-member-signup)
6. [Guest Registration → Account Creation](#guest-registration--account-creation)
7. [Post-Signup Processes](#post-signup-processes)
8. [API Reference](#api-reference)
9. [Database Changes on Signup](#database-changes-on-signup)

---

## Overview

The CPD Events platform supports multiple signup pathways depending on the user's intended role:

```mermaid
flowchart TD
    A[User Visits Platform] --> B{Entry Point?}
    B -->|Direct Signup| C["/signup"]
    B -->|From Pricing| D["/signup?role=X&plan=Y"]
    B -->|Zoom SSO| E["/auth/zoom/login/"]
    B -->|Organization Invite| F["/accept-invite/:token"]
    B -->|Event Registration| G["/events/:id/register"]
    
    C --> H[Account Type Selection]
    D --> I[Pre-selected Role]
    E --> J[OAuth Flow]
    F --> K[Accept Invitation]
    G --> L[Guest or Create Account]
```

---

## User Types & Account Types

The platform distinguishes between three primary account types:

| Account Type | Database Value | Description | Trial Period |
|--------------|----------------|-------------|--------------|
| **Attendee** | `attendee` | Default user who attends events | None (Free) |
| **Organizer** | `organizer` | Can create and manage events | 30 days (configurable) |
| **Course Manager** | `course_manager` | Can create and manage LMS courses | 30 days (configurable) |

### Backend Model Reference

**File:** [models.py](file:///home/beyonder/projects/cpd_events/backend/src/accounts/models.py#L74-L77)

```python
class AccountType(models.TextChoices):
    ATTENDEE = 'attendee', 'Attendee'
    ORGANIZER = 'organizer', 'Organizer'
    COURSE_MANAGER = 'course_manager', 'Course Manager'
```

---

## Individual Signup Workflows

### 1. Attendee Signup

#### User Flow

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Frontend
    participant BE as Backend
    participant DB as Database
    participant Email as Email Service

    U->>FE: Navigate to /signup
    FE->>U: Show Attendee Registration Form
    U->>FE: Fill form (email, name, password)
    U->>FE: Accept Terms & Submit
    FE->>BE: POST /api/v1/auth/signup/
    BE->>DB: Create User (account_type='attendee')
    BE->>DB: Create Subscription (plan='attendee', status='active')
    BE->>DB: Link guest registrations
    BE->>Email: Send verification email
    BE->>FE: Return JWT tokens + user data
    FE->>U: Redirect to /login with success message
```

#### Frontend Experience

**URL:** `/signup` (no query parameters)

**Form Fields:**
- Email address (required)
- Full Name (required, min 2 chars)
- Password (required, min 8 chars)
- Confirm Password (required, must match)
- Accept Terms & Conditions (required checkbox)

**Frontend File:** [SignupPage.tsx](file:///home/beyonder/projects/cpd_events/frontend/src/pages/auth/SignupPage.tsx)

#### Backend Processing

1. **User Creation** - Creates user record with `account_type='attendee'`
2. **Subscription Creation** - Signal creates an `ATTENDEE` plan subscription (free, active)
3. **Registration Linking** - Links any guest registrations with same email
4. **Email Verification** - Generates token and sends verification email

**API Endpoint:** `POST /api/v1/auth/signup/`

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword",
  "password_confirm": "securepassword",
  "full_name": "John Doe",
  "account_type": "attendee"
}
```

**Response (201 Created):**
```json
{
  "message": "Account created successfully. Please check your email.",
  "access": "<jwt_access_token>",
  "refresh": "<jwt_refresh_token>",
  "user": {
    "uuid": "...",
    "email": "user@example.com",
    "full_name": "John Doe",
    "account_type": "attendee"
  }
}
```

---

### 2. Organizer Signup

#### User Flow

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Frontend
    participant BE as Backend
    participant DB as Database
    participant Stripe as Stripe API
    participant Email as Email Service

    U->>FE: Navigate to /signup?role=organizer
    FE->>U: Show Organizer Form + Trial Banner
    Note right of FE: "30-Day Trial - No credit card required"
    U->>FE: Fill form (email, name, password)
    U->>FE: Submit
    FE->>BE: POST /api/v1/auth/signup/
    BE->>DB: Create User (account_type='organizer')
    BE->>DB: Create Subscription (plan='organizer', status='trialing')
    BE->>DB: Set trial_ends_at (30 days)
    BE->>Email: Send verification email
    BE->>FE: Return JWT tokens + user data
    FE->>U: Toast: "Your 30-day Organizer trial has started"
    FE->>U: Redirect to /login
```

#### Frontend Experience

**URL:** `/signup?role=organizer` or `/signup?plan=organizer`

**Additional UI Elements:**
- Trial banner: "30-Day Trial - Full access to all features. No credit card required."
- Organizer benefits card with feature list:
  - Create unlimited events (with plan limits)
  - Zoom integration for attendance tracking
  - Issue professional certificates
  - Accept payments for paid events

**Button Text:** "Create Organizer Account"

#### Backend Processing

Same as attendee but with key differences:

1. **User Creation** - `account_type='organizer'`
2. **Subscription Creation** - Signal creates `ORGANIZER` plan with:
   - `status='trialing'`
   - `trial_ends_at` set based on StripeProduct configuration (default 30 days)

**Backend Signal:** [signals.py](file:///home/beyonder/projects/cpd_events/backend/src/billing/signals.py#L13-L59)

```python
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_subscription_for_organizer(sender, instance, created, **kwargs):
    if not created:
        return
    
    if instance.account_type == 'organizer':
        plan = Subscription.Plan.ORGANIZER
        # Fetch trial days from StripeProduct configuration
        product = StripeProduct.objects.filter(plan=plan, is_active=True).first()
        trial_days = product.trial_period_days if product else 0
        
        Subscription.objects.get_or_create(
            user=instance,
            defaults={
                'plan': plan,
                'status': Subscription.Status.TRIALING,
                'trial_ends_at': timezone.now() + timedelta(days=trial_days),
            },
        )
```

---

### 3. Course Manager (LMS) Signup

#### User Flow

Identical to Organizer signup with different URL parameters.

**URL:** `/signup?role=course_manager` or `/signup?plan=lms`

**Additional UI Elements:**
- LMS benefits card:
  - Build self-paced courses and modules
  - Track learner progress and completion
  - Issue course completion certificates
  - Accept payments for paid courses

#### Backend Processing

1. **User Creation** - `account_type='course_manager'`
2. **Subscription Creation** - Signal creates `LMS` plan with:
   - `status='trialing'`
   - `trial_ends_at` based on LMS product configuration

---

## Alternative Authentication Methods

### Zoom SSO Login

Users can authenticate using their Zoom account. This creates/links a user account automatically.

#### Flow

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Frontend
    participant BE as Backend
    participant Zoom as Zoom OAuth

    U->>FE: Click "Login with Zoom"
    FE->>BE: GET /api/v1/auth/zoom/login/
    BE->>FE: Return authorization URL
    FE->>Zoom: Redirect to Zoom OAuth
    U->>Zoom: Authorize application
    Zoom->>BE: Callback with auth code
    BE->>Zoom: Exchange code for tokens
    BE->>Zoom: Get user info
    BE->>BE: Find/Create user by email
    BE->>BE: Create/Update ZoomConnection
    BE->>FE: Redirect with JWT tokens
    FE->>U: Logged in
```

#### Backend Processing

**Callback View:** [views.py](file:///home/beyonder/projects/cpd_events/backend/src/accounts/views.py#L640-L748)

1. **Token Exchange** - Exchange authorization code for access/refresh tokens
2. **User Info Fetch** - Get email, name from Zoom API
3. **User Matching** - First by ZoomConnection, then by email
4. **User Creation** (if new):
   - `email_verified=True` (Zoom emails trusted)
   - `password=None` (unusable password)
5. **ZoomConnection Creation** - Store OAuth tokens for future API calls
6. **JWT Generation** - Create access/refresh tokens

---

## Organization Member Signup

Organizations can invite members via email. Invitees receive a token-based invitation link.

### Invitation Flow

```mermaid
sequenceDiagram
    participant A as Admin
    participant BE as Backend
    participant Email as Email Service
    participant I as Invitee
    participant FE as Frontend

    A->>BE: POST /organizations/:id/members/invite
    BE->>BE: Create OrganizationMembership (is_active=false)
    BE->>BE: Generate invitation token
    BE->>Email: Send invitation email
    Email->>I: Invitation link
    I->>FE: Click /accept-invite/:token
    
    alt User not logged in
        FE->>FE: Redirect to /login with return URL
        I->>FE: Login or Signup
    end
    
    FE->>BE: GET /accept-invite/:token (view details)
    BE->>FE: Organization info, role, requirements
    
    alt Organizer role with organizer-paid billing
        FE->>I: Show "Subscription Required" message
        I->>FE: Upgrade subscription
    end
    
    I->>FE: Accept invitation
    FE->>BE: POST /accept-invite/:token
    BE->>BE: Link user to membership
    BE->>BE: Set accepted_at, is_active=true
    BE->>FE: Success response
```

### Organization Membership Roles

| Role | Description | Billing |
|------|-------------|---------|
| `admin` | Organization manager | Included in base plan |
| `organizer` | Can create events under org | Per-seat or self-paid |
| `course_manager` | Can manage LMS courses | Per-seat billing |
| `instructor` | Assigned to specific courses | Free |

### Backend Endpoints

**Invite Member:** `POST /api/v1/organizations/:uuid/members/invite/`

**Request:**
```json
{
  "email": "member@example.com",
  "role": "organizer",
  "title": "Senior Trainer",
  "billing_payer": "organization"  // or "organizer"
}
```

**Accept Invitation:** `POST /api/v1/accept-invite/:token/`

**View Source:** [views.py](file:///home/beyonder/projects/cpd_events/backend/src/organizations/views.py#L202-L446)

---

## Guest Registration → Account Creation

Users can register for events as guests, then later create an account to link their registrations.

### Flow

```mermaid
flowchart TD
    A[Guest registers for event] --> B[Registration created with email only]
    B --> C{Later, user signs up with same email}
    C -->|Signup| D[SignupSerializer.create]
    D --> E[Registration.link_registrations_for_user]
    E --> F[All guest registrations linked to new account]
    
    C -->|Email Verification| G[EmailVerificationView.post]
    G --> H[Registration.link_registrations_for_user]
    H --> F
```

### Backend Implementation

**Linking Logic:** [serializers.py](file:///home/beyonder/projects/cpd_events/backend/src/accounts/serializers.py#L66-L70)

```python
def create(self, validated_data):
    # ... create user ...
    
    # Link any guest registrations
    from registrations.models import Registration
    Registration.link_registrations_for_user(user)
    
    return user
```

The linking also occurs:
- During email verification ([views.py](file:///home/beyonder/projects/cpd_events/backend/src/accounts/views.py#L126-L129))
- During signup view response ([views.py](file:///home/beyonder/projects/cpd_events/backend/src/accounts/views.py#L60-L62))

---

## Post-Signup Processes

### Sequence of Backend Events

```mermaid
sequenceDiagram
    participant API as SignupView
    participant Ser as SignupSerializer
    participant DB as Database
    participant Sig as Django Signals
    participant Email as Email Service
    participant Task as Task Queue

    API->>Ser: Create user
    Ser->>DB: Save User model
    DB-->>Sig: post_save signal
    Sig->>DB: Create Subscription (billing/signals.py)
    Ser->>DB: Link guest registrations
    API->>DB: Generate email verification token
    API->>Task: send_email_verification.delay()
    Task->>Email: Send verification email
    API->>API: Return JWT + user data
```

### Email Verification Flow

1. **Token Generation** - 32-character random token stored on user
2. **Email Sent** - Contains link: `{FRONTEND_URL}/auth/verify-email?token={token}`
3. **Token Validity** - 24 hours from generation
4. **Verification** - `POST /api/v1/auth/verify-email/` with token

**Verification View:** [views.py](file:///home/beyonder/projects/cpd_events/backend/src/accounts/views.py#L97-L131)

---

## API Reference

### Authentication Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/signup/` | POST | Create new user account |
| `/api/v1/auth/token/` | POST | Login (get JWT tokens) |
| `/api/v1/auth/verify-email/` | POST | Verify email with token |
| `/api/v1/auth/password-reset/` | POST | Request password reset |
| `/api/v1/auth/password-reset/confirm/` | POST | Confirm password reset |
| `/api/v1/auth/zoom/login/` | GET | Get Zoom OAuth URL |
| `/api/v1/auth/zoom/callback/` | GET | Zoom OAuth callback |

### Organization Invitation Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/organizations/:uuid/members/invite/` | POST | Invite member |
| `/api/v1/accept-invite/:token/` | GET | View invitation details |
| `/api/v1/accept-invite/:token/` | POST | Accept invitation |

---

## Database Changes on Signup

### Tables Modified

| Table | Action | Conditions |
|-------|--------|------------|
| `users` | INSERT | Always |
| `subscriptions` | INSERT | Always (via signal) |
| `registrations` | UPDATE | If guest registrations exist with same email |
| `zoom_connections` | INSERT | Only for Zoom SSO signup |
| `organization_memberships` | UPDATE | Only for invitation acceptance |
| `user_sessions` | INSERT | On subsequent login |

### User Table Fields Populated

```sql
-- New user record structure
INSERT INTO users (
    uuid,              -- Auto-generated
    email,             -- From form
    full_name,         -- From form
    account_type,      -- 'attendee' | 'organizer' | 'course_manager'
    password,          -- Hashed (or NULL for SSO)
    email_verified,    -- false (or true for Zoom SSO)
    email_verification_token,  -- 32-char token
    email_verification_sent_at,  -- current timestamp
    is_active,         -- true
    created_at,        -- current timestamp
    updated_at         -- current timestamp
);
```

### Subscription Table Fields Populated

```sql
-- For attendees
INSERT INTO subscriptions (
    user_id,
    plan = 'attendee',
    status = 'active'
);

-- For organizers/course_managers
INSERT INTO subscriptions (
    user_id,
    plan = 'organizer' | 'lms',
    status = 'trialing',
    trial_ends_at = NOW() + INTERVAL '30 days'
);
```

---

## Related Documentation

- [USER_WORKFLOWS.md](file:///home/beyonder/projects/cpd_events/frontend/USER_WORKFLOWS.md) - Frontend workflow diagrams
- [ADMIN_PANEL_GUIDE.md](file:///home/beyonder/projects/cpd_events/docs/ADMIN_PANEL_GUIDE.md) - Admin configuration for trial periods
- [drf-api-specification.md](file:///home/beyonder/projects/cpd_events/docs/drf-api-specification.md) - Full API specification
