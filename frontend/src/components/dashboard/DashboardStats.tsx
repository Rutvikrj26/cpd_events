import React from 'react';
import { Card, CardContent } from "@/components/ui/card";
import { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface DashboardStatProps {
    title: string;
    value: string | number;
    icon: LucideIcon;
    description?: string;
    trend?: {
        value: number;
        label: string;
        positive?: boolean;
    };
    className?: string;
}

export const DashboardStat = ({ title, value, icon: Icon, description, trend, className }: DashboardStatProps) => {
    return (
        <Card className={cn("overflow-hidden", className)}>
            <CardContent className="p-6">
                <div className="flex items-center justify-between space-x-4">
                    <div className="flex flex-col space-y-1">
                        <span className="text-sm font-medium text-muted-foreground tracking-wide uppercase">
                            {title}
                        </span>
                        <span className="text-2xl font-bold tracking-tight">
                            {value}
                        </span>
                    </div>
                    <div className={cn("p-2 rounded-full", "bg-primary/10 text-primary")}>
                        <Icon size={20} />
                    </div>
                </div>
                {(description || trend) && (
                    <div className="mt-4 flex items-center text-xs">
                        {trend && (
                            <span className={cn(
                                "flex items-center font-medium mr-2",
                                trend.positive ? "text-green-600" : "text-red-600"
                            )}>
                                {trend.positive ? "+" : ""}{trend.value}%
                            </span>
                        )}
                        <span className="text-muted-foreground truncate">
                            {trend ? trend.label : description}
                        </span>
                    </div>
                )}
            </CardContent>
        </Card>
    );
};
