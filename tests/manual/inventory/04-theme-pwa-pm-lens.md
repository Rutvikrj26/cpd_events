# Theme · PWA · Global UI · PM Lens — Test Inventory

This doc covers the cross-cutting layer that the per-page docs (01–03) do not — global behaviors that span every route, plus a product-manager critique applied to the highest-value surfaces.

---

## PART A — Theme, PWA, and Global UI Behaviors

### 1. Theme System

**What it does**
Context-based theme provider (`frontend/src/components/theme-provider.tsx`) manages light/dark/system modes. Persisted to `localStorage` under `vite-ui-theme` (configurable). System mode uses `prefers-color-scheme`. On change, the provider strips `light`/`dark` classes from `document.documentElement` and adds the new one. `useTheme()` hook exposes state. Toggle UI at `frontend/src/components/mode-toggle.tsx` (dropdown: Light / Dark / System).

File refs: `frontend/src/components/theme-provider.tsx:1-72`, `frontend/src/components/mode-toggle.tsx:1-36`.

**Interactions to test**
1. Load app cold → default theme is `system`
2. localStorage hydrates selected theme on first render
3. Click Light → `<html class="light">` + localStorage updated
4. Click Dark → `<html class="dark">` + localStorage updated
5. Click System → adapts to OS via matchMedia, localStorage updated
6. Change OS appearance while app open → app follows system change automatically
7. Toggle theme rapidly → no race conditions / flickers
8. Refresh after Light → Light persists
9. Clear localStorage and reload → reverts to `system`
10. Mobile browsers (iOS Safari, Chrome Android) → system theme detection in landscape + portrait

**Edge cases**
- localStorage unavailable (private browsing, quota exceeded) → falls back to default `system`
- matchMedia reports neither light nor dark → defaults to `light`
- Invalid value in localStorage (e.g. "cyan") → treat as invalid, use default
- Media query listener fires multiple times during OS change → no infinite loops
- Rapid theme toggling followed by navigation → theme persists correctly

---

### 2. PWA Install Prompt

**What it does**
`InstallPrompt` (`frontend/src/components/pwa/InstallPrompt.tsx`) listens for `beforeinstallprompt` (Chrome/Edge when PWA criteria met). Stores deferred prompt and shows custom card with Install / Not Now / X. Dismissals persist in `localStorage` under `installPromptDismissed` with a 7-day suppression window. Manifest at `frontend/public/manifest.json`: theme_color `#63945f`, display `standalone`, two shortcuts (Browse Events, My Dashboard).

File refs: `frontend/src/components/pwa/InstallPrompt.tsx:11-115`, `frontend/public/manifest.json:1-64`.

**Interactions to test**
1. First visit on Chrome desktop (PWA criteria met) → custom card appears (bottom-left mobile, bottom-right desktop)
2. Click Install → Chrome native install prompt appears, custom card dismisses on completion
3. Click "Not now" → card hides, localStorage timestamp written
4. Click X → same as Not now
5. Refresh within 7 days of dismiss → no card
6. Wait 7+ days (or backdate localStorage) → card returns
7. iOS Safari → no `beforeinstallprompt`; user follows Share → Add to Home Screen (no custom prompt)
8. Android Chrome → `beforeinstallprompt` fires; Install triggers native prompt
9. App already installed → event never fires, card never shows
10. Malformed dismiss timestamp → isNaN guard returns false → card shows

**Edge cases**
- localStorage returns null → first-time prompt shows
- Non-numeric value in localStorage → treated as invalid
- Both native Chrome prompt dismissed AND custom Not now → both events logged
- Multiple `beforeinstallprompt` events fire (some Chrome versions) → only latest stored
- Dev mode (`isDev`) → console.log shows outcome, no functional difference

---

### 3. Service Worker / Offline

**What it does**
`vite-plugin-pwa` with Workbox (`frontend/vite.config.ts:5-66`):
- **Precaching:** all JS, CSS, HTML, icons, images (max 4 MB per file)
- **Runtime cache (NetworkFirst):** `https://api.*` — 24h expiry, max 50 entries
- **Runtime cache (CacheFirst):** images (png/jpg/svg/gif) — 30d expiry, max 100 entries
- **Auto-update:** `registerType: "autoUpdate"` — silent SW updates, applied on next page load (no user prompt)

File ref: `frontend/vite.config.ts:10-66`.

**Interactions to test**
1. Load app on Chrome → SW registers (DevTools → Application → Service Workers)
2. Toggle offline (DevTools → Network → Offline) → cached pages remain usable
3. API call while offline → fails (NetworkFirst tries network, falls back to cache; if no cache, error)
4. Image assets while offline → load from cache
5. First visit → reload offline → cached version serves
6. Offline + visit a route not in precache → blank/fallback (no offline fallback page defined)
7. Deploy new bundle → old SW still in control until next refresh
8. Refresh after deploy → new SW installs, old unregisters, new version on next nav
9. DevTools → Cache Storage → observe `api-cache` and `images-cache`
10. API cache > 50 entries → LRU eviction
11. Image cache > 100 entries → LRU eviction

**Edge cases**
- SW install fails (invalid plugin config) → app still works (falls back to non-PWA)
- File > 4 MB → excluded from precache; relies on runtime caching
- Clock skew → 24h expiry approximate; cached API data may be stale
- User clears site data → all caches gone, fresh SW registration
- Two tabs open, SW updates in one → other tab unchanged until nav/refresh

---

### 4. ScrollToTop

**What it does**
`frontend/src/components/layout/ScrollToTop.tsx:1-12` — listens to `useLocation().pathname`, calls `window.scrollTo(0, 0)` on every pathname change. Renders null.

**Interactions to test**
1. Load `/dashboard`, scroll 500px → navigate to `/events` → page scrolls to top instantly
2. On event list, scroll, click event → detail loads at top
3. Browser back after scrolling → browser may restore position (not ScrollToTop's job); forward nav → scrolls to top
4. Navigate to `/events#section` → ScrollToTop fires (0, 0), then browser hash resolution may scroll to anchor (race possible)
5. Rapid nav (multiple clicks) → each pathname change triggers; no debounce
6. Same pathname, different query params → pathname unchanged, scroll does NOT trigger
7. Hash-only change (`#top` → `#bottom`) → pathname unchanged, no scroll
8. Long page with infinite scroll → top-scroll on nav may feel jarring but is by design

**Edge cases**
- Component unmounts before scrollTo runs → no observable issue (synchronous)
- Page shorter than viewport → scrollTo(0, 0) fires but no visual change
- Mobile browser scroll-restoration → may fight ScrollToTop on back/forward; test carefully

---

### 5. Toasts (shadcn + Sonner — both mounted)

**What it does**
Both toast systems are mounted in `App.tsx:309-310`.
- **shadcn toast** (`frontend/src/components/ui/toaster.tsx`, `use-toast.ts:8-9`): max 1 concurrent (`TOAST_LIMIT = 1`), removal delay `1_000_000ms` (effectively never auto-dismisses), reducer-based.
- **Sonner**: `position="top-right"`, `richColors`, `closeButton`, default duration ~4 s.

In practice, call sites use Sonner exclusively (`ImportDialog.tsx:12,50,63`, `CertificateTemplatesList.tsx`, etc.).

**Interactions to test**
1. Sonner success → top-right green, close button
2. Sonner error → top-right red
3. Sonner warning/info → richColors variants
4. Multiple toasts rapidly → shadcn limited to 1; Sonner stacks
5. Wait 4 s → Sonner auto-dismisses; shadcn persists
6. Click Sonner close → immediate dismiss
7. Click elsewhere → toast persists (no click-away dismiss)
8. Route change with toast visible → persists or auto-dismisses depending on Sonner config
9. shadcn toast with action button → action clickable
10. Long message → wraps or truncates by viewport
11. Multiple Sonner toasts → vertical stack top-right
12. Title-only / description-only / both → all render

**Edge cases**
- Toast created just before nav → may appear on wrong page (no route-aware auto-dismiss)
- Rapid `toast.success()` calls < 1 s apart → Sonner stacks; shadcn keeps only 1 (others discarded)
- HTML in description → verify no XSS
- Network error toast, recovery before dismiss → user may not retry
- shadcn TOAST_REMOVE_DELAY = 1 M → second queued toast appears only after first dismissed

---

### 6. ErrorBoundary

**What it does**
Class component (`frontend/src/components/ErrorBoundary.tsx:19-142`) wraps the entire app (`App.tsx:99`). Catches render errors via `getDerivedStateFromError` + `componentDidCatch`. Logs to console in dev. Fallback UI: AlertCircle icon + error message + three actions: **Try Again** (resets state), **Reload Page** (window.location.reload), **Go Home** (navigate `/`). Dev mode shows expandable error details. Custom fallback supported via prop.

**Interactions to test**
1. Trigger render error (e.g. `null.property`) → fallback renders
2. Dev mode → expandable details visible (message + component stack)
3. Production mode (`isDev=false`) → details hidden
4. Try Again → state resets, retries render (works if error was transient)
5. Reload Page → full refresh
6. Go Home → navigate to `/`
7. Child component throws → fallback shown
8. Nested error boundaries (if any) → child catches first, parent only on re-throw
9. Error in event handler (not render) → NOT caught (React limitation)
10. Error boundary itself throws → white screen
11. Custom fallback prop → renders custom UI
12. Multiple sequential errors → each triggers new error state

**Edge cases**
- Error in `useEffect` → caught on next render
- Async/Promise rejection → NOT caught by boundary
- Event listener error (onClick, onChange) → NOT caught; needs try/catch in handler
- Hydration mismatch → caught and shows fallback
- Boundary unmounts while error is showing → cleans up

---

### 7. Layouts

#### DashboardLayout (`frontend/src/components/layout/DashboardLayout.tsx:9-20`)
Two-column: collapsible Sidebar + main content. Sidebar (`Sidebar.tsx:42-200+`) filters nav by role + feature flags. Logout + ModeToggle in footer. Active item highlighted. Tooltip on collapsed hover.

#### AuthLayout (`frontend/src/components/layout/AuthLayout.tsx:5-37`)
Centered form on semi-transparent secondary bg. Logo at top. Terms / Privacy at bottom.

#### PublicLayout (`frontend/src/components/layout/PublicLayout.tsx:32-418`)
Full-width header + main + footer. Sticky header, z-50, backdrop blur. Desktop: NavigationMenu dropdowns (Products / Browse / Resources). Mobile: hamburger → full-screen overlay with body scroll lock. Auth section (top-right desktop): Login/Signup if anon; Dashboard + avatar dropdown if authed. Footer: 5-column grid.

**Interactions to test (DashboardLayout)**
1. Click sidebar toggle → collapses, tooltips on items
2. Click nav item → loads page, item highlighted
3. Long sidebar → scrollable
4. Logout → triggers logout, redirects `/login`
5. Theme toggle → flips colors
6. Mobile width → sidebar should collapse/hide
7. Role check: learner sees My Learning / Accreditations; organizer sees Manage Events / Contacts / Reports

**Interactions to test (AuthLayout)**
8. Logo click → `/`
9. Terms / Privacy click → `/terms`, `/privacy`

**Interactions to test (PublicLayout)**
10. Products dropdown → reveals Events / LMS / Organizations
11. Browse dropdown → Events / Courses / Programs
12. Resources dropdown → Features / FAQ / About / Contact / Verify Certificate
13. Mobile hamburger → overlay, body scroll locked
14. Click nav link in mobile menu → menu closes, link navigates
15. Click backdrop → menu closes (verify)
16. Anon → Login / Signup buttons
17. Authed → Dashboard + avatar
18. Avatar click → dropdown (Profile / Dashboard / Sign out)
19. Sign out from dropdown → logout
20. Footer links → navigate
21. Copyright auto-updates via `new Date().getFullYear()`

**Edge cases**
- Sidebar overflows viewport → scrollable
- Long username in avatar dropdown → truncate or wrap
- Role changes mid-session → nav refreshes if manifest re-fetched
- Mobile menu open + window resize to desktop → menu auto-closes
- Rapid nav clicks → race conditions
- Logout from mobile menu → menu closes before redirect

---

### 8. Auth Refresh / Session Expiry

**What it does**
`AuthContext` (`frontend/src/contexts/AuthContext.tsx:38-244`):
- On mount: read token from localStorage (`getToken()`), validate with `isTokenValid()` (expiry check)
- If valid → fetch user profile + manifest in parallel
- `login()` API → `completeLogin(access, refresh)` persists tokens, hydrates user
- `logout()` removes tokens, clears state, `window.location.href = '/login'`
- Applies institution branding: hex → HSL → CSS vars (`--primary`, `--primary-foreground`), favicon + page title
- Exposes `hasRoute()`, `hasFeature()` for feature-flag UI gating

Token refresh likely lives in an axios interceptor (`/lib/auth` not surfaced in research).

**Interactions to test**
1. Cold load with valid token → auto-login, profile fetched, dashboard accessible
2. Cold load with no token → unauth, `/login`
3. Cold load with expired token → invalid, unauth, `/login`
4. Login form submit → tokens stored, user fetched
5. Token expires while active → depends on 401 handling (auto-logout or refresh)
6. Manual logout → tokens removed, redirected
7. Logout while offline → still clears tokens + redirects
8. Rapid login attempts → no token-hydration race
9. Backend role change → next manifest reflects new role; nav updates
10. Institution `primary_color` set → CSS var updated, brand applied
11. Institution `favicon_url` set → favicon swaps
12. Page title set to institution name → `document.title` updates
13. Manifest features → `hasFeature('create_events')` gates UI

**Edge cases**
- Token in localStorage but `getToken()` returns null (parse error) → unauth
- `getCurrentUser()` fails → init stalls (needs timeout/error handling)
- Multi-tab logout → other tabs still hold tokens in memory; will fail next API call (interceptor catches)
- Manifest fetch fails → routes/features unavailable, UI may not gate properly
- Invalid hex for institution color → CSS var unset, default fallback
- Invalid favicon URL → no favicon
- Refresh interceptor fails repeatedly → exponential backoff or gives up (depends on impl)

---

### 9. Toaster vs Sonner Overlap

Both Toasters are mounted in `App.tsx:309-310`. Overlap is intentional: shadcn for persistent system messages, Sonner for user feedback. Observed call sites use Sonner exclusively.

**Interactions to test**
1. Sonner success + dismiss shadcn simultaneously → coexist, no visual conflict
2. Sonner top-right + shadcn default (bottom-right) → no overlap
3. Multiple Sonner + 1 shadcn → Sonner stacks vertically, shadcn isolated
4. Close Sonner, then shadcn appears → timing-dependent
5. Tall viewport → both stacks fit

**Edge cases**
- z-index conflict → one behind the other
- Mobile narrow viewport → wrap or truncate; verify readability
- Both `position: fixed` → potential stacking-context issues
- Rapid toast creation → Sonner queues; shadcn keeps only 1 visible

---

### 10. Modal / Dialog Conventions

**Dialog** (`frontend/src/components/ui/dialog.tsx:9-58`): wraps Radix DialogPrimitive. Fixed centered with slide+fade animations. Black/80% backdrop, click-to-dismiss. Close X top-right (toggleable via `hideCloseButton`). ESC dismisses.

**AlertDialog** + `ConfirmDialog` wrapper (`frontend/src/components/ui/confirm-dialog.tsx:37-87`): title, description, confirm/cancel, loading state with spinner, destructive variant (red), async `onConfirm` supported. Buttons disabled during loading.

**Interactions to test**
1. Open dialog → backdrop visible, content centered, animation smooth
2. Click X → closes, backdrop removed, focus returns to trigger
3. Press ESC → closes
4. Click backdrop → closes (Radix default)
5. Dialog with form → fields focusable, Tab cycles
6. Focus management → first focusable receives focus on open
7. AlertDialog destructive → confirm button red
8. ConfirmDialog loading → confirm disabled, spinner, cancel disabled
9. Async `onConfirm` 2+ s → button stays disabled until resolved
10. Nested dialogs → outer closes if inner closes (verify Radix)
11. Content larger than viewport → scrollable inside dialog
12. Mobile width → full-width or centered with max-width

**Edge cases**
- Rapid open/close → animations stutter
- Prefilled form → initial focus on first input
- Browser back while dialog open → dialog closes (router-dependent)
- Sidebar z-index conflict (dialog z-50 vs unspecified sidebar)
- Very long content → must overflow scroll inside

---

### 11. Loading Skeletons

`Skeleton` (`frontend/src/components/ui/skeleton.tsx:4-14`): `<div class="animate-pulse bg-muted">`. Composed templates (`page-skeleton.tsx:1-97`): `PageHeaderSkeleton`, `CardSkeleton`, `TableSkeleton`, `FormSkeleton`, `DashboardSkeleton`, `ListSkeleton`. Used in `CourseCatalogPage`, `EventRecordingPage`, `OrgCoursesPage`, etc.

**Interactions to test**
1. Page loading → skeleton visible, boxes pulse
2. Data arrives → real content swaps in (no jarring flicker if smooth)
3. Fast network → skeleton barely visible
4. Throttled network → skeleton visible 2+ s, then content
5. TableSkeleton with 5 rows → 5 gray lines pulse
6. DashboardSkeleton → 4-grid stats pulse → populate
7. FormSkeleton → 4 label-input pairs pulse
8. ListSkeleton → multiple items pulse
9. Content taller than viewport → scroll position preserved on load
10. Animation smooth, not jerky

**Edge cases**
- Skeleton animates but content never arrives (silent error) → skeleton persists indefinitely; needs error fallback
- Navigate away mid-load → animation stops, cleaned up
- Custom className override (e.g. `h-20 w-20`) → applied
- Multiple skeletons → animate in sync (global CSS animation)

---

### 12. EmptyState Component

`EmptyState` (`frontend/src/components/ui/empty-state.tsx:17-56`): icon (Lucide) + title + description + optional action (React element OR `{label, onClick, variant}`). Centered, dashed border, `bg-muted/50`, icon in circle. Used by `ContactsPage`, `MyEvents`, `CourseDiscoveryPage`, `data-table`.

**Interactions to test**
1. No data → EmptyState renders with icon / title / description
2. Click action button → custom `onClick` fires
3. Multiple EmptyStates on page → independent
4. Long title/description → wraps/truncates per max-width
5. No icon prop → icon div hidden, title/description centered
6. No action → no button
7. React-element action → custom element rendered
8. Destructive variant action → red button
9. Narrow container → responsive
10. Spinner-action → loading state

**Edge cases**
- `icon` undefined → renders nothing (graceful?)
- Long action label → button wraps/truncates
- Action onClick throws → unhandled (should catch)
- className override → applied
- Mobile → padding adjusted

---

### Global UI test summary

**Critical paths for Chrome testing:**
1. Theme persistence + system mode detection
2. PWA install (Chrome desktop, Android Chrome, iOS Safari)
3. Service worker offline + cache behaviour
4. ScrollToTop on every route change
5. Toaster/Sonner visibility, stacking, auto-dismiss
6. ErrorBoundary recovery + fallback UI
7. Layout role-based nav filter + mobile responsiveness
8. Auth init / login / logout / session
9. Dialog ESC/backdrop dismiss + focus management
10. Skeleton → real content swap
11. EmptyState rendering + action handling

**Estimate:** ~150 distinct interactions across these 12 areas, with ~40 edge cases needing specific conditions (offline, slow network, role changes, localStorage failures, etc.).

---

## PART B — Product Manager Critique Lens

This is an evaluation framework, not a feature inventory. For each high-value surface, apply the 15-point checklist below to identify usability, trust, and conversion issues that the per-page test docs won't surface.

### How to use this section

1. Open the surface in Chrome (logged in as the appropriate persona).
2. For each numbered point in the checklist, observe and write a one-line verdict: ✅ good / ⚠ caveat / ❌ broken / N/A.
3. Roll the ❌ and ⚠ items into the **PM red flags** running list at the bottom of this doc.
4. Red flags become product backlog candidates — they don't block release of test workflows, but should be visible to the PM.

### The 15-point PM checklist

For each surface answer:

1. **Job-to-be-done clarity** — within 5 seconds of landing, can the user state what this screen lets them do?
2. **Empty-state quality** — actionable (CTA + explainer + illustration) or hostile (blank table)?
3. **Loading-state quality** — skeleton matching final layout vs spinner vs nothing? Layout shift on data arrival?
4. **Error-message quality** — does each error state tell the user what to do next, in plain language?
5. **Confirmation & undo affordances** — destructive actions (cancel, refund, revoke, deactivate, delete) confirmed? Undo within window?
6. **Trust signals** — verification badges, payment-success cues, encryption icons, "your data is safe" copy where relevant?
7. **First-run friction** — count clicks from sign-up → first registered event. Anything > 5 clicks is a flag.
8. **Conversion-funnel hygiene** — public discovery → event detail → register → checkout → confirmation: where can a user drop?
9. **Dead-end pages** — any route a user can land on with no clear next action?
10. **Cross-screen consistency** — does "Cancel registration" look/word the same on MyEvents and EventDetail?
11. **Cognitive load** — how many things compete for attention at first glance? Rank by f-pattern visual weight.
12. **Mobile-first audit** — DevTools-emulate iPhone 14, run the path: any element clipped, scroll-locked, tap-target-too-small?
13. **Notification redundancy** — does the same backend event spawn email + in-app + dashboard banner? Helpful or noisy?
14. **Time/timezone display** — every datetime respects `user.timezone`? Anywhere it falls back to UTC?
15. **Currency display** — paid events in CAD / USD / etc.: are conversions or "displayed in CAD" disclaimers shown?

---

### Surface 1 — Organizer Dashboard (`/dashboard` as organizer)

**Persona:** Dr. James Wilson (organizer@utoronto.ca)

| # | Verdict | Notes |
|---|---|---|
| 1 | ✅ | Title "Organizer Dashboard" + subtitle + 8 stat cards make the JTBD legible. |
| 2 | N/A | No empty state observed with current seed. Test by seeding zero events. |
| 3 | ⚠ | Stat cards show 0 then jump to real number — slight layout-shift moment. |
| 4 | ⚠ | If `getEvents` 500s, no graceful error message — silent fail. |
| 5 | N/A | No destructive actions on this screen. |
| 6 | ✅ | "Active Events" / "Currently live or published" subtitles act as trust signals. |
| 7 | ✅ | Big "Create New Event" CTA. |
| 8 | N/A | This screen is not a funnel step. |
| 9 | ✅ | Multiple onward links (Recent Activity → events, Quick Actions → create flows). |
| 10 | ⚠ | "Recent Activity" event names link to `/organizer/events/:uuid/manage` — same target as Events list — good consistency. |
| 11 | ⚠ | 8 stat cards + recent activity table + quick actions — feels dense. Consider grouping. |
| 12 | ⚠ | Stat-card grid wraps on mobile but `Recent Activity` table is wide — needs horizontal scroll. |
| 13 | N/A | Dashboard doesn't trigger notifications. |
| 14 | ⚠ | Recent Activity dates ("4/13/2026") are MM/DD/YYYY — assumes en-US even for Toronto-tz user. |
| 15 | N/A | Dashboard doesn't show currency. |

**Observed concrete bug — flag for product backlog:**
- "Certificates Issued: 0" while seed has issued 7 certificates (verified in DB). Likely the count filters by `issued_by=current_user` but the seed assigns the org as issuer, not the logged-in admin. Either the metric is wrong or the spec is wrong — clarify.
- "Course Completions: 0" while Emily has completed two courses. Same root cause likely.

---

### Surface 2 — Learner Dashboard (`/dashboard` as Emily — heavy learner)

**Persona:** Dr. Emily Park (emily.park@hospital.com)

Apply the 15-point checklist:

1. **JTBD** — Welcome banner + upcoming-event cards make it clear; ⚠ "what should I do today" is not surfaced (no prioritised queue).
2. **Empty-state** — Test by seeding learner with zero registrations (Aisha-style). Should show onboarding nudges + Discover CTA.
3. **Loading** — Cards likely use Skeleton (verify in Part A).
4. **Error** — Test 500 on `getMyRegistrations`. Should not hide the rest of the page.
5. **Undo** — N/A on read screen.
6. **Trust** — Issued certificates surfaced with download icon — good.
7. **First-run** — Count clicks: signup → verify email → onboarding → dashboard → Discover Events → Event detail → Register → Pay → confirmation. ~9 steps. Friction warning.
8. **Funnel** — Dashboard's "Browse Events" CTA must be 1 click away (check).
9. **Dead-end** — If user has zero registrations + zero certs + zero CPD: what does the dashboard show? Probably empty cards. ⚠
10. **Consistency** — "Resume course" should look the same on Dashboard and MyLearningPage.
11. **Cognitive load** — Multiple sections (upcoming events, recent certs, CPD progress, notifications). Risk of overload.
12. **Mobile** — Does the upcoming-event card stack readably on iPhone width?
13. **Notification redundancy** — Same event triggers email reminder + Notification + dashboard banner. Audit per `Notification.Type`.
14. **Time** — `event.starts_at` in user's `timezone`? Verify on a Toronto-tz user vs LA-tz user (Michael).
15. **Currency** — Cert pages show "$X.XX" — does it indicate currency? Verify.

**PM red flags to confirm:**
- The "Aisha empty-state" experience (intentional in seed) — does it actually feel inviting or sterile? PM judgement call.
- Does the dashboard surface "Action Required" items (e.g. submit feedback, retry failed payment)? If not, those orphan in `/registrations`.

---

### Surface 3 — Course Player (`/learn/:courseUuid`)

**Persona:** Emily on Patient Communication Essentials (60% progress)

1. **JTBD** — Sidebar module tree + main content area = clear "consume this lesson, mark complete, advance".
2. **Empty-state** — Course with zero modules: what shows? Test on Pharmacology (now seeded with 2) and Surgical Draft (still 0).
3. **Loading** — Module tree skeleton vs blocking spinner?
4. **Error** — 403 enrollment-blocked: clear "Enroll to continue" CTA?
5. **Undo** — Marking content complete — can user un-mark? (Should be possible for accidental clicks.)
6. **Trust** — Quiz pass score visible? Certificate-on-completion preview?
7. **First-run** — On first content load, is there a brief "how this works" tooltip?
8. **Funnel** — Within course: complete content → next content auto-loads? Or manual click?
9. **Dead-end** — At end of course (100%), what's the next action? "View certificate" should be primary.
10. **Consistency** — Quiz UI matches assignment UI matches video player UI?
11. **Cognitive load** — Sidebar tree depth: modules → contents — good. If three-level (modules → lessons → contents) it's heavy.
12. **Mobile** — Sidebar collapses to drawer? Video player responsive?
13. **Notification redundancy** — On completion: email + notification + on-screen confetti? Audit.
14. **Time** — Due dates on assignments — user tz?
15. **Currency** — N/A.

**Notes from earlier observation:** Digital Health Records had 0 modules under "25 enrollments" — confusing for a learner who paid CA$99 and lands on an empty player. Now fixed (4 modules + content seeded).

---

### Surface 4 — Event Lobby (`/events/:id/lobby` and `/r/:registrationUuid/lobby`)

**Persona:** Emily 5 minutes before "ICU Protocols: Quick Update" (imminent)

1. **JTBD** — "Join when ready, here's the countdown" — should be obvious.
2. **Empty-state** — Lobby for an event without a video room? Should explain.
3. **Loading** — Countdown should not have a flash of "Loading…" each second.
4. **Error** — LiveKit unreachable: graceful "Reconnecting" or hard fail?
5. **Undo** — N/A.
6. **Trust** — Event title, organizer, CPD credits visible? Reduces "did I land on the right page?" anxiety.
7. **First-run** — First-time joiners: brief "you'll be muted by default, here's how to enable camera" pre-roll?
8. **Funnel** — Pre-15-min window: button disabled or hidden? Within window: prominent.
9. **Dead-end** — After event ends: lobby should redirect to `/events/:id/recording` or show "this event has ended; recording will be available shortly."
10. **Consistency** — Auth lobby vs guest lobby (`/r/:uuid/lobby`) — visual parity? Different copy for guests?
11. **Cognitive load** — Single primary action ("Join") — good.
12. **Mobile** — Camera permission dialog blocks? Tap-target for Join large enough?
13. **Notification redundancy** — Reminder email + push + dashboard banner — all firing at T-15min? Audit.
14. **Time** — "Starts in 5m" — relative time good. Absolute fallback for unusual timezones?
15. **Currency** — N/A.

**Open questions for PM:**
- What does the lobby show 1 hour before vs 15 min before vs at start? Time-window UX is the entire UX of this page.

---

### Surface 5 — Public Discovery (`/discover/events`)

**Persona:** Anonymous visitor evaluating the platform

1. **JTBD** — Hero copy + filter sidebar + event cards = "browse and pick" — clear.
2. **Empty-state** — Filtered to zero results: actionable "clear filters" CTA?
3. **Loading** — Skeleton card layout vs jumping content?
4. **Error** — `/api/v1/public/events/` down: what shows? Public users won't have logs.
5. **Undo** — N/A.
6. **Trust** — Hosted-by badge, CPD-accreditation indicator on cards — surface these prominently.
7. **First-run** — Anon visitor → click event → register → forced login? Or guest-checkout option clear?
8. **Funnel** — Card → detail → Register → checkout → confirmation. Drop points: detail-page load time, login wall on register, checkout abandonment.
9. **Dead-end** — Zero filtered results without a "create alert / get notified" option = waste.
10. **Consistency** — Card layout matches on dashboard logged-in `/events` page?
11. **Cognitive load** — Filters: Event Type (5 options) + Format (3) + Fee (2). Reasonable.
12. **Mobile** — Filter sidebar collapses behind a drawer? Cards stack readably?
13. **Notification redundancy** — Anon: N/A. Logged-in viewing public discovery: any preview of "you registered for X" elsewhere?
14. **Time** — "Apr 25 · webinar" — date format implicit en-US locale.
15. **Currency** — Cards show "X Credits" but not price. Price only on detail page. Fine for browse.

**PM red flag:** The anonymous → register flow currently requires a login wall (verified in EventRegistration.tsx). If guest checkout is supposed to work, surface it on the discovery card directly with a "Register as guest" affordance, otherwise the flow buries.

---

### Surface 6 — Admin Billing (`/admin/billing`)

**Persona:** Admin (admin@utoronto.ca)

1. **JTBD** — "Audit Stripe state" — title makes this clear, three tabs deepen.
2. **Empty-state** — When zero events: "No Stripe events match the current filter" — minimal but informative. Now populated with the new seed.
3. **Loading** — List skeleton or spinner? Verify.
4. **Error** — Reconcile call timeout: clear retry?
5. **Undo** — Retry button re-runs handler — explicitly idempotent per copy. Good trust.
6. **Trust** — "Idempotent on every write" copy is reassuring for an admin.
7. **First-run** — N/A admin tooling.
8. **Funnel** — N/A.
9. **Dead-end** — Drilling into a Stripe event: where does that go? Verify the event-detail modal/page exists.
10. **Consistency** — Disputes tab status badges should colour-match Registration payment_status.
11. **Cognitive load** — Three tabs + filters per tab. Clean.
12. **Mobile** — Probably not optimised for mobile (admin tooling). Note as low-priority.
13. **Notification redundancy** — N/A on this page.
14. **Time** — "Received less than a minute ago" / "Received 5 days ago" — relative, no absolute fallback. ⚠
15. **Currency** — Amounts in cents from Stripe — UI formatting verifies.

**Concrete observation:** all Stripe event timestamps are relative ("5 days ago"). For audit/compliance this should also expose absolute timestamps on hover. PM red flag.

---

### Surface 7 — Registration Funnel (event detail → register → checkout → confirmation)

This is a flow, not a page. Walk it as a learner, anon, and known-paid persona.

1. **JTBD per step** — Each step's purpose self-evident? "Register for this event", "Tell us who you are", "Confirm payment", "You're in."
2. **Empty-state** — Trying to register for a sold-out event: clear waitlist option?
3. **Loading** — Submitting registration: button spinner + disable?
4. **Error** — Card declined on Stripe checkout: returns user to `/checkout/cancel` with retry option? Verify.
5. **Undo** — Cancellation pre-event: clear self-service path? Refund window communicated?
6. **Trust** — Stripe-hosted page = green padlock domain trust. Confirmation page = receipt + calendar invite.
7. **First-run** — Anon: signup-required wall here? Or guest-checkout fully works?
8. **Funnel** — Drop tracking: which step has highest abandonment? (PM telemetry question.)
9. **Dead-end** — `/checkout/success`: clear "What's next" with "Add to calendar" + "View registration" CTAs?
10. **Consistency** — Email confirmation copy matches the in-app confirmation copy?
11. **Cognitive load** — Each step focused on one task — good if maintained.
12. **Mobile** — Stripe page is mobile-good. Pre-Stripe steps?
13. **Notification redundancy** — Email + Notification + dashboard "Upcoming" card all confirm same event. Helpful here.
14. **Time** — Confirmation: "Starts on Wed 15 May at 2pm" — user-tz?
15. **Currency** — Pre-checkout shows "CA$149"; checkout uses Stripe's natural currency display. Consistent.

**PM red flags:**
- If guest checkout exists (`allow_guest_registration=True` per seed), is it surfaced on the discovery card / detail page, or buried under "Sign in to register"?
- Calendar invite (.ics) — attached to confirmation email and downloadable in-app? Per cross-cutting flow #7 in doc 03 — verify.

---

### Surface 8 — Instructor Grading Queue (`/courses/manage/:slug` — Submissions tab)

**Persona:** Dr. Priya Shah (instructor)

1. **JTBD** — "Grade these submissions" — title or empty-state copy must say this.
2. **Empty-state** — No ungraded items: "Nothing to grade — well done!" or blank list?
3. **Loading** — Submission list skeleton.
4. **Error** — Saving a grade: rollback on error?
5. **Undo** — Submitted grade: editable for X mins post-submission?
6. **Trust** — Rubric persisted alongside grade — auditable.
7. **First-run** — First-time instructor: rubric explained?
8. **Funnel** — N/A internal tool.
9. **Dead-end** — After grading the last item: "All caught up" + return-to-courses link?
10. **Consistency** — Grade form matches across courses?
11. **Cognitive load** — Per-submission: rubric scoring + free-text feedback + status dropdown. Heavier than ideal but appropriate for grading.
12. **Mobile** — Probably not optimised. Note as low-priority.
13. **Notification redundancy** — Learner notified via email + Notification on grade. Single email is enough; dashboard banner overkill.
14. **Time** — Submission date in instructor tz.
15. **Currency** — N/A.

---

### Additional surfaces — quick PM notes

These didn't get the full 15-point treatment; pass through them with the framework when you have time.

- **`/onboarding`** — Wizard length per role. Skip-options visible? Progress indicator? Branch for "instructor" vs "organizer" different from "learner"?
- **`/profile` (settings)** — Notification preferences UI complete? Email-change flow includes confirmation step? Account deletion (if any) buried far enough that it's not accidentally triggered.
- **`/notifications`** — Mark-all-read affordance? Filter by unread? Group similar notifications (5 reminder emails for the same event)?
- **`/badges` and `/certificates`** — Public-share affordance prominent? "Verify this credential" link on every cert?
- **`/cpd`** — Add Requirement modal reasonable? Yearly progress visualisation (donut vs bar)? Export to PDF works for compliance?
- **`/organizer/contacts`** — Bulk actions (tag, message, export) discoverable? Search by name/email + filter by event-attended both supported?
- **`/organizer/promo-codes`** — Code-validity calendar visible? Usage analytics drill-down?
- **`/organizer/reports`** — Period filter prominent? Export-to-CSV one click?
- **`/admin/users`** — Role-change action confirmation? Search + filter by role + status?
- **`/admin/users/:uuid`** — Cross-role activity panels (events attended, courses enrolled, certs earned)?

---

## Running list — PM red flags identified

(Append items here as new ones surface during testing.)

| # | Surface | Issue | Severity |
|---|---|---|---|
| 1 | Organizer dashboard | "Certificates Issued: 0" + "Course Completions: 0" while data exists. Metric filter likely scoped to `current_user` instead of org. | High |
| 2 | Organizer dashboard | Recent-activity dates use MM/DD/YYYY regardless of user `timezone`/locale. | Low |
| 3 | Organizer dashboard | 8 stat cards + table + quick actions on first viewport — cognitive overload. | Medium |
| 4 | Course detail (DHR) | Pre-fix: "25 enrollments" + 0 modules — denormalised count without backing rows. Now fixed. Audit `update_counts()` for similar drifts on other models. | Medium |
| 5 | Public discovery | If guest registration is supported, it's not surfaced on the card — login wall hides the feature. | Medium |
| 6 | Admin billing | Stripe-event timestamps are relative-only ("5 days ago"); no hover for absolute. | Low |
| 7 | Event lobby | Pre-15-min window vs in-window vs ended states need distinct UX (verify each renders correctly). | High to test |
| 8 | Notifications stack | Same backend event can spawn email + in-app + dashboard banner. Audit per `Notification.Type` whether each channel is necessary. | Medium |

---

## Maintenance

This doc is maintained alongside docs 01–03. When the UI changes:

- Re-run the global-UI Explore agent to refresh Part A.
- Walk the surfaces in Part B and update verdicts.
- Move resolved red flags to a "Resolved" subsection (don't delete — keep for institutional memory).

Re-run cadence suggestion: every minor release that touches navigation, layout, or a core funnel.
