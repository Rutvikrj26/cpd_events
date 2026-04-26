import React, { useState } from 'react';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { toast } from 'sonner';
import { FlagReason } from '@/api/courses';

interface FlagDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onSubmit: (data: { reason: FlagReason; note: string }) => Promise<void>;
    targetLabel: string;
}

const REASONS: { value: FlagReason; label: string }[] = [
    { value: 'spam', label: 'Spam' },
    { value: 'harassment', label: 'Harassment' },
    { value: 'off_topic', label: 'Off-topic' },
    { value: 'other', label: 'Other' },
];

export function FlagDialog({ open, onOpenChange, onSubmit, targetLabel }: FlagDialogProps) {
    const [reason, setReason] = useState<FlagReason>('off_topic');
    const [note, setNote] = useState('');
    const [submitting, setSubmitting] = useState(false);

    const handleSubmit = async () => {
        setSubmitting(true);
        try {
            await onSubmit({ reason, note });
            toast.success('Flag submitted — staff will review.');
            onOpenChange(false);
            setNote('');
            setReason('off_topic');
        } catch (error) {
            toast.error('Failed to submit flag.');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Flag {targetLabel}</DialogTitle>
                    <DialogDescription>
                        Let staff know this content may violate community guidelines.
                    </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-2">
                    <div className="space-y-2">
                        <Label>Reason</Label>
                        <RadioGroup value={reason} onValueChange={(v) => setReason(v as FlagReason)}>
                            {REASONS.map((r) => (
                                <div key={r.value} className="flex items-center gap-2">
                                    <RadioGroupItem id={`reason-${r.value}`} value={r.value} />
                                    <Label htmlFor={`reason-${r.value}`} className="font-normal">
                                        {r.label}
                                    </Label>
                                </div>
                            ))}
                        </RadioGroup>
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="flag-note">Additional context (optional)</Label>
                        <Textarea
                            id="flag-note"
                            value={note}
                            onChange={(e) => setNote(e.target.value)}
                            placeholder="Anything else staff should know?"
                        />
                    </div>
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={submitting}>
                        Cancel
                    </Button>
                    <Button onClick={handleSubmit} disabled={submitting}>
                        Submit Flag
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
