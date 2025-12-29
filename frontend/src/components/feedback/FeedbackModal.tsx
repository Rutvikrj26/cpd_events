import React from 'react';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import { FeedbackForm } from './FeedbackForm';
import { EventFeedback } from '@/api/feedback/types';

interface FeedbackModalProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    eventUuid: string;
    registrationUuid: string;
    eventTitle: string;
    existingFeedback?: EventFeedback | null;
    onSuccess?: (feedback: EventFeedback) => void;
}

export function FeedbackModal({
    open,
    onOpenChange,
    eventUuid,
    registrationUuid,
    eventTitle,
    existingFeedback,
    onSuccess
}: FeedbackModalProps) {
    const handleSuccess = (feedback: EventFeedback) => {
        onSuccess?.(feedback);
        onOpenChange(false);
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>
                        {existingFeedback ? 'Update Your Feedback' : 'Share Your Feedback'}
                    </DialogTitle>
                    <DialogDescription>
                        {existingFeedback
                            ? `Update your feedback for "${eventTitle}"`
                            : `Help us improve by rating your experience at "${eventTitle}"`
                        }
                    </DialogDescription>
                </DialogHeader>
                <FeedbackForm
                    eventUuid={eventUuid}
                    registrationUuid={registrationUuid}
                    eventTitle={eventTitle}
                    existingFeedback={existingFeedback}
                    onSuccess={handleSuccess}
                    onCancel={() => onOpenChange(false)}
                    compact
                />
            </DialogContent>
        </Dialog>
    );
}
