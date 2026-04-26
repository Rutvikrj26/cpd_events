# Test Inventory — Accredit CPD/LMS Platform

Exhaustive Chrome-browser interaction inventory for every surface of the platform. This is the **input** to writing test workflows — not the workflows themselves. Every clickable, every form field, every state variant, every cross-cutting flow is enumerated here so that workflow authors can pick scenarios off a list rather than re-discover them.

The inventory is grounded in actual code (route table from `frontend/src/App.tsx`, page components, API client, backend models / signals / tasks). File:line citations are embedded throughout.

---

## Doc map

| File | Scope | Headings | Source |
|---|---|---|---|
| [`01-public-auth-learner.md`](./01-public-auth-learner.md) | Anonymous browsing, marketing, auth flows, learner/attendee dashboards & player | 36 page sections + state matrices + API/SEO/mobile checklists | Explore agent (84 KB) |
| [`02-organizer-instructor.md`](./02-organizer-instructor.md) | Event lifecycle, course/program management, instructor grading, all org-side ops surfaces | Org dashboard + event create/edit + 7 EventManagement tabs + 8 CourseManagement tabs + 6 ProgramManagement tabs + Contacts/Reports/Video/Promo/Speakers + Instructor variants + form validation + permission gating | Explore agent (68 KB) |
| [`03-admin-live-crosscutting.md`](./03-admin-live-crosscutting.md) | User management, billing admin, live event journey (lobby → video → recording), 15 numbered cross-cutting flows | Admin users (2 tabs) + admin user detail + billing admin (3 tabs) + live event journey + 15 numbered flow sequences | Explore agent (72 KB) |
| [`04-theme-pwa-pm-lens.md`](./04-theme-pwa-pm-lens.md) | Global UI behaviors (theme, PWA, service worker, layouts, toasts, error boundary, skeletons, empty states) **plus** PM critique applied to high-value surfaces | Part A: 12 global UI areas; Part B: 15-point PM checklist applied to 8 surfaces + running red-flag list | Explore agent (Part A) + authored (Part B), 39 KB |

**Total:** 263 KB across 4 docs covering 60 routes + 15 cross-cutting flows + 12 global UI behaviors.

---

## How to read each entry

Every page-level section follows this structure:

```
### Page: <route> — <Component> (file: ...)

**Purpose:** one-line.

**Preconditions:**
- Auth state (anon / authed / role / verified email / onboarding done)
- Data state (e.g. "≥1 published event with capacity remaining")
- URL params

**Visible elements / regions:** comprehensive list.

**Interactions to test:** numbered, exhaustive — each names the element + action + expected outcome (and API endpoint where known).

**Edge cases & state variants:** empty / loading / error / permission-denied / long-content / mobile.

**State transitions triggered:** DB writes, signals, async tasks, emails sent, notifications created.

**Cross-page navigation:** where each link/button sends the user.
```

Cross-cutting flows in doc 03 follow:

```
### Flow N: <name>

Trigger → Preconditions → Step-by-step → Backend side effects → Edge cases → Verification points
```

Doc 04 Part B (PM critique) uses a 15-point checklist applied per surface with ✅ / ⚠ / ❌ / N/A verdicts.

---

## Conventions

- **Heading levels:** `#` doc title, `##` major section, `###` per-page or per-flow.
- **File:line citation:** `frontend/src/pages/dashboard/DashboardPage.tsx:42` — clickable in editors that support it.
- **Persona shorthand** (matches `seed_demo.py`):
  - **Admin** — Dr. Sarah Chen, `admin@utoronto.ca`
  - **Organizer** — Dr. James Wilson, `organizer@utoronto.ca`
  - **Instructor** — Dr. Priya Shah, `priya.shah@utoronto.ca`
  - **Learner (heavy)** — Dr. Emily Park, `emily.park@hospital.com`
  - **Learner (blocked)** — Dr. Michael Torres, `m.torres@clinic.com`
  - **Learner (early-journey / onboarding-incomplete)** — Dr. Aisha Khan, `aisha.khan@university.edu`
  - All persona passwords: `demo12345`
- **Status verdicts (doc 04 Part B):** ✅ good · ⚠ caveat · ❌ broken · N/A.

---

## Coverage check (verified at write time)

Extracted every `<Route path=` from `frontend/src/App.tsx`, excluded redirects-only routes (`/profile`, `/my-certificates`, `/auth/callback`, `/organizer/events`, `/organizer/events/new`, `/organizer/settings`, `/organizer/notifications`, `/organizer/contacts/tags` (TAGGING-DISABLED), and `*` catch-all).

- **60 / 60** real routes covered across docs 01–03.
- Doc 01 covers **45** routes (public + auth + learner-shared); doc 02 covers **26** (organizer/instructor); doc 03 covers **31** (admin + cross-cutting flows reference shared routes).
- Some routes appear in multiple docs by design — e.g., `/dashboard` is documented per-role, `/courses/manage/:slug` is documented for both organizer (doc 02) and instructor restricted view (doc 02 Part 2).

---

## How to use these for test workflow generation (next cycle)

These inventories are the **catalogue**. Test workflows are the **scripts**. The next cycle will:

1. Pick a persona + a scenario from the inventory (e.g. "Learner with attended past event submits feedback then checks certificate").
2. Compose interactions from the relevant page sections in order.
3. Note required fixture state (these inventories list preconditions per page).
4. Encode as a Playwright/Cypress test or a manual-QA script.

For now: read the inventory before designing a workflow so you don't miss a state variant. Open this README, jump to the doc covering your surface, scan the structure, then drill into specific sections.

---

## Maintenance

Regenerate the inventory whenever any of these change materially:

- `frontend/src/App.tsx` route table (new routes, removed routes, redirect changes)
- A multi-tab page gains/loses a tab (`EventManagement`, `CourseManagementPage`, `ProgramManagementPage`, `BillingAdminPage`, `UserManagementPage`)
- A new persona or role appears
- A cross-cutting backend flow changes shape (Stripe webhook handlers, email reminder lifecycle, notification fan-out, waitlist promotion)
- Global UI changes (theme system, PWA manifest, layout primitives)

Regen approach (matches what produced this version):

1. Three parallel Explore agents, prompted with route slices (public+auth+learner / organizer+instructor / admin+live+cross-cutting).
2. One additional Explore agent for global UI behaviours (Part A of doc 04).
3. Author Part B PM-lens by walking the application as each persona.
4. Update this README's coverage table.

The plan file at `/home/beyonder/.claude/plans/perfect-now-i-want-soft-acorn.md` documents the prompts and the structure; reuse it.

---

## What this inventory does NOT cover (deferred)

- Actual test scripts (Playwright/Cypress/manual). Next cycle.
- Performance / load testing. Out of scope.
- Browser compatibility beyond Chrome. Out of scope per project mandate.
- Backend unit / integration tests — those live under `backend/src/.../tests/`.
- Visual regression / design system audit. Out of scope.
