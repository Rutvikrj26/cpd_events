import React from 'react';
import { Star } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import type { Event } from '../../types';

interface EventStats {
    registered: number;
    checkedIn: number;
    cancelled: number;
    issued: number;
    feedbackCount: number;
    avgRating: number;
}

interface EventOverviewTabProps {
    event: Event;
    stats: EventStats;
}

export function EventOverviewTab({ event, stats }: EventOverviewTabProps) {
    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <Card>
                <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">
                        Total Registrations
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="text-2xl font-bold">{stats.registered}</div>
                    <p className="text-xs text-muted-foreground mt-1">
                        {event.capacity
                            ? `${((stats.registered / event.capacity) * 100).toFixed(0)}% of capacity`
                            : 'Unlimited capacity'}
                    </p>
                </CardContent>
            </Card>
            <Card>
                <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">
                        Checked In
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="text-2xl font-bold">{stats.checkedIn}</div>
                    <p className="text-xs text-muted-foreground mt-1">
                        {stats.registered > 0
                            ? `${((stats.checkedIn / stats.registered) * 100).toFixed(0)}% attendance rate`
                            : '0% attendance rate'}
                    </p>
                </CardContent>
            </Card>
            <Card>
                <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">
                        Certificates Issued
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="text-2xl font-bold">{stats.issued}</div>
                    <p className="text-xs text-muted-foreground mt-1">
                        {stats.checkedIn > 0
                            ? `${((stats.issued / stats.checkedIn) * 100).toFixed(0)}% of attendees`
                            : '0% of attendees'}
                    </p>
                </CardContent>
            </Card>
            <Card>
                <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">
                        Feedback
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="flex items-center gap-2">
                        <div className="text-2xl font-bold">
                            {stats.avgRating > 0 ? stats.avgRating : '-'}
                        </div>
                        {stats.avgRating > 0 && (
                            <Star className="h-5 w-5 fill-yellow-400 text-yellow-400" />
                        )}
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                        {stats.feedbackCount} response{stats.feedbackCount !== 1 ? 's' : ''}
                    </p>
                </CardContent>
            </Card>
        </div>
    );
}
