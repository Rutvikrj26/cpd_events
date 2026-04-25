// Pure helpers for the learner-side LiveSession primitive (per
// docs/design/hybrid-course-experience.md §A). Same shape as backend
// LiveSessionSerializer. No React imports — usable from any helper.

import type { CourseSession } from '@/api/courses/types';

export type LiveSessionStatus =
    | { kind: 'attended'; eligible: boolean }
    | { kind: 'live_now'; endsAt: Date }
    | { kind: 'within_join_window'; startsAt: Date; minutesUntilStart: number }
    | { kind: 'upcoming'; startsAt: Date; daysUntilStart: number; hoursUntilStart: number }
    | { kind: 'past_no_recording' }
    | { kind: 'past_with_recording' }
    | { kind: 'cancelled' };

export interface AttendanceLike {
    is_eligible?: boolean;
    attendance_minutes?: number;
    is_manual_override?: boolean;
}

const JOIN_WINDOW_LEAD_MINUTES = 15;

function endsAt(session: CourseSession): Date {
    if (session.actual_end_at) return new Date(session.actual_end_at);
    const start = new Date(session.starts_at);
    return new Date(start.getTime() + (session.duration_minutes ?? 0) * 60_000);
}

export function isWithinJoinWindow(
    session: CourseSession,
    now: Date = new Date(),
    leadMinutes: number = JOIN_WINDOW_LEAD_MINUTES,
): boolean {
    if (session.status === 'cancelled') return false;
    const start = new Date(session.starts_at);
    const open = new Date(start.getTime() - leadMinutes * 60_000);
    const close = endsAt(session);
    return now >= open && now <= close;
}

export function deriveLiveSessionStatus(
    session: CourseSession,
    attendance: AttendanceLike | null | undefined = null,
    now: Date = new Date(),
    publishedRecording: { uuid: string } | null = null,
): LiveSessionStatus {
    if (session.status === 'cancelled') return { kind: 'cancelled' };
    if (attendance?.is_eligible) {
        return { kind: 'attended', eligible: true };
    }
    const start = new Date(session.starts_at);
    const end = endsAt(session);

    if (now >= start && now <= end) {
        return { kind: 'live_now', endsAt: end };
    }
    if (isWithinJoinWindow(session, now)) {
        const minutesUntilStart = Math.max(
            0, Math.round((start.getTime() - now.getTime()) / 60_000),
        );
        return { kind: 'within_join_window', startsAt: start, minutesUntilStart };
    }
    if (now < start) {
        const ms = start.getTime() - now.getTime();
        return {
            kind: 'upcoming',
            startsAt: start,
            daysUntilStart: Math.floor(ms / 86_400_000),
            hoursUntilStart: Math.floor(ms / 3_600_000),
        };
    }
    // Past
    if (publishedRecording || (session as any).recording) {
        return { kind: 'past_with_recording' };
    }
    return { kind: 'past_no_recording' };
}

export function statusLabel(status: LiveSessionStatus): string {
    switch (status.kind) {
        case 'attended': return 'Attended';
        case 'live_now': return 'Live now';
        case 'within_join_window':
            return status.minutesUntilStart > 0
                ? `Starts in ${status.minutesUntilStart}m`
                : 'Starting now';
        case 'upcoming':
            if (status.daysUntilStart >= 1) {
                return `In ${status.daysUntilStart}d`;
            }
            if (status.hoursUntilStart >= 1) {
                return `In ${status.hoursUntilStart}h`;
            }
            return 'Soon';
        case 'past_no_recording': return 'Missed';
        case 'past_with_recording': return 'Recording';
        case 'cancelled': return 'Cancelled';
    }
}
