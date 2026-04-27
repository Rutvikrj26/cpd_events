// Format-aware pill that surfaces course shape (online / live / hybrid)
// + the next live-session timing on My Learning cards. Per §C of
// docs/design/hybrid-course-experience.md.
//
// Reads CourseEnrollment.next_session_at — a backend-computed timestamp of
// the earliest upcoming non-attended-eligibly session. Avoids per-card N+1
// queries.

import { Badge } from '@/shared/ui/badge';
import { Calendar, Radio, Video } from 'lucide-react';

interface FormatBadgeProps {
    course: { format?: string | null; session_count?: number | null } | null | undefined;
    nextSessionAt?: string | null;
}

function relativeWindow(iso: string): string {
    const target = new Date(iso);
    const now = new Date();
    const ms = target.getTime() - now.getTime();
    if (ms <= 0) return 'now';
    const minutes = Math.floor(ms / 60_000);
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h`;
    const days = Math.floor(hours / 24);
    return `${days}d`;
}

export function FormatBadge({ course, nextSessionAt }: FormatBadgeProps) {
    const fmt = course?.format ?? 'online';
    if (fmt === 'online') return null;

    if (fmt === 'live') {
        const count = course?.session_count;
        return (
            <Badge variant="outline" className="text-xs gap-1">
                <Radio className="h-3 w-3" />
                <span>Live{count ? ` · ${count} session${count === 1 ? '' : 's'}` : ''}</span>
            </Badge>
        );
    }

    // Hybrid
    const upcoming = nextSessionAt ? `Next session in ${relativeWindow(nextSessionAt)}` : 'Sessions complete';
    const Icon = nextSessionAt ? Calendar : Video;
    return (
        <Badge variant="outline" className="text-xs gap-1">
            <Icon className="h-3 w-3" />
            <span>Hybrid · {upcoming}</span>
        </Badge>
    );
}
