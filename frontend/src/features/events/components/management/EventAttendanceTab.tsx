import React, { useState } from 'react';
import { MoreVertical } from 'lucide-react';
import { Button } from '@/shared/ui/button';
import { Card } from '@/shared/ui/card';
import { Checkbox } from '@/shared/ui/checkbox';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from '@/shared/ui/dropdown-menu';
import { toast } from 'sonner';
import { AttendanceReconciliation } from '@/components/events/AttendanceReconciliation';
import { EditAttendanceDialog } from '@/components/events/EditAttendanceDialog';
import { useEventAttendees, useCheckInAttendee } from '../../hooks';
import type { Event } from '../../types';

interface EventAttendanceTabProps {
    event: Event;
    searchTerm: string;
}

export function EventAttendanceTab({ event, searchTerm }: EventAttendanceTabProps) {
    const [editAttendanceOpen, setEditAttendanceOpen] = useState(false);
    const [selectedAttendee, setSelectedAttendee] = useState<any>(null);

    const { data: attendees = [], refetch } = useEventAttendees(event.uuid);
    const { mutate: checkIn } = useCheckInAttendee(event.uuid);

    const filtered = (attendees as any[])
        .filter((a) => a.status !== 'cancelled')
        .filter(
            (a) =>
                (a.full_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
                (a.email || '').toLowerCase().includes(searchTerm.toLowerCase()),
        );

    const handleCheckIn = (attendeeUuid: string) => {
        const attendee = (attendees as any[]).find((a) => a.uuid === attendeeUuid);
        if (!attendee) return;
        checkIn(
            { registrationUuid: attendeeUuid, attended: !attendee.attended },
            {
                onSuccess: () =>
                    toast.success(attendee.attended ? 'Check-in canceled' : 'Attendee checked in'),
                onError: () => toast.error('Failed to update check-in status'),
            },
        );
    };

    return (
        <div className="space-y-4">
            {(event.format === 'online' || event.format === 'hybrid') && (
                <AttendanceReconciliation
                    eventUuid={event.uuid}
                    onReconciled={() => refetch()}
                />
            )}

            <Card>
                <div className="p-4 border-b border-border bg-muted/30">
                    <div className="text-sm text-muted-foreground">
                        {event.format === 'online'
                            ? 'Attendance is tracked automatically via online participation.'
                            : event.format === 'hybrid'
                            ? 'Track in-person check-ins and online participation.'
                            : 'Mark attendance manually or use the QR scanner app.'}
                    </div>
                </div>
                <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-border">
                        <thead className="bg-muted/50">
                            <tr>
                                {event.format !== 'online' && (
                                    <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider w-10">
                                        Present
                                    </th>
                                )}
                                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                                    Attendee
                                </th>
                                {event.format !== 'online' && (
                                    <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                                        Check-in Time
                                    </th>
                                )}
                                {event.format !== 'in-person' && (
                                    <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                                        Attendance Minutes
                                    </th>
                                )}
                                <th className="px-6 py-3 relative">
                                    <span className="sr-only">Actions</span>
                                </th>
                            </tr>
                        </thead>
                        <tbody className="bg-card divide-y divide-border">
                            {filtered.map((attendee: any) => (
                                <tr key={attendee.uuid} className="hover:bg-muted/50">
                                    {event.format !== 'online' && (
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <Checkbox
                                                checked={attendee.attended}
                                                onCheckedChange={() =>
                                                    handleCheckIn(attendee.uuid)
                                                }
                                            />
                                        </td>
                                    )}
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <div className="text-sm font-medium text-foreground">
                                            {attendee.full_name}
                                        </div>
                                        <div className="text-xs text-muted-foreground">
                                            {attendee.email}
                                        </div>
                                    </td>
                                    {event.format !== 'online' && (
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">
                                            {attendee.check_in_time
                                                ? new Date(attendee.check_in_time).toLocaleTimeString(
                                                      [],
                                                      { hour: '2-digit', minute: '2-digit' },
                                                  )
                                                : '-'}
                                        </td>
                                    )}
                                    {event.format !== 'in-person' && (
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">
                                            {attendee.total_attendance_minutes != null
                                                ? `${attendee.total_attendance_minutes} min`
                                                : '-'}
                                        </td>
                                    )}
                                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                        <DropdownMenu>
                                            <DropdownMenuTrigger asChild>
                                                <Button variant="ghost" className="h-8 w-8 p-0">
                                                    <MoreVertical className="h-4 w-4" />
                                                </Button>
                                            </DropdownMenuTrigger>
                                            <DropdownMenuContent align="end">
                                                <DropdownMenuItem
                                                    onClick={() => {
                                                        setSelectedAttendee(attendee);
                                                        setEditAttendanceOpen(true);
                                                    }}
                                                >
                                                    Edit Attendance
                                                </DropdownMenuItem>
                                            </DropdownMenuContent>
                                        </DropdownMenu>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </Card>

            <EditAttendanceDialog
                isOpen={editAttendanceOpen}
                onOpenChange={setEditAttendanceOpen}
                attendee={selectedAttendee}
                eventUuid={event.uuid}
                onSuccess={() => refetch()}
            />
        </div>
    );
}
