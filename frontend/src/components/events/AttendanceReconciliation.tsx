import React, { useState, useEffect, useCallback } from 'react';
import {
    getUnmatchedParticipants,
    matchParticipant,
    getEventRegistrations
} from '@/api/events';
import { AttendanceReconciliation as GenericAttendanceReconciliation } from '../common/AttendanceReconciliation';

interface AttendanceReconciliationProps {
    eventUuid: string;
    onReconciled?: () => void;
}

export function AttendanceReconciliation({ eventUuid, onReconciled }: AttendanceReconciliationProps) {
    const [unmatchedRecords, setUnmatchedRecords] = useState<any[]>([]);
    const [registrations, setRegistrations] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchData = useCallback(async () => {
        try {
            setLoading(true);
            const [unmatched, regs] = await Promise.all([
                getUnmatchedParticipants(eventUuid),
                getEventRegistrations(eventUuid),
            ]);
            setUnmatchedRecords(unmatched);
            setRegistrations(regs.filter((r: any) => r.status === 'confirmed' || r.status === 'waitlisted' || r.status === 'attended'));
        } catch (e: any) {
            console.error('Failed to fetch reconciliation data', e);
        } finally {
            setLoading(false);
        }
    }, [eventUuid]);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    const handleMatch = async (record: any, registrationUuid: string) => {
        await matchParticipant(eventUuid, {
            registration_uuid: registrationUuid,
            participant_email: record.user_email,
            participant_name: record.user_name,
            join_time: record.join_time,
            attendance_minutes: record.duration_minutes
        });
        setUnmatchedRecords(prev => prev.filter(r => r.user_id !== record.user_id));
        onReconciled?.();
    };

    return (
        <GenericAttendanceReconciliation
            title="Event Unmatched Participants"
            unmatchedParticipants={unmatchedRecords}
            enrollments={registrations}
            loading={loading}
            onRefresh={fetchData}
            onMatch={handleMatch}
            onReconciled={onReconciled}
        />
    );
}
