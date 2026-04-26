import * as React from "react";
import { Link } from "react-router-dom";
import { Button } from "@/shared/ui/button";

/**
 * SectionHeader — heading row above a section list (Up next, Recently
 * earned, Recent activity). Optional "View all" link on the right.
 */

interface SectionHeaderProps {
    title: React.ReactNode;
    link?: { to: string; label: React.ReactNode };
}

export function SectionHeader({ title, link }: SectionHeaderProps) {
    return (
        <div className="flex items-end justify-between">
            <h2 className="text-h2 text-foreground">{title}</h2>
            {link && (
                <Button
                    variant="link"
                    asChild
                    className="h-auto p-0 text-body font-medium text-primary"
                >
                    <Link to={link.to}>{link.label}</Link>
                </Button>
            )}
        </div>
    );
}

export type { SectionHeaderProps };
