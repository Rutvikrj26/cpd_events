import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { PageHeader } from '@/components/ui/page-header';
import { EventWizard } from '@/components/events/wizard/EventWizard';
import { getEvent } from '@/api/events';
import { toast } from 'sonner';

export function EventCreatePage() {
    const { uuid } = useParams<{ uuid: string }>();
    const isEditMode = !!uuid;
    const [eventData, setEventData] = useState<any>(null);
    const [loading, setLoading] = useState(isEditMode);

    useEffect(() => {
        async function fetchEvent() {
            if (!uuid) return;
            try {
                const data = await getEvent(uuid);
                const durationMinutes = Number(data.duration_minutes || 0);
                let minimumAttendanceMinutes = Number(data.minimum_attendance_minutes || 0);

                if (!minimumAttendanceMinutes && data.minimum_attendance_percent && durationMinutes) {
                    minimumAttendanceMinutes = Math.ceil((Number(data.minimum_attendance_percent) / 100) * durationMinutes);
                }
                // Map API response fields to form field names
                setEventData({
                    ...data,
                    // Map aliased fields back to form field names
                    cpd_credit_value: data.cpd_credits,
                    cpd_credit_type: data.cpd_type,
                    // Map sessions to wizard internal state
                    _sessions: data.sessions || [],
                    // Explicitly set is_free based on price, as backend might not return is_free
                    is_free: !data.price || parseFloat(data.price.toString()) === 0,
                    minimum_attendance_minutes: minimumAttendanceMinutes,
                    minimum_attendance_percent: 0,
                });
            } catch (e) {
                console.error("Failed to fetch event", e);
                toast.error("Failed to load event details");
            } finally {
                setLoading(false);
            }
        }
        fetchEvent();
    }, [uuid]);

    if (loading) {
        return <div className="p-8">Loading event...</div>;
    }

    return (
        <div className="space-y-6">
            <PageHeader
                title={isEditMode ? "Edit Event" : "Create New Event"}
                description={isEditMode
                    ? "Update your event details, schedule, and settings."
                    : "Follow the steps to set up your event, schedule, and settings."
                }
            />

            <EventWizard initialData={eventData} isEditMode={isEditMode} />
        </div>
    );
}
