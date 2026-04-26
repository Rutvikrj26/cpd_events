// Compact sidebar row for a live session. Format-agnostic — used by the
// course player two-track sidebar today; future event multi-session
// sidebars will use the same component (per
// docs/design/hybrid-course-experience.md §A).

import { Check, Circle, Clock, MapPin, Radio, Video, X } from 'lucide-react';
import type { CourseSession } from '@/api/courses/types';
import { cn } from '@/lib/utils';
import { deriveLiveSessionStatus, statusLabel } from '@/lib/liveSession';

interface LiveSessionRowProps {
    session: CourseSession & {
        attendance?: { is_eligible?: boolean; attendance_minutes?: number };
        recording?: { uuid: string } | null;
    };
    isActive?: boolean;
    onClick?: () => void;
}

const STATUS_ICON = {
    attended: Check,
    live_now: Radio,
    within_join_window: Radio,
    upcoming: Clock,
    past_no_recording: X,
    past_with_recording: Video,
    cancelled: X,
} as const;

export function LiveSessionRow({ session, isActive = false, onClick }: LiveSessionRowProps) {
    const status = deriveLiveSessionStatus(session, session.attendance, new Date(), session.recording ?? null);
    const Icon = STATUS_ICON[status.kind] ?? Circle;
    const isLive = status.kind === 'live_now' || status.kind === 'within_join_window';
    const isInPerson = session.delivery_mode === 'in_person';

    return (
        <button
            type="button"
            onClick={onClick}
            className={cn(
                'w-full text-left px-3 py-2 rounded-md transition-colors',
                'flex items-start gap-2 text-sm',
                'hover:bg-accent/50',
                isActive && 'bg-accent',
                status.kind === 'cancelled' && 'opacity-60',
            )}
        >
            <Icon
                className={cn(
                    'h-4 w-4 mt-0.5 shrink-0',
                    status.kind === 'attended' && 'text-emerald-500',
                    isLive && 'text-red-500 animate-pulse',
                    status.kind === 'cancelled' && 'line-through',
                )}
            />
            <div className="flex-1 min-w-0">
                <div className={cn(
                    'truncate font-medium',
                    status.kind === 'cancelled' && 'line-through',
                )}>
                    {session.title}
                </div>
                <div className="text-xs text-muted-foreground flex items-center gap-2 mt-0.5">
                    <span>{statusLabel(status)}</span>
                    {isInPerson && (
                        <span className="inline-flex items-center gap-0.5">
                            <MapPin className="h-3 w-3" />
                            In person
                        </span>
                    )}
                    {session.is_mandatory && status.kind !== 'cancelled' && (
                        <span className="text-amber-600 dark:text-amber-400">Required</span>
                    )}
                </div>
            </div>
        </button>
    );
}
