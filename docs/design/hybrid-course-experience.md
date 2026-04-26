# Design: Hybrid Course Experience

## Context

Hybrid courses combine self-paced modules with scheduled live sessions. The data model already supports this (`Course.format=hybrid`, `CourseSession`, `CourseSessionAttendance`, `Course.hybrid_completion_criteria`), but the UI layer was built assuming self-paced courses; sessions have no place in the player navigation, no learner-facing lobby/recording surfaces, and no presentation hooks on aggregate views (My Learning cards, dashboards). A learner viewing the seeded *Procedural Skills Bootcamp* sees 62% progress and "2 of 3 modules complete" — but cannot see Session 1 was attended, that Session 2 is mandatory in 7 days, or how to join when it goes live.

This doc designs the changes properly — reusable primitives, polymorphism over duplication, format-driven presentation. No bolt-ons.

## Audit of what exists today (file-grounded)

### Backend — already correct primitives, missing surfaces

| Concern | Where | Status |
|---|---|---|
| `CourseSession` model with status / scheduling / video config | `backend/src/learning/models.py:1653` | ✅ structurally complete |
| `CourseSessionAttendance` with `is_eligible`, attendance_minutes, manual override | `backend/src/learning/models.py:1795` | ✅ |
| Polymorphic `VideoRoom` (GenericForeignKey to any content_object) | `backend/src/conferencing/models.py:31-33` | ✅ already supports both Event and CourseSession |
| LiveKit webhook → `CourseSessionAttendance` → `enrollment.update_progress()` cascade | `backend/src/conferencing/tasks.py:414` | ✅ symmetric to Event attendance cascade |
| `_progress_snapshot()` returns module + session breakdown for hybrid | `backend/src/learning/models.py:1399-1442` | ✅ already produces `module_units_completed/total` and `session_units_completed/total` |
| API exposes the breakdown to the frontend | `getCourseProgress` response shape | ❌ flattened to a single `progress_percent` |
| Per-session progress / attendance API for learners | none | ❌ |

### Frontend — single-track sidebar, no session routes

| Concern | Where | Status |
|---|---|---|
| Course player sidebar | `frontend/src/pages/courses/CoursePlayerPage.tsx:619-660` | ❌ iterates `modules.map()` only; sessions excluded |
| `SessionsPanel` exists | `frontend/src/components/courses/SessionsPanel.tsx` | ⚠ only renders in the empty-state branch (line 922-927); auto-select hides it |
| Event lobby with countdown / Join window / attendance | `frontend/src/pages/events/EventLobbyPage.tsx` | ✅ pattern to follow |
| Event recording playback | `frontend/src/pages/events/EventRecordingPage.tsx` | ✅ pattern to follow |
| Format badge on My Learning cards | `frontend/src/pages/registrations/MyRegistrationsPage.tsx:347+` | ❌ not visualised |
| Progress breakdown for hybrid courses | nowhere | ❌ |

## Design principles

1. **Polymorphism over duplication.** A "live session" is a primitive. Both `events.Event` (single-session events) / `events.EventSession` (multi-session) and `learning.CourseSession` are realisations. Surfaces (lobby, recording, attendance card) consume a `LiveSession` shape; backends remain separate models.
2. **Single source of truth for derived state.** Status ("scheduled" / "live" / "completed" / "cancelled") and time-window logic ("Join active iff now ∈ [starts_at − 15 min, ends_at]") live in one helper, used by every renderer.
3. **Format-driven presentation.** `course.format ∈ {online, live, hybrid}` is the discriminator. Components ask "given this format, what do I render?" through a small set of helpers, not scattered conditionals.
4. **Backend exposes structure; frontend renders.** The backend already computes the module/session split inside `_progress_snapshot` — surface it in the API rather than recomputing on the client.
5. **Reuse the existing primitives.** `VideoRoom`, `deriveProgressDisplay`, the LiveKit webhook pipeline, the dialog/skeleton/EmptyState components — all already wired. New code composes; it doesn't duplicate.

## Architecture decisions

### A. Live-session UI primitive (new)

A learner-side `LiveSession` shape (TypeScript interface) collapses the relevant fields exposed by both `EventSession` and `CourseSession`:

```ts
interface LiveSession {
    uuid: string;
    title: string;
    description?: string;
    starts_at: string;
    ends_at: string;             // computed: starts_at + duration_minutes
    duration_minutes: number;
    timezone: string;
    is_mandatory: boolean;
    minimum_attendance_percent: number;
    status: 'scheduled' | 'live' | 'completed' | 'cancelled';
    actual_start_at?: string;
    actual_end_at?: string;
    cpd_credits: number;
    // Learner-context fields populated on hydrated reads
    attendance?: { is_eligible: boolean; attendance_minutes: number; };
    recording?: { uuid: string; is_published: boolean; storage_url?: string; };
    join_url?: string;           // present iff video room exists + within window
    is_within_join_window: boolean;
    next_action: 'view_recording' | 'join_now' | 'add_to_calendar' | 'mark_attended_manually' | null;
}
```

Two **shared components** under `frontend/src/components/live/`:

- `LiveSessionRow` — compact sidebar row (status pill, countdown, click-through). Used by the course player sidebar (gap 1) and any future event-multi-session sidebar.
- `LiveSessionLobby` — full-page lobby experience. Used by both `EventLobbyPage` (refactor) and the new `CourseSessionLobbyPage` (gap 2).

A pure helper module `frontend/src/lib/liveSession.ts` exports:

- `deriveLiveSessionStatus(session, now)` → discrete state + countdown text
- `isWithinJoinWindow(session, now)` → boolean (15-min lead time, ends at `actual_end_at` if set else `starts_at + duration_minutes`)
- `nextAction(session, attendance)` → string

This is the same pattern `frontend/src/lib/progress.ts:deriveProgressDisplay` follows (single helper, 4 callers). No conditional sprawl.

### B. Backend — expose progress breakdown

Extend `getCourseProgress` response (`backend/src/learning/views.py:CourseViewSet.progress`):

```python
data = {
    ...,
    "enrollment": {
        ...,
        "progress_percent": int,
        "module_progress": {
            "units_completed": int,
            "units_total": int,
            "modules_completed": int,
            "modules_total": int,
        },
        "session_progress": {  # only for live/hybrid
            "units_completed": int,
            "units_total": int,
            "sessions_attended": int,
            "sessions_total": int,
            "criteria": "both" | "either" | "modules_only" | "sessions_only" | "min_sessions",
        },
    },
    "modules": [...],            # unchanged
    "sessions": [LiveSession],   # NEW — array of LiveSession-shaped rows for live/hybrid
}
```

`_progress_snapshot` already produces all the inputs. The change is in the serializer — no model changes, no new computation.

The `sessions` array is hydrated from `CourseSession` + the learner's `CourseSessionAttendance` rows + the polymorphic `VideoRoom` lookup. Centralised in a new `serializers.LiveSessionSerializer` so the same shape can be reused elsewhere (instructor session listing, enrollment detail, etc.).

### C. Routing — symmetric to events

| Surface | Event route | New Course Session route |
|---|---|---|
| Pre-event lobby (auth) | `/events/:id/lobby` | `/courses/:slug/sessions/:sessionUuid/lobby` |
| Recording playback | `/events/:id/recording` | `/courses/:slug/sessions/:sessionUuid/recording` |
| Guest lobby (no auth) | `/r/:registrationUuid/lobby` | not needed — course sessions require enrollment |

Both course routes go through `frontend/src/lib/auth/ProtectedRoute` and resolve the session via the new API endpoints. No new permission rules — re-use `Course.is_enrolled(user)` (already in the codebase).

### D. Course player IA — two-track sidebar

The player sidebar becomes section-driven, not a flat module list. Two collapsible groups, in this order for hybrid courses:

```
Sidebar
├── Live Sessions (only when course.format ∈ live | hybrid)
│   ├── ✓ Session 1: Live Q&A on Anatomy   (Attended · Apr 21)
│   └── 📅 Session 2: Hands-on Skills Lab  (In 7 days · Required)
├── Modules
│   ├── ✓ Pre-work: Anatomy Review
│   ├── ✓ Equipment & Sterile Setup
│   └── ○ Post-procedure Care
└── Progress
    └── 62% — 4 of 6 content units · 1 of 2 sessions attended
```

For pure online courses the Live Sessions group is omitted; for live courses it's the only section. Same component, format-driven render.

Click on a Live Sessions row routes to the session lobby (or recording if past + published). Click on a Module behaves as today.

### E. Format-aware progress display (frontend)

Extend `frontend/src/lib/progress.ts` (the helper already used in 4 places):

```ts
export interface ProgressBreakdown {
    modules: { completed: number; total: number };
    sessions?: { completed: number; total: number };
    criteria?: HybridCompletionCriteria;
}

export function deriveProgressDisplay(
    enrollment: ProgressLike,
    course?: { format: CourseFormat },
): ProgressDisplay & { breakdown?: ProgressBreakdown } { ... }

export function formatProgressSubtitle(
    enrollment: ProgressLike,
    course: { format: CourseFormat; module_count: number },
): string {
    // online: "3 of 5 modules complete"
    // hybrid (BOTH): "3 of 5 modules · 1 of 2 sessions"
    // hybrid (EITHER): "3 of 5 modules or 1 of 2 sessions"
    // live: "1 of 2 sessions attended"
}
```

`MyRegistrationsPage`, `CoursePlayerPage`, `EnrollmentsTab`, `CertificatesTab` all already call `deriveProgressDisplay` — they each pick up the breakdown for free.

### F. Format badge on cards

A new `FormatBadge` component:

```tsx
<FormatBadge course={enrollment.course} nextSession={enrollment.next_session_at} />
```

Renders:
- `online` → no badge (default; visual default state)
- `live` → small pill: `Live · 2 sessions`
- `hybrid` → small pill: `Hybrid · Next session in 7d`

Reads `course.format` and an optional `enrollment.next_session_at` (new field exposed by the enrollment serializer; null when no upcoming sessions). The `next_session_at` is computed at the API layer from the learner's `CourseSession`s minus any with eligible attendance — keeps client-side logic minimal.

### G. Attendance cascade — already correct, document it

`CourseSessionAttendance.save()` does not auto-trigger `enrollment.update_progress()`, but the LiveKit "leave room" task does (`backend/src/conferencing/tasks.py:414`). For non-LiveKit paths (manual override by instructor, seed, admin tooling), today's setup leaves the cascade missing.

Symmetric to the `ContentProgress → ModuleProgress` signal we added: a new `post_save` signal on `CourseSessionAttendance` that calls `enrollment.update_progress()` whenever `is_eligible` flips. This makes the cascade automatic for **every** writer (LiveKit, manual override, seed, future bulk imports), not just one.

Lives in `backend/src/learning/signals.py` next to the existing cascades. No model or behaviour change for the LiveKit path (idempotent — `update_progress` is a no-op once status=COMPLETED, and recompute from leaf data is safe to repeat).

## Implementation plan (phased — each phase ships independently)

### Phase 1 — Backend API surface (no UI work)

**Files**:
- `backend/src/learning/serializers.py` — add `LiveSessionSerializer`, extend `CourseProgress` shape with `module_progress` / `session_progress` / `sessions` array
- `backend/src/learning/views.py:CourseViewSet.progress` — populate the new fields from `_progress_snapshot()` output (no recomputation)
- `backend/src/learning/views.py:CourseEnrollmentViewSet` — add `next_session_at` virtual field to enrollment list
- `backend/src/learning/signals.py` — new `post_save` on `CourseSessionAttendance` mirroring the `ContentProgress` cascade

**Tests** (`backend/src/learning/tests/test_hybrid_progress_breakdown.py`):
- Hybrid course progress endpoint returns `module_progress` + `session_progress` + sessions list
- Recording the attendance cascade fires `update_progress` once per `is_eligible=True` save
- `next_session_at` is the earliest upcoming session the learner hasn't yet attended-eligibly
- Pure-online courses omit `session_progress` (not just zero — absent)

### Phase 2 — Live session learner routes (lobby + recording)

**Files**:
- `frontend/src/lib/liveSession.ts` — new helper module (status, join-window, next-action)
- `frontend/src/components/live/LiveSessionLobby.tsx` — new shared component (extracted from `EventLobbyPage`'s body; takes a `LiveSession` and a `joinUrl`-resolver)
- `frontend/src/pages/courses/CourseSessionLobbyPage.tsx` — thin wrapper that fetches the session + attendance + video room and renders `LiveSessionLobby`
- `frontend/src/pages/courses/CourseSessionRecordingPage.tsx` — same pattern as `EventRecordingPage`
- `frontend/src/App.tsx` — register the two new routes
- `frontend/src/pages/events/EventLobbyPage.tsx` — refactor body to consume `LiveSessionLobby` (no behaviour change)

**Tests** (Playwright / manual checklist):
- Lobby pre-window shows countdown, no Join button.
- Within 15 min of start: Join button activates, video room provisioned (real LiveKit dev container or stub).
- After end + recording published: lobby auto-redirects to recording page.
- Non-enrollee → 403 → redirect to course public page.

### Phase 3 — Course player two-track sidebar

**Files**:
- `frontend/src/components/courses/PlayerSidebar.tsx` — extract sidebar into its own component (currently inline in `CoursePlayerPage.tsx:619+`); add a `LiveSessionsGroup` section above the modules tree, format-conditional
- `frontend/src/components/live/LiveSessionRow.tsx` — new shared row component (status pill + countdown + click)
- `frontend/src/pages/courses/CoursePlayerPage.tsx` — drop the dead `SessionsPanel` placement (line 922-927); pipe the new sessions data into the sidebar
- Delete `frontend/src/components/courses/SessionsPanel.tsx` once its callers are migrated

**Tests**:
- Hybrid course → sidebar shows "Live Sessions" header + N rows.
- Online course → sidebar shows modules only (no extra group, no spacing artifacts).
- Click on a session row → routes to lobby (future) or recording (past + published).
- Sidebar correctly reflects attendance state (✓ for attended-eligible, 📅 for upcoming, ⏺ for live-now, 🚫 for missed-no-recording).

### Phase 4 — Format-aware presentation across cards

**Files**:
- `frontend/src/lib/progress.ts` — extend `deriveProgressDisplay` + add `formatProgressSubtitle`
- `frontend/src/components/courses/FormatBadge.tsx` — new component
- `frontend/src/pages/registrations/MyRegistrationsPage.tsx` — replace inline subtitle with `formatProgressSubtitle`; mount `<FormatBadge>` on the card
- `frontend/src/pages/dashboard/attendee/AttendeeDashboard.tsx` — same on upcoming-events tile if it lists course sessions
- `frontend/src/pages/organizations/courses/manage/EnrollmentsTab.tsx` — instructor view picks up the breakdown automatically (no code change beyond importing `formatProgressSubtitle`)

**Tests**:
- Bootcamp card shows `Hybrid · Next session in 7d` badge + `2 of 3 modules · 1 of 2 sessions` subtitle.
- Pharmacology card shows no badge (online), `2 of 2 modules complete` subtitle (unchanged).
- Live-format course (future): card shows `Live · 2 sessions` badge.

### Phase 5 — Polish + docs

- Update `tests/manual/inventory/01-public-auth-learner.md` and `02-organizer-instructor.md` with the new routes + sidebar IA.
- Add `docs/design/hybrid-course-experience.md` (this file) to the team docs index.
- Audit instructor-side surfaces (`CourseManagementPage` Sessions tab) for the same display utilities.

## Files that remain stable (intentionally)

- `CourseSession`, `CourseSessionAttendance` models — no schema changes
- `_progress_snapshot()` — already produces the right output
- `conferencing.VideoRoom` polymorphism — already correct, just gets two more callers
- `deriveProgressDisplay` — extends, doesn't break (existing call sites continue to work)
- LiveKit webhook pipeline — already cascades into attendance correctly

## Tradeoffs and rejected alternatives

- **Reject** "make CourseSession a thin wrapper around Event". Considered; rejected because the data semantics differ (CourseSession.attendance is per-enrollment, Event.attendance is per-registration; CourseSession lives inside the gradebook, Event has its own waitlist + payment flow). Coupling them would force one set of constraints on both.
- **Reject** "interleave sessions within the modules tree by start_at order". Plausible; rejected because the data model has independent ordering (`CourseModule.order` and `CourseSession.order` are separate fields) and most LMS conventions (Coursera, Canvas, Moodle) keep live sessions in a parallel track. Two-track is also better when sessions span pre-work and post-work modules.
- **Reject** "compute progress breakdown on the client by walking modules + sessions arrays". Considered; rejected because the BOTH/EITHER/MIN_SESSIONS criteria + required-vs-optional weighting already lives in `_progress_snapshot`. Re-implementing on the client guarantees drift.
- **Reject** "let `EventLobbyPage` keep its own implementation, just clone it for course sessions". Considered for speed; rejected because we'd have two divergent implementations of the same logic within a quarter. The shared `LiveSessionLobby` is roughly 200 lines — extracting it is a one-time tax that pays back on the first event-lobby bug fix.

## Decisions on previously-open questions

Decisions below are anchored to industry research (sourced) and reviewed for fit to Accredit's CME-focused, clinician-personas, single-tenant institutional positioning. Each decision closes a question that previously blocked phase 1; the rationale below should be enough for engineering to ship without a follow-up product review.

### D1 — Completion-criteria learner copy

Hybrid completion criteria render with action-focused, plain-English templates. No raw enum exposure to learners.

| Internal enum | Learner-facing copy |
|---|---|
| `MODULES_ONLY` | "Complete all required lessons." |
| `SESSIONS_ONLY` | "Attend all required live sessions." |
| `BOTH` | "Complete all lessons and attend all live sessions." |
| `EITHER` | "Complete the lessons OR attend the live sessions." |
| `MIN_SESSIONS` | "Complete all lessons and attend at least {N} live sessions." |

These strings are the only labels — the design does not maintain a separate "admin label" set. An organizer building a course sees the same line a learner does, which keeps the mental model consistent and removes the divergence risk. Internal enum names remain as they are for API stability.

**Rationale.** Docebo and ACCME both express completion as conditions ("when X happens", "when Y is satisfied") rather than as named states. Clinicians scan; the verb-first pattern ("Complete…", "Attend…") matches how medical curricula already communicate requirements ([Docebo enrollment rules](https://help.docebo.com/hc/en-us/articles/360020128579-Activating-and-managing-the-Enrollment-rules-app); [Royal College Section 1 framing](https://www.royalcollege.ca/)). Splitting admin and learner copy was considered and dropped: there's no audience whose needs are served by exposing the enum name.

### D2 — Cancelled sessions auto-recompute

When a `CourseSession.status` is set to `CANCELLED`:

1. The cancelled session is **automatically removed** from completion-criteria denominators for every active enrollment in the course. No manual "Recompute completion" click is required.
2. Existing `CourseSessionAttendance` rows for the cancelled session are **preserved** in the audit log, but **excluded** from the active completion calculation.
3. Every active enrollee is **emailed** ("Session N cancelled — your completion requirements have been updated"), with the new effective requirements stated explicitly.
4. **Rescheduling is a separate workflow**: the cancelled session stays cancelled; the instructor creates a new `CourseSession` (which appears as a fresh attendance opportunity for all enrollees). Old attendance is not migrated forward.

**Rationale.** Existing LMS systems (Moodle, Canvas) deal with this by deleting sessions, which is why their guides describe manual workarounds — they don't have an explicit cancelled state. Accredit does (`CourseSession.Status.CANCELLED` in `backend/src/learning/models.py:1666`). Treating the cancellation as the signal that triggers recompute removes a source of friction (admin clicking "Recompute" after every cancellation) without sacrificing the audit trail (attendance rows survive). Email notification is the established UX pattern across cohort-based platforms (Coursera, edX) and is non-negotiable for CME contexts where the credit obligations are real.

### D3 — Recording-as-attendance: track always, credit never

Recording playback is **tracked but not credited** toward `CourseSessionAttendance.is_eligible`.

- A new lightweight model `CourseSessionRecordingView` captures playback events (enrollment, session, watch_seconds, last_position, completed_at). Used for instructor signal ("80% of missed-live attendees watched the replay") and learner signal ("✓ You watched the Session 1 recording").
- The completion calculation reads only `CourseSessionAttendance.is_eligible`. Watching the recording — even all the way through — does not flip that field.
- The compassionate-exception path is `CourseSessionAttendance.is_manual_override` (already in the model — `backend/src/learning/models.py:1817`). An instructor can mark a specific learner attended for a specific reason. This is auditable and individual — exactly what CME requires.

**Rationale.** ACCME explicitly treats a live activity and its recording as **two separate activities**, both with their own compliance requirements ([ACCME Enduring Materials Guide](https://www.ismanet.org/PDF/OneSource/EnduringMaterials-PlanningGuidetoMaintainingCompliance.pdf)). Royal College Section 1 vs Section 3 carries the same separation. The xAPI specification reserves the `attended` verb for real-time participation; recording-viewing uses `experienced` or `watched` ([xAPI verbs](https://xapi.com/blog/deep-dive-verb/)). Conflating the two would fail accreditation review. Tracking playback is non-negotiable separately — it's useful product signal and a foundation for an eventual async-credit path (D5 below).

### D4 — In-person delivery mode: 3 values, no async

`CourseSession.delivery_mode` is a required enum with **three** values:

```
delivery_mode: 'online' | 'in_person' | 'hybrid'
```

- `online` — synchronous live session backed by a `VideoRoom` (today's only mode).
- `in_person` — physical co-location. **No `VideoRoom` is provisioned**; LiveKit webhook attendance does not apply. Attendance is recorded via `is_manual_override` (sign-in sheet → instructor enters the roster) or via a future badge/QR-scan integration.
- `hybrid` — instructor in-person plus remote synchronous attendees. `VideoRoom` provisioned; attendance from both LiveKit webhook (for remote) and `is_manual_override` (for in-person).

`asynchronous` is **rejected as a value**: a "session" is, by definition, something that happens at a scheduled time. Asynchronous content belongs in `ModuleContent`, not in `CourseSession`. Forcing the enum to carry async would confuse the conceptual boundary and create surfaces (lobby, recording playback, attendance) that don't apply.

**Implementation precondition** for Phase 2: when `delivery_mode == 'in_person'`, the lobby route renders an "in-person session" variant (location, time, what to bring) without a Join button or video-room indicator, and the LiveKit webhook task short-circuits before creating a `CourseSessionAttendance` row.

**Rationale.** Mature LMS distinguish in-person from online at the session level (Cornerstone ILT vs vILT, Moodle facetoface, Canvas Calendar meeting types). The `asynchronous` value the research initially proposed conflates two different primitives — most institutions handle async via separate self-paced course content, not via "asynchronous sessions" ([institutional modality definitions](https://www.unomaha.edu/online-at-uno/online-resources/modes-definitions.php)). Three values map cleanly to existing data: `VideoRoom` already exists for `online`/`hybrid`; the path for `in_person` is the existing `is_manual_override` field, which today's LiveKit webhook already respects.

### D5 — Flagged for a follow-up design pass: per-mode credit attribution

ACCME and Royal College both treat live attendance and recording-viewing as **separate creditable activities** that may award **different credit values** under different frameworks (Section 1 group-live vs Section 3 self-assessment, or AMA PRA Category 1 direct vs indirect). Today, `CourseSession.cpd_credits` and `Course.cpd_credits` are flat decimal fields — a session is worth N credits regardless of how the learner experienced it.

The phase 1 API shape this design introduces (`module_progress`, `session_progress`, `LiveSessionSerializer`) will need to carry **credit-attribution metadata** when this is properly modelled — likely a per-attendance-event credit type, not a per-session one. This is **out of scope for the current implementation** but should be revisited before any sale to a customer that requires Royal College Section-1/Section-3 distinction or AMA PRA Direct/Indirect tracking. Phase 1 should not bake assumptions that the future model would have to undo (e.g., assuming credits are exactly `session.cpd_credits` regardless of attendance source).

Concrete guardrail for Phase 1: when surfacing per-session CPD on the lobby/recording pages, label it as "**Up to** {N} CPD credits" rather than "{N} CPD credits earned" until the attribution model is in place.
