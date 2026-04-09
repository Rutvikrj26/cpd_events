import * as React from "react";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

export interface FormDialogProps {
    /** Whether the dialog is open */
    open: boolean;
    /** Callback when open state changes */
    onOpenChange: (open: boolean) => void;
    /** Dialog title */
    title: string;
    /** Optional description below the title */
    description?: string;
    /** Form content (fields) */
    children: React.ReactNode;
    /** Submit handler */
    onSubmit: (e: React.FormEvent) => void | Promise<void>;
    /** Label for the submit button */
    submitLabel?: string;
    /** Label for the cancel button */
    cancelLabel?: string;
    /** Whether the form is submitting */
    isLoading?: boolean;
    /** Whether submit is disabled (beyond loading state) */
    submitDisabled?: boolean;
    /** Submit button variant */
    submitVariant?: "default" | "destructive" | "outline" | "secondary";
    /** Optional className for DialogContent */
    contentClassName?: string;
}

export function FormDialog({
    open,
    onOpenChange,
    title,
    description,
    children,
    onSubmit,
    submitLabel = "Save",
    cancelLabel = "Cancel",
    isLoading = false,
    submitDisabled = false,
    submitVariant = "default",
    contentClassName,
}: FormDialogProps) {
    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className={cn("sm:max-w-lg", contentClassName)}>
                <form onSubmit={onSubmit}>
                    <DialogHeader>
                        <DialogTitle>{title}</DialogTitle>
                        {description && (
                            <DialogDescription>{description}</DialogDescription>
                        )}
                    </DialogHeader>
                    <div className="py-4 space-y-4">{children}</div>
                    <DialogFooter>
                        <Button
                            type="button"
                            variant="outline"
                            onClick={() => onOpenChange(false)}
                            disabled={isLoading}
                        >
                            {cancelLabel}
                        </Button>
                        <Button
                            type="submit"
                            variant={submitVariant}
                            disabled={isLoading || submitDisabled}
                        >
                            {isLoading && (
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            )}
                            {submitLabel}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
