# Organizer · Instructor — Test Inventory

---

## PART 1: ORGANIZER SURFACES

### Dashboard — `/dashboard` (OrganizerDashboard.tsx)

**Purpose:** High-level overview of organizer's events and courses, quick-access stats.

**Preconditions:**
- Role: Organizer (checked via `isOrganizer` flag in getRoleFlags)
- Data state: ≥0 events and courses (renders even empty)

**Visible elements / regions:**
- Page header: "Organizer Dashboard" or "Admin Dashboard" (if isAdmin)
- Description: "Manage your professional events, track attendance, and issue certificates."
- Primary action button: "+ Create New Event" → links to `/events/create`
- OnboardingChecklist component (if not dismissed)
- Stat cards grid (1 col mobile, 2 cols tablet, 4 cols desktop):
  - Total Events (icon: Calendar)
  - Active Events (Published or Live) (icon: Activity)
  - Total Registrations (across all events) (icon: Users)
  - Certificates Issued (icon: Award)
- If `isInstructor` (instructor-scoped organizers):
  - Second stat grid (4 cols max):
    - Total Courses (icon: BookOpen)
    - Published Courses (icon: CheckCircle2)
    - Course Enrollments (all time) (icon: Users)
    - Course Completions (icon: GraduationCap)
- "Recent Events" section (if `isInstructor` is false, hidden; if true, shown):
  - Table header: Course | Status | Enrollments | Completions
  - "View All" link in header → `/courses/manage`
  - Empty state: "No courses yet" with conditional message (admin: "Create your first"; non-admin: "You have not been assigned to any courses yet")

**Interactions to test:**
1. "+ Create New Event" button → navigates to `/events/create` (EventCreatePage)
2. Stat cards → verify numbers match API call results (getEvents, getOwnedCourses)
3. Recent Events table rows → click course name → navigates to `/courses/manage/:courseSlug`
4. OnboardingChecklist → click items to mark complete, verify persistent state (localStorage or API)

**Edge cases & state variants:**
- Empty state: 0 events → stats show 0, Recent Events hidden
- Loading state: page shows animate-pulse "Loading dashboard..."
- isInstructor=false (pure organizer): courses section hidden
- isInstructor=true && isAdmin=true: both Events and Courses tabs shown, "Admin Dashboard" header
- Failed API call (getEvents catch): shows "Failed to fetch events" in console, displays empty list

**State transitions triggered:**
- Page load → getEvents() call + (if isInstructor) getOwnedCourses() call
- Stat aggregation: events.filter(status='published'|'live'), reduce registration_count, certificate_count

---

### Event Creation/Edit — `/events/create` & `/events/:uuid/edit` (EventCreatePage → EventWizard)

**Purpose:** Create new events or edit existing ones via multi-step wizard.

**Preconditions:**
- Route: `/events/create` → new event (initialData=null); `/events/:uuid/edit` → edit mode (fetches event via getEvent(uuid))
- Role: Organizer with `create_events` feature flag (enforced by ProtectedRoute requiredFeature)
- For edit mode: event must exist and belong to authenticated user

**Visible elements / regions (EventWizard):**

**Step 1: Basic Info (StepBasicInfo)**
- Section title: "Basic Information"
- Form fields:
  - Title (text input, required)
  - Category (dropdown/select)
  - Format (radio/buttons): online | in-person | hybrid
  - CPD enabled toggle (switch)
  - If CPD enabled: CPD Credit Value (number) + CPD Credit Type (dropdown: points/hours/credits)
  - Certificates enabled toggle (switch)
  - Badges enabled toggle (switch)
  - Video enabled toggle (switch)
  - Multi-session enabled toggle (switch) → reveals session management UI later
  - Free toggle (switch) → if unchecked, shows Price field (currency + amount)
- Validation on blur: Title non-empty, price ≥0 if paid

**Step 2: Schedule (StepSchedule)**
- Section title: "Schedule & Sessions"
- Form fields:
  - Start date + time (datetime picker)
  - Duration (hours:minutes picker or numeric hours/mins)
  - Registration open date + time (datetime picker)
  - Registration close date + time (datetime picker, can be after event start if set to not auto-close)
  - Waitlist enabled toggle (switch)
  - Capacity (number input, nullable for unlimited)
  - Minimum attendance (either % or absolute minutes input, with computed conversion)
  - If multi-session enabled:
    - Sessions list table: Name | Start | Duration | Actions (Edit/Delete)
    - "+ Add Session" button → modal dialog with Name, Start datetime, Duration
- Validation: Start before end, registration open before close, capacity ≥ registrations if editing

**Step 3: Details (StepDetails)**
- Section title: "Event Details"
- Form fields:
  - Description (rich-text editor using ReactQuill)
  - Location (address autocomplete, shown only for in-person/hybrid)
  - Cover image upload (drag-drop or file picker):
    - Validates file type (JPEG, PNG, GIF, WebP)
    - Validates size (max 5MB)
    - Shows preview; "Change" and "Remove" buttons
    - Stores _imageFile for later upload
- Validation: Description required (non-empty after stripping HTML tags)

**Step 4: Settings (StepSettings)**
- Section title: "Event Settings"
- Form fields:
  - Speakers picker (multi-select dropdown, populates from /api/speakers)
  - Custom fields builder:
    - Existing fields list with Edit/Delete actions
    - "+ Add Field" button → modal with Name, Type (text/email/phone/dropdown/checkbox), Required toggle
  - Accreditation note (text area)
  - Feedback form builder (if certificates_enabled):
    - Existing feedback fields list
    - "+ Add Question" button → modal with Question, Type (rating/text/nps), Required toggle
- Validation: Custom fields and feedback fields have unique names

**Step 5: Review (StepReview)**
- Displays read-only summary of all fields from previous steps
- Card per section: Basic Info | Schedule | Details | Settings
- "Create Event" or "Update Event" button (depending on mode) → calls createEvent or updateEvent
- On success: toast success, navigate to `/events`
- On error: toast error with message from response

**Interactions to test:**
1. **Basic Info:**
   - Toggle CPD → reveals/hides CPD Credit Value and Type fields
   - Toggle Certificates → affects later review
   - Toggle Video → affects event management tabs
   - Toggle Free → reveals/hides Price and Currency fields
   - Toggle Multi-Session → reveals session table in Schedule step
   - Select Category → filters available accreditations
2. **Schedule:**
   - Drag datetime pickers → updates start/duration
   - Capacity input → numeric validation (positive int or empty)
   - Add Session (if multi-session) → modal opens; fill Name/DateTime/Duration → clicks "Add" → appends to sessions list
   - Edit Session → populates modal; save → updates in list
   - Delete Session → removes from list (with confirmation)
3. **Details:**
   - Type in Description → rich-text formatting available (bold, italic, lists, links)
   - Upload image → file input opens; select file → preview renders; "Change" → re-opens picker; "Remove" → clears preview and sets _isImageRemoved=true
   - Location autocomplete → start typing → dropdown shows suggestions → click one → fills field
4. **Settings:**
   - Speakers picker → click dropdown → lists all speakers from API → select multiple → chips/tags show selection
   - Custom fields "+ Add Field" → modal; fill Name and Type; toggle Required → clicks "Add" → appends field to list
   - Edit custom field → modal pre-populated; change and save → updates list
   - Delete custom field → removes from list
   - Same flow for Feedback form fields
   - Accreditation note → free-text input
5. **Review:**
   - Read-only display of all wizard steps
   - Click "Create Event" or "Update Event" → submission handler:
     - Cleans description (strips empty HTML tags)
     - Calls createEvent or updateEvent with form data (minus _imageFile, _sessions, etc.)
     - If new event and image selected: uploadEventImage(uuid, _imageFile) after create
     - If multi-session: createEventSession / updateEventSession / deleteEventSession calls for each session
     - On any error: toast error, stay on review step
     - On success: toast success, navigate to `/events`

**Edge cases & state variants:**
- **Empty state (create):** All fields empty; "Create Event" disabled until required fields filled
- **Edit mode:** Event data pre-populated from API; form shows "Update Event" button instead of "Create Event"
- **Form validation errors:** Next button disabled until current step valid (isStepValid checks required fields)
- **File upload errors:** Image upload fails → toast warning "Event saved but image upload failed"
- **Session save errors (multi-session):** Some sessions fail to save → toast warning "Event saved but some sessions could not be saved"
- **Currency:** price field uses currency code from event.currency or org default
- **Custom fields with conditional visibility:** Not visible in the UI yet (feature planned)

**State transitions triggered:**
- Wizard steps: currentStep progresses 0→1→2→3→4 (or back with prev button)
- Form data: updateFormData merges into formData state (context-based)
- Image upload: _imageFile stored, then uploadEventImage called asynchronously
- Event status post-create: defaults to draft (publishEvent must be called separately)

---

### Event Management — `/organizer/events/:uuid/manage` (EventManagement.tsx)

**Purpose:** Manage event registrations, attendance, certificates, feedback, and lifecycle (publish/unpublish/cancel).

**Preconditions:**
- Route param: uuid (event UUID)
- Role: Organizer with `create_events` feature
- Event state: must exist and belong to authenticated user
- Data fetched: event details, registrations/attendees, feedback

**Visible elements / regions:**

**Page Header:**
- Title: event.title
- Description: "Manage registrations and attendance for your {format} event."
- Status badge (shows event.status: draft | published | live | completed)
- Date/time info: "Scheduled for [date]"
- Capacity: "{x} / {capacity}" or "Unlimited"
- Action buttons (conditional on status):
  - If status='draft' && not started: "Publish Event" (bg-success)
  - If status='published' && not started: "Convert to Draft" (variant-outline, warning text)
  - If not started: "Edit Event" (variant-outline) → links to `/events/:uuid/edit`
  - "View Public Page" → links to `/events/:slug/details`
  - "Delete" (variant-outline, destructive text) → AlertDialog confirm

**Stats Cards (4-col grid, 1 col mobile):**
- Total Registrations: count of non-cancelled registrations
- Checked In: count where attended=true; % of registered shown
- Certificates Issued: count where certificate_uuid is set; % of checked-in shown
- Feedback: average rating (if feedback exists); count of responses

**Tabs:**

### Tab: Registrations
- **Elements:**
  - Search bar: "Search attendees..." (filters by full_name or email)
  - Filter button (placeholder, not yet functional)
  - Export CSV button → downloads CSV with columns: Full Name, Email, Status, Payment Status, Attended, Registered At
  - Table headers: Attendee (name + email + avatar) | Ticket Type | Status | Actions
  - Table rows per attendee:
    - Avatar (UI-avatars.com fallback)
    - Name and email
    - Ticket type (status enum: confirmed | waitlisted | cancelled | pending)
    - Badge (payment_status logic):
      - Refunded → primary/10 bg
      - Payment Failed → destructive/10 bg
      - Payment Pending → warning bg
      - Paid → success bg
      - Cancelled → destructive/10 bg
      - Confirmed → success bg
    - Action menu (MoreVertical dropdown):
      - Send Email → mailto: link
      - Edit Attendance → opens EditAttendanceDialog
      - View Responses (if event.custom_fields.length > 0) → CustomFieldResponsesDialog
      - Refund Registration (if payment_status='paid') → openActionDialog('refund')
      - Cancel Registration (if not refunded/cancelled) → openActionDialog('cancel')
- **Interactions:**
  1. Search term → filters attendees on full_name or email (case-insensitive, live)
  2. Export CSV → calls handleExportCsv → creates Blob, downloads as `{event.title}-attendees.csv`
  3. "Edit Attendance" menu item → opens EditAttendanceDialog (modal) with attendee details; can modify attended/check_in_time
  4. "View Responses" → CustomFieldResponsesDialog shows custom field answers for attendee
  5. "Send Email" → window.location.href = `mailto:${email}`
  6. "Refund Registration" → ActionDialog (modal) with reason textarea; submit → refundEventRegistration(uuid, registration_uuid, reason)
  7. "Cancel Registration" → ActionDialog (modal) with reason; submit → cancelEventRegistration(uuid, registration_uuid, reason)
  8. Row hover → bg-muted/50 transition
- **State transitions:**
  - Check-in: attended toggled → optimistic update → API call (checkInAttendee) → server response updates check_in_time
  - Refund/Cancel: actionLoading state during API call; on error, toast error with server message; on success, fetchRegistrations() re-fetches list
- **Edge cases:**
  - Empty state: 0 registrations → "No registrations yet"
  - Search no matches → table empty
  - Long attendee name → truncated in cell
  - Refund failed: error message from response.data.error.message displayed in toast

### Tab: Registration Form
- **Elements:**
  - RegistrationFormBuilder component (CRUD for custom fields)
  - Table: Field Name | Type | Required | Actions (Edit/Delete)
  - "+ Add Field" button → FormDialog (modal)
- **Interactions:**
  1. Click field row → edit modal pre-populates
  2. "+ Add Field" → modal with empty fields; fill Name, select Type (text/email/checkbox/dropdown), toggle Required; submit → POST /api/events/{uuid}/custom-fields/
  3. Edit field → modal; modify; submit → PATCH
  4. Delete field → confirm dialog; submit → DELETE

### Tab: Attendance
- **Elements:**
  - AttendanceReconciliation component (visual, check-in list with filters)
  - Table: Name | Email | Checked In (toggle) | Check-in Time | Actions
  - Bulk action row (if rows selected): "Mark as Checked In" / "Mark as Absent"
- **Interactions:**
  1. Toggle Checked In checkbox → handleCheckIn → optimistic update → API call
  2. Edit check-in time → manual time picker, submit → API update

### Tab: Certificates (conditional: if event.certificates_enabled)
- **Elements:**
  - Table: Attendee | Status | Issued Date | Certificate Code | Actions
  - Stat card: X certificates issued out of Y eligible
  - "+ Issue All Eligible Certificates" button (large CTA)
  - "Issue Certificate" button per row (if not yet issued)
  - "Reissue Certificate" option (if already issued)
  - Revoke action → modal with reason textarea
- **Interactions:**
  1. "+ Issue All Eligible Certificates" → handleIssueAllCertificates() → issueCertificates(uuid, {issue_all_eligible:true}) → toast result with counts
  2. "Issue Certificate" (row action) → handleIssueCertificate(registration_uuid) → toast result
  3. "Reissue Certificate" → handleReissueCertificate(registration_uuid) → toast result
  4. "Revoke" → revokeDialog (modal, reason textarea); submit → revokeCertificate(uuid, certificate_uuid, reason)
- **State transitions:**
  - Issue result summary (CertificateIssueResult):
    - All issued, 0 skipped → "Issued X certificate(s)"
    - Some issued, some skipped → "Issued X, skipped Y" + list of skip reasons
    - 0 issued, >0 skipped → error toast "No certificates issued — Y skipped" + reasons

### Tab: Badges (conditional: if event.badges_enabled)
- **Elements:** Similar to Certificates; badge-specific fields
- **Interactions:** Issue/revoke badge flows

### Tab: Feedback Form
- **Elements:**
  - FeedbackFormBuilder component
  - CRUD for feedback template fields (Rating, Text, NPS)
- **Interactions:**
  1. "+ Add Question" → modal; select Type (rating/text/nps); submit → creates field
  2. Edit question → modal pre-populate; update
  3. Delete question → confirm; delete

### Tab: Feedback (Results)
- **Elements:**
  - FeedbackSummary card: avg rating (if rating field present), feedback count, rating distribution (bar chart)
  - FeedbackCard list (one per response):
    - Respondent name (if captured)
    - Per-field response (rating as stars, text as quote, NPS as score)
    - Response timestamp
  - Filter by response status (submitted / draft)
  - Search by respondent name
- **Interactions:**
  1. Load feedback on tab open → getEventFeedback(uuid) → renders FeedbackCard per response
  2. Click response → expands to show full answers
  3. Drill-in capability (if FeedbackCard is clickable → detail page, not yet visible in code)
- **State transitions:**
  - fetchFeedback() called on mount; feedbackLoading state managed

**Action States & Validations:**
- **Publish Event:** hasStarted check; if true, button disabled
- **Unpublish Event:** hasStarted check; if true, button disabled (can't convert to draft after started)
- **Delete Event:** AlertDialog confirm; if deleting, setDeleting=true, delete call, on success navigate to /events
- **Check-in:** Optimistic update then server sync; if error, revert state
- **Refund/Cancel:** actionLoading during submission; actionReason textarea required (trim check)

**Edge cases & state variants:**
- **No attendees:** All tabs show empty state
- **Event live (started):** Edit button disabled; Publish/Unpublish buttons hidden
- **No feedback yet:** "No feedback responses yet"
- **Custom fields empty:** "View Responses" menu item hidden on attendee row
- **Multi-session event:** Sessions tab (not shown in EventManagement code review, but routes in App.tsx suggest it exists)
- **Large attendee list:** Pagination not visible in current code; assumes all loaded (potential performance issue)

**State transitions triggered:**
- Page load:
  - getEvent(uuid) → setEvent
  - getEventRegistrations(uuid) → setAttendees
  - getEventFeedback(uuid) → setFeedback (on Feedback tab open)
- Publish: publishEvent(uuid) → event.status='published' → toast success
- Unpublish: unpublishEvent(uuid) → event.status='draft' → toast success
- Delete: deleteEvent(uuid) → navigate('/events') → toast success
- Check-in: checkInAttendee(uuid, attendee_uuid, newAttended) → updates attendee.attended, check_in_time
- Refund: refundEventRegistration(uuid, attendee_uuid, reason) → fetchRegistrations()
- Certificate issue: issueCertificates(uuid, {registration_uuids: [...]}) → summarizeIssueResult() → fetchRegistrations()

---

### Events List — `/events` (EventsPage.tsx)

**Purpose:** Browse and filter organizer's events.

**Preconditions:**
- Role: Any authenticated user (learner, instructor, organizer)
- Filters vary by role

**Visible elements / regions:**
- Page header: "Events"
- Search bar (filters by title, description)
- Filter buttons: status (all/draft/published/live/completed), date range
- Card grid (1 col mobile, 2-3 cols desktop) showing event summaries:
  - Event image (featured_image_url or placeholder)
  - Title, category badge
  - Format badge (online/in-person/hybrid), CPD badge (if enabled)
  - Date and time
  - Registration count / capacity
  - Action buttons per event (View, Edit if owner, Manage if organizer)

---

### Courses Management — `/courses/manage` (OrgCoursesPage.tsx)

**Purpose:** Browse and manage instructor/organizer-owned courses.

**Preconditions:**
- Role: Instructor or Organizer with `create_courses` feature
- canCreateCourses = isAdmin || isInstructor

**Visible elements / regions:**
- Page header: "Manage Courses" (if canCreateCourses) or "Assigned Courses"
- Search bar: filters by course title
- Tabs: All | Draft | Published | Archived
- Course cards/rows (table or card layout):
  - Course title (clickable → `/courses/manage/:courseSlug`)
  - Status badge (published/draft/archived)
  - Format badge (self-paced/live/hybrid)
  - Enrollment count, completion count, progress %
  - Action menu (MoreVertical): Edit, View Public Page, Archive/Unarchive, Delete
- "+ Create Course" button (if canCreateCourses) → `/courses/manage/new`

**Interactions:**
1. Search term → filters courses (case-insensitive title match)
2. Tab click → filters by status
3. Course row click → navigates to CourseManagementPage
4. "+ Create Course" → `/courses/manage/new` (CreateCoursePage)
5. Edit action → `/courses/manage/:courseSlug`?tab=overview
6. Delete action → confirm → deleteCourse(uuid) → toast success, remove from list
7. Archive action → archiveCourse(uuid) → status changes to archived

**Edge cases:**
- Empty state: 0 courses → "No courses yet" with "Create your first course" CTA
- All filters inactive (no courses match) → "No courses found"
- Search + filter combination → "No courses match your search"

---

### Course Management — `/courses/manage/:courseSlug` (CourseManagementPage.tsx)

**Purpose:** Multi-tab interface for managing course content, enrollments, and settings.

**Preconditions:**
- Route param: courseSlug
- Role: Course owner (isStaffOnly check: user_role !== 'instructor' for full access; 'instructor' = staff-only tabs)
- Data: fetched via getCourseBySlug(courseSlug, {owned:true})

**Tab Visibility Logic:**
```
isStaffOnly = course.user_role === 'instructor'
showSessions = course.format === 'hybrid' || course.format === 'live'
showCurriculum = course.format !== 'live'

Available tabs for owner: Overview | Sessions (if hybrid/live) | Curriculum (if not live) | Enrollments | Announcements | Discussion | Submissions | Certificates | Settings
Available tabs for instructor staff: [skip Overview] | Sessions (if hybrid/live) | Curriculum (if not live) | Enrollments | Announcements | Discussion | Submissions | Certificates | [skip Settings]
```

### Tab: Overview (Owner Only)
- **Elements:**
  - Course summary: title, slug, description, category
  - Key metrics: total enrollments, active enrollments, completion rate
  - Course settings quick-view: format, pricing, enrollment period
  - Link to public course page
  - "Edit Settings" button → SettingsTab
- **Interactions:**
  1. Edit field → modal or inline edit (specific implementation varies)
  2. "Edit Settings" → switches to Settings tab

### Tab: Curriculum (Owner Only, if course.format !== 'live')
- **Elements:**
  - Module tree (expandable hierarchy):
    - Modules list (module can contain lessons, assignments, quizzes, etc.)
    - Drag-reorder modules and content within
    - Per-module actions: Add content, Duplicate, Delete, Settings
  - Content editor modal (for each content block):
    - Type selector: text/video/quiz/document/external-link/lesson/assignment
    - Type-specific fields:
      - **Text:** Rich-text editor (ReactQuill)
      - **Video:** Video URL input, duration, transcription
      - **Quiz:** Question builder (multiple choice, short answer, essay), grading rules
      - **Document:** File upload (PDF, DOC, etc.)
      - **External Link:** URL input, open in new tab toggle
      - **Lesson:** Title, description, estimated time
      - **Assignment:** Instructions, rubric builder, submission deadline, grading mode (manual/auto)
    - Prerequisites (select prior modules/lessons to complete first)
    - Release rules (drip content by date/completion of prior modules)
    - Required toggle
  - Actions per item: Edit (opens content editor modal), Duplicate, Delete (with confirmation)
- **Interactions:**
  1. Drag module → reorders module list
  2. "+ Add Content" button → selector dialog (Type) → opens content editor for that type
  3. Edit content → modal pre-populates with current data; save → PATCH /courses/{uuid}/content/{content_uuid}/
  4. Duplicate content → creates new content block with same settings, appends to module
  5. Delete content → confirm → DELETE request; remove from list
  6. Drag content within module → reorder
  7. Drag content across modules → move (if drag-drop supports cross-module)
  8. Toggle prerequisite → updates release rules
  9. Toggle required → marks content as required for progression
- **State transitions:**
  - Load curriculum on tab open → getCurriculumTree(courseUuid) → renders module tree
  - Save content → optimistic update (add/edit) → API call → refetch tree on error
  - Order change → drag updates local state → POST /courses/{uuid}/reorder-content/ with new order

### Tab: Enrollments
- **Elements:**
  - Search bar: filters by user name or email
  - Status filter buttons: All | Active | Completed | Pending | Dropped
  - Stats cards (2-4 cols): Total Enrollments | Active | Completed | Dropped
  - Table headers: Student | Status | Enrolled | Progress | Actions
  - Table rows per enrollment:
    - Student name and email (clickable → user detail page)
    - Status badge (active/completed/dropped/pending)
    - Enrolled date (formatted)
    - Progress bar (% complete)
    - Payment badge (if applicable): Paid | Refunded | Failed
    - Action menu: Refund | Mark Complete | Cancel | Certificate (if eligible)
- **Interactions:**
  1. Search term → filters enrollments (case-insensitive, name or email)
  2. Status filter → shows only matching status
  3. Refund action → RefundDialog (modal):
     - Refund reason (textarea, required)
     - Refund amount (pre-filled with full amount; can edit for partial)
     - Submit → refundEnrollment(courseUuid, enrollmentUuid, {reason, amount_cents})
     - On success: enrollment.payment updated → toast "Refund issued"
     - On error: toast error with code and message
  4. "Mark Complete" → marks enrollment.status='completed', issue certificate if available
  5. "Cancel" → confirms → enrollment.status='dropped'
  6. "Issue Certificate" → issueCertificates(courseUuid, {enrollment_uuids: [...]})
  7. Bulk actions (if rows selected): "Refund All" / "Issue All Certificates"
- **State transitions:**
  - Load enrollments on tab open → getCourseEnrollments(courseUuid) → renders table
  - Filter change → re-filter local enrollments state
  - Refund → optimistic update → API call → refetch on error
  - Certificate issue → certificate_issued flag updated

### Tab: Announcements
- **Elements:**
  - List of announcements (title, publish status, scheduled date if applicable)
  - Per-announcement: Edit | Delete | Pin/Unpin | Publish/Unpublish | Schedule actions
  - "+ Create Announcement" button → AnnouncementDialog (modal)
  - Announcement card: title, content preview, author, created date, status badge (draft/published/scheduled)
- **Interactions:**
  1. "+ Create Announcement" → modal with:
     - Title input
     - Content (rich-text editor)
     - Publish immediately toggle vs. Schedule (datetime picker)
     - Submit → createAnnouncement(courseUuid, {title, content, scheduled_at, published})
  2. Edit announcement → modal pre-populated; submit → updateAnnouncement
  3. Delete announcement → confirm → deleteAnnouncement(courseUuid, announcementUuid)
  4. Publish/Unpublish → toggle published flag
  5. Pin announcement → pins to top of list
  6. Schedule announcement → calendar picker; future publish date
- **State transitions:**
  - Load announcements on tab open → getAnnouncements(courseUuid) → renders list
  - Create/edit → optimistic update → API call → refetch on error

### Tab: Discussion (Q&A / Forum)
- **Elements:**
  - Thread list: Topic | Starter | Replies | Last Activity | Status (Open/Locked/Resolved)
  - Per-thread: View (opens detail), Edit (if own post), Lock, Hide, Mark Resolved
  - Search/filter: by topic, status, date range
  - "+ Start Discussion" button → DiscussionDialog (create thread modal)
  - Thread detail view (when expanded/clicked):
    - Original post (title, body, author, timestamp, vote count)
    - Replies list (nested, with vote/flag/reply-to-reply actions)
    - "Reply" button → reply compose box (rich-text editor)
- **Interactions:**
  1. "+ Start Discussion" → modal with title, body (rich-text); submit → createThread(courseUuid, {title, body})
  2. Click thread title → expands/opens thread detail
  3. In thread detail: reply compose → enter text; submit → createReply(threadUuid, {body}) → reply appends to list
  4. Flag reply as inappropriate → creates flag record; instructor sees count
  5. Instructor "Hide" action → reply visibility='hidden'
  6. Instructor "Lock" thread → prevents further replies
  7. Instructor "Mark Resolved" → threads marked as resolved for easy filtering
  8. Delete own reply (if author) → confirm → deleteReply(replyUuid)
- **State transitions:**
  - Load threads on tab open → getDiscussions(courseUuid) → renders thread list
  - New reply posted → optimistic append to replies list → API call → refetch on error
  - Thread locked/hidden → local state updated; UI reflects (lock icon, grayed out)

### Tab: Submissions (Assignment Grading Queue)
- **Elements:**
  - Search bar: filters by assignment or student name
  - Status filter: All | Submitted | In Review | Needs Revision | Graded | Approved
  - Submissions table:
    - Assignment | Student | Status | Submitted | Score | Last Updated | Actions
  - Per-submission row: Grade (button) | Approve | Return for Revision | View
  - Grade submission modal:
    - Assignment title (read-only)
    - Student name (read-only)
    - Submission content (code block, text, image, etc.)
    - Rubric (if defined for assignment):
      - Rubric criteria rows: Criterion | Level (Excellent/Good/Fair/Poor) | Points
      - Total score calculation
    - Score input (number)
    - Feedback textarea (instructor notes to student)
    - Action dropdown: Grade | Return for Revision | Approve
    - Submit → gradeCourseSubmission(courseUuid, submissionUuid, {score, feedback, action})
- **Interactions:**
  1. Search term → filters by assignment_title or student_name
  2. Status filter → shows only matching status
  3. "Grade" button on row → opens GradeDialog (modal)
  4. In modal:
     - View submission content (read-only)
     - View rubric (if exists)
     - Enter score
     - Enter feedback
     - Select action (grade/return/approve)
     - Submit → gradeCourseSubmission API call
  5. On success: submission status updated; modal closes; table re-fetches
  6. "Return for Revision" action → status='needs_revision' → student notified
  7. "Approve" action → status='approved' → may trigger certificate issuance
- **State transitions:**
  - Load submissions on tab open → getCourseSubmissions(courseUuid) → renders table
  - Filter change → re-filter local state
  - Grade submission → optimistic update → API call → refetch on error
  - Rubric evaluation → score auto-calculated based on levels selected

### Tab: Sessions (if format=hybrid or live)
- **Elements:**
  - Sessions list: Date | Time | Attendance | Recording | Actions
  - Per-session: Edit | Start Session | End Session | View Attendance | Download Recording
  - "+ Add Session" button (for hybrid courses with flexible scheduling)
  - Session edit modal:
    - Title
    - Start datetime
    - Duration
    - Platform (Zoom, Meet, custom)
    - Attendee list (filtered to show who attended)
  - Attendance reconciliation per session (mark present/absent)
- **Interactions:**
  1. "Add Session" → modal; fill details; submit → createSession(courseUuid, {title, start_at, duration, platform})
  2. "Edit Session" → modal pre-populate; save → updateSession
  3. "Start Session" → marks session.status='in_progress'; recording API call (if video enabled)
  4. "End Session" → marks session.status='completed'; ends recording
  5. "View Attendance" → shows attendee list with check-in marks; instructor can manually mark attended
  6. "Download Recording" → if available, allows download or stores in video vault
- **State transitions:**
  - Load sessions on tab open → getCourseSessions(courseUuid) → renders list
  - Start session → video room creation trigger (backend handles)
  - End session → recording save initiated
  - Attendance update → optimistic → API call

### Tab: Certificates
- **Elements:**
  - Certificate issued log (read-only):
    - Student | Date Issued | Template | Status (Active/Revoked) | Actions
  - Stats: X certificates issued, Y pending (not yet met criteria)
  - "+ Issue Certificate Manually" button
  - Manual issue modal:
    - Select recipient (dropdown or search, filters enrolled students)
    - Select certificate template
    - Issue date (defaulted to today)
    - Submit → issueCertificates(courseUuid, {enrollment_uuids: [...]})
  - "Bulk Issue All Eligible" button
  - Revoke action per row: confirm → revokeCertificate(courseUuid, certificateUuid, reason)
- **Interactions:**
  1. Manual issue modal: select student; select template; submit → certificate created
  2. Bulk issue: "Issue All Eligible" → API issues to all enrollments meeting criteria (completion, attendance, etc.)
  3. Revoke: confirm reason; submit → revokeCertificate API call; toast success/error
- **State transitions:**
  - Load certificates on tab open → getCertificates(courseUuid) → renders table
  - Issue certificate → optimistic append → API call → refetch on error
  - Revoke → optimistic update (status='revoked') → API call

### Tab: Settings (Owner Only)
- **Elements:**
  - Course metadata section:
    - Title (text input)
    - Slug (auto-generated from title, editable)
    - Description (rich-text editor)
    - Category (dropdown)
    - Featured image (upload)
  - Enrollment rules section:
    - Enrollment period (start/end dates, can be open-ended)
    - Capacity (number or unlimited)
    - Enrollment require approval toggle
    - Price (free vs. paid, currency, amount)
    - Prerequisites (select other courses that must be completed first)
  - Access control section:
    - Visibility (public/private/unlisted)
    - Require login toggle
  - Grading section:
    - Passing score (%)
    - Grading scale (A-F, 1-5, custom)
  - Certificate settings (if certificates enabled):
    - Certificate template (dropdown)
    - Auto-issue on completion toggle
  - Actions:
    - "Save Changes" button (primary)
    - "Archive Course" button (secondary, destructive color) → confirm → archiveCourse(courseUuid)
    - "Delete Course" button (destructive) → confirm → deleteCourse(courseUuid) → navigate('/courses/manage')
- **Interactions:**
  1. Edit any field → updateCourse(courseUuid, {field: newValue})
  2. Slug edit → auto-validates uniqueness (if changed)
  3. Featured image upload → uploadCourseImage(courseUuid, file)
  4. Featured image remove → deleteCourseImage(courseUuid)
  5. Save changes → PATCH /courses/{uuid}/ → toast success "Course updated"; onCourseUpdated callback fired
  6. Archive course → confirm → archiveCourse(courseUuid) → course.status='archived' → toast "Course archived"
  7. Delete course → confirm → deleteCourse(courseUuid) → navigate('/courses/manage') → toast "Course deleted"
- **State transitions:**
  - Load settings on tab open (if Settings tab accessed) → course object already loaded in CourseManagementPage
  - Update field → optimistic update → API call (PATCH) → refetch on error
  - Archive/delete → navigate away or refresh page state

**Edge cases for CourseManagementPage:**
- **Instructor staff view:** Overview and Settings tabs hidden; all other tabs shown (if applicable to format)
- **Live course:** Curriculum tab hidden (live courses have no modules, only sessions)
- **No enrollments:** Enrollments tab shows "No enrollments yet"
- **No submissions:** Submissions tab shows "No submissions to grade"
- **Course archived:** All tabs read-only; Settings shows "Course is archived" notice

---

### Course Creation — `/courses/manage/new` (CreateCoursePage.tsx)

**Purpose:** Multi-step form to create new courses.

**Preconditions:**
- Role: Instructor or Organizer with `create_courses` feature
- Feature flag: `create_courses` (enforced by ProtectedRoute)

**Form Structure (details from codebase not fully visible; inferred from CourseManagementPage patterns):**
- Step 1: Basic Info
  - Title, slug, description, category, format (self-paced/live/hybrid)
  - Instructor name (auto-populated from user), add co-instructors
- Step 2: Details
  - Enrollment rules, pricing, capacity, prerequisites
  - Enrollment open/close dates
  - Passing score, grading scale
- Step 3: Curriculum (if self-paced)
  - Module structure, add content
- Step 4: Settings
  - Visibility, certificate template, auto-issue
- Step 5: Review and Create

**Interactions:** Similar to EventWizard flow (next/prev navigation, form validation, submit handler creates course)

**State transitions:**
- Form submission → createCourse(courseData) → on success, navigate to `/courses/manage/{slug}`

---

### Programs Management — `/programs/manage` (OrgProgramsPage.tsx)

**Purpose:** Browse and manage course bundles (programs).

**Preconditions:**
- Role: Organizer with `create_courses` feature (or equivalent)

**Visible elements / regions:**
- Page header: "Manage Programs" with description "Bundle courses and offer them at a discount."
- "+ Create Program" button → `/programs/manage/new`
- Program cards (grid or table):
  - Program title (clickable → `/programs/manage/{slug}`)
  - Status badge (published/draft/archived)
  - Course count, enrollment count
  - Price (formatted currency)
  - Action menu per card: Edit Settings, View Public Page, Archive/Publish, Delete

**Interactions:**
1. "+ Create Program" → `/programs/manage/new` (CreateProgramPage)
2. Click program card → `/programs/manage/:programSlug` (ProgramManagementPage)
3. Edit/Delete/Archive actions similar to courses

---

### Program Management — `/programs/manage/:programSlug` (ProgramManagementPage.tsx)

**Purpose:** Multi-tab interface for managing program composition and settings.

**Preconditions:**
- Route param: programSlug
- Role: Program owner (fetches via getProgramBySlug with owned=true)
- Data: fetches program and available owned courses

**Tabs:**

### Tab: Overview (Owner)
- Program metadata summary
- Course list (included in program)
- Enrollment metrics
- Link to public program page

### Tab: Courses (Curriculum)
- **Elements:**
  - Course list (added to program):
    - Course name | Order | Actions (Edit order, Remove)
  - "+ Add Course" button → course selector (multi-select from owned courses)
  - Drag-reorder courses
- **Interactions:**
  1. "+ Add Course" → modal with course list; select course; submit → addProgramCourse(programUuid, {course_uuid})
  2. Drag course → reorder within program → POST /programs/{uuid}/reorder-courses/
  3. "Remove Course" → removeProgramCourse(programUuid, programCourseUuid)
  4. "Edit" course order/position → editProgramCourse (if position can be set independently)

### Tab: Enrollments
- **Elements:**
  - Enrollment list: Student | Enrollment Date | Progress | Status | Actions
  - Filter by status (enrolled/completed/cancelled)
  - Search by student name
- **Interactions:**
  1. Search/filter similar to Course Enrollments tab
  2. Refund, cancel, or issue certificate for program enrollment (cascades to contained courses)

### Tab: Announcements
- Similar to Course Announcements

### Tab: Discussion
- Similar to Course Discussion

### Tab: Analytics (optional)
- Program-level metrics:
  - Total enrollments (trend over time)
  - Completion rate
  - Course popularity (which courses in program most popular)
  - Revenue (if paid program)

### Tab: Settings (Owner)
- **Elements:**
  - Program metadata: title, slug, description, category
  - Pricing: free vs. paid, currency, amount
  - Enrollment rules: period (open/close), capacity
  - Visibility (public/private)
  - Certificate template (if enabled)
  - Archive/Delete buttons
- **Interactions:**
  1. Edit field → updateProgram(programUuid, {field: value})
  2. Publish program → publishProgram(programUuid) → requires ≥1 course added, else toast error
  3. Archive program → archiveProgram(programUuid) → confirm "Existing learners keep access"
  4. Delete program → deleteProgram(programUuid) → confirm "Courses inside will not be deleted"

**Edge cases:**
- **Cannot publish:** 0 courses in program → toast error "Add at least one course first"
- **Archived program:** Tabs show read-only; enrollments can't be added; existing enrollments can still access
- **All courses archived:** Program may be archived too (business logic TBD)

---

### Contacts — `/organizer/contacts` (ContactsPage.tsx)

**Purpose:** Manage contact database for outreach, segmentation, and attendee tracking.

**Preconditions:**
- Role: Organizer with `manage_contacts` feature
- ProtectedRoute enforced

**Visible elements / regions:**
- Page header: "Contacts"
- Action buttons:
  - "Import" (Upload CSV) → ImportDialog
  - "Export" (Download CSV) → exportContacts() API call
  - "+ Add Contact" → ContactFormDialog (create new)
- Search bar: filters by name or email
- Tag filter (disabled/commented out; feature pending re-enable)
- Contact table:
  - Headers: Name | Email | Organization | Phone | Added | Status | Actions
  - Row per contact:
    - Name (text), email (mailto link)
    - Organization (if captured)
    - Phone (if captured)
    - Added date (formatted)
    - Status badge (subscribed/unsubscribed/bounced)
    - Action menu: Edit (ContactFormDialog), Send Email (mailto), View Attendance (link to registrations), Delete (confirm)

**Interactions:**
1. "+ Add Contact" → ContactFormDialog (modal):
   - Name (text input, required)
   - Email (text input, required, validates format)
   - Organization (text input)
   - Phone (text input)
   - Custom tags (if enabled) → multi-select
   - Submit → createContact(payload) → toast success; refetch contacts
2. "Import" button → ImportDialog (modal):
   - File upload (CSV)
   - Validate columns (Name, Email, Organization, Phone, etc.)
   - On file select → parse CSV → preview rows
   - Submit → importContacts(csvData) → background job queued; toast "Import in progress"
   - Results → toast with count imported/skipped
3. "Export" button → exportContacts() API call → downloads CSV file with all contacts
4. Search term → filters contacts (live filter, case-insensitive)
5. Edit contact row → ContactFormDialog pre-populated; save → updateContact(uuid, payload)
6. Delete contact → confirm → deleteContact(uuid) → toast success; refetch
7. "Send Email" action → window.location.href = `mailto:${email}`
8. "View Attendance" → link to `/registrations?contact=${uuid}` (shows attendee's event history)
9. Tag filter (when re-enabled) → filter contacts by selected tags

**State transitions:**
- Load contacts on mount → getContacts() → renders table
- Import complete → fetchContacts() re-fetches list with new imports
- Create/update/delete → optimistic update or refetch on error
- Tag filter change (future) → re-filter contacts state

**Edge cases:**
- **Empty contacts:** "No contacts yet. Add one to get started."
- **Search no matches:** "No contacts match your search"
- **CSV import with errors:** "X imported, Y skipped with errors"
- **Bounced email:** Status badge shows "Bounced"; import/export may mark as "unsubscribed"
- **Large contact list (1000+):** Pagination not visible in code; potential performance issue

---

### Reports — `/organizer/reports` (ReportsPage.tsx)

**Purpose:** Analytics and reporting across events, courses, and programs.

**Preconditions:**
- Role: Any organizer or instructor (tab visibility gated by role)
- Tab visibility:
  - Events tab: visible if isOrganizer
  - Courses tab: visible if isInstructor
  - Programs tab: visible if isInstructor

**Visible elements / regions:**

**Global Controls (above tabs):**
- Period selector (dropdown):
  - Last 7 days
  - Last 30 days
  - Last 3 months
  - This Year
- "Export Report" button (placeholder, not yet implemented in visible code)

**Tab: Events (if isOrganizer)**
- **Stat cards (4-col grid):**
  - Total Revenue (currency-formatted)
  - Total Attendees (count)
  - Events Hosted (count)
  - Avg. Satisfaction (rating out of 5 or "N/A")
- **Registration Trends card:**
  - Bar chart (horizontal or vertical): date on x-axis, registration count on y-axis
  - Trend over selected period
  - BarList component (custom, shows row per date with bar visualization)
- **Ticket Sales by Status card:**
  - KeyValueList component: breakdown of ticket sales
  - Rows: Paid | Free | Refunded | Failed (with counts)
- **Recent Transactions table:**
  - Transaction date | Event | Registrant | Amount | Status
  - Sortable; filterable
- **Event performance table:**
  - Event name | Date | Registrations | Capacity | Attendance % | Revenue

**Tab: Courses (if isInstructor)**
- **Stat cards (similar structure):**
  - Total Enrollments
  - Course Completions (count)
  - Avg. Completion Time
  - Avg. Score (if grading enabled)
- **Enrollment trends chart**
- **Course performance table:**
  - Course name | Enrollments | Completion % | Avg. Score | Revenue (if paid)
- **Learning outcomes metrics:**
  - Most completed courses
  - Courses with low completion (at-risk)
  - Time-to-completion distribution

**Tab: Programs (if isInstructor)**
- **Stat cards:**
  - Total Program Enrollments
  - Program Completion Rate
  - Avg. Program Revenue
  - Engagement Score
- **Program performance table:**
  - Program name | Enrollments | Completion % | Revenue
- **Course popularity within programs:**
  - Which courses in programs have highest completion

**Interactions:**
1. Period selector → changes period parameter → re-fetches reports data (getReports, getCourseReports, getProgramReports) → charts re-render
2. Chart drill-down (if clickable) → navigates to event/course detail
3. Export Report → (future) generates PDF or CSV export of visible metrics

**State transitions:**
- Tab open/period change → setLoading(true) → API call (getReports/getCourseReports/getProgramReports) → parse response → render metrics and charts

**Edge cases:**
- **No data for period:** Charts show "No registrations yet" or similar empty message
- **Loading:** Stat cards show "--" placeholder; charts show skeleton loaders
- **Error:** Toast error "Failed to load event reports"
- **Seasonal data:** Charts may show zero or sparse data for certain periods

---

### Video Management — `/organizer/video` (VideoManagement.tsx)

**Purpose:** Manage video conferencing rooms and recordings.

**Preconditions:**
- Role: Organizer with `manage_video` feature
- ProtectedRoute enforced

**Visible elements / regions:**
- Page header: "Video Rooms"
- Provider status card:
  - Icon (CheckCircle if configured, XCircle if not)
  - Status: "Connected" or "Not configured"
  - Provider badge: "Zoom" / "Google Meet" / etc.
- Active rooms card:
  - Badge showing count of active/scheduled rooms
  - Room rows: Room Name | Status badge | Started/Created date | Actions
  - Status: active | scheduled | ended | error
  - Actions per room (if active): End Session | View Room | Download Recording
  - Empty state: "No video rooms yet. Create an event with video enabled to get started."
- Past rooms card:
  - Room rows (ended or errored)
  - Same columns as active rooms
  - View recording, etc.

**Interactions:**
1. "End Session" action (if room active) → endVideoSession(roomUuid) → room.status='ended' → toast success
2. "View Room" action → Opens video session in new window/tab (join URL)
3. "Download Recording" action (if available) → Downloads video file or redirects to vault

**State transitions:**
- Load video data on mount → getVideoStatus() + getVideoRooms() → renders cards
- Room status changes (if real-time polling) → UI updates to reflect live/ended state

**Edge cases:**
- **Video provider not configured:** Status card shows "Not configured" (red X icon); no rooms appear
- **No rooms:** Both cards show "No video rooms yet"
- **Room in error state:** Status badge shows "error" (red)
- **Recording not yet available:** "Download Recording" button disabled; message "Recording processing"

---

### Accreditations (Organizer View) — `/manage/accreditations` (OrganizerAccreditationsPage.tsx)

**Purpose:** Track all certificates and badges issued by the organization.

**Preconditions:**
- Role: Organizer (no explicit feature flag in code, but implied)

**Visible elements / regions:**
- Page header: "Accreditations"
- Search bar: filters by template name, source title, recipient name, or short code
- Filter dropdowns:
  - Kind: All | Certificate | Badge
  - Source: All | Event | Course
- Stat cards (compact):
  - Total Issued: count of all active accreditations
  - Certificates: count of certificates
  - Badges: count of badges
  - Revoked: count of revoked accreditations
- Accreditations table:
  - Headers: Template | Source | Recipient | Code | Status | Issued Date | Actions
  - Row per accreditation:
    - Template name (certificate or badge name)
    - Source title (event or course name)
    - Recipient name (learner name)
    - Short code (verification code)
    - Status badge: active (green) | revoked (red)
    - Issued date (formatted)
    - Action menu: View (verification page), Revoke (if active), Re-issue (if revoked)

**Interactions:**
1. Search term → filters by template_name, source_title, recipient_name, short_code (case-insensitive)
2. Kind filter (Certificate/Badge) → shows only matching kind
3. Source filter (Event/Course) → shows only matching source
4. "View" action → navigates to verification page (public route `/verify/{code}`)
5. "Revoke" action (if active) → RevokeDialog (modal) with reason textarea; submit → revokeCertificate/revokeBadge API call
6. "Re-issue" action (if revoked) → re-issues accreditation (same recipient, new code)

**State transitions:**
- Load accreditations on mount → getOrganizationCertificates() + getIssuedBadgesByMe() → merge and sort by issued_at desc → renders table
- Revoke action → accreditation.status='revoked' → optimistic update → API call → refetch on error

**Edge cases:**
- **No accreditations:** "No accreditations yet"
- **Search/filter no matches:** "No accreditations match your filters"
- **Revoked accreditation:** Status badge shows "revoked" (grayed out); "View" still works (shows revocation reason)

---

### Promo Codes — `/organizer/promo-codes` (PromoCodesPage.tsx)

**Purpose:** Create and manage discount codes for events.

**Preconditions:**
- Role: Organizer with `create_events` feature
- ProtectedRoute enforced

**Visible elements / regions:**
- Page header: "Promo Codes"
- "+ Create Promo Code" button → FormDialog
- Search bar: filters by code or description
- Status filter: All | Active | Inactive
- Promo code table (DataTable component):
  - Headers: Code | Description | Type | Value | Valid | Uses | Status | Actions
  - Row per promo code:
    - Code (all-caps code string)
    - Description (if provided)
    - Type badge: Percentage | Fixed Amount
    - Value (e.g., "10%" or "$5.00")
    - Valid date range (from–to)
    - Uses: X / {max_uses} (if unlimited, shows "∞")
    - Status toggle: Active (switch) | Inactive
    - Action menu: Edit (FormDialog), View Usage (UsageDialog), Deactivate (toggle), Delete (confirm)

**Interactions:**
1. "+ Create Promo Code" → FormDialog (modal):
   - Code input (required, unique; all-caps)
   - Description textarea (optional)
   - Discount Type radio: Percentage | Fixed Amount
   - Discount Value input (required, number)
   - Valid From date picker (optional)
   - Valid Until date picker (optional)
   - Max Uses input (optional; if empty = unlimited)
   - First-time User Only toggle
   - Scope picker (optional):
     - Empty = applies to all organizer's events
     - Select events (multi-select; lazy-loads event list on modal open)
   - Submit → createPromoCode(payload) → toast success
2. Edit promo code row → FormDialog pre-populated; save → updatePromoCode
3. "View Usage" action → UsageDialog (modal):
   - Table: Date | User | Event | Discount Amount | Status
   - Shows all transactions where promo code was applied
4. Status toggle (on/off) → togglePromoCodeActive(uuid, active) → optimistic update
5. Delete promo code → confirm → deletePromoCode(uuid) → toast success
6. Search term → filters by code or description
7. Status filter → shows only active or inactive codes

**State transitions:**
- Load promo codes on mount → getPromoCodes() → renders table
- Create/edit → optimistic update → API call → refetch on error
- Toggle active → optimistic → API call
- Lazy-load events (on form open) → getEvents() → populates scope selector

**Edge cases:**
- **No promo codes:** "No promo codes yet. Create one to offer discounts."
- **Code already exists:** Form validation error "Code already in use"
- **Scope empty vs. specific events:**
  - Empty scope (all events): discount applies to registrations across all events organizer owns
  - Specific events selected: discount only applies to those event registrations
- **Usage tracking:** Not all uses may be visible (if usage data is async/eventually consistent)
- **Expired code:** Valid Until date in past; code may still show but with "Expired" badge

---

### Speakers — `/organizer/speakers` (SpeakersPage.tsx)

**Purpose:** Manage speaker profiles and assign to events.

**Preconditions:**
- Role: Organizer with `create_events` feature
- ProtectedRoute enforced

**Visible elements / regions:**
- Page header: "Speakers"
- "+ Add Speaker" button → FormDialog
- Search bar: filters by name or email
- Speakers table (DataTable component):
  - Headers: Speaker | Bio | Qualifications | Email | LinkedIn | Status | Actions
  - Row per speaker:
    - Avatar + Name (clickable → detail page or expand)
    - Bio (short preview, truncated)
    - Qualifications (short preview)
    - Email (mailto link)
    - LinkedIn link (if provided)
    - Status badge: Active | Inactive
    - Action menu: Edit (FormDialog), View Assignments (link to events where assigned), Deactivate (toggle), Delete (confirm)

**Interactions:**
1. "+ Add Speaker" → FormDialog (modal):
   - Name input (required)
   - Bio textarea (optional, rich-text editor or plain text)
   - Qualifications textarea (optional)
   - Email input (optional, validates format)
   - LinkedIn URL input (optional)
   - Submit → createSpeaker(payload) → toast success; refetch speakers
2. Edit speaker row → FormDialog pre-populate; save → updateSpeaker(uuid, payload)
3. "View Assignments" action → navigates to list of events where speaker is assigned
4. Deactivate speaker → toggleSpeakerActive(uuid, active) → speaker marked inactive (still assignable to past events, not suggested for new)
5. Delete speaker → confirm → deleteSpeaker(uuid) → toast success
6. Search term → filters by name or email

**State transitions:**
- Load speakers on mount → getSpeakers() → renders table
- Create/edit → optimistic update → API call → refetch on error
- Deactivate → optimistic → API call

**Edge cases:**
- **No speakers:** "No speakers yet. Add one to assign to events."
- **Speaker inactive but assigned to events:** Can still view assignments; marked as inactive for new event creation
- **Deleted speaker:** Cannot be accessed; past event assignments may show "Speaker Deleted"

---

## PART 2: INSTRUCTOR SURFACES

### Dashboard — `/dashboard` (InstructorDashboard.tsx)

**Purpose:** Instructor-scoped overview of courses managed and taught.

**Preconditions:**
- Role: Instructor (checked via `isInstructor` flag in getRoleFlags)
- User has no `isOrganizer` flag (pure instructor)
- Data: fetches via getOwnedCourses()

**Visible elements / regions:**
- Page header: "Instructor Dashboard"
- Description: "Manage your courses, grade submissions, and track enrollments."
- Action buttons:
  - "Manage Courses" (variant-outline) → `/courses/manage`
  - "+ Create Course" (primary) → `/courses/manage/new`
- Stat cards (4-col grid):
  - Total Courses (icon: BookOpen)
  - Published (icon: CheckCircle)
  - Enrollments (icon: Users)
  - Completions (icon: Award)
- Recent Courses section (table):
  - Course name (clickable → `/courses/manage/:courseSlug`)
  - Status badge (published/draft/archived)
  - Enrollments count
  - Completions count
  - Empty state: "No courses yet" with conditional message (admin: create CTA; non-admin: "contact your administrator")

**Interactions:**
1. "Manage Courses" button → `/courses/manage`
2. "+ Create Course" button → `/courses/manage/new`
3. Course row click → `/courses/manage/:courseSlug`
4. Search/sort (if visible) → filters recent courses

**Edge cases:**
- **No courses:** Empty state shown
- **Instructor with no creation rights:** "+" button hidden; only "Manage Courses" shown; empty state message reads "contact your administrator"
- **isAdmin flag set:** Stats may include summary metrics (TBD based on role definitions)

---

### Course Management Tabs (Instructor Staff Perspective)

When an instructor (non-owner) accesses `/courses/manage/:courseSlug`, the tab rendering logic in CourseManagementPage checks:
```
isStaffOnly = course.user_role === 'instructor'
```

**Available tabs for instructor staff:**
- ~~Overview~~ (HIDDEN)
- Sessions (if hybrid or live)
- Curriculum (if not live)
- Enrollments (VISIBLE: staff can view/manage)
- Announcements (VISIBLE: staff can post/read)
- Discussion (VISIBLE: staff can moderate)
- Submissions (VISIBLE: staff can grade)
- Certificates (VISIBLE: staff can issue)
- ~~Settings~~ (HIDDEN)

**Restricted Interactions (Instructor Staff Only):**

### Tab: Enrollments (Instructor View)
- Can view enrollments
- Can **grade** submissions → Submissions tab (primary grading interface)
- Can **issue certificates** (if course has certificate)
- Can **see refund history** (read-only; refund initiated by owner)
- **Cannot:** Delete enrollments, modify payment settings, archive course

### Tab: Curriculum (Instructor View)
- Can **view** module/content structure
- Can **edit content** if has grading role (depends on permission model):
  - May be able to add quiz questions, update instructions
  - May NOT be able to add/remove modules or change prerequisites (content owner-only)
- **Cannot:** Reorder modules, change overall structure

### Tab: Announcements (Instructor View)
- Can **create** announcements (visible to students)
- Can **edit own announcements** (not others')
- Can **view** all announcements
- Can **pin important announcements** (if permission granted)
- **Cannot:** Publish/unpublish announcements on behalf of owner (only own)

### Tab: Discussion (Instructor View)
- Can **view** all discussion threads and replies
- Can **reply** to threads (as staff)
- Can **moderate** discussion:
  - Hide inappropriate replies
  - Lock threads (prevent further replies)
  - Mark threads as resolved
  - Flag/unflag responses
- Can **delete own replies** (not others')
- **Cannot:** Delete threads (owner-only), archive discussion

### Tab: Submissions (Instructor View)
- Can **grade** all student submissions
- Can **view** all submissions in queue (filtered by status)
- Can **provide feedback** on assignments
- Can **assign scores** (0 to max points)
- Can **return for revision** (change status to needs_revision, notify student)
- Can **approve** submission (mark status='approved', potentially trigger certificate)
- **Cannot:** Delete submissions, change grading rubric

### Tab: Certificates (Instructor View)
- Can **view** issued certificates (read-only log)
- Can **manually issue** certificates to eligible students
- Can **re-issue** revoked certificates (to same student or different)
- Can **revoke** certificates (with reason)
- Can **bulk issue** to all eligible
- **Cannot:** Modify certificate template (owner-only)

---

## PART 3: SHARED INTERACTIONS & API ENDPOINTS

### Common API Calls (Frontend `/api/` folder):

**Events:**
- `GET /events/` → getEvents()
- `POST /events/` → createEvent()
- `GET /events/{uuid}/` → getEvent()
- `PATCH /events/{uuid}/` → updateEvent()
- `POST /events/{uuid}/publish/` → publishEvent()
- `POST /events/{uuid}/unpublish/` → unpublishEvent()
- `DELETE /events/{uuid}/` → deleteEvent()
- `GET /events/{uuid}/registrations/` → getEventRegistrations()
- `PATCH /events/{uuid}/registrations/{reg_uuid}/check-in/` → checkInAttendee()
- `POST /events/{uuid}/registrations/{reg_uuid}/cancel/` → cancelEventRegistration()
- `POST /events/{uuid}/registrations/{reg_uuid}/refund/` → refundEventRegistration()
- `POST /events/{uuid}/certificates/issue/` → issueCertificates()
- `DELETE /events/{uuid}/certificates/{cert_uuid}/` → revokeCertificate()
- `POST /events/{uuid}/certificates/{cert_uuid}/reissue/` → reissueCertificate()
- `GET /events/{uuid}/feedback/` → getEventFeedback()
- `POST /events/{uuid}/sessions/` → createEventSession()
- `PATCH /events/{uuid}/sessions/{session_uuid}/` → updateEventSession()
- `DELETE /events/{uuid}/sessions/{session_uuid}/` → deleteEventSession()
- `GET /events/{uuid}/sessions/` → getEventSessions()
- `POST /events/{uuid}/image/` → uploadEventImage()
- `DELETE /events/{uuid}/image/` → deleteEventImage()

**Courses:**
- `GET /courses/?owned=true` → getOwnedCourses()
- `GET /courses/{slug}/?owned=true` → getCourseBySlug()
- `POST /courses/` → createCourse()
- `PATCH /courses/{uuid}/` → updateCourse()
- `DELETE /courses/{uuid}/` → deleteCourse()
- `GET /courses/{uuid}/enrollments/` → getCourseEnrollments()
- `POST /courses/{uuid}/refund-enrollment/` → refundEnrollment()
- `GET /courses/{uuid}/submissions/` → getCourseSubmissions()
- `POST /courses/{uuid}/submissions/{submission_uuid}/grade/` → gradeCourseSubmission()
- `GET /courses/{uuid}/announcements/` → getAnnouncements()
- `POST /courses/{uuid}/announcements/` → createAnnouncement()
- `PATCH /courses/{uuid}/announcements/{announcement_uuid}/` → updateAnnouncement()
- `DELETE /courses/{uuid}/announcements/{announcement_uuid}/` → deleteAnnouncement()
- `GET /courses/{uuid}/discussions/` → getDiscussions()
- `POST /courses/{uuid}/discussions/` → createDiscussion()
- `GET /courses/{uuid}/certificates/` → getCertificates()
- `POST /courses/{uuid}/certificates/issue/` → issueCertificates()
- `POST /courses/{uuid}/sessions/` → createSession()
- `GET /courses/{uuid}/sessions/` → getCourseSessions()

**Programs:**
- `GET /programs/?owned=true` → getPrograms()
- `GET /programs/{slug}/?owned=true` → getProgramBySlug()
- `POST /programs/` → createProgram()
- `PATCH /programs/{uuid}/` → updateProgram()
- `POST /programs/{uuid}/publish/` → publishProgram()
- `POST /programs/{uuid}/archive/` → archiveProgram()
- `DELETE /programs/{uuid}/` → deleteProgram()
- `POST /programs/{uuid}/courses/` → addProgramCourse()
- `DELETE /programs/{uuid}/courses/{program_course_uuid}/` → removeProgramCourse()
- `GET /programs/{uuid}/enrollments/` → getProgramEnrollments()

**Contacts:**
- `GET /contacts/` → getContacts()
- `POST /contacts/` → createContact()
- `PATCH /contacts/{uuid}/` → updateContact()
- `DELETE /contacts/{uuid}/` → deleteContact()
- `POST /contacts/import/` → importContacts()
- `POST /contacts/export/` → exportContacts()

**Promo Codes:**
- `GET /promo-codes/` → getPromoCodes()
- `POST /promo-codes/` → createPromoCode()
- `PATCH /promo-codes/{uuid}/` → updatePromoCode()
- `DELETE /promo-codes/{uuid}/` → deletePromoCode()
- `POST /promo-codes/{uuid}/toggle/` → togglePromoCodeActive()
- `GET /promo-codes/{uuid}/usages/` → getPromoCodeUsages()

**Speakers:**
- `GET /speakers/` → getSpeakers()
- `POST /speakers/` → createSpeaker()
- `PATCH /speakers/{uuid}/` → updateSpeaker()
- `DELETE /speakers/{uuid}/` → deleteSpeaker()

**Video:**
- `GET /video/status/` → getVideoStatus()
- `GET /video/rooms/` → getVideoRooms()

**Accreditations:**
- `GET /certificates/organization/` → getOrganizationCertificates()
- `GET /badges/issued/` → getIssuedBadgesByMe()

**Reports:**
- `GET /reports/events/?period={period}` → getReports()
- `GET /reports/courses/?period={period}` → getCourseReports()
- `GET /reports/programs/?period={period}` → getProgramReports()

---

## PART 4: FORM VALIDATION & ERROR HANDLING

**Common Validation Patterns:**
- Required fields: non-empty check on blur and submit
- Email: regex validation (RFC 5322 simplified)
- URLs: URL constructor validation or regex
- Numbers: parseFloat / parseInt with NaN check
- Dates: Date constructor, comparison (start < end)
- Textarea/description: allow empty or trim whitespace
- File uploads: type whitelist (image/* for images), size limit (5MB typical)
- Rich-text editors: strip HTML tags for empty check

**Error Handling:**
- API errors: toast.error(response.data?.error?.message || response.data?.detail || generic message)
- Network errors: console.error logged; generic "Failed to load" toast
- Optimistic updates: revert state on error, show error toast
- Form submission: disable button, show loading state during API call
- Image upload failures: non-blocking warning toast; event saved but image not uploaded

---

## PART 5: EDGE CASES & PERMISSION GATING

**Permission Model (inferred from code):**
- `create_events`: can create, edit, publish events; manage registrations
- `create_courses`: can create courses and programs
- `manage_contacts`: can access contacts page (CRUD)
- `manage_video`: can access video management page
- `manage_users` (admin-only): can access user management

**Role Hierarchy (inferred):**
- Admin (all features)
- Organizer (create_events, manage_contacts, manage_video, create_courses, promo-codes, speakers)
- Instructor (create_courses, limited to owned courses; can grade, manage enrollments)
- Attendee (no create features; view/register for events/courses)

**Visibility Rules:**
- Pages gated by ProtectedRoute with requiredFeature check
- Dashboard variant rendered based on isOrganizer / isInstructor / default (attendee)
- Tabs in CourseManagementPage hidden if user_role != 'owner' (Overview, Settings, Curriculum if not applicable)
- ReportsPage tabs visible based on role flags (Events for organizer, Courses/Programs for instructor)

---

## PART 6: PERFORMANCE & STATE MANAGEMENT

**Caching:**
- Dashboard: fetches on mount (no polling)
- EventManagement: refetches registrations/feedback on tab change
- Reports: re-fetches when period selector changes
- Lazy-loading: event list for promo code scope loaded on form open

**Optimistic Updates:**
- Check-in toggle: immediate UI update → server sync → revert on error
- Certificate issue: append to list → API call → refetch on error
- Refund/cancel: status change → API call → refetch registrations

**Pagination:**
- Not visible in most tables (assumes all data loaded)
- Contacts page may benefit from pagination (large lists not addressed)
- Reports charts may show limited data (e.g., last 10 transactions)

**Loading States:**
- Page-level: animate-pulse "Loading..." placeholder
- Component-level: Skeleton loaders, LoadingButton, disabled actions
- Tab content: Loader2 spinner (lucide-react icon) centered

---

## TESTING PRIORITIES

### High-Priority Test Coverage:
1. **Event Lifecycle:** Create → Publish → Live → Complete (status transitions)
2. **Check-in Flow:** Attendee toggle, optimistic update, error handling
3. **Certificate Issuance:** Bulk issue, individual issue, revocation
4. **Form Validation:** Required fields, date logic, image upload
5. **Permission Gating:** Role-based tab visibility, feature flags
6. **Multi-step Wizards:** Step navigation, back/next, form state persistence
7. **CSV Export/Import:** Data integrity, error messages
8. **Refund Flow:** Payment status updates, reason tracking
9. **Search & Filter:** Case-insensitivity, multi-filter combination
10. **Error Boundaries:** API failures, network errors, toast display

### Medium-Priority Test Coverage:
- Announcement CRUD (create, edit, delete, publish/schedule)
- Discussion moderation (lock, hide, resolve, flag)
- Submission grading workflow (score, feedback, action)
- Program course ordering (drag-reorder, add/remove)
- Speaker assignment to events
- Promo code usage tracking
- Video room status transitions
- Accreditation search and filtering

### Low-Priority Test Coverage:
- Accessibility (WCAG compliance, screen reader)
- Performance (large data sets, slow networks)
- Internationalization (if multilingual future planned)
- Dark mode (if theme toggle future planned)
- Mobile responsiveness (covered implicitly via tailwind classes)

---

**End of Test Inventory**