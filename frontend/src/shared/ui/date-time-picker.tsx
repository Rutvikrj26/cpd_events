import * as React from "react";
import { cn } from "@/lib/utils";
import { Label } from "./label";

export interface DateTimePickerProps {
    label?: string;
    value?: string;
    onDateTimeChange?: (value: string) => void;
    className?: string;
    disabled?: boolean;
}

/**
 * DateTimePicker component using native datetime-local input.
 * Accepts and returns ISO 8601 strings.
 */
export const DateTimePicker = React.forwardRef<HTMLInputElement, DateTimePickerProps>(
    ({ label, value, onDateTimeChange, className, disabled }, ref) => {
        // Convert ISO string to datetime-local format (YYYY-MM-DDTHH:MM)
        const formatForInput = (isoString?: string): string => {
            if (!isoString) return "";
            try {
                const date = new Date(isoString);
                if (isNaN(date.getTime())) return "";
                // Convert to local time for display
                const year = date.getFullYear();
                const month = String(date.getMonth() + 1).padStart(2, "0");
                const day = String(date.getDate()).padStart(2, "0");
                const hours = String(date.getHours()).padStart(2, "0");
                const minutes = String(date.getMinutes()).padStart(2, "0");
                return `${year}-${month}-${day}T${hours}:${minutes}`;
            } catch {
                return "";
            }
        };

        // Convert datetime-local format to ISO string
        const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
            const localValue = e.target.value;
            if (!localValue) {
                onDateTimeChange?.("");
                return;
            }
            // Parse as local time and convert to ISO
            const date = new Date(localValue);
            if (!isNaN(date.getTime())) {
                onDateTimeChange?.(date.toISOString());
            }
        };

        return (
            <div className={cn("space-y-2", className)}>
                {label && <Label>{label}</Label>}
                <input
                    ref={ref}
                    type="datetime-local"
                    value={formatForInput(value)}
                    onChange={handleChange}
                    disabled={disabled}
                    className={cn(
                        "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background",
                        "file:border-0 file:bg-transparent file:text-sm file:font-medium",
                        "placeholder:text-muted-foreground",
                        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                        "disabled:cursor-not-allowed disabled:opacity-50"
                    )}
                />
            </div>
        );
    }
);

DateTimePicker.displayName = "DateTimePicker";
