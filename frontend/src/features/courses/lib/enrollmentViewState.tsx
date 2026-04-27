/**
 * UI mapping for `CourseEnrollment.view_state` — the discriminated union
 * the backend returns on every learner-facing enrollment payload.
 *
 * Six kinds map to (badge, CTA, optional secondary CTA). One file, one
 * exhaustive switch — adding a seventh kind to the backend produces a
 * TypeScript error here at the `_exhaustive: never` line, which catches
 * the consumer drift class of bug.
 *
 * See ``backend/src/learning/view_states.py:derive_course_enrollment_view_state``
 * for the producer side.
 */

import type { CourseEnrollmentViewState } from '@/features/courses/hooks/useCoursePlayerBootstrap';

export type EnrollmentViewStateKind = NonNullable<CourseEnrollmentViewState['kind']>;

// Restricted to variants that actually exist in `shared/ui/badge.tsx`.
type BadgeVariant =
    | 'default'
    | 'secondary'
    | 'outline'
    | 'destructive'
    | 'success'
    | 'progress'
    | 'locked'
    | 'overdue'
    | 'success-subtle'
    | 'progress-subtle'
    | 'locked-subtle';

export interface EnrollmentCardCta {
    /** Label shown in the badge (top-left of the card). */
    badge: {
        label: string;
        variant: BadgeVariant;
    };
    /** Primary CTA — what the big button at the bottom of the card does. */
    primary: {
        label: string;
        /** Where the button links. ``null`` = button is rendered disabled. */
        to: string | null;
    };
}

interface MinimalEnrollment {
    uuid: string;
    course?: { uuid?: string; slug?: string | null } | null;
}

/**
 * Resolve the badge + CTA for a given enrollment + its view_state.
 *
 * The function takes the enrollment as a second arg so it can build the
 * `/learn/{uuid}` and `/courses/{slug}` links without each consumer
 * having to repeat that derivation.
 */
export function resolveEnrollmentCardCta(
    viewState: CourseEnrollmentViewState | null | undefined,
    enrollment: MinimalEnrollment,
): EnrollmentCardCta {
    const courseUuid = enrollment.course?.uuid ?? '';
    const courseSlug = enrollment.course?.slug ?? courseUuid;

    if (!viewState) {
        // Defensive default — should never fire once the backend rolls out
        // view_state to every consumer surface, but keeps the UI safe if a
        // legacy serializer somewhere still omits the field.
        return {
            badge: { label: 'Enrolled', variant: 'secondary' },
            primary: { label: 'Open Course', to: `/learn/${courseUuid}` },
        };
    }

    switch (viewState.kind) {
        case 'awaiting_approval':
            return {
                // `locked-subtle` reads warning-neutral (no red urgency,
                // matches the lock-icon vibe of the gated module rows).
                badge: { label: 'Awaiting Approval', variant: 'locked-subtle' },
                primary: {
                    // Routes to /learn/{uuid} → bootstrap returns
                    // `pending_approval` → PendingApprovalShell renders.
                    // Same destination for consistency; the shell explains
                    // the wait.
                    label: 'View Status',
                    to: `/learn/${courseUuid}`,
                },
            };

        case 'payment_pending':
            return {
                badge: { label: 'Payment Pending', variant: 'overdue' },
                primary: {
                    label: 'Complete Payment',
                    to: `/courses/${courseSlug}`,
                },
            };

        case 'ready_to_start':
            return {
                badge: { label: 'Ready to start', variant: 'success-subtle' },
                primary: { label: 'Start Course', to: `/learn/${courseUuid}` },
            };

        case 'in_progress':
            return {
                badge: { label: 'In Progress', variant: 'progress-subtle' },
                primary: { label: 'Continue', to: `/learn/${courseUuid}` },
            };

        case 'completed':
            return {
                badge: { label: 'Completed', variant: 'success' },
                primary: { label: 'Review', to: `/learn/${courseUuid}` },
            };

        case 'revoked': {
            // Sub-cases by reason. Dropped vs expired both surface
            // "view course" as the recovery path; the catalog page's CTA
            // (Re-enroll, "registration closed", etc.) handles the rest.
            const reason = viewState.reason ?? '';
            const label = reason === 'expired' ? 'Expired' : 'Dropped';
            return {
                badge: { label, variant: 'outline' },
                primary: { label: 'View Course', to: `/courses/${courseSlug}` },
            };
        }

        default: {
            // Exhaustiveness guard — narrowing on viewState.kind (not the
            // surrounding object, which the generated OpenAPI schema models
            // as a single optional-fields type rather than a TS discriminated
            // union). Adding a 7th kind on the backend produces a TS error
            // here at build time.
            const _exhaustive: never = viewState.kind;
            throw new Error(`Unhandled view_state kind: ${_exhaustive}`);
        }
    }
}
