# Platform Screens & Information Architecture v2

## Table of Contents
1. [Navigation Architecture](#navigation-architecture)
2. [Public Screens](#public-screens)
3. [Authentication Flows](#authentication-flows)
4. [Attendee Screens](#attendee-screens)
5. [Organizer Screens](#organizer-screens)
6. [Learning & Modules (LMS)](#learning--modules-lms)
7. [Recordings](#recordings)
8. [Multi-Session Events](#multi-session-events)
9. [Settings Screens](#settings-screens)
10. [Billing & Subscription](#billing--subscription)
11. [Onboarding Flows](#onboarding-flows)
12. [Event State Machine](#event-state-machine)
13. [Email Templates](#email-templates)
14. [Modals & Overlays](#modals--overlays)
15. [Loading & Error Patterns](#loading--error-patterns)
16. [Form Specifications](#form-specifications)
17. [Mobile Behavior](#mobile-behavior)
18. [Accessibility Requirements](#accessibility-requirements)

---

## Navigation Architecture

### Global Navigation Structure

**Desktop: Top Navigation Bar**
```
┌─────────────────────────────────────────────────────────────────────┐
│  [Logo]    Dashboard | Events | Certificates | Contacts    [?] [👤] │
└─────────────────────────────────────────────────────────────────────┘
                                                              │    │
                                                         Help  Profile
                                                               Menu
```

**Profile Menu Dropdown:**
- Profile Settings
- Security
- Integrations (organizers only)
- Notifications
- Subscription (organizers only)
- Help & Support
- Logout

### Role-Based Navigation

| Nav Item | Attendee | Organizer |
|----------|----------|-----------|
| Dashboard | ✓ (certificates focus) | ✓ (events focus) |
| Events | "My Upcoming" | "My Events" + "Create" |
| Certificates | ✓ | ✓ |
| Contacts | — | ✓ |
| Templates | — | ✓ |
| Reports | — | ✓ |

### Mobile Navigation

**Bottom Tab Bar (4 items max):**

| Attendee | Organizer |
|----------|-----------|
| Home | Home |
| Events | Events |
| Certificates | Certificates |
| Profile | More (menu) |

**"More" menu for organizers:** Contacts, Templates, Reports, Settings

### Breadcrumb Logic

| Screen | Breadcrumb |
|--------|------------|
| Event Detail | Events → [Event Name] |
| Event Attendance | Events → [Event Name] → Attendance |
| Template Editor | Templates → [Template Name] |
| Contact List | Contacts → [List Name] |

### Contextual Navigation

**Event Detail Tabs:**
```
┌─────────────────────────────────────────────────────────────────────┐
│  [← Back to Events]              Event Title                        │
│  ─────────────────────────────────────────────────────────────────  │
│  Overview | Registrations | Attendance | Modules | Recordings |     │
│  Certificates | Settings                                            │
└─────────────────────────────────────────────────────────────────────┘
```

**Note:** Modules tab only visible if `modules_enabled=true`. Recordings tab only visible after event has recordings.

---

## Public Screens

### Landing Page
**URL:** `/`

| Section | Content | CTA |
|---------|---------|-----|
| Hero | Value prop headline, subheadline, visual | "Get Started Free" / "Login" |
| Problem Statement | Pain points of manual tracking | — |
| Features | 3-4 key features with icons | — |
| How It Works | 3-step visual: Create → Track → Certify | — |
| Social Proof | Testimonials, logos (when available) | — |
| Pricing | Plan comparison (or link to pricing page) | "Start Free Trial" |
| Footer | Links, legal, contact, social | — |

**Mobile:** Stacked sections, sticky CTA button

---

### Event Discovery
**URL:** `/events/browse` or `/discover`

Public page for browsing upcoming events. Only shows events with `visibility=PUBLIC`.

**Layout:**
```
┌─────────────────────────────────────────────────────────────────────┐
│  Discover Events                                        [Login]     │
│  ─────────────────────────────────────────────────────────────────  │
│  Find professional development events and earn CPD credits          │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  🔍 Search events...                          [Search]      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Filters:                                                           │
│  [Date Range ▼]  [Credit Type ▼]  [Event Type ▼]  [Clear Filters]  │
│                                                                     │
│  Showing 24 events                              [Grid] [List]       │
│                                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │
│  │ Event Card  │  │ Event Card  │  │ Event Card  │                 │
│  │             │  │             │  │             │                 │
│  │ Title       │  │ Title       │  │ Title       │                 │
│  │ Date/Time   │  │ Date/Time   │  │ Date/Time   │                 │
│  │ Organizer   │  │ Organizer   │  │ Organizer   │                 │
│  │ [CPD Badge] │  │ [CPD Badge] │  │ [CPD Badge] │                 │
│  └─────────────┘  └─────────────┘  └─────────────┘                 │
│                                                                     │
│  [Load More Events]                                                 │
└─────────────────────────────────────────────────────────────────────┘
```

**Filters:**

| Filter | Options |
|--------|---------|
| Date Range | This Week, This Month, Next 30 Days, Custom Range |
| Credit Type | All, CME, CLE, CPE, General (based on available events) |
| Event Type | All, Webinar, Workshop, Course, Conference, Training |
| Search | Title, description, organizer name |

**Event Card Contents:**
- Event title
- Date and time (in user's timezone if detected)
- Organizer name (linked to profile if public)
- CPD badge showing credit type and value
- "Free" or price indicator
- Spots remaining (if limited and <20)

**Sorting Options:**
- Date (soonest first) — default
- Recently Added
- Most Popular

**Empty State:**
```
No Events Found
───────────────
No events match your filters. Try adjusting your search.

[Clear Filters]  [Browse All Events]
```

---

### Organizer Public Profile
**URL:** `/organizers/{organizer_slug}` or `/o/{uuid}`

**Shown when:** Organizer has `is_organizer_profile_public=true`

**Layout:**
```
┌─────────────────────────────────────────────────────────────────────┐
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  [Logo]   Dr. Sarah Johnson                                 │   │
│  │           Healthcare Education Expert                       │   │
│  │           🌐 website.com  📧 contact@email.com             │   │
│  │           [LinkedIn] [Twitter]                              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  About                                                              │
│  ─────                                                              │
│  Dr. Johnson has 20 years of experience in medical education...    │
│                                                                     │
│  Upcoming Events (3)                                                │
│  ──────────────────                                                │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Advanced Clinical Skills Workshop                           │   │
│  │ Feb 15, 2025 • 2 CME Credits                               │   │
│  │ [Register]                                                  │   │
│  ├─────────────────────────────────────────────────────────────┤   │
│  │ Patient Communication Masterclass                          │   │
│  │ Mar 1, 2025 • 1.5 CME Credits                              │   │
│  │ [Register]                                                  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Past Events (12)                                    [View All]     │
│  ────────────                                                       │
│  • Healthcare Leadership Summit 2024 — 45 attendees                │
│  • Medical Documentation Best Practices — 32 attendees             │
│  • ...                                                              │
│                                                                     │
│  [Follow This Organizer] (future feature)                          │
└─────────────────────────────────────────────────────────────────────┘
```

**Sections:**
- Header with logo, name, title, links
- About/Bio
- Upcoming public events (with register buttons)
- Past events summary
- Total events hosted, certificates issued (stats)

**Profile Not Public State:**
```
Organizer Profile Not Available
────────────────────────────────
This organizer has chosen to keep their profile private.

[Browse Events]
```

---

### Public Event Page
**URL:** `/e/{event_slug}` or `/events/{event_id}`

| Section | Content |
|---------|---------|
| Header | Event title, organizer name/logo |
| Key Info | Date, time (with timezone), duration |
| Description | Full event description (markdown supported) |
| CPD Info | Credit type, credit value |
| Organizer | Name, profile link (if public) |
| Registration | Status indicator + CTA |

**Registration States:**

| State | Display |
|-------|---------|
| Open | "Register" button + spots remaining (if limited) |
| Full | "Event Full" + "Join Waitlist" (if enabled) |
| Closed | "Registration Closed" |
| Cancelled | "This event has been cancelled" banner |
| Past | "This event has ended" + link to organizer's other events |
| Already Registered | "You're registered!" + calendar links |

**Actions:**
- Register (→ registration flow)
- Add to Calendar (Google, Outlook, iCal)
- Share (copy link, social)

---

### Registration Flow

**Step 1: Registration Form**
**URL:** `/e/{event_slug}/register`

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| Email | Email input | Yes | Auto-fill if logged in |
| Full Name | Text | Yes | |
| Professional Title | Text | No | |
| Organization | Text | No | Free text |
| Custom Fields | Dynamic | Varies | Organizer-defined |

**Logged-in User:** Pre-filled, single "Confirm Registration" button

**Guest User:** Form + options:
- "Register as Guest"
- "Login to Register" 
- "Create Account & Register"

---

**Step 2: Registration Confirmation**
**URL:** `/e/{event_slug}/registered`

| Section | Content |
|---------|---------|
| Success Message | "You're registered for [Event Name]!" |
| Event Summary | Date, time, Zoom link (if released) |
| Calendar | "Add to Calendar" buttons |
| Next Steps | What to expect (email confirmation, reminder) |
| Account Prompt | (Guests) "Create an account to track your certificates" |

**Email Sent:** Confirmation with event details

---

### Certificate Verification (Public)
**URL:** `/verify/{certificate_code}`

| Element | Details |
|---------|---------|
| Header | "Certificate Verification" |
| Status Badge | ✓ Valid / ✗ Revoked / ⚠ Not Found |
| Certificate Info | |
| → Recipient | Full name |
| → Event | Event title |
| → Date | Event date |
| → Issuer | Organizer name |
| → CPD Credits | Type + value |
| → Issue Date | When certificate was issued |
| Certificate ID | Verification code |
| Organizer Branding | Logo (if provided) |

**Privacy Note:** Attendee must have consented to public verification during registration.

**Not Found State:**
```
Certificate Not Found
─────────────────────
The certificate code you entered could not be verified.
This may mean:
• The code was entered incorrectly
• The certificate has been revoked
• The certificate does not exist

[Contact Support]
```

---

## Authentication Flows

### Sign Up
**URL:** `/signup`

| Element | Details |
|---------|---------|
| Form Fields | Email, Password, Confirm Password |
| Password Requirements | 8+ chars, shown inline |
| OAuth | "Continue with Google" |
| Terms | Checkbox: "I agree to Terms & Privacy Policy" |
| CTA | "Create Account" |
| Footer Link | "Already have an account? Login" |

**Post-Submit:** Redirect to email verification pending screen

---

### Login
**URL:** `/login`

| Element | Details |
|---------|---------|
| Form Fields | Email, Password |
| Options | "Remember me" checkbox |
| OAuth | "Continue with Google" |
| CTA | "Login" |
| Links | "Forgot password?" / "Sign up" |

**Post-Login Routing:**

| Scenario | Redirect To |
|----------|-------------|
| Default | Dashboard |
| Had pending registration | Complete registration |
| Had pending certificate claim | Dashboard (certificates linked) |
| First-time organizer | Onboarding flow |

---

### Email Verification

**Pending State**
**URL:** `/verify-email`

| Element | Details |
|---------|---------|
| Message | "Check your email" + email address shown |
| Sub-message | "Click the link in the email to verify your account" |
| Actions | "Resend Email" (with cooldown) |
| Help | "Wrong email? Start over" |

**Success State**
**URL:** `/verify-email?success=true` (or redirect from email link)

| Element | Details |
|---------|---------|
| Message | "Email verified!" |
| CTA | "Continue to Profile Setup" |

**Expired/Invalid Link**
| Element | Details |
|---------|---------|
| Message | "This link has expired or is invalid" |
| CTA | "Request New Link" |

---

### Forgot Password
**URL:** `/forgot-password`

| Element | Details |
|---------|---------|
| Form | Email input |
| CTA | "Send Reset Link" |
| Success State | "If an account exists, you'll receive an email" |
| Link | "Back to Login" |

---

### Reset Password
**URL:** `/reset-password?token={token}`

| Element | Details |
|---------|---------|
| Form | New password, Confirm password |
| Validation | Password strength indicator, match validation |
| CTA | "Reset Password" |
| Success | "Password reset! Redirecting to login..." |
| Invalid Token | "This link has expired" + request new link |

---

## Attendee Screens

### Attendee Dashboard
**URL:** `/dashboard`

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
──────────────────────
Your certificates will appear here when organizers issue them.

In the meantime:
• Complete your profile to ensure certificates show your credentials
• Browse upcoming events

[Complete Profile]  [Browse Events]
```

---

### My Upcoming Events (Attendee)
**URL:** `/events`

| Element | Details |
|---------|---------|
| Header | "My Events" |
| Tabs | Upcoming | Past |
| Event Cards | |
| → Each Card | Event name, organizer, date/time, status badge |
| → Actions | "View Details", "Add to Calendar", "Cancel Registration" |
| Empty State | "No upcoming events. Browse events to register." |

**Past Events Tab:**
- Shows attended events
- Certificate status indicator (Issued / Pending / Not Eligible)
- Link to certificate if issued

---

### Certificates Dashboard
**URL:** `/certificates`

| Section | Content |
|---------|---------|
| Header | "My Certificates" |
| Summary Bar | Total: X certificates, Y CPD credits |
| Filters | Date range, Organizer, CPD type, Search |
| View Toggle | Grid / List |
| Certificates | |
| → Grid View | Thumbnail, event name, date, CPD badge |
| → List View | Table: Event, Organizer, Date, CPD Type, Credits, Actions |
| Actions | View, Download, Share |

**Filters:**
- Date Range: Presets (This Year, Last Year, All Time) + Custom
- Organizer: Dropdown of orgs that issued certs
- CPD Type: CME, CLE, CPE, General, etc.
- Search: Event name, organizer name

**Empty State:**
```
No Certificates Yet
───────────────────
Certificates you earn will appear here automatically.

When you attend events and organizers issue certificates,
they'll be linked to your account via your email address.

[Browse Events]
```

---

### Certificate Detail (Attendee)
**URL:** `/certificates/{certificate_id}`

| Section | Content |
|---------|---------|
| Certificate Preview | Visual PDF preview (or image) |
| Details Panel | |
| → Event | Event name (linked if public page exists) |
| → Date | Event date |
| → Organizer | Organizer name |
| → CPD Type | Credit type |
| → Credits | Numeric value |
| → Issue Date | When issued |
| → Certificate ID | Verification code |
| Actions | Download PDF, Copy Share Link, View Verification Page |
| Share Options | LinkedIn, Email, Copy Link |
| Verification QR | QR code linking to verification page |

**Privacy Setting Section:**
```
Public Verification
───────────────────
☑ Allow anyone with the verification link to see this certificate

When enabled:
• Certificate details visible at verification URL
• Verification QR code works
• Can share on LinkedIn

When disabled:
• Verification page shows "Private Certificate"
• Only you can see certificate details

Note: This setting was configured when you registered.
You can change it anytime.
```

**Data Location:** Stored on Registration model (`allow_public_verification`), reflected on certificate page. Changing updates the registration; new certificates inherit registration setting.

---

### CPD Tracking
**URL:** `/cpd`

| Section | Content |
|---------|---------|
| Period Selector | Dropdown: This Year, Last Year, Custom Range |
| Summary Cards | One card per CPD type showing total |
| Progress Bars | Shows progress toward annual requirements (if configured) |
| Breakdown Table | |
| → Columns | CPD Type, Credits Earned, Events Count |
| → Rows | Each CPD type with totals |
| Certificate List | Grouped by CPD type |
| Export | "Download CPD Report" (PDF) |

**Progress Bar (when requirements configured):**
```
CME Credits
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━░░░░░░░░░░  35 / 50 (70%)
Due by: December 31, 2025

CLE Credits  
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  20 / 20 ✓ Complete!
```

**Configure Requirements Link:** "Set up your CPD requirements" → Settings page to add CPDRequirement entries.

---

## Organizer Screens

### Organizer Dashboard
**URL:** `/dashboard` (organizer view)

| Section | Content |
|---------|---------|
| Header | "Welcome, [Name]" + "Create Event" button |
| Stats Row | 4 cards: Total Events, Upcoming, Attendees, Certificates Issued |
| Upcoming Events | Next 3 events with quick stats |
| Recent Activity | Feed: registrations, certificates issued |
| Action Prompts | Contextual (e.g., "3 events need attendance review") |

**First-Time Organizer:**
- Shows onboarding checklist instead
- See [Onboarding Flows](#onboarding-flows)

---

### Events List (Organizer)
**URL:** `/events`

| Element | Details |
|---------|---------|
| Header | "My Events" + "Create Event" button |
| Tabs | Upcoming | Past | Drafts | Cancelled |
| Filters | Date range, Status, Search |
| View Toggle | List / Calendar |
| Event Row | |
| → Info | Title, date/time, status badge |
| → Stats | Registered, Attended, Certificates |
| → Actions | Edit, Duplicate, View |
| Bulk Actions | (Select multiple) Delete drafts, Export |

**Calendar View:**
- Monthly calendar with event dots
- Click date to see events
- Drag to create (future)

---

### Create Event
**URL:** `/events/new`

**Multi-Section Form (Single Page with Sections)**

#### Section 1: Basic Info
| Field | Type | Required | Validation |
|-------|------|----------|------------|
| Title | Text | Yes | 3-100 chars |
| Description | Rich Text | No | Max 5000 chars |
| Event Type | Dropdown | Yes | Webinar, Workshop, Course, Other |

#### Section 2: Date & Time
| Field | Type | Required | Validation |
|-------|------|----------|------------|
| Start Date | Date Picker | Yes | Must be future |
| Start Time | Time Picker | Yes | — |
| Duration | Dropdown | Yes | 15min - 8hrs |
| Timezone | Dropdown | Yes | Auto-detect default |

#### Section 3: Zoom Settings
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| Create Zoom Meeting | Toggle | — | Default on |
| Waiting Room | Toggle | — | Default on |
| Passcode | Toggle + Input | — | Auto-generate or custom |
| Allow Join Before Host | Toggle | — | Default off |

**Zoom Not Connected State:**
```
⚠ Zoom Not Connected
Connect your Zoom account to automatically create meetings.
[Connect Zoom]

Or manually add meeting details after creating the event.
```

#### Section 4: Registration Settings
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| Registration | Toggle | — | Default open |
| Capacity | Number | No | Leave blank for unlimited |
| Registration Deadline | DateTime | No | Defaults to event start |
| Waitlist | Toggle | No | If capacity set |
| Custom Fields | Builder | No | Add custom registration questions |

**Custom Field Builder:**

Clicking "Add Custom Field" opens builder modal:

```
Add Custom Field
────────────────

Field Label: [____________________________]

Field Type: [Text Input ▼]
• Text Input (short answer)
• Text Area (long answer)  
• Dropdown (select one)
• Checkboxes (select multiple)
• Radio Buttons (select one)
• Date
• Number
• File Upload

[Options section - shown for Dropdown/Checkbox/Radio]
┌─────────────────────────────────────────────────────────────────────┐
│  Options (one per line):                                            │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Option 1                                                    │   │
│  │ Option 2                                                    │   │
│  │ Option 3                                                    │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  ☐ Allow "Other" with text input                                   │
└─────────────────────────────────────────────────────────────────────┘

Settings:
☐ Required field
☐ Show on certificate (if applicable)

Placeholder text: [____________________________]
Help text: [____________________________]

[Cancel]  [Add Field]
```

**Custom Fields List:**
```
Custom Registration Fields
──────────────────────────
┌─────────────────────────────────────────────────────────────────────┐
│  ≡  Dietary Requirements        Dropdown      Required    [Edit][×] │
│  ≡  Company Name                Text Input    Optional    [Edit][×] │
│  ≡  How did you hear about us?  Dropdown      Optional    [Edit][×] │
└─────────────────────────────────────────────────────────────────────┘
Drag ≡ to reorder

[+ Add Custom Field]
```

#### Section 5: CPD / Credits
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| Offer CPD Credits | Toggle | — | |
| Credit Type | Dropdown | If toggle on | CME, CLE, CPE, General, Custom |
| Credit Value | Number | If toggle on | Decimal allowed |
| Accreditation Note | Text | No | e.g., "Accredited by XYZ Board" |

#### Section 6: Certificate Settings
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| Issue Certificates | Toggle | — | Default on |
| Template | Dropdown | If toggle on | Select from own/org templates |
| Auto-Issue | Toggle | — | Issue automatically after attendance confirmed |
| Minimum Attendance | Number | No | % of event duration required (default 80%) |

**Form Actions:**
- "Save as Draft" — saves, returns to events list
- "Publish Event" — validates all, publishes
- "Preview" — shows public event page preview

---

### Edit Event
**URL:** `/events/{event_id}/edit`

Same as Create Event, with:
- Pre-populated fields
- Status indicator at top
- State-based field restrictions (see [Event State Machine](#event-state-machine))
- "Danger Zone" section at bottom:
  - Cancel Event (with confirmation)
  - Delete Event (drafts only)

---

### Event Detail (Organizer)
**URL:** `/events/{event_id}`

**Header:**
```
┌─────────────────────────────────────────────────────────────────────┐
│ [← Events]                                                          │
│                                                                     │
│ Event Title                                      [Edit] [⋮ More]    │
│ 📅 Jan 15, 2025 • 2:00 PM EST • 60 min              Status: Live    │
│                                                                     │
│ ┌─────────┬─────────┬─────────┐                                    │
│ │ 45      │ 38      │ 0       │                                    │
│ │Registered│Attended │Certified│                                    │
│ └─────────┴─────────┴─────────┘                                    │
│                                                                     │
│ [Overview] [Registrations] [Attendance] [Certificates] [Settings]   │
└─────────────────────────────────────────────────────────────────────┘
```

**More Menu:** Duplicate, Share, Cancel Event

---

#### Tab: Overview

| Section | Content |
|---------|---------|
| Event Details | Description, CPD info |
| Zoom Meeting | Meeting ID, Passcode, Host Link, Join Link |
| Quick Actions | Copy invite link, Send reminder, Start meeting |
| Activity Feed | Recent registrations, attendance updates |

---

#### Tab: Registrations

| Element | Details |
|---------|---------|
| Header | "Registrations (45)" + "Add Attendee" button |
| Search | Filter by name/email |
| Table Columns | Name, Email, Registered Date, Status, Actions |
| Status | Confirmed, Cancelled, Waitlisted |
| Row Actions | Resend invite, Remove |
| Bulk Actions | Select all, Send bulk email, Export CSV |
| Add Attendee | Modal: single email or CSV import |

**Empty State:**
```
No Registrations Yet
────────────────────
Share your event to get registrations.

[Copy Event Link]  [Import Attendees]
```

---

#### Tab: Attendance

| Element | Details |
|---------|---------|
| Header | "Attendance (38/45)" + "Import" button |
| Sync Status | "Last synced: 2 min ago" or "Live" indicator |
| Threshold | "Minimum attendance: 80% (48 min)" — editable |
| Table Columns | Name, Email, Join Time, Leave Time, Duration, Eligible, Actions |
| Eligible | ✓ / ✗ based on threshold |
| Row Actions | Mark attended, Mark not attended (override) |
| Bulk Actions | Mark selected as attended |

**Live Event State:**
- Real-time updates
- "Currently in meeting: 32" counter
- Live join/leave feed

**Pre-Event State:**
```
Attendance Tracking
───────────────────
Attendance will be tracked automatically when the event starts.

Zoom attendance data syncs in real-time during the event
and for up to 1 hour after it ends.
```

**Unmatched Attendees:**
Separate section for Zoom participants that couldn't be matched to registrations (phone dial-ins, different email).
- Option to manually match to registered attendee

---

#### Tab: Certificates

| Element | Details |
|---------|---------|
| Header | "Certificates" + "Issue Certificates" button |
| Status Summary | "38 eligible, 0 issued" |
| Template Preview | Selected template thumbnail |
| Eligible Table | Name, Email, Attendance, Certificate Status, Actions |
| Certificate Status | Not Issued, Issued, Revoked |
| Row Actions | Issue, Preview, Revoke (if issued) |
| Bulk Actions | Issue to all eligible |

**Issue Flow:**
1. Click "Issue Certificates"
2. Modal: Select template, preview with sample data
3. Confirm: "Issue to 38 attendees?"
4. Processing: Progress indicator
5. Done: Success message + email confirmation

---

#### Tab: Settings

| Section | Content |
|---------|---------|
| Registration | Open/closed toggle, capacity, deadline |
| Notifications | Toggle: send reminders, when |
| Certificate | Template selection, auto-issue toggle |
| Danger Zone | Cancel event |

---

### Live Event Monitor
**URL:** `/events/{event_id}/live`

| Element | Details |
|---------|---------|
| Header | Event name + LIVE badge + elapsed time |
| Current Count | Large number: "47 in meeting" |
| Attendance Rate | "47/52 registered (90%)" |
| Live Feed | Real-time join/leave with timestamps |
| Attendee List | Who's currently in, duration so far |
| Quick Actions | Send in-meeting message (future), end tracking |

**Auto-redirect:** After event ends, redirect to Attendance tab

---

### Templates Management
**URL:** `/templates`

| Element | Details |
|---------|---------|
| Header | "Certificate Templates" + "Upload Template" |
| View Toggle | Grid / List |
| Template Cards | |
| → Thumbnail | Preview image |
| → Info | Name, created date, usage count |
| → Badge | "Default" if set as default |
| → Actions | Edit, Duplicate, Delete, Set as Default |

**Empty State:**
```
No Templates Yet
────────────────
Upload your first certificate template to start issuing certificates.

Supported formats: PDF (recommended), PNG, JPG
Recommended size: 11" x 8.5" (landscape)

[Upload Template]  [Use Default Template]
```

---

### Template Editor
**URL:** `/templates/{template_id}` or `/templates/new`

**Header (when editing existing):**
```
┌─────────────────────────────────────────────────────────────────────┐
│  [← Back to Templates]                                              │
│                                                                     │
│  Professional Certificate Template                                  │
│  Version 3 (current) • Last edited Jan 10, 2025                    │
│                                                         [History ▼] │
└─────────────────────────────────────────────────────────────────────┘
```

**Version History Dropdown:**
- Version 3 (current) — Jan 10, 2025
- Version 2 — Dec 15, 2024
- Version 1 — Nov 1, 2024

**Clicking version:** Shows read-only preview of that version.

| Section | Content |
|---------|---------|
| Template Upload | Drag-drop or file picker |
| Field Placement | Draggable fields on template preview |
| Available Fields | Attendee Name, Event Title, Event Date, CPD Credits, Certificate ID, Signature |
| Field Properties | Font, size, color, alignment |
| Preview | Toggle sample data preview |
| Settings | Template name, set as default |
| Actions | Save, Cancel |

**Versioning Behavior:**
- Editing a template that has issued certificates creates a new version
- Warning shown: "This template has been used to issue 45 certificates. Saving will create a new version."
- New certificates use new version; old certificates retain old version
- Versions can be compared side-by-side (future feature)

**Supported Formats:** PDF, PNG, JPG
**Max Size:** 10MB
**Recommended Dimensions:** 11" x 8.5" (landscape)

---

### Contacts Management
**URL:** `/contacts`

| Element | Details |
|---------|---------|
| Header | "Contacts" + "Create List" |
| Lists Table | Name, Contact Count, Created, Last Used, Actions |
| Actions | View, Edit, Delete, Export |
| Global Search | Search across all contacts |

---

### Contact List Detail
**URL:** `/contacts/{list_id}`

| Element | Details |
|---------|---------|
| Header | List name + "Add Contacts" |
| Table | Name, Email, Title, Organization, Tags, Added Date, Events, Actions |
| Actions | Remove, Edit, View profile |
| Bulk Actions | Import CSV, Export, Delete selected, Add Tags |
| Add Contacts | Single entry or CSV import |

**CSV Import:**
```
Import Contacts from CSV
────────────────────────

Step 1: Upload File
[Drop CSV file here or click to browse]

Step 2: Map Columns
┌────────────────────┬────────────────────┐
│ Your Column        │ Maps To            │
├────────────────────┼────────────────────┤
│ email_address      │ [Email ▼]          │
│ full_name          │ [Full Name ▼]      │
│ job_title          │ [Professional Title ▼] │
│ company            │ [Organization ▼]   │
│ phone_number       │ [Phone ▼]          │
│ category           │ [Tags ▼]           │
└────────────────────┴────────────────────┘

Step 3: Preview (first 5 rows)
┌──────────────────┬─────────────────────┬───────────────────┐
│ Email            │ Full Name           │ Organization      │
├──────────────────┼─────────────────────┼───────────────────┤
│ jane@example.com │ Jane Smith          │ Acme Corp         │
│ john@example.com │ John Doe            │ Tech Inc          │
└──────────────────┴─────────────────────┴───────────────────┘

Found: 150 valid rows, 3 errors (invalid email format)

[Cancel]  [Import 150 Contacts]
```

**Supported CSV Columns:**
| Column | Required | Notes |
|--------|----------|-------|
| email | Yes | Must be valid email format |
| name / full_name | No | Contact's full name |
| first_name | No | Used with last_name if full_name missing |
| last_name | No | Used with first_name |
| title / professional_title / job_title | No | Professional title |
| organization / company / org | No | Organization name |
| phone / phone_number | No | Phone number |
| tags / category | No | Comma-separated tags |

---

### Reports
**URL:** `/reports`

| Section | Content |
|---------|---------|
| Date Range | Preset + custom picker |
| Summary Cards | Events held, Total attendees, Certificates issued, Avg attendance rate |
| Events Table | Event, Date, Registered, Attended, Attendance %, Certificates |
| Charts | Attendance over time, CPD credits issued by type |
| Export | Download CSV, Download PDF report |

---

## Learning & Modules (LMS)

Learning features are **optional per event**. When enabled, organizers can add structured content modules, assignments, and track attendee progress.

### Enabling Learning Features

**Location:** Event Settings tab or Create Event form

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| Enable Modules | Toggle | Off | Allow content modules for this event |
| Enable Assignments | Toggle | Off | Allow assignments with submissions |
| Require Module Completion | Toggle | Off | Must complete all modules for certificate |
| Require Assignments Passed | Toggle | Off | Must pass all required assignments for certificate |
| Passing Score | Number | 70% | Minimum score to pass assignments |

---

### Tab: Modules (Organizer)
**URL:** `/events/{event_id}/modules`

**Header:**
```
┌─────────────────────────────────────────────────────────────────────┐
│  Modules (4)                              [+ Add Module]            │
│  ─────────────────────────────────────────────────────────────────  │
│  Drag to reorder modules                                            │
└─────────────────────────────────────────────────────────────────────┘
```

**Module List:**

| Element | Details |
|---------|---------|
| Module Card | Title, description preview, content count, status |
| Status Badge | Draft, Published, Scheduled |
| Content Count | "5 items • 45 min estimated" |
| Drag Handle | Reorder modules |
| Actions | Edit, Duplicate, Delete, Publish/Unpublish |

**Empty State:**
```
No Modules Yet
──────────────
Add modules to organize your learning content into 
sections, weeks, or topics.

[+ Add First Module]
```

---

### Module Editor
**URL:** `/events/{event_id}/modules/{module_id}` or `/events/{event_id}/modules/new`

**Layout:**
```
┌─────────────────────────────────────────────────────────────────────┐
│  [← Back to Modules]                      [Save Draft] [Publish]    │
│                                                                     │
│  ┌─────────────────────────────┐  ┌───────────────────────────────┐│
│  │ Module Settings             │  │ Content Items                 ││
│  │                             │  │                               ││
│  │ Title: [_______________]    │  │ [+ Add Content]               ││
│  │                             │  │                               ││
│  │ Description:                │  │ ┌─────────────────────────┐   ││
│  │ [____________________]      │  │ │ 📹 Welcome Video        │   ││
│  │ [____________________]      │  │ │    Duration: 5:30       │   ││
│  │                             │  │ └─────────────────────────┘   ││
│  │ Release Type:               │  │ ┌─────────────────────────┐   ││
│  │ (•) Immediately             │  │ │ 📄 Course Overview PDF  │   ││
│  │ ( ) Scheduled Date          │  │ │    Document             │   ││
│  │ ( ) After Previous Module   │  │ └─────────────────────────┘   ││
│  │ ( ) Days After Registration │  │ ┌─────────────────────────┐   ││
│  │                             │  │ │ ✏️ Module 1 Quiz        │   ││
│  │ Prerequisite Module:        │  │ │    Assignment           │   ││
│  │ [None____________▼]         │  │ └─────────────────────────┘   ││
│  │                             │  │                               ││
│  │ ☑ Required for completion   │  │ Drag to reorder               ││
│  └─────────────────────────────┘  └───────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

**Module Settings:**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| Title | Text | Yes | Module name |
| Description | Textarea | No | Brief overview |
| Release Type | Radio | Yes | When module becomes available |
| → Immediately | — | — | Available when event published |
| → Scheduled Date | DateTime | — | Specific date/time |
| → After Previous Module | — | — | Unlocks when prior module complete |
| → Days After Registration | Number | — | X days after attendee registers |
| Prerequisite Module | Dropdown | No | Must complete this module first |
| Required | Checkbox | — | Must complete for certificate |

---

### Add Content Modal

**Content Type Selection:**
```
Add Content
───────────
Select content type:

┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐
│  📹     │  │  📄     │  │  🔗     │  │  📝     │
│ Video   │  │Document │  │  Link   │  │  Text   │
└─────────┘  └─────────┘  └─────────┘  └─────────┘

┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐
│  🎧     │  │  📊     │  │  ✏️     │  │  🎬     │
│ Audio   │  │ Slides  │  │  Quiz   │  │Recording│
└─────────┘  └─────────┘  └─────────┘  └─────────┘
```

**Content Forms by Type:**

| Type | Fields |
|------|--------|
| Video | Title, Video URL (YouTube/Vimeo/direct), Duration (auto-detect), Required toggle |
| Document | Title, File upload (PDF, DOCX), Required toggle |
| Link | Title, URL, Description, Open in new tab toggle |
| Text | Title, Rich text editor (HTML content) |
| Audio | Title, Audio URL or upload, Duration |
| Slides | Title, File upload (PDF/PPTX) or URL |
| Quiz | Redirects to Assignment creation with type=quiz |
| Recording | Select from event recordings (if any exist) |

---

### Assignments List (Organizer)
**URL:** `/events/{event_id}/assignments`

| Element | Details |
|---------|---------|
| Header | "Assignments (3)" + "Create Assignment" |
| Assignment Row | Title, Module (if linked), Due date, Submissions count, Status |
| Status | Draft, Published, Grading, Completed |
| Submissions | "12/45 submitted • 8 graded" |
| Actions | Edit, View Submissions, Duplicate, Delete |

---

### Assignment Editor
**URL:** `/events/{event_id}/assignments/new` or `.../assignments/{id}`

**Sections:**

#### Basic Info
| Field | Type | Required |
|-------|------|----------|
| Title | Text | Yes |
| Description | Rich text | No |
| Instructions | Rich text | Yes |
| Module | Dropdown | No (can be standalone) |

#### Submission Settings
| Field | Type | Notes |
|-------|------|-------|
| Submission Type | Radio | File, Text, Link, File or Text, Quiz, Completion Only |
| Allowed File Types | Multi-select | If file submission (PDF, DOCX, images, etc.) |
| Max File Size | Number | MB limit |
| Max Files | Number | How many files allowed |
| Min Word Count | Number | For text submissions |
| Max Word Count | Number | For text submissions |

#### Deadlines
| Field | Type | Notes |
|-------|------|-------|
| Due Date | DateTime | Primary deadline |
| Allow Late Submissions | Toggle | Accept after due date |
| Late Deadline | DateTime | Final cutoff if late allowed |
| Late Penalty | Percentage | Points deducted for late |

#### Grading
| Field | Type | Notes |
|-------|------|-------|
| Grading Type | Radio | Pass/Fail, Points, Percentage, Ungraded |
| Max Points | Number | If points-based |
| Passing Score | Number | Minimum to pass |
| Weight | Number | For overall score calculation |
| Use Rubric | Toggle | Enable rubric grading |

#### Rubric Builder (if enabled)
```
Rubric Criteria
───────────────
┌─────────────────────────────────────────────────────────────────────┐
│ Criterion: [Content Quality_______]              Points: [25]       │
│                                                                     │
│ Levels:                                                             │
│ ┌──────────────┬───────────────┬───────────────┬──────────────┐    │
│ │ Excellent    │ Good          │ Satisfactory  │ Needs Work   │    │
│ │ 25 pts       │ 20 pts        │ 15 pts        │ 5 pts        │    │
│ │ [Description]│ [Description] │ [Description] │ [Description]│    │
│ └──────────────┴───────────────┴───────────────┴──────────────┘    │
│                                                    [+ Add Level]    │
└─────────────────────────────────────────────────────────────────────┘
[+ Add Criterion]
```

---

### Assignment Submissions (Organizer Grading)
**URL:** `/events/{event_id}/assignments/{id}/submissions`

**Header:**
```
┌─────────────────────────────────────────────────────────────────────┐
│  [← Back]  Assignment: Module 1 Quiz                                │
│                                                                     │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐               │
│  │   45    │  │   38    │  │   30    │  │    8    │               │
│  │Assigned │  │Submitted│  │ Graded  │  │ Pending │               │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘               │
└─────────────────────────────────────────────────────────────────────┘
```

**Filters:**
- Status: All, Pending Review, Under Review, Graded, Revision Requested
- Search: Name, email

**Submissions Table:**

| Column | Content |
|--------|---------|
| Attendee | Name, email |
| Submitted | Date/time, "Late" badge if applicable |
| Status | Submitted, Under Review, Approved, Rejected, Revision Requested |
| Score | Points or Pass/Fail indicator |
| Actions | Review, View History |

---

### Submission Review (Grading Interface)
**URL:** `/events/{event_id}/assignments/{id}/submissions/{submission_id}`

**Layout:**
```
┌─────────────────────────────────────────────────────────────────────┐
│  [← Back to Submissions]           [Previous] [Next Pending]        │
│                                                                     │
│  Attendee: Jane Smith (jane@example.com)                           │
│  Submitted: Jan 15, 2025 at 3:45 PM  ⚠️ Late (2 hours)             │
│  Version: 2 (resubmission)                                          │
│                                                                     │
│  ┌─────────────────────────────┐  ┌───────────────────────────────┐│
│  │ Submission                  │  │ Grading                       ││
│  │                             │  │                               ││
│  │ [Submitted content here]    │  │ Status: [Under Review ▼]      ││
│  │                             │  │                               ││
│  │ Files:                      │  │ Rubric Scoring:               ││
│  │ 📎 report.pdf (2.3 MB)     │  │ □ Content Quality: [__]/25    ││
│  │ 📎 data.xlsx (450 KB)      │  │ □ Analysis:       [__]/25     ││
│  │                             │  │ □ Presentation:   [__]/25     ││
│  │ Text Response:              │  │ □ Citations:      [__]/25     ││
│  │ "Lorem ipsum dolor sit..."  │  │                               ││
│  │                             │  │ Total: 0/100                  ││
│  │ [View Full Submission]      │  │ Late Penalty: -10%            ││
│  │                             │  │ Final Score: 0/100            ││
│  │                             │  │                               ││
│  │                             │  │ Feedback (visible to student):││
│  │                             │  │ [____________________]        ││
│  │                             │  │                               ││
│  │                             │  │ Internal Notes:               ││
│  │                             │  │ [____________________]        ││
│  │                             │  │                               ││
│  │                             │  │ [Request Revision] [Approve]  ││
│  └─────────────────────────────┘  └───────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

**Grading Actions:**

| Action | Result |
|--------|--------|
| Save Progress | Save score/feedback without changing status |
| Request Revision | Status → Revision Requested, notify attendee |
| Approve | Status → Approved, score finalized |
| Reject | Status → Rejected, does not pass |

---

### Attendee Learning Dashboard
**URL:** `/events/{event_id}/learn` (attendee view)

**Shown when:** Attendee is registered and event has modules enabled.

**Layout:**
```
┌─────────────────────────────────────────────────────────────────────┐
│  Course: Advanced Data Analysis Workshop                            │
│                                                                     │
│  Your Progress                                                      │
│  ████████████░░░░░░░░░░░░░░░░░  45% Complete                       │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ ✅ Module 1: Introduction                      Completed    │   │
│  │    └─ 4/4 items complete                                    │   │
│  ├─────────────────────────────────────────────────────────────┤   │
│  │ 🔄 Module 2: Data Fundamentals                 In Progress  │   │
│  │    └─ 2/5 items complete • Assignment due Jan 20           │   │
│  ├─────────────────────────────────────────────────────────────┤   │
│  │ 🔒 Module 3: Advanced Techniques               Locked       │   │
│  │    └─ Complete Module 2 to unlock                           │   │
│  ├─────────────────────────────────────────────────────────────┤   │
│  │ 🔒 Module 4: Final Project                     Locked       │   │
│  │    └─ Available Feb 1, 2025                                 │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Assignments                                                        │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ ✅ Module 1 Quiz              100/100    Passed             │   │
│  │ ⏳ Data Analysis Report       Due Jan 20  [Start →]         │   │
│  │ 🔒 Final Project              Due Feb 15  Locked            │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

**Module States:**
- ✅ Completed — All required content viewed, assignments passed
- 🔄 In Progress — Started but not complete
- 🔓 Available — Can start
- 🔒 Locked — Prerequisites not met or not yet released

---

### Module Content Viewer (Attendee)
**URL:** `/events/{event_id}/learn/modules/{module_id}`

**Layout:**
```
┌─────────────────────────────────────────────────────────────────────┐
│  Module 2: Data Fundamentals                                        │
│  ─────────────────────────────────────────────────────────────────  │
│  Progress: 2/5 complete                                             │
│                                                                     │
│  Content:                                                           │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ ✅ 1. Introduction Video (5:30)              [Rewatch]      │   │
│  │ ✅ 2. Reading: Key Concepts (PDF)            [Review]       │   │
│  │ ▶️ 3. Tutorial: Data Cleaning (12:45)        [Continue]     │   │
│  │ ○  4. Practice Dataset (Download)            [Start]        │   │
│  │ ○  5. Module Quiz                            [Locked]       │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  [← Previous Module]                         [Next Module →]        │
└─────────────────────────────────────────────────────────────────────┘
```

**Content Item States:**
- ✅ Completed
- ▶️ In Progress (for video — shows resume position)
- ○ Not Started
- 🔒 Locked (requires previous items)

---

### Content Player (Attendee)
**URL:** `/events/{event_id}/learn/content/{content_id}`

**Video Player:**
```
┌─────────────────────────────────────────────────────────────────────┐
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                                                             │   │
│  │                     [Video Player]                          │   │
│  │                                                             │   │
│  │   advancement                                                │   │
│  │  ▶ ────────────●──────────────────────  5:30 / 12:45       │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Tutorial: Data Cleaning                                            │
│  Module 2: Data Fundamentals                                        │
│                                                                     │
│  [✓ Mark as Complete]     [← Previous]  [Next →]                   │
└─────────────────────────────────────────────────────────────────────┘
```

**Auto-completion:** Video marks complete when 90%+ watched.

**Document Viewer:**
- Embedded PDF viewer
- Download option
- Manual "Mark as Complete" button

**Text Content:**
- Rendered HTML/Markdown
- Manual "Mark as Complete" button

---

### Assignment Submission (Attendee)
**URL:** `/events/{event_id}/learn/assignments/{assignment_id}`

**States:**

**Not Started:**
```
┌─────────────────────────────────────────────────────────────────────┐
│  Data Analysis Report                                               │
│  Due: January 20, 2025 at 11:59 PM                                 │
│                                                                     │
│  Instructions:                                                      │
│  Analyze the provided dataset and submit a written report...        │
│                                                                     │
│  Requirements:                                                      │
│  • File types: PDF, DOCX                                           │
│  • Max file size: 10 MB                                            │
│  • Word count: 1000-2000 words                                     │
│                                                                     │
│  Resources:                                                         │
│  📎 Dataset.xlsx    📎 Rubric.pdf                                  │
│                                                                     │
│  [Start Assignment]                                                 │
└─────────────────────────────────────────────────────────────────────┘
```

**Draft/Submission Form:**
```
┌─────────────────────────────────────────────────────────────────────┐
│  Data Analysis Report                           Draft saved 2m ago  │
│  Due: January 20, 2025 at 11:59 PM (3 days remaining)              │
│                                                                     │
│  Your Submission:                                                   │
│                                                                     │
│  File Upload:                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  📎 my_report_v2.pdf (2.3 MB)                    [Remove]   │   │
│  │  [+ Add Another File]                                       │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Additional Comments (optional):                                    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                                                             │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  [Save Draft]                                    [Submit Assignment]│
└─────────────────────────────────────────────────────────────────────┘
```

**Submitted (Awaiting Grade):**
```
┌─────────────────────────────────────────────────────────────────────┐
│  Data Analysis Report                                ⏳ Under Review│
│                                                                     │
│  Submitted: January 19, 2025 at 4:30 PM                            │
│                                                                     │
│  Your Submission:                                                   │
│  📎 my_report_v2.pdf (2.3 MB)                                      │
│                                                                     │
│  Status: Awaiting review by instructor                              │
└─────────────────────────────────────────────────────────────────────┘
```

**Revision Requested:**
```
┌─────────────────────────────────────────────────────────────────────┐
│  Data Analysis Report                         ⚠️ Revision Requested│
│                                                                     │
│  Feedback from Instructor:                                          │
│  "Please expand on the methodology section and include citations."  │
│                                                                     │
│  Original Submission:                                               │
│  📎 my_report_v2.pdf                                               │
│                                                                     │
│  Resubmission Due: January 25, 2025                                │
│                                                                     │
│  [Resubmit Assignment]                                              │
└─────────────────────────────────────────────────────────────────────┘
```

**Graded (Approved):**
```
┌─────────────────────────────────────────────────────────────────────┐
│  Data Analysis Report                                    ✅ Passed  │
│                                                                     │
│  Score: 85/100                                                      │
│                                                                     │
│  Rubric Breakdown:                                                  │
│  • Content Quality:    22/25                                        │
│  • Analysis:           23/25                                        │
│  • Presentation:       20/25                                        │
│  • Citations:          20/25                                        │
│                                                                     │
│  Feedback:                                                          │
│  "Great analysis! Consider adding more visualizations next time."   │
│                                                                     │
│  Your Submission:                                                   │
│  📎 my_report_v2.pdf                                               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Recordings

### Tab: Recordings (Organizer)
**URL:** `/events/{event_id}/recordings`

**Shown when:** Event has at least one recording OR event is completed.

**Header:**
```
┌─────────────────────────────────────────────────────────────────────┐
│  Recordings (2)                                                     │
│  ─────────────────────────────────────────────────────────────────  │
│  Recordings are automatically captured from Zoom cloud recording.   │
└─────────────────────────────────────────────────────────────────────┘
```

**Recording List:**

| Element | Details |
|---------|---------|
| Recording Card | Date, duration, file size, status |
| Status | Processing, Available, Expired, Published |
| Published Badge | 🌐 if published |
| Thumbnail | Auto-generated or custom |
| Stats | Views, unique viewers |
| Actions | Publish/Unpublish, Settings, Delete |

**No Recordings State:**
```
No Recordings Yet
─────────────────
Recordings will appear here after your event ends 
(if cloud recording was enabled in Zoom).

Zoom typically processes recordings within 1-2 hours.

[Configure Zoom Recording Settings]
```

---

### Recording Settings Modal

**Trigger:** Click "Settings" on a recording

```
Recording Settings
──────────────────

Title: [Event Recording - Jan 15, 2025_____]

Description (optional):
[________________________________]
[________________________________]

Access Level:
(•) Registered attendees only
( ) Attended event only
( ) Certificate holders only
( ) Public (anyone with link)

☑ Require password for access
Password: [auto-generated____] [Regenerate]

Thumbnail:
[Current thumbnail preview]
[Upload Custom] [Use Auto-generated]

[Cancel]                              [Save Settings]
```

---

### Recording Analytics
**URL:** `/events/{event_id}/recordings/{recording_id}/analytics`

| Section | Content |
|---------|---------|
| Summary | Total views, unique viewers, avg watch time |
| Completion | % who watched 90%+ |
| Watch Time Chart | Views over time |
| Viewer List | Name, views, watch time, completed |
| Export | CSV of viewer data |

---

### Recording Viewer (Attendee)
**URL:** `/events/{event_id}/recording` or `/events/{event_id}/recordings/{id}`

**Access Check:** Verify attendee meets access level requirements.

**Layout:**
```
┌─────────────────────────────────────────────────────────────────────┐
│  Event Recording: Data Analysis Workshop                            │
│  Recorded: January 15, 2025 • Duration: 1h 23m                     │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                                                             │   │
│  │                     [Video Player]                          │   │
│  │                                                             │   │
│  │  ▶ ────────────●──────────────────────  45:30 / 1:23:00    │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Available Files:                                                   │
│  📹 Video (MP4) - 1.2 GB        [Download]                         │
│  🎧 Audio Only (M4A) - 85 MB    [Download]                         │
│  💬 Chat Log (TXT)              [Download]                         │
│  📝 Transcript (VTT)            [Download]                         │
│                                                                     │
│  [← Back to Event]                                                  │
└─────────────────────────────────────────────────────────────────────┘
```

**Access Denied State:**
```
Recording Not Available
───────────────────────
This recording is only available to [attendees who attended the live event].

You registered but did not attend.

[Contact Organizer]
```

---

## Multi-Session Events

Multi-session events (courses, series, workshops) contain multiple scheduled sessions, each with its own Zoom meeting and attendance tracking.

### Event Type Selection
**Location:** Create Event form, first field

```
Event Type
──────────
(•) Single Session
    One date/time, one Zoom meeting

( ) Multi-Session (Course/Series)
    Multiple sessions over days/weeks
```

---

### Multi-Session Event Creation
**URL:** `/events/new?type=multi-session`

**Additional Sections:**

#### Sessions Section
```
Sessions
────────
Add the individual sessions for this course.

┌─────────────────────────────────────────────────────────────────────┐
│  Session 1: Introduction                                            │
│  📅 Jan 15, 2025 • 2:00 PM - 3:30 PM EST                          │
│  [Edit] [Remove]                                                    │
├─────────────────────────────────────────────────────────────────────┤
│  Session 2: Fundamentals                                            │
│  📅 Jan 22, 2025 • 2:00 PM - 3:30 PM EST                          │
│  [Edit] [Remove]                                                    │
├─────────────────────────────────────────────────────────────────────┤
│  Session 3: Advanced Topics                                         │
│  📅 Jan 29, 2025 • 2:00 PM - 3:30 PM EST                          │
│  [Edit] [Remove]                                                    │
└─────────────────────────────────────────────────────────────────────┘

[+ Add Session]  [+ Add Multiple Sessions]
```

**Add Session Modal:**

| Field | Type | Required |
|-------|------|----------|
| Session Title | Text | Yes |
| Date | Date picker | Yes |
| Start Time | Time picker | Yes |
| Duration | Dropdown | Yes |
| Description | Textarea | No |
| Create Zoom Meeting | Toggle | Default on |

**Add Multiple Sessions (Recurring):**

| Field | Options |
|-------|---------|
| Recurrence | Weekly, Bi-weekly |
| Day of Week | Mon-Sun |
| Start Time | Time picker |
| Duration | Dropdown |
| Number of Sessions | Number |
| Starting | Date picker |

---

### Multi-Session Event Detail (Organizer)
**URL:** `/events/{event_id}`

**Header shows aggregate stats:**
```
┌─────────────────────────────────────────────────────────────────────┐
│  Data Analysis Course (4 sessions)                                  │
│  📅 Jan 15 - Feb 5, 2025 • Wednesdays 2:00 PM EST                  │
│                                                                     │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐               │
│  │   45    │  │  82%    │  │   36    │  │    0    │               │
│  │Enrolled │  │Avg Att. │  │Completed│  │Certified│               │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘               │
└─────────────────────────────────────────────────────────────────────┘
```

**Tabs adjusted:**
```
Overview | Sessions | Registrations | Attendance | Modules | Certificates | Settings
```

---

### Tab: Sessions
**URL:** `/events/{event_id}/sessions`

| Element | Details |
|---------|---------|
| Session Row | Title, date/time, status, attendance |
| Status | Upcoming, Live, Completed |
| Attendance | "32/45 attended (71%)" |
| Actions | Edit, Start Meeting (host), View Attendance |
| Add Session | For adding additional sessions |

**Session Timeline View:**
```
┌─────────────────────────────────────────────────────────────────────┐
│  Session Timeline                                                   │
│                                                                     │
│  Jan 15 ─●─ Session 1: Introduction           ✅ Completed (89%)   │
│          │                                                         │
│  Jan 22 ─●─ Session 2: Fundamentals           ✅ Completed (85%)   │
│          │                                                         │
│  Jan 29 ─◉─ Session 3: Advanced Topics        🔴 Live Now          │
│          │                                                         │
│  Feb 5  ─○─ Session 4: Final Workshop         ○ Upcoming           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

### Session Detail
**URL:** `/events/{event_id}/sessions/{session_id}`

| Section | Content |
|---------|---------|
| Session Info | Title, date/time, description |
| Zoom Meeting | Meeting ID, links (same as single event) |
| Attendance | Session-specific attendance list |
| Recording | Session recording (if available) |

---

### Multi-Session Attendance Tab
**URL:** `/events/{event_id}/attendance`

**Aggregate View:**
```
┌─────────────────────────────────────────────────────────────────────┐
│  Overall Attendance                                                 │
│                                                                     │
│  Completion Requirement: Attend 3 of 4 sessions (75%)               │
│                                                                     │
│  Attendee          │ S1  │ S2  │ S3  │ S4  │ Total │ Eligible │   │
│  ──────────────────┼─────┼─────┼─────┼─────┼───────┼──────────│   │
│  Jane Smith        │ ✅  │ ✅  │ ✅  │  -  │ 3/3   │    ✅    │   │
│  John Doe          │ ✅  │ ✅  │  -  │  -  │ 2/3   │    ⏳    │   │
│  Alice Johnson     │ ✅  │  ❌ │ ✅  │  -  │ 2/3   │    ⏳    │   │
│  Bob Williams      │  ❌ │  ❌ │  -  │  -  │ 0/3   │    ❌    │   │
└─────────────────────────────────────────────────────────────────────┘

Legend: ✅ Attended  ❌ Missed  - Upcoming  ⏳ In Progress
```

**Certificate Eligibility Settings:**

| Setting | Description |
|---------|-------------|
| Minimum Sessions | Must attend X sessions |
| Minimum Percentage | Must attend X% of sessions |
| Specific Required | Must attend specific sessions |

---

### Attendee Multi-Session View
**URL:** `/events/{event_id}` (attendee, multi-session)

```
┌─────────────────────────────────────────────────────────────────────┐
│  Data Analysis Course                                               │
│                                                                     │
│  Your Progress: 2/4 sessions attended                               │
│  Certificate Requirement: Attend at least 3 sessions               │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ ✅ Session 1: Introduction                     Attended     │   │
│  │    Jan 15, 2025 • Recording available                       │   │
│  ├─────────────────────────────────────────────────────────────┤   │
│  │ ✅ Session 2: Fundamentals                     Attended     │   │
│  │    Jan 22, 2025 • Recording available                       │   │
│  ├─────────────────────────────────────────────────────────────┤   │
│  │ 📅 Session 3: Advanced Topics                  Upcoming     │   │
│  │    Jan 29, 2025 at 2:00 PM EST                              │   │
│  │    [Add to Calendar] [Join Meeting]                         │   │
│  ├─────────────────────────────────────────────────────────────┤   │
│  │ 📅 Session 4: Final Workshop                   Upcoming     │   │
│  │    Feb 5, 2025 at 2:00 PM EST                               │   │
│  │    [Add to Calendar]                                        │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Waitlist Management

### Registration Waitlist (within Registrations Tab)
**URL:** `/events/{event_id}/registrations?tab=waitlist`

**Sub-tabs in Registrations:**
```
[Confirmed (45)] [Waitlist (12)] [Cancelled (3)]
```

**Waitlist View:**

| Element | Details |
|---------|---------|
| Header | "Waitlist (12)" + "Promote All Available" |
| Position Column | #1, #2, #3... |
| Attendee Info | Name, email, joined waitlist date |
| Actions | Promote (move to confirmed), Remove |
| Auto-promote Toggle | Settings to auto-promote when spots open |

**Waitlist Table:**
```
┌─────────────────────────────────────────────────────────────────────┐
│  Waitlist (12)                     [⚙ Auto-Promote Settings]       │
│                                                                     │
│  # │ Name            │ Email              │ Joined      │ Actions  │
│  ──┼─────────────────┼────────────────────┼─────────────┼──────────│
│  1 │ Sarah Connor    │ sarah@email.com    │ Jan 10      │ [Promote]│
│  2 │ Mike Ross       │ mike@email.com     │ Jan 10      │ [Promote]│
│  3 │ Rachel Green    │ rachel@email.com   │ Jan 11      │ [Promote]│
│  ...                                                                │
└─────────────────────────────────────────────────────────────────────┘

[Promote Selected]  [Export Waitlist]
```

**Auto-Promote Settings Modal:**
```
Auto-Promote Settings
─────────────────────

When a spot becomes available:
(•) Automatically promote next person in line
( ) Notify me to manually promote
( ) Do nothing

Notification to promoted attendee:
☑ Send confirmation email
☑ Include calendar invite

[Cancel]  [Save]
```

---

### Attendee Waitlist View
**URL:** `/events/{event_id}` (when user is waitlisted)

```
┌─────────────────────────────────────────────────────────────────────┐
│  Data Analysis Workshop                                             │
│  📅 January 15, 2025 at 2:00 PM EST                                │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  ⏳ You're on the Waitlist                                  │   │
│  │                                                             │   │
│  │  Position: #3 of 12                                         │   │
│  │  Joined: January 10, 2025                                   │   │
│  │                                                             │   │
│  │  You'll be notified if a spot becomes available.           │   │
│  │                                                             │   │
│  │  [Leave Waitlist]                                           │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Event Details:                                                     │
│  ...                                                                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Settings Screens

### Settings Layout
**URL:** `/settings/*`

**Sidebar Navigation:**
- Profile
- CPD Requirements
- Security
- Integrations (organizers)
- Notifications
- Subscription (organizers)
- Account

---

### Profile Settings
**URL:** `/settings/profile`

| Field | Type | Notes |
|-------|------|-------|
| Profile Photo | Upload | Crop tool |
| Full Name | Text | Required |
| Professional Title | Text | e.g., "Senior Consultant" |
| Credentials | Text | e.g., "MD, PhD, FACP" |
| Organization | Text | For display on certificates |
| Bio | Textarea | Optional, for public profile |
| Public Profile | Toggle | Allow profile to be viewed |

---

### CPD Requirements Settings
**URL:** `/settings/cpd`

Configure annual CPD/CE credit requirements for progress tracking.

**Layout:**
```
┌─────────────────────────────────────────────────────────────────────┐
│  CPD Requirements                              [+ Add Requirement]  │
│  ─────────────────────────────────────────────────────────────────  │
│  Track your progress toward annual continuing education goals.      │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ CME (Continuing Medical Education)                          │   │
│  │ 50 credits per calendar year                                │   │
│  │ Progress: 35/50 (70%)                                       │   │
│  │ [Edit] [Delete]                                             │   │
│  ├─────────────────────────────────────────────────────────────┤   │
│  │ CLE (Continuing Legal Education)                            │   │
│  │ 20 credits per fiscal year (Jul-Jun)                        │   │
│  │ Progress: 20/20 ✓ Complete                                  │   │
│  │ [Edit] [Delete]                                             │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  [+ Add Requirement]                                                │
└─────────────────────────────────────────────────────────────────────┘
```

**Add/Edit Requirement Modal:**
```
Add CPD Requirement
───────────────────

Credit Type: [CME - Continuing Medical Education ▼]
            (or enter custom type)

Annual Requirement: [50] credits

Tracking Period:
(•) Calendar Year (January - December)
( ) Fiscal Year (custom start)
( ) Rolling 12 Months

[If Fiscal Year selected]
Start Month: [July ▼]  Start Day: [1 ▼]

Optional Details:
Licensing Body: [State Medical Board________]
License Number: [MD-12345________________]
Notes: [________________________________]

[Cancel]  [Save Requirement]
```

**Empty State:**
```
No CPD Requirements Set
───────────────────────
Add your annual continuing education requirements 
to track progress toward your goals.

[+ Add Your First Requirement]
```

---

### Security Settings
**URL:** `/settings/security`

| Section | Content |
|---------|---------|
| Change Password | Current, New, Confirm fields |
| Change Email | New email field → triggers verification |
| Two-Factor Auth | Setup/manage 2FA (future) |
| Active Sessions | List with device, location, "Log out" action |
| Log Out Everywhere | Button to terminate all sessions |

---

### Integrations (Organizers)
**URL:** `/settings/integrations`

| Integration | Details |
|-------------|---------|
| Zoom | |
| → Connected | ✓ Connected as [email] — "Disconnect" |
| → Not Connected | "Connect Zoom" button → OAuth flow |
| → Error | "Connection expired" — "Reconnect" |
| Future | Google Calendar, Outlook, LMS webhooks |

**Zoom Connection States:**

**Connected:**
```
Zoom Account
────────────
✓ Connected as john@example.com

Your Zoom meetings will be created automatically when 
you publish events.

[Disconnect Zoom]
```

**Expired/Error:**
```
⚠️ Zoom Connection Expired
──────────────────────────

Your Zoom connection needs to be refreshed.

Impact:
• 2 upcoming events may not sync attendance
• New events cannot create Zoom meetings

Affected Events:
• "Data Analysis Workshop" — Jan 20
• "Leadership Training" — Jan 25

[Reconnect Zoom]
```

**Disconnecting Warning:**
```
Disconnect Zoom?
────────────────

This will:
• Stop automatic meeting creation
• Stop attendance syncing for future events
• NOT affect already-created Zoom meetings

Existing events with Zoom meetings will still work, 
but attendance won't sync automatically.

[Cancel]  [Disconnect]
```

---

### Notification Preferences
**URL:** `/settings/notifications`

| Category | Options |
|----------|---------|
| **Attendee Notifications** | |
| Event reminders | 24hr before, 1hr before |
| Certificate issued | Email toggle |
| **Organizer Notifications** | |
| New registration | Email toggle |
| Registration cancelled | Email toggle |
| Post-event summary | Email toggle |
| **Marketing** | |
| Product updates | Email toggle |
| Tips & best practices | Email toggle |

**How Reminders Work:**

```
Reminder System
───────────────

Organizers control WHEN reminders are sent:
• Configure in Event Settings: 24hr, 1hr, or custom times
• Organizer can disable reminders per event

Attendees control WHETHER they receive reminders:
• Toggle in Notification Preferences
• If disabled, no reminders for any events

Flow:
1. Organizer creates event with reminders at 24hr and 1hr
2. System schedules reminders for all registrants
3. At send time, check attendee's notify_event_reminders preference
4. Only send if attendee has reminders enabled
```

**Note:** Attendees cannot configure reminder timing—only on/off. This prevents confusion where attendees expect reminders at times the organizer didn't configure.

---

### Account Settings
**URL:** `/settings/account`

| Section | Content |
|---------|---------|
| Account Type | Attendee / Organizer — upgrade option |
| Export Data | "Download all my data" — GDPR compliance |
| Danger Zone | |
| → Downgrade | (Organizers) Revert to attendee |
| → Delete Account | Confirmation flow with password |

---

### Export Data (GDPR)
**Trigger:** Click "Download all my data"

**Process:**
1. User clicks "Export My Data"
2. System queues export job
3. Email sent when ready (typically 5-15 minutes)
4. Download link valid for 7 days

**Export Contents:**

| Data | Format | Included |
|------|--------|----------|
| Profile | JSON | Name, email, credentials, preferences |
| Registrations | JSON | All event registrations with status |
| Certificates | JSON + PDFs | Certificate data + PDF files |
| Attendance | JSON | All attendance records |
| Events (if organizer) | JSON | All events created |
| Contacts (if organizer) | JSON | All contact lists and contacts |
| Invoices | JSON + PDFs | Payment history |

**Package Format:** ZIP file containing:
```
export-2025-01-15/
├── profile.json
├── registrations.json
├── certificates/
│   ├── certificates.json
│   ├── cert-abc123.pdf
│   └── cert-def456.pdf
├── attendance.json
├── events.json (organizers)
├── contacts.json (organizers)
└── invoices/
    ├── invoices.json
    └── invoice-001.pdf
```

---

### Downgrade to Attendee

**Trigger:** Organizer clicks "Downgrade to Attendee"

**Confirmation Modal:**
```
Downgrade to Attendee?
──────────────────────

This will:
• Cancel your subscription (if active)
• Remove access to organizer features
• Keep your events accessible (read-only)
• Preserve all issued certificates

Your existing events will:
✓ Remain visible to registrants
✓ Keep all certificates valid
✓ Show as "by [Your Name]"
✗ Cannot be edited or duplicated
✗ Cannot create new events

Are you sure you want to downgrade?

[Cancel]  [Downgrade to Attendee]
```

**Business Rules:**
1. **Active events**: Block downgrade if any events are in PUBLISHED or LIVE state
2. **Subscription**: Automatically cancelled, prorated refund issued
3. **Events**: Remain in database, marked as archived
4. **Certificates**: Remain valid and verifiable
5. **Contacts**: Read-only access retained
6. **Templates**: Retained but cannot be edited or used for new events

---

## Billing & Subscription

### Subscription Overview
**URL:** `/settings/subscription`

| Section | Content |
|---------|---------|
| Current Plan | Plan name, price, billing cycle |
| Usage | Events this month, Certificates issued |
| Next Invoice | Date, amount |
| Payment Method | Card on file (last 4 digits), "Update" |
| Actions | Change plan, Cancel subscription |

---

### Plan Selection
**URL:** `/settings/subscription/plans`

| Element | Details |
|---------|---------|
| Plan Cards | Name, price, features list, CTA |
| Comparison | Feature comparison table |
| FAQ | Common billing questions |

---

### Payment Method
**URL:** `/settings/subscription/payment`

| Element | Details |
|---------|---------|
| Current Method | Card type, last 4, expiry |
| Update | Stripe/payment form embed |
| Billing Address | If required |

---

### Invoices
**URL:** `/settings/subscription/invoices`

| Element | Details |
|---------|---------|
| Invoice List | Date, Amount, Status, Download |
| Status | Paid, Pending, Failed |

---

### Subscription Status States

**Active:** Normal experience, all features available.

**Trial Ending (3 days before):**
```
┌─────────────────────────────────────────────────────────────────────┐
│ ⏰ Your trial ends in 3 days                                        │
│    Add a payment method to continue using organizer features.       │
│    [Add Payment Method]                                   [Dismiss] │
└─────────────────────────────────────────────────────────────────────┘
```
*Shown as banner on dashboard*

**Past Due (payment failed):**
```
┌─────────────────────────────────────────────────────────────────────┐
│ ⚠️ Payment Failed                                                   │
│    We couldn't process your payment. Update your payment method     │
│    to avoid service interruption.                                   │
│    [Update Payment Method]                                          │
└─────────────────────────────────────────────────────────────────────┘
```
*Shown as persistent banner. Grace period: 7 days.*

**Grace Period Behavior:**
- All features work normally
- Daily email reminders
- Banner shown on all pages

**Cancelled/Expired:**
```
┌─────────────────────────────────────────────────────────────────────┐
│  Your subscription has ended                                        │
│  ─────────────────────────────────────────────────────────────────  │
│                                                                     │
│  Your organizer features are now read-only:                        │
│  ✗ Cannot create new events                                        │
│  ✗ Cannot publish draft events                                     │
│  ✗ Cannot issue new certificates                                   │
│                                                                     │
│  You still have access to:                                          │
│  ✓ View past events and attendance                                 │
│  ✓ Download existing certificates                                  │
│  ✓ Export your data                                                │
│                                                                     │
│  [Reactivate Subscription]  [Downgrade to Attendee]                │
└─────────────────────────────────────────────────────────────────────┘
```

**Cancelled Dashboard Experience:**
- Events list shows all events (read-only)
- "Create Event" button disabled with tooltip: "Reactivate subscription to create events"
- Existing published events continue to accept registrations
- Zoom meetings continue to work
- Attendance still syncs (for already-created events)
- Cannot issue new certificates

---

## Onboarding Flows

### Attendee Onboarding

**Trigger:** First login after email verification

**Step 1: Welcome**
```
Welcome to [Platform]!
──────────────────────
Let's set up your profile so your certificates 
display your credentials correctly.

[Get Started]
```

**Step 2: Profile Setup**
- Full Name (required)
- Professional Title (optional)
- Credentials (optional)
- Organization (optional)

**Step 3a: Certificates Found (conditional)**

*Shown only if certificates exist for user's email address*

```
🎉 We Found Your Certificates!
──────────────────────────────

We found 3 certificates that were issued to your 
email address before you created an account.

┌─────────────────────────────────────────────────────────────────────┐
│ ✓ Healthcare Leadership Workshop — Jan 2024                        │
│ ✓ Patient Safety Training — Nov 2023                               │
│ ✓ Medical Documentation Course — Sep 2023                          │
└─────────────────────────────────────────────────────────────────────┘

These have been automatically linked to your account.

[View My Certificates]  [Continue Setup]
```

**Step 3b: Complete (if no certificates found)**
```
You're all set!
───────────────
Your certificates will automatically appear in your 
dashboard when organizers issue them.

[Go to Dashboard]  [Browse Events]
```

**Step 4: Complete (if certificates were found)**
```
You're all set!
───────────────
Your 3 certificates are ready to view in your dashboard.
Future certificates will appear automatically.

[Go to Dashboard]  [Browse Events]
```

---

### Organizer Onboarding

**Trigger:** After clicking "Become an Organizer" or first organizer login

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

[Skip for Now] — you can connect later in Settings
```

**Step 3: Upload Template (Optional)**
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
✓ Account upgraded to Organizer
✓ Zoom connected (or skipped)
✓ Template ready

[Create Your First Event]
```

**Checklist (Persistent until complete):**
Shows in dashboard until all items done:
- [ ] Connect Zoom
- [ ] Upload certificate template
- [ ] Create first event

---

## Event State Machine

### States

```
                    ┌──────────┐
                    │  DRAFT   │
                    └────┬─────┘
                         │ publish
                         ▼
                    ┌──────────┐
         ┌─────────│ PUBLISHED│─────────┐
         │         └────┬─────┘         │
         │ cancel       │ event starts  │ cancel
         ▼              ▼               │
    ┌──────────┐   ┌──────────┐         │
    │CANCELLED │   │   LIVE   │         │
    └──────────┘   └────┬─────┘         │
                        │ event ends    │
                        ▼               │
                   ┌──────────┐         │
                   │ COMPLETED│◄────────┘
                   └────┬─────┘
                        │ all certificates issued
                        ▼
                   ┌──────────┐
                   │  CLOSED  │
                   └──────────┘
```

### State Behaviors

| State | Can Edit | Can Register | Can Issue Certs | Visible Actions |
|-------|----------|--------------|-----------------|-----------------|
| Draft | Everything | No | No | Publish, Delete |
| Published | Limited* | Yes | No | Edit, Cancel, Share |
| Live | Nothing | No | No | Monitor, Cancel |
| Completed | Nothing | No | Yes | Issue Certs, View |
| Closed | Nothing | No | Reissue only | View, Duplicate |
| Cancelled | Nothing | No | No | Delete, Duplicate |

*Published: Can edit description, capacity. Cannot change date/time (must cancel & recreate).

---

## Email Templates

**Phase 1:** System-controlled email templates. Content is standardized, not customizable by organizers.

**Phase 2 (Future):** Organizer email customization with template editor, custom fields, and branding.

| Email | Trigger | Content |
|-------|---------|---------|
| **Welcome** | Account created | Welcome message, verify email CTA |
| **Email Verification** | Sign up / email change | Verification link (expires 24hr) |
| **Password Reset** | Forgot password request | Reset link (expires 1hr) |
| **Registration Confirmed** | Attendee registers | Event details, calendar links |
| **Event Reminder (24hr)** | 24hr before event | Event details, join link |
| **Event Reminder (1hr)** | 1hr before event | Join link, quick details |
| **Event Cancelled** | Organizer cancels event | Cancellation notice, reason |
| **Certificate Issued** | Certificate generated | Certificate attached, dashboard link |
| **Certificate Revoked** | Organizer revokes cert | Revocation notice, reason |
| **Waitlist Joined** | Attendee joins waitlist | Position, what to expect |
| **Waitlist Promoted** | Spot becomes available | Registration confirmed, event details |
| **Assignment Due Reminder** | 24hr before due date | Assignment details, submission link |
| **Revision Requested** | Organizer requests revision | Feedback, resubmission instructions |
| **Assignment Graded** | Submission reviewed | Score, feedback summary |
| **Recording Available** | Recording published | Access link, event details |
| **Organizer: New Registration** | Attendee registers | Attendee name, event name |
| **Organizer: Event Summary** | 1hr post-event | Attendance stats, action needed |
| **Subscription Receipt** | Payment processed | Invoice details, PDF attached |
| **Payment Failed** | Payment fails | Update payment method CTA |
| **Trial Ending** | 3 days before trial ends | Upgrade prompt |

**Email Variables Available:**
- `{{attendee_name}}` — Recipient's full name
- `{{event_title}}` — Event title
- `{{event_date}}` — Formatted event date/time
- `{{organizer_name}}` — Organizer's display name
- `{{join_url}}` — Zoom join link
- `{{dashboard_url}}` — Link to attendee dashboard
- `{{certificate_url}}` — Link to certificate
- `{{unsubscribe_url}}` — One-click unsubscribe

---

## Modals & Overlays

### Add Attendee Modal
| Element | Details |
|---------|---------|
| Tabs | Single / Bulk Import |
| Single | Email input, Name (optional), "Add" |
| Bulk | File upload, column mapping, preview, "Import" |

### Issue Certificates Modal
| Step | Content |
|------|---------|
| 1. Select | Choose template from dropdown |
| 2. Preview | Show sample certificate with real data |
| 3. Confirm | "Issue to X attendees?" with checkbox for email notification |
| 4. Processing | Progress bar |
| 5. Complete | Success message, summary |

### Confirm Cancel Event
```
Cancel Event?
─────────────
This will:
• Notify all registered attendees
• Delete the Zoom meeting
• This cannot be undone

[Keep Event]  [Cancel Event]
```

### Confirm Delete Account
```
Delete Account?
───────────────
This will permanently delete:
• Your profile and all data
• All events you've created
• All certificates you've issued

Certificates issued to attendees will remain in their accounts.

Type "DELETE" to confirm:
[__________]

[Cancel]  [Delete Account]
```

### Revoke Certificate Modal
```
Revoke Certificate?
───────────────────
This certificate will be marked as invalid.
The attendee will be notified.

Reason (optional):
[__________________]

[Cancel]  [Revoke]
```

---

## Loading & Error Patterns

### Loading States

| Context | Pattern |
|---------|---------|
| Page Load | Skeleton screen matching layout |
| Data Fetch | Skeleton rows/cards in tables/grids |
| Button Action | Button shows spinner, disabled |
| Form Submit | Button shows spinner, form disabled |
| Background Sync | Subtle "Syncing..." indicator |
| Large Import | Full-page progress with status messages |

### Error States

| Context | Pattern |
|---------|---------|
| Form Validation | Inline red text below field |
| API Error | Toast notification (dismissible) |
| Page Load Fail | Full-page error with retry |
| Network Offline | Banner at top: "You're offline" |
| Permission Denied | Redirect to dashboard with toast |

### Success Feedback

| Context | Pattern |
|---------|---------|
| Form Save | Toast: "Changes saved" |
| Item Created | Redirect to item + toast |
| Item Deleted | Return to list + toast |
| Bulk Action | Toast with count: "38 certificates issued" |

### Empty States

Every list/table has a designed empty state with:
- Friendly illustration or icon
- Explanatory message
- Primary action CTA

---

## Form Specifications

### Validation Rules

| Field Type | Rules |
|------------|-------|
| Email | Required, valid format, max 254 chars |
| Password | Min 8 chars, require complexity (optional) |
| Event Title | Required, 3-100 chars |
| Event Description | Optional, max 5000 chars |
| Duration | Required, 15 min - 8 hours |
| CPD Credits | Positive number, max 2 decimal places, max 100 |
| Capacity | Positive integer, max 10,000 |
| Template Name | Required, 3-50 chars |

### Error Messages

| Scenario | Message |
|----------|---------|
| Required empty | "[Field] is required" |
| Invalid email | "Please enter a valid email address" |
| Password too short | "Password must be at least 8 characters" |
| Passwords don't match | "Passwords do not match" |
| Date in past | "Event date must be in the future" |
| Duplicate email | "An account with this email already exists" |
| Generic server error | "Something went wrong. Please try again." |

### Input Formatting

| Field | Format |
|-------|--------|
| Date | Locale-aware display, ISO storage |
| Time | 12hr with AM/PM (US) or 24hr based on locale |
| Numbers | Locale-aware separators |
| Phone | International format with country code |

---

## Mobile Behavior

### Critical Mobile Screens

| Screen | Priority | Notes |
|--------|----------|-------|
| Attendee Dashboard | High | Primary mobile use case |
| Certificate View | High | Often shared from mobile |
| Event Registration | High | May register on the go |
| Live Event Monitor | Medium | Organizers may monitor remotely |
| Create Event | Low | Desktop preferred |
| Template Editor | Low | Desktop only |

### Responsive Patterns

| Component | Desktop | Mobile |
|-----------|---------|--------|
| Tables | Full table | Card list or horizontal scroll |
| Navigation | Top bar | Bottom tab bar |
| Modals | Centered overlay | Full-screen sheet |
| Forms | Multi-column | Single column |
| Date Picker | Calendar popup | Native date input |
| File Upload | Drag-drop + click | Click only |

### Touch Considerations

- Minimum touch target: 44x44px
- Adequate spacing between interactive elements
- Swipe actions for common tasks (delete, archive)
- Pull-to-refresh on lists

### Mobile-Specific Features

| Feature | Notes |
|---------|-------|
| Share Certificate | Native share sheet (LinkedIn, save, email) |
| Add to Wallet | Apple Wallet / Google Pay pass (future) |
| Calendar Integration | Deep link to native calendar |
| Push Notifications | Event reminders, certificate issued |

---

## Accessibility Requirements

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
| Modals | Focus trap, Escape to close, return focus on close |
| Forms | Associated labels, error announcements, field descriptions |
| Tables | Proper headers, row/column associations |
| Alerts/Toasts | ARIA live regions, sufficient display time |
| Images | Alt text for informational, empty alt for decorative |
| Icons | Screen reader text for icon-only buttons |
| Loading | Announce loading state and completion |

### Testing Checklist

- [ ] Navigate entire app with keyboard only
- [ ] Use with screen reader (VoiceOver, NVDA)
- [ ] Test at 200% browser zoom
- [ ] Verify color contrast ratios
- [ ] Check focus management in modals
- [ ] Test with `prefers-reduced-motion`
