import React from 'react';
import { MessageSquare } from 'lucide-react';
import { FeedbackCard, FeedbackSummary } from '@/components/feedback';
import { calculateFeedbackSummary } from '@/api/feedback';
import { useEventFeedbackList } from '../../hooks';

interface EventFeedbackTabProps {
    eventUuid: string;
}

export function EventFeedbackTab({ eventUuid }: EventFeedbackTabProps) {
    const { data: feedback = [], isLoading } = useEventFeedbackList(eventUuid);
    const feedbackSummary = calculateFeedbackSummary(feedback);

    if (isLoading) {
        return (
            <div className="text-center py-8 text-muted-foreground">
                Loading feedback...
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <FeedbackSummary summary={feedbackSummary} />

            {feedback.length > 0 && (
                <div className="space-y-4">
                    <h3 className="text-lg font-semibold flex items-center gap-2">
                        <MessageSquare className="h-5 w-5" />
                        All Responses
                    </h3>
                    <div className="grid gap-4">
                        {feedback.map((fb) => (
                            <FeedbackCard key={fb.uuid} feedback={fb} />
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
