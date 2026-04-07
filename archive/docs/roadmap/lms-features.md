# LMS-Only Plan + Organization Bundle

## Target Model (what we are building toward)
- Individual plans:
  - Organizer plan: events-only (current organizer shape)
  - LMS plan: courses-only
  - Attendee: free, consumption-only
- Organization plan: bundles Organizer + LMS plus team/branding/shared assets

## High-Level Steps
1. Define plan entitlements and naming
   - Decide plan IDs (e.g., `organizer`, `lms`, `organization`, `attendee`).
   - Map features per plan (events, courses, certificates, team/branding).
   - Align Stripe product/price naming with plan IDs.

2. Update data models to support LMS-only ownership
   - `Course`:
     - Make `organization` nullable.
     - Add `owner` (user) for LMS-only courses.
     - Update unique constraints to support `organization + slug` and `owner + slug`.
   - `Subscription`:
     - Add `lms` plan enum.
     - Add course usage counters and limit checks (similar to events).
   - `StripeProduct`:
     - Add course-specific limit fields (e.g., `courses_per_month`, optional learner caps).
     - Add plan tax code entry for `lms`.
   - Backfill existing courses with an `owner` (created_by or org owner).

3. Adjust permissions and RBAC for course-only accounts
   - Extend role set to include `course_manager` (or decide to keep role=organizer and gate by plan).
   - Restrict event routes to organizer plans; restrict course routes to LMS/organization plans.
   - Add manifest feature flags for course creation/management.

4. Update backend business logic and APIs
   - Course creation:
     - Accept either `organization_slug` (org-owned) or default to `owner` for LMS-only.
     - Enforce course limits via org subscription or user subscription.
   - Course modules/content:
     - Query scoping should allow `owner` access when `organization` is null.
   - Billing:
     - Subscription upgrade/downgrade logic should set account type appropriately
       (e.g., LMS plan should not upgrade to event organizer).
   - Add plan checks to event creation and certificate issuance paths.

5. Frontend updates for plan-aware UX
   - Pricing + Billing pages:
     - Add LMS plan card, price display, and plan IDs.
   - Signup/Onboarding:
     - Allow LMS plan selection and role assignment.
   - Navigation + feature gating:
     - Show course management only for LMS/org plans.
     - Hide event organizer flows for LMS-only accounts.

6. Stripe and plan configuration
   - Create new Stripe Product/Price for LMS plan.
   - Seed/update `StripeProduct` in Django admin with course limits.
   - Confirm checkout + webhooks map LMS plan to correct local plan and role.

7. Migrations and cleanup
   - Create migrations for model changes (Course ownership, plan enums, limits).
   - Update tests and fixtures that assume existing plan enums.
   - Ensure any plan-dependent constants (billing config, RBAC) are updated.

8. Verification
   - LMS plan user can create/manage courses but cannot create events.
   - Organizer plan user can create events but cannot create courses.
   - Organization plan users can do both and share assets across members.
   - Existing org-owned courses/events still function after migration.

## Post-Implementation Audit
- After LMS gaps are closed, run a full-platform audit across all plans and document remaining gaps before the next cycle.
