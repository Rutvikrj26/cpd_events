/**
 * Single source of truth for "given an enrollment, what should the badge
 * and progress bar show?".
 *
 * Background: prior to this helper, MyRegistrationsPage / CoursePlayerPage /
 * CertificatesTab / EnrollmentsTab each re-derived completion display logic
 * with subtle differences. The most common bug was rendering a "Completed"
 * badge alongside a progress bar at < 100%.
 *
 * Rule: `enrollment.status === 'completed'` is the only authoritative
 * completion signal. When status is "completed", the percentage is clamped
 * to 100 regardless of what the backend returns (defends against legacy
 * archived enrollments where progress_percent was never recomputed).
 */

interface ProgressLike {
    status?: string | null;
    progress_percent?: number | null;
}

export interface ProgressDisplay {
    /** True iff the enrollment has been marked complete (terminal state). */
    isCompleted: boolean;
    /** 0–100 integer; always 100 when isCompleted is true. */
    percent: number;
    /**
     * Human-facing badge text. Three values:
     *   - "Completed" — terminal state.
     *   - "Awaiting Review" — reached 100% but instructor hasn't confirmed.
     *   - "In Progress" — anything else.
     */
    statusLabel: 'Completed' | 'Awaiting Review' | 'In Progress';
}

export function deriveProgressDisplay(enrollment: ProgressLike | null | undefined): ProgressDisplay {
    const status = enrollment?.status ?? '';
    const isCompleted = status === 'completed';
    const raw = Number(enrollment?.progress_percent ?? 0);
    const clamped = Number.isFinite(raw) ? Math.max(0, Math.min(100, raw)) : 0;
    const percent = isCompleted ? 100 : clamped;
    const statusLabel: ProgressDisplay['statusLabel'] = isCompleted
        ? 'Completed'
        : percent >= 100
            ? 'Awaiting Review'
            : 'In Progress';
    return { isCompleted, percent, statusLabel };
}

// Format-aware subtitle line for course cards. Driven by course.format +
// hybrid_completion_criteria. See docs/design/hybrid-course-experience.md §C
// (Phase 4 / D). The function tolerates partial inputs — pages that don't
// have the breakdown yet keep rendering today's "X of Y modules complete"
// shape (preserves backward compat).
interface SubtitleEnrollment {
    modules_completed?: number | null;
    module_progress?: { modules_completed?: number; modules_total?: number } | null;
    session_progress?: {
        sessions_attended?: number;
        sessions_total?: number;
        criteria?: string;
    } | null;
    progress_percent?: number | null;
    status?: string | null;
}

interface SubtitleCourse {
    format?: string | null;
    module_count?: number | null;
}

export function formatProgressSubtitle(
    enrollment: SubtitleEnrollment | null | undefined,
    course: SubtitleCourse | null | undefined,
): string {
    if (!enrollment || !course) return '';
    const fmt = course.format ?? 'online';
    const sp = enrollment.session_progress;
    const mp = enrollment.module_progress;
    const modulesDone = mp?.modules_completed ?? enrollment.modules_completed ?? 0;
    const modulesTotal = mp?.modules_total ?? course.module_count ?? 0;
    const sessionsDone = sp?.sessions_attended ?? 0;
    const sessionsTotal = sp?.sessions_total ?? 0;

    if (fmt === 'live') {
        if (sessionsTotal > 0) {
            return `${sessionsDone} of ${sessionsTotal} session${sessionsTotal === 1 ? '' : 's'} attended`;
        }
        return enrollment.status === 'completed' ? 'Sessions complete' : 'No sessions scheduled';
    }

    if (fmt === 'hybrid' && sp) {
        const moduleFrag = `${modulesDone} of ${modulesTotal} module${modulesTotal === 1 ? '' : 's'}`;
        const sessionFrag = `${sessionsDone} of ${sessionsTotal} session${sessionsTotal === 1 ? '' : 's'}`;
        const criteria = sp.criteria ?? 'both';
        switch (criteria) {
            case 'either':
                return `${moduleFrag} or ${sessionFrag}`;
            case 'modules_only':
                return `${moduleFrag} complete`;
            case 'sessions_only':
                return `${sessionFrag} attended`;
            case 'min_sessions':
                return `${moduleFrag} · ${sessionFrag} required`;
            case 'both':
            default:
                return `${moduleFrag} · ${sessionFrag}`;
        }
    }

    // Online (default) — preserve today's wording.
    return `${modulesDone} of ${modulesTotal} modules complete`;
}
