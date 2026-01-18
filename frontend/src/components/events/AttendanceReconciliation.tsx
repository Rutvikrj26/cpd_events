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
import { getUnmatchedAttendance, matchAttendance, getEventRegistrations, UnmatchedAttendanceRecord, MatchSuggestion } from '@/api/events';

interface AttendanceReconciliationProps {
    eventUuid: string;
    onReconciled?: () => void;
}

export function AttendanceReconciliation({ eventUuid, onReconciled }: AttendanceReconciliationProps) {
    const [unmatchedRecords, setUnmatchedRecords] = useState<UnmatchedAttendanceRecord[]>([]);
    const [registrations, setRegistrations] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [matching, setMatching] = useState<string | null>(null);
    const [selectedMatches, setSelectedMatches] = useState<Record<string, string>>({});

    const fetchData = useCallback(async () => {
        try {
            setLoading(true);
            const [unmatched, regs] = await Promise.all([
                getUnmatchedAttendance(eventUuid),
                getEventRegistrations(eventUuid),
            ]);
            setUnmatchedRecords(unmatched);
            setRegistrations(regs.filter((r: any) => r.status === 'confirmed' || r.status === 'waitlisted'));
        } catch (e) {
            console.error('Failed to fetch reconciliation data', e);
            toast.error('Failed to load attendance records');
        } finally {
            setLoading(false);
        }
    }, [eventUuid]);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    const handleMatch = async (recordUuid: string, registrationUuid: string) => {
        if (!registrationUuid) {
            toast.error('Please select a registration to match');
            return;
        }

        try {
            setMatching(recordUuid);
            await matchAttendance(eventUuid, recordUuid, registrationUuid);
            toast.success('Attendance matched successfully');

            // Remove from unmatched list
            setUnmatchedRecords(prev => prev.filter(r => r.uuid !== recordUuid));
            setSelectedMatches(prev => {
                const copy = { ...prev };
                delete copy[recordUuid];
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

    const getConfidenceBadgeColor = (confidence: number) => {
        if (confidence >= 80) return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400';
        if (confidence >= 60) return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400';
        return 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400';
    };

    if (loading) {
        return (
            <Card className="w-full">
                <CardContent className="py-8 text-center">
                    <RefreshCw className="h-6 w-6 animate-spin mx-auto mb-2 text-muted-foreground" />
                    <p className="text-sm text-muted-foreground">Loading unmatched attendance...</p>
                </CardContent>
            </Card>
        );
    }

    if (unmatchedRecords.length === 0) {
        return (
            <Card className="w-full border-green-200 bg-green-50/50 dark:bg-green-950/20 dark:border-green-900">
                <CardContent className="py-6">
                    <div className="flex items-center gap-3">
                        <div className="p-2 rounded-full bg-green-100 dark:bg-green-900/50">
                            <UserCheck className="h-5 w-5 text-green-600 dark:text-green-400" />
                        </div>
                        <div>
                            <p className="font-medium text-green-700 dark:text-green-300">All Attendance Matched</p>
                            <p className="text-sm text-green-600 dark:text-green-400">
                                No unmatched Zoom attendance records found.
                            </p>
                        </div>
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
                            <CardTitle className="text-base">Unmatched Attendance</CardTitle>
                            <CardDescription>
                                {unmatchedRecords.length} Zoom participant{unmatchedRecords.length !== 1 ? 's' : ''} not automatically matched
                            </CardDescription>
                        </div>
                    </div>
                    <Button variant="outline" size="sm" onClick={fetchData} disabled={loading}>
                        <RefreshCw className={`h-4 w-4 mr-1 ${loading ? 'animate-spin' : ''}`} />
                        Refresh
                    </Button>
                </div>
            </CardHeader>
            <CardContent className="space-y-4">
                {unmatchedRecords.map((record) => (
                    <div
                        key={record.uuid}
                        className="border rounded-lg p-4 bg-card hover:bg-accent/20 transition-colors"
                    >
                        <div className="flex flex-col md:flex-row md:items-start gap-4">
                            {/* Zoom Participant Info */}
                            <div className="flex-1 space-y-2">
                                <div className="flex items-center gap-2">
                                    <span className="font-medium">{record.zoom_user_name || 'Unknown Participant'}</span>
                                    {record.zoom_user_email && (
                                        <span className="text-sm text-muted-foreground">({record.zoom_user_email})</span>
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
                                    {record.device_type && <span>Device: {record.device_type}</span>}
                                </div>

                                {/* Match Suggestions */}
                                {record.match_suggestions.length > 0 && (
                                    <div className="mt-2 pt-2 border-t">
                                        <p className="text-xs font-medium text-muted-foreground mb-1">Suggested Matches:</p>
                                        <div className="flex flex-wrap gap-1">
                                            {record.match_suggestions.map((suggestion) => (
                                                <Badge
                                                    key={suggestion.uuid}
                                                    variant="outline"
                                                    className={`cursor-pointer ${getConfidenceBadgeColor(suggestion.confidence)} ${selectedMatches[record.uuid] === suggestion.uuid ? 'ring-2 ring-primary' : ''
                                                        }`}
                                                    onClick={() => setSelectedMatches(prev => ({ ...prev, [record.uuid]: suggestion.uuid }))}
                                                >
                                                    {suggestion.full_name} ({suggestion.confidence}%)
                                                </Badge>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* Match Controls */}
                            <div className="flex items-center gap-2 min-w-[280px]">
                                <Select
                                    value={selectedMatches[record.uuid] || ''}
                                    onValueChange={(value) => setSelectedMatches(prev => ({ ...prev, [record.uuid]: value }))}
                                >
                                    <SelectTrigger className="w-full">
                                        <SelectValue placeholder="Select registration..." />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {registrations.map((reg) => (
                                            <SelectItem key={reg.uuid} value={reg.uuid}>
                                                {reg.full_name} ({reg.email})
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                                <Button
                                    size="sm"
                                    onClick={() => handleMatch(record.uuid, selectedMatches[record.uuid])}
                                    disabled={!selectedMatches[record.uuid] || matching === record.uuid}
                                >
                                    {matching === record.uuid ? (
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
