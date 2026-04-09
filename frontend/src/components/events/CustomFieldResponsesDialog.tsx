import { useState, useEffect } from "react";
import { Loader2 } from "lucide-react";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
} from "@/components/ui/dialog";
import { getRegistrationDetail } from "@/api/events";

interface CustomFieldResponse {
    uuid?: string;
    field_label: string;
    field_type?: string;
    value: any;
}

interface CustomFieldResponsesDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    attendeeName: string;
    /** Custom field responses already available on the registration object */
    responses?: CustomFieldResponse[];
    /** If responses are not provided, fetch them from the API using these */
    eventUuid?: string;
    registrationUuid?: string;
}

function formatValue(response: CustomFieldResponse): string {
    if (response.value === null || response.value === undefined || response.value === "") {
        return "";
    }
    if (response.field_type === "checkbox") {
        return response.value === true || response.value === "true" ? "Yes" : "No";
    }
    if (typeof response.value === "object") {
        return JSON.stringify(response.value);
    }
    return String(response.value);
}

export function CustomFieldResponsesDialog({
    open,
    onOpenChange,
    attendeeName,
    responses: propResponses,
    eventUuid,
    registrationUuid,
}: CustomFieldResponsesDialogProps) {
    const [loading, setLoading] = useState(false);
    const [fetchedResponses, setFetchedResponses] = useState<CustomFieldResponse[]>([]);
    const [error, setError] = useState<string | null>(null);

    const needsFetch = !propResponses && eventUuid && registrationUuid;
    const responses = propResponses || fetchedResponses;

    useEffect(() => {
        if (!open || !needsFetch) return;

        const fetchResponses = async () => {
            setLoading(true);
            setError(null);
            try {
                const detail = await getRegistrationDetail(eventUuid!, registrationUuid!);
                setFetchedResponses(detail.custom_field_responses || []);
            } catch (err) {
                console.error("Failed to fetch custom field responses", err);
                setError("Failed to load custom field responses.");
            } finally {
                setLoading(false);
            }
        };

        fetchResponses();
    }, [open, needsFetch, eventUuid, registrationUuid]);

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-md">
                <DialogHeader>
                    <DialogTitle>Custom Field Responses</DialogTitle>
                    <DialogDescription>
                        Responses from {attendeeName}
                    </DialogDescription>
                </DialogHeader>
                {loading ? (
                    <div className="flex items-center justify-center py-8">
                        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                        <span className="ml-2 text-sm text-muted-foreground">Loading...</span>
                    </div>
                ) : error ? (
                    <p className="text-sm text-destructive py-4">{error}</p>
                ) : responses.length === 0 ? (
                    <p className="text-sm text-muted-foreground py-4 text-center">
                        No custom field responses.
                    </p>
                ) : (
                    <div className="space-y-3 py-2">
                        {responses.map((r, i) => (
                            <div key={r.uuid || i} className="space-y-1">
                                <p className="text-sm font-medium text-foreground">
                                    {r.field_label}
                                </p>
                                <p className="text-sm text-muted-foreground bg-muted/50 rounded px-3 py-2">
                                    {formatValue(r) || <span className="italic">No response</span>}
                                </p>
                            </div>
                        ))}
                    </div>
                )}
            </DialogContent>
        </Dialog>
    );
}
