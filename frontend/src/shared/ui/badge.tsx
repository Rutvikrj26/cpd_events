import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
    "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
    {
        variants: {
            variant: {
                default:
                    "border-transparent bg-primary text-primary-foreground hover:bg-primary/80",
                secondary:
                    "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
                destructive:
                    "border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80",
                outline: "text-foreground",
                /* Status variants (D4) — narrative meaning over decoration.
                   `success` reads "completed/passed" without competing with the primary CTA. */
                success:
                    "border-transparent bg-success text-success-foreground",
                progress:
                    "border-transparent bg-status-progress text-status-progress-foreground",
                locked:
                    "border-transparent bg-status-locked text-status-locked-foreground",
                overdue:
                    "border-transparent bg-status-overdue text-status-overdue-foreground",
                /* Soft/subtle versions for use against busy backgrounds (e.g. inside a card body). */
                'success-subtle':
                    "border-success/30 bg-success/12 text-success",
                'progress-subtle':
                    "border-status-progress/30 bg-status-progress/12 text-status-progress",
                'locked-subtle':
                    "border-status-locked/30 bg-status-locked/12 text-status-locked",
            },
        },
        defaultVariants: {
            variant: "default",
        },
    }
)

export interface BadgeProps
    extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> { }

function Badge({ className, variant, ...props }: BadgeProps) {
    return (
        <div className={cn(badgeVariants({ variant }), className)} {...props} />
    )
}

export { Badge, badgeVariants }
