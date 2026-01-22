import React from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { LucideIcon } from "lucide-react";

export interface QuickAction {
    to: string;
    icon: LucideIcon;
    label: string;
    description: string;
}

interface QuickActionsProps {
    actions: QuickAction[];
}

export function QuickActionsCard({ actions }: QuickActionsProps) {
    return (
        <div className="grid grid-cols-1 gap-2">
            {actions.map((action) => {
                const Icon = action.icon;
                return (
                    <Button key={action.to} variant="outline" className="justify-start h-auto py-3 px-4" asChild>
                        <Link to={action.to}>
                            <div className="bg-primary/10 p-2 rounded-md mr-3">
                                <Icon className="h-4 w-4 text-primary" />
                            </div>
                            <div className="text-left">
                                <span className="font-semibold block">{action.label}</span>
                                <span className="text-xs text-muted-foreground">{action.description}</span>
                            </div>
                        </Link>
                    </Button>
                );
            })}
        </div>
    );
}
