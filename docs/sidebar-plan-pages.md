# Sidebar Plan Access Audit (Frontend)

Scope: This audit lists pages reachable from the sidebar and summarizes the visible information on each page. It is based on `frontend/src/components/layout/Sidebar.tsx` and the routed pages in `frontend/src/App.tsx`. Page visibility depends on the effective role derived from subscription plan plus the org context (`currentOrg`).

Sidebar role mapping (plan -> role used for nav):
- `attendee` plan -> attendee sidebar.
- `organizer` plan -> organizer sidebar.
- `lms` plan -> course manager sidebar.
- `organization` plan -> organizer + course manager sidebar (events and courses).

Context switching:
- Personal context (no `currentOrg`): shows personal nav items.
- Organization context (`currentOrg` set): hides personal items and shows org nav items, plus shared `Profile`.
- The manifest route filter can still hide items at runtime if the backend does not allow a route.

---

## Personal Context: Attendee Plan

Dashboard (`/dashboard`, `AttendeeDashboard`): welcome hero, pending invitations banner, stats cards (Total Credits, Certificates, Upcoming Events, Learning Hours), upcoming events list with Join Session and View Details actions, organizer upsell card for becoming an organizer.

Browse Events (`/events`, `EventsPage` -> `EventDiscovery`): filter sidebar (event type, format, registration fee), search and sort bar, results grid of public event cards with date, type, description, CPD credits, status/format badges, and link to event detail.

Browse Courses (`/courses`, `CourseCatalogPage`): public course catalog with search, category/filters (if implemented), and cards linking to course detail.

My Registrations (`/registrations`, `MyRegistrationsPage`): table of registrations (event title/date, registration date, status badge, payment status badge), actions to view event, pay now/retry payment, leave/edit feedback for past events; “Missing Events” card to link historical registrations; feedback modal for event ratings.

My Courses (`/my-courses`, `MyCoursesPage`): enrolled course cards with progress bars, status badges, continue/review action, certificate shortcut; empty state with browse courses CTA.

My Certificates (`/certificates`, `CertificatesPage`): search input, table of certificates (event, certificate ID, issued date, CPD credits, status), actions to view, share, and download PDF; empty state with call to browse events.

Profile (`/settings`, `ProfileSettings`): tabs for General (profile fields, avatar), Billing (payment methods via Stripe portal), Security (change password), Notifications (toggle preferences). Subscription status and Payouts tabs are not shown for attendee.

---

## Personal Context: Organizer Plan

Dashboard (`/dashboard`, `OrganizerDashboard`): page header with Create Event, pending invitations banner, onboarding checklist, stats (Total Events, Active Events, Total Registrations, Certificates Issued), recent events table with manage/edit actions, quick action cards, Zoom integration status card with connect/disconnect.

My Events (`/events`, `EventsPage`): organizer event grid with status badges, date/format, organization badge, Create Event button, and per-event actions (View & Manage, Edit, Duplicate, Delete).

Certificates (`/organizer/certificates`, `OrganizerCertificatesPage`): tabs for Issued Certificates (filters by event, search by recipient/ID, table with status and View action) and Templates (certificate template manager list).

Zoom Meetings (`/organizer/zoom`, `ZoomManagement`): connection status card, connect/disconnect actions, meetings table (event, date, meeting ID with copy, status, copy/open join URL). Empty state when no meetings.

Contacts (`/organizer/contacts`, `ContactsPage`): search, tag filter, contacts table with name/email, org/title, tags, status (active/opted out/bounced), event counts; actions to edit, email, delete; import/export and add contact dialogs.

Billing (`/billing`, `BillingPage`): current plan card, change plan dialog, usage metrics (events, certificates, status, renewal date), cancel/reactivate, Stripe portal link, payment methods management card, invoice history table with download links.

Profile (`/settings`, `ProfileSettings`): General, Billing (payment methods + subscription status), Security, Notifications, and Payouts (Stripe Connect status and dashboard links). Organizer and course manager accounts see subscription status and payouts.

---

## Personal Context: LMS Plan (Course Manager)

Dashboard (`/dashboard`, `CourseManagerDashboard`): header with Manage Courses and Create New Course, pending invitations banner, onboarding checklist, stats (Total Courses, Published, Enrollments, Completions), recent courses table with status and enrollment/completion counts.

Browse Courses (`/courses`, `CourseCatalogPage`): public course catalog with search, category/filters (if implemented), and cards linking to course detail.

My Courses (`/my-courses`, `MyCoursesPage`): enrolled course cards with progress bars, start/finish dates, status badges, continue/review action, certificate shortcut; empty state with browse courses button.

Manage Courses (`/courses/manage`, `OrgCoursesPage` in personal mode): tabs (All, Published, Drafts, Archived), search, table of courses (title, status, enrollments, module count, created date), actions to manage course, view public page, and delete draft courses (confirm dialog).

Course Certificates (`/courses/certificates`, `CourseCertificatesPage`): summary cards for issued certificates, certified learners, and courses with certificates; searchable/filterable table of issued course certificates with learner info and issued date.

Billing (`/billing`, `BillingPage`): current plan card, change plan dialog, usage metrics (courses, certificates, status, renewal date), cancel/reactivate, Stripe portal link, payment methods management card, invoice history table.

Profile (`/settings`, `ProfileSettings`): General, Billing (payment methods + subscription status), Security, Notifications, and Payouts tabs.

---

## Personal Context: Organization Plan

Sidebar behavior: the organization plan shows both organizer and course manager items. Personal context pages mirror the Organizer + LMS sections above unless the user is in an organization context.

---

## Organization Context: Any Plan with `currentOrg`

Overview (`/org/:slug`, `OrganizationDashboard`): org header with logo/verification badge, description; stats cards (Team Members, Events, Courses); tabs for Overview (quick actions, team preview), Events (org events overview for admins), Courses (org courses overview for admins), Team (team management), Certificates (template management CTA), and Settings (admin-only organization settings).

Events (`/org/:slug/events`, `OrgEventsPage`): admin view shows OrgEventsOverview table with search, status filter, registrations count, and Manage action; non-admin view shows a message and link back to personal events.

Courses (`/org/:slug/courses`, `OrgCoursesPage` in org mode): tabs (All, Published, Drafts, Archived), search, table of courses (title, status, enrollments, module count, created date), actions to manage course or view public page, Create Course button for managers.

Team & Subscription (`/org/:slug/team`, `TeamManagementPage`): subscription usage card (seat counts, estimated monthly total, manage billing), members list with roles and statuses, invite dialog with role and billing payer selection, role edit dialog, re-invite and remove actions.

Settings (`/org/:slug/settings`, `OrganizationSettingsPage`): tabs for General (org name, description, website, contact details, GST/HST), Branding (logo preview, primary/secondary colors, preview), Payments & Payouts (Stripe Connect settings). Editing is admin-only.

Profile (`/settings`, `ProfileSettings`): same account settings page described above, always available as a shared item.

---

## Notes and Known Mismatches

- Some page logic still uses `user.account_type` (not subscription plan) for content switching, notably `DashboardPage` and `EventsPage`. If account_type is stale after plan changes, the sidebar may show LMS or organizer items while those pages render attendee or organizer content based on account_type.
- Organization plan currently shows organizer nav only, even though the plan enables courses. Course manager items (`My Courses`, `Manage Courses`) do not appear in the sidebar for the organization plan.
