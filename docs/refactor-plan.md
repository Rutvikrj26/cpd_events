# Frontend Restructure Plan

> **Status:** Drafted 2026-04-26. Not yet started.
> **Branch:** `refactor/feature-architecture` (to be created)
> **Strategy:** Big-bang on a long-lived branch, **feature-first** layout, **React Query + Zustand** state.
> **Estimate:** ~25–35 working days end-to-end (single dev). Parallelizable in Phase 3.

## Why

The frontend audit identified five compounding problems:

1. **Mega-pages.** `CoursePlayerPage.tsx` (1334 LOC), `EventManagement.tsx` (1142), `CurriculumTab.tsx` (989), `ProfileSettings.tsx` (958) — data, state, dispatch, and UI tangled in single files. Untestable, hard to extend.
2. **Manual data fetching everywhere.** ~47 instances of `useState + useEffect + try/catch + setLoading`. No dedup, no cache, no refetch-on-focus, lots of boilerplate. React Query is already installed and wired into [main.tsx](frontend/src/main.tsx) but no page uses it.
3. **No code splitting.** Zero `React.lazy()` usages → 2.8 MB main JS bundle. Every page loads upfront.
4. **Half-migrated `features/` folder.** Only `auth` and `events` live there; everything else is in `pages/` or `components/`. Two competing organizing principles.
5. **244 `any` types in pages, only 9 forms** use the claimed RHF + Zod stack.

This plan addresses all five plus dead-code purge, naming conventions, and module-boundary enforcement.

---

## Target architecture

### Folder layout

```
frontend/src/
├── app/                         # App-level shell
│   ├── App.tsx                  # router only (lazy-loaded routes)
│   ├── providers/               # QueryClientProvider, ThemeProvider, AuthProvider
│   └── routes.tsx               # route table (single source)
├── features/                    # feature modules — each self-contained
│   ├── auth/
│   │   ├── api/                 # raw HTTP wrappers (axios)
│   │   ├── hooks/               # useLogin, useCurrentUser, useManifest (React Query)
│   │   ├── components/          # LoginForm, SignupForm, ProtectedRoute
│   │   ├── store/               # authStore (Zustand) — token only
│   │   ├── schemas/             # Zod schemas
│   │   ├── types.ts
│   │   └── index.ts             # public barrel — only export from here
│   ├── courses/
│   ├── events/
│   ├── registrations/
│   ├── certificates/
│   ├── badges/
│   ├── programs/
│   ├── cpd/
│   ├── organizations/
│   ├── billing/
│   ├── contacts/
│   ├── notifications/
│   ├── dashboard/               # role-aware composition of other features
│   └── public/                  # marketing, discovery, FAQ
├── shared/                      # cross-feature primitives
│   ├── ui/                      # shadcn primitives (button, card, dialog, …)
│   ├── components/              # cross-feature composites (PageHeader, EmptyState, …)
│   ├── hooks/                   # useAsync, useDebounce, useLocalStorage, useMediaQuery
│   ├── lib/                     # pure utilities (datetime, initials, sanitize, cn)
│   ├── schemas/                 # cross-feature Zod (id, email, datetime)
│   └── types/                   # cross-feature TS types
├── stores/                      # cross-feature Zustand stores (uiStore, themeStore)
├── api/                         # axios client + interceptors only — feature APIs live IN features
└── pages/                       # thin route shells, ≤100 LOC each
```

### Rules

1. **Feature isolation.** A feature may import from `shared/`, `stores/`, `api/` (client only), and its own folder. **No cross-feature imports** (`features/courses` cannot import from `features/events`). Cross-feature composition happens in `pages/` or `features/dashboard/`. Enforced via `eslint-plugin-boundaries`.
2. **Public surface.** Each feature exposes only what its `index.ts` re-exports. Internal components stay private.
3. **One story per file.** Components are < 250 LOC. Hooks are < 100. If you exceed, extract.
4. **Co-location.** Tests, types, schemas live next to the code they cover (`Button.tsx` + `Button.test.tsx` + `Button.types.ts`).
5. **Pages are dumb.** A page composes feature components and handles routing concerns only. No `useState`-driven business logic in `pages/`.
6. **Server state** lives in React Query. **Client state** lives in Zustand. **Form state** lives in React Hook Form. **URL state** lives in the URL. No state mechanism without a clear lane.

### Naming

- Files: `PascalCase.tsx` for components, `camelCase.ts` for everything else (hooks, stores, utilities). Drop kebab-case from `ui/` to match.
- Components: `PascalCase`. Hooks: `useFoo`. Stores: `useFooStore`. Schemas: `fooSchema`.
- Query keys: `[feature, resource, ...args]`, e.g. `['courses', 'detail', uuid]`. Centralized in each feature's `hooks/queryKeys.ts`.

---

## Phase 0 — Branch + dependencies (½ day)

**Goal:** A blank green-field with all foundations installed.

**Steps:**
1. Cut branch `refactor/feature-architecture` from `dev`.
2. Install: `zustand`, `eslint-plugin-boundaries`, `vite-plugin-bundle-analyzer`. (`@tanstack/react-query`, `@tanstack/react-query-devtools`, `react-hook-form`, `zod` already installed.)
3. Add `<ReactQueryDevtools />` to [main.tsx](frontend/src/main.tsx) in dev mode.
4. Add ESLint rules for module boundaries (allowed import graph encoded in config).
5. Add `pnpm bundle:analyze` script (or npm equivalent).
6. Create `docs/architecture.md` with the rules above so the team has one source of truth.

**Deliverables:** Green branch, ESLint passing, dev tools mounted.

---

## Phase 1 — Folder skeleton + dead-code purge (1 day)

**Goal:** New folder shape exists; obvious dead code is gone.

**Steps:**
1. Create empty feature folders (`features/auth`, `features/courses`, …) and `shared/`, `stores/`, `app/`.
2. **Delete:**
   - [components/layout/ProtectedRoute.tsx](frontend/src/components/layout/ProtectedRoute.tsx) — stub overshadowed by `features/auth` version.
   - [shared/](frontend/src/shared) — old barrel folder (rename target conflicts; will be replaced by new `shared/`).
   - [pages/dashboard/organizer/TagLibraryPage.tsx](frontend/src/pages/dashboard/organizer/TagLibraryPage.tsx) — disabled, comment says `TAGGING-DISABLED`.
3. **Rename:** `lib/useDocumentTitle.ts` is a side-effect function, not a hook → move to `shared/lib/setDocumentTitle.ts`. Build a real `useDocumentTitle` hook in `shared/hooks/`.
4. Move [components/ui/](frontend/src/components/ui/) → `shared/ui/` and update imports (codemod).
5. Move [lib/utils.ts](frontend/src/lib/utils.ts) (cn helper) → `shared/lib/`.

**Deliverables:** Old + new folders coexist; nothing user-facing changed; bundle still builds.

---

## Phase 2 — Cross-cutting foundations (2–3 days)

**Goal:** All the primitives features will rely on are in place.

### 2a. Shared hooks (`shared/hooks/`)

- `useAsync<T>(fn, deps)` — generic async with `data | error | isLoading`. For one-off calls outside React Query.
- `useDebounce(value, ms)`.
- `useLocalStorage<T>(key, initial)`.
- `useMediaQuery(query)`.
- `useDocumentTitle(title)` — real hook.
- `useBreakpoint()` — wrap useMediaQuery for sm/md/lg/xl.

### 2b. Zustand stores (`stores/`)

- `themeStore` — replaces `ThemeProvider`. Single source of truth for theme; persists to localStorage.
- `uiStore` — modal stack, drawer state, command-menu open. Replaces ad-hoc `useState(false)` modal patterns.
- `notificationStore` — local toast queue management (sonner stays as the renderer).

> **Pattern:** stores expose `{state, actions}`; selectors are encouraged (`useThemeStore(s => s.theme)`).

### 2c. React Query conventions

- Expand [lib/queryClient.ts](frontend/src/lib/queryClient.ts) `queryKeys` factory into a per-feature pattern. Each feature owns its keys in `features/{name}/hooks/queryKeys.ts`.
- Standard error handling: API client throws typed errors; React Query's `onError` is configured globally to log; per-mutation `onError` decides whether to toast.
- Standard cache invalidation patterns documented in `docs/architecture.md`.

### 2d. API client refactor (`api/client.ts`)

- Stop auto-toasting on errors. Throw typed errors with `{status, code, message, fields}`.
- Move the token refresh queue to a dedicated `api/auth-interceptor.ts`.
- Keep public-route bypass.
- Update existing API modules in `api/*/` (don't move yet — that happens in Phase 3 per feature).

### 2e. Form library (`shared/lib/forms.ts`)

- `useZodForm<T>(schema, defaults)` — wraps `useForm` + `zodResolver`.
- Shared schemas in `shared/schemas/` for primitives (UUID, email, ISO date, slug).
- A `<FormField>` shadcn-aware wrapper that pulls Zod errors automatically.

### 2f. Code splitting

- Convert every route in [App.tsx](frontend/src/App.tsx) to `React.lazy`. Wrap in `<Suspense>` with skeleton fallback.
- Add `manualChunks` config to vite for vendor splits (radix, lucide, livekit, quill, recharts).
- **Target:** main bundle < 800 KB; per-route chunk < 200 KB.

**Deliverables:** Foundations exist; one canary feature (auth) ready to migrate using them.

---

## Phase 3 — Feature migrations (8–14 days, parallelizable)

**Order chosen for risk and learning:** smallest + best-defined first, then biggest payoff.

For each feature, the recipe is the same:

> 1. Create `features/{name}/` folders.
> 2. Move/rewrite API calls into `features/{name}/api/` (kept thin; just typed wrappers).
> 3. Create `features/{name}/hooks/` with React Query hooks (`useFooQuery`, `useFooMutation`).
> 4. Move components into `features/{name}/components/`. Break files > 250 LOC.
> 5. Move/create Zod schemas in `features/{name}/schemas/`.
> 6. Move types into `features/{name}/types.ts`.
> 7. Define the public barrel `features/{name}/index.ts`.
> 8. Update consumers — pages first, then any cross-feature composition.
> 9. Delete the old code.
> 10. Add unit tests for hooks + stores.

### 3a. Auth (1 day) — canary

Smallest, well-defined. Validates the recipe.
- `authStore` (Zustand) — token, refresh token. No user — user comes from RQ.
- `useCurrentUser`, `useManifest`, `useLogin`, `useSignup`, `useLogout` (React Query).
- `LoginForm`, `SignupForm`, `ResetPasswordForm` (RHF + Zod).
- `ProtectedRoute` moves here from `features/auth/components/` → `features/auth/components/`. Delete old `AuthContext` once migrated.
- Refactor `OrganizationContext` similarly into `features/organizations/store/`.

### 3b. Dashboard (1 day) — composer

Cross-feature consumer. Tests the import-only-from-features rule.
- `features/dashboard/components/`: `HeroBand`, `MiniStat`, `UpcomingEventRow`, `RecentCertificateRow`, `ResumeHero`, `WelcomeHero`. (Already drafted in last session — formalize.)
- `useDashboardStats(role)` hook combines RQ data from features/courses, features/events, features/certificates.
- Pages `pages/dashboard/AttendeeDashboard.tsx` etc. shrink to < 50 LOC each.

### 3c. Courses (3 days) — biggest payoff

Explodes [CoursePlayerPage.tsx](frontend/src/pages/courses/CoursePlayerPage.tsx) (1334 LOC) and [CurriculumTab.tsx](frontend/src/pages/organizations/courses/manage/CurriculumTab.tsx) (989).

`features/courses/components/` target inventory:
- **Player chrome:** `CoursePlayer`, `PlayerSidebar`, `PlayerHeader`, `PlayerRightRail`.
- **Module nav:** `ModuleList`, `ModuleItem`, `LockedModuleTooltip`.
- **Content viewers (one per type):** `TextContentViewer`, `VideoContentViewer`, `LessonViewer`, `DocumentViewer`, `QuizTaker`, `ExternalContentViewer`.
- **Authoring:** `CurriculumBuilder`, `ModuleEditor`, `ContentEditor` (with subforms per type), `QuizBuilder`, `RubricEditor`, `AssignmentEditor`.
- **Discussion drawer:** `DiscussionPanel`, `ThreadList`, `ThreadView`, `ReplyForm`.
- **Assignment submission:** `AssignmentSubmissionForm`, `SubmissionStatus`.
- **Sessions:** `SessionsPanel`, `SessionRow`, `JoinButton` (already standalone).

Hooks: `useCourse(uuid)`, `useCourseModules`, `useCourseProgress`, `useEnrollment`, `useEnroll`, `useUpdateContentProgress`, `useSubmitAssignment`, etc.

Pages collapse: `CoursePlayerPage.tsx` (1334 LOC) → `<CoursePlayer courseUuid={uuid} />` (5 LOC).

### 3d. Events (2 days)

Explodes [EventManagement.tsx](frontend/src/pages/dashboard/organizer/EventManagement.tsx) (1142 LOC) and [EventDetail.tsx](frontend/src/pages/public/EventDetail.tsx) (935).

`features/events/components/`: `EventCard`, `EventCalendar`, `EventWizard` (5 steps), `EventDetailHeader`, `EventAgenda`, `EventSpeakers`, `EventManagementTabs`, `AttendeeList`, `AttendanceReconciliation`, etc.

### 3e. Registrations / Certificates / Badges / CPD / Programs (1 day each, parallelizable)

Smaller features. Same recipe.

### 3f. Organizations / Admin (1 day)

`features/organizations`: `UserManagementTable`, `RoleEditor`, `InvitationFlow`. Explodes [UserManagementPage.tsx](frontend/src/pages/admin/UserManagementPage.tsx) (776).

`features/billing`: subscription card, invoice list, payout management.

### 3g. Public / Marketing (1 day)

`features/public`: discovery, FAQ, terms, contact. Mostly static; least benefit but completes the migration.

**Deliverables:** Every domain lives under `features/`. `pages/` is thin. `components/` only contains cross-feature primitives in `shared/`.

---

## Phase 4 — Forms standardization + modal centralization (2–3 days)

**Goal:** Every form uses RHF + Zod; every modal is dispatched the same way.

### 4a. Form audit + conversion

- Grep for raw `<form>` and `useState` form objects in pages still using them after Phase 3.
- Convert each to `useZodForm`. Schemas live in their feature's `schemas/`.
- Standardize submission UX: disabled button while submitting, inline error display, success toast via `notificationStore`.

### 4b. Modal centralization

- All dialog opens go through `uiStore.openDialog({type, props})` instead of local `useState`.
- Define dialog registry in `app/providers/DialogHost.tsx` that mounts the right component for each dialog type.
- Removes a class of "stale state when navigating away from open modal" bugs.

**Deliverables:** Zero raw `useState`-driven forms. Zero local modal-state outside the registry.

---

## Phase 5 — Hardening (3–4 days)

**Goal:** Confidence to merge.

### 5a. Tests

- **Vitest unit:** every hook + store gets tests. Target: 80%+ coverage on `shared/` and `stores/`, 60%+ on `features/`.
- **Playwright E2E:** five golden flows.
  1. Signup → email verify → onboarding → dashboard.
  2. Browse catalog → enroll in free course → start lesson → mark complete → see progress.
  3. Take a quiz → pass → see "Passed" badge → continue to next module.
  4. Register for an event (free) → see in My Learning → check in.
  5. Course completion → certificate auto-issues → appears in wallet.

### 5b. Visual regression

- Stand up [Ladle](https://ladle.dev) (lighter than Storybook) for `shared/ui/` + key feature components.
- Snapshot tests via Playwright for the five pages most likely to regress visually.

### 5c. A11y + perf

- `eslint-plugin-jsx-a11y` in CI.
- `axe-core` in Playwright tests.
- Bundle analyzer report; verify per-route chunks are < 200 KB.
- Lighthouse run on dashboard, catalog, player.

### 5d. Documentation

- Update [docs/architecture.md](docs/architecture.md) (Phase 0 stub) with concrete examples per rule.
- Update [CLAUDE.md](CLAUDE.md) with feature-folder conventions so future AI work follows them.
- Per-feature `README.md` (one paragraph) describing what the feature owns.

**Deliverables:** Green CI, > 60% coverage, bundle within budget, a11y baseline.

---

## Phase 6 — Merge prep (1–2 days)

1. Rebase against `dev`. Resolve conflicts (will be many; lean on the strangler-fig discipline of Phase 3).
2. Full smoke test: every role's golden path.
3. Run `vite build` — verify chunk sizes meet targets.
4. Stakeholder demo + sign-off.
5. **Squash merge** as one commit with a comprehensive body listing all features migrated. Tag the merge commit `refactor/feature-architecture-complete`.
6. Branch retention: delete after 30 days.

---

## Module-boundary ESLint config (Phase 0 deliverable)

```js
// .eslintrc.cjs (excerpt)
'boundaries/elements': [
  { type: 'shared',   pattern: 'src/shared/*' },
  { type: 'feature',  pattern: 'src/features/:featureName/*' },
  { type: 'store',    pattern: 'src/stores/*' },
  { type: 'page',     pattern: 'src/pages/*' },
  { type: 'app',      pattern: 'src/app/*' },
  { type: 'api',      pattern: 'src/api/*' },
],
'boundaries/rules': [
  { from: 'shared',  allow: ['shared'] },
  { from: 'feature', allow: ['shared', 'store', 'api', { from: 'feature', sameFeature: true }] },
  { from: 'store',   allow: ['shared'] },
  { from: 'page',    allow: ['shared', 'feature', 'store'] },
  { from: 'app',     allow: ['*'] },
],
```

This is what enforces "no cross-feature imports."

---

## Risks & mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Branch lifetime > 6 weeks → unmergeable | Medium | Weekly rebase against `dev`. If `dev` ships big features, freeze them or pull them into the branch. |
| Hidden coupling between current pages | High | Phase 3a (auth canary) surfaces the patterns. Use it to refine recipe before scaling. |
| Test debt explosion | Medium | Phase 5 budgets 3–4 days. If under, ship anyway with documented gaps. Don't let tests block the refactor. |
| Lost context on monolith pages | Medium | Before each Phase-3 sub-step, read the existing page top-to-bottom and write a one-page extraction sketch. Costs ½ hour per file, saves days. |
| Backend API drift mid-refactor | Low | Backend is stable per [TECH_SUMMARY.md](TECH_SUMMARY.md). Coordinate any backend changes through one channel during the branch. |

---

## What's explicitly out of scope

- **Backend changes.** This is a frontend-only refactor.
- **Visual redesign.** The visual design plan ([async-booping-seahorse.md](~/.claude/plans/async-booping-seahorse.md)) ships independently. Phases 1–2 of that plan (tokens + dashboard hero + catalog cards) are already merged.
- **Feature work.** No new features land on this branch. If product needs ship something urgent, it goes to `dev` and we rebase.
- **Storybook full coverage.** Ladle for primitives only; full coverage is a follow-up.
- **i18n.** Tracked separately.

---

## Definition of Done

- [ ] All `pages/*` files ≤ 100 LOC.
- [ ] No `pages/*` file imports from `axios` or contains `useEffect(() => {fetch...})`.
- [ ] Every domain has a `features/{name}/` with `index.ts` barrel.
- [ ] ESLint module-boundaries passing.
- [ ] Bundle: main < 800 KB, per-route < 200 KB.
- [ ] Test coverage: shared 80%+, features 60%+.
- [ ] Five Playwright golden flows passing in CI.
- [ ] All five mega-page files (CoursePlayerPage, EventManagement, CurriculumTab, ProfileSettings, EventDetail) are decomposed; their replacements are < 250 LOC each.
- [ ] Zero forms using raw `useState` for input state.
- [ ] Zero `<Dialog>` opens via local `useState(false)`.
- [ ] `docs/architecture.md` exists and is referenced from `CLAUDE.md`.
