import { CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface FormFieldSuccessProps {
    show: boolean;
    message?: string;
    className?: string;
}

/**
 * Success indicator for form fields
 * Shows a checkmark icon and optional message when validation passes
 */
export function FormFieldSuccess({ show, message, className }: FormFieldSuccessProps) {
    if (!show) return null;

    return (
        <div className={cn("flex items-center gap-1.5 text-sm text-success mt-1", className)}>
            <CheckCircle2 className="h-4 w-4" />
            {message && <span>{message}</span>}
        </div>
    );
}
