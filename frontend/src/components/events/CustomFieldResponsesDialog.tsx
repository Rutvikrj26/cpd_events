import { useState, useEffect } from "react";
import { Loader2 } from "lucide-react";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
} from "@/components/ui/dialog";

interface CustomFieldResponse {
    field_label: string;
    value: string;
}

interface CustomFieldResponsesDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    attendeeName: string;
    /** Custom field responses already available on the registration object */
    responses: CustomFieldResponse[];
}

export function CustomFieldResponsesDialog({
    open,
    onOpenChange,
    attendeeName,
    responses,
}: CustomFieldResponsesDialogProps) {
    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-md">
                <DialogHeader>
                    <DialogTitle>Custom Field Responses</DialogTitle>
                    <DialogDescription>
                        Responses from {attendeeName}
                    </DialogDescription>
                </DialogHeader>
                {responses.length === 0 ? (
                    <p className="text-sm text-muted-foreground py-4 text-center">
                        No custom field responses.
                    </p>
                ) : (
                    <div className="space-y-3 py-2">
                        {responses.map((r, i) => (
                            <div key={i} className="space-y-1">
                                <p className="text-sm font-medium text-foreground">
                                    {r.field_label}
                                </p>
                                <p className="text-sm text-muted-foreground bg-muted/50 rounded px-3 py-2">
                                    {r.value || <span className="italic">No response</span>}
                                </p>
                            </div>
                        ))}
                    </div>
                )}
            </DialogContent>
        </Dialog>
    );
}
