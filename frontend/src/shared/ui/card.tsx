import * as React from "react"
import { cn } from "@/lib/utils"

type CardElevation = "flat" | "rest" | "interactive" | "lifted"

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
    /**
     * Visual elevation tier (D3, visual design plan).
     * - `flat`: no shadow — for cards inside other cards or busy contexts.
     * - `rest`: default subtle shadow — passive cards.
     * - `interactive`: rest shadow + hover lift — clickable cards (catalog, dashboard).
     * - `lifted`: pronounced shadow — modal-adjacent or hero cards.
     */
    elevation?: CardElevation
}

const elevationClasses: Record<CardElevation, string> = {
    flat: "shadow-none",
    rest: "shadow-rest",
    interactive:
        "shadow-rest transition-all duration-200 ease-out hover:shadow-hover hover:-translate-y-0.5 hover:border-border/80 motion-reduce:transition-none motion-reduce:hover:transform-none",
    lifted: "shadow-lifted",
}

const Card = React.forwardRef<HTMLDivElement, CardProps>(
    ({ className, elevation = "rest", ...props }, ref) => (
        <div
            ref={ref}
            className={cn(
                "rounded-lg border bg-card text-card-foreground",
                elevationClasses[elevation],
                className
            )}
            {...props}
        />
    )
)
Card.displayName = "Card"

const CardHeader = React.forwardRef<
    HTMLDivElement,
    React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
    <div
        ref={ref}
        className={cn("flex flex-col space-y-1.5 p-6", className)}
        {...props}
    />
))
CardHeader.displayName = "CardHeader"

const CardTitle = React.forwardRef<
    HTMLParagraphElement,
    React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
    <h3
        ref={ref}
        className={cn(
            "text-h2 font-semibold leading-none tracking-tight",
            className
        )}
        {...props}
    />
))
CardTitle.displayName = "CardTitle"

const CardDescription = React.forwardRef<
    HTMLParagraphElement,
    React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
    <p
        ref={ref}
        className={cn("text-body text-muted-foreground", className)}
        {...props}
    />
))
CardDescription.displayName = "CardDescription"

const CardContent = React.forwardRef<
    HTMLDivElement,
    React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
    <div ref={ref} className={cn("p-6 pt-0", className)} {...props} />
))
CardContent.displayName = "CardContent"

const CardFooter = React.forwardRef<
    HTMLDivElement,
    React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
    <div
        ref={ref}
        className={cn("flex items-center p-6 pt-0", className)}
        {...props}
    />
))
CardFooter.displayName = "CardFooter"

export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent }
export type { CardElevation, CardProps }
