import React, { useState } from 'react';
import { MessageSquare, Award } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/shared/ui/tabs';
import { Badge } from '@/shared/ui/badge';
import { Card } from '@/shared/ui/card';
import { RegistrationFormBuilder } from '@/components/events/RegistrationFormBuilder';
import { FeedbackFormBuilder } from '@/components/events/FeedbackFormBuilder';
import { EventRecordingPanel } from '@/components/dashboard/EventRecordingPanel';
import { useEventAttendees, useEventFeedbackList } from '../../hooks';
import { calculateFeedbackSummary } from '@/api/feedback';
import { toast } from 'sonner';
import { EventOverviewTab } from './EventOverviewTab';
import { EventAttendeesTab } from './EventAttendeesTab';
import { InvitationsListTab } from '@/shared/components/invitations/InvitationsListTab';
import { EventAttendanceTab } from './EventAttendanceTab';
import { EventFeedbackTab } from './EventFeedbackTab';
import { EventCertificatesTab } from './EventCertificatesTab';
import type { Event } from '../../types';

interface EventManagementTabsProps {
    event: Event;
    isEventHost: boolean;
}

const TRIGGER =
    'rounded-none border-b-2 border-transparent px-6 py-3 data-[state=active]:border-primary data-[state=active]:text-primary data-[state=active]:bg-transparent shadow-none';

export function EventManagementTabs({ event, isEventHost }: EventManagementTabsProps) {
    const [searchTerm, setSearchTerm] = useState('');

    const { data: attendees = [] } = useEventAttendees(event.uuid);
    const { data: feedback = [] } = useEventFeedbackList(event.uuid);

    const feedbackSummary = calculateFeedbackSummary(feedback as any[]);
    const primaryRating = feedbackSummary.per_field.find((f) => f.field_type === 'rating');

    const stats = {
        registered: (attendees as any[]).filter((a) => a.status !== 'cancelled').length,
        checkedIn: (attendees as any[]).filter((a) => a.attended).length,
        cancelled: (attendees as any[]).filter((a) => a.status === 'cancelled').length,
        issued: (attendees as any[]).filter((a) => a.certificate_uuid).length,
        feedbackCount: feedback.length,
        avgRating: primaryRating?.average ?? 0,
    };

    const handleExportCsv = () => {
        if ((attendees as any[]).length === 0) {
            toast.error('No attendees to export');
            return;
        }
        const headers = ['Full Name', 'Email', 'Status', 'Payment Status', 'Attended', 'Registered At'];
        const rows = (attendees as any[]).map((a) =>
            [
                `"${(a.full_name || '').replace(/"/g, '""')}"`,
                `"${(a.email || '').replace(/"/g, '""')}"`,
                a.status || '',
                a.payment_status || '',
                a.attended ? 'Yes' : 'No',
                a.created_at ? new Date(a.created_at).toISOString() : '',
            ].join(','),
        );
        const csvContent = [headers.join(','), ...rows].join('\n');
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `${event.title || 'event'}-attendees.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        toast.success('CSV exported');
    };

    return (
        <div className="space-y-8">
            <EventOverviewTab event={event} stats={stats} />

            {isEventHost && <EventRecordingPanel eventUuid={event.uuid} />}

            <Tabs defaultValue="registrations" className="w-full">
                <TabsList className="w-full justify-start border-b border-border bg-transparent p-0 h-auto rounded-none mb-6">
                    <TabsTrigger value="registrations" className={TRIGGER}>
                        Registrations
                    </TabsTrigger>
                    {isEventHost && (
                        <TabsTrigger value="invitations" className={TRIGGER}>
                            Invitations
                        </TabsTrigger>
                    )}
                    <TabsTrigger value="registration-form" className={TRIGGER}>
                        Registration form
                    </TabsTrigger>
                    <TabsTrigger value="attendance" className={TRIGGER}>
                        Attendance
                    </TabsTrigger>
                    {event.certificates_enabled && (
                        <TabsTrigger value="certificates" className={TRIGGER}>
                            Certificates
                        </TabsTrigger>
                    )}
                    {event.badges_enabled && (
                        <TabsTrigger value="badges" className={TRIGGER}>
                            Badges
                        </TabsTrigger>
                    )}
                    <TabsTrigger value="feedback-form" className={TRIGGER}>
                        Feedback form
                    </TabsTrigger>
                    <TabsTrigger value="feedback" className={TRIGGER}>
                        <MessageSquare className="h-4 w-4 mr-2" />
                        Feedback
                        {stats.feedbackCount > 0 && (
                            <Badge variant="secondary" className="ml-2 h-5 px-1.5">
                                {stats.feedbackCount}
                            </Badge>
                        )}
                    </TabsTrigger>
                </TabsList>

                <TabsContent value="registrations" className="mt-0">
                    <EventAttendeesTab
                        event={event}
                        searchTerm={searchTerm}
                        onSearchChange={setSearchTerm}
                        onExportCsv={handleExportCsv}
                    />
                </TabsContent>

                {isEventHost && (
                    <TabsContent value="invitations" className="mt-0">
                        <InvitationsListTab
                            target={{
                                type: 'event',
                                uuid: event.uuid,
                                title: event.title,
                                isPaid: Number(event.price ?? 0) > 0,
                            }}
                        />
                    </TabsContent>
                )}

                <TabsContent value="registration-form" className="mt-0">
                    <RegistrationFormBuilder eventUuid={event.uuid} />
                </TabsContent>

                <TabsContent value="attendance" className="mt-0">
                    <EventAttendanceTab event={event} searchTerm={searchTerm} />
                </TabsContent>

                {event.certificates_enabled && (
                    <TabsContent value="certificates" className="mt-0">
                        <EventCertificatesTab eventUuid={event.uuid} />
                    </TabsContent>
                )}

                {event.badges_enabled && (
                    <TabsContent value="badges" className="mt-0">
                        <div className="mb-4 p-4 rounded-lg bg-muted/50 border">
                            <div className="flex gap-3 items-center">
                                <Award className="h-5 w-5 text-muted-foreground" />
                                <div>
                                    <h3 className="text-sm font-medium">Auto-Issue Badges</h3>
                                    <p className="text-sm text-muted-foreground">
                                        {event.auto_issue_badges
                                            ? 'Badges are automatically issued to eligible attendees when the event completes.'
                                            : 'Auto-issue is disabled. Badges will not be automatically issued.'}
                                    </p>
                                </div>
                            </div>
                        </div>
                        <Card>
                            <div className="overflow-x-auto">
                                <table className="min-w-full divide-y divide-border">
                                    <thead className="bg-muted/50">
                                        <tr>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                                                Attendee
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                                                Eligibility
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                                                Badge Status
                                            </th>
                                        </tr>
                                    </thead>
                                    <tbody className="bg-card divide-y divide-border">
                                        {(attendees as any[])
                                            .filter((a) => a.status !== 'cancelled')
                                            .map((attendee: any) => (
                                                <tr key={attendee.uuid} className="hover:bg-muted/50">
                                                    <td className="px-6 py-4 whitespace-nowrap">
                                                        <div className="text-sm font-medium text-foreground">
                                                            {attendee.full_name}
                                                        </div>
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap">
                                                        {attendee.attendance_eligible ? (
                                                            <Badge
                                                                variant="outline"
                                                                className="text-success bg-success-subtle border-success"
                                                            >
                                                                Eligible
                                                            </Badge>
                                                        ) : (
                                                            <Badge
                                                                variant="outline"
                                                                className="text-muted-foreground bg-muted border-border"
                                                            >
                                                                Not Eligible
                                                            </Badge>
                                                        )}
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">
                                                        {attendee.badge_uuid ? (
                                                            <Badge variant="default">Issued</Badge>
                                                        ) : (
                                                            <span>Not Issued</span>
                                                        )}
                                                    </td>
                                                </tr>
                                            ))}
                                    </tbody>
                                </table>
                            </div>
                        </Card>
                    </TabsContent>
                )}

                <TabsContent value="feedback-form" className="mt-0">
                    <FeedbackFormBuilder eventUuid={event.uuid} />
                </TabsContent>

                <TabsContent value="feedback" className="mt-0">
                    <EventFeedbackTab eventUuid={event.uuid} />
                </TabsContent>
            </Tabs>
        </div>
    );
}
