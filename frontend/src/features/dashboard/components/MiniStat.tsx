import * as React from "react";
import type { LucideIcon } from "lucide-react";
import { Card } from "@/shared/ui/card";
import { cn } from "@/lib/utils";

/**
 * MiniStat — compact KPI tile used on every dashboard hero strip.
 *
 * Optimized for a 4-up grid below the hero band. Fixed height so the
 * row reads as a strip, not as four cards of varying size.
 */

type MiniStatTone = "primary" | "success" | "warning" | "muted" | "danger" | "accent";

interface MiniStatProps {
    label: string;
    value: number | string;
    icon: LucideIcon;
    tone?: MiniStatTone;
    /** Optional secondary text under the value (e.g. "+3 this week"). */
    delta?: string;
    /** Click-through target. When provided, renders as an interactive card. */
    href?: string;
    className?: string;
}

const TONE_CLASSES: Record<MiniStatTone, string> = {
    primary: "bg-primary/10 text-primary",
    success: "bg-success/12 text-success",
    warning: "bg-status-progress/12 text-status-progress",
    muted: "bg-muted text-muted-foreground",
    danger: "bg-destructive/10 text-destructive",
    accent: "bg-accent/15 text-accent-foreground",
};

export function MiniStat({ label, value, icon: IconComp, tone = "muted", delta, href, className }: MiniStatProps) {
    const content = (
        <div className="flex items-center gap-tight">
            <div
                className={cn(
                    "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg",
                    TONE_CLASSES[tone]
                )}
            >
                <IconComp className="h-5 w-5" strokeWidth={1.75} aria-hidden="true" />
            </div>
            <div className="min-w-0">
                <div className="text-h2 leading-none font-semibold tabular-nums">{value}</div>
                <div className="mt-1 text-caption uppercase tracking-wide text-muted-foreground">
                    {label}
                </div>
                {delta && (
                    <div className="mt-0.5 text-caption font-medium text-muted-foreground/80">
                        {delta}
                    </div>
                )}
            </div>
        </div>
    );

    return (
        <Card elevation={href ? "interactive" : "rest"} className={cn("p-tight", className)}>
            {href ? (
                <a href={href} className="block focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/60">
                    {content}
                </a>
            ) : (
                content
            )}
        </Card>
    );
}

export type { MiniStatProps, MiniStatTone };
