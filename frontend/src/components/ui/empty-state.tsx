import React from "react";
import { LucideIcon } from "lucide-react";
import { Button } from "./button";
import { cn } from "@/lib/utils";

interface EmptyStateProps extends React.HTMLAttributes<HTMLDivElement> {
    icon?: LucideIcon;
    title: string;
    description: string;
    action?: React.ReactNode | {
        label: string;
        onClick: () => void;
        variant?: "default" | "secondary" | "outline" | "ghost" | "link";
    };
}

export function EmptyState({
    icon: Icon,
    title,
    description,
    action,
    className,
    ...props
}: EmptyStateProps) {
    return (
        <div
            className={cn(
                "flex flex-col items-center justify-center rounded-lg border border-dashed border-gray-300 bg-gray-50/50 p-12 text-center",
                className
            )}
            {...props}
        >
            {Icon && (
                <div className="flex h-12 w-12 item-center justify-center rounded-full bg-muted mb-4 p-3 ring-4 ring-white">
                    <Icon className="h-full w-full text-gray-400" />
                </div>
            )}
            <h3 className="text-base font-semibold text-foreground">{title}</h3>
            <p className="mt-1 text-sm text-muted-foreground max-w-sm">{description}</p>
            {action && (
                <div className="mt-6">
                    {React.isValidElement(action) ? (
                        action
                    ) : (
                        <Button
                            onClick={(action as any).onClick}
                            variant={(action as any).variant || "default"}
                        >
                            {(action as any).label}
                        </Button>
                    )}
                </div>
            )}
        </div>
    );
}
