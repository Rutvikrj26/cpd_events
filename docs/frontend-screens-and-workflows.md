# Frontend Screens & User Workflows - Complete Reference

## Document Overview

This document provides an exhaustive catalog of all frontend screens for the CPD Events Management Platform, along with the user workflows they support. It serves as the definitive reference for frontend development.

**Platform:** CPD Events Management Platform  
**Document Version:** 1.0  
**Last Updated:** December 2024

---

## Table of Contents

1. [Summary Statistics](#summary-statistics)
2. [Public Screens](#1-public-screens)
3. [Authentication Screens](#2-authentication-screens)
4. [Attendee Screens](#3-attendee-screens)
5. [Organizer Screens](#4-organizer-screens)
6. [Settings Screens](#5-settings-screens)
7. [Billing Screens](#6-billing-screens)
8. [Onboarding Flows](#7-onboarding-flows)
9. [Modals & Overlays](#8-modals--overlays)
10. [Email Templates](#9-email-templates)
11. [Error & Empty States](#10-error--empty-states)
12. [Loading States](#11-loading-states)
13. [User Workflow Summary](#12-user-workflow-summary)
14. [Mobile Considerations](#13-mobile-considerations)
15. [Navigation Architecture](#14-navigation-architecture)

---

## Summary Statistics

| Category | Screen Count | Primary User |
|----------|--------------|--------------|
| Public Screens | 8 | Anyone |
| Authentication | 6 | Anyone |
| Attendee Screens | 12 | Attendees |
| Organizer Screens | 28 | Organizers |
| Learning/LMS | 10 | Both |
| Recordings | 4 | Both |
| Multi-Session Events | 5 | Both |
| Settings | 8 | Both |
| Billing | 5 | Organizers |
| Onboarding | 4 | Both |
| **TOTAL** | **~90 screens** | |

| Additional Elements | Count |
|---------------------|-------|
| Modals | 15+ |
| Email Templates | 20+ |
| Empty States | 10+ |
| Error States | 5+ |

---

## 1. Public Screens

*No authentication required*

### 1.1 Landing Page

| Attribute | Details |
|-----------|---------|
| **URL** | `/` |
| **Purpose** | Marketing page, conversion entry point |
| **Key Elements** | Hero section, features, how it works, pricing tiers, footer |
| **CTAs** | "Sign Up", "Login", "Start Free Trial" |
| **Workflows Supported** | New user acquisition, plan comparison |

**Sections:**
- Hero with value proposition
- Features: Zoom integration, attendance tracking, certificates, CPD tracking
- How It Works: 3-step visual flow
- Pricing: Subscription tiers
- Footer: Links, legal, contact

---

### 1.2 Pricing Page

| Attribute | Details |
|-----------|---------|
| **URL** | `/pricing` |
| **Purpose** | Display subscription tiers and features |
| **Key Elements** | Plan comparison table, feature lists, FAQ |
| **CTAs** | "Get Started" per plan |
| **Workflows Supported** | Plan selection before signup |

---

### 1.3 Event Discovery / Browse Events

| Attribute | Details |
|-----------|---------|
| **URL** | `/events/browse` |
| **Purpose** | Public event listing for discovery |
| **Key Elements** | Search bar, filters, event cards, sorting |

**Filters:**
- Date range
- Credit type (CME, CLE, CPE, etc.)
- Event type (Webinar, Workshop, Course, etc.)
- Organizer

**Event Card Elements:**
- Title
- Organizer name
- Date/time
- CPD badge (type + credits)
- "Register" button

**Empty State:** "No events match your filters"

**Workflows Supported:** Event discovery, public registration

---

### 1.4 Public Event Detail

| Attribute | Details |
|-----------|---------|
| **URL** | `/events/{slug}` or `/e/{slug}` |
| **Purpose** | Event information and registration |
| **Key Elements** | Event header, description, schedule, CPD info, organizer info, registration form |

**States:**
| State | Display | CTA |
|-------|---------|-----|
| Open | Normal registration | "Register" |
| Full (waitlist) | Capacity reached | "Join Waitlist" |
| Closed | Registration closed | None |
| Cancelled | Event cancelled | None |

**Workflows Supported:** Guest registration, authenticated registration, waitlist join

---

### 1.5 Certificate Verification

| Attribute | Details |
|-----------|---------|
| **URL** | `/verify/{certificate_code}` |
| **Purpose** | Public verification of certificate authenticity |

**Display Elements:**
- Certificate holder name
- Event name and date
- Issuing organizer (with logo if available)
- CPD credits (type + value)
- Issue date
- Certificate ID
- Validity status badge

**States:**
| State | Display |
|-------|---------|
| Valid | Green "Valid" badge, full details |
| Revoked | Red "Revoked" badge, revocation date |
| Not Found | Error message with support link |

**Workflows Supported:** Third-party certificate verification

---

### 1.6 Organizer Public Profile

| Attribute | Details |
|-----------|---------|
| **URL** | `/organizers/{slug}` or `/o/{slug}` |
| **Purpose** | Public-facing organizer information |

**Key Elements:**
- Logo and display name
- Bio/description
- Website link
- Social links (LinkedIn, Twitter)
- Upcoming events list
- Past events list

**States:**
- Profile public: Full display
- Profile not public: 404 page

**Workflows Supported:** Organizer discovery, event browsing by organizer

---

### 1.7 Terms of Service

| Attribute | Details |
|-----------|---------|
| **URL** | `/terms` |
| **Purpose** | Legal terms and conditions |
| **Workflows Supported** | Legal compliance |

---

### 1.8 Privacy Policy

| Attribute | Details |
|-----------|---------|
| **URL** | `/privacy` |
| **Purpose** | Privacy policy display |
| **Workflows Supported** | Legal compliance, GDPR information |

---

## 2. Authentication Screens

### 2.1 Sign Up

| Attribute | Details |
|-----------|---------|
| **URL** | `/signup` |
| **Purpose** | New account creation |

**Form Fields:**
| Field | Type | Required | Validation |
|-------|------|----------|------------|
| Email | Email input | Yes | Valid email format |
| Password | Password input | Yes | 8+ characters |
| Confirm Password | Password input | Yes | Must match password |
| Terms | Checkbox | Yes | Must be checked |

**Additional Elements:**
- "Continue with Google" OAuth button
- Password strength indicator
- Link: "Already have an account? Login"

**Post-Submit:** Redirect to email verification pending screen

**Workflows Supported:** New user registration

---

### 2.2 Login

| Attribute | Details |
|-----------|---------|
| **URL** | `/login` |
| **Purpose** | User authentication |

**Form Fields:**
| Field | Type | Required |
|-------|------|----------|
| Email | Email input | Yes |
| Password | Password input | Yes |
| Remember me | Checkbox | No |

**Additional Elements:**
- "Continue with Google" OAuth button
- Links: "Forgot password?", "Sign up"

**Post-Login Routing:**
| Scenario | Redirect To |
|----------|-------------|
| Default | Dashboard |
| Pending registration | Complete registration |
| First-time organizer | Onboarding flow |
| Had pending certificate claim | Dashboard (certificates linked) |

**Workflows Supported:** User authentication, session creation

---

### 2.3 Email Verification Pending

| Attribute | Details |
|-----------|---------|
| **URL** | `/verify-email` |
| **Purpose** | Prompt user to check email |

**Key Elements:**
- Instructions message
- Email address display (masked)
- "Resend Email" button (with cooldown timer)
- "Wrong email? Start over" link

**Workflows Supported:** Email verification flow

---

### 2.4 Email Verification Success

| Attribute | Details |
|-----------|---------|
| **URL** | `/verify-email?token={token}` (redirect target) |
| **Purpose** | Confirm email verified |

**Key Elements:**
- Success message with checkmark
- "Continue to Profile Setup" button

**Workflows Supported:** Email verification completion

---

### 2.5 Forgot Password

| Attribute | Details |
|-----------|---------|
| **URL** | `/forgot-password` |
| **Purpose** | Initiate password reset |

**Form Fields:**
| Field | Type | Required |
|-------|------|----------|
| Email | Email input | Yes |

**Success State:** "If an account exists, you'll receive an email"

**Link:** "Back to Login"

**Workflows Supported:** Password recovery initiation

---

### 2.6 Reset Password

| Attribute | Details |
|-----------|---------|
| **URL** | `/reset-password?token={token}` |
| **Purpose** | Set new password |

**Form Fields:**
| Field | Type | Required | Validation |
|-------|------|----------|------------|
| New Password | Password input | Yes | 8+ characters |
| Confirm Password | Password input | Yes | Must match |

**Additional Elements:**
- Password strength indicator
- Match validation feedback

**States:**
| State | Display |
|-------|---------|
| Valid token | Password form |
| Expired/invalid token | Error message + "Request new link" |

**Workflows Supported:** Password reset completion

---

## 3. Attendee Screens

### 3.1 Attendee Dashboard

| Attribute | Details |
|-----------|---------|
| **URL** | `/dashboard` |
| **Purpose** | Attendee home - certificates and events overview |

**Sections:**
| Section | Content |
|---------|---------|
| Header | "Welcome, [First Name]" |
| Upcoming Events Card | Next 1-2 registered events with countdown |
| CPD Summary Card | Total credits this year by type |
| Recent Certificates | Last 3-5 certificates |
| Quick Actions | "Browse Events", "View All Certificates" |

**Empty State (New User):**
```
Welcome to [Platform]!
────────────────────────
Your certificates will appear here when organizers issue them.

In the meantime:
• Complete your profile to ensure certificates show your credentials
• Browse upcoming events

[Complete Profile]  [Browse Events]
```

**Workflows Supported:** Dashboard overview, navigation hub

---

### 3.2 My Events (Attendee)

| Attribute | Details |
|-----------|---------|
| **URL** | `/events` |
| **Purpose** | List of registered events |

**Tabs:**
| Tab | Content |
|-----|---------|
| Upcoming | Future registered events |
| Past | Completed events with certificate status |

**Event Card Elements:**
- Event name
- Organizer
- Date/time
- Status badge (Registered, Attended, etc.)

**Card Actions:**
- "View Details"
- "Add to Calendar"
- "Cancel Registration"

**Past Events Tab Additional:**
- Certificate status indicator (Issued / Pending / Not Eligible)
- Link to certificate if issued

**Empty State:** "No upcoming events. Browse events to register."

**Workflows Supported:** Event management, registration cancellation

---

### 3.3 My Event Detail (Attendee)

| Attribute | Details |
|-----------|---------|
| **URL** | `/events/{uuid}` |
| **Purpose** | Single event details for attendee |

**Key Elements:**
- Event info header
- Zoom join link (when available)
- Schedule/agenda
- Materials/resources
- Learning modules (if enabled)
- Recordings (if available)

**States:**
| State | Display | Primary Action |
|-------|---------|----------------|
| Upcoming | Countdown timer | "Add to Calendar" |
| Live | Live indicator | "Join Meeting" (prominent) |
| Past | Completed badge | "View Certificate" / "Watch Recording" |

**Actions:**
- "Join Meeting" (Zoom link)
- "Add to Calendar"
- "Cancel Registration"
- "View Certificate"

**Workflows Supported:** Event participation, meeting access

---

### 3.4 Certificates Dashboard

| Attribute | Details |
|-----------|---------|
| **URL** | `/certificates` |
| **Purpose** | View all earned certificates |

**Header Elements:**
- "My Certificates" title
- Summary bar: Total certificates, Total CPD credits

**Filters:**
| Filter | Options |
|--------|---------|
| Date Range | This Year, Last Year, All Time, Custom |
| Organizer | Dropdown of orgs that issued certs |
| CPD Type | CME, CLE, CPE, General, etc. |
| Search | Event name, organizer name |

**View Toggle:** Grid / List

**Grid View Card:**
- Thumbnail preview
- Event name
- Date
- CPD badge

**List View Columns:**
- Event
- Organizer
- Date
- CPD Type
- Credits
- Actions

**Actions:** View, Download, Share

**Empty State:**
```
No Certificates Yet
───────────────────
Certificates you earn will appear here automatically.

When you attend events and organizers issue certificates,
they'll be linked to your account via your email address.
```

**Workflows Supported:** Certificate browsing, downloading, sharing

---

### 3.5 Certificate Detail (Attendee)

| Attribute | Details |
|-----------|---------|
| **URL** | `/certificates/{uuid}` |
| **Purpose** | View single certificate |

**Key Elements:**
- Certificate preview/PDF viewer
- Event details (name, date, organizer)
- CPD info (type, credits)
- Metadata (issued date, certificate ID)
- Privacy toggle

**Actions:**
| Action | Description |
|--------|-------------|
| Download PDF | Download certificate file |
| Copy Share Link | Copy verification URL |
| View Verification | Open public verification page |
| Share to LinkedIn | Direct LinkedIn share |

**Privacy Toggle:** Allow/disallow public verification

**Workflows Supported:** Certificate viewing, sharing, privacy management

---

### 3.6 CPD Tracking Dashboard

| Attribute | Details |
|-----------|---------|
| **URL** | `/cpd` or `/certificates/cpd` |
| **Purpose** | Track progress toward CPD requirements |

**Key Elements:**
- Summary cards by credit type
- Progress bars (earned vs required)
- Period selector
- Breakdown table

**Period Options:**
- Current year
- Last year
- Custom range

**Progress Display:**
| Element | Display |
|---------|---------|
| Progress Bar | Visual earned/required |
| Numbers | "15 / 20 credits earned" |
| Status | On track / Behind / Completed |

**Export:** Download CPD summary report (PDF/CSV)

**Workflows Supported:** CPD progress monitoring, reporting

---

### 3.7 Event Registration Form

| Attribute | Details |
|-----------|---------|
| **URL** | `/events/{slug}/register` (or modal on event page) |
| **Purpose** | Complete registration for an event |

**Form Fields:**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| Full Name | Text | Yes | Pre-filled if logged in |
| Email | Email | Yes | Pre-filled if logged in |
| Professional Title | Text | No | |
| Organization | Text | No | |
| Custom Fields | Various | Varies | Event-specific |

**Guest Mode:** Available if `allow_guest_registration=true`

**Confirmation:** Success message with:
- Registration confirmation
- Calendar add option (.ics download)
- "View My Events" link

**Workflows Supported:** Event registration (authenticated and guest)

---

### 3.8 Waitlist Position View

| Attribute | Details |
|-----------|---------|
| **URL** | Part of event detail |
| **Purpose** | Show waitlist status |

**Key Elements:**
- Position number (#1, #2, etc.)
- Estimated wait message
- Notification promise: "You'll be notified when a spot opens"
- "Leave Waitlist" button

**Workflows Supported:** Waitlist management

---

### 3.9 Attendee Learning Dashboard

| Attribute | Details |
|-----------|---------|
| **URL** | `/events/{uuid}/learning` or `/learning/{registration_uuid}` |
| **Purpose** | View learning progress for an event |

**Key Elements:**
- Overall progress bar
- Module list with completion status
- Assignment status summary
- Certificate eligibility progress

**Module Card:**
- Title
- Progress (e.g., "3/5 completed")
- Status badge (Not started / In progress / Completed)

**Assignment Card:**
- Title
- Due date
- Status (Not started / In progress / Submitted / Graded)
- Score (if graded)

**Workflows Supported:** Learning progress tracking

---

### 3.10 Module Content Viewer (Attendee)

| Attribute | Details |
|-----------|---------|
| **URL** | `/learning/{registration_uuid}/modules/{module_uuid}` |
| **Purpose** | View and complete module content |

**Layout:**
- Left sidebar: Content list
- Main area: Content viewer
- Top: Module title, progress

**Content Types:**
| Type | Viewer |
|------|--------|
| Video | Embedded player with progress tracking |
| Document | PDF viewer |
| Text | HTML content display |
| External Link | Opens in new tab |
| Quiz | Quiz interface |

**Navigation:**
- Previous/Next content buttons
- "Mark as Complete" button (for non-auto-tracked content)

**Progress Tracking:**
- Video: Auto-tracked (watch time)
- Documents: Manual completion
- Links: Click tracking
- Quiz: Score-based

**Workflows Supported:** Content consumption, progress tracking

---

### 3.11 Assignment Submission (Attendee)

| Attribute | Details |
|-----------|---------|
| **URL** | `/learning/{registration_uuid}/assignments/{assignment_uuid}` |
| **Purpose** | View assignment and submit work |

**Key Elements:**
- Assignment title and instructions
- Rubric (if provided)
- Submission form
- Submission history

**Submission Types:**
| Type | Input |
|------|-------|
| Text | Rich text editor |
| File | File upload (PDF, DOCX, images) |
| Link | URL input |
| Completion Only | Checkbox |

**States:**
| State | Display | Actions |
|-------|---------|---------|
| Not Started | Instructions only | "Start Assignment" |
| Draft | Draft content | "Save Draft", "Submit" |
| Submitted | Submission content (read-only) | "Waiting for review" |
| Revision Requested | Feedback shown | "Resubmit" |
| Approved | Score/feedback | View only |
| Rejected | Score/feedback | View only |

**Workflows Supported:** Assignment submission, resubmission

---

### 3.12 Recording Viewer (Attendee)

| Attribute | Details |
|-----------|---------|
| **URL** | `/events/{uuid}/recordings/{recording_uuid}` |
| **Purpose** | Watch event recordings |

**Key Elements:**
- Video player
- Playback controls
- Chapter markers (if available)
- Transcript (if available)
- Progress indicator

**Progress Tracking:**
- Watch position saved (resume capability)
- Completion tracked (for certificate eligibility)

**Access States:**
| State | Display |
|-------|---------|
| Available | Full player |
| Not Available (didn't attend) | Access denied message |
| Processing | "Recording being processed" |

**Workflows Supported:** Recording playback, progress tracking

---

## 4. Organizer Screens

### 4.1 Organizer Dashboard

| Attribute | Details |
|-----------|---------|
| **URL** | `/dashboard` (organizer view) |
| **Purpose** | Organizer home - events and activity overview |

**Stats Row (4 Cards):**
| Card | Metric |
|------|--------|
| Total Events | All-time event count |
| Upcoming | Events in future |
| Total Attendees | Sum of all attendees |
| Certificates Issued | Total certificates |

**Sections:**
- Upcoming events (next 3) with quick stats
- Recent activity feed (registrations, certificates)
- Action prompts (contextual alerts)

**Action Prompts Examples:**
- "3 events need attendance review"
- "15 certificates ready to issue"
- "Payment method expiring soon"

**First-Time State:** Onboarding checklist instead of stats

**Workflows Supported:** Overview, quick navigation

---

### 4.2 Events List (Organizer)

| Attribute | Details |
|-----------|---------|
| **URL** | `/events` |
| **Purpose** | Manage all events |

**Header:** "My Events" + "Create Event" button

**Tabs:**
| Tab | Content |
|-----|---------|
| Upcoming | Future published/live events |
| Past | Completed/closed events |
| Drafts | Unpublished events |
| Cancelled | Cancelled events |

**Filters:**
- Date range
- Status
- Search (title)

**View Toggle:** List / Calendar

**Event Row Elements:**
| Column | Content |
|--------|---------|
| Title | Event name |
| Date/Time | Start date and time |
| Status | Badge (Draft, Published, Live, Completed, Cancelled) |
| Registered | Registration count |
| Attended | Attendance count |
| Certificates | Issued count |
| Actions | Edit, Duplicate, View |

**Bulk Actions:**
- Delete drafts
- Export (CSV)

**Calendar View:**
- Monthly calendar
- Event dots on dates
- Click date to see events

**Workflows Supported:** Event management, bulk operations

---

### 4.3 Create Event

| Attribute | Details |
|-----------|---------|
| **URL** | `/events/new` |
| **Purpose** | Create new event |

#### Section 1: Basic Info

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| Title | Text | Yes | 3-100 characters |
| Description | Rich Text | No | Max 5000 characters |
| Event Type | Dropdown | Yes | Webinar, Workshop, Course, Conference, Training, Other |

#### Section 2: Date & Time

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| Start Date | Date picker | Yes | Must be future |
| Start Time | Time picker | Yes | — |
| Duration | Dropdown | Yes | 15min - 8hrs |
| Timezone | Dropdown | Yes | Auto-detect default |

#### Section 3: Zoom Settings

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| Create Zoom Meeting | Toggle | On | Auto-create meeting |
| Waiting Room | Toggle | On | Enable waiting room |
| Passcode | Toggle + Input | Auto | Auto-generate or custom |
| Allow Join Before Host | Toggle | Off | — |

**Zoom Not Connected State:**
```
⚠ Zoom Not Connected
Connect your Zoom account to automatically create meetings.
[Connect Zoom]

Or manually add meeting details after creating the event.
```

#### Section 4: Registration Settings

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| Enable Registration | Toggle | On | Accept registrations |
| Capacity | Number | Unlimited | Max attendees |
| Registration Deadline | DateTime | None | Auto-close date |
| Enable Waitlist | Toggle | Off | When capacity reached |
| Allow Guest Registration | Toggle | On | Register without account |

#### Section 5: CPD Configuration

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| Enable CPD | Toggle | — | Show CPD on certificates |
| Credit Type | Dropdown | If enabled | CME, CLE, CPE, etc. |
| Credit Value | Number | If enabled | Credit hours/units |
| Accreditation Note | Text | No | Additional accreditation info |

#### Section 6: Certificate Settings

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| Enable Certificates | Toggle | On | Issue certificates |
| Template | Dropdown | Default | Select template |
| Auto-Issue | Toggle | Off | Issue automatically after event |

#### Section 7: Advanced

| Field | Type | Notes |
|-------|------|-------|
| Custom Fields | Builder | Add registration fields |
| Visibility | Radio | Public / Unlisted / Private |

**Actions:**
- "Save Draft" — Save without publishing
- "Publish" — Make event live

**Workflows Supported:** Single event creation

---

### 4.4 Create Multi-Session Event

| Attribute | Details |
|-----------|---------|
| **URL** | `/events/new?type=multi-session` |
| **Purpose** | Create event series/course |

**Additional Elements:**

**Event Format Selector:**
- Single Session (default)
- Multi-Session (course/series)

**Sessions List:**
| Column | Content |
|--------|---------|
| # | Session number |
| Title | Session title |
| Date/Time | Session date and time |
| Duration | Session length |
| Speaker | Speaker name (optional) |
| Required | Required for certificate (toggle) |
| Actions | Edit, Delete |

**Add Session Modal:**
| Field | Type | Required |
|-------|------|----------|
| Title | Text | Yes |
| Date | Date picker | Yes |
| Time | Time picker | Yes |
| Duration | Dropdown | Yes |
| Speaker Name | Text | No |
| Speaker Bio | Textarea | No |
| Required | Checkbox | No |

**Recurring Setup:**
| Field | Options |
|-------|---------|
| Pattern | Weekly, Bi-weekly, Custom |
| Days | Day selection |
| Count | Number of sessions |

**Attendance Settings:**
| Setting | Options |
|---------|---------|
| Requirement Type | % time, % sessions, All sessions, Minimum sessions |
| Threshold | Percentage or count |

**Workflows Supported:** Multi-session event creation

---

### 4.5 Edit Event

| Attribute | Details |
|-----------|---------|
| **URL** | `/events/{uuid}/edit` |
| **Purpose** | Modify existing event |

**Key Elements:**
- Same form as Create Event, pre-populated
- Status badge display
- Field restrictions after publish

**Restricted After Publish:**
- Event type (single/multi-session)
- Cannot reduce capacity below current registrations

**Danger Zone:**
- "Cancel Event" button with confirmation modal

**Workflows Supported:** Event modification

---

### 4.6 Event Detail (Organizer) - Overview Tab

| Attribute | Details |
|-----------|---------|
| **URL** | `/events/{uuid}` |
| **Purpose** | Event management hub |

**Header:**
- Event title
- Status badge
- Date/time
- Quick stats (Registered, Attended, Certificates)

**Tabs:**
| Tab | Purpose | Visibility |
|-----|---------|------------|
| Overview | Summary and quick actions | Always |
| Registrations | Manage registrations | Always |
| Attendance | Review attendance | After event |
| Modules | Learning content | If modules_enabled |
| Recordings | Manage recordings | After event |
| Certificates | Issue certificates | Always |
| Settings | Event settings | Always |

**Overview Content:**
- Event info summary
- Zoom details (meeting ID, passcode, host link)
- Quick actions

**Quick Actions:**
- Edit event
- Send reminder
- Copy invite link
- View public page

**Workflows Supported:** Event overview, quick actions

---

### 4.7 Event Detail - Registrations Tab

| Attribute | Details |
|-----------|---------|
| **URL** | `/events/{uuid}/registrations` |
| **Purpose** | Manage event registrations |

**Sub-tabs:**
| Tab | Content |
|-----|---------|
| Confirmed | Confirmed registrations |
| Waitlist | Waitlisted registrations |
| Cancelled | Cancelled registrations |

**Table Columns:**
| Column | Content |
|--------|---------|
| Name | Attendee name |
| Email | Attendee email |
| Registration Date | When registered |
| Status | Badge |
| Actions | Context menu |

**Actions:**
- Add attendee (manual)
- Import CSV
- Remove attendee
- Resend invite

**Bulk Actions:**
- Select all
- Send bulk reminder
- Export CSV

**Search:** Filter by name/email

**Add Attendee Modal:**
| Field | Type | Required |
|-------|------|----------|
| Email | Email | Yes |
| Full Name | Text | No |
| Send Invite Email | Checkbox | No |

**Workflows Supported:** Registration management, bulk import

---

### 4.8 Event Detail - Waitlist Management

| Attribute | Details |
|-----------|---------|
| **URL** | `/events/{uuid}/registrations?tab=waitlist` |
| **Purpose** | Manage waitlist |

**Table Columns:**
| Column | Content |
|--------|---------|
| Position | #1, #2, #3... |
| Name | Attendee name |
| Email | Attendee email |
| Joined | When joined waitlist |
| Actions | Promote, Remove |

**Actions:**
- Promote (individual) — Move to confirmed
- Remove — Remove from waitlist

**Bulk Actions:**
- "Promote All Available" — Fill available spots
- "Promote Selected" — Promote checked

**Auto-Promote Settings Modal:**
| Field | Type | Notes |
|-------|------|-------|
| Enable Auto-Promote | Toggle | Auto-promote when spots open |
| Notify on Promotion | Toggle | Email notification |

**Workflows Supported:** Waitlist promotion, auto-promotion configuration

---

### 4.9 Event Detail - Attendance Tab

| Attribute | Details |
|-----------|---------|
| **URL** | `/events/{uuid}/attendance` |
| **Purpose** | Review and manage attendance |

**Table Columns:**
| Column | Content |
|--------|---------|
| Name | Attendee name |
| Email | Attendee email |
| Join Time | First join timestamp |
| Leave Time | Last leave timestamp |
| Duration | Total time in meeting |
| Attendance % | Percentage of event attended |
| Eligible | Yes/No badge |
| Actions | Override |

**Manual Override Actions:**
- Mark as attended (override to eligible)
- Mark as not attended (override to ineligible)

**Threshold Setting:**
| Field | Type | Default |
|-------|------|---------|
| Minimum Attendance | Percentage | 80% |

**Unmatched Section:**
- Zoom participants not matched to registrations
- Option to match manually

**Import:**
- Manual CSV import (fallback for non-Zoom events)

**Workflows Supported:** Attendance review, eligibility override

---

### 4.10 Event Detail - Certificates Tab

| Attribute | Details |
|-----------|---------|
| **URL** | `/events/{uuid}/certificates` |
| **Purpose** | Issue and manage certificates |

**Status Summary:**
| Status | Meaning |
|--------|---------|
| Not Issued | No certificates issued yet |
| Partially Issued | Some eligible attendees have certificates |
| All Issued | All eligible attendees have certificates |

**Eligible List:**
- Checkbox selection
- Name, email, attendance status
- "Issue" action (individual)

**Template Selection:**
- Dropdown of available templates
- Preview button

**Bulk Actions:**
- "Issue to All Eligible"
- "Issue Selected"
- "Preview" (sample certificate)

**Issued List:**
| Column | Content |
|--------|---------|
| Attendee | Name |
| Issued Date | When issued |
| Status | Issued/Revoked |
| Actions | View, Download, Revoke |

**Revoke Flow:**
1. Click "Revoke"
2. Enter reason (modal)
3. Confirm revocation
4. Attendee notified

**Workflows Supported:** Certificate issuance, revocation

---

### 4.11 Event Detail - Modules Tab

| Attribute | Details |
|-----------|---------|
| **URL** | `/events/{uuid}/modules` |
| **Purpose** | Manage learning modules |
| **Visibility** | Only shown if `modules_enabled=true` |

**Header:**
- "Modules (X)" count
- "Add Module" button

**Module Cards:**
| Element | Content |
|---------|---------|
| Drag Handle | Reorder |
| Title | Module title |
| Description | Preview text |
| Content Count | "5 items • 45 min" |
| Status Badge | Draft/Published/Scheduled |
| Actions | Edit, Duplicate, Delete, Publish/Unpublish |

**Reorder:** Drag-and-drop modules

**Empty State:**
```
No Modules Yet
──────────────
Add modules to organize your learning content into 
sections, weeks, or topics.

[+ Add First Module]
```

**Workflows Supported:** Module management

---

### 4.12 Module Editor

| Attribute | Details |
|-----------|---------|
| **URL** | `/events/{uuid}/modules/{module_uuid}` or `/events/{uuid}/modules/new` |
| **Purpose** | Create/edit module |

**Layout:** Two-column
- Left: Module settings
- Right: Content items list

**Settings Fields:**
| Field | Type | Required |
|-------|------|----------|
| Title | Text | Yes |
| Description | Textarea | No |
| Release Type | Radio | Yes |
| Scheduled Date | DateTime | If scheduled |
| Prerequisite Module | Dropdown | No |

**Release Types:**
| Type | Behavior |
|------|----------|
| Immediately | Available when published |
| Scheduled Date | Available at specific date/time |
| After Previous Module | Available after prior module completed |
| Days After Registration | Available X days after user registers |

**Content List:**
- Draggable items
- Add content button
- Each item shows: Icon, Title, Duration/size, Required badge

**Actions:**
- "Save Draft"
- "Publish"

**Workflows Supported:** Module creation, content organization

---

### 4.13 Add Content Modal

| Attribute | Details |
|-----------|---------|
| **URL** | Modal on Module Editor |
| **Purpose** | Add content to module |

**Content Type Selector:**
| Type | Icon |
|------|------|
| Video | 📹 |
| Document | 📄 |
| Link | 🔗 |
| Text | 📝 |
| Audio | 🎵 |
| Slides | 📊 |
| Quiz | ❓ |
| Recording | 🎬 |

**Type-Specific Fields:**

**Video:**
| Field | Type | Required |
|-------|------|----------|
| Title | Text | Yes |
| Video URL | URL | Yes |
| Duration | Auto-detect | — |
| Required | Toggle | No |

**Document:**
| Field | Type | Required |
|-------|------|----------|
| Title | Text | Yes |
| File | Upload | Yes |
| Required | Toggle | No |

**Link:**
| Field | Type | Required |
|-------|------|----------|
| Title | Text | Yes |
| URL | URL | Yes |
| Description | Text | No |
| Open in New Tab | Toggle | Yes (default on) |

**Text:**
| Field | Type | Required |
|-------|------|----------|
| Title | Text | Yes |
| Content | Rich Text | Yes |

**Recording:**
| Field | Type | Required |
|-------|------|----------|
| Select Recording | Dropdown | Yes |

**Workflows Supported:** Content creation

---

### 4.14 Event Detail - Assignments Tab

| Attribute | Details |
|-----------|---------|
| **URL** | `/events/{uuid}/assignments` |
| **Purpose** | Manage assignments |
| **Visibility** | Only shown if `assignments_enabled=true` |

**Header:**
- "Assignments (X)" count
- "Create Assignment" button

**Assignment Row:**
| Column | Content |
|--------|---------|
| Title | Assignment title |
| Module | Linked module (if any) |
| Due Date | Due date/time |
| Submissions | "12/45 submitted • 8 graded" |
| Status | Draft/Published/Grading/Completed |
| Actions | Edit, View Submissions, Duplicate, Delete |

**Workflows Supported:** Assignment management

---

### 4.15 Assignment Editor

| Attribute | Details |
|-----------|---------|
| **URL** | `/events/{uuid}/assignments/{assignment_uuid}` or `new` |
| **Purpose** | Create/edit assignment |

#### Section 1: Basic Info

| Field | Type | Required |
|-------|------|----------|
| Title | Text | Yes |
| Description | Rich Text | No |
| Instructions | Rich Text | Yes |
| Module | Dropdown | No |

#### Section 2: Submission Settings

| Field | Type | Options |
|-------|------|---------|
| Submission Type | Radio | File, Text, Link, File or Text, Quiz, Completion Only |
| Allowed File Types | Multi-select | PDF, DOCX, Images, etc. |
| Max File Size | Dropdown | 5MB, 10MB, 25MB, 50MB |

#### Section 3: Deadlines

| Field | Type | Notes |
|-------|------|-------|
| Due Date | DateTime | When assignment is due |
| Late Submissions | Toggle | Allow late submissions |
| Late Penalty | Number | % deduction per day |

#### Section 4: Grading

| Field | Type | Options |
|-------|------|---------|
| Grading Type | Radio | Pass/Fail, Points, Rubric |
| Max Points | Number | If points-based |
| Passing Score | Number | Minimum to pass |

#### Section 5: Rubric Builder (if rubric grading)

| Element | Content |
|---------|---------|
| Criterion | Name, Description, Max Points |
| Levels | Label, Points, Description per level |
| Add Criterion | Button |

#### Section 6: Options

| Field | Type | Default |
|-------|------|---------|
| Required for Certificate | Toggle | Yes |
| Allow Resubmission | Toggle | No |
| Max Attempts | Number | 1 |

**Actions:**
- "Save Draft"
- "Publish"

**Workflows Supported:** Assignment creation

---

### 4.16 Assignment Submissions View (Organizer)

| Attribute | Details |
|-----------|---------|
| **URL** | `/events/{uuid}/assignments/{assignment_uuid}/submissions` |
| **Purpose** | Review and grade submissions |

**Filter Tabs:**
| Tab | Content |
|-----|---------|
| All | All submissions |
| Pending Review | Awaiting grading |
| Graded | Already graded |

**Table Columns:**
| Column | Content |
|--------|---------|
| Attendee | Name |
| Submitted At | Timestamp |
| Status | Pending/Approved/Rejected/Revision Requested |
| Score | Points or Pass/Fail |
| Actions | View/Grade |

**Bulk Actions:**
- Export submissions

**Workflows Supported:** Submission review queue

---

### 4.17 Grading Interface

| Attribute | Details |
|-----------|---------|
| **URL** | `/events/{uuid}/submissions/{submission_uuid}/grade` or modal |
| **Purpose** | Grade individual submission |

**Layout:** Two-column
- Left: Submission content
- Right: Grading form

**Submission Display:**
- Text content (if text submission)
- File preview/download (if file submission)
- Link (if link submission)

**Grading Form:**
| Field | Type | Notes |
|-------|------|-------|
| Score | Number | If points-based |
| Rubric Scoring | Per-criterion | If rubric |
| Feedback | Rich Text | Comments for student |

**Actions:**
| Action | Effect |
|--------|--------|
| Approve | Mark as passed/approved |
| Request Revision | Return for resubmission |
| Reject | Mark as failed/rejected |

**Navigation:**
- Previous/Next submission buttons

**Workflows Supported:** Assignment grading

---

### 4.18 Event Detail - Recordings Tab

| Attribute | Details |
|-----------|---------|
| **URL** | `/events/{uuid}/recordings` |
| **Purpose** | Manage event recordings |

**Recording List:**
| Column | Content |
|--------|---------|
| Thumbnail | Preview image |
| Title | Recording title |
| Duration | Length |
| Date | Recording date |
| Status | Processing/Available/Published |
| Views | View count |
| Actions | Settings, Publish/Unpublish, Delete |

**Status Badges:**
| Status | Meaning |
|--------|---------|
| Processing | Being processed by Zoom |
| Available | Ready but not published |
| Published | Visible to attendees |

**Analytics Per Recording:**
- View count
- Unique viewers
- Average watch time

**Empty State:**
```
No Recordings Yet
─────────────────
Recordings will appear here after the event when
Zoom cloud recording is enabled.
```

**Workflows Supported:** Recording management

---

### 4.19 Recording Settings Modal

| Attribute | Details |
|-----------|---------|
| **URL** | Modal on Recordings tab |
| **Purpose** | Configure recording access |

**Fields:**
| Field | Type | Options |
|-------|------|---------|
| Title | Text | Editable |
| Description | Textarea | Optional |
| Access Level | Radio | See below |
| Published | Toggle | Visible to attendees |

**Access Levels:**
| Level | Who Can Access |
|-------|----------------|
| Registrants Only | Anyone who registered |
| Attendees Only | Only those who attended live |
| Certificate Holders | Only those who received certificate |
| Public | Anyone with link |

**Workflows Supported:** Recording access configuration

---

### 4.20 Event Detail - Settings Tab

| Attribute | Details |
|-----------|---------|
| **URL** | `/events/{uuid}/settings` |
| **Purpose** | Event-specific settings |

**Sections:**

**Registration Settings:**
- Enable/disable registration
- Capacity changes
- Deadline changes

**Notification Settings:**
- Reminder schedule
- Custom reminder messages

**Custom Fields Builder:**
- Add/edit/reorder registration fields
- Field types: Text, Email, Phone, Dropdown, Checkbox, Textarea

**Danger Zone:**
- Cancel event (with modal)
- Delete draft (if draft status)

**Workflows Supported:** Event configuration

---

### 4.21 Live Event Monitor

| Attribute | Details |
|-----------|---------|
| **URL** | `/events/{uuid}/live` |
| **Purpose** | Real-time event monitoring |

**Header:**
- Event name
- LIVE indicator (pulsing)
- Current time

**Current Count:**
- Large number display
- "Currently in meeting"

**Activity Feed:**
- Real-time join/leave log
- Timestamp + Name + Action (Joined/Left)

**Attendee List:**
- Who's currently in meeting
- Duration so far per person

**Refresh:**
- Auto-refresh (configurable interval)
- Manual refresh button

**Workflows Supported:** Live event monitoring

---

### 4.22 Templates Management

| Attribute | Details |
|-----------|---------|
| **URL** | `/templates` |
| **Purpose** | Manage certificate templates |

**Display:** Grid of template cards

**Template Card:**
| Element | Content |
|---------|---------|
| Preview | Thumbnail image |
| Name | Template name |
| Created | Creation date |
| Usage | "Used in X certificates" |
| Default Badge | If set as default |
| Actions | Edit, Duplicate, Delete, Set as default |

**Header Action:** "Add Template" button

**Workflows Supported:** Template management

---

### 4.23 Template Editor

| Attribute | Details |
|-----------|---------|
| **URL** | `/templates/{uuid}` or `/templates/new` |
| **Purpose** | Create/edit certificate template |

**Upload Section:**
- Drag-drop zone
- File picker button
- Accepts: PDF, PNG, JPG

**Field Placement:**
- Draggable field tokens
- Position on template preview
- Resize handles

**Available Fields:**
| Field | Token |
|-------|-------|
| Attendee Name | `{{attendee_name}}` |
| Event Title | `{{event_title}}` |
| Event Date | `{{event_date}}` |
| CPD Credits | `{{cpd_credits}}` |
| CPD Type | `{{cpd_type}}` |
| Certificate ID | `{{certificate_id}}` |
| Organizer Name | `{{organizer_name}}` |
| Signature | `{{signature}}` |

**Field Properties:**
| Property | Options |
|----------|---------|
| Font | Dropdown |
| Size | Number |
| Color | Color picker |
| Alignment | Left/Center/Right |

**Preview:**
- Toggle sample data
- Shows rendered example

**Settings:**
| Field | Type |
|-------|------|
| Template Name | Text |
| Set as Default | Checkbox |

**Version Warning:**
```
⚠ This template has been used to issue 45 certificates.
Saving will create a new version. Existing certificates
will not be affected.
```

**Actions:**
- Save
- Cancel

**Workflows Supported:** Template design

---

### 4.24 Contacts Management

| Attribute | Details |
|-----------|---------|
| **URL** | `/contacts` |
| **Purpose** | Manage contact lists |

**Contact Lists View:**
| Column | Content |
|--------|---------|
| Name | List name |
| Contacts | Contact count |
| Created | Creation date |
| Actions | Edit, Delete, Export |

**Header Actions:**
- "Create List" button
- "Manage Tags" link

**Tags Section:**
- View all tags
- Create/edit/delete tags
- Tag usage counts

**Workflows Supported:** Contact list management

---

### 4.25 Contact List Detail

| Attribute | Details |
|-----------|---------|
| **URL** | `/contacts/{list_uuid}` |
| **Purpose** | View/manage contacts in a list |

**Contacts Table:**
| Column | Content |
|--------|---------|
| Name | Contact name |
| Email | Contact email |
| Title | Professional title |
| Organization | Company/org |
| Tags | Tag badges |
| Added | Date added |
| Actions | Edit, Remove |

**Actions:**
- Add contact (manual)
- Import CSV
- Remove selected
- Edit contact

**Bulk Actions:**
- Export
- Delete selected
- Add tags to selected

**Search/Filter:**
- By name
- By email
- By tags

**Workflows Supported:** Contact management

---

### 4.26 CSV Import Modal

| Attribute | Details |
|-----------|---------|
| **URL** | Modal on Contact List or Registrations |
| **Purpose** | Bulk import contacts/registrations |

**Step 1: Upload**
- File drop zone
- Accepts: CSV, XLSX, XLS

**Step 2: Column Mapping**
| Your Column | Maps To |
|-------------|---------|
| [Dropdown] | Email (required) |
| [Dropdown] | Name |
| [Dropdown] | Title |
| [Dropdown] | Organization |
| [Dropdown] | Phone |
| [Dropdown] | Tags |

**Step 3: Preview**
- First 5 rows displayed
- Validation indicators
- Error highlighting

**Step 4: Import**
- Progress bar
- Success/error count
- "View Results" button

**Error Handling:**
- Invalid rows shown
- Options: Skip, Fix, Cancel

**Workflows Supported:** Bulk contact import

---

### 4.27 Reports Dashboard

| Attribute | Details |
|-----------|---------|
| **URL** | `/reports` |
| **Purpose** | Analytics and reporting |

**Date Range Selector:**
- Presets: This Month, Last Month, This Year, Last Year, Custom
- Custom date picker

**Summary Stats Cards:**
| Stat | Value |
|------|-------|
| Events Held | Count |
| Total Attendees | Count |
| Certificates Issued | Count |
| Avg Attendance Rate | Percentage |

**Events Table:**
| Column | Content |
|--------|---------|
| Event Name | Title with link |
| Date | Event date |
| Registered | Count |
| Attended | Count |
| Attendance Rate | Percentage |
| Certificates | Issued count |

**Charts:**
- Events over time (line)
- Attendance trends (bar)
- CPD credits issued by type (pie)

**Export:**
- Download CSV
- Download PDF report

**Workflows Supported:** Analytics, reporting

---

### 4.28 Duplicate Event Modal

| Attribute | Details |
|-----------|---------|
| **URL** | Modal from event actions |
| **Purpose** | Create copy of event |

**Pre-filled Fields:**
- Title (with " (Copy)" appended)
- Description
- All settings
- Custom fields
- Template selection

**Editable Fields:**
- Title
- Date/time (required change)

**What's Copied:**
| Copied | Not Copied |
|--------|------------|
| Title/description | Registrations |
| Settings | Attendance data |
| Custom fields | Certificates |
| Template selection | Zoom meeting |
| CPD configuration | Status (reset to Draft) |

**Actions:**
- "Create Draft"
- "Cancel"

**Workflows Supported:** Event duplication

---

## 5. Settings Screens

### 5.1 Settings Layout

| Attribute | Details |
|-----------|---------|
| **URL** | `/settings/*` |
| **Purpose** | Settings navigation container |

**Sidebar Menu:**
| Item | URL | Visibility |
|------|-----|------------|
| Profile | `/settings/profile` | All |
| CPD Requirements | `/settings/cpd` | All |
| Security | `/settings/security` | All |
| Integrations | `/settings/integrations` | Organizers |
| Notifications | `/settings/notifications` | All |
| Subscription | `/settings/subscription` | Organizers |
| Account | `/settings/account` | All |

**Content Area:** Selected settings section

---

### 5.2 Profile Settings

| Attribute | Details |
|-----------|---------|
| **URL** | `/settings/profile` |
| **Purpose** | Personal profile management |

**All Users:**
| Field | Type | Required |
|-------|------|----------|
| Profile Photo | Upload | No |
| Full Name | Text | Yes |
| Professional Title | Text | No |
| Credentials | Text | No |
| Organization | Text | No |
| Bio | Textarea | No |

**Organizer-Specific:**
| Field | Type | Notes |
|-------|------|-------|
| Display Name | Text | Public organizer name |
| Logo | Upload | Shown on certificates/profile |
| Website | URL | Public link |
| LinkedIn | URL | Social link |
| Twitter | URL | Social link |
| Public Profile | Toggle | Allow public profile page |

**Workflows Supported:** Profile management

---

### 5.3 CPD Requirements Settings

| Attribute | Details |
|-----------|---------|
| **URL** | `/settings/cpd` |
| **Purpose** | Configure CPD tracking requirements |

**Header:**
- "CPD Requirements"
- "Add Requirement" button

**Requirements List:**
| Column | Content |
|--------|---------|
| Credit Type | CME, CLE, etc. |
| Annual Requirement | Hours/credits |
| Period | Calendar year, etc. |
| Progress | Progress bar |
| Actions | Edit, Delete |

**Add/Edit Requirement Modal:**
| Field | Type | Required |
|-------|------|----------|
| Credit Type | Dropdown | Yes |
| Annual Hours/Credits | Number | Yes |
| Period Type | Radio | Yes |
| Licensing Body | Text | No |
| License Number | Text | No |

**Period Types:**
- Calendar Year (Jan-Dec)
- Fiscal Year (custom start)
- Rolling 12 Months

**Progress Display:**
- Progress bar
- "X of Y credits earned"
- Percentage complete

**Workflows Supported:** CPD requirement configuration

---

### 5.4 Security Settings

| Attribute | Details |
|-----------|---------|
| **URL** | `/settings/security` |
| **Purpose** | Account security management |

**Change Password Section:**
| Field | Type | Required |
|-------|------|----------|
| Current Password | Password | Yes |
| New Password | Password | Yes |
| Confirm Password | Password | Yes |

**Change Email Section:**
- New email input
- Requires verification

**Active Sessions:**
| Column | Content |
|--------|---------|
| Device | Device type + browser |
| Location | City, Country (from IP) |
| Last Activity | Timestamp |
| Actions | "Logout" (except current) |

**Two-Factor Authentication (Phase 2):**
- Enable/disable toggle
- Setup flow

**Workflows Supported:** Password change, session management

---

### 5.5 Integrations (Organizers)

| Attribute | Details |
|-----------|---------|
| **URL** | `/settings/integrations` |
| **Purpose** | Manage external integrations |
| **Visibility** | Organizers only |

**Zoom Section:**
| State | Display |
|-------|---------|
| Not Connected | "Connect Zoom" button |
| Connected | Email, "Disconnect" button |
| Expired | Warning, affected events list, "Reconnect" button |

**Expired State:**
```
⚠ Your Zoom connection has expired
Some features may not work correctly.

Affected events:
• Event Name 1 (Jan 15)
• Event Name 2 (Jan 22)

[Reconnect Zoom]
```

**Disconnect Warning Modal:**
```
Disconnect Zoom?
────────────────
This will affect:
• Automatic meeting creation
• Attendance tracking
• Recording sync

Existing meetings will continue to work.

[Disconnect]  [Cancel]
```

**Future Integrations:**
- Placeholder for additional integrations

**Workflows Supported:** Zoom OAuth, integration management

---

### 5.6 Notification Preferences

| Attribute | Details |
|-----------|---------|
| **URL** | `/settings/notifications` |
| **Purpose** | Email notification preferences |

**All Users:**
| Category | Default |
|----------|---------|
| Event Reminders | On |
| Certificate Issued | On |
| Marketing | Off |

**Organizers Only:**
| Category | Default |
|----------|---------|
| New Registration | On |
| Attendance Summary | On |
| Payment Notifications | On |

**Format:** Toggle on/off per category

**Workflows Supported:** Notification preference management

---

### 5.7 Subscription Management

| Attribute | Details |
|-----------|---------|
| **URL** | `/settings/subscription` |
| **Purpose** | View and manage subscription |
| **Visibility** | Organizers only |

**Current Plan Section:**
| Field | Content |
|-------|---------|
| Plan Name | Starter/Professional/Enterprise |
| Price | $X/month |
| Billing Cycle | Monthly/Annual |
| Next Billing | Date |

**Usage Section:**
| Metric | Display |
|--------|---------|
| Events This Month | X of Y |
| Certificates Issued | X of Y |
| Storage Used | X of Y GB |

**Payment Method:**
- Card on file (last 4 digits)
- "Update" button

**Actions:**
- Change plan
- Update payment method
- View invoices
- Cancel subscription

**Trial Banner (if applicable):**
```
🕐 Trial ends in X days
Add a payment method to continue using organizer features.
[Add Payment Method]
```

**Workflows Supported:** Subscription management

---

### 5.8 Account Settings

| Attribute | Details |
|-----------|---------|
| **URL** | `/settings/account` |
| **Purpose** | Account-level actions |

**Export Data Section:**
- "Export My Data" button
- Triggers email with download link

**Export Contents:**
| Data | Included |
|------|----------|
| Profile | All profile information |
| Events | Events created/attended |
| Registrations | All registrations |
| Certificates | All certificates |
| Contacts | Contact lists (organizers) |

**ZIP File Structure:**
```
export_2024-01-15/
├── profile.json
├── events.json
├── registrations.json
├── certificates.json
├── contacts.json
└── certificates/
    └── [PDF files]
```

**Downgrade Section (Organizers):**
- "Downgrade to Attendee" button
- Warning about what's lost

**Downgrade Rules:**
- Cannot have active/upcoming events
- Existing events become read-only
- Certificates remain valid
- Contacts/templates archived

**Danger Zone:**
- "Delete Account" button (red)

**Delete Flow:**
1. Click "Delete Account"
2. Warning modal with consequences
3. Type "DELETE" to confirm
4. Final confirmation button
5. Account deleted, logged out

**Workflows Supported:** Data export, account deletion

---

## 6. Billing Screens

### 6.1 Upgrade to Organizer

| Attribute | Details |
|-----------|---------|
| **URL** | `/upgrade` or modal |
| **Purpose** | Convert attendee to organizer |

**Plan Selection:**
| Plan | Price | Features |
|------|-------|----------|
| Starter | $X/mo | 5 events, 100 registrations, basic |
| Professional | $X/mo | 20 events, 500 registrations, advanced |
| Enterprise | Custom | Unlimited, custom features |

**Features Comparison Table:**
| Feature | Starter | Professional | Enterprise |
|---------|---------|--------------|------------|
| Events/month | 5 | 20 | Unlimited |
| Registrations/event | 100 | 500 | Unlimited |
| Certificates/month | 500 | 2000 | Unlimited |
| Storage | 5 GB | 50 GB | Unlimited |
| Support | Email | Priority | Dedicated |

**Trial Info:**
- 14-day free trial
- No credit card required to start

**CTAs:**
- "Start Free Trial"
- "Select Plan"

**Workflows Supported:** Account upgrade

---

### 6.2 Checkout

| Attribute | Details |
|-----------|---------|
| **URL** | `/checkout` or Stripe hosted page |
| **Purpose** | Complete payment |

**Elements:**
- Plan summary
- Price breakdown
- Stripe payment form (card input)

**Payment Methods:**
- Credit/debit card (via Stripe Elements)

**Success Redirect:**
- Dashboard with success message
- Onboarding flow (if first time)

**Workflows Supported:** Payment processing

---

### 6.3 Billing Portal

| Attribute | Details |
|-----------|---------|
| **URL** | Stripe Billing Portal (external) |
| **Purpose** | Self-service billing management |

**Features:**
- Update payment method
- View invoice history
- Download invoices
- Cancel subscription

**Access:**
- Button in Subscription settings
- Redirects to Stripe-hosted portal

**Workflows Supported:** Self-service billing

---

### 6.4 Invoice History

| Attribute | Details |
|-----------|---------|
| **URL** | `/settings/subscription/invoices` |
| **Purpose** | View past invoices |

**Table Columns:**
| Column | Content |
|--------|---------|
| Date | Invoice date |
| Amount | Dollar amount |
| Status | Paid/Pending/Failed |
| Actions | Download PDF, View in Stripe |

**Workflows Supported:** Invoice access

---

### 6.5 Payment Failed Banner

| Attribute | Details |
|-----------|---------|
| **URL** | Banner on all pages |
| **Purpose** | Alert to payment issue |

**Display:**
```
⚠ Payment failed. Update your payment method to avoid service interruption.
[Update Payment Method]
```

**Grace Period:**
- 7 days before service impact
- Daily email reminders

**Workflows Supported:** Payment recovery

---

## 7. Onboarding Flows

### 7.1 Attendee Onboarding

| Attribute | Details |
|-----------|---------|
| **Trigger** | First login after email verification |

**Step 1: Welcome**
```
Welcome to [Platform]!
──────────────────────
Let's set up your profile so your certificates 
display your credentials correctly.

[Get Started]
```

**Step 2: Profile Setup**
| Field | Required |
|-------|----------|
| Full Name | Yes |
| Professional Title | No |
| Credentials | No |
| Organization | No |

**Step 3a: Certificates Found (Conditional)**
*Shown only if certificates exist for user's email*
```
🎉 We Found Your Certificates!
──────────────────────────────

We found 3 certificates that were issued to your 
email address before you created an account.

[List of certificates]

These have been automatically linked to your account.

[View My Certificates]  [Continue Setup]
```

**Step 3b: Complete (No certificates)**
```
You're all set!
───────────────
Your certificates will automatically appear in your 
dashboard when organizers issue them.

[Go to Dashboard]  [Browse Events]
```

**Workflows Supported:** New attendee setup, certificate claiming

---

### 7.2 Organizer Onboarding

| Attribute | Details |
|-----------|---------|
| **Trigger** | After "Become Organizer" or first organizer login |

**Step 1: Welcome**
```
Welcome, Organizer!
───────────────────
Let's get you set up to create events and issue certificates.

This will take about 2 minutes.

[Let's Go]
```

**Step 2: Connect Zoom**
```
Connect Zoom
────────────
Connect your Zoom account to automatically create 
meetings and track attendance.

[Connect Zoom Account]

[Skip for Now]
```

**Step 3: Upload Template**
```
Certificate Template
────────────────────
Upload your certificate design, or use our default template.

[Upload Template]  [Use Default]
```

**Step 4: Complete**
```
You're Ready!
─────────────
You can now create events and issue certificates.

[Create Your First Event]  [Go to Dashboard]
```

**Workflows Supported:** New organizer setup

---

### 7.3 Onboarding Checklist (Dashboard)

| Attribute | Details |
|-----------|---------|
| **Location** | Organizer dashboard (until dismissed) |

**Checklist Items:**
| Item | Status |
|------|--------|
| Complete profile | ✓ / ○ |
| Connect Zoom | ✓ / ○ |
| Upload certificate template | ✓ / ○ |
| Create first event | ✓ / ○ |

**Progress:**
- Visual progress bar
- "X of 4 complete"

**Dismiss:**
- "Dismiss checklist" link

**Workflows Supported:** Guided setup

---

### 7.4 First Event Guide

| Attribute | Details |
|-----------|---------|
| **Location** | Create Event form |

**Elements:**
- Tooltips on complex fields
- Inline help text
- "Learn more" links

**Topics Covered:**
- Zoom integration explanation
- CPD credits configuration
- Certificate settings

**Workflows Supported:** First event guidance

---

## 8. Modals & Overlays

### 8.1 Confirmation Modals

| Modal | Purpose | Actions |
|-------|---------|---------|
| Cancel Event | Confirm event cancellation | "Cancel Event" / "Keep Event" |
| Delete Draft | Confirm draft deletion | "Delete" / "Cancel" |
| Revoke Certificate | Enter reason, confirm | "Revoke" / "Cancel" |
| Delete Account | Type "DELETE" confirmation | "Delete Account" / "Cancel" |
| Leave Waitlist | Confirm leaving | "Leave Waitlist" / "Stay" |
| Cancel Registration | Confirm cancellation | "Cancel Registration" / "Keep" |
| Disconnect Zoom | Warning about impact | "Disconnect" / "Keep Connected" |

### 8.2 Action Modals

| Modal | Purpose | Key Fields |
|-------|---------|------------|
| Add Attendee | Manual registration | Email, Name, Send invite toggle |
| Import CSV | Bulk import | File upload, Column mapping, Preview |
| Issue Certificates | Bulk issuance | Template selection, Recipients, Preview |
| Add Custom Field | Create form field | Type, Label, Options, Required |
| Auto-Promote Settings | Waitlist config | Toggle, Notification settings |
| Add Session | Create event session | Title, Date/time, Speaker |
| Recording Settings | Configure access | Title, Access level, Publish toggle |

### 8.3 Information Modals

| Modal | Purpose |
|-------|---------|
| Certificate Preview | Preview before issuance |
| Zoom Connection Help | Troubleshooting steps |
| Plan Comparison | Feature comparison table |
| Version Warning | Template versioning notice |

---

## 9. Email Templates

*Backend-generated, listed for completeness*

### 9.1 Account Emails

| Email | Trigger | Recipient |
|-------|---------|-----------|
| Welcome | Account creation | New user |
| Email Verification | After signup | New user |
| Password Reset | Reset request | User |

### 9.2 Event Emails

| Email | Trigger | Recipient |
|-------|---------|-----------|
| Event Invitation | Manual invite | Invitee |
| Registration Confirmation | Successful registration | Attendee |
| Event Reminder (24h) | 24 hours before | Registrants |
| Event Reminder (1h) | 1 hour before | Registrants |
| Event Cancelled | Event cancelled | Registrants |
| Waitlist Confirmation | Joined waitlist | Attendee |
| Waitlist Promoted | Spot opened | Attendee |

### 9.3 Certificate Emails

| Email | Trigger | Recipient |
|-------|---------|-----------|
| Certificate Issued | Certificate ready | Attendee |
| Certificate Revoked | Certificate revoked | Attendee |

### 9.4 Learning Emails

| Email | Trigger | Recipient |
|-------|---------|-----------|
| Assignment Due Reminder | Due date approaching | Attendee |
| Assignment Graded | Submission graded | Attendee |
| Revision Requested | Resubmission needed | Attendee |

### 9.5 Organizer Emails

| Email | Trigger | Recipient |
|-------|---------|-----------|
| New Registration | New registration | Organizer |
| Attendance Summary | Post-event | Organizer |

### 9.6 Billing Emails

| Email | Trigger | Recipient |
|-------|---------|-----------|
| Payment Failed | Billing issue | Organizer |
| Trial Ending | 3 days before | Organizer |
| Subscription Cancelled | Subscription ended | Organizer |

---

## 10. Error & Empty States

### 10.1 Error Pages

| Page | Trigger | Content |
|------|---------|---------|
| 404 Not Found | Invalid URL | "Page not found" + Home link |
| 403 Forbidden | No access | "You don't have access" + Contact support |
| 500 Server Error | Server error | "Something went wrong" + Retry |
| Event Not Found | Invalid event | "This event doesn't exist or was removed" |
| Certificate Invalid | Invalid code | "Certificate could not be verified" |

### 10.2 Empty States

| Screen | Message | CTA |
|--------|---------|-----|
| Attendee Dashboard (new) | "Welcome! Your certificates will appear here." | "Browse Events" |
| Organizer Dashboard (new) | "Create your first event to get started." | "Create Event" |
| Events List (empty) | "No events yet." | "Create Event" |
| Certificates (empty) | "No certificates yet. They'll appear automatically." | "Browse Events" |
| Attendance Tab (pre-event) | "Attendance data will appear after the event." | — |
| Templates (empty) | "No templates yet." | "Upload Template" |
| Contacts (empty) | "No contact lists yet." | "Create List" |
| Modules (empty) | "No modules yet. Add modules to organize content." | "Add Module" |
| Recordings (empty) | "Recordings will appear here after the event." | — |
| Search Results (no match) | "No results found for '[query]'" | "Clear filters" |

---

## 11. Loading States

| Pattern | Usage | Implementation |
|---------|-------|----------------|
| Page Skeleton | Initial page load | Skeleton shapes matching layout |
| Inline Spinner | Button actions | Spinner replaces button text |
| Progress Bar | File uploads, bulk operations | Determinate progress bar |
| Table Loading | Data tables | Skeleton rows |
| Card Loading | Card grids | Skeleton cards |
| Overlay | Modal actions | Semi-transparent overlay with spinner |

---

## 12. User Workflow Summary

### 12.1 Attendee Workflows

| Workflow | Screens Involved |
|----------|------------------|
| **Sign Up & Verify** | Landing → Signup → Email Verification → Profile Setup → Dashboard |
| **Login** | Login → Dashboard |
| **Browse & Register** | Event Discovery → Event Detail → Registration Form → Confirmation |
| **Join Waitlist** | Event Detail → Waitlist Confirmation |
| **Attend Event** | My Events → Event Detail → Join Meeting (Zoom) |
| **View Certificate** | Certificates Dashboard → Certificate Detail → Download/Share |
| **Track CPD** | CPD Dashboard → View Progress → Export Report |
| **Complete Learning** | Event Detail → Learning Dashboard → Module Viewer → Assignment Submission |
| **Watch Recording** | Event Detail → Recordings → Recording Viewer |
| **Update Profile** | Settings → Profile → Save |
| **Configure CPD Requirements** | Settings → CPD → Add/Edit Requirements |

### 12.2 Organizer Workflows

| Workflow | Screens Involved |
|----------|------------------|
| **Upgrade Account** | Attendee Dashboard → Upgrade → Checkout → Organizer Onboarding |
| **Connect Zoom** | Settings → Integrations → Zoom OAuth → Connected |
| **Create Event** | Events List → Create Event → Publish |
| **Create Multi-Session Event** | Events List → Create Event (Multi-session) → Add Sessions → Publish |
| **Manage Registrations** | Event Detail → Registrations Tab → Add/Import/Remove |
| **Manage Waitlist** | Event Detail → Registrations → Waitlist Tab → Promote |
| **Monitor Live Event** | Event Detail → Live Monitor |
| **Review Attendance** | Event Detail → Attendance Tab → Override if needed |
| **Issue Certificates** | Event Detail → Certificates Tab → Select → Issue |
| **Revoke Certificate** | Certificates Tab → Select → Revoke → Confirm |
| **Add Learning Modules** | Event Detail → Modules Tab → Add Module → Add Content |
| **Create Assignment** | Event Detail → Assignments Tab → Create → Publish |
| **Grade Submissions** | Assignments Tab → Submissions → Grade → Approve/Revise/Reject |
| **Publish Recording** | Event Detail → Recordings Tab → Settings → Publish |
| **Manage Templates** | Templates → Create/Edit → Save |
| **Import Contacts** | Contacts → Contact List → Import CSV → Map Columns → Import |
| **View Reports** | Reports → Select Date Range → View/Export |
| **Manage Subscription** | Settings → Subscription → Change Plan/Update Payment |
| **Cancel Event** | Event Detail → Settings → Cancel Event → Confirm |
| **Duplicate Event** | Events List → Event Actions → Duplicate → Edit → Save |

### 12.3 Account & Settings Workflows

| Workflow | Steps |
|----------|-------|
| **Edit Profile** | Settings → Profile → Update fields → Save |
| **Change Password** | Settings → Security → Current + new password → Save |
| **Manage Sessions** | Settings → Security → View sessions → Logout others |
| **Configure Notifications** | Settings → Notifications → Toggle preferences |
| **Export Data** | Settings → Account → Export → Wait for email → Download |
| **Delete Account** | Settings → Account → Delete → Type "DELETE" → Confirm |

### 12.4 Billing Workflows

| Workflow | Steps |
|----------|-------|
| **Start Trial** | Upgrade → Select plan → 14-day trial starts |
| **Add Payment** | Settings → Subscription → Add card → Stripe form |
| **Change Plan** | Settings → Subscription → Change → Confirm → Prorated |
| **Payment Failed** | Banner appears → Update payment → Retry |
| **Cancel Subscription** | Settings → Subscription → Cancel → Confirm → Grace period |
| **Reactivate** | Settings → Subscription → Reactivate → Select plan |

---

## 13. Mobile Considerations

### 13.1 Screen Priority

| Screen | Priority | Notes |
|--------|----------|-------|
| Attendee Dashboard | High | Primary mobile use case |
| Certificate View | High | Often shared from mobile |
| Event Registration | High | May register on the go |
| Live Event Monitor | Medium | Organizers may monitor remotely |
| Create Event | Low | Desktop preferred |
| Template Editor | Low | Desktop only |

### 13.2 Responsive Patterns

| Component | Desktop | Mobile |
|-----------|---------|--------|
| Tables | Full table | Card list or horizontal scroll |
| Navigation | Top bar | Bottom tab bar |
| Modals | Centered overlay | Full-screen sheet |
| Forms | Multi-column | Single column |
| Date Picker | Calendar popup | Native date input |
| File Upload | Drag-drop + click | Click only |

### 13.3 Mobile Navigation

**Bottom Tab Bar (4 items max):**

| Attendee | Organizer |
|----------|-----------|
| Home | Home |
| Events | Events |
| Certificates | Certificates |
| Profile | More (menu) |

**"More" Menu (Organizers):**
- Contacts
- Templates
- Reports
- Settings

### 13.4 Touch Considerations

- Minimum touch target: 44x44px
- Adequate spacing between interactive elements
- Swipe actions for common tasks (delete, archive)
- Pull-to-refresh on lists

### 13.5 Mobile-Specific Features

| Feature | Notes |
|---------|-------|
| Share Certificate | Native share sheet (LinkedIn, save, email) |
| Add to Wallet | Apple Wallet / Google Pay pass (Phase 2) |
| Calendar Integration | Deep link to native calendar |
| Push Notifications | Event reminders, certificate issued (Phase 2) |

---

## 14. Navigation Architecture

### 14.1 Global Navigation

**Desktop Top Bar:**
```
┌─────────────────────────────────────────────────────────────────────┐
│  [Logo]    Dashboard | Events | Certificates | Contacts    [?] [👤] │
└─────────────────────────────────────────────────────────────────────┘
```

**Profile Menu Dropdown:**
- Profile Settings
- Security
- Integrations (organizers only)
- Notifications
- Subscription (organizers only)
- Help & Support
- Logout

### 14.2 Role-Based Navigation

| Nav Item | Attendee | Organizer |
|----------|----------|-----------|
| Dashboard | ✓ | ✓ |
| Events | "My Upcoming" | "My Events" + "Create" |
| Certificates | ✓ | ✓ |
| Contacts | — | ✓ |
| Templates | — | ✓ |
| Reports | — | ✓ |

### 14.3 Breadcrumb Logic

| Screen | Breadcrumb |
|--------|------------|
| Event Detail | Events → [Event Name] |
| Event Attendance | Events → [Event Name] → Attendance |
| Template Editor | Templates → [Template Name] |
| Contact List | Contacts → [List Name] |

### 14.4 Event Detail Tabs

```
┌─────────────────────────────────────────────────────────────────────┐
│  [← Back to Events]              Event Title                        │
│  ─────────────────────────────────────────────────────────────────  │
│  Overview | Registrations | Attendance | Modules | Recordings |     │
│  Certificates | Settings                                            │
└─────────────────────────────────────────────────────────────────────┘
```

**Conditional Tabs:**
- Modules: Only if `modules_enabled=true`
- Recordings: Only after event completion

---

## Appendix A: Accessibility Requirements

### WCAG 2.1 AA Compliance

| Requirement | Implementation |
|-------------|----------------|
| Color Contrast | Min 4.5:1 text, 3:1 UI components |
| Focus Indicators | Visible focus ring on all interactive elements |
| Keyboard Navigation | Full functionality via keyboard |
| Screen Reader | Proper ARIA labels, landmarks, live regions |
| Motion | Respect `prefers-reduced-motion` |
| Text Scaling | Support up to 200% zoom |

### Component-Specific

| Component | Requirements |
|-----------|--------------|
| Modals | Focus trap, Escape to close, return focus |
| Forms | Associated labels, error announcements |
| Tables | Proper headers, row/column associations |
| Alerts/Toasts | ARIA live regions, sufficient display time |
| Icons | Screen reader text for icon-only buttons |

---

## Appendix B: Form Validation

### Real-Time Validation

| Field Type | Validation | Timing |
|------------|------------|--------|
| Email | Format check | On blur |
| Password | Strength check | On input |
| Required | Not empty | On blur |
| URL | Format check | On blur |
| Number | Range check | On input |

### Error Display

| Pattern | Usage |
|---------|-------|
| Inline | Below field, red text |
| Summary | Top of form (on submit) |
| Toast | Global errors |

### Input Formatting

| Field | Format |
|-------|--------|
| Date | Locale-aware display, ISO storage |
| Time | 12hr with AM/PM (US) or 24hr |
| Numbers | Locale-aware separators |
| Phone | International format with country code |

---

*End of Document*
