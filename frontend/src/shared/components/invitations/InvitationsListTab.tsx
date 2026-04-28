/**
 * InvitationsListTab — host-facing list of pending/sent invitations.
 *
 * One component shared between Event and Course management:
 *   - For events, pass `target={ type: 'event', uuid }`.
 *   - For courses, pass `target={ type: 'course', uuid }`.
 *
 * Renders a table with status, recipient, send count, last-sent timestamp,
 * and per-row Resend / Cancel actions. Auto-refreshes after each action.
 */

import { useCallback, useEffect, useState } from 'react';
import { Loader2, MailPlus, RefreshCw, X } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/shared/ui/button';
import { Badge } from '@/shared/ui/badge';
import {
    cancelInvitation,
    listCourseInvitations,
    listEventInvitations,
    resendInvitation,
} from '@/api/invitations';
import type { LearningInvitation } from '@/api/invitations/types';
import { formatDateTime } from '@/lib/datetime';
import { InviteLearnerDialog, type InviteTarget } from './InviteLearnerDialog';

interface InvitationsListTabProps {
    target: InviteTarget;
}

const STATUS_COLOR: Record<LearningInvitation['status'], 'default' | 'secondary' | 'destructive' | 'outline'> = {
    pending: 'default',
    accepted: 'secondary',
    expired: 'outline',
    cancelled: 'destructive',
};

export function InvitationsListTab({ target }: InvitationsListTabProps) {
    const [invitations, setInvitations] = useState<LearningInvitation[]>([]);
    const [loading, setLoading] = useState(true);
    const [busyUuid, setBusyUuid] = useState<string | null>(null);
    const [dialogOpen, setDialogOpen] = useState(false);

    const refresh = useCallback(async () => {
        setLoading(true);
        try {
            const list =
                target.type === 'event'
                    ? await listEventInvitations(target.uuid)
                    : await listCourseInvitations(target.uuid);
            setInvitations(list);
        } catch (err) {
            toast.error((err as Error)?.message || 'Failed to load invitations.');
        } finally {
            setLoading(false);
        }
    }, [target.type, target.uuid]);

    useEffect(() => {
        refresh();
    }, [refresh]);

    const handleResend = async (uuid: string) => {
        setBusyUuid(uuid);
        try {
            await resendInvitation(uuid);
            toast.success('Invitation resent.');
            await refresh();
        } catch (err) {
            const detail =
                (err as { response?: { data?: { error?: { message?: string } } } })?.response?.data?.error?.message ||
                (err as Error)?.message ||
                'Failed to resend.';
            toast.error(detail);
        } finally {
            setBusyUuid(null);
        }
    };

    const handleCancel = async (uuid: string) => {
        setBusyUuid(uuid);
        try {
            await cancelInvitation(uuid);
            toast.success('Invitation cancelled.');
            await refresh();
        } catch (err) {
            const detail =
                (err as { response?: { data?: { error?: { message?: string } } } })?.response?.data?.error?.message ||
                (err as Error)?.message ||
                'Failed to cancel.';
            toast.error(detail);
        } finally {
            setBusyUuid(null);
        }
    };

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between gap-3">
                <div>
                    <h3 className="text-base font-semibold">Invitations</h3>
                    <p className="text-sm text-muted-foreground">
                        Pending and accepted invitations for this {target.type}.
                    </p>
                </div>
                <Button size="sm" onClick={() => setDialogOpen(true)}>
                    <MailPlus className="mr-2 h-4 w-4" />
                    Invite Learner
                </Button>
            </div>

            {loading ? (
                <div className="flex items-center gap-2 p-8 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Loading invitations…
                </div>
            ) : invitations.length === 0 ? (
                <div className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
                    No invitations yet. Click <strong>Invite Learner</strong> to send the first one.
                </div>
            ) : (
                <div className="overflow-x-auto rounded-lg border">
                    <table className="w-full text-left text-sm">
                        <thead className="border-b bg-muted/30">
                            <tr>
                                <th className="px-4 py-2 text-xs font-medium text-muted-foreground">Invitee</th>
                                <th className="px-4 py-2 text-xs font-medium text-muted-foreground">Status</th>
                                <th className="px-4 py-2 text-xs font-medium text-muted-foreground">Sent</th>
                                <th className="px-4 py-2 text-xs font-medium text-muted-foreground">Invited by</th>
                                <th className="px-4 py-2 text-xs font-medium text-muted-foreground">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y">
                            {invitations.map((inv) => (
                                <tr key={inv.uuid}>
                                    <td className="px-4 py-2">
                                        <div className="font-medium">{inv.full_name || inv.email}</div>
                                        <div className="text-xs text-muted-foreground">{inv.email}</div>
                                    </td>
                                    <td className="px-4 py-2">
                                        <Badge variant={STATUS_COLOR[inv.status]} className="capitalize">
                                            {inv.status}
                                        </Badge>
                                        {inv.comp && (
                                            <span className="ml-1.5 text-xs text-muted-foreground">comp</span>
                                        )}
                                    </td>
                                    <td className="px-4 py-2 text-xs text-muted-foreground">
                                        {inv.last_sent_at ? formatDateTime(inv.last_sent_at) : '—'}
                                        {inv.send_count > 1 && (
                                            <span className="ml-1">(×{inv.send_count})</span>
                                        )}
                                    </td>
                                    <td className="px-4 py-2 text-xs text-muted-foreground">
                                        {inv.invited_by_name || '—'}
                                    </td>
                                    <td className="px-4 py-2">
                                        {inv.status === 'pending' && (
                                            <div className="flex items-center gap-1">
                                                <Button
                                                    type="button"
                                                    size="sm"
                                                    variant="ghost"
                                                    disabled={busyUuid === inv.uuid}
                                                    onClick={() => handleResend(inv.uuid)}
                                                    className="h-7 px-2 text-xs"
                                                >
                                                    <RefreshCw className="mr-1 h-3 w-3" />
                                                    Resend
                                                </Button>
                                                <Button
                                                    type="button"
                                                    size="sm"
                                                    variant="ghost"
                                                    disabled={busyUuid === inv.uuid}
                                                    onClick={() => handleCancel(inv.uuid)}
                                                    className="h-7 px-2 text-xs text-destructive hover:text-destructive"
                                                >
                                                    <X className="mr-1 h-3 w-3" />
                                                    Cancel
                                                </Button>
                                            </div>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            <InviteLearnerDialog
                open={dialogOpen}
                onOpenChange={setDialogOpen}
                target={target}
                onInvited={() => refresh()}
            />
        </div>
    );
}
