// Centralised event-status presentation helpers. Used by event lists/cards so
// that `live`, `published`, `completed`, etc. don't all collapse to the same
// teal pill (QA finding F-15).

export type EventStatus =
    | 'draft'
    | 'published'
    | 'live'
    | 'completed'
    | 'closed'
    | 'cancelled';

type StyleSpec = {
    /** Tailwind classes overriding the default Badge look. */
    className: string;
    /** Whether to render a small pulsing dot inside the badge (live only). */
    pulse?: boolean;
};

const STATUS_STYLES: Record<string, StyleSpec> = {
    live: {
        className:
            'border-red-500/40 bg-red-500/15 text-red-600 dark:text-red-400',
        pulse: true,
    },
    published: {
        className:
            'border-emerald-500/40 bg-emerald-500/15 text-emerald-600 dark:text-emerald-400',
    },
    completed: {
        className:
            'border-slate-400/40 bg-slate-400/10 text-slate-500 dark:text-slate-400',
    },
    closed: {
        className:
            'border-slate-400/40 bg-slate-400/10 text-slate-500 dark:text-slate-400',
    },
    draft: {
        className:
            'border-amber-500/40 bg-amber-500/15 text-amber-600 dark:text-amber-400',
    },
    cancelled: {
        className:
            'border-red-500/40 bg-red-500/5 text-red-500 dark:text-red-400 line-through',
    },
};

const FALLBACK: StyleSpec = {
    className: 'border-border bg-muted/40 text-muted-foreground',
};

export function getEventStatusStyle(status: string | undefined | null): StyleSpec {
    if (!status) return FALLBACK;
    return STATUS_STYLES[status.toLowerCase()] ?? FALLBACK;
}

/**
 * Render-ready label for an event status enum value.
 *
 * The backend ships lower-case enum strings (`"published"`, `"draft"`).
 * Rendering them raw (or with the `capitalize` CSS class, which only
 * styles the first letter and breaks for compounds like `"in_progress"`)
 * produces "published" / "in_progress" in the UI. This single helper
 * keeps the casing rule in one place so `EventsPage`, the dashboard
 * Recent Activity table, and any future surface format identically.
 */
export function formatEventStatus(status: string | undefined | null): string {
    if (!status) return 'Unknown';
    return status
        .split(/[_\s]+/)
        .filter(Boolean)
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
        .join(' ');
}
