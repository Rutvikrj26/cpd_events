# Admin · Live Event · Cross-cutting Flows — Test Inventory

## SECTION 1: ADMIN SURFACES

### Page/Tab: `/admin/users` — Users Tab (UserManagementPage, file: frontend/src/pages/admin/UserManagementPage.tsx)

**Purpose:** Manage institutional users (learners, organizers, instructors, admins), search, filter by role, deactivate/activate, change roles.

**Preconditions:** User authenticated with `admin` role (group membership). Role validation via RBAC `@roles("admin")` decorator (backend/src/common/rbac.py).

**Visible elements:**
- Page header: "User Management"
- Two tabs: "All Users" and "Pending Invitations"
- Search bar (by name or email)
- Role filter dropdown (All roles, Learner, Organizer, Instructor, Admin)
- Table with columns: User, Roles, Status, Last Login, Actions
- User rows show: full_name, email, roles (badges), is_active/is_inactive status, last_login_at (formatted date or "Never"), action menu
- Action buttons in header: "Send Invite" (single) and "Bulk Upload" buttons
- Action menu per row: "Deactivate"/"Activate", "Change Role"

**Interactions to test:**
1. Search by email — filters table immediately
2. Search by full name — filters table immediately
3. Role filter dropdown — filters by exact role match (includes admins who have any role)
4. Clear filters — search and filter reset to defaults
5. Click user row (name/email) — navigates to `/admin/users/<uuid>` (AdminUserDetailPage)
6. Click "Deactivate" on active user → shows error if last active admin; otherwise confirms deactivation and refreshes list
7. Click "Activate" on inactive user → re-activates and refreshes list
8. Click "Change Role" → opens dialog with user profile and role selector
9. Select new role in dialog → saves via `PUT /admin/users/<uuid>/roles/` → refreshes list
10. "Send Invite" button → opens InviteDialog modal
11. "Bulk Upload" button → opens file picker for CSV bulk invite upload
12. Pagination (if applicable) → next/prev page controls
13. Sort by Last Login — click column header to toggle asc/desc
14. Empty state — "No users found" when search/filter returns zero results
15. Loading state — "Loading..." spinner shown while fetching

**Edge cases & state variants:**
- Last admin cannot be deactivated (error toast shows "Cannot deactivate the last active admin.")
- User with no last login shows "Never"
- User with multiple roles shows all role badges
- Deactivate action blocked for self (if testing with own admin account)
- Role filter="all" includes all users regardless of group membership
- Search is case-insensitive and searches full_name or email

**State transitions triggered:**
- Deactivate: `POST /admin/users/<uuid>/deactivate/` → `is_active=False`, broadcast signal to update counts
- Role change: `POST /admin/users/<uuid>/roles/` → upsert Group memberships, record UserRoleChange audit row (backend/src/accounts/models.py:303-309)
- Email sent when user activated/deactivated (if workflow enabled)

**Cross-page navigation:**
- "All Users" → "Pending Invitations" tab: switches to invitations list
- User name → `/admin/users/<uuid>` (detail page)
- "Send Invite" modal → on success, refreshes invitations tab if currently viewing it

---

### Page/Tab: `/admin/users` — Invitations Tab (InvitationsTab within UserManagementPage)

**Purpose:** View and manage pending, accepted, expired, and revoked user invitations. Resend, revoke, inspect status.

**Preconditions:** User authenticated with `admin` role. Invitation data from `GET /admin/invitations/` API endpoint.

**Visible elements:**
- Status filter buttons: Pending, Accepted, Expired, Revoked, All
- Search bar (by email)
- Table columns: Email, Role, Status, Sent At, Expires At, Actions
- Invitation rows showing: email, assigned role (badge), status (color-coded), created/sent timestamp, expiry timestamp, action menu
- Action menu: "Resend", "Revoke", "View"
- Loading spinner when fetching
- Empty state message: "No invitations match the current filter."

**Interactions to test:**
1. Status filter "Pending" — shows only status=pending invitations
2. Status filter "Accepted" — shows only status=accepted invitations
3. Status filter "Expired" — shows only status=expired (token age > 7 days)
4. Status filter "Revoked" — shows only status=revoked invitations
5. Status filter "All" — shows all invitation statuses
6. Search by email — filters within current status
7. Click "Resend" on pending invitation → queues new email send, shows toast "Invitation re-sent to <email>"
8. Click "Resend" on accepted invitation → shows error "This invitation has already been accepted."
9. Click "Resend" on revoked invitation → shows error "This invitation has been revoked."
10. Click "Revoke" → soft-deletes invitation, prevents further resends/accepts
11. Click "View" → shows modal with full invitation details (token expiry, role, email)
12. Refresh button (icon) → manually refresh invitation list

**Edge cases & state variants:**
- Invitation created_at shows "2 days ago" (formatDistanceToNow)
- Expired invitation shows red/destructive badge
- Already-accepted invitation shows success badge
- Search field clears when switching status filters (optional behavior)
- Resend on expired invitation allows new token generation if org policy allows

**State transitions triggered:**
- Resend: `POST /admin/invitations/<uuid>/resend/` → generates new token, creates ScheduledEmail with email_type=invitation (backend/src/accounts/models.py UserInvitation)
- Revoke: `POST /admin/invitations/<uuid>/revoke/` → sets status=revoked, user cannot use token afterward
- Email dispatch: task queues `send_email(template="invitation", ...)` with accept link `/auth/accept-invitation?token=<token>`

**Cross-page navigation:**
- Back to "All Users" tab → refreshes users list

---

### Page/Tab: `/admin/users/:uuid` — AdminUserDetailPage (file: frontend/src/pages/admin/AdminUserDetailPage.tsx)

**Purpose:** View detailed user profile, edit user attributes (name, email, roles, org), see activity (logins, registrations, certificates), manage subscriptions/permissions.

**Preconditions:** User authenticated with `admin` role. Target user UUID valid (404 if not found). Data from `GET /admin/users/<uuid>/` endpoint.

**Visible elements:**
- Back button → navigate to `/admin/users`
- User header: avatar, full_name, email, status badge (Active/Inactive)
- Tabs: Profile, Activity, Permissions, Certificates, Registrations (if enabled)
- Profile tab:
  - Full Name (editable input)
  - Email (read-only or editable)
  - Roles (multi-select dropdown showing: learner, organizer, instructor, admin)
  - Professional Title (editable)
  - Organization Name (editable)
  - Timezone (dropdown)
  - Email Verified (checkbox, shows verification date if verified)
  - Save button
- Activity tab:
  - Login history table (last_login_at, IP if tracked)
  - Last login date and time
- Permissions tab:
  - Permission matrix: can_manage_users, can_invite_users, etc. (checkboxes)
  - Save button
- Certificates tab:
  - List of certificates earned (if any)
- Registrations tab:
  - List of event registrations (confirmed, cancelled, waitlisted)

**Interactions to test:**
1. Edit Full Name → change and save → `PATCH /admin/users/<uuid>/` with updated full_name
2. Edit Professional Title → change and save
3. Edit Organization Name → change and save
4. Edit Timezone → select from dropdown, save
5. Change Roles (multi-select) → select/unselect admin, organizer, learner, instructor → save
6. Verify Email (if unverified) → clicking checkbox sends verification email, shows pending state
7. Click on "Activity" tab → loads login history (if implemented)
8. Click on "Certificates" tab → shows list of earned certificates with dates
9. Click on "Registrations" tab → shows all event registrations with status
10. Click certificate link → navigates to certificate detail/download page
11. Click registration link → navigates to registration detail (if available)
12. Deactivate user toggle → `POST /admin/users/<uuid>/deactivate/` → refreshes page, shows inactive badge
13. Re-activate user toggle → flips is_active back to True
14. Delete user (if permission exists) → soft-delete with confirmation modal

**Edge cases & state variants:**
- User not found → 404 error page
- Editing own user account → some fields may be locked (e.g., role changes forbidden)
- User with no certificates → "No certificates" empty state
- User with no registrations → "No registrations" empty state
- Email change workflow: if editing email field, system sends confirmation to new email, requires click-through before commit
- Last admin cannot have admin role removed (validation error)

**State transitions triggered:**
- Profile save: `PATCH /admin/users/<uuid>/` → updates User model fields, broadcasts user_updated signal
- Role change: `POST /admin/users/<uuid>/roles/` → upsert Group memberships, record UserRoleChange audit row with changed_by=authenticated_user, reason="Manual role change"
- Deactivate: `POST /admin/users/<uuid>/deactivate/` → sets is_active=False, cancels pending event reminders (backend/src/events/services.py:129-146)
- Email verification: `POST /admin/users/<uuid>/verify-email/` → sets email_verified=True, email_verified_at=now

**Cross-page navigation:**
- Back button → `/admin/users` (Users tab)
- Certificate click → `/certificates/:code/verify` (public verify page)
- Registration click → `/registrations/:uuid` (if detail page exists)

---

### Page/Tab: `/admin/billing` — BillingAdminPage (file: frontend/src/pages/admin/BillingAdminPage.tsx)

**Purpose:** Admin-only observability on Stripe webhook events, disputes, and reconciliation findings. Monitor payment health, resolve disputes, detect drift.

**Preconditions:** User authenticated with `admin` role. Stripe webhooks configured and events stored in StripeEvent table.

**Visible elements:**
- Three tabs: "Stripe Events", "Disputes", "Reconcile"

#### Tab: Stripe Events
- Filter buttons: All, Errored, Unprocessed
- Refresh button (icon)
- List of events showing:
  - Event ID (truncated, monospace font)
  - Event Type badge (e.g., charge.succeeded, charge.refunded, charge.dispute.created)
  - Status badge: Processed (green), Pending (amber), Error (red)
  - Received timestamp (relative, e.g., "5 minutes ago")
  - Error message (if present, red text)
  - Retry button per event

**Interactions to test:**
1. Click filter "All" → shows all events (default)
2. Click filter "Errored" → shows only events with non-empty error field
3. Click filter "Unprocessed" → shows only events where processed_at=NULL
4. Click "Refresh" button → reloads event list
5. Click "Retry" button on errored event → `POST /admin/billing/stripe-events/{event_id}/retry/` → clears processed_at and error, re-enqueues for processing, shows toast "Retry queued"
6. Scroll/paginate event list (if paginated)
7. Click event ID → (if detail view implemented) shows full webhook payload JSON for debugging

**Edge cases & state variants:**
- Loading spinner while fetching events (max 200 most recent)
- Empty state: "No Stripe events match the current filter."
- Error text truncated if very long (font-mono, truncated class)
- Event type is exact string from Stripe (charge.succeeded, charge.failed, charge.refunded, charge.dispute.created, charge.dispute.closed, etc.)
- Retry on already-processed event — re-runs handler chain idempotently (safe no-op if already handled)
- Retry on network-unreachable event — task fails and error is captured in StripeEvent.error field

**State transitions triggered:**
- Retry: backend clears processed_at and error, enqueues `process_stripe_event.delay(event_id)` → handler chain runs (backend/src/billing/tasks.py)
- Handler chain for charge.succeeded → creates/updates Payment or Registration, sends confirmation email
- Handler chain for charge.refunded → updates Registration payment_status, sends refund email, creates Notification
- Handler chain for charge.dispute.created → creates Dispute record, notifies admin

**Cross-page navigation:**
- External link: "Stripe" button links to https://dashboard.stripe.com/disputes (or charges) in new tab

#### Tab: Disputes
- Open/All filter toggle button
- Table showing disputes:
  - Stripe Dispute ID (monospace)
  - Status badge (color-coded: red for open states, gray for closed)
  - Reason badge (secondary color)
  - Evidence due soon alert (amber, if within 3 days)
  - Amount in currency (e.g., "$150.00 USD")
  - Evidence due date (relative, if open)
  - Outcome (if closed, e.g., "won" / "lost")
  - Link to Stripe dashboard

**Interactions to test:**
1. Click "Open only" toggle → filters to only disputes with status in [needs_response, under_review, warning_needs_response, warning_under_review]
2. Click "Open only" again → toggle off, shows all disputes
3. Hover over "Evidence due soon" alert → shows deadline timestamp
4. Click "Stripe" button → opens https://dashboard.stripe.com/disputes/{dispute_id} in new tab
5. Scroll/paginate dispute list

**Edge cases & state variants:**
- Empty state: "No disputes currently open." (if open_only=True) or "No disputes on record." (if showing all)
- No evidence_due_by for closed disputes
- Status values: needs_response, under_review, warning_needs_response, warning_under_review (open), won, lost (closed)
- Amount displays in currency with 2 decimals
- Outcome shows capitalized: Won, Lost, Expired (enum)
- Related registration/course_purchase shown in metadata (if exists)

**State transitions triggered:**
- Webhook charge.dispute.created → creates Dispute record, sets status=needs_response, evidence_due_by calculated from Stripe response
- Webhook charge.dispute.closed → updates Dispute status, sets closed_at and outcome

#### Tab: Reconcile
- Input field: hours (default 72)
- "Run Reconciliation" button
- Results section (appears after run):
  - Summary card showing: since_date, total_findings_count, breakdown by kind (e.g., charge_without_registration, registration_without_charge)
  - Findings list:
    - Kind (e.g., orphan_charge, orphan_registration)
    - Entity (e.g., Stripe charge ID or Registration ID)
    - Detail (nested JSON showing mismatch)

**Interactions to test:**
1. Edit hours input → change from 72 to 24, 48, 120, etc.
2. Click "Run Reconciliation" → `POST /admin/billing/reconcile/` with {hours: N} → shows loading spinner
3. View reconciliation results → summary card and findings table
4. Empty results → "0 drift finding(s)" message
5. Multiple findings → each shown with expandable detail (or static JSON)

**Edge cases & state variants:**
- Loading spinner while running (can take several seconds)
- Error on Stripe API unreachable → shows error toast
- Invalid hours input (non-numeric) → backend defaults to 72
- No findings for period → "0 drift finding(s) since [date]."
- Findings sorted by kind (grouped)
- Detail JSON nested; may show Stripe charge metadata vs. local Registration

**State transitions triggered:**
- None — reconciliation is read-only audit. Results inform manual corrective actions.

---

## SECTION 2: LIVE EVENT EXPERIENCE

### Journey: `/events/:id/lobby` or `/r/:registrationUuid/lobby` → Join → Video Room → Leave → `/events/:id/recording`

**Overview:** Event lobby → countdown timer → "Join" button activation logic → livekit embed → attendance tracking → feedback → recording availability.

#### State: EventLobbyPage Load (Preconditions)

**Authenticated User Path:**
- User navigates to `/events/:id/lobby` (where `:id` is event UUID or slug)
- API endpoint: `GET /events/{uuid}/` (public event detail, backend/src/events/views.py GetPublicEventView)
- Returns Event object with: uuid, title, short_description, description, starts_at, ends_at, timezone, location, duration_minutes, registration_count, max_attendees, status (published/live/completed/closed/cancelled)

**Guest Registration Path:**
- Guest clicks link in registration confirmation email: `/r/{registrationUuid}/lobby`
- API endpoint: `GET /registrations/{uuid}/lobby/` (backend/src/registrations/views.py GetRegistrationLobbyView)
- Returns RegistrationLobbyResponse: event (full Event object), registration (with status, full_name, email)

**Visible Elements (Lobby):**
- Back button → "Back to My Events" (auth) or redirect to discover page (guest)
- Event title (H1)
- Short description (if present)
- EventCountdown component showing:
  - Time until start (e.g., "Starts in 2 hours 15 minutes")
  - Or "Live now" (if event.status=live or now >= starts_at)
  - Or "Event ended" (if now >= ends_at)
- Event metadata card:
  - When: start datetime + timezone + duration
  - Where: location (if present)
  - Registered: registration_count / max_attendees
- Action buttons:
  - JoinButton (green, enabled only if now >= starts_at - 15min AND now < ends_at OR event.status=live)
  - AddToCalendar button (secondary)
- Join button inactive message (if applicable): "The Join button activates 15 minutes before the event starts."
- Event description (if present)
- Registration details card (auth user): Name, Email, Status (capitalized)
- Post-event card (if event is past): "After the event" text + link to `/events/{uuid}/recording`

**Interactions to test:**
1. Load page before 15-min window → Join button shows with opacity-60 and pointer-events-none (disabled visual)
2. Hover disabled Join button → no cursor change
3. Load page within 15-min window before start → Join button becomes enabled (full opacity, cursor-pointer)
4. Click enabled Join button → calls `POST /events/{uuid}/join/` (backend/src/conferencing/views.py JoinEventView) → returns livekit token + room name → navigates to livekit embed
5. Load page after event start → Join button shows "Join now" and is enabled
6. Load page after event ends → Join button is hidden, "After the event" card shown
7. Cancelled event → Join button hidden, message about cancellation (if any)
8. Click "Add to Calendar" → exports .ics file or opens Google/Outlook calendar deep link
9. Click event title → no navigation (static text)
10. User refreshes during event → countdown updates, Join button remains in same state
11. Page auto-updates countdown timer every second (visual)

**Edge cases & state variants:**
- Event not found → error page with "Couldn't load this event" message
- Guest registration link with invalid UUID → 404
- Registered user without registration object → still shows event details (guest view)
- Event with no location → "Where" card hidden
- Event with no description → "About this event" card hidden
- Event status=cancelled → countdown shows cancellation notice
- Event cancelled but still in future → Join button hidden
- Timezone missing or empty → only shows datetime without timezone suffix

#### State: Join Event (Interaction)

**Trigger:** User clicks enabled "Join" button.

**Backend Flow:**
1. `POST /events/{uuid}/join/` → creates or updates AttendanceRecord, generates livekit access token
2. Livekit token signed with room_name (event UUID) + participant_identity (user UUID or registration UUID)
3. Response: {access_token, room_name, video_url} (or livekit_embed_url)
4. Frontend receives token, injects into livekit-react or custom livekit embed

**Frontend Navigation:**
- Button shows loading state (spinner)
- Navigates to `/events/{uuid}/live` or embeds livekit component in-place
- Passes access_token to livekit client library

#### State: In-Event Video Room (Livekit Embed)

**Visible Elements (Live Experience):**
- Livekit participant grid (self video + other participants)
- Control bar: Microphone toggle, Camera toggle, Screen share toggle, Leave button, Settings menu
- Participant list (sidebar, if implemented) showing: participant names, audio/video status icons
- Chat panel (if enabled) showing: message history, input field
- Countdown/timer showing event end time or session duration
- Recording indicator badge (if recording active): "Recording" (red dot)

**Interactions to test:**
1. Audio/video controls → mute/unmute microphone, disable/enable camera
2. Screen share → share tab/window, stop sharing
3. Chat → send message, receive messages from other participants, emoji support (if enabled)
4. Participant list → hover shows participant details (role, connection time)
5. Leave button → disconnects from room, shows "You left the room" message, optionally shows feedback form
6. Reconnect (if connection drops) → automatic or manual "Rejoin" button
7. Another user joins → participant appears in grid, joined notification (if any)
8. Another user leaves → participant disappears, left notification (if any)
9. Recording badge visible → confirms event is being recorded (badge style per design)
10. Organizer view (if role=organizer) → sees "End Event" button, "Record" toggle, participant management (mute all, remove participant)
11. Organizer ends event → all participants disconnected, redirected to post-event page

**Backend Side Effects:**
- `POST /events/{uuid}/attendance/ping/` sent periodically (heartbeat) to track attendance
- AttendanceRecord updated with join_time (first), leave_time (on disconnect)
- Duration calculated: leave_time - join_time = attendance_minutes
- Conference signals: `participant_joined.send()`, `participant_left.send()` (backend/src/conferencing/signals.py) → updates event participant count, triggers notifications if needed

**Edge cases & state variants:**
- Livekit server unavailable → error state with message "Unable to connect to video room"
- User's camera/mic denied by OS → shows permission error, user can still listen/watch
- Network latency high → video freezes/pixelates, UI shows "Reconnecting..."
- User closes browser tab → livekit connection dropped, server records leave_time
- Event ends while user in room → livekit room automatically closes, participants see "Event ended"
- Recording started/stopped during event → recording badge appears/disappears

#### State: Post-Event Feedback & Departure

**Trigger:** User clicks "Leave" button or event ends.

**Visible Elements (Feedback):**
- Modal or page: "Event Feedback" (if event.feedback_enabled and registration not yet submitted)
- Feedback form with FeedbackField rows (e.g., "Overall rating" 1–5, "Content quality" 1–5, "Speaker rating" 1–5, "Comments" textarea)
- Submit button (disabled until required fields filled)
- Skip button

**Interactions to test:**
1. Click rating field → select 1–5 stars
2. Type comment in textarea → freeform text
3. Click "Submit" → `POST /events/{uuid}/feedback/` with {rating, comment_text, ...} → creates FeedbackResponse row
4. After submit → shows thank-you message or redirects to `/registrations` or `/my-events`
5. Click "Skip" → redirects without submitting feedback

**Backend Side Effects:**
- FeedbackResponse created, linked to registration
- Organizer notified of new feedback (if enabled)
- Feedback visible on event detail page for organizer

#### State: Event Recording Access (`/events/:id/recording`)

**Preconditions:** Event completed and recording published. RecordingTask in status=ready (file_url available).

**Visible Elements:**
- Back button → `/my-events`
- Event title (H1)
- Recording metadata: "Recorded [date] · [duration]"
- Video player (HTML5 `<video>` with controls)
- Download link for recording file

**Interactions to test:**
1. Load recording page → `GET /events/{uuid}/recording/` → retrieves VideoRecording with status=ready
2. Page shows video player with src={file_url}
3. Click play → starts video playback
4. Seek bar → click to seek through recording
5. Full-screen button → toggles full-screen mode
6. Volume control → adjust audio level
7. Speed control (if enabled) → 0.75x, 1x, 1.5x, 2x playback speed
8. Download link → `<a href={file_url} download={file_name}>` → triggers browser download
9. Recording not ready → shows "Recording isn't ready" with status and "Try again in a few minutes"
10. No recording available → shows "No recording available yet" message
11. Recording in processing state → shows loading spinner + status

**Edge cases & state variants:**
- Multiple recordings for same event → selects most recently published
- Video file not found (link broken) → video player shows playback error
- File large (>500MB) → slow load, user sees buffering
- Guest registration without user account → can still access recording if link shared
- Recording without video file (only audio) → message "Recording isn't ready" or audio-only player

---

## SECTION 3: CROSS-CUTTING FLOWS

### Flow 1: Stripe Checkout — Paid Event Registration

**Trigger:** User clicks "Register" on paid event, or "Confirm Registration" after waitlist promotion on paid event.

**Preconditions:**
- Event has price > 0
- User not already registered (or registration in PENDING/CANCELLED state)
- Stripe publishable key loaded (frontend)
- Stripe API keys configured (backend)

**Step-by-step:**

1. **Pre-checkout Page** (`/events/:id/register` or EventRegistration.tsx)
   - User sees event title, price, description
   - Optional: promo code field
   - "Proceed to Payment" button

2. **Promo Code Validation** (if user enters code)
   - `POST /registrations/validate-promo/` with {code, event_uuid}
   - Backend checks PromoCode table: valid, not expired, not capped (if cap_amount set), applies to event
   - Response: {valid: true, discount_percent: 10, discount_amount: 5.00} OR {valid: false, error: "Code expired"}
   - UI updates: shows discount breakdown, adjusts total price

3. **Proceed to Stripe Checkout**
   - `POST /checkout/create-session/` with {event_uuid, promo_code?, guest_email?, guest_name?}
   - Backend creates Stripe Checkout Session:
     - line_items: [{price_data: {product_data: {name: event.title}, unit_amount_decimal: event.price_cents}, quantity: 1}]
     - metadata: {kind: "event", event_uuid, registration_uuid, promo_code}
     - success_url: `{FRONTEND_URL}/checkout/success?session_id={id}&kind=event`
     - cancel_url: `{FRONTEND_URL}/checkout/cancel?kind=event`
   - Response: {checkout_url: "https://checkout.stripe.com/..."}
   - Frontend redirects to checkout_url (Stripe-hosted page)

4. **Stripe Checkout Page** (Stripe-hosted, not in app)
   - User enters payment method (card, Google Pay, Apple Pay)
   - Email field (prefilled if user logged in)
   - Country, ZIP, etc.
   - User clicks "Pay {amount}"

5. **Payment Success/Failure**
   - Success: Stripe posts `checkout.session.completed` webhook (backend/src/billing/tasks.py process_stripe_event)
   - Webhook handler:
     - Retrieves session details from Stripe
     - Creates/updates Registration: status=CONFIRMED, payment_status=PAID, payment_intent_id=session.payment_intent
     - Enqueues `send_registration_confirmation.delay(registration_id)` task
     - Enqueues `enqueue_event_reminders(registration)` (sets up reminder emails)
     - Creates Notification(type=registration_confirmed) for user
   - User redirected to `/checkout/success?session_id=...&kind=event`
   - Failure: User clicks "back" on Stripe error page, returns to pre-checkout

6. **Checkout Success Page** (`/checkout/success?kind=event`)
   - Displays: "Payment received" header, "Your event registration will appear in My Learning within a few moments."
   - Buttons: "Go to My Learning", "Browse more events"
   - Displays session_id for reference
   - No DB writes (webhook drives registration creation)

7. **Post-Webhook Flow**
   - Email sent: registration_confirmation with .ics attachment (5-30 sec delay)
   - Reminder emails scheduled: 24h, 1h before start (ScheduledEmail rows created, background cron dispatches)
   - User sees registration in `/registrations` list within 30 seconds

**Edge cases & failure modes:**
- Promo code expired → error toast, user proceeds without discount
- Promo code capped (e.g., 10 uses) → "Code no longer available" error
- Promo code wrong scope (e.g., applies to courses, not events) → validation error
- User cancels on Stripe page → redirects to `/checkout/cancel?kind=event`, no registration created
- Payment intent fails (e.g., declined card) → Stripe shows error, user can retry with different card
- Webhook delivery fails (Stripe retries up to 3x) → registration not created until webhook succeeds
- User closes browser mid-checkout → session left in draft state on Stripe; user can resume with link in email
- Network timeout during checkout creation → backend returns 500, frontend shows error, user retries
- Duplicate registration by same email → `unique_together = [['event', 'email']]` — registration update happens instead of create (idempotent)

**Verification points:**
- Registration appears in DB: `Registration.objects.filter(event_uuid=X, email=Y, status=CONFIRMED)`
- ScheduledEmail rows created: `ScheduledEmail.objects.filter(event_id=X, template_key='event_reminder')`
- EmailLog row created: `EmailLog.objects.filter(email_type='registration_confirm', registration=reg)`
- Notification created: `Notification.objects.filter(user_id=user_id, notification_type='...')`
- Stripe Event recorded: `StripeEvent.objects.filter(event_type='checkout.session.completed', processed_at__isnull=False)`

---

### Flow 2: Stripe Checkout — Paid Course / Program

**Trigger:** User clicks "Enroll" on paid course or "Enroll in Program" on program page.

**Preconditions:**
- Course or Program has price > 0
- User not already enrolled (or enrollment in PENDING state)

**Step-by-step:**

1. **Pre-checkout Page** (`/courses/:id/enroll` or `/programs/:id/enroll`)
   - Shows course/program title, price, description
   - Optional: promo code field
   - "Proceed to Payment" button

2. **Promo Code Validation** (same as event)
   - `POST /checkout/validate-promo/` with {code, course_uuid or program_uuid}
   - Response: {valid, discount_percent, new_total}

3. **Create Checkout Session**
   - `POST /checkout/create-session/` with {kind: "course" or "program", course_uuid or program_uuid}
   - Backend creates Stripe Session:
     - For course: line_items with course.price
     - For program: line_items with program.price (all bundled courses at one charge)
     - metadata: {kind, entity_uuid}
   - Response: {checkout_url}

4. **Stripe Checkout → Payment**
   - User enters payment details on Stripe-hosted page
   - Click "Pay {amount}"

5. **Webhook: checkout.session.completed**
   - Handler creates/updates CourseEnrollment or ProgramEnrollment
   - Status set to CONFIRMED
   - Payment tracking: payment_intent_id, amount_paid, tax_amount
   - For program: creates multiple CourseEnrollment rows (one per course in program)
   - Enqueues `send_course_enrollment_email(enrollment_id)` task
   - Enqueues `create_course_access_token(user_id, course_id)` (if learning platform has token)

6. **Checkout Success Page**
   - "Payment received" + "You're enrolled. The course will appear on your dashboard within a few moments."
   - Buttons: "Go to dashboard", "Browse more courses"

7. **Post-Webhook**
   - Email sent: "enrollment_confirmation" template with course title, access link
   - Enrollment visible in user's `/dashboard` or `/my-learning` within 30 seconds

**Edge cases:**
- Same as event checkout; additionally:
- Program with 0-price bundled courses → checkout still creates session for program price
- User already enrolled but checkout session created → webhook updates existing enrollment (idempotent)
- Course archived after checkout session created → webhook validates course is_published; if not, enrollment marked FAILED

**Verification points:**
- CourseEnrollment or ProgramEnrollment in DB with status=CONFIRMED
- EmailLog with type='enrollment_confirmation'
- User sees course in dashboard

---

### Flow 3: Refund Flow

**Trigger:** Organizer initiates refund via admin UI, or system issues refund (e.g., event cancelled).

**Preconditions:**
- Registration or CourseEnrollment has payment_status=PAID (not NA or FAILED)
- Stripe charge exists (charge_id or payment_intent_id recorded)
- Organizer has manage_refunds permission

**Step-by-step:**

1. **Organizer Initiates Refund** (Admin UI for event, course management page for course)
   - Clicks "Refund" button on registration or enrollment row
   - Modal appears: "Reason for refund" (dropdown: customer_request, duplicate, expired_card, general_adjustment)
   - Optional: "Partial refund amount" (defaults to full amount)
   - Submit button

2. **Backend Refund Request**
   - `POST /registrations/{uuid}/refund/` or `/course-enrollments/{uuid}/refund/`
   - Backend validates:
     - Payment status is PAID
     - Charge exists (stripe_charge_id or derived from payment_intent_id)
     - Amount >= 0 and <= original_amount
   - Calls Stripe API: `stripe.Refund.create(charge=charge_id, amount=amount_cents, reason=reason)`
   - Creates RefundRecord in DB: status=PENDING, stripe_refund_id from response

3. **Webhook: charge.refunded**
   - Stripe posts webhook `charge.refunded` with refund details
   - Backend handler:
     - Updates RefundRecord: status=COMPLETED, completed_at=now
     - Updates Registration/CoursEnrollment: payment_status=REFUNDED, refunded_at=now
     - Enqueues `send_refund_email.delay(registration_id or enrollment_id)`
     - Creates Notification(type=refund_processed) for user

4. **Refund Email**
   - Template: "refund_processed"
   - Shows: original amount, refund amount, refund reason
   - Estimated processing time (e.g., 3–5 business days)

5. **Partial Refund**
   - If amount < original_amount, Stripe creates refund for difference
   - Registration payment_status remains PAID (not fully refunded)
   - Refund notes on record

**Edge cases:**
- Refund request fails (e.g., Stripe API timeout) → RefundRecord status=FAILED, error_message captured
- Duplicate refund request (webhook delivery retry) → idempotent (checks refund_id not already recorded)
- User cancels registration → registration.cancel() calls registration._promote_next_from_waitlist() before refund is issued
- Refund issued after event completed → user still has certificate if attendance eligible; certificate issuance not affected

**Verification points:**
- RefundRecord in DB with status=COMPLETED
- Registration.payment_status=REFUNDED
- Stripe refund visible in Stripe dashboard
- Email sent with refund details

---

### Flow 4: Dispute Flow

**Trigger:** Customer disputes charge in Stripe dashboard; Stripe posts webhook to app.

**Preconditions:**
- Registration or CourseEnrollment has PAID charge
- Dispute opened in Stripe (chargeback, etc.)

**Step-by-step:**

1. **Webhook: charge.dispute.created**
   - Stripe posts webhook with dispute details: dispute_id, charge_id, amount, reason, evidence_due_by
   - Backend handler (backend/src/billing/tasks.py):
     - Creates Dispute record: status=needs_response, reason (from Stripe), evidence_due_by
     - Links to Registration or CoursEnrollment if found
     - Creates Notification(type=dispute_opened) for admins
     - Sends email to admins: "Payment dispute opened for {amount} — respond by {due_date}"

2. **Admin Views Dispute** (`/admin/billing` Disputes tab)
   - Dispute appears in list with status=needs_response, evidence_due_by highlighted if within 3 days
   - Admin clicks "Stripe" link to open dispute in Stripe dashboard (external)

3. **Admin Submits Evidence** (via Stripe UI, not in-app)
   - Admin logs into Stripe dashboard
   - Uploads evidence (invoice screenshot, transaction proof, customer communication, etc.)
   - Submits evidence in Stripe UI

4. **Webhook: charge.dispute.closed**
   - Stripe posts webhook: outcome (won, lost, expired)
   - Backend handler:
     - Updates Dispute: status=closed (or won/lost, depending on schema), outcome, closed_at=now
     - Creates Notification(type=dispute_closed, outcome) for admins
     - If outcome=won: no action on registration (payment already charged)
     - If outcome=lost: optionally issue refund or update payment_status to disputed

5. **Admin Monitoring** (in-app)
   - Dispute status updated in real-time (via API polling or WebSocket if implemented)
   - Admin can view on BillingAdminPage

**Edge cases:**
- Evidence not submitted → dispute auto-lost at evidence_due_by timestamp
- Multiple disputes for same charge → separate Dispute records created
- Dispute on registration that's already refunded → outcome=won (charge already credited to customer)
- Dispute on old charge (>90 days) → may not be allowed by Stripe; webhook error handled

**Verification points:**
- Dispute record in DB with status, reason, evidence_due_by, outcome
- Admin Notification created
- Dispute visible in `/admin/billing` Disputes tab

---

### Flow 5: Waitlist Promotion

**Trigger:** Capacity becomes available (attendee cancels, event max_attendees increased).

**Preconditions:**
- Event has waitlist_enabled=True
- Event has registrations in WAITLISTED status
- Capacity check: confirmed_count < max_attendees OR max_attendees increased

**Step-by-step:**

1. **Automatic Promotion** (if waitlist_auto_promote=True)
   - Registration.cancel() calls _promote_next_from_waitlist() (backend/src/registrations/models.py:225–238)
   - Selects first waitlisted registration (order_by waitlist_position)
   - Calls next_reg.promote_from_waitlist():
     - For free event: status=CONFIRMED, payment_status=NA, promoted_from_waitlist_at=now
     - For paid event: status=PENDING, payment_status=PENDING, amount_paid=ticket_price, promoted_from_waitlist_at=now

2. **Email: Waitlist Promotion**
   - Enqueues send_email(template='waitlist_promotion', recipient=promoted_reg.email, context={event_title, action_url})
   - Email body: "Great news! A spot opened up in [event]. Click here to confirm."
   - For paid events: action_url links to `/start-checkout/registration/{uuid}` (resume checkout)

3. **Notification: In-App**
   - Creates Notification(type=waitlist_promoted) for promoted user
   - Shows in bell icon with message

4. **Paid Event: User Must Complete Payment**
   - User clicks link in email or app notification → `/start-checkout/registration/{uuid}`
   - Launches Stripe Checkout Session (with same flow as Flow 1)
   - On success: registration.status=CONFIRMED
   - If user doesn't complete payment: registration stays PENDING, moved to next waitlist position after N days (if policy exists)

5. **Paid Event: Automatic Promotion Pauses**
   - If promoted registration stays PENDING, next waitlist entry not auto-promoted until this one is confirmed or cancelled

**Edge cases:**
- Multiple seats freed → promotes multiple registrations one-by-one (as each is confirmed or deadline passes)
- Waitlist_auto_promote disabled → promotions happen on-demand (organizer button in UI)
- Promoted user cancels without paying → next in line auto-promoted (if policy allows)
- Event max_attendees decreased → no effect; waitlist not affected retroactively

**Verification points:**
- Waitlisted Registration status changes to CONFIRMED (free) or PENDING (paid)
- ScheduledEmail for waitlist_promotion created
- Notification in user's inbox
- waitlist_position cleared (set to NULL)
- promoted_from_waitlist_at timestamp recorded

---

### Flow 6: Email Reminder Lifecycle (P1)

**Trigger:** Registration confirmed (for event); scheduled reminder offsets define send times.

**Preconditions:**
- Event has reminder offsets set (default: [1440, 60] minutes before start = 24h, 1h)
- Registration status=CONFIRMED
- Event status in [PUBLISHED, LIVE]

**Step-by-step:**

1. **Enqueue on Registration Confirmation** (backend/src/registrations/tasks.py:send_registration_confirmation)
   - Task calls `enqueue_event_reminders(registration)` (backend/src/events/services.py:78–126)
   - For each offset in event.effective_reminder_offsets_minutes:
     - Calculates send_at = event.starts_at - timedelta(minutes=offset)
     - If send_at > now: creates ScheduledEmail record with unique constraint (event, recipient_email, template_key, send_at)
     - Returns count of ScheduledEmail rows created (PENDING status)

2. **Cron Tick Dispatch** (backend/src/common/cron_views.py CronTickView)
   - Cloud Scheduler hits `/cron/tick/` every minute (or dev: `curl http://localhost:8000/cron/tick/ -H "Authorization: Bearer SECRET"`)
   - CronTickView.post() dispatches periodic tasks:
     - `dispatch_scheduled_emails.delay()` — finds ScheduledEmail rows where send_at <= now and status=PENDING
     - `send_event_reminders.delay()` — legacy alternate path (if used)
   - Task processes batch of due emails, idempotent by ScheduledEmail.status (PENDING only)

3. **Email Dispatch** (backend/src/integrations/tasks.py:dispatch_scheduled_emails)
   - Iterates over due ScheduledEmail rows
   - For each:
     - Calls scheduled_email.dispatch():
       - Creates EmailLog record (status=PENDING)
       - Renders template (event_reminder.html)
       - Attaches .ics calendar file
       - Calls email_service.send_log(log, context=scheduled_email.context, attachments=ics)
       - Sets ScheduledEmail.status=DISPATCHED, email_log=log
       - Catches exceptions, marks ScheduledEmail.status=FAILED, error_message

4. **Email Send** (backend/src/integrations/services.py:email_service.send_email)
   - Renders subject from template: "Reminder: {event_title} starts soon"
   - Renders body from event_reminder.html template (with offset_minutes context)
   - Attaches .ics file: `event.ics` (text/calendar; method=PUBLISH)
   - Sends via Django EmailMultiAlternatives (Anymail backend, e.g., Sendgrid, Mailgun, SES)
   - Creates EmailLog record: status=SENT, sent_at=now, provider_message_id from backend

5. **Notification Mirror** (backend/src/integrations/services.py:create_notification_for_log)
   - EmailLog.dispatch() calls create_notification_for_log(log, context)
   - Checks TEMPLATE_NOTIFICATION_TYPE mapping: event_reminder → event_reminder_24h or event_starting_soon (if offset <= 60min)
   - Creates Notification record (user_id, type, title, message, action_url=join_url, metadata)
   - User sees notification in bell icon

6. **Idempotency Guarantee**
   - ScheduledEmail unique constraint: `(event, recipient_email, template_key, send_at)`
   - Cron task re-runs are safe: PENDING filter ensures only unsent rows processed
   - ScheduledEmail.status blocks repeat dispatch: DISPATCHED rows skipped on retry
   - If webhook/retry triggers enqueue_event_reminders() again: update_or_create finds existing row, no duplicate

**Edge cases & failure modes:**
- Event cancelled before send_at → flow continues, email sent (email service can check event.status and omit join link if cancelled)
- Registration cancelled before send_at → cancel_event_reminders() called (backend/src/registrations/signals.py), ScheduledEmail.status=CANCELLED
- Email service failure (SMTP timeout, rate limit) → exception logged, ScheduledEmail.status=FAILED, error_message captured, no retry auto-triggered (manual operator action or retry task)
- Cron tick misses (Cloud Scheduler down) → emails accumulate in PENDING state, next tick processes backlog (no emails lost)
- User timezone — no handling (sends in UTC; users expected to have event timezone in context)

**Verification points:**
- ScheduledEmail rows in DB: `ScheduledEmail.objects.filter(event_id=X, template_key='event_reminder', status='PENDING')`
- Sent emails: `EmailLog.objects.filter(email_type='event_reminder', status='SENT', sent_at__isnull=False)`
- Notifications: `Notification.objects.filter(notification_type='event_reminder_24h' or 'event_starting_soon')`
- Email provider logs (Sendgrid, etc.): message_id recorded in EmailLog.provider_message_id

---

### Flow 7: Calendar Invite (.ics)

**Trigger:** Email with calendar attachment sent (registration confirmation, event reminder).

**Preconditions:**
- Email template in `_ICS_ATTACHED_TEMPLATES` set (registration_confirm, event_reminder, waitlist_promotion, event_cancelled, invitation)
- Event and registration objects available

**Step-by-step:**

1. **ICS Generation** (backend/src/events/services.py:build_event_ics)
   - Called from ScheduledEmail._build_attachments() or send_registration_confirmation()
   - Inputs: event (Event object), attendee_email (registration email), attendee_name (registration full_name)
   - Calls build_event_ics():
     - Constructs RFC 5545 VCALENDAR with single VEVENT:
       - UID: `event-{event.uuid}@accredit.app` (globally unique)
       - DTSTART: event.starts_at (iCalendar format, UTC)
       - DTEND: event.ends_at
       - SUMMARY: event.title
       - DESCRIPTION: short_description + join_url
       - LOCATION: event.location or join_url
       - ORGANIZER: event.owner.email (CN=event.owner.full_name)
       - ATTENDEE: registration.email (PARTSTAT=NEEDS-ACTION)
       - METHOD: PUBLISH (or CANCEL if event.status=cancelled)
     - Returns RFC 5545 string

2. **Email Attachment** (backend/src/integrations/models.py:ScheduledEmail._build_attachments)
   - Builds attachment tuple: (filename='event.ics', content=ics_string, mimetype='text/calendar; method=PUBLISH; charset=utf-8')
   - Method header: PUBLISH for new/update, CANCEL for cancellation (so calendar clients remove event)

3. **Email Send with Attachment** (backend/src/integrations/services.py:email_service.send_email)
   - Creates EmailMultiAlternatives message
   - Attaches alternative (HTML body)
   - Attaches .ics file: `msg.attach(filename, content, mimetype)`
   - Sends via backend

4. **Calendar Client Processing**
   - User receives email with .ics attachment
   - Outlook, Gmail, Apple Mail: display "Add to Calendar" button or auto-import
   - User clicks button → event added to their calendar (DTSTART/DTEND define time, DESCRIPTION includes join_url)
   - Multi-session events: single .ics with single VEVENT (covers first session; multi-session series not currently supported)

5. **Cancellation Notification**
   - If event.status changes to CANCELLED while reminders pending:
     - cancel_event_reminders(event=event) sets ScheduledEmail.status=CANCELLED for all pending reminders
     - OR: manually enqueue new ScheduledEmail with method=CANCEL, attendees receive cancellation notice
   - Calendar clients recognize METHOD:CANCEL and remove event from user calendars

**Edge cases:**
- Multi-session events: .ics covers only first session (event.starts_at/ends_at); no RRULE (recurrence) support in current schema
- Event rescheduled: new reminders enqueued with updated DTSTART/DTEND; old reminders cancelled (backend/src/events/services.py:reschedule_event_reminders)
- User already has event in calendar: importing new .ics may prompt duplicate or replace (client-specific)
- Timezone handling: .ics uses UTC (Z suffix), client renders in user's local timezone (event.timezone not encoded in .ics)
- Invite forwarding: .ics forwarded to third party; METHOD:PUBLISH allows add-to-calendar

**Verification points:**
- .ics file attachment in sent email (via email provider UI or curl test)
- ICS content validates against RFC 5545 (online validator or openssl)
- Calendar clients import event at correct time (test in Outlook, Google Calendar, Apple Calendar)

---

### Flow 8: Notification Fan-Out

**Trigger:** Any action that creates a Notification row (registration confirmation, reminder, event update, certificate issued, waitlist promotion, etc.).

**Preconditions:**
- User logged in (authenticated)
- Notification preference allows email and/or in-app (user.notify_event_reminders, etc.)

**Step-by-step:**

1. **Notification Creation** (various task handlers)
   - Example: send_registration_confirmation → calls create_notification_for_log(email_log, context)
   - Backend checks Notification.Type enum: EVENT_REMINDER_24H, EVENT_STARTING_SOON, WAITLIST_PROMOTED, CERTIFICATE_ISSUED, etc. (backend/src/accounts/models.py:370–394)
   - Creates Notification row:
     - user_id: linked user
     - notification_type: enum value
     - title: email subject or custom text
     - message: brief description (event title + date, etc.)
     - action_url: link to event lobby, certificate verification page, etc.
     - metadata: {email_log_id, event_uuid, registration_uuid, ...}
     - read_at: NULL (unread)

2. **Preference Gating** (backend/src/integrations/services.py:user_allows_email)
   - Before email send, checks EMAIL_PREF_MAP: template_key → user field (e.g., event_reminder → notify_event_reminders)
   - If user.notify_event_reminders=False: email suppressed (in-app notification still created)
   - Transactional emails (registration_confirm, password_reset) always sent regardless of prefs

3. **Email Send** (parallel to notification)
   - Sends email only if user_allows_email(user, template_key)
   - In-app notification created regardless

4. **In-App Notification Display** (frontend)
   - Bell icon with unread count badge (red circle with number)
   - User clicks bell → notification dropdown/panel opens
   - Shows list: unread notifications at top (bold text), older below
   - Each notification row: title, message, timestamp, action link
   - "Mark as read" button or auto-read on click

5. **Notification Click/Read**
   - User clicks notification row → navigates to action_url (event lobby, certificate page, etc.)
   - Frontend: `PATCH /notifications/{uuid}/read/` → sets read_at=now
   - Notification disappears from unread list, badge count decrements

6. **Notification Settings** (user dashboard `/settings` or `/profile`)
   - Checkboxes for: notify_event_reminders, notify_event_updates, notify_certificate_issued, notify_badges, notify_recordings, notify_course_progress
   - User unchecks preference → future emails of that type suppressed
   - Already-sent notifications remain in inbox

**Edge cases:**
- User without account (guest) → no in-app notification (transactional emails still sent)
- Notification metadata corrupt or missing data → title/message still shows, action_url may be empty
- User deleted → notification orphaned (on_delete=models.CASCADE removes Notifications on User delete)
- User preferences changed after email sent → no effect on already-sent email; future emails respect new preference

**Verification points:**
- Notification in DB: `Notification.objects.filter(user_id=X, notification_type='event_reminder_24h')`
- Bell icon unread count == count of Notification rows where read_at=NULL
- Email sent only if user.notify_event_reminders=True (or transactional type)
- Notification appears in frontend notification list within 1 second of creation

---

### Flow 9: Onboarding Wizard Branches

**Trigger:** New user signs up (creates account), onboarding_completed=False.

**Preconditions:**
- User authenticated
- onboarding_completed=False
- First navigation to dashboard or logged-in homepage

**Step-by-step:**

1. **Onboarding Route Guard** (frontend)
   - If user.onboarding_completed=False: redirect to `/onboarding` (OnboardingWizard.tsx)
   - Component renders multi-step wizard with progress bar

2. **Step Selection Based on Role** (backend/src/accounts/models.py User properties)
   - System fetches user.roles (groups)
   - Defines steps per role:
     - **Learner only:** (1) Profile completion, (2) Event discovery, (3) Done
     - **Organizer:** (1) Profile, (2) Organization setup, (3) Create first event (or skip), (4) Done
     - **Instructor:** (1) Profile, (2) Speaker info, (3) Done
     - **Admin:** (1) Profile, (2) Admin setup (org settings), (3) Done
   - Multiple roles: show union of all required steps (organizer + learner → show all)

3. **Step 1: Profile Completion**
   - Form fields: full_name (prefilled), professional_title, organization_name, timezone
   - Optional: profile photo upload
   - Submit → `PATCH /users/me/` with {full_name, professional_title, organization_name, timezone}

4. **Step 2: Role-Specific Setup**
   - **Learner:** Browse events carousel (populated from `/discover/events/` with featured events)
   - **Organizer:** Org setup form (organization name, logo, description) OR skip
   - **Instructor:** Speaker profile (bio, title, expertise areas)

5. **Step 3: Optional First Action**
   - **Learner:** "Register for an event" button → navigates to event discovery
   - **Organizer:** "Create your first event" button → navigates to event creation form (or skip)
   - Can skip all; simply completes onboarding

6. **Completion**
   - User clicks "Done" or completes final step
   - Frontend: `PATCH /users/me/` with {onboarding_completed=True}
   - Backend updates User: onboarding_completed=True
   - Redirect to `/dashboard`

7. **Skip Options**
   - Each step has "Skip" button (except profile completion, which is mandatory)
   - Skip → move to next step or complete if last step
   - User can re-run wizard from settings (link "Redo onboarding")

**Gating:**
- Pages check if onboarding_completed:
  - False → redirect to `/onboarding` (except onboarding page itself)
  - True → allow access to all pages

**Edge cases:**
- User adds new role after onboarding → onboarding_completed remains True (no re-trigger)
- User skips org setup as organizer → onboarding_completed=True but organization_name empty (can fill in org settings later)
- User never completes onboarding → can still use app (role pages may show guidance banner "Complete your profile")

**Verification points:**
- User.onboarding_completed=False on signup
- Redirect to `/onboarding` on first login
- User.onboarding_completed=True after wizard completion
- Role-appropriate steps shown in wizard

---

### Flow 10: Invitation Lifecycle

**Trigger:** Admin sends invite via UserManagementPage.

**Preconditions:**
- Admin authenticated with manage_users role
- Recipient email provided in form

**Step-by-step:**

1. **Send Invite** (InviteDialog component)
   - Admin fills form: email, role(s) (dropdown: learner, organizer, instructor, admin)
   - Optional: message body
   - Submit → `POST /admin/invitations/` with {email, roles, message}

2. **Invite Creation** (backend/src/accounts/models.py UserInvitation or similar)
   - Backend creates UserInvitation record:
     - email (normalized lowercase)
     - token (32-char secure random, generate_verification_code(32))
     - status=PENDING
     - invited_at=now
     - invited_by=authenticated_admin
     - roles: array of role names to assign
     - expires_at = now + 7 days

3. **Email Sent** (integrations/tasks.py send_invitation_email)
   - Enqueues send_email(template='invitation', recipient=invite.email, context={invite_link, message, roles})
   - Template: "You're invited to join [org]"
   - Includes button: "Accept Invitation" → `/auth/accept-invitation?token={token}`
   - Sent via Sendgrid/Anymail

4. **User Clicks Email Link**
   - Navigates to `/auth/accept-invitation?token={token}` (AcceptInvitationPage.tsx)
   - Frontend validates token format (length, chars)
   - Backend: `GET /auth/accept-invitation/?token={token}` → returns invite details (email, roles, expires_at) if valid, else error

5. **Accept Flow** (AcceptInvitationPage)
   - Form: Password + Confirm Password (both required)
   - Backend validates:
     - Token exists and status=PENDING
     - Token not expired (now < expires_at)
     - Password strength (>= 8 chars)
   - If valid: `POST /auth/accept-invitation/` with {token, password, password_confirm}
   - Backend:
     - Creates User record: email=invite.email, password=hashed, full_name=email (default, can update later)
     - Sets roles: assigns user to Group(learner), Group(organizer), etc. per invite.roles
     - Sets UserInvitation.status=ACCEPTED, accepted_at=now
     - Auto-login: returns JWT tokens (access, refresh)
   - Frontend redirects to `/dashboard` (or onboarding if first-time user)

6. **Resend Invite** (InvitationsTab)
   - Admin clicks "Resend" on pending invitation
   - Backend: `POST /admin/invitations/{uuid}/resend/` 
   - Generates new token, updates expires_at = now + 7 days
   - Sends invitation email with new link
   - Toast: "Invitation re-sent to {email}"

7. **Revoke Invite** (InvitationsTab)
   - Admin clicks "Revoke"
   - Backend: `POST /admin/invitations/{uuid}/revoke/`
   - Sets status=REVOKED
   - Token no longer valid; user cannot accept
   - Toast: "Invitation revoked"

8. **Invite Expiry**
   - Cron job (or manual check) marks invites with expires_at < now as status=EXPIRED
   - Can be resent (generates new token)

**Edge cases:**
- Invite token leaked → anyone with token can accept and create account (by design, invite sent to specific email but no verification on accept)
- User already has account with same email → accept flow creates duplicate account (error or merge flow needed)
- Resend on expired invite → generates new token (resets expiry)
- Revoke after accept → no effect (invite already consumed)
- Token with non-existent role → accept still succeeds, user assigned available roles only

**Verification points:**
- UserInvitation in DB: status=PENDING, ACCEPTED, EXPIRED, REVOKED
- User created on accept: `User.objects.filter(email=invite.email)`
- User groups set: `user.groups.filter(name__in=['learner', 'organizer', ...])`
- Email sent: `EmailLog.objects.filter(email_type='invitation', recipient_email=invite.email)`

---

### Flow 11: Email Change Confirmation

**Trigger:** User updates email in `/dashboard/profile-settings`.

**Preconditions:**
- User authenticated
- User on ProfileSettings page (frontend/src/pages/dashboard/ProfileSettings.tsx)

**Step-by-step:**

1. **Initiate Email Change** (ProfileSettings form)
   - Form field: "Email Address"
   - User edits from old@example.com to new@example.com
   - Click "Save" (or separate "Change Email" button)
   - Frontend: `PATCH /users/me/` with {pending_email: "new@example.com"}

2. **Backend Validation**
   - Backend checks:
     - new email not already used by another user (unique constraint)
     - new email different from current email
   - If valid:
     - Sets User.pending_email = new email
     - Generates email_change_token = generate_verification_code(32)
     - Sets email_change_requested_at = now
     - Saves User

3. **Confirmation Email Sent** (to new address)
   - Enqueues send_email(template='email_change_confirmation', recipient=pending_email, context={confirm_link, old_email})
   - Link: `/auth/confirm-email-change?token={token}`
   - Subject: "Confirm your new email address"
   - Body: "We received a request to change your email to [new@]. If this wasn't you, ignore this email."

4. **User Confirms** (via email link)
   - Clicks link → `/auth/confirm-email-change?token={token}`
   - Frontend: `POST /auth/confirm-email-change/` with {token}
   - Backend validates:
     - Token exists and matches User.email_change_token
     - Token not expired (< 24 hours old, from email_change_requested_at)
     - pending_email is set
   - If valid:
     - Sets User.email = pending_email
     - Clears pending_email, email_change_token, email_change_requested_at
     - Broadcasts user_email_changed signal

5. **Post-Confirmation**
   - Email sent to OLD address: "Your email was changed" (for security awareness)
   - Email sent to NEW address: "Your email change is confirmed" (welcome)
   - User can continue using account (JWT tokens still valid)

**Edge cases:**
- User confirms token from old request (>24 hours old) → error "Link expired"
- Confirmation email lost → user can retry from profile settings (sends new email)
- User cancels email change (navigates away during confirm step) → pending_email persists; user can confirm later if token not expired
- Another user tries to confirm token → backend validates token matches requesting user only (user_id embedded or checked via token ownership)
- User changes email again before confirming first → old pending_email overwritten, new token generated

**Verification points:**
- User.pending_email set during request
- Email sent to new address with confirmation link
- User.email updated on confirm
- Confirmation emails sent to both old and new addresses

---

### Flow 12: Password Reset

**Trigger:** User clicks "Forgot Password" on login page, or "Reset Password" in profile settings.

**Preconditions:**
- User account exists with email
- User not currently authenticated (or initiates reset from settings)

**Step-by-step:**

1. **Request Password Reset** (ForgotPasswordPage.tsx)
   - Form field: Email address
   - User enters email, clicks "Send Reset Link"
   - Frontend: `POST /auth/forgot-password/` with {email}

2. **Backend Validation & Token Generation**
   - Looks up user by email (case-insensitive)
   - If not found: returns success message anyway (security: don't reveal if email registered)
   - If found:
     - Generates password_reset_token = generate_verification_code(32)
     - Sets password_reset_sent_at = now
     - Saves User

3. **Reset Email Sent**
   - Enqueues send_email(template='password_reset', recipient=user.email, context={reset_link, username})
   - Link: `/auth/reset-password?token={token}`
   - Subject: "Password Reset Request"
   - Body: "Click the link below to reset your password. Link expires in 24 hours."
   - Sent via email backend

4. **User Clicks Reset Link**
   - Navigates to `/auth/reset-password?token={token}` (ResetPasswordPage.tsx)
   - Frontend: `GET /auth/reset-password/?token={token}` → validates token exists (if needed)

5. **Reset Password Form** (ResetPasswordPage)
   - Form fields: New Password, Confirm Password
   - Both >= 8 characters, match
   - Click "Reset Password"
   - Frontend: `POST /auth/reset-password/` with {token, password, password_confirm}

6. **Backend Password Update**
   - Validates:
     - Token exists in User.password_reset_token
     - Token not expired (now - password_reset_sent_at < 24 hours)
     - password == password_confirm
     - password_length >= 8 (checked on frontend too)
   - If valid:
     - Sets User password = hashed_password(password)
     - Clears password_reset_token, password_reset_sent_at
     - Saves User
     - Response: {success: true}

7. **Post-Reset**
   - Frontend shows success message: "Password reset successfully. You can now log in."
   - Optionally auto-redirects to login page
   - User logs in with email + new password

**Edge cases:**
- Token expired (>24 hours) → error "Reset link expired. Request a new one."
- User already reset password with same token → token cleared; second attempt fails with "Invalid token"
- Token doesn't match DB → error "Invalid reset link"
- User requests reset, then logs in via another method (Google OAuth) before confirming → password reset still works if done later
- New password == old password → allowed (user choice)
- User tries reset token from another account → backend checks token ownership (linked to specific user)

**Verification points:**
- User.password_reset_token set on request
- Email sent with reset link
- User.password updated on confirm
- User can log in with new password

---

### Flow 13: Email Verification on Signup

**Trigger:** User completes signup form (signs up locally, not OAuth).

**Preconditions:**
- User account created (auth_provider=local)
- email_verified=False on signup

**Step-by-step:**

1. **Signup Flow** (signup form or accept-invitation)
   - User creates account: email + password
   - Backend creates User: email, password_hash, email_verified=False, email_verified_token=generate_verification_code(32), email_verification_sent_at=now

2. **Verification Email Sent**
   - Enqueues send_email(template='email_verification', recipient=user.email, context={verify_link, username})
   - Link: `/auth/verify-email?token={token}`
   - Subject: "Verify Your Email"

3. **Check Email Page** (CheckEmailPage.tsx, shows after signup)
   - Message: "We've sent a verification link to [email]. Click it to confirm your account."
   - Optional: "Resend verification email" button (if user lost email)

4. **User Clicks Verification Link**
   - Navigates to `/auth/verify-email?token={token}` (VerifyEmailPage.tsx)
   - Frontend: `POST /auth/verify-email/` with {token}
   - Backend validates:
     - Token matches User.email_verification_token
     - Token not expired (now - email_verification_sent_at < 24 hours)
   - If valid:
     - Sets User.email_verified = True, email_verified_at = now
     - Clears email_verification_token
     - Response: {success: true}

5. **Post-Verification**
   - Frontend shows success: "Email verified! You can now log in."
   - User redirected to login page or auto-logged in (depending on design)

**Login Behavior Before Verification:**
- **Option A:** Block login if email_verified=False → user must verify first
- **Option B:** Allow login (marked as unverified) → some features gated to verified users (registering for paid events, downloading certificates)
- **Option C (current):** Login allowed; invite user to verify via banner, but no hard block

**Edge cases:**
- Token expired (>24 hours) → error "Link expired. Request a new verification email."
- Token already used → error "Email already verified."
- User logs in before verifying → app shows banner "Verify your email to access all features"
- User requests resend → generates new token, sends new email
- User provides invalid token → error "Invalid verification link"

**Verification points:**
- User.email_verified=False on signup
- Email sent with verification link
- User.email_verified=True after confirm
- User can log in

---

### Flow 14: Soft Delete / Deactivation

**Trigger:** Admin deactivates user via `/admin/users` → "Deactivate" menu item, or user initiates account deletion from settings (if enabled).

**Preconditions:**
- User authenticated (admin or self)
- User not last admin (if deactivating admin)

**Step-by-step:**

1. **Deactivate User** (Admin initiates)
   - Admin clicks "Deactivate" on user row in UserManagementPage
   - Modal: "Deactivate [user name]? They will no longer be able to log in."
   - Click "Confirm Deactivate"
   - Frontend: `POST /admin/users/{uuid}/deactivate/`

2. **Backend Deactivate Handler**
   - Checks: User not last admin (error if so)
   - Sets User.is_active = False
   - Saves User
   - Broadcasts user_deactivated signal

3. **Signal Handlers** (if defined)
   - Cancel pending event reminders for this user (ScheduledEmail.objects.filter(recipient_user=user, status=PENDING).update(status=CANCELLED))
   - Cancel pending invitations sent to user (if any)
   - No data deletion (soft deactivation only)

4. **Login Attempt by Deactivated User**
   - User tries to log in with email + password
   - Backend checks `is_active` in login view
   - Returns error: "This account is inactive. Contact support."
   - Login fails, JWT not issued

5. **Data Preservation**
   - Registrations remain (attended status, certificates preserved)
   - Certificates still valid (can be verified by public link)
   - Event organizer can still see their events + registrations
   - Enrollments remain (courses not removed)

6. **Reactivation** (Admin action)
   - Admin clicks "Activate" on deactivated user
   - Sets User.is_active = True
   - User can log in again

**User-Initiated Deletion** (if enabled):
- User clicks "Delete Account" from settings
- Modal: "Are you sure? This cannot be undone." + confirmation checkbox
- Initiates soft delete: User.deleted_at = now, email anonymized (changes to uuid@deleted.accredit.app)
- Triggers anonymization task: clears full_name, professional_title, org_name, phone, etc.
- Can be reversed by admin within 30-day grace period (if supported)

**Edge cases:**
- Last admin cannot be deactivated (error toast)
- Deactivated organizer still has events → events visible to other organizers, registrations unchanged
- Deactivated user is the only organizer for an event → event may be orphaned (depends on policy)
- User deleted in Stripe (manual admin action) — local user not affected (no cascade)

**Verification points:**
- User.is_active=False after deactivation
- User cannot log in
- Registrations preserved in DB
- Admin can reactivate user

---

### Flow 15: Public Certificate / Badge Verification

**Trigger:** Certificate issued → public shareable link generated. User visits link to verify, download, or add to LinkedIn.

**Preconditions:**
- Registration or CourseEnrollment has attendance_eligible=True (or override)
- Certificate issued (Certificate record created, email_sent_at set)
- Verification code generated (unique per certificate)

**Step-by-step:**

1. **Certificate Issuance** (certificates/tasks.py issue_certificate)
   - After event/course ends, eligibility check runs
   - For each eligible registration:
     - Creates Certificate record: registration=reg, code=generate_secure_code(), issued_at=now
     - Generates public URL: `{FRONTEND_URL}/certificates/verify/{code}`
     - Enqueues send_email(template='certificate_issued', recipient=reg.email, context={cert_url, event_title, ...})
     - Creates Notification(type=certificate_issued)

2. **Email with Certificate Link**
   - User receives email: "Your Certificate: [Event Title]"
   - Includes button: "View Certificate" → `/certificates/verify/{code}`
   - User can forward link to others (public sharing)

3. **Public Verification Page** (`/certificates/verify/:code`)
   - No authentication required (public)
   - Frontend: `GET /certificates/{code}/` → returns certificate details
   - Displays:
     - Recipient name
     - Event/course title
     - Issued date
     - Attendance percentage (or "Completed" for courses)
     - Organization name
     - Signature (digital or scanned image)
     - Badge (if earned)
   - Buttons:
     - "Download as PDF" → exports certificate PDF
     - "Add to LinkedIn" (if LinkedIn API enabled)
     - "Share link" → copy URL or share to social

4. **PDF Download**
   - Frontend: `GET /certificates/{code}/pdf/` (or download link)
   - Backend generates PDF from certificate data + template
   - Returns PDF file with headers: Content-Disposition: attachment; filename="Certificate_[Name]_[Event].pdf"
   - File includes event details, QR code linking to verification URL

5. **LinkedIn Integration** (optional)
   - User clicks "Add to LinkedIn"
   - Redirects to LinkedIn OAuth flow
   - On return, creates credential linking certificate to LinkedIn account
   - User can manually add certificate to LinkedIn profile

6. **Certificate Revocation** (admin action)
   - Admin can revoke certificate (marks as revoked)
   - `PATCH /certificates/{code}/` with {status: 'revoked', reason: '...'}
   - Public page shows: "This certificate has been revoked."
   - QR code no longer scans

**QR Code Support:**
- PDF embeds QR code → links to `{FRONTEND_URL}/certificates/verify/{code}`
- Scanner (phone camera or QR app) → opens verification page

**Badge Verification** (`/badges/verify/:code`):
- Similar flow to certificate
- Badge record linked to achievement (e.g., "First Event Attendee", "Milestone Badge")
- Public page: badge image, achievement name, criteria, earned date
- Sharable via link or embedded in portfolio

**Edge cases:**
- Certificate code misspelled or invalid → error "Certificate not found."
- Certificate revoked → verification page shows status with explanation
- User without email → certificate link sent via platform notification only
- PDF generation fails → error "PDF generation temporarily unavailable. Please try again."
- Public link shared widely → no access control (by design; certificate is publicly verifiable credential)

**Verification points:**
- Certificate record in DB with code, issued_at
- PDF generated and downloadable
- Public verification page loads without auth
- QR code scans and resolves to verification page

---

## END OF INVENTORY

**Total Coverage:**
- **Admin Pages:** 3 routes (Users tab, Invitations tab, Users detail, Billing tabs)
- **Live Event Experience:** 1 journey (lobby → join → room → leave → recording)
- **Cross-Cutting Flows:** 15 end-to-end sequences (checkout, refunds, disputes, waitlist, reminders, calendar, notifications, onboarding, invitations, email change, password reset, email verification, deactivation, certificates)

**Test Execution Approach:**
- **Unit tests:** Database models, serializers, signal handlers
- **Integration tests:** API endpoints (mocked Stripe, livekit)
- **E2E tests:** Chrome browser scenarios (Selenium/Playwright) for all major user journeys
- **Manual testing:** Admin UI interactions, real Stripe webhook testing (sandbox), livekit room features

All flows documented with preconditions, visible UI elements, step-by-step interactions, backend side effects, edge cases, and verification points to enable comprehensive test plan generation.