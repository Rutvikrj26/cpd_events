import React, { useState, useEffect, useCallback } from 'react';
import {
    getUnmatchedParticipants,
    matchParticipant,
    getCourseEnrollments
} from '@/api/courses';
import { AttendanceReconciliation as GenericAttendanceReconciliation } from '../common/AttendanceReconciliation';

interface SessionAttendanceReconciliationProps {
    courseUuid: string;
    sessionUuid: string;
    onReconciled?: () => void;
}

export function SessionAttendanceReconciliation({ courseUuid, sessionUuid, onReconciled }: SessionAttendanceReconciliationProps) {
    const [unmatchedRecords, setUnmatchedRecords] = useState<any[]>([]);
    const [enrollments, setEnrollments] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchData = useCallback(async () => {
        try {
            setLoading(true);
            const [unmatched, enr] = await Promise.all([
                getUnmatchedParticipants(courseUuid, sessionUuid),
                getCourseEnrollments(courseUuid),
            ]);
            setUnmatchedRecords(unmatched);
            setEnrollments(enr.filter((r: any) => r.status === 'active' || r.status === 'completed'));
        } catch (e: any) {
            console.error('Failed to fetch reconciliation data', e);
        } finally {
            setLoading(false);
        }
    }, [courseUuid, sessionUuid]);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    const handleMatch = async (record: any, enrollmentUuid: string) => {
        await matchParticipant(courseUuid, sessionUuid, {
            enrollment_uuid: enrollmentUuid,
            zoom_user_email: record.user_email,
            zoom_user_name: record.user_name,
            zoom_join_time: record.join_time,
            attendance_minutes: record.duration_minutes
        });
        setUnmatchedRecords(prev => prev.filter(r => r.user_id !== record.user_id));
        onReconciled?.();
    };

    return (
        <GenericAttendanceReconciliation
            title="Session Unmatched Participants"
            unmatchedParticipants={unmatchedRecords}
            enrollments={enrollments}
            loading={loading}
            onRefresh={fetchData}
            onMatch={handleMatch}
            onReconciled={onReconciled}
        />
    );
}
