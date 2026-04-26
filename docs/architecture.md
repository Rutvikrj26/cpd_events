# Frontend Architecture

> Status: skeleton. Filled out incrementally during the `refactor/feature-architecture` migration. See [refactor-plan.md](refactor-plan.md) for the migration phases.

## TL;DR

- **Layout:** Feature-first under `src/features/{name}/`. Cross-cutting primitives in `src/shared/`. Cross-feature client state in `src/stores/`. Pages are thin route shells.
- **Server state:** [@tanstack/react-query](https://tanstack.com/query/latest). One query-key factory per feature. Mounted in [main.tsx](../frontend/src/main.tsx).
- **Client state:** [Zustand](https://github.com/pmndrs/zustand). One store per concern (theme, ui, notifications). Selectors over `getState()`.
- **Forms:** [react-hook-form](https://react-hook-form.com) + [Zod](https://zod.dev) via the shared `useZodForm` hook.
- **Styling:** Tailwind 4 with a token system in [tailwind.config.cjs](../frontend/tailwind.config.cjs) and [index.css](../frontend/src/index.css). shadcn/ui primitives in `shared/ui/`.
- **Routing:** React Router 7. All routes lazy-loaded.
- **Module boundaries:** enforced by `eslint-plugin-boundaries`. See [eslint.config.js](../frontend/eslint.config.js).

---

## Folder layout

```
frontend/src/
├── app/                  App shell — providers, route table, root error boundary
├── features/             Self-contained feature modules
│   └── {name}/
│       ├── services/     HTTP wrappers (typed axios calls). The "what to call".
│       ├── hooks/        React Query hooks + queryKeys. The "when to call".
│       ├── components/   UI for this feature only.
│       ├── store/        Zustand stores scoped to the feature.
│       ├── schemas/      Zod schemas (form + payload validation).
│       ├── types/        Domain types (or types.ts if small).
│       └── index.ts      Public barrel — only what's imported externally.
├── shared/
│   ├── ui/               shadcn primitives (Button, Card, Dialog, …)
│   ├── components/       Cross-feature composites (PageHeader, EmptyState, …)
│   ├── hooks/            Generic hooks (useDebounce, useMediaQuery, …)
│   ├── lib/              Pure utilities (cn, datetime, sanitize, …)
│   ├── schemas/          Cross-feature Zod (id, email, slug, …)
│   └── types/            Cross-feature TS types
├── stores/               Cross-feature Zustand (themeStore, uiStore, …)
├── api/                  Axios client + interceptors only
└── pages/                Thin route shells (≤ 100 LOC each)
```

## Module-import rules

Encoded in [eslint.config.js](../frontend/eslint.config.js). Currently `warn`. Promoted to `error` in Phase 5.

| from →     | app | feature | shared | store | page | api | lib | hooks | context | legacy |
|------------|-----|---------|--------|-------|------|-----|-----|-------|---------|--------|
| **app**    | ✓   | ✓       | ✓      | ✓     | ✓    | ✓   | ✓   | ✓     | ✓       | ✓      |
| **feature**| –   | own only| ✓      | ✓     | –    | ✓   | ✓   | ✓     | ✓       | ✓      |
| **shared** | –   | –       | ✓      | –     | –    | –   | ✓   | –     | –       | –      |
| **store**  | –   | –       | ✓      | –     | –    | –   | ✓   | –     | –       | –      |
| **page**   | –   | ✓       | ✓      | ✓     | –    | ✓   | ✓   | ✓     | ✓       | ✓      |
| **api**    | –   | –       | ✓      | –     | –    | –   | ✓   | –     | –       | –      |
| **lib**    | –   | –       | ✓      | –     | –    | –   | ✓   | –     | –       | –      |
| **legacy** | ✓   | ✓       | ✓      | ✓     | ✓    | ✓   | ✓   | ✓     | ✓       | ✓      |

**Key:** `feature → feature` is allowed only within the *same* feature (`features/courses/components/Foo` may import from `features/courses/hooks/useBar`, but not from `features/events/...`). Legacy paths (`src/components/`, `src/utils/`) keep their privileges so the migration doesn't have to land all at once.

## Naming conventions

- **Files:** `PascalCase.tsx` for React components. `camelCase.ts` for hooks, stores, utilities, schemas.
- **Components:** `PascalCase` exports.
- **Hooks:** `useFoo`. Hooks live in `hooks/` and end with `.ts` (not `.tsx`) unless they return JSX.
- **Stores:** `useFooStore` (exposed as a hook even though they're stores).
- **Schemas:** `fooSchema` lowercase singular.
- **Query keys:** `[featureName, resource, ...args]`, e.g. `['courses', 'detail', uuid]`.

## Conventions

### React Query

Each feature owns a `hooks/queryKeys.ts` factory. Keys are hierarchical: `[featureName, resource, ...args]`.

```ts
// features/courses/hooks/queryKeys.ts
export const courseKeys = {
    all: ['courses'] as const,
    detail: (uuid: string) => [...courseKeys.all, 'detail', uuid] as const,
    modules: (courseUuid: string) => [...courseKeys.all, 'modules', courseUuid] as const,
};
```

**Invalidation:** narrowest scope that's correct. After a mutation, invalidate the specific key that's now stale, not `.all`, unless every cached entry is affected.

**Hooks must be `disabled` when their key arg is undefined.** Pages call hooks before route params resolve.

### Zustand stores

- One store per concern. Cross-feature stores in `stores/`. Feature-scoped stores in `features/{name}/store/`.
- Always select narrowly: `useFooStore(s => s.foo)`, never `useFooStore()` (full snapshot causes re-render storms).
- Persist middleware for anything that should survive reload (theme, auth tokens). Use `partialize` to avoid persisting derived/transient state.

Example: [features/auth/store/authStore.ts](../frontend/src/features/auth/store/authStore.ts).

### Forms

Always `useZodForm(schema, { defaultValues })` (from `@/shared/lib/forms`). Compose with shadcn's `<Form>` / `<FormField>` / `<FormItem>` / `<FormLabel>` / `<FormControl>` / `<FormMessage>` from `@/shared/ui/form`.

Cross-feature primitive schemas live in [shared/schemas/primitives.ts](../frontend/src/shared/schemas/primitives.ts) (`uuid`, `email`, `slug`, `nonEmpty`, etc.).

### Modals

Don't `useState(false)`. Open dialogs via the `uiStore` and the `DialogHost` registry:

```ts
import { openDialog, registerDialog } from '@/app/providers/DialogHost';

// At feature load (e.g. features/foo/index.ts):
registerDialog('foo/confirm-delete', ConfirmDeleteDialog);

// From any callsite:
openDialog('foo/confirm-delete', { itemId: 123 });
```

`DialogHost` is mounted once in [App.tsx](../frontend/src/App.tsx) and renders the topmost dialog from the store.

### Code splitting

Every route in App.tsx is `React.lazy`-loaded via `lazyNamed` (for named exports) or stock `lazy` (for defaults). The whole `<Routes>` block is wrapped in `<Suspense fallback={<RouteFallback />}>`.

### Bundle budget

- Main JS chunk: < 800 KB (currently 751 KB; was 2.86 MB before P2)
- Per-route chunk: < 200 KB
- Run `npm run bundle:analyze` for a treemap (drops `dist/stats.html`).

### Testing

- Vitest unit tests next to the code: `Foo.tsx` → `Foo.test.tsx`.
- Hooks + stores: target 80%+ coverage.
- Five Playwright E2E flows (signup, course enrollment, quiz pass, event registration, certificate issuance) — the critical paths that most refactors risk breaking.

## Migration status (refactor/feature-architecture branch)

| Phase | Status |
|---|---|
| P0 Branch + deps | Done |
| P1 Skeleton + dead-code purge | Done |
| P2 Cross-cutting foundations | Done — shared hooks, stores (theme, ui), useZodForm, lazy routes (74% bundle reduction), shared/components (CardRow, AvatarTile, DateBlock) |
| P3a Auth canary | Done — features/auth full migration, AuthContext deleted |
| P3b Dashboard | Done — features/dashboard with hero/mini-stat/section-header, role-specific RQ hooks, three pages refactored (-34% LOC) |
| P3c Courses | Done — features/courses with 12 RQ hooks, 6 content viewers, QuizTaker, CourseCard. CoursePlayerPage went 1334 → 1091 LOC. Catalog fully migrated |
| P3d Events | Done — features/events with full hook surface, EventCard, RegistrationRow, EventStatusBadge. Dashboards consume RegistrationRow |
| P3e Smaller features | Done — features/{certificates, badges, programs, cpd, notifications} with RQ hooks |
| P3f Orgs & Admin | Done — features/{admin, contacts} with RQ hooks |
| P3g Public/Marketing | Done — features/public re-exports public catalog hooks |
| P4 Forms + DialogHost | Done — DialogHost mounted, registerDialog/openDialog API, useZodForm in shared/lib |
| P5 Hardening | Done — docs + boundary lint promoted to `error`; deferred: tests, a11y |
| P6 Merge prep | Pending — squash + smoke + merge |

### Page-level RQ migrations completed

| Page | Before | After | Notes |
|---|---|---|---|
| `Notifications.tsx` | 202 LOC, useState+useEffect | 247 LOC, RQ + sub-components | useNotifications, EmptyState |
| `MyBadgesPage.tsx` | 115 LOC, useState | 106 LOC, RQ | useMyBadges, EmptyState |
| `MyProgramsPage.tsx` | 114 LOC, useState | 128 LOC, RQ | useMyProgramEnrollments, EmptyState |
| `CertificatesPage.tsx` | 282 LOC, useState | 314 LOC, RQ | useMyCertificates, success Badge variant |
| `MyRegistrationsPage.tsx` | 470 LOC | 460 LOC partial | Data layer migrated; rest intact |

### Module-boundary lint

- Rule promoted from `warn` to `error` after migration. Zero violations across the entire `src/` tree.
- `feature → feature` cross-imports forbidden (only same-feature). Pages may import from features.

### Out-of-band tasks still deferred

- **ProfileSettings.tsx (958 LOC).** Untouched — 25+ useState hooks across multiple tabs (general, security, notifications, sessions, payouts, video). Same recipe as the other mega-pages: extract per-tab components into `features/profile/components/`, add `useProfileSettings` composite hook.
- **New Vitest unit tests** for hooks + stores (target: 80% shared / 60% features). Infra works on Node 24+; just write the tests.
- **Two skipped integration tests** — `LoginFlow.test.tsx` and `EventCreationFlow.test.tsx` need re-authoring against current UI. Per-step unit tests already cover the constituent pieces.
- **Playwright golden flows** (signup, course enrollment, quiz pass, event registration, certificate issuance) — none authored yet.
- **A11y audit** — `eslint-plugin-jsx-a11y` + axe-core in CI.
- **Squash merge** to `dev` (P6).

### Mega-page decompositions completed

| Page | Before | After | Components extracted |
|---|---|---|---|
| `EventManagement.tsx` | 1142 LOC | **52 LOC** | `EventOverviewTab`, `EventAttendeesTab`, `EventAttendanceTab`, `EventFeedbackTab`, `EventCertificatesTab`, `EventManagementTabs` (in `features/events/components/management/`) |
| `CurriculumTab.tsx` | 989 LOC | **10 LOC** | `CurriculumBuilder`, `ModuleList`, `ModuleEditor`, `ContentEditor`, `AssignmentEditor`, `RubricEditor`, `ContentPreviewDialog` (in `features/courses/components/authoring/`) |
| `CoursePlayerPage.tsx` | 1091 LOC | **21 LOC** | `CoursePlayer`, `PlayerSidebar`, `PlayerHeader`, `PlayerContent`, `PlayerDialogs`, `AssignmentSubmissionForm`, `LockedModuleNotice` (in `features/courses/components/player/`) + `useCoursePlayerData` composite hook with `useQueries` for per-module content |
| `AttendeeDashboard.tsx` | 422 LOC | 184 LOC | (see P3b) |
| `OrganizerDashboard.tsx` | 324 LOC | 247 LOC | (see P3b) |
| `InstructorDashboard.tsx` | 175 LOC | 130 LOC | (see P3b) |
| `CoursePlayerPage.tsx` | 1334 LOC | 1091 LOC | Content viewers + QuizTaker (P3c partial; chrome remains) |

### Node version

- Required: **Node 20.19+** (per `vite@7`, `jsdom@29`, multiple workspace deps).
- Use `nvm use 24` (or `nvm alias default 24`) before running `npm install`, `npm run build`, `npx vitest`, etc.
- Bash scripts can prefix with `PATH="/Users/$USER/.nvm/versions/node/v24.14.1/bin:$PATH"` if their shell defaults to an older version.
