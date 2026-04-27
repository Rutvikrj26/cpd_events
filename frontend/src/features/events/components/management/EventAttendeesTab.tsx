import React, { useState } from 'react';
import { MoreVertical, Search, Download, Filter } from 'lucide-react';
import { Button } from '@/shared/ui/button';
import { Input } from '@/shared/ui/input';
import { Badge } from '@/shared/ui/badge';
import { Card } from '@/shared/ui/card';
import { Avatar, AvatarFallback, AvatarImage } from '@/shared/ui/avatar';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
    DropdownMenuSeparator,
} from '@/shared/ui/dropdown-menu';
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from '@/shared/ui/alert-dialog';
import { toast } from 'sonner';
import { getInitials } from '@/lib/initials';
import { EditAttendanceDialog } from '@/components/events/EditAttendanceDialog';
import { CustomFieldResponsesDialog } from '@/components/events/CustomFieldResponsesDialog';
import { useEventAttendees, useCancelRegistration, useRefundRegistration } from '../../hooks';
import type { Event } from '../../types';

interface EventAttendeesTabProps {
    event: Event;
    searchTerm: string;
    onSearchChange: (value: string) => void;
    onExportCsv: () => void;
}

function getRegistrationBadge(attendee: any) {
    const paymentStatus = (attendee.payment_status || '').toLowerCase();
    const registrationStatus = (attendee.status || '').toLowerCase();

    if (paymentStatus === 'refunded')
        return { label: 'Refunded', className: 'text-primary border-primary bg-primary/10' };
    if (paymentStatus === 'failed')
        return { label: 'Payment Failed', className: 'text-destructive border-destructive bg-destructive/10' };
    if (paymentStatus === 'pending')
        return { label: 'Payment Pending', className: 'text-warning border-warning bg-warning-subtle' };
    if (paymentStatus === 'paid')
        return { label: 'Paid', className: 'text-success border-success bg-success-subtle' };
    if (registrationStatus === 'cancelled')
        return { label: 'Cancelled', className: 'text-destructive border-destructive bg-destructive/10' };
    if (registrationStatus === 'waitlisted')
        return { label: 'Waitlisted', className: 'text-warning border-warning bg-warning-subtle' };
    if (registrationStatus === 'pending')
        return { label: 'Pending', className: 'text-warning border-warning bg-warning-subtle' };
    return { label: 'Confirmed', className: 'text-success border-success bg-success-subtle' };
}

export function EventAttendeesTab({
    event,
    searchTerm,
    onSearchChange,
    onExportCsv,
}: EventAttendeesTabProps) {
    const [editAttendanceOpen, setEditAttendanceOpen] = useState(false);
    const [selectedAttendee, setSelectedAttendee] = useState<any>(null);
    const [customFieldDialogOpen, setCustomFieldDialogOpen] = useState(false);
    const [customFieldAttendee, setCustomFieldAttendee] = useState<any>(null);
    const [actionDialogOpen, setActionDialogOpen] = useState(false);
    const [actionType, setActionType] = useState<'cancel' | 'refund' | null>(null);
    const [actionReason, setActionReason] = useState('');
    const [actionAttendee, setActionAttendee] = useState<any>(null);

    const { data: attendees = [], refetch } = useEventAttendees(event.uuid);
    const { mutate: cancelReg, isPending: cancelling } = useCancelRegistration(event.uuid);
    const { mutate: refundReg, isPending: refunding } = useRefundRegistration(event.uuid);
    const actionLoading = cancelling || refunding;

    const filtered = (attendees as any[]).filter(
        (a) =>
            (a.full_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
            (a.email || '').toLowerCase().includes(searchTerm.toLowerCase()),
    );

    const openActionDialog = (attendee: any, type: 'cancel' | 'refund') => {
        setActionAttendee(attendee);
        setActionType(type);
        setActionReason('');
        setActionDialogOpen(true);
    };

    const closeActionDialog = () => {
        setActionDialogOpen(false);
        setActionType(null);
        setActionReason('');
        setActionAttendee(null);
    };

    const handleActionConfirm = () => {
        if (!actionAttendee || !actionType) return;
        const reason = actionReason.trim() || undefined;
        const mutate = actionType === 'refund' ? refundReg : cancelReg;
        mutate(
            { registrationUuid: actionAttendee.uuid, reason },
            {
                onSuccess: () => {
                    toast.success(actionType === 'refund' ? 'Registration refunded' : 'Registration cancelled');
                    closeActionDialog();
                },
                onError: (e: any) => {
                    toast.error(
                        e?.response?.data?.error?.message ||
                            e?.response?.data?.detail ||
                            'Action failed',
                    );
                },
            },
        );
    };

    return (
        <div className="space-y-4">
            <div className="flex flex-col sm:flex-row justify-between items-center gap-4">
                <div className="relative w-full sm:w-80">
                    <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                        placeholder="Search attendees..."
                        className="pl-9"
                        value={searchTerm}
                        onChange={(e) => onSearchChange(e.target.value)}
                    />
                </div>
                <div className="flex gap-2 w-full sm:w-auto">
                    <Button variant="outline" size="sm" className="w-full sm:w-auto">
                        <Filter className="mr-2 h-4 w-4" /> Filter
                    </Button>
                    <Button variant="outline" size="sm" className="w-full sm:w-auto" onClick={onExportCsv}>
                        <Download className="mr-2 h-4 w-4" /> Export CSV
                    </Button>
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
                                    Ticket Type
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                                    Status
                                </th>
                                <th className="px-6 py-3 relative">
                                    <span className="sr-only">Actions</span>
                                </th>
                            </tr>
                        </thead>
                        <tbody className="bg-card divide-y divide-border">
                            {filtered.map((attendee: any) => {
                                const badge = getRegistrationBadge(attendee);
                                const paymentStatus = (attendee.payment_status || '').toLowerCase();
                                const registrationStatus = (attendee.status || '').toLowerCase();
                                const isRefunded = paymentStatus === 'refunded';
                                const isCancelled = registrationStatus === 'cancelled';
                                const canRefund = paymentStatus === 'paid';
                                const canCancel = !canRefund && !isRefunded && !isCancelled;

                                return (
                                    <tr key={attendee.uuid} className="hover:bg-muted/50">
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="flex items-center">
                                                <Avatar className="h-8 w-8 mr-3">
                                                    <AvatarImage
                                                        src={`https://ui-avatars.com/api/?name=${encodeURIComponent(attendee.full_name || '')}`}
                                                    />
                                                    <AvatarFallback>
                                                        {getInitials(attendee.full_name || 'U')}
                                                    </AvatarFallback>
                                                </Avatar>
                                                <div>
                                                    <div className="text-sm font-medium text-foreground">
                                                        {attendee.full_name}
                                                    </div>
                                                    <div className="text-xs text-muted-foreground">
                                                        {attendee.email}
                                                    </div>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground capitalize">
                                            {attendee.status}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <Badge variant="outline" className={badge.className}>
                                                {badge.label}
                                            </Badge>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                            <DropdownMenu>
                                                <DropdownMenuTrigger asChild>
                                                    <Button variant="ghost" className="h-8 w-8 p-0">
                                                        <MoreVertical className="h-4 w-4" />
                                                    </Button>
                                                </DropdownMenuTrigger>
                                                <DropdownMenuContent align="end">
                                                    <DropdownMenuItem>Send Email</DropdownMenuItem>
                                                    <DropdownMenuItem
                                                        onClick={() => {
                                                            setSelectedAttendee(attendee);
                                                            setEditAttendanceOpen(true);
                                                        }}
                                                    >
                                                        Edit Attendance
                                                    </DropdownMenuItem>
                                                    {event.custom_fields &&
                                                        event.custom_fields.length > 0 && (
                                                            <DropdownMenuItem
                                                                onClick={() => {
                                                                    setCustomFieldAttendee(attendee);
                                                                    setCustomFieldDialogOpen(true);
                                                                }}
                                                            >
                                                                View Responses
                                                            </DropdownMenuItem>
                                                        )}
                                                    <DropdownMenuSeparator />
                                                    {canRefund ? (
                                                        <DropdownMenuItem
                                                            onClick={() =>
                                                                openActionDialog(attendee, 'refund')
                                                            }
                                                            className="text-warning"
                                                        >
                                                            Refund Registration
                                                        </DropdownMenuItem>
                                                    ) : (
                                                        <DropdownMenuItem
                                                            onClick={() =>
                                                                openActionDialog(attendee, 'cancel')
                                                            }
                                                            disabled={!canCancel}
                                                            className="text-destructive"
                                                        >
                                                            {isRefunded
                                                                ? 'Already Refunded'
                                                                : isCancelled
                                                                ? 'Already Cancelled'
                                                                : 'Cancel Registration'}
                                                        </DropdownMenuItem>
                                                    )}
                                                </DropdownMenuContent>
                                            </DropdownMenu>
                                        </td>
                                    </tr>
                                );
                            })}
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

            <CustomFieldResponsesDialog
                open={customFieldDialogOpen}
                onOpenChange={setCustomFieldDialogOpen}
                attendeeName={customFieldAttendee?.full_name || ''}
                eventUuid={event.uuid}
                registrationUuid={customFieldAttendee?.uuid || ''}
            />

            <AlertDialog
                open={actionDialogOpen}
                onOpenChange={(open) => {
                    if (!open) closeActionDialog();
                    else setActionDialogOpen(true);
                }}
            >
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>
                            {actionType === 'refund'
                                ? 'Refund Registration'
                                : 'Cancel Registration'}
                        </AlertDialogTitle>
                        <AlertDialogDescription>
                            {actionType === 'refund'
                                ? 'This will refund the attendee and cancel their registration.'
                                : 'This will cancel the registration without issuing a refund.'}
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-foreground">
                            Reason (optional)
                        </label>
                        <Input
                            placeholder="Add a reason for the attendee"
                            value={actionReason}
                            onChange={(e) => setActionReason(e.target.value)}
                        />
                    </div>
                    <AlertDialogFooter>
                        <AlertDialogCancel disabled={actionLoading}>Back</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={(e) => {
                                e.preventDefault();
                                handleActionConfirm();
                            }}
                            disabled={actionLoading}
                            className={
                                actionType === 'refund'
                                    ? 'bg-warning hover:bg-warning/90 text-white'
                                    : 'bg-destructive hover:bg-destructive/90'
                            }
                        >
                            {actionLoading
                                ? 'Processing...'
                                : actionType === 'refund'
                                ? 'Refund Registration'
                                : 'Cancel Registration'}
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    );
}
