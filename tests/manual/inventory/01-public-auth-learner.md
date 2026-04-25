# Public · Auth · Learner — Test Inventory

**Scope:** PUBLIC, AUTH, and LEARNER surfaces only (frontend/src/pages/).
**Repo:** /media/beyonder/LENOVO_USB_HDD/universe/code/projects/accredit

---

## PUBLIC / ANONYMOUS PAGES

### Page: `/` — AuthenticatedRoot (file: frontend/src/components/auth/AuthenticatedRoot.tsx)

**Purpose:** Root redirect route that branches to dashboard if authenticated, else login.

**Preconditions:**
- No auth required (checks isAuthenticated at render time)
- Deployed instance must be active

**Visible elements / regions:**
- Renders nothing (redirect-only component)
- Flash of loader if checking auth state

**Interactions to test (exhaustive):**
1. Navigate to `/` while unauthenticated → redirects to `/login`
2. Navigate to `/` while authenticated → redirects to `/dashboard`

**Edge cases & state variants:**
- Auth context not yet initialized (should show spinner)
- Auth context load failure

---

### Page: `/terms` — TermsPage (file: frontend/src/pages/public/TermsPage.tsx)

**Purpose:** Display platform Terms of Service.

**Preconditions:**
- No auth required
- Wrapped in AuthLayout

**Visible elements / regions:**
- Static HTML prose sections (h1 "Terms of Service", h2 sections: Acceptance of Terms, Description of Service, User Accounts, Content, Payments and Subscriptions, etc.)
- "Last Updated" timestamp
- Multiple subsections with paragraph/list content (not dynamic)

**Interactions to test (exhaustive):**
1. Page load → all text renders, no errors
2. Scroll to bottom → all content accessible
3. Links within text (if any) → click and navigate

**Edge cases & state variants:**
- Mobile view: ensure responsive layout

---

### Page: `/privacy` — PrivacyPage (file: frontend/src/pages/public/PrivacyPage.tsx)

**Purpose:** Display Privacy Policy.

**Preconditions:**
- No auth required
- Wrapped in AuthLayout

**Visible elements / regions:**
- Prose sections with privacy terms, data collection, GDPR, etc.
- Last updated date

**Interactions to test (exhaustive):**
1. Page load → all content renders
2. Scroll and read all sections
3. Mobile responsive

---

### Page: `/cookies` — CookiePolicyPage (file: frontend/src/pages/public/CookiePolicyPage.tsx)

**Purpose:** Display Cookie Policy.

**Preconditions:**
- No auth required

**Visible elements / regions:**
- Cookie disclosure and preferences info

**Interactions to test (exhaustive):**
1. Page load and scroll
2. Cookie banner interaction (if present)

---

### Page: `/verify` and `/verify/:code` — CertificateVerify (file: frontend/src/pages/certificates/CertificateVerify.tsx)

**Purpose:** Public-facing certificate verification lookup & verification.

**Preconditions:**
- No auth required
- `:code` param: certificate short_code (alphanumeric, typically 8-12 chars)

**Visible elements / regions:**
- **No code provided state:** Hero card with ShieldCheck icon, "Verify Certificate" heading, description, input form for code entry
- **Loading state:** Spinner with "Verifying certificate…"
- **Certificate found state:**
  - Header with event/course title
  - Status badge (active/issued/revoked)
  - Verification code
  - Event date
  - Registrant name
  - Organizer name
  - CPD credits (if issued)
  - Share button (copy link)
  - Download button (if file_url available)
  - Print button
- **Certificate not found (404) state:** Error card with AlertCircle icon, "Certificate not found" heading, suggestion to check code
- **Other error state (500, network):** "Unable to verify certificate" message

**Interactions to test (exhaustive):**
1. `/verify` (no code) → form rendered
2. Enter valid code → submit → certificate data loads and displays
3. Copy verification link button → link copied to clipboard, toast shows
4. Download button (if available) → opens file URL in new tab
5. Print button → browser print dialog
6. Share icon on certificate → copy link
7. Enter invalid code → 404 error displayed
8. Network error during verification → error state
9. Expired/revoked certificate with status field → UI shows status badge (revoked, expired if tracked)

**Edge cases & state variants:**
- Certificate with/without file_url
- Certificate status: active, issued, revoked
- Missing code param on url entry
- Invalid format code
- Very long code (overflow handling)
- Slow network (timeout handling)

---

### Page: `/badges/verify/:code` — PublicBadgePage (file: frontend/src/pages/badges/PublicBadgePage.tsx)

**Purpose:** Public badge verification (similar to certificate verify but for badges).

**Preconditions:**
- No auth required
- `:code` param: badge verification_code or short_code

**Visible elements / regions:**
- Badge image/icon display
- Badge name and issuer
- Event/course source
- Issue date
- Verification details
- Share/download controls

**Interactions to test (exhaustive):**
1. Navigate with valid badge code → badge details display
2. Navigate with invalid badge code → 404 error
3. Copy share link → clipboard copy toast
4. Download badge (if available) → file download
5. Print → browser print dialog

---

### Page: `/discover/events` — EventDiscovery (file: frontend/src/pages/public/EventDiscovery.tsx)

**Purpose:** Public event discovery and browsing page with filters and pagination.

**Preconditions:**
- No auth required
- `getPublicEvents()` API call should return paginated list of published events

**Visible elements / regions:**
- Page header: "Discover Events"
- Search bar (full-text search on title, description)
- Filter sidebar / panel:
  - Event Types checkboxes: Webinar, Workshop, Training Session, Lecture, Other
  - Formats checkboxes: Online, In-Person, Hybrid
  - Price filter: Free Only, Paid Only toggle
  - Clear All Filters button
  - Active filter count badge
- Results grid (3 columns desktop, 1-2 mobile):
  - Event cards showing: image (or gradient placeholder), title, short_description, date+time, format badge, price, attendee count
  - Hover effects on cards
- Pagination controls: Previous/Next buttons, current page indicator
- Loading state: skeleton loaders for cards
- Empty state: "No events match your filters" message with icon

**Interactions to test (exhaustive):**
1. Page load → initial 12 events load (or page_size from state)
2. Search by title → API call fires with search param, results update, pagination resets to page 1
   - API endpoint: `getPublicEvents({ search: term, page: 1, page_size: 12 })`
3. Click Event Type checkbox → filter applied, results update
   - API param: `event_type: "webinar,workshop,…"` (comma-separated)
4. Click Format checkbox → filter applied, results update
   - API param: `format: "online,hybrid,…"`
5. Toggle "Free Only" → filter applied
   - API param: `is_free: true` (if only free selected)
6. Toggle "Paid Only" → filter applied
   - API param: `is_free: false` (if only paid selected)
7. Click "Clear All Filters" → all filters reset, search cleared, page 1 reloads
8. Pagination: Click next page → `page` increments, scroll to top, results load
9. Pagination: Click prev page → `page` decrements
10. Click event card → navigate to `/events/:id/details`
11. Window resize → filters may collapse on mobile, hamburger icon to toggle (if implemented)

**Edge cases & state variants:**
- Zero events in catalog → empty state
- All filters applied with 0 results → empty state with "No events match your filters"
- Network error during search → error toast
- Slow load (simulate with network throttle) → skeleton loaders visible for >2s
- Very long event titles → truncate with ellipsis
- Very old event (past date) → still appears in discovery, marked as "past" or filtered out depending on backend logic
- Large page count → pagination UI tested at page 1, last page, middle pages

---

### Page: `/discover/courses` — CourseCatalogPage (file: frontend/src/pages/courses/CourseCatalogPage.tsx)

**Purpose:** Public course discovery, browsing, and enrollment/purchase.

**Preconditions:**
- No auth required (but some flows require login)
- Fetches public, published courses from API
- Client-side filter: only `status === 'published' && is_public` shown

**Visible elements / regions:**
- Page header: "Discover Courses"
- Search bar (title search)
- Filter/Sort panel:
  - Free Only checkbox
  - Paid Only checkbox
  - Sort dropdown: newest, popular, title A-Z (if implemented)
  - Clear Filters button
- Results grid:
  - Course cards: image, title, org logo, short_description, price, CPD credits, difficulty/duration
  - Avatar with org info
  - Hover effects
- Pagination (12 per page)
- Loading state
- Empty state

**Interactions to test (exhaustive):**
1. Page load → fetch published public courses
2. Search → API call with `search` param, results update, page 1
3. Free Only checkbox → client-side filter applied to results
4. Paid Only checkbox → client-side filter applied
5. Sort dropdown (if present) → reorder displayed courses
6. Clear filters → reset, reload page 1
7. Pagination → load next/prev page
8. Click course card → navigate to `/courses/:slug`
9. (If authenticated) Enroll button on card → call `enrollInCourse()` or redirect to purchase

**Edge cases & state variants:**
- No published courses → empty state
- Mixed free/paid courses → both filter toggles work independently and in combination
- Course with missing logo → fallback to initials avatar
- Very long course titles → ellipsis truncation
- Course with 0 enrollments → still visible
- Network error → error toast

---

### Page: `/events/:id/details` — EventDetail (file: frontend/src/pages/public/EventDetail.tsx)

**Purpose:** Public event detail page with registration call-to-action.

**Preconditions:**
- No auth required (but registration CTA may require auth)
- `:id` param: event uuid or slug
- Fetches event data from `getPublicEvent(id)`
- If authenticated, checks if user already registered via `getMyRegistrations()`

**Visible elements / regions:**
- Event hero/image (or gradient placeholder)
- Title, subtitle/description
- Key details card:
  - Date + time (with timezone if available)
  - Duration (minutes)
  - Location (if in-person/hybrid)
  - Format badge (Online/In-Person/Hybrid)
  - Capacity (X slots available or "Fully booked")
- Organizer card:
  - Org logo, name, description
- Full description (sanitized HTML)
- Agenda/Schedule (if included)
- Speakers list (with bios if available)
- Custom registration fields (if event has them)
- CTA buttons:
  - **Unauthenticated:** "Register" → redirect to `/events/:id/register`
  - **Already registered (confirmed):** "View Registration" or "Go to Lobby" button
  - **Already registered (waitlisted):** "You're on the waitlist" badge, option to view details
  - **Already registered (payment pending):** "Complete Payment" button
  - **Event full/closed:** "Event is full" message
- Related events from same org (carousel or list of 3-6 events)
- Share buttons (social, copy link)

**Interactions to test (exhaustive):**
1. Page load with valid id → event data displays
2. Page load with invalid id → error state: "Event not found"
3. (Unauthenticated) Click Register → navigate to `/events/:id/register`
4. (Authenticated, not registered) Click Register → navigate to register page
5. (Authenticated, confirmed registration) Click Join/Lobby button → navigate to `/events/:id/lobby`
6. (Authenticated, waitlisted) Status badge shows, interaction options limited
7. (Authenticated, payment pending) Show "Complete Payment" CTA
8. Related events carousel → click event → navigate to its detail
9. Share button → copy event link or social share
10. Scroll long description → content scrolls and is readable
11. Custom fields (if present) → display below description

**Edge cases & state variants:**
- Event with no image → gradient bg
- Event with no speakers → "No speakers listed"
- Event with no custom fields → registration form simple
- Event past date → "This event has ended" state, no registration CTA
- Event cancelled → red banner "This event has been cancelled"
- Event full/waitlist enabled → shows capacity status, waitlist option on registration
- Network error loading related events → don't break main event display, silently skip related section

---

### Page: `/events/:id/register` — EventRegistration (file: frontend/src/pages/public/EventRegistration.tsx)

**Purpose:** Public event registration form for paid/free events.

**Preconditions:**
- No auth required (anonymous registration allowed)
- `:id` param: event uuid
- Fetches event data
- If authenticated user provided, auto-fills email/name fields
- Registration can be free or trigger Stripe checkout

**Visible elements / regions:**
- Event title + "Register" heading
- Form card with fields:
  - Email (required; pre-filled if user authenticated)
  - First Name (required)
  - Last Name (required)
  - Professional Title (optional)
  - Organization Name (optional)
  - Custom Fields (if event configured any)
  - Allow Public Verification checkbox (default: true)
- Submit button: "Register" (free) or "Proceed to Payment" (paid)
- Loading/submitting state on button
- Success screen (after registration):
  - Confirmation icon/message
  - Confirmation email sent notice
  - Links to view ticket, add to calendar, etc.
- Error states (form validation, API errors):
  - Field-level validation errors
  - "Registration closed" error
  - "Event is full" error
  - Generic API error message

**Interactions to test (exhaustive):**
1. Page load → event title displays, form renders with empty fields (unless authenticated)
2. Leave fields empty → submit button click → validation errors show on each required field
3. Enter invalid email → validation error
4. Enter all required fields → submit → loading state, then success screen (for free events) or redirect to Stripe (for paid)
5. (Paid event) Click submit → `registerForEvent()` called, returns `checkout_url`, window.location.href redirects to Stripe
6. (Free event) Click submit → `registerForEvent()` called, `step` state changes to "success", confirmation page displays
7. Close success screen, navigate back → registration not lost (already created on backend)
8. Custom fields render based on event config (type, required, options)
9. Allow Public Verification toggle → can check/uncheck
10. Network error → error toast + form remains editable for retry
11. (Authenticated) Pre-fill: email from user.email, name from user.full_name split
12. (If registration requires approval) "Your registration is pending approval" message after submit

**Edge cases & state variants:**
- Event with 0 custom fields → form simple
- Event with multiple required custom fields (5+) → form scrollable, all fields visible
- Event with single-select custom field → dropdown renders
- Event with multi-select custom field → checkboxes or multi-select dropdown
- Registration closed (closes_at in past) → form disabled with "Registration closed" message
- Event is_free true → no payment flow
- Event is_free false, price > 0 → payment flow
- Event waitlist_enabled, at capacity → shows "Join Waitlist" option instead of register
- Very long event title → wraps or truncates
- Mobile view → form fields stack vertically, submit button full width

---

### Page: `/r/:registrationUuid/lobby` — EventLobbyPage (guest access, file: frontend/src/pages/events/EventLobbyPage.tsx)

**Purpose:** Pre-event lobby for registered attendees (guest, no auth required if using registration UUID).

**Preconditions:**
- No auth required (uses `:registrationUuid` from URL)
- Fetches lobby data from `getRegistrationLobby(registrationUuid)`
- Shows event details and join button if within 15 minutes of start or event is live

**Visible elements / regions:**
- Event title + short description
- Countdown timer:
  - If event in future: "Starts in 2h 15m"
  - If event live or within 15 min: "Join Now" or "Event is Live"
  - If event ended: "Recording Available" (if present)
- Event details card:
  - When: date, time, timezone, duration
  - Where: location (if in-person)
  - Attendees: capacity and registered count (if public)
- Join button / Video embed:
  - If event not yet live (>15 min away): disabled or "Doors open 15 minutes before"
  - If event live or within 15 min: enabled, clickable → calls JoinButton component → joins video room
  - If event ended: "Recording" link (if available) instead of join button
- Add to Calendar button (generates .ics or opens Google Calendar add dialog)
- Back link (if accessed via authenticated user, shows "Back to My Events")

**Interactions to test (exhaustive):**
1. Navigate with valid registrationUuid → lobby loads
2. Navigate with invalid registrationUuid → error page "Couldn't load this event"
3. Event not yet live (>15 min away) → Join button disabled, countdown shows
4. Event live (now >= starts_at and now <= ends_at) → Join button enabled
5. Within 15 minutes of start → Join button enabled even if not yet started
6. Click Join button → calls `JoinButton` component logic, opens videoroom or Jitsi/Zoom link
7. Event ended, recording available → Recording link visible instead of join
8. Event ended, no recording → "Recording will be available later" message
9. Add to Calendar button → opens calendar dialog or downloads .ics
10. Responsive design: mobile view → all elements stack, button full width

**Edge cases & state variants:**
- Event cancelled → "This event has been cancelled" banner, join disabled
- Guest access with guest not found (registrationUuid invalid) → 404
- Network error loading lobby data → error state with retry
- Event past end time but recording not yet published → "Recording will be available soon" state
- Very long event title → wraps or truncates
- Timezone edge case (event at 11:59pm UTC) → countdown shows correct time

---

### Page: `/courses/:slug` — PublicCourseDetailPage (file: frontend/src/pages/courses/PublicCourseDetailPage.tsx)

**Purpose:** Public course detail page with enrollment and purchase options.

**Preconditions:**
- No auth required (but enrollment may require login)
- `:slug` param: course slug (e.g., "intro-python")
- Fetches course by slug
- If authenticated, checks if user already enrolled

**Visible elements / regions:**
- Course hero image (or placeholder gradient)
- Course title, short_description
- Org logo and name
- Course stats card:
  - CPD credits
  - Estimated hours
  - Difficulty level (if available)
  - Format: Online / Hybrid / Live
  - Enrollment count / completion rate
  - Price (Free or $XX.XX in currency)
- Course description (sanitized HTML)
- Curriculum/Modules (expandable list):
  - Module titles, optional descriptions
  - Content count per module
  - Estimated duration
- Learning outcomes (if provided)
- Requirements/Prerequisites (if any)
- Instructor/Author info (avatar, bio)
- CTA buttons:
  - **Unauthenticated:** "Sign in to Enroll"
  - **Authenticated, not enrolled:** "Enroll Free" (free) or "Enroll Now" (paid, with price)
  - **Authenticated, enrolled:** "Go to Course" or "Resume Course" (if in progress)
  - **Enrollment closed:** "Enrollment Closed" message
- Related courses from same org (carousel/grid of 3)
- Reviews/Testimonials (if available)

**Interactions to test (exhaustive):**
1. Page load with valid slug → course details load
2. Page load with invalid slug → navigate to `/discover/courses`
3. (Unauthenticated) Click "Sign in to Enroll" → redirect to `/login?returnUrl=/courses/:slug`
4. (Authenticated, not enrolled, free course) Click "Enroll Free" → `enrollInCourse()` called, navigate to `/learn/:courseUuid`
5. (Authenticated, not enrolled, paid) Click "Enroll Now" → button shows loading, `courseCheckout()` called, redirect to Stripe checkout
6. (Authenticated, already enrolled) Click "Go to Course" → navigate to `/learn/:courseUuid`
7. Expand module → module contents display
8. Related courses → click card → navigate to that course detail
9. Scroll long description → content readable, no layout breaks
10. Mobile responsive → all sections stack, buttons full width

**Edge cases & state variants:**
- Course with no image → gradient background
- Course with 0 modules → "No modules yet" or similar
- Course is_free false, price_cents > 0 → shows price, triggers checkout flow
- Course status draft or archived (shouldn't be public but test if displayed) → warning or unavailable
- Course enrollment closed → enrollment buttons disabled with message
- Network error on enroll → error toast, form state persists
- Authenticated user already enrolled, attempts to enroll again → skip checkout, navigate to course

---

### Page: `/programs` — ProgramDiscoveryPage (file: frontend/src/pages/public/ProgramDiscoveryPage.tsx)

**Purpose:** Browse curated bundles of courses (programs).

**Preconditions:**
- No auth required
- Fetches public, published programs
- Client-side filter: `status === 'published' && is_public`

**Visible elements / regions:**
- Page header: "Programs" + "Curated bundles of courses — buy the whole program at a discount."
- Search bar (search by program title)
- Program grid (3 columns desktop):
  - Program image (or Layers icon placeholder)
  - Title
  - Short description
  - Price display (Free or currency)
  - Course count badge
- Loading state: spinner
- Empty state: "No programs are available yet" or "No programs match your search"

**Interactions to test (exhaustive):**
1. Page load → programs list loads
2. Type in search → results filter, "No programs match your search" if none
3. Click program card → navigate to `/programs/:slug`
4. Clear search → all programs reappear

**Edge cases & state variants:**
- Zero programs in catalog → empty state
- Search with no matches → "No programs match your search."
- Program with no image → Layers icon + gradient bg
- Program with very long title → ellipsis truncation
- Responsive → grid changes to 2 or 1 column on mobile

---

### Page: `/programs/:slug` — PublicProgramDetailPage (file: frontend/src/pages/programs/PublicProgramDetailPage.tsx)

**Purpose:** View program details and enroll in bundled courses.

**Preconditions:**
- No auth required (enrollment may require auth)
- `:slug` param: program slug
- Fetches program by slug

**Visible elements / regions:**
- Program title, description
- Price display (Free or with discount badge)
- Org info
- Course list (sorted by `order`):
  - Course title, short_description, duration, price
- Enrollment value prop / benefits
- CTA button:
  - **Free program:** "Enroll in Program"
  - **Paid program:** "Enroll Now - $XX" or "Checkout"
  - **Authenticated, enrolled:** "View My Programs"
- Related programs (if present)

**Interactions to test (exhaustive):**
1. Page load with valid slug → program details load
2. Page load with invalid slug → navigate to `/programs`
3. (Unauthenticated) Click enroll → redirect to `/login`
4. (Authenticated, free) Click "Enroll in Program" → `programEnrollFree()` called, success toast, navigate to `/my-programs`
5. (Authenticated, paid) Click enroll → `programCheckout()` called, redirect to Stripe
6. Course list scrollable and readable
7. Mobile responsive

---

### Page: `/checkout/success` and `/checkout/cancel` — CheckoutReturn (file: frontend/src/pages/public/CheckoutReturn.tsx)

**Purpose:** Stripe checkout return pages (post-payment success/cancellation).

**Preconditions:**
- Post-Stripe redirect
- Success: user completed payment, Stripe created checkout session, order is finalized
- Cancel: user clicked back/cancelled checkout before completing

**Visible elements / regions:**
- **Success page:**
  - Checkmark icon / success badge
  - "Thank you for your purchase" heading
  - Confirmation message with next steps
  - Order summary (if available)
  - "Go to Dashboard" or "View My Events" button
- **Cancel page:**
  - Alert icon
  - "Payment Cancelled" heading
  - "You can try again anytime" message
  - "Return to Browse" or "Go to Events" button

**Interactions to test (exhaustive):**
1. Navigate to `/checkout/success` → success state renders
2. Click "Go to Dashboard" → navigate to `/dashboard`
3. Navigate to `/checkout/cancel` → cancel state renders
4. Click "Go to Events" → navigate to `/events` or `/discover/events`

**Edge cases & state variants:**
- Page accessed directly (without going through checkout) → still renders, no error
- Session ID in URL query param (if backend checks) → validate or ignore gracefully

---

## AUTH PAGES

### Page: `/login` — LoginPage (file: frontend/src/pages/auth/LoginPage.tsx)

**Purpose:** Email/password login form with optional Google OAuth and remember-me toggle.

**Preconditions:**
- Unauthenticated user
- Wrapped in AuthLayout
- Query param `returnUrl` (optional) specifies post-login redirect
- Query param `error` (optional) displays OAuth errors (e.g., `invite_only`)
- Firebase configured (optional, for Google sign-in)

**Visible elements / regions:**
- Form card with:
  - Email input field
  - Password input field with show/hide toggle
  - Remember Me checkbox
  - Submit button "Sign In"
  - Loading state on submit
- "Forgot Password?" link
- "Don't have an account? Sign up" link
- (Optional) Google Sign-In button (if Firebase configured and `isFirebaseConfigured()` true)
- Error message display (red alert box):
  - "Invalid email or password"
  - "Account temporarily locked"
  - "Registration is by invitation only" (if `error=invite_only` query param)
- Form validation errors (red text under fields)

**Interactions to test (exhaustive):**
1. Page load → form renders empty
2. Leave email field empty, submit → validation error "Please enter a valid email address."
3. Enter invalid email format (e.g., "notanemail") → validation error on blur/submit
4. Enter email but no password → validation error "Password must be at least 8 characters."
5. Enter email + password (correct) → submit → loading state, success toast, redirect to `/dashboard` or `returnUrl`
   - API call: `login({ email, password })`
6. Enter email + password (incorrect) → submit → error toast "Invalid email or password"
7. Check "Remember Me" checkbox → form state tracks, (if backend supports) sets persistent login
8. Click "Show password" icon → password field type toggles to text
9. Click "Forgot Password?" → navigate to `/forgot-password`
10. Click signup link → navigate to `/signup`
11. (If Google OAuth available) Click Google button → Firebase OAuth flow, email auto-filled after callback
12. (If `error=invite_only` in query) → warning toast at load: "Registration is by invitation only. Contact your institution administrator for access."
13. With `returnUrl` query param → after login, redirect to that URL instead of `/dashboard`
14. Slow network → loading spinner visible, button disabled during submission

**Edge cases & state variants:**
- Empty email + empty password → show validation errors on both
- Email with leading/trailing spaces → trim and process
- Very long password → no overflow, input scrolls
- OAuth flow fails → error handling, fallback to email/password form
- Network error during login → error toast, form retains values for retry
- Account locked after failed attempts (if backend implements) → error message and unlock instructions
- Deployment in invite_only mode → signup link hidden or disabled, message shown
- Session already exists (cookies, localStorage) → immediate redirect without form

---

### Page: `/signup` — SignupPage (file: frontend/src/pages/auth/SignupPage.tsx)

**Purpose:** User registration form with password confirmation and terms acceptance.

**Preconditions:**
- Unauthenticated
- `deployment.registration_mode` checked (if "invite_only", page shows message and disables signup)
- Wrapped in AuthLayout

**Visible elements / regions:**
- Form card with:
  - Full Name input (required)
  - Email input (required)
  - Password input (required, with show/hide toggle, real-time validation)
  - Confirm Password input (required, with show/hide toggle)
  - Submit button "Create Account"
  - Loading state
- Password requirements indicator (real-time):
  - At least 8 characters
  - Contains uppercase letter
  - Contains lowercase letter
  - Contains number
  - (Visual checkmarks or X marks showing compliance)
- "Already have an account? Sign in" link
- (Optional) Google Sign-In button
- Error messages:
  - Field-level validation
  - "Email already in use"
  - "Passwords don't match"
- **Invite-only mode:** Large card with message "Sign-up is disabled. Accounts on this platform are created by invitation only. Contact your administrator for access." + link to login

**Interactions to test (exhaustive):**
1. Page load (invite_only mode off) → form renders
2. Page load (invite_only mode on) → disable message and "Back to sign in" link show
3. Enter name, email, password, confirm → all validations pass → submit button enabled
4. Password strength:
   - "pass" (too short) → show "must be at least 8 characters"
   - "Password1" → show all checks pass
   - "password1" (no uppercase) → highlight missing uppercase check
   - "PASSWORD1" (no lowercase) → highlight missing lowercase check
   - "Password" (no number) → highlight missing number check
5. Confirm password doesn't match password → error "Passwords don't match."
6. Email already in use → submit → error "Email already in use. Please use a different email or sign in."
7. Valid signup → submit → loading state, success toast "Account created. Check your email to verify.", redirect to `/auth/check-email?email=...`
   - API call: `signup({ full_name, email, password, password_confirm })`
8. Click "Sign in" link → navigate to `/login`
9. Show/hide password toggle → text input type changes
10. Slow network → loading button
11. Network error → error toast, form retains values

**Edge cases & state variants:**
- Full name with special characters → accepted (e.g., "Jean-Pierre O'Brien")
- Email with subdomain (e.g., "user+tag@example.com") → accepted
- Very long password (100+ chars) → accepted, input scrolls
- Copy-paste password to confirm → both fields populate, validation passes
- Invite-only mode redirect: if user accesses signup while in invite_only, show disable message

---

### Page: `/auth/verify-email` — VerifyEmailPage (file: frontend/src/pages/auth/VerifyEmailPage.tsx)

**Purpose:** Email verification from signup or password reset with optional password setup step.

**Preconditions:**
- Query param `token` (required): email verification token from email link
- Query param `password_token` (optional): if present, user must set password after verification
- Unauthenticated initially, becomes authenticated after successful verification

**Visible elements / regions:**
- **Loading state:**
  - Spinner + "Verifying your email…"
- **Success state (no password_token):**
  - Checkmark icon
  - "Email Verified!" heading
  - "You're all set. Redirecting to onboarding…" message
  - Auto-redirect to `/onboarding` after 2 seconds
- **Password setup required state (password_token present):**
  - "Email Verified! Please set your password" heading
  - Password input (required)
  - Confirm password input (required)
  - Show/hide toggle on both
  - Password strength indicator
  - Submit button "Set Password"
  - Loading state during submit
  - Error message display (e.g., "Passwords don't match")
- **Error state:**
  - Alert icon
  - "Verification Failed" heading
  - Error message:
    - "No verification token provided."
    - "Invalid or expired token."
    - "Token already used."
  - "Request a new link" or "Back to login" button

**Interactions to test (exhaustive):**
1. Navigate `/auth/verify-email?token=<valid>` → loading state, verification attempt, success state, auto-redirect to `/onboarding`
2. Navigate `/auth/verify-email?token=<invalid>` → error state "Invalid or expired token."
3. Navigate `/auth/verify-email` (no token) → error state "No verification token provided."
4. Navigate `/auth/verify-email?token=<used>` (token already consumed) → error state "Token already used."
5. With `password_token`, form shows password setup:
   - Enter password, confirm, submit → `confirmPasswordReset(passwordToken, password)` called
   - On success → auto-login (token/user set in context), redirect to `/onboarding`
   - Password mismatch → error "Passwords don't match."
   - Weak password → validation error
6. Network error → error state with retry option
7. Click "Request a new link" → navigate to `/signup` or show resend email form

**Edge cases & state variants:**
- Token expires while on page (edge case, unlikely)
- Multiple verify attempts with same token → second attempt shows "already used"
- Password setup required but password validation fails → error shown, form remains editable
- Auto-redirect to onboarding may be interrupted if user navigates away

---

### Page: `/auth/check-email` — CheckEmailPage (file: frontend/src/pages/auth/CheckEmailPage.tsx)

**Purpose:** Confirmation page after signup, instructs user to check email for verification link.

**Preconditions:**
- Unauthenticated
- Query param `email` (optional): email address verification was sent to (passed during navigation)

**Visible elements / regions:**
- Email icon in circle at top
- "Check your email" heading
- "We've sent a verification link to <email>" description
- Instructions: "Click the link in the email to verify your account and continue to onboarding. If you don't see it, check your spam folder."
- "Resend Email" button (with cooldown: 60 seconds between resends)
  - States: idle, loading, success ("Email resent!"), error
  - Cooldown timer: "Resend in 45s" (counting down)
  - On error: shorter cooldown (15s)
- "Back to sign in" link

**Interactions to test (exhaustive):**
1. Page load → email address displays (from query param or "your email address" if missing)
2. Click "Resend Email" → `resendVerificationEmail(email)` called
   - Loading state during request
   - Success: "Email resent!" toast, cooldown timer starts (60 seconds)
   - Error: error message displayed, shorter cooldown (15 seconds)
3. During cooldown: button disabled + "Resend in 45s" text, countdown updates every second
4. After cooldown expires: button re-enabled
5. Click "Back to sign in" → navigate to `/login`
6. Network error during resend → error toast shown

**Edge cases & state variants:**
- Email not provided in URL → "your email address" shown instead
- Resend error (network, invalid email, rate limited) → error message + shorter cooldown
- User goes to check email, verifies → no UI update, but if they return, they should be redirected (handled by login check)

---

### Page: `/forgot-password` — ForgotPasswordPage (file: frontend/src/pages/auth/ForgotPasswordPage.tsx)

**Purpose:** Request password reset link via email.

**Preconditions:**
- Unauthenticated
- Wrapped in AuthLayout

**Visible elements / regions:**
- Form card:
  - Email input (required)
  - Submit button "Send Reset Link"
  - Loading state
- Error message display
- **After submission (success):**
  - Email icon in circle
  - "Check your email" heading
  - "We've sent a password reset link to <email>" description
  - "Didn't receive the email? Check your spam folder or try again." text
  - "Try a different email" button (to reset form)
  - "Back to Login" link
- Success/error states are displayed as conditional renders, not navigation

**Interactions to test (exhaustive):**
1. Page load → form renders
2. Leave email empty, submit → validation error or disabled submit
3. Enter invalid email → validation error
4. Enter valid email → submit → loading state, success state (isSent becomes true)
   - API call: `resetPassword({ email })` (security: shows success even if email not found)
5. Click "Try a different email" → form clears, isSent resets to false, re-editable
6. Click "Back to Login" → navigate to `/login`
7. Network error → error toast (but isSent may still be true for security, preventing retry with same email)
8. Check spam folder instruction visible in success state

**Edge cases & state variants:**
- Email not in system → API shows success anyway (security best practice)
- Very long email address → input scrolls or wraps

---

### Page: `/auth/reset-password` — ResetPasswordPage (file: frontend/src/pages/auth/ResetPasswordPage.tsx)

**Purpose:** Confirm password reset with token from email link.

**Preconditions:**
- Query param `token` (required): reset token from email link
- Unauthenticated

**Visible elements / regions:**
- **No token provided state:**
  - Alert icon (red)
  - "Invalid Reset Link" heading
  - "This password reset link is invalid or has expired." description
  - "Request New Reset Link" button → navigate to `/forgot-password`
  - "Back to Login" link
- **Form state:**
  - "Reset Your Password" heading
  - Password input (required, with show/hide toggle)
  - Confirm Password input (required, with show/hide toggle)
  - Real-time password strength validation:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
  - Submit button "Update Password"
  - Loading state
- **Success state:**
  - Checkmark icon (green)
  - "Password Reset Successfully" heading
  - "You can now sign in with your new password." description
  - "Go to Login" button
- Error message display:
  - "Passwords don't match"
  - "Password must be at least 8 characters"
  - "Password must contain uppercase, lowercase, and a number"
  - "Token expired or invalid"

**Interactions to test (exhaustive):**
1. Navigate `/auth/reset-password` (no token) → error state
2. Navigate `/auth/reset-password?token=<invalid>` → error state "Invalid Reset Link"
3. Click "Request New Reset Link" → navigate to `/forgot-password`
4. Click "Back to Login" (from error) → navigate to `/login`
5. With valid token, form renders
6. Enter password + confirm (matching, valid) → submit → loading state, success state, "Go to Login" button
   - API call: `confirmPasswordReset(token, password, confirmPassword)`
7. Passwords don't match → error "Passwords don't match"
8. Password too short → validation error "Password must be at least 8 characters"
9. Password lacks uppercase → validation error
10. Password lacks number → validation error
11. All validations pass → submit enabled
12. Network error → error message, form retains values
13. Token expired between form load and submit → error "Token expired or invalid"
14. Click "Go to Login" (from success) → navigate to `/login`

**Edge cases & state variants:**
- Token used twice → second attempt shows "Token expired or invalid"
- Very long password (100+ chars) → accepted
- Password validation changes in real-time as user types

---

### Page: `/auth/accept-invitation` — AcceptInvitationPage (file: frontend/src/pages/auth/AcceptInvitationPage.tsx)

**Purpose:** Accept org invite and set initial password.

**Preconditions:**
- Query param `token` (required): invitation token sent via email
- Unauthenticated

**Visible elements / regions:**
- **No token state:**
  - "Invalid Link" card
  - "This invitation link is invalid or missing." message
- **Form state:**
  - "Set Up Your Account" heading
  - "Choose a password to complete your account setup." description
  - Password input (required)
  - Confirm Password input (required)
  - Show/hide toggles
  - Submit button "Complete Setup"
  - Loading state
  - Error message display (red alert)
- **Success:** Auto-login and redirect to `/dashboard`

**Interactions to test (exhaustive):**
1. Navigate `/auth/accept-invitation` (no token) → error card shown
2. Navigate `/auth/accept-invitation?token=<valid>` → form renders
3. Enter mismatched passwords → error "Passwords don't match."
4. Enter short password (< 8 chars) → error "Password must be at least 8 characters."
5. Valid password + confirm → submit → loading state, success toast, auto-login, redirect to `/dashboard`
   - API call: `POST /auth/accept-invitation/` with `{ token, password, password_confirm }`
6. Token invalid or expired → error "Failed to accept invitation. Please try again."
7. Network error → error displayed, form retains values

**Edge cases & state variants:**
- Token already used → error when submitting
- User account already exists with that email → error or alternate flow

---

### Page: `/auth/confirm-email-change` — ConfirmEmailChangePage (file: frontend/src/pages/auth/ConfirmEmailChangePage.tsx)

**Purpose:** Confirm email change from settings page.

**Preconditions:**
- Query param `token` (required): confirmation token from email link
- Unauthenticated (user must re-login after confirmation)

**Visible elements / regions:**
- **Loading state:**
  - Spinner + "Confirming your new email…"
- **Success state:**
  - Checkmark icon (green)
  - "Email updated" heading
  - "Your email address has been updated. For security, all sessions on other devices have been signed out. Please log in again with your new email." description
  - "Go to login" button
- **Error state:**
  - Alert icon (red)
  - "Can't confirm change" heading
  - Error message:
    - "This confirmation link has expired. Request a new one from your settings."
    - "That email is now in use by another account. Start a new request with a different address."
    - "This confirmation link is invalid."
    - Generic "Failed to confirm email change."
  - "Back to settings" button

**Interactions to test (exhaustive):**
1. Navigate `/auth/confirm-email-change?token=<valid>` → loading, success state
2. Click "Go to login" → navigate to `/login`
3. Navigate `/auth/confirm-email-change?token=<invalid>` → error state "This confirmation link is invalid."
4. Navigate `/auth/confirm-email-change?token=<expired>` → error state "This confirmation link has expired..."
5. Navigate `/auth/confirm-email-change` (no token) → error "Missing confirmation token."
6. Navigate `/auth/confirm-email-change?token=<taken>` → error "That email is now in use by another account..."
7. Network error → error state with generic message

**Edge cases & state variants:**
- User attempts to confirm same token twice → second attempt shows error
- Email was taken by someone else between request and confirmation → error with instruction to start new request

---

## LEARNER PAGES (Authenticated, requiredFeature ≈ none / attendee role)

### Page: `/dashboard` — DashboardPage (file: frontend/src/pages/dashboard/DashboardPage.tsx)

**Purpose:** Role-based dashboard entry point (dispatcher).

**Preconditions:**
- Authenticated required
- User role determines which dashboard variant is rendered:
  - Organizer → OrganizerDashboard
  - Instructor → InstructorDashboard
  - Learner (default) → AttendeeDashboard

**Visible elements / regions:**
- Role-dependent (see respective dashboard components)

**Interactions to test (exhaustive):**
1. Authenticated as learner → AttendeeDashboard renders
2. Authenticated as instructor → InstructorDashboard renders
3. Authenticated as organizer → OrganizerDashboard renders
4. Unauthenticated redirect → handled by ProtectedRoute (not this component's concern)

---

### Page: `/events` — EventsPage (file: frontend/src/pages/events/EventsPage.tsx)

**Purpose:** Authenticated user event discovery page (similar to public, but may show additional filters or organizer options).

**Preconditions:**
- Authenticated required
- Shows events user can attend or manage (depending on role)

**Visible elements / regions:**
- Event list/grid similar to `/discover/events`
- (If organizer role) Create Event button
- Search, filters, pagination
- Tabs or filters for upcoming/past/my events (depending on implementation)

**Interactions to test (exhaustive):**
1. Page load → events load (including past events if user is organizer)
2. Search → filter results
3. (If organizer) Create Event button → navigate to `/events/create`
4. Click event → navigate to event detail or management page

---

### Page: `/events/:uuid` — EventDetailPage (file: frontend/src/pages/events/EventDetailPage.tsx)

**Purpose:** Authenticated event detail (for attendees and organizers; organizer view shows management options).

**Preconditions:**
- Authenticated required
- `:uuid` param: event uuid

**Visible elements / regions:**
- Event details (title, description, date, location, etc.)
- (Attendee view) Register/join options
- (Organizer view) Edit, Duplicate, Manage Attendees, View Reports buttons
- Attendee list (if organizer)
- Analytics (if organizer)

**Interactions to test (exhaustive):**
1. Organizer navigates to own event → edit/manage buttons visible
2. Attendee navigates to event → register button visible
3. Click Edit (organizer) → navigate to `/events/:uuid/edit`
4. Click Manage (organizer) → navigate to `/organizer/events/:uuid/manage`

---

### Page: `/events/:id/lobby` (auth) — EventLobbyPage (file: frontend/src/pages/events/EventLobbyPage.tsx)

**Purpose:** Pre-event lobby for authenticated attendees (via `/events/:id/lobby` route, not guest UUID).

**Preconditions:**
- Authenticated required
- `:id` param: event uuid or id
- User is registered for event

**Visible elements / regions:**
- Same as guest lobby but with "Back to My Events" button
- Event details card with join/countdown
- Video room embed/button if event is live

**Interactions to test (exhaustive):**
1. Authenticated user navigates to event lobby → lobbies loads
2. Join button → opens video room (Jitsi, Zoom, or custom video)
3. Within 15 minutes of start → join enabled
4. Event live → join enabled
5. Event ended → recording link shown

---

### Page: `/events/:id/recording` — EventRecordingPage (file: frontend/src/pages/events/EventRecordingPage.tsx)

**Purpose:** Watch post-event recording.

**Preconditions:**
- Authenticated required
- Event has completed and recording published
- `:id` param: event uuid

**Visible elements / regions:**
- Event title + subtitle
- Video player (HTML5 video or embedded player)
- Recording metadata:
  - Recorded date
  - Duration
  - Format (MP4, HLS, etc.)
- Download button (if enabled)
- Share button
- Back to My Events link

**Interactions to test (exhaustive):**
1. Page load → recording loads and plays
2. Play/pause → video controls work
3. Seek to different timestamp → video seeks
4. Download button (if present) → downloads video file
5. Share button → copy link or social share
6. Back link → navigate to `/my-events`
7. No recording yet → "No recording available yet" message
8. Multiple recordings → shows latest/primary one

---

### Page: `/registrations` — MyLearningPage (file: frontend/src/pages/registrations/MyRegistrationsPage.tsx)

**Purpose:** Unified view of event registrations and course enrollments.

**Preconditions:**
- Authenticated required
- Combines registrations (events) and enrollments (courses)

**Visible elements / regions:**
- Tabs: Events, Courses (or combined list)
- Registration cards:
  - Event title, date, status badge (Confirmed/Attended/Cancelled/Waitlisted/Pending Payment)
  - Payment status badge (Paid/Pending/Failed/Refunded)
  - Actions:
    - View Details
    - Give Feedback (if attended, feedback not yet submitted)
    - Download Certificate (if issued)
    - Join/Lobby button (if upcoming and can join)
- Course enrollments:
  - Course title, progress bar, status
  - Resume button
- Search by event/course title
- Filters: Status (Confirmed, Attended, etc.), time (Upcoming, Past)
- Empty state (no registrations/enrollments)
- Link Registrations button (finds registrations by email and links to account)

**Interactions to test (exhaustive):**
1. Page load → registrations and enrollments fetch
2. Click registration → navigate to event detail or lobby
3. Attended event, no feedback → "Give Feedback" button visible
4. Click "Give Feedback" → FeedbackModal opens
5. Feedback modal:
   - Form with rating, comment fields
   - Submit button
   - On submit → API call, feedback saved, button disabled or removed
6. Certificate issued, click Download → certificate PDF downloads
7. Link Registrations button → fetches registrations by current user email, links any found to account, toast shows count
8. Search filters registrations/enrollments
9. Status filter → shows only selected statuses
10. Mobile responsive → cards stack, buttons reorganized

**Edge cases & state variants:**
- User with no registrations → "You haven't registered for any events yet" + "Browse Events" button
- User with no enrollments → similar empty state for courses
- Registration with pending payment → "Complete Payment" button visible
- Registration waitlisted → "Waitlisted" badge, no join button
- Certificate not issued yet (event past but cert not yet issued) → no download button, "Certificate pending" message
- Feedback already submitted → feedback button disabled or shows "Feedback submitted"
- Network error on load → error toast, retry option
- Network error on link registrations → error toast

---

### Page: `/accreditations` — MyAccreditationsPage (file: frontend/src/pages/accreditations/MyAccreditationsPage.tsx)

**Purpose:** View all issued certificates and badges in unified view.

**Preconditions:**
- Authenticated required
- Fetches certificates and badges from API

**Visible elements / regions:**
- Stats cards:
  - Total count, Certificate count, Badge count
- Search bar (by title, source, code)
- Filter dropdown (All, Certificates, Badges)
- Accreditation grid:
  - Card for each certificate/badge:
    - Icon (Award for cert, BadgeCheck for badge)
    - Title, Source (event/course), Issue date
    - View/Share/Download buttons
- Empty state: "You haven't earned any accreditations yet" + "Attend events or complete courses to start earning."

**Interactions to test (exhaustive):**
1. Page load → fetch accreditations, display counts
2. Search by title → filter results
3. Search by code → filter results
4. Filter dropdown: select "Certificates" → show only certificates
5. Filter dropdown: select "Badges" → show only badges
6. Filter dropdown: select "All" → show both
7. Click accreditation card:
   - Certificates: navigate to `/verify/:code`
   - Badges: navigate to `/badges/verify/:code`
8. Share button → copy verification link to clipboard
9. Download button (if present) → download file
10. No accreditations → empty state with guidance
11. Mobile responsive → grid adjusts to 1-2 columns

---

### Page: `/my-programs` — MyProgramsPage (file: frontend/src/pages/programs/MyProgramsPage.tsx)

**Purpose:** View programs user is enrolled in.

**Preconditions:**
- Authenticated required
- Fetches user's program enrollments

**Visible elements / regions:**
- Program cards (similar to discovery, but with progress bars):
  - Program title, image
  - Courses completed / total
  - Progress bar (% of courses completed)
  - "Resume" button (navigate to first incomplete course)
  - "View Details" button
- Empty state: "You haven't enrolled in any programs yet" + "Browse Programs" button
- Search/filter (optional)

**Interactions to test (exhaustive):**
1. Page load → fetch enrolled programs
2. Click "Resume" → navigate to `/learn/:courseUuid` for first incomplete course in program
3. Click "View Details" → navigate to `/programs/:slug`
4. Browse Programs button → navigate to `/programs`
5. No programs → empty state
6. All courses completed → progress bar at 100%, "View Details" button primary

---

### Page: `/certificates` — CertificatesPage (file: frontend/src/pages/certificates/CertificatesPage.tsx)

**Purpose:** View issued certificates (for learners) or all certificates issued by org (for organizers/staff).

**Preconditions:**
- Authenticated required
- API returns only certs issued to current user (unless staff role)

**Visible elements / regions:**
- Page header (title may vary by role: "My Certificates" vs "Certificates")
- Total certificates badge
- Search bar (by event/course title or code)
- Table (responsive):
  - Columns: Event/Course | Certificate ID | Issued | CPD Credits | Status | Actions
  - Rows: one per certificate
  - Status badge (Issued, Revoked, Expired if tracked)
  - Actions buttons:
    - Eye icon (View/Verify) → open `/verify/:code` in new tab
    - Copy icon (Copy link) → copy verification URL to clipboard, toast shows
    - Download icon → download PDF, error if PDF not available
    - Share icon (Share) → copy link
- Empty state: "You haven't earned any certificates yet" + "Attend events or complete courses to earn certificates."

**Interactions to test (exhaustive):**
1. Page load → fetch user's certificates
2. Search by event title → filter table
3. Search by course title → filter table
4. Search by certificate ID → filter table
5. View button → open certificate verification page in new tab
6. Copy link button → copy URL, toast shows "Verification link copied!"
7. Copy icon state: after click, change to checkmark temporarily, then back to copy
8. Download button:
   - Available and working → PDF opens in new tab/downloads
   - Not available → error toast "PDF not available for this certificate"
   - Feedback required (from backend) → error with action link "Give Feedback" → navigate to `/registrations`
9. Status badge shows:
   - Issued (green)
   - Revoked (red) if revoked_at set
   - Expired (yellow) if expiration tracking enabled
10. Mobile responsive → table becomes card list or scrollable

**Edge cases & state variants:**
- Certificate with revoked status → red badge, download disabled
- Certificate expired → yellow badge
- No PDF generated yet → download button disabled
- Staff view (organizer/admin) → different header, may show all org certificates
- Network error → error toast, retry option

---

### Page: `/my-events` — MyEvents (file: frontend/src/pages/dashboard/attendee/MyEvents.tsx)

**Purpose:** View upcoming and past events attendee is registered for.

**Preconditions:**
- Authenticated required
- Fetches registrations from API

**Visible elements / regions:**
- Tabs: Upcoming | Past
- Search bar (search by event title)
- Link Registrations button (finds events by email and links)
- Event cards:
  - Event title, date, time
  - Status badge (Confirmed, Waitlisted, Cancelled, Attended)
  - Actions:
    - Upcoming: Join/Lobby button (if within 15 min or live), View Details
    - Past: View Recording (if available), Give Feedback (if not submitted), View Certificate
- Empty state per tab:
  - Upcoming: "You don't have any upcoming events" + "Browse Events" button
  - Past: "You haven't attended any events yet"
- Active filter indicator and count in tabs

**Interactions to test (exhaustive):**
1. Page load → fetch registrations, split into upcoming/past
2. Search → filter events
3. Upcoming tab → show only future events (event.starts_at >= now)
4. Past tab → show only past events or cancelled
5. Join button (upcoming, within 15 min) → navigate to `/events/:id/lobby`
6. View Details → navigate to `/events/:uuid`
7. View Recording (past) → navigate to `/events/:id/recording`
8. Give Feedback (past, attended, feedback not submitted) → open FeedbackModal
9. View Certificate (past, attended, cert issued) → download or navigate to cert page
10. Link Registrations → API call, toast shows count linked
11. Mobile responsive → cards stack

**Edge cases & state variants:**
- Event upcoming, >15 min away → Join button disabled, shows "Doors open at XX time"
- Event cancelled → red badge, all action buttons disabled
- Event past, no recording yet → "Recording will be available soon" message
- Network error → error toast

---

### Page: `/courses` (authenticated) — CourseCatalogPage (file: frontend/src/pages/courses/index.tsx, reuses CourseCatalogPage)

**Purpose:** Browse and discover courses while authenticated (may have additional options vs public view).

**Preconditions:**
- Authenticated required (but page may also be accessible unauthenticated)
- Shows all public courses or personalized recommendations

**Visible elements / regions:**
- Search, filters (same as public discovery)
- Course grid with cards
- Enrollment button (shows different state if already enrolled)
- Pagination

**Interactions to test (exhaustive):**
1. Authenticated user views course → "Enroll" or "Resume" button appears depending on enrollment status
2. Enrolled user clicks "Resume" → navigate to `/learn/:courseUuid`
3. Not enrolled user clicks "Enroll" → enroll in free course or redirect to checkout for paid
4. Search, filters, pagination (same as public)

---

### Page: `/learn/:courseUuid` — CoursePlayerPage (file: frontend/src/pages/courses/CoursePlayerPage.tsx)

**Purpose:** Course learning experience with module navigation, content display, assignments, quizzes, progress tracking, discussions, and announcements.

**Preconditions:**
- Authenticated required
- User must be enrolled in course (checked on mount, redirect if not)
- `:courseUuid` param: course UUID

**Visible elements / regions:**
- **Left sidebar (module navigation):**
  - Collapsible list of modules
  - Module headers (expandable):
    - Module title, progress (X / Y items completed), lock icon if not available
    - Content items nested under module:
      - Icon (text, video, quiz, document, external, lesson, assignment)
      - Item title
      - Checkmark if completed
      - Lock icon if locked (sequential unlock)
      - Click to navigate/load content
- **Main content area:**
  - Breadcrumb: Course > Module > Content Item
  - Back button
  - Current item title and metadata (type, duration if applicable)
  - **Content types:**
    - **Text:** HTML-rendered text content, scrollable
    - **Video:** Embedded video player (HTML5 or external), play/pause/seek controls, duration
    - **Document:** Embedded PDF viewer or download link
    - **Lesson:** Structured lesson with text + interactive elements
    - **External link:** Opens in new tab with warning
    - **Quiz:** Question display with radio/checkbox/text input answers
      - Submit button
      - Score display (if attempted)
      - Retry button (if retries allowed)
      - Explanation text (if provided)
    - **Assignment:** Text editor (Quill) + file upload
      - Status: Draft / Submitted / In Review / Needs Revision / Graded / Approved
      - Submission history (past attempts)
      - Feedback from instructor (if submitted and reviewed)
      - Resubmit button (if needs revision)
  - Mark as Complete button / checkbox (for required content)
  - Next/Previous item buttons
- **Right sidebar / tabs:**
  - Announcements panel (collapsible, shows recent org/course announcements)
  - Discussion panel (collapsible, shows course discussion threads):
    - Current discussions for this content item
    - New post form
    - Thread replies
  - Sessions panel (if hybrid course, shows live session schedule)
- **Progress bar at top:** Overall course completion percentage
- **Loading states:** Skeleton loaders for content while fetching

**Interactions to test (exhaustive):**
1. Page load (user enrolled) → course data, modules, and progress fetch
2. Page load (user not enrolled) → redirect to `/courses/:slug`
3. Module collapsed → click to expand, contents show
4. Module locked → lock icon shows, expand disabled
5. Click content item → item loads in main area
   - API call: `getModuleContents(moduleUuid)` if needed
6. **Content type: Text** → HTML renders, scrollable
7. **Content type: Video**
   - Video plays
   - Seek to different time
   - Mark as complete after watching (automatic on playback completion or manual checkbox)
8. **Content type: Document** → PDF embedded or download link
9. **Content type: Quiz**
   - Display questions (shuffle if enabled)
   - Select radio button / checkbox
   - Type text answer
   - Click Submit
   - Score displayed (e.g., "8/10")
   - Explanation text shown
   - Retry button (if attempts_remaining > 0):
     - Click → re-present questions
     - Previous attempt score shown for comparison
   - On last attempt, no retry button
   - Passing score → checkmark, content marked complete
   - Failing score → red X, may show "You need 70% to pass"
10. **Content type: Assignment**
    - Text editor (Quill) shows rich text tools
    - Type or paste content
    - File upload zone (drag-drop or click to select)
    - Save Draft button → saves `AssignmentSubmission` with status=draft
    - Submit button (only if draft exists) → status changes to submitted
    - If already submitted:
      - Edit button → opens editor again with draft mode (if resubmit allowed)
      - Submit button (if needs_revision status)
    - Instructor feedback displayed (if submission reviewed)
11. Mark as Complete checkbox → toggles completion, `updateContentProgress()` called
12. Next button → navigate to next sequential item (or next module if at module end)
13. Previous button → navigate to previous item
14. Announcement click → expand, show full text
15. Discussion: Click on discussion → show replies and reply form
16. Discussion: Type reply → submit → reply posted, thread updated
17. Sessions panel: If hybrid course, show upcoming live sessions with join buttons
18. Progress bar → updates as content completed
19. Module status → updates as child content completed
20. Scroll sidebar → module list scrolls while content area scrolls independently

**Edge cases & state variants:**
- **Content locked (sequential):** Lock icon, item unclickable until previous content completed
- **Module unavailable:** All contents locked, module header shows lock
- **Quiz with 0 attempts left:** Submit button disabled, "No attempts remaining"
- **Assignment feedback too long:** Scrollable in feedback section
- **Video not playable:** Error message "Video unavailable"
- **Document download fails:** Error message, retry option
- **Network error loading content:** Error displayed, reload button
- **Enrollment blocked mid-course:** "Enrollment has ended" message, content inaccessible
- **Quiz with randomized questions:** Each attempt shows different order (if backend supports)
- **Course completion:**
  - All required content completed → "Course Complete!" banner
  - Certificate auto-issued (if auto_issue enabled) → banner shows "Certificate issued"
  - Badge auto-issued → banner shows "Badge earned"
- **Long module list:** Sidebar scrollable, current module stays visible
- **Very long content:** Main area scrollable independently
- **Mobile responsive:**
  - Sidebar collapses to hamburger menu
  - Content full-width
  - Right tabs (announcements/discussion) stack below content or in bottom sheet

---

### Page: `/badges` — MyBadgesPage (file: frontend/src/pages/badges/MyBadgesPage.tsx)

**Purpose:** View digital badges earned.

**Preconditions:**
- Authenticated required
- Fetches issued badges from API

**Visible elements / regions:**
- Page header: "My Badges"
- Badge grid (4 columns desktop, responsive):
  - Badge image (or Award icon placeholder)
  - Badge name (title)
  - Source (event or course)
  - Issue date
  - Actions:
    - Share button → copy verification link to clipboard
    - Download button (if available) → download badge file
- Empty state: "No badges earned yet" + "Complete courses or attend events to start building your digital badge collection."
- Loading state: spinner

**Interactions to test (exhaustive):**
1. Page load → fetch user's badges
2. Share button → copy link, toast shows "Verification link copied!"
3. Download button → downloads badge file
4. Badge card click (optional) → navigate to badge detail/verification page
5. Mobile responsive → grid adjusts to 1-2 columns

---

### Page: `/cpd` — CPDTracking (file: frontend/src/pages/dashboard/attendee/CPDTracking.tsx)

**Purpose:** Track CPD progress toward annual requirements.

**Preconditions:**
- Authenticated required
- Fetches CPD progress and requirements

**Visible elements / regions:**
- Page header: "CPD Tracking"
- Overall progress card:
  - Total earned / total required credits
  - Progress bar (percentage)
  - Status (e.g., "On track" if >= 100%, "XX credits to go" if < 100%)
- Per-requirement cards (if multiple CPD types):
  - CPD type (e.g., "General CPD", "Medical CPD")
  - Annual requirement (e.g., "50 credits/year")
  - Period type (e.g., "Calendar Year", "Financial Year")
  - Credits earned toward this requirement
  - Progress bar
  - Progress percentage
- Add Requirement button (dialog):
  - CPD Type dropdown
  - Annual Requirement number input
  - Period Type dropdown (Calendar Year, Financial Year, etc.)
  - Save button
- Delete Requirement button (per requirement) → confirm dialog
- Export Report dropdown:
  - Export as JSON
  - Export as CSV
  - Export as TXT
  - Loading state during export
- Loading state: spinner
- Empty state: "No CPD tracking requirements set up" + "Add a requirement to get started"

**Interactions to test (exhaustive):**
1. Page load → fetch CPD progress
2. Progress cards display with correct values
3. Add Requirement button → dialog opens
4. Fill form (select CPD type, enter requirement, select period) → Save → success toast, requirement added to list
5. Delete Requirement button (on card) → confirm dialog → click Delete → requirement removed
6. Export dropdown → click Export as CSV → file downloads
7. Progress bars → update as credits earned
8. Overall progress → sum of all requirements
9. Mobile responsive → cards stack

**Edge cases & state variants:**
- Zero requirements → empty state with guidance
- Single requirement → shows that requirement's progress primarily
- Multiple requirements → multiple cards, each with separate progress
- Credits earned > requirement → progress bar at 100%+, status message "Exceeds requirement"
- No CPD credits yet → progress bars at 0%
- Network error on add → error toast, form retains values
- Network error on delete → error toast
- Export takes time → loading spinner on button, disabled during export

---

### Page: `/notifications` — Notifications (file: frontend/src/pages/dashboard/Notifications.tsx)

**Purpose:** View and manage notifications (read/unread, delete).

**Preconditions:**
- Authenticated required
- Fetches notifications from API

**Visible elements / regions:**
- Page header: "Notifications"
- Tabs: All | Unread
- Unread count badge (visible in header if unread > 0)
- Mark All as Read button (visible if unread count > 0)
- Notification list:
  - Each notification card shows:
    - Icon (by type: org_invite, payment_failed, refund_processed, certificate_issued, discussion_reply, system, etc.)
    - Title/Subject
    - Snippet/preview text
    - Date (relative: "2 hours ago")
    - Unread indicator (dot or badge)
    - Read/Unread toggle button
    - Delete button
    - (Optional) Action link (e.g., "View Certificate")
- Empty state: "You have no notifications"
- Loading state: spinner

**Interactions to test (exhaustive):**
1. Page load → fetch notifications
2. Unread badge shows count
3. All tab → show all notifications
4. Unread tab → show only unread (is_read === false)
5. Mark All as Read button → all notifications marked read, button disappears
6. Click notification card (if clickable) → navigate to action_url if present
7. Read/Unread toggle button → mark notification as read/unread, UI updates, toast confirms
8. Delete button → remove notification from list, toast confirms
9. Notification types display different icons:
   - org_invite → Building2 icon
   - payment_failed → CreditCard icon (red)
   - refund_processed → DollarSign icon (green)
   - certificate_issued → award icon (gold)
   - discussion_reply → MessageSquare icon
   - system → Info icon
10. Mobile responsive → cards stack

**Edge cases & state variants:**
- Zero notifications → empty state
- Very long notification text → truncate or scrollable
- Notification with action_url → link navigates to resource
- Notification without action_url → no link, info-only
- Network error on delete → error toast
- Notifications from 6+ months ago → still shown, not archived automatically

---

### Page: `/settings` — ProfileSettings (file: frontend/src/pages/dashboard/ProfileSettings.tsx)

**Purpose:** User profile and account settings (edit profile, change password, notification preferences, email change, data export, account deletion, payout setup for organizers).

**Preconditions:**
- Authenticated required
- Fetches user profile and notification preferences from API

**Visible elements / regions:**
- **General Tab:**
  - Full Name field (pre-filled, editable)
  - Professional Title field (optional, editable)
  - Organization Name field (optional, editable)
  - Timezone dropdown (optional, editable)
  - GST/HST Number field (optional, for Canadian users, editable)
  - Save button (disabled until changes made)
  - Success/error toast on save
- **Security Tab:**
  - Current Password field (required)
  - New Password field (required)
  - Confirm Password field (required)
  - Password strength indicator
  - Change Password button
  - Success/error toast
  - Email change section:
    - Current Email (read-only display)
    - New Email field (editable)
    - Password field (required for verification)
    - Request Email Change button
    - (If pending change) "Confirmation email sent to..." message
    - Success/error toast
- **Notifications Tab:**
  - Preference toggles:
    - Event reminders (24h before, 15m before, etc.)
    - Certificate issued notifications
    - Course announcements
    - Payment notifications
    - Discussion replies
    - (Per-type toggles)
  - Save button (save all preferences)
  - Success/error toast
- **Active Sessions / Devices Tab** (if implemented):
  - List of active sessions (device, location, last activity, IP)
  - Logout from this device button
  - Logout from all other devices button
- **Billing / Payouts Tab** (if organizer):
  - Stripe Connect status
  - Connect button (if not connected)
  - Payout dashboard link (if connected)
  - Next payout date and amount
  - Payout history
- **Data & Privacy Tab:**
  - Download My Data button → exports user data as JSON/CSV
  - Loading state during export
  - Delete Account button → opens confirm dialog with warning
    - Confirm dialog asks for password
    - Warning: "This action is permanent and cannot be undone. All your data, events, and certificates will be deleted."
    - Delete button in dialog (disabled until password entered)
    - Cancel button
- Avatar upload (at top of page, optional):
  - Camera icon or "Change Avatar" button
  - File picker for image upload
  - Loading state during upload
- Loading state (on initial load): skeleton loaders for all sections

**Interactions to test (exhaustive):**
1. Page load → fetch user profile and preferences
2. **General tab:**
   - Edit Full Name → change, Save button enabled
   - Click Save → `updateProfile()` called, success toast
   - Edit Professional Title → change, Save
   - Edit Organization Name → change, Save
   - Select Timezone from dropdown → Save
   - Network error on save → error toast, form retains values
3. **Security tab:**
   - Change Password:
     - Enter current password (incorrect) → error "Invalid password"
     - Enter current password (correct), new password (weak) → validation error
     - Passwords don't match → error "Passwords don't match"
     - Correct current + valid new matching password → Change Password button enabled
     - Click Change Password → loading state, success toast "Password changed successfully", form clears
   - Email Change:
     - Enter new email + password (correct) → Request Email Change button enabled
     - Click Request → `requestEmailChange()` called, success message "Confirmation link sent to..."
     - User checks email, clicks link in `/auth/confirm-email-change?token=...`
     - On confirmation, session ends (logout), user redirected to login
4. **Notifications tab:**
   - Toggle preference → form tracks change
   - Click Save → `updateNotificationPreferences()` called, success toast
   - Multiple preferences toggled → all saved together
5. **Sessions tab** (if present):
   - List of current sessions displayed
   - Logout button on a session → logs out that session, list updates
   - Logout All Other Devices → confirms, logs out all other sessions
6. **Billing tab** (if organizer):
   - Connect Stripe button → OAuth flow to Stripe, redirects back with status
   - View Payout Dashboard link → opens Stripe dashboard
   - Next payout info displayed if available
7. **Data & Privacy tab:**
   - Download My Data button → export dialog or direct download starts
   - Delete Account button → confirm dialog opens
   - In confirm dialog:
     - Enter password field
     - Delete button disabled until password entered
     - Click Delete → `deleteAccount()` called, account deleted, user logged out, redirected to login with message
     - Click Cancel → dialog closes, no action taken
   - Export loading state visible during download
8. Avatar upload (if present):
   - Click change avatar → file picker opens
   - Select image → preview shows, upload button enabled
   - Click Upload → loading, success toast, avatar updates
9. Mobile responsive → all tabs accessible via scroll, form fields stack

**Edge cases & state variants:**
- Very long email address → input scrolls
- Password with special characters → accepted
- Email already in use → error "That email is already in use"
- Email change pending confirmation → message shows, new email not active until confirmed
- Timezone with DST → correct timezone handling
- Network error on preference save → error toast, preferences not updated
- Avatar upload large file → error "File too large", retry option
- Delete account with API error → error message, account not deleted
- Multiple unsaved changes across tabs → warning on navigation away (optional)

---

### Page: `/onboarding` — OnboardingWizard (file: frontend/src/pages/onboarding/OnboardingWizard.tsx)

**Purpose:** Post-signup onboarding wizard with profile setup and role-specific steps.

**Preconditions:**
- Authenticated required
- Post-signup flow (typically after email verification)
- Primary role of user determines which steps are shown

**Visible elements / regions:**
- **Progress header:**
  - Step indicators (circles with icons or numbers)
  - Progress bar
  - Step titles visible (desktop) or mobile-friendly
- **Step 0: Welcome**
  - Welcome message
  - "Get Started" button or auto-advance
  - Confetti animation (optional)
- **Step 1: Profile (for organizers/instructors)**
  - Full Name field (pre-filled, editable)
  - Organization Name field (editable)
  - Save button
  - Skip button (optional)
- **Step 2: Complete / Get Started**
  - Summary or final message
  - "Go to Dashboard" button (or auto-navigate)
  - Completion state (check mark)
- **For learners:** Simpler flow (Welcome → Complete)
- Navigation buttons: Previous, Next, Skip (if applicable)

**Interactions to test (exhaustive):**
1. Page load → current step displays (default step 0)
2. Click Next button → move to step 1
3. Click Previous button → move back to step 0
4. Fill profile fields (organizer) → Next button enabled
5. Click Save (if profile step) → `updateProfile()` called, advance to next step
6. Skip button (if available) → advance without saving (optional)
7. Click Complete / Go to Dashboard (final step) → `completeOnboarding()` called, navigate to `/dashboard`
8. URL updates with step param: `/onboarding?step=1`, `/onboarding?step=2`, etc.
9. Refresh page → returns to saved step
10. Mobile responsive → step indicators adjust, buttons stack

**Edge cases & state variants:**
- Learner role → fewer steps (welcome + complete)
- Organizer role → profile step included
- Instructor role → different title on final step
- Profile validation error → step doesn't advance, error displayed
- Network error on save → error toast, step remains
- User navigates away mid-onboarding → onboarding not marked complete, user returns to `/onboarding` on next login
- Back to login during onboarding (edge case, user bypasses) → handled by ProtectedRoute

---

## Additional State Matrices & Comprehensive Testing Scenarios

### Registration State Matrix (for `/registrations` and MyLearningPage)

**Status × Payment Status × Certificate Issued × Feedback Submitted Combinations:**

| Status | payment_status | certificate_issued | feedback_submitted | UI Behavior | Buttons |
|--------|---|---|---|---|---|
| pending | pending | false | false | Amber badge "Pending Payment", show "Complete Payment" | Complete Payment, View Event |
| confirmed | paid | false | false | Green badge "Confirmed", show date/time | Join (if upcoming, within 15m), View Event, Give Feedback (if past) |
| confirmed | paid | true | false | Green badge, "Confirmed"; gold badge "Certificate Issued" | View Event, Download Certificate, Give Feedback (if past & attended) |
| confirmed | paid | true | true | Same as above; "Feedback submitted" indicator | View Event, Download Certificate |
| attended | paid | true | true | Blue badge "Attended", gold cert badge | View Recording, Download Certificate |
| waitlisted | na | false | false | Yellow badge "Waitlisted", show position | View Event |
| cancelled | refunded | false | false | Red badge "Cancelled"; if refund show "Refund processed" | View Event |

---

### Course Player State Matrix (for `/learn/:courseUuid`)

**Content Type × Completion × Lock Status × User Permission Combinations:**

| Content Type | completed | is_available | Behavior |
|---|---|---|---|
| text | false | true | Display, show Mark Complete checkbox |
| text | true | true | Display, checkbox checked, content locked from editing |
| video | false | true | Play video, auto-mark complete on end or manual checkbox |
| video | true | true | Display playback controls, marked complete |
| quiz | false | true | Show questions, Submit button, no score yet |
| quiz | true | true | Show last score, Retry button (if attempts_remaining > 0) |
| quiz | false | false | Lock icon, "Complete previous content to unlock" |
| assignment | false | true | Show editor, Save Draft, Submit button |
| assignment | true | true | Show submission with status (Graded, Needs Revision, etc.) |
| document | false | true | Display or download link available |
| external | false | true | Show external link with warning |
| lesson | false | true | Display structured lesson content |

---

### Certificate/Badge Verification State Matrix (for `/verify/:code`)

| Certificate Status | File Present | is_valid | UI State |
|---|---|---|---|
| active | true | true | ✓ Green badge, full details, download enabled |
| issued | true | true | ✓ Green badge, full details, download enabled |
| revoked | any | false | ✗ Red badge "Revoked", details shown but download disabled |
| (expired) | true | false | ⚠ Yellow badge "Expired", details shown, download disabled |
| (not found) | — | false | ✗ Error page "Certificate not found" |

---

## Key API Interactions to Verify

### GET Endpoints Tested

- `getPublicEvents()` → EventDiscovery, EventDetail
- `getPublicEvent(id)` → EventDetail, EventLobbyPage
- `getPublicCourses()` → CourseCatalogPage, PublicCourseDetailPage (related)
- `getCourseBySlug(slug)` → PublicCourseDetailPage
- `getPublicPrograms(search)` → ProgramDiscoveryPage
- `getProgramBySlug(slug)` → PublicProgramDetailPage
- `getMyRegistrations()` → EventDetail (check registration), MyLearningPage, MyEvents
- `getEnrollments()` → PublicCourseDetailPage (enrollment check), CoursePlayerPage
- `getCourse(uuid)` → CoursePlayerPage
- `getCourseModules(courseUuid)` → CoursePlayerPage
- `getCourseProgress(courseUuid)` → CoursePlayerPage
- `getModuleContents(moduleUuid)` → CoursePlayerPage
- `getRegistrationLobby(registrationUuid)` → EventLobbyPage (guest)
- `getMyCertificates()` → CertificatesPage
- `getMyBadges()` → MyBadgesPage
- `getMyAccreditations()` → MyAccreditationsPage
- `getCPDProgress()` → CPDTracking
- `getNotifications()` → Notifications
- `getCurrentUser()` → ProfileSettings
- `getNotificationPreferences()` → ProfileSettings
- `verifyCertificate(code)` → CertificateVerify
- `getVideoRecordings(eventUuid)` → EventRecordingPage

### POST Endpoints Tested

- `registerForEvent(eventUuid, payload)` → EventRegistration
- `startRegistrationCheckout(registrationUuid)` → EventRegistration (payment)
- `enrollInCourse(courseUuid)` → PublicCourseDetailPage (free)
- `courseCheckout(courseUuid)` → PublicCourseDetailPage (paid)
- `programEnrollFree(programUuid)` → PublicProgramDetailPage
- `programCheckout(programUuid)` → PublicProgramDetailPage (paid)
- `linkRegistrations()` → MyLearningPage, MyEvents
- `updateContentProgress(contentUuid, { completed })` → CoursePlayerPage
- `createSubmission(assignmentUuid, data)` → CoursePlayerPage (assignment)
- `submitSubmission(submissionUuid)` → CoursePlayerPage
- `markNotificationRead(uuid)` → Notifications
- `markAllNotificationsRead()` → Notifications
- `deleteNotification(uuid)` → Notifications
- `updateProfile(data)` → ProfileSettings, OnboardingWizard
- `changePassword(data)` → ProfileSettings
- `requestEmailChange(data)` → ProfileSettings
- `confirmEmailChange(token)` → ConfirmEmailChangePage
- `updateNotificationPreferences(data)` → ProfileSettings
- `exportUserData()` → ProfileSettings
- `deleteAccount(password)` → ProfileSettings (with confirm dialog)
- `completeOnboarding()` → OnboardingWizard
- `login(credentials)` → LoginPage
- `signup(data)` → SignupPage
- `verifyEmail(token)` → VerifyEmailPage
- `resetPassword(email)` → ForgotPasswordPage
- `confirmPasswordReset(token, password)` → ResetPasswordPage, VerifyEmailPage (password setup)
- `acceptInvitation(token, password)` → AcceptInvitationPage
- `resendVerificationEmail(email)` → CheckEmailPage

### Error States to Test on All Pages

- **Network timeout:** Long-running API call → error toast, retry option
- **4xx errors:**
  - 400 Bad Request: form validation errors, display on form
  - 403 Forbidden: permission error, "You don't have access to this resource"
  - 404 Not Found: resource not found, navigate away or show error state
- **5xx errors:** Generic "Something went wrong" error, retry button
- **Offline state:** Network unavailable → error, optional offline UI

---

## Mobile Responsiveness Checklist (Test All Pages)

- [ ] Viewport: 375px (iPhone SE) — all content fits, no horizontal scroll
- [ ] Viewport: 768px (iPad) — layout adjusts, sidebar collapses if present
- [ ] Viewport: 1024px (iPad Pro) — desktop layout applies
- [ ] Forms: inputs 100% width on mobile, stack vertically
- [ ] Tables: convert to cards or horizontal scroll on mobile
- [ ] Grids: adjust columns (3 → 2 → 1)
- [ ] Navigation: hamburger menu on mobile (if sidebar present)
- [ ] Modals: fit within viewport with padding
- [ ] Buttons: min height 44px for touch targets
- [ ] Typography: readable font sizes, no overflow

---

## SEO & Meta Tag Verification (Public Pages Only)

- [ ] `/` — redirect, no meta tags needed
- [ ] `/terms` — title, description meta tags (static)
- [ ] `/privacy` — title, description meta tags (static)
- [ ] `/discover/events` — title, description (dynamic or static)
- [ ] `/discover/courses` — title, description (dynamic or static)
- [ ] `/events/:id/details` — title (event title), description (short_description), og:image (event image)
- [ ] `/courses/:slug` — title (course title), description (short_description), og:image
- [ ] `/programs` — title, description
- [ ] `/programs/:slug` — title (program title), description, og:image
- [ ] `/verify` — title "Verify Certificate"
- [ ] `/badges/verify/:code` — title "Verify Badge"

---

**End of Exhaustive Test Inventory**

This inventory covers all public, auth, and learner surfaces. Each page lists visible elements, preconditions, and exhaustive interaction tests. State matrices capture complex combinations. API interactions are documented. Error handling and mobile responsiveness are flagged for comprehensive testing. Use this as a reference to build automated and manual test cases.