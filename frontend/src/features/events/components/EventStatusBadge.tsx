import { Badge } from '@/shared/ui/badge';
import { cn } from '@/lib/utils';

/**
 * EventStatusBadge — single source of truth for the colored event-status
 * pill. Keep all event lifecycle states (draft, published, live, completed,
 * cancelled, …) consistent across organizer + learner surfaces.
 */

const STATUS_VARIANT: Record<string, 'success' | 'progress' | 'locked' | 'overdue' | 'secondary' | 'destructive'> = {
    draft: 'secondary',
    published: 'success',
    live: 'overdue',
    completed: 'locked',
    cancelled: 'destructive',
    closed: 'locked',
};

interface EventStatusBadgeProps {
    status: string;
    className?: string;
}

export function EventStatusBadge({ status, className }: EventStatusBadgeProps) {
    const variant = STATUS_VARIANT[status] || 'secondary';
    return (
        <Badge
            variant={variant}
            className={cn(
                'capitalize',
                status === 'live' && 'animate-pulse',
                className
            )}
        >
            {status}
        </Badge>
    );
}
