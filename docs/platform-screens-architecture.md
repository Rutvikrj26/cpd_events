# Platform Screens & Information Architecture

## Public Screens

### Landing Page
| Section | Content |
|---------|---------|
| Hero | Value prop, CTA: "Sign Up" / "Login" |
| Features | Zoom integration, attendance tracking, certificates, CPD tracking |
| How It Works | 3-step visual flow |
| Pricing | Subscription tiers (if shown publicly) |
| Footer | Links, legal, contact |

### Sign Up
| Element | Details |
|---------|---------|
| Form Fields | Email, password, confirm password |
| OAuth Options | Google sign-in (optional) |
| Terms | Checkbox for terms & privacy |
| CTA | "Create Account" |
| Link | "Already have an account? Login" |

### Login
| Element | Details |
|---------|---------|
| Form Fields | Email, password |
| Options | "Remember me" checkbox |
| Links | "Forgot password?", "Sign up" |
| OAuth | Google sign-in (if enabled) |

### Email Verification
| Element | Details |
|---------|---------|
| State: Pending | "Check your email" message, resend link |
| State: Success | "Email verified!" → redirect to profile setup |
| State: Expired | "Link expired" → resend option |

### Forgot Password
| Element | Details |
|---------|---------|
| Form | Email input |
| Success State | "Check your email for reset link" |

### Reset Password
| Element | Details |
|---------|---------|
| Form | New password, confirm password |
| Validation | Password strength indicator |

### Certificate Verification (Public)
| Element | Details |
|---------|---------|
| URL | `/verify/{certificate_code}` |
| Display | Certificate holder name, event name, date, issuing organizer, CPD credits |
| Status | Valid / Revoked badge |
| Branding | Organizer logo (if available) |

---

## Attendee Screens

### Profile Setup (Post-Verification)
| Element | Details |
|---------|---------|
| Form Fields | Full name, professional title, credentials/designations |
| Optional | Profile photo, organization (free text) |
| CTA | "Complete Setup" |

### Attendee Dashboard
| Section | Content |
|---------|---------|
| Header | Welcome message, profile summary |
| CPD Summary | Total credits by type, current period |
| Certificates List | Filterable table/grid |
| Filters | Date range, organizer, CPD type, search |
| Each Certificate Row | Event name, organizer, date, CPD credits, status, actions (view/download) |
| Empty State | "No certificates yet" message |
| CTA | "Become an Organizer" upgrade prompt |

### Certificate Detail (Attendee View)
| Section | Content |
|---------|---------|
| Certificate Preview | Visual preview of certificate PDF |
| Details | Event name, date, organizer, CPD type, credits |
| Actions | Download PDF, copy share link, view verification page |
| Metadata | Issued date, certificate ID |

### CPD Tracking
| Section | Content |
|---------|---------|
| Summary Cards | Credits by type (CME, CLE, CPE, etc.) |
| Period Selector | Current year, custom range |
| Breakdown Table | List by CPD type with totals |
| Export | Download CPD summary report |

---

## Organizer Screens

### Organizer Dashboard
| Section | Content |
|---------|---------|
| Stats Cards | Total events, upcoming events, certificates issued, total attendees |
| Upcoming Events | List with date, time, registration count |
| Recent Activity | Latest registrations, issued certificates |
| Quick Actions | "Create Event", "View Reports" |

### Create Event
| Section | Fields |
|---------|--------|
| Basic Info | Title, description |
| Date & Time | Start datetime, duration, timezone |
| Zoom Settings | Auto-create meeting toggle, waiting room, passcode |
| CPD Configuration | Credit type (dropdown), credit value (number) |
| Registration | Open/closed, capacity limit (optional) |
| Certificate | Select template, auto-issue toggle |
| Actions | "Save Draft", "Publish" |

### Edit Event
| Section | Content |
|---------|---------|
| Same as Create | Pre-populated fields |
| Status | Draft / Published / Completed / Cancelled |
| Danger Zone | Cancel event (with confirmation) |

### Event Detail (Organizer View)
| Section | Content |
|---------|---------|
| Header | Event title, status badge, date/time |
| Stats | Registered, attended, certificates issued |
| Tabs | Overview, Attendees, Attendance, Certificates |

#### Event Tab: Overview
| Element | Details |
|---------|---------|
| Event Info | Description, Zoom link, CPD details |
| Quick Actions | Edit event, send reminder, copy invite link |
| Zoom Details | Meeting ID, passcode, host link |

#### Event Tab: Attendees (Registered)
| Element | Details |
|---------|---------|
| Attendee List | Name, email, registration date, status |
| Actions | Add attendee (email/CSV), remove, resend invite |
| Bulk Actions | Select all, send bulk reminder |
| Search | Filter by name/email |

#### Event Tab: Attendance
| Element | Details |
|---------|---------|
| Attendance List | Name, email, join time, leave time, duration, eligible (Y/N) |
| Manual Override | Mark as attended, mark as not attended |
| Threshold Setting | Minimum duration for eligibility |
| Import | Manual CSV import (fallback) |

#### Event Tab: Certificates
| Element | Details |
|---------|---------|
| Status | Not issued / Partially issued / All issued |
| Eligible List | Attendees eligible for certificates |
| Template Selection | Choose from available templates |
| Actions | "Issue to All", "Issue Selected", "Preview" |
| Issued List | Certificates issued with download/revoke options |

### Live Event Monitor
| Section | Content |
|---------|---------|
| Header | Event name, live status indicator |
| Current Count | Attendees currently in meeting |
| Activity Feed | Real-time join/leave log |
| Attendee List | Who's currently in, duration so far |

### Templates Management
| Section | Content |
|---------|---------|
| Templates List | Grid/list of templates with preview thumbnails |
| Each Template | Name, preview, created date, usage count |
| Actions | Edit, duplicate, delete, set as default |
| Upload | "Add Template" with file upload |

### Template Editor / Upload
| Section | Content |
|---------|---------|
| Upload | PDF/image upload for background |
| Field Mapping | Drag/position: attendee name, event name, date, CPD credits, certificate ID |
| Preview | Live preview with sample data |
| Settings | Name, default toggle |

### Contacts Management
| Section | Content |
|---------|---------|
| Contact Lists | List of saved lists |
| Each List | Name, contact count, created date |
| Actions | Create list, edit, delete, export |

### Contact List Detail
| Section | Content |
|---------|---------|
| Contacts Table | Name, email, added date |
| Actions | Add contact, import CSV, remove selected |
| Bulk Actions | Export, delete list |

### Reports
| Section | Content |
|---------|---------|
| Date Range | Filter by period |
| Summary Stats | Events held, total attendees, certificates issued, attendance rate |
| Events Table | Event name, date, registered, attended, attendance %, certs issued |
| Export | Download CSV/PDF report |

---

## Settings Screens

### Settings Layout
| Element | Details |
|---------|---------|
| Sidebar | Profile, Security, Integrations, Notifications, Account |
| Content Area | Selected settings section |

### Profile Settings
| Fields | Details |
|--------|---------|
| Profile Photo | Upload/change |
| Full Name | Text input |
| Professional Title | Text input |
| Credentials | Text input (e.g., "MD, PhD") |
| Email | Display only (change via security) |

### Security Settings
| Section | Content |
|---------|---------|
| Change Password | Current password, new password, confirm |
| Change Email | New email → verification required |
| Sessions | Active sessions list, logout others |

### Integrations (Organizers Only)
| Integration | Details |
|-------------|---------|
| Zoom | Connection status, connected account email, "Connect" / "Disconnect" button |
| Future | Placeholder for additional integrations |

### Notification Preferences
| Category | Options |
|----------|---------|
| Event Reminders | Email toggle |
| Certificate Issued | Email toggle |
| Marketing | Email toggle |
| Organizer Notifications | New registration, attendance summary (organizers only) |

### Account Settings
| Section | Content |
|---------|---------|
| Subscription | Current plan, billing info (organizers) |
| Export Data | Download all my data |
| Danger Zone | Delete account (with confirmation flow) |

---

## Email Screens (Templates)

| Email | Content |
|-------|---------|
| Welcome | Account created, verify email link |
| Email Verification | Verification link |
| Password Reset | Reset link |
| Event Invitation | Event details, date/time, Zoom link, add to calendar |
| Event Reminder | Same as invitation, "happening soon" messaging |
| Certificate Issued | Certificate attached/link, view in dashboard CTA |
| Organizer: New Registration | Attendee name registered for event |
| Organizer: Attendance Summary | Post-event summary stats |

---

## Modal / Overlay Components

| Modal | Content |
|-------|---------|
| Add Attendee | Email input, optional name |
| Import CSV | File upload, column mapping preview |
| Confirm Cancel Event | Warning message, "Cancel Event" / "Keep Event" |
| Confirm Delete | Generic confirmation pattern |
| Issue Certificates | Template selection, preview, confirm |
| Revoke Certificate | Reason (optional), confirm |

---

## Empty States

| Screen | Message |
|--------|---------|
| Attendee Dashboard | "You haven't received any certificates yet. They'll appear here automatically when organizers issue them." |
| Organizer Dashboard | "Create your first event to get started." |
| Events List | "No events yet. Create one!" |
| Attendance Tab | "Attendance data will appear after the event." |
| Templates | "No templates yet. Upload your first certificate template." |
| Contacts | "No contact lists yet. Create one to quickly invite attendees." |

---

## Error States

| Error | Display |
|-------|---------|
| 404 | "Page not found" with home link |
| 403 | "You don't have access to this page" |
| 500 | "Something went wrong. Please try again." |
| Zoom Disconnected | Banner: "Zoom disconnected. Reconnect to create events." |
| Event Not Found | "This event doesn't exist or has been removed." |
| Certificate Invalid | Verification page: "This certificate could not be verified." |
