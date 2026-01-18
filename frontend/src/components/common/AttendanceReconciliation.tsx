import React, { useState, useEffect, useCallback } from 'react';
import { RefreshCw, UserCheck, AlertTriangle, Clock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { toast } from 'sonner';

export interface UnmatchedParticipant {
    user_id: string;
    user_name: string;
    user_email: string;
    join_time: string;
    leave_time?: string;
    duration_minutes: number;
}

interface AttendanceReconciliationProps {
    title?: string;
    description?: string;
    unmatchedParticipants: UnmatchedParticipant[];
    enrollments: any[];
    loading?: boolean;
    onRefresh: () => Promise<void>;
    onMatch: (record: UnmatchedParticipant, enrollmentUuid: string) => Promise<void>;
    onReconciled?: () => void;
}

export function AttendanceReconciliation({
    title = "Unmatched Participants",
    description,
    unmatchedParticipants,
    enrollments,
    loading = false,
    onRefresh,
    onMatch,
    onReconciled
}: AttendanceReconciliationProps) {
    const [matching, setMatching] = useState<string | null>(null);
    const [selectedMatches, setSelectedMatches] = useState<Record<string, string>>({});

    const handleMatch = async (record: UnmatchedParticipant, enrollmentUuid: string) => {
        if (!enrollmentUuid) {
            toast.error('Please select a registration to match');
            return;
        }

        try {
            setMatching(record.user_id);
            await onMatch(record, enrollmentUuid);
            toast.success('Attendance matched successfully');

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

    if (unmatchedParticipants.length === 0) {
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
                        <Button variant="outline" size="sm" onClick={onRefresh} disabled={loading}>
                            <RefreshCw className={`h-4 w-4 mr-1 ${loading ? 'animate-spin' : ''}`} />
                            Refresh
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
                            <CardTitle className="text-base">{title}</CardTitle>
                            <CardDescription>
                                {description || `${unmatchedParticipants.length} Zoom participant${unmatchedParticipants.length !== 1 ? 's' : ''} not linked to registration`}
                            </CardDescription>
                        </div>
                    </div>
                    <Button variant="outline" size="sm" onClick={onRefresh} disabled={loading}>
                        <RefreshCw className={`h-4 w-4 mr-1 ${loading ? 'animate-spin' : ''}`} />
                        Refresh
                    </Button>
                </div>
            </CardHeader>
            <CardContent className="space-y-4">
                {unmatchedParticipants.map((record) => (
                    <div
                        key={record.user_id || record.join_time}
                        className="border rounded-lg p-4 bg-card hover:bg-accent/20 transition-colors"
                    >
                        <div className="flex flex-col md:flex-row md:items-start gap-4">
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

                            <div className="flex items-center gap-2 min-w-[320px]">
                                <Select
                                    value={selectedMatches[record.user_id] || ''}
                                    onValueChange={(value) => setSelectedMatches(prev => ({ ...prev, [record.user_id]: value }))}
                                >
                                    <SelectTrigger className="w-full">
                                        <SelectValue placeholder="Select registrant..." />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {enrollments.map((reg) => (
                                            <SelectItem key={reg.uuid} value={reg.uuid}>
                                                {reg.full_name || reg.user_name || reg.user?.full_name} ({reg.email || reg.user_email || reg.user?.email})
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
