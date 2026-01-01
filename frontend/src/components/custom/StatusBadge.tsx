import React from "react";
import { cn } from "@/lib/utils";
import { Badge } from "../ui/badge";

export type StatusType =
  | "draft"
  | "published"
  | "live"
  | "completed"
  | "cancelled"
  | "issued"
  | "revoked"
  | "registered"
  | "attended";

interface StatusBadgeProps {
  status: StatusType | string;
  className?: string;
}

const statusConfig: Record<string, { label: string; variant: "default" | "secondary" | "destructive" | "outline"; className?: string }> = {
  draft: { label: "Draft", variant: "secondary", className: "bg-muted text-gray-700 hover:bg-gray-200 border-border" },
  published: { label: "Published", variant: "default", className: "bg-primary/10 text-primary hover:bg-primary/20 border-primary/20" },
  live: { label: "Live Now", variant: "default", className: "bg-destructive/10 text-destructive hover:bg-destructive/20 border-destructive/20 animate-pulse" },
  completed: { label: "Completed", variant: "outline", className: "text-muted-foreground border-border" },
  cancelled: { label: "Cancelled", variant: "destructive", className: "bg-destructive/5 text-destructive border-destructive/10 hover:bg-destructive/10" },
  issued: { label: "Issued", variant: "default", className: "bg-primary/15 text-primary hover:bg-primary/25 border-primary/20" },
  revoked: { label: "Revoked", variant: "destructive", className: "bg-destructive/10 text-destructive border-destructive/20" },
  registered: { label: "Registered", variant: "default", className: "bg-primary/5 text-primary border-primary/10" },
  attended: { label: "Attended", variant: "default", className: "bg-primary/10 text-primary border-primary/20" },
};

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const statusKey = status?.toLowerCase() || 'draft';
  const config = statusConfig[statusKey] || { label: status || 'Unknown', variant: "outline" as const };

  return (
    <Badge
      variant={config.variant}
      className={cn("font-medium shadow-none border", config.className, className)}
    >
      {config.label}
    </Badge>
  );
}
