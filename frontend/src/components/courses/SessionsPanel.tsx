import React from 'react';
import { Video, Calendar, Clock, ExternalLink, Users, CheckCircle2, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { CourseSession } from '@/api/courses/types';

interface SessionsPanelProps {
    sessions: CourseSession[];
    courseTitle: string;
}

export function SessionsPanel({ sessions, courseTitle }: SessionsPanelProps) {
    if (sessions.length === 0) {
        return null;
    }

    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        return date.toLocaleDateString(undefined, {
            weekday: 'short',
            month: 'short',
            day: 'numeric',
            year: 'numeric',
        });
    };

    const formatTime = (dateString: string, timezone?: string) => {
        const date = new Date(dateString);
        return date.toLocaleTimeString(undefined, {
            hour: '2-digit',
            minute: '2-digit',
            timeZoneName: 'short',
        });
    };

    const getSessionStatus = (session: CourseSession) => {
        const now = new Date();
        const start = new Date(session.starts_at);
        const end = session.ends_at ? new Date(session.ends_at) : new Date(start.getTime() + (session.duration_minutes || 60) * 60000);

        if (now < start) {
            const diffMs = start.getTime() - now.getTime();
            const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
            const diffDays = Math.floor(diffHours / 24);

            if (diffDays > 0) {
                return { status: 'upcoming', label: `In ${diffDays} day${diffDays > 1 ? 's' : ''}` };
            } else if (diffHours > 0) {
                return { status: 'upcoming', label: `In ${diffHours} hour${diffHours > 1 ? 's' : ''}` };
            } else {
                const diffMins = Math.floor(diffMs / (1000 * 60));
                return { status: 'upcoming', label: `Starting in ${diffMins} min` };
            }
        } else if (now >= start && now <= end) {
            return { status: 'live', label: 'Live Now' };
        } else {
            return { status: 'past', label: 'Ended' };
        }
    };

    const getStatusBadge = (session: CourseSession) => {
        const { status, label } = getSessionStatus(session);

        switch (status) {
            case 'live':
                return (
                    <Badge className="bg-red-500 text-white animate-pulse">
                        <span className="mr-1">●</span> {label}
                    </Badge>
                );
            case 'upcoming':
                return <Badge variant="outline" className="text-blue-600 border-blue-300">{label}</Badge>;
            case 'past':
                return <Badge variant="secondary">{label}</Badge>;
            default:
                return null;
        }
    };

    // Sort sessions: live first, then upcoming, then past
    const sortedSessions = [...sessions].sort((a, b) => {
        const statusA = getSessionStatus(a).status;
        const statusB = getSessionStatus(b).status;
        const order = { live: 0, upcoming: 1, past: 2 };
        return (order[statusA as keyof typeof order] ?? 2) - (order[statusB as keyof typeof order] ?? 2);
    });

    return (
        <Card className="mb-6">
            <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-lg">
                    <Video className="h-5 w-5 text-primary" />
                    Live Sessions
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
                {sortedSessions.map((session, index) => {
                    const { status } = getSessionStatus(session);
                    const canJoin = status === 'live' || status === 'upcoming';

                    return (
                        <React.Fragment key={session.uuid}>
                            {index > 0 && <Separator />}
                            <div className={`p-4 rounded-lg ${status === 'live' ? 'bg-red-50 border border-red-200' : 'bg-muted/50'}`}>
                                <div className="flex items-start justify-between gap-3">
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-2">
                                            <h4 className="font-medium truncate">{session.title}</h4>
                                            {getStatusBadge(session)}
                                            {session.is_mandatory && (
                                                <Badge variant="outline" className="text-xs">Required</Badge>
                                            )}
                                        </div>

                                        {session.description && (
                                            <p className="text-sm text-muted-foreground mb-3 line-clamp-2">
                                                {session.description}
                                            </p>
                                        )}

                                        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
                                            <span className="flex items-center gap-1">
                                                <Calendar className="h-3.5 w-3.5" />
                                                {formatDate(session.starts_at)}
                                            </span>
                                            <span className="flex items-center gap-1">
                                                <Clock className="h-3.5 w-3.5" />
                                                {formatTime(session.starts_at)} ({session.duration_minutes} min)
                                            </span>
                                            {session.cpd_credits && Number(session.cpd_credits) > 0 && (
                                                <span className="flex items-center gap-1">
                                                    <CheckCircle2 className="h-3.5 w-3.5" />
                                                    {session.cpd_credits} CPD
                                                </span>
                                            )}
                                        </div>

                                        {session.minimum_attendance_percent > 0 && (
                                            <p className="text-xs text-muted-foreground mt-2 flex items-center gap-1">
                                                <AlertCircle className="h-3 w-3" />
                                                Attend at least {session.minimum_attendance_percent}% to receive credit
                                            </p>
                                        )}
                                    </div>

                                    <div className="flex-shrink-0">
                                        {session.zoom_join_url && canJoin ? (
                                            <Button
                                                variant={status === 'live' ? 'default' : 'outline'}
                                                size="sm"
                                                asChild
                                            >
                                                <a
                                                    href={session.zoom_join_url}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                >
                                                    <ExternalLink className="mr-2 h-4 w-4" />
                                                    {status === 'live' ? 'Join Now' : 'Join'}
                                                </a>
                                            </Button>
                                        ) : session.zoom_error ? (
                                            <Badge variant="destructive" className="text-xs">
                                                Zoom Error
                                            </Badge>
                                        ) : status === 'past' ? (
                                            <Badge variant="secondary">Completed</Badge>
                                        ) : null}
                                    </div>
                                </div>
                            </div>
                        </React.Fragment>
                    );
                })}
            </CardContent>
        </Card>
    );
}

export default SessionsPanel;
