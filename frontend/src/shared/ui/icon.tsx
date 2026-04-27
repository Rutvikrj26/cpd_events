import * as React from "react"
import type { LucideIcon, LucideProps } from "lucide-react"
import { cn } from "@/lib/utils"

/**
 * Icon size tokens (D5, visual design plan).
 * Wrap any Lucide icon to enforce consistent sizing and stroke weight
 * across the app. Default lucide stroke is 2; we use 1.75 for a slightly
 * lighter, more refined feel that pairs with Inter/Outfit.
 *
 * Usage:
 *   <Icon icon={Lock} size="status" />
 *   <Icon icon={ChevronRight} size="nav" tone="muted" />
 */

type IconSize = "dense" | "body" | "status" | "nav" | "lg" | "xl"
type IconTone = "default" | "muted" | "primary" | "success" | "warning" | "danger" | "locked"

const sizeClasses: Record<IconSize, string> = {
    dense: "h-3.5 w-3.5",   // 14px — inside dense tables / chips
    body: "h-4 w-4",         // 16px — inline with body copy
    status: "h-[18px] w-[18px]", // 18px — status icons in lists / cards
    nav: "h-5 w-5",          // 20px — sidebar / nav rail
    lg: "h-6 w-6",           // 24px — section headers
    xl: "h-8 w-8",           // 32px — empty states / hero
}

const toneClasses: Record<IconTone, string> = {
    default: "text-current",
    muted: "text-muted-foreground",
    primary: "text-primary",
    success: "text-success",
    warning: "text-warning",
    danger: "text-destructive",
    locked: "text-status-locked",
}

interface IconProps extends Omit<LucideProps, "size" | "ref"> {
    icon: LucideIcon
    size?: IconSize
    tone?: IconTone
    /** Accessible label. Defaults to aria-hidden when omitted. */
    label?: string
}

const Icon = React.forwardRef<SVGSVGElement, IconProps>(
    ({ icon: LucideComp, size = "body", tone = "default", label, className, strokeWidth = 1.75, ...rest }, ref) => {
        const a11yProps = label
            ? { role: "img" as const, "aria-label": label }
            : { "aria-hidden": true as const, focusable: false as const }

        return (
            <LucideComp
                ref={ref}
                strokeWidth={strokeWidth}
                className={cn(sizeClasses[size], toneClasses[tone], "shrink-0", className)}
                {...a11yProps}
                {...rest}
            />
        )
    }
)
Icon.displayName = "Icon"

export { Icon }
export type { IconSize, IconTone, IconProps }
