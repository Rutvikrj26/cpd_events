import * as React from "react";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { buttonVariants } from "@/components/ui/button";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog";

export interface ConfirmDialogProps {
    /** Whether the dialog is open */
    open: boolean;
    /** Callback when open state changes */
    onOpenChange: (open: boolean) => void;
    /** Dialog title */
    title: string;
    /** Dialog description / body */
    description: string | React.ReactNode;
    /** Label for the confirm button */
    confirmLabel?: string;
    /** Label for the cancel button */
    cancelLabel?: string;
    /** Variant for the confirm button */
    variant?: "default" | "destructive";
    /** Whether the action is in progress */
    isLoading?: boolean;
    /** Callback when confirmed */
    onConfirm: () => void | Promise<void>;
}

export function ConfirmDialog({
    open,
    onOpenChange,
    title,
    description,
    confirmLabel = "Confirm",
    cancelLabel = "Cancel",
    variant = "default",
    isLoading = false,
    onConfirm,
}: ConfirmDialogProps) {
    async function handleConfirm(e: React.MouseEvent) {
        e.preventDefault();
        await onConfirm();
    }

    return (
        <AlertDialog open={open} onOpenChange={onOpenChange}>
            <AlertDialogContent>
                <AlertDialogHeader>
                    <AlertDialogTitle>{title}</AlertDialogTitle>
                    <AlertDialogDescription asChild={typeof description !== "string"}>
                        {typeof description === "string" ? (
                            description
                        ) : (
                            <div className="text-sm text-muted-foreground">{description}</div>
                        )}
                    </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                    <AlertDialogCancel disabled={isLoading}>
                        {cancelLabel}
                    </AlertDialogCancel>
                    <AlertDialogAction
                        onClick={handleConfirm}
                        disabled={isLoading}
                        className={cn(
                            variant === "destructive" &&
                                buttonVariants({ variant: "destructive" })
                        )}
                    >
                        {isLoading && (
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        )}
                        {confirmLabel}
                    </AlertDialogAction>
                </AlertDialogFooter>
            </AlertDialogContent>
        </AlertDialog>
    );
}
