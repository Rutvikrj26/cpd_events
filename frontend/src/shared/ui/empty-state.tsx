import React from "react";
import { LucideIcon } from "lucide-react";
import { Button } from "./button";
import { cn } from "@/lib/utils";

type EmptyStateTone = "default" | "muted" | "dashed";

interface EmptyStateProps extends React.HTMLAttributes<HTMLDivElement> {
    icon?: LucideIcon;
    /**
     * Optional inline SVG / illustration. Renders above the icon ring.
     * Keep illustrations to a single brand-tinted color for consistency (D10).
     */
    illustration?: React.ReactNode;
    title: string;
    description: string;
    /**
     * Visual tone:
     * - `default`: solid card with subtle border (use inside neutral surfaces).
     * - `muted`:   tinted muted background, no border (use inside white cards).
     * - `dashed`:  dashed border, transparent background (today's default).
     */
    tone?: EmptyStateTone;
    action?: React.ReactNode | {
        label: string;
        onClick: () => void;
        variant?: "default" | "secondary" | "outline" | "ghost" | "link";
    };
    secondaryAction?: React.ReactNode;
}

const toneClasses: Record<EmptyStateTone, string> = {
    default: "bg-card border-border",
    muted: "bg-muted/40 border-transparent",
    dashed: "bg-muted/30 border-dashed border-border",
};

export function EmptyState({
    icon: IconComp,
    illustration,
    title,
    description,
    tone = "dashed",
    action,
    secondaryAction,
    className,
    ...props
}: EmptyStateProps) {
    return (
        <div
            className={cn(
                "flex flex-col items-center justify-center rounded-lg border p-block text-center",
                "min-h-[18rem]",
                toneClasses[tone],
                className
            )}
            {...props}
        >
            {illustration && (
                <div className="mb-card flex h-24 w-24 items-center justify-center text-primary/70" aria-hidden="true">
                    {illustration}
                </div>
            )}
            {IconComp && !illustration && (
                <div className="mb-tight flex h-12 w-12 items-center justify-center rounded-full bg-muted p-3 ring-4 ring-background">
                    <IconComp className="h-full w-full text-muted-foreground" aria-hidden="true" strokeWidth={1.75} />
                </div>
            )}
            <h3 className="text-h3 text-foreground">{title}</h3>
            <p className="mt-2 max-w-sm text-body text-muted-foreground">{description}</p>
            {(action || secondaryAction) && (
                <div className="mt-card flex flex-wrap items-center justify-center gap-3">
                    {action && (
                        React.isValidElement(action) ? (
                            action
                        ) : (
                            <Button
                                onClick={(action as any).onClick}
                                variant={(action as any).variant || "default"}
                            >
                                {(action as any).label}
                            </Button>
                        )
                    )}
                    {secondaryAction}
                </div>
            )}
        </div>
    );
}
