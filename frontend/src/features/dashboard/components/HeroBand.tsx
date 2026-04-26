import * as React from "react";
import { Link } from "react-router-dom";
import { Progress } from "@/shared/ui/progress";
import { Button } from "@/shared/ui/button";
import { cn } from "@/lib/utils";

/**
 * HeroBand — the role-specific full-width banner at the top of every
 * dashboard. Composes:
 *
 * - eyebrow (small uppercase greeting)
 * - title (main hook line)
 * - description (optional subtitle)
 * - optional progress bar (for "resume" semantics)
 * - primary + secondary CTAs
 *
 * Visual treatment is consistent — sage gradient, decorative blurs,
 * rounded-2xl, elevated shadow. Use this rather than re-rendering the
 * hero block per role.
 */

interface HeroAction {
    label: React.ReactNode;
    to: string;
    /** When true, renders as the primary `secondary`-styled solid button. */
    primary?: boolean;
}

interface HeroBandProps {
    eyebrow?: React.ReactNode;
    title: React.ReactNode;
    description?: React.ReactNode;
    /** Render an inline progress bar (0-100) under the description. */
    progressPercent?: number | null;
    /** Up to 3 actions; the first with `primary` becomes the prominent CTA. */
    actions?: HeroAction[];
    className?: string;
}

export function HeroBand({
    eyebrow,
    title,
    description,
    progressPercent,
    actions = [],
    className,
}: HeroBandProps) {
    const primaryAction = actions.find((a) => a.primary);
    const secondaryActions = actions.filter((a) => !a.primary);
    const pct =
        progressPercent != null
            ? Math.min(100, Math.max(0, Math.round(progressPercent)))
            : null;

    return (
        <section
            className={cn(
                "relative overflow-hidden rounded-2xl bg-gradient-to-br from-primary via-primary to-accent p-block text-primary-foreground shadow-elevated",
                className
            )}
        >
            <div className="relative z-10 grid gap-card md:grid-cols-[1fr_auto] md:items-end">
                <div className="min-w-0">
                    {eyebrow && (
                        <p className="text-caption uppercase tracking-wider text-primary-foreground/80">
                            {eyebrow}
                        </p>
                    )}
                    <h1 className="mt-2 text-display-lg text-white drop-shadow-sm">{title}</h1>
                    {description && (
                        <p className="mt-tight text-body-lg text-primary-foreground/85 line-clamp-2">
                            {description}
                        </p>
                    )}
                    {pct != null && (
                        <div className="mt-card flex max-w-sm items-center gap-tight">
                            <Progress value={pct} className="h-2 bg-white/20" />
                            <span className="text-caption font-medium tabular-nums text-primary-foreground/90">
                                {pct}%
                            </span>
                        </div>
                    )}
                </div>
                {actions.length > 0 && (
                    <div className="flex flex-wrap gap-tight md:flex-col md:items-end">
                        {primaryAction && (
                            <Button asChild size="lg" variant="secondary" className="font-semibold">
                                <Link to={primaryAction.to}>{primaryAction.label}</Link>
                            </Button>
                        )}
                        {secondaryActions.map((action, i) => (
                            <Button
                                key={i}
                                asChild
                                variant="ghost"
                                className="text-white hover:bg-white/10 hover:text-white"
                            >
                                <Link to={action.to}>{action.label}</Link>
                            </Button>
                        ))}
                    </div>
                )}
            </div>
            <div
                className="pointer-events-none absolute -top-16 -right-16 h-64 w-64 rounded-full bg-white/10 blur-3xl"
                aria-hidden="true"
            />
            <div
                className="pointer-events-none absolute -bottom-20 right-32 h-40 w-40 rounded-full bg-accent/30 blur-2xl"
                aria-hidden="true"
            />
        </section>
    );
}

export type { HeroBandProps, HeroAction };
