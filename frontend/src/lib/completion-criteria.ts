// Single source of truth for hybrid-completion-criteria copy.
// Per docs/design/hybrid-course-experience.md (D1): the same plain-English
// action-focused sentence is shown to organizers in the course form AND to
// learners in player surfaces. No separate admin/learner copy.

export type CompletionCriteria =
    | 'modules_only'
    | 'sessions_only'
    | 'both'
    | 'either'
    | 'min_sessions';

export function formatCompletionCriteria(
    criteria: CompletionCriteria | null | undefined,
    minSessions?: number | null,
): string {
    switch (criteria) {
        case 'modules_only':
            return 'Complete all required lessons.';
        case 'sessions_only':
            return 'Attend all required live sessions.';
        case 'both':
            return 'Complete all lessons and attend all live sessions.';
        case 'either':
            return 'Complete the lessons OR attend the live sessions.';
        case 'min_sessions': {
            const n = minSessions && minSessions > 0 ? minSessions : 1;
            return `Complete all lessons and attend at least ${n} live session${n === 1 ? '' : 's'}.`;
        }
        default:
            return '';
    }
}

// Per D5 in docs/design/hybrid-course-experience.md: when attendance only
// partially determines credit (criteria ∈ EITHER, MIN_SESSIONS), advertise
// CPD as "Up to N" until completion. Once enrollment status is COMPLETED,
// switch to the actual earned figure if known.
export function formatCpdLabel(args: {
    credits: number | string | null | undefined;
    criteria: CompletionCriteria | null | undefined;
    isCompleted: boolean;
    earnedCredits?: number | string | null;
}): string {
    const { credits, criteria, isCompleted, earnedCredits } = args;
    const total = credits == null ? 0 : credits;
    if (isCompleted && earnedCredits != null && earnedCredits !== '') {
        return `${earnedCredits} CPD`;
    }
    const partial = criteria === 'either' || criteria === 'min_sessions';
    return partial ? `Up to ${total} CPD` : `${total} CPD`;
}

