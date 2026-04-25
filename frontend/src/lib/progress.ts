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
