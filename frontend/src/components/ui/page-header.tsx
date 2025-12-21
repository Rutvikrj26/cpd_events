import React from "react";
import { cn } from "@/lib/utils";

interface PageHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
    title: string;
    description?: string;
    children?: React.ReactNode;
    actions?: React.ReactNode;
}

export function PageHeader({
    title,
    description,
    children,
    actions,
    className,
    ...props
}: PageHeaderProps) {
    return (
        <div
            className={cn("flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between pb-6", className)}
            {...props}
        >
            <div className="space-y-1">
                <h1 className="text-2xl font-bold tracking-tight text-gray-900 leading-none">
                    {title}
                </h1>
                {description && (
                    <p className="text-sm text-gray-500 max-w-2xl">
                        {description}
                    </p>
                )}
            </div>
            {(children || actions) && <div className="flex items-center gap-2">{children || actions}</div>}
        </div>
    );
}
