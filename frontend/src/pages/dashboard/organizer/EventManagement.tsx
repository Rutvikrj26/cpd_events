import React from 'react';
import { useParams } from 'react-router-dom';
import {
    useEvent,
    useEventAttendees,
    useEventFeedbackList,
    EventManagementHeader,
    EventManagementTabs,
} from '@/features/events';
import { DashboardSkeleton } from '@/features/dashboard';
import { calculateFeedbackSummary } from '@/api/feedback';

export function EventManagement() {
    const { uuid } = useParams<{ uuid: string }>();
    const { data: event, isLoading } = useEvent(uuid);
    const { data: attendees = [] } = useEventAttendees(uuid);
    const { data: feedback = [] } = useEventFeedbackList(uuid);

    if (isLoading || !event) {
        return <DashboardSkeleton />;
    }

    const now = new Date();
    const hasStarted = new Date(event.starts_at) < now;
    const hasEnded = event.ends_at ? new Date(event.ends_at) < now : false;
    const isTerminalStatus = ['completed', 'cancelled', 'closed'].includes(event.status);
    const isLive = hasStarted && !hasEnded && !isTerminalStatus && event.format !== 'in-person';
    const isEventHost = !!event.is_current_user_host;

    const feedbackSummary = calculateFeedbackSummary(feedback as any[]);
    const primaryRating = feedbackSummary.per_field.find((f) => f.field_type === 'rating');

    const stats = {
        registered: (attendees as any[]).filter((a) => a.status !== 'cancelled').length,
        checkedIn: (attendees as any[]).filter((a) => a.attended).length,
        issued: (attendees as any[]).filter((a) => a.certificate_uuid).length,
        feedbackCount: (feedback as any[]).length,
        avgRating: primaryRating?.average ?? 0,
    };

    return (
        <div className="space-y-8">
            <EventManagementHeader
                event={event}
                stats={stats}
                isLive={isLive}
                hasStarted={hasStarted}
            />
            <EventManagementTabs event={event} isEventHost={isEventHost} />
        </div>
    );
}
