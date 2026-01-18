import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { getAttendanceStats, AttendanceStats as AttendanceStatsType } from '@/api/courses';
import { Loader2, Users } from 'lucide-react';

interface AttendanceStatsProps {
    courseUuid: string;
}

export function AttendanceStats({ courseUuid }: AttendanceStatsProps) {
    const [stats, setStats] = useState<AttendanceStatsType | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function fetchStats() {
            try {
                const data = await getAttendanceStats(courseUuid);
                setStats(data);
            } catch (error) {
                console.error("Failed to fetch attendance stats", error);
            } finally {
                setLoading(false);
            }
        }
        fetchStats();
    }, [courseUuid]);

    if (loading) {
        return <div className="p-4 flex justify-center"><Loader2 className="animate-spin text-muted-foreground" /></div>;
    }

    if (!stats || stats.total_sessions === 0) {
        return null;
    }

    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <Users className="h-5 w-5" />
                    Session Attendance
                </CardTitle>
            </CardHeader>
            <CardContent>
                <div className="mb-6 grid grid-cols-2 gap-4">
                    <div className="bg-muted/30 p-3 rounded-md">
                        <p className="text-sm text-muted-foreground">Avg. Attendance</p>
                        <p className="text-xl font-bold">{stats.average_attendance_rate}%</p>
                    </div>
                    <div className="bg-muted/30 p-3 rounded-md">
                        <p className="text-sm text-muted-foreground">Total Sessions</p>
                        <p className="text-xl font-bold">{stats.total_sessions}</p>
                    </div>
                </div>

                <div className="space-y-4">
                    {stats.sessions.map(session => (
                        <div key={session.uuid} className="space-y-1">
                            <div className="flex justify-between text-sm">
                                <span className="font-medium truncate max-w-[70%]" title={session.title}>
                                    {session.title}
                                </span>
                                <span className="text-muted-foreground text-xs">
                                    {session.attended_count}/{session.enrollment_count} ({session.attendance_rate}%)
                                </span>
                            </div>
                            <div className="h-2 bg-muted rounded-full overflow-hidden">
                                <div
                                    className="h-full bg-primary transition-all duration-500"
                                    style={{ width: `${session.attendance_rate}%` }}
                                />
                            </div>
                        </div>
                    ))}
                </div>
            </CardContent>
        </Card>
    );
}
