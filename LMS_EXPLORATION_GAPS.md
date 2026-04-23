# LMS Exploration — Gaps & Readiness Notes

**Branch:** `demo-ready`
**Captured:** 2026-04-20
**Anchor commits:** `990804e` (Discussion Board) on top of `b2e942f` (Phase 1–5 browser validation)

This doc captures the state of the admin-creates → learner-consumes loop for the LMS, what's wired end-to-end, what's stubbed, and what is demo-critical vs. deliberately out of scope.

## How this was produced

Static analysis of the Django backend (`backend/src/`) and React frontend (`frontend/src/`). Three initial agent findings were reversed after direct grep verification (flagged inline below). **No browser walkthrough was performed** — every "it works" claim here is a code-wiring claim, not a runtime guarantee. The `## Verification checklist` at the bottom is deliberately unchecked.

---

## 1. Admin Content Creation

### What works (model → API → UI wired end-to-end)

- **Course authoring** — `frontend/src/pages/organizations/courses/CreateCoursePage.tsx` covers title/slug/description (Quill), format (`online` / `live` / `hybrid`), pricing, CPD credits, hybrid completion criteria, certificate & badge templates, auto-issue toggles. Backend forces `DRAFT` on create (`backend/src/learning/views.py:676`); explicit publish action required.
- **Modules & content** — `CurriculumTab.tsx` (~990 lines) creates modules and adds content across six types: `text`, `video`, `document`, `quiz`, `lesson`, `external`. File uploads flow through `MultiPartParser` → `learning/modules/` via `common/storage.py` (GCS if configured, local fallback).
- **Quiz authoring** — `QuizBuilder` stores questions + `passing_score` in `ModuleContent.content_data` JSON. Verified wired to the learner side (§2).
- **Assignments** — full CRUD with rubric (raw JSON textarea), submission types (`text` / `url` / `file` / `mixed`), max attempts, resubmission toggle.
- **Live sessions** — `SessionsTab` + `SessionScheduler` for hybrid/live courses. Backend `CourseSessionViewSet` exposes publish, unpublish, sync_attendance, match_participant, start/complete/cancel/reschedule actions.
- **Programs** — UI exists: `CreateProgramPage.tsx`, `ProgramManagementPage.tsx`, `OrgProgramsPage.tsx`. *(Correction: initial exploration claimed programs were backend-only.)*
- **Course-management tabs** — Overview, Settings, Enrollments, Sessions, Discussion, Announcements, Certificates, Submissions (grading) — all present.
- **RBAC** — `@roles('instructor', 'admin')` + `can_manage()` + `has_perm("learning.can_create_course")` gate all write paths. Frontend `ProtectedRoute` with `requiredFeature="create_courses"` hides admin routes from learners.

### What's stubbed

- **Drag-reorder** — `GripVertical` icons in `CurriculumTab.tsx` have no handlers. Order field exists on models but no PATCH `order` endpoint exposed.
- **Release scheduling** — `EventModule.release_type` (`SCHEDULED`, `DAYS_AFTER_REG`, `PREREQUISITE`) and `EventModule.prerequisite_module` FK are modeled and serialized, but there is no UI editor. Prereq gating works at read time; admins cannot configure it.
- **Video upload** — no transcoding, HLS, or direct upload to a video service. The `video`/`lesson` content editors collect an external URL (YouTube, Vimeo, direct MP4) even though `ModuleContent.file` accepts binary.
- **Content-type coverage** — `lesson` and `quiz` have first-class editors. `external`, `document`, and raw `text` paths are thinner.
- **Rubric templates** — `Assignment.rubric` is a raw JSON textarea; no template library.

---

## 2. Learner Content Consumption

### What works

- **Enrollment** — `CourseEnrollment` with states `PENDING` / `ACTIVE` / `COMPLETED` / `DROPPED` / `EXPIRED`. Free courses auto-enroll; paid go through Stripe (`/enrollments/checkout/` → `/enrollments/confirm-checkout/`).
- **CoursePlayerPage** (`frontend/src/pages/courses/CoursePlayerPage.tsx`, ~1850 lines) — single main learner surface with module navigator, content viewer dispatched by `content_type`, assignment submission UI, announcements panel, discussion panel.
- **Quiz taking — end-to-end.** *(Correction: initial exploration claimed "no quiz-taking logic on frontend".)* `QuizContent` at `CoursePlayerPage.tsx:989` renders questions from `content_data`, collects answers, scores client-side against `passing_score`, and persists via `updateContentProgress` with `{quiz_answers, score, passed}` in `last_position`. Shows "Passed — N%" badge on return.
- **Live session join — wired.** *(Correction: initial exploration claimed "no join/live-room logic".)* `SessionsPanel` imports `JoinButton` from `components/video/JoinButton.tsx` and renders it per session (`SessionsPanel.tsx:180`). CoursePlayerPage embeds `SessionsPanel` for `live` and `hybrid` courses.
- **Progress tracking** — `ContentProgress`, `ModuleProgress`, `CourseSessionAttendance`. `CourseEnrollment.check_completion()` evaluates per-format rules (online = all modules passed; live = attendance %; hybrid = configurable criteria) and on completion auto-issues certificate + badge if enabled.
- **Discussions** — threads + flat replies, pin/lock/hide/flag moderation, @mention member search (`GET /courses/{uuid}/members/search/`), notifications via `learning/discussions_service.py`.
- **Certificates wallet** — `CertificatesList.tsx` and `CertificateDetail.tsx`. Public verify route at `/verify/:code`.
- **Programs (learner side)** — `MyProgramsPage.tsx` and `PublicProgramDetailPage.tsx` exist.

### What's stubbed

- **Video playback progress** — only mark-complete is tracked. No `currentTime` scrubbing, resume-from-here, or watch-time telemetry, even though `ContentProgress.time_spent_minutes` exists.
- **Module unlock UX** — locked modules show a Lock icon but no tooltip or modal explaining *why* they're locked or what must be completed to unlock them.
- **Badges wallet** — `IssuedBadge` is created on completion, but no learner-facing badge wall page exists (unlike certificates).
- **CPD claim flow** — credits are denormalized onto completion; no explicit "claim CPD" action or per-session CPD log surface for learners beyond the `CPDTracking.tsx` totals on the dashboard.
- **Discussion mention rendering** — backend stores mentions and the search endpoint exists; the Quill editor calls search, but rendered-message mention linkification wasn't confirmed in `RichTextEditor.tsx`.

---

## 3. Demo-Critical Gaps, Ranked

| # | Gap | Effort | Why it matters in a demo |
|---|---|---|---|
| 1 | Module unlock explanation (tooltip + "Complete X to unlock") | Low | Clicking a locked module with zero feedback reads as broken. |
| 2 | Video playback resume (persist `currentTime` to `last_position`) | Medium | "Come back to a half-watched lesson" scenario currently restarts at 0:00. |
| 3 | Drag-reorder: either wire it up or remove the `GripVertical` visual cue | Low–medium | The icon promises a feature that doesn't exist. |
| 4 | Release-scheduling editor (prereq module picker, release_type selector) | Medium | Backend gating works; admins cannot configure it. Only a problem if demo asks "how do I sequence modules?" |
| 5 | Badges wallet page | Low–medium | Auto-issued badges are invisible to learners. Only surfaces if badges are mentioned in the demo. |

---

## 4. Out of Scope — Do Not Address Reactively

These are real limitations but clearly infrastructure-tier and should not be taken on in a demo polish pass:

- Video transcoding pipeline / HLS / DASH streaming
- Direct video upload to an ingest service
- Rubric template library
- Bulk course import / clone
- Real-time video watch telemetry analytics

---

## 5. Verification Checklist

Everything above is static analysis. Before calling the branch demo-ready, run the following in a browser against seeded fixtures:

- [ ] `python manage.py seed` loads without error; fixtures include the sample hybrid course.
- [ ] As admin/instructor, create a hybrid course with 1 module (quiz + lesson) + 1 live session + certificate template, then publish.
- [ ] As a learner, enroll in the published course (free path).
- [ ] Take the quiz; score is persisted and "Passed — N%" badge appears on return.
- [ ] Complete all required modules; course auto-completes and a certificate is issued.
- [ ] Open the certificate in the learner wallet and verify the public `/verify/:code` page.
- [ ] Join the live session from `SessionsPanel` (requires conferencing service running).
- [ ] Post a discussion thread as a learner; reply as an instructor with an @mention; confirm notification.

---

## 6. Critical File Reference

| Layer | File |
|---|---|
| Admin course form | `frontend/src/pages/organizations/courses/CreateCoursePage.tsx` |
| Admin curriculum | `frontend/src/pages/organizations/courses/manage/CurriculumTab.tsx` |
| Learner player | `frontend/src/pages/courses/CoursePlayerPage.tsx` |
| Live sessions (learner) | `frontend/src/components/courses/SessionsPanel.tsx` + `frontend/src/components/video/JoinButton.tsx` |
| Discussion UI | `frontend/src/components/courses/discussion/DiscussionPanel.tsx` |
| LMS models | `backend/src/learning/models.py` |
| LMS views / routes | `backend/src/learning/views.py`, `backend/src/learning/urls.py` |
| RBAC | `backend/src/common/rbac.py`, `backend/src/accounts/management/commands/setup_groups.py` |
| Demo seed | `backend/src/fixtures/05_learning.json` |
