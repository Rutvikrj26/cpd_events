import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * DateBlock — vertical "calendar tile" used as the leading slot on
 * upcoming-event / scheduled-session card rows.
 *
 * Three stacked elements: month (caption uppercase), day (display
 * number), time (caption tabular). Tinted with the primary palette by
 * default; switch tones for status-driven contexts (e.g. amber for
 * "starting soon", muted for past sessions).
 *
 * Usage:
 *     <DateBlock date={event.starts_at} />
 *     <DateBlock date={s.starts_at} tone="progress" showTime={false} />
 */

type DateBlockTone = "primary" | "progress" | "muted" | "accent";

interface DateBlockProps {
    date: Date | string;
    tone?: DateBlockTone;
    showTime?: boolean;
    className?: string;
    /**
     * Override how the time is formatted. Accepts an Intl.DateTimeFormat
     * locale and options. Defaults to the user's locale + h:mm a.
     */
    timeOptions?: Intl.DateTimeFormatOptions;
}

const toneClasses: Record<DateBlockTone, string> = {
    primary: "bg-primary/10 text-primary",
    progress: "bg-status-progress/12 text-status-progress",
    muted: "bg-muted text-muted-foreground",
    accent: "bg-accent/15 text-accent-foreground",
};

const DEFAULT_TIME_OPTIONS: Intl.DateTimeFormatOptions = { hour: "2-digit", minute: "2-digit" };

export const DateBlock = React.forwardRef<HTMLDivElement, DateBlockProps>(
    ({ date, tone = "primary", showTime = true, className, timeOptions }, ref) => {
        const d = date instanceof Date ? date : new Date(date);
        const month = d.toLocaleString(undefined, { month: "short" });
        const day = d.getDate();
        const time = d.toLocaleTimeString([], timeOptions ?? DEFAULT_TIME_OPTIONS);

        return (
            <div
                ref={ref}
                className={cn(
                    "flex min-w-[68px] flex-col items-center justify-center rounded-lg px-3 py-2 text-center leading-tight",
                    toneClasses[tone],
                    className
                )}
                aria-label={d.toLocaleDateString(undefined, {
                    month: "long",
                    day: "numeric",
                    year: "numeric",
                    ...(showTime ? { hour: "2-digit", minute: "2-digit" } : {}),
                })}
            >
                <span className="text-caption font-bold uppercase tracking-wide opacity-90">
                    {month}
                </span>
                <span className="text-display-lg leading-none tabular-nums">{day}</span>
                {showTime && (
                    <span className="mt-1 text-caption font-medium tabular-nums opacity-80">
                        {time}
                    </span>
                )}
            </div>
        );
    }
);
DateBlock.displayName = "DateBlock";

export type { DateBlockTone, DateBlockProps };
