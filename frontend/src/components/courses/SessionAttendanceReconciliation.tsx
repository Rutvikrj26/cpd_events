import React, { useState, useEffect, useCallback } from 'react';
import { RefreshCw, UserCheck, AlertTriangle, Clock, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { toast } from 'sonner';
import {
    getUnmatchedParticipants,
    matchParticipant,
    syncSessionAttendance,
    getCourseEnrollments,
    UnmatchedParticipant
} from '@/api/courses';

interface SessionAttendanceReconciliationProps {
    courseUuid: string;
    sessionUuid: string;
    onReconciled?: () => void;
}

export function SessionAttendanceReconciliation({ courseUuid, sessionUuid, onReconciled }: SessionAttendanceReconciliationProps) {
    const [unmatchedRecords, setUnmatchedRecords] = useState<UnmatchedParticipant[]>([]);
    const [enrollments, setEnrollments] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [syncing, setSyncing] = useState(false);
    const [matching, setMatching] = useState<string | null>(null);
    const [selectedMatches, setSelectedMatches] = useState<Record<string, string>>({});

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
            const msg = e?.response?.data?.error?.message || e?.message || 'Failed to load attendance records';
            toast.error(msg);
        } finally {
            setLoading(false);
        }
    }, [courseUuid, sessionUuid]);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    const handleSync = async () => {
        try {
            setSyncing(true);
            await syncSessionAttendance(courseUuid, sessionUuid);
            toast.success('Sync started. Check back in a few moments.');
            // Wait a bit then refresh
            setTimeout(fetchData, 3000);
        } catch (e: any) {
            toast.error('Failed to trigger sync');
        } finally {
            setSyncing(false);
        }
    };

    const handleMatch = async (record: UnmatchedParticipant, enrollmentUuid: string) => {
        if (!enrollmentUuid) {
            toast.error('Please select an enrollment to match');
            return;
        }

        try {
            setMatching(record.user_id); // Use user_id as key, or some unique id from unmatched? 
            // unmatched participant usually has id, or we use index? 
            // API returns user_id from zoom, which is unique per meeting usually.

            await matchParticipant(courseUuid, sessionUuid, {
                enrollment_uuid: enrollmentUuid,
                zoom_user_email: record.user_email,
                zoom_user_name: record.user_name,
                zoom_join_time: record.join_time,
                attendance_minutes: record.duration_minutes
            });

            toast.success('Attendance matched successfully');

            // Remove from unmatched list
            setUnmatchedRecords(prev => prev.filter(r => r.user_id !== record.user_id));
            setSelectedMatches(prev => {
                const copy = { ...prev };
                delete copy[record.user_id];
                return copy;
            });

            onReconciled?.();
        } catch (e: any) {
            console.error('Failed to match attendance', e);
            toast.error(e?.response?.data?.error?.message || 'Failed to match attendance');
        } finally {
            setMatching(null);
        }
    };

    if (loading) {
        return (
            <Card className="w-full">
                <CardContent className="py-8 text-center">
                    <RefreshCw className="h-6 w-6 animate-spin mx-auto mb-2 text-muted-foreground" />
                    <p className="text-sm text-muted-foreground">Loading unmatched participants...</p>
                </CardContent>
            </Card>
        );
    }

    if (unmatchedRecords.length === 0) {
        return (
            <Card className="w-full border-green-200 bg-green-50/50 dark:bg-green-950/20 dark:border-green-900">
                <CardContent className="py-6">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="p-2 rounded-full bg-green-100 dark:bg-green-900/50">
                                <UserCheck className="h-5 w-5 text-green-600 dark:text-green-400" />
                            </div>
                            <div>
                                <p className="font-medium text-green-700 dark:text-green-300">All Attendance Matched</p>
                                <p className="text-sm text-green-600 dark:text-green-400">
                                    No unmatched Zoom participants found.
                                </p>
                            </div>
                        </div>
                        <Button variant="outline" size="sm" onClick={handleSync} disabled={syncing}>
                            <RefreshCw className={`h-4 w-4 mr-1 ${syncing ? 'animate-spin' : ''}`} />
                            Sync Now
                        </Button>
                    </div>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card className="w-full">
            <CardHeader>
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <AlertTriangle className="h-5 w-5 text-amber-500" />
                        <div>
                            <CardTitle className="text-base">Unmatched Participants</CardTitle>
                            <CardDescription>
                                {unmatchedRecords.length} Zoom participant{unmatchedRecords.length !== 1 ? 's' : ''} not linked to enrollment
                            </CardDescription>
                        </div>
                    </div>
                    <div className="flex gap-2">
                        <Button variant="outline" size="sm" onClick={handleSync} disabled={syncing}>
                            <RefreshCw className={`h-4 w-4 mr-1 ${syncing ? 'animate-spin' : ''}`} />
                            Sync Now
                        </Button>
                        <Button variant="outline" size="sm" onClick={fetchData} disabled={loading}>
                            <RefreshCw className={`h-4 w-4 mr-1 ${loading ? 'animate-spin' : ''}`} />
                            Refresh
                        </Button>
                    </div>
                </div>
            </CardHeader>
            <CardContent className="space-y-4">
                {unmatchedRecords.map((record) => (
                    <div
                        key={record.user_id || record.join_time} // Fallback key
                        className="border rounded-lg p-4 bg-card hover:bg-accent/20 transition-colors"
                    >
                        <div className="flex flex-col md:flex-row md:items-start gap-4">
                            {/* Zoom Participant Info */}
                            <div className="flex-1 space-y-2">
                                <div className="flex items-center gap-2">
                                    <span className="font-medium">{record.user_name || 'Unknown Participant'}</span>
                                    {record.user_email && (
                                        <span className="text-sm text-muted-foreground">({record.user_email})</span>
                                    )}
                                </div>
                                <div className="flex items-center gap-4 text-xs text-muted-foreground">
                                    <span className="flex items-center gap-1">
                                        <Clock className="h-3 w-3" />
                                        {record.duration_minutes} min
                                    </span>
                                    <span>
                                        Joined: {new Date(record.join_time).toLocaleString()}
                                    </span>
                                </div>
                            </div>

                            {/* Match Controls */}
                            <div className="flex items-center gap-2 min-w-[280px]">
                                <Select
                                    value={selectedMatches[record.user_id] || ''}
                                    onValueChange={(value) => setSelectedMatches(prev => ({ ...prev, [record.user_id]: value }))}
                                >
                                    <SelectTrigger className="w-full">
                                        <SelectValue placeholder="Select student..." />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {enrollments.map((reg) => (
                                            <SelectItem key={reg.uuid} value={reg.uuid}>
                                                {reg.user_name || reg.user?.full_name} ({reg.user_email || reg.user?.email})
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                                <Button
                                    size="sm"
                                    onClick={() => handleMatch(record, selectedMatches[record.user_id])}
                                    disabled={!selectedMatches[record.user_id] || matching === record.user_id}
                                >
                                    {matching === record.user_id ? (
                                        <RefreshCw className="h-4 w-4 animate-spin" />
                                    ) : (
                                        <UserCheck className="h-4 w-4" />
                                    )}
                                </Button>
                            </div>
                        </div>
                    </div>
                ))}
            </CardContent>
        </Card>
    );
}
