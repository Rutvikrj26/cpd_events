import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

/* D12 — base motion: smooth color/shadow/transform transitions, gentle press
   feedback (scale-[.98]), and reduced-motion respect. The press scale is
   suppressed on the `link` variant where it would feel out of place. */
const buttonVariants = cva(
    [
        "inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium",
        "ring-offset-background transition-[color,background-color,border-color,box-shadow,transform] duration-150 ease-out",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
        "active:scale-[0.98] motion-reduce:active:scale-100 motion-reduce:transition-none",
        "disabled:pointer-events-none disabled:opacity-50 disabled:active:scale-100",
    ].join(" "),
    {
        variants: {
            variant: {
                default: "bg-primary text-primary-foreground hover:bg-primary/90 hover:shadow-rest",
                destructive:
                    "bg-destructive text-destructive-foreground hover:bg-destructive/90 hover:shadow-rest",
                outline:
                    "border border-input bg-background hover:bg-accent hover:text-accent-foreground hover:border-accent",
                secondary:
                    "bg-secondary text-secondary-foreground hover:bg-secondary/80",
                ghost: "hover:bg-accent hover:text-accent-foreground",
                link: "text-primary underline-offset-4 hover:underline active:scale-100",
            },
            size: {
                default: "h-11 px-4 py-2",
                sm: "h-10 rounded-md px-3",
                lg: "h-12 rounded-md px-8",
                icon: "h-11 w-11",
            },
        },
        defaultVariants: {
            variant: "default",
            size: "default",
        },
    }
)

export interface ButtonProps
    extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
    asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
    ({ className, variant, size, asChild = false, ...props }, ref) => {
        const Comp = asChild ? Slot : "button"
        return (
            <Comp
                className={cn(buttonVariants({ variant, size, className }))}
                ref={ref}
                {...props}
            />
        )
    }
)
Button.displayName = "Button"

export { Button, buttonVariants }
