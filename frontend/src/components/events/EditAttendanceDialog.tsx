
import React, { useState } from 'react';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Textarea } from "@/components/ui/textarea";
import { overrideAttendance } from '@/api/events';
import { toast } from 'sonner';

interface EditAttendanceDialogProps {
    isOpen: boolean;
    onOpenChange: (open: boolean) => void;
    attendee: any; // Using any for now to match parent component
    eventUuid: string;
    onSuccess: () => void;
}

export function EditAttendanceDialog({
    isOpen,
    onOpenChange,
    attendee,
    eventUuid,
    onSuccess
}: EditAttendanceDialogProps) {
    const [loading, setLoading] = useState(false);
    const [eligibility, setEligibility] = useState<string>(
        attendee?.attendance_eligible ? 'eligible' : 'not_eligible'
    );
    const [reason, setReason] = useState("");

    const handleSave = async () => {
        if (!attendee || !eventUuid) return;

        setLoading(true);
        try {
            const isEligible = eligibility === 'eligible';
            await overrideAttendance(eventUuid, attendee.uuid, isEligible, reason);
            toast.success("Attendance updated successfully");
            onSuccess();
            onOpenChange(false);
        } catch (error) {
            console.error("Failed to update attendance", error);
            toast.error("Failed to update attendance");
        } finally {
            setLoading(false);
        }
    };

    if (!attendee) return null;

    return (
        <Dialog open={isOpen} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                    <DialogTitle>Edit Attendance</DialogTitle>
                    <DialogDescription>
                        Manually override attendance eligibility for {attendee.full_name}.
                    </DialogDescription>
                </DialogHeader>

                <div className="grid gap-4 py-4">
                    <div className="space-y-2">
                        <Label>Certificate Eligibility</Label>
                        <RadioGroup value={eligibility} onValueChange={setEligibility}>
                            <div className="flex items-center space-x-2">
                                <RadioGroupItem value="eligible" id="r1" />
                                <Label htmlFor="r1">Eligible (Issue Certificate)</Label>
                            </div>
                            <div className="flex items-center space-x-2">
                                <RadioGroupItem value="not_eligible" id="r2" />
                                <Label htmlFor="r2">Not Eligible</Label>
                            </div>
                        </RadioGroup>
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="reason">Reason for Override</Label>
                        <Textarea
                            id="reason"
                            placeholder="e.g. Verified manually, Technical issues with zoom..."
                            value={reason}
                            onChange={(e) => setReason(e.target.value)}
                        />
                    </div>
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
                    <Button onClick={handleSave} disabled={loading}>
                        {loading ? "Saving..." : "Save Changes"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
