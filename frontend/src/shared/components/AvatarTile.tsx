import * as React from "react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * AvatarTile — square colored tile with a centered icon.
 *
 * The canonical "icon avatar" used on list-item cards (certificates,
 * badges, my courses, etc.). Pairs with CardRow's leading slot.
 *
 * Tone determines the surface tint + icon color. Sizes match the
 * accompanying body block heights so CardRow's alignment reads cleanly.
 *
 * Usage:
 *     <AvatarTile icon={GraduationCap} tone="success" />
 *     <AvatarTile icon={Lock} tone="locked" size="lg" />
 */

type AvatarTileTone = "primary" | "success" | "progress" | "locked" | "warning" | "danger" | "muted" | "accent";
type AvatarTileSize = "sm" | "md" | "lg";

interface AvatarTileProps extends Omit<React.HTMLAttributes<HTMLDivElement>, "children"> {
    icon: LucideIcon;
    tone?: AvatarTileTone;
    size?: AvatarTileSize;
    label?: string;
}

const toneClasses: Record<AvatarTileTone, string> = {
    primary: "bg-primary/12 text-primary",
    success: "bg-success/12 text-success",
    progress: "bg-status-progress/12 text-status-progress",
    locked: "bg-status-locked/12 text-status-locked",
    warning: "bg-warning/15 text-warning",
    danger: "bg-destructive/12 text-destructive",
    muted: "bg-muted text-muted-foreground",
    accent: "bg-accent/15 text-accent-foreground",
};

const sizeClasses: Record<AvatarTileSize, { box: string; icon: string }> = {
    sm: { box: "h-8 w-8 rounded-md", icon: "h-4 w-4" },
    md: { box: "h-10 w-10 rounded-lg", icon: "h-5 w-5" },
    lg: { box: "h-12 w-12 rounded-lg", icon: "h-6 w-6" },
};

export const AvatarTile = React.forwardRef<HTMLDivElement, AvatarTileProps>(
    ({ icon: IconComp, tone = "primary", size = "md", label, className, ...rest }, ref) => {
        const sizing = sizeClasses[size];
        const a11y = label ? { role: "img" as const, "aria-label": label } : { "aria-hidden": true as const };

        return (
            <div
                ref={ref}
                className={cn(
                    "flex shrink-0 items-center justify-center",
                    sizing.box,
                    toneClasses[tone],
                    className
                )}
                {...a11y}
                {...rest}
            >
                <IconComp className={sizing.icon} strokeWidth={1.75} aria-hidden="true" />
            </div>
        );
    }
);
AvatarTile.displayName = "AvatarTile";

export type { AvatarTileTone, AvatarTileSize, AvatarTileProps };
