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
  draft: { label: "Draft", variant: "secondary", className: "bg-gray-100 text-gray-700 hover:bg-gray-200 border-gray-200" },
  published: { label: "Published", variant: "default", className: "bg-blue-100 text-blue-700 hover:bg-blue-200 border-blue-200" },
  live: { label: "Live Now", variant: "default", className: "bg-red-100 text-red-700 hover:bg-red-200 border-red-200 animate-pulse" },
  completed: { label: "Completed", variant: "outline", className: "text-gray-600 border-gray-300" },
  cancelled: { label: "Cancelled", variant: "destructive", className: "bg-red-50 text-red-600 border-red-200 hover:bg-red-100" },
  issued: { label: "Issued", variant: "default", className: "bg-green-100 text-green-700 hover:bg-green-200 border-green-200" },
  revoked: { label: "Revoked", variant: "destructive", className: "bg-red-50 text-red-600 border-red-200" },
  registered: { label: "Registered", variant: "default", className: "bg-green-50 text-green-700 border-green-200" },
  attended: { label: "Attended", variant: "default", className: "bg-blue-50 text-blue-700 border-blue-200" },
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
