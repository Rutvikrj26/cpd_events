/**
 * InviteLearnerDialog — one modal that works for both events and courses.
 *
 * The dialog is the single entry point for the invite flow. It:
 *   - lets the user mix existing contacts and free-form emails via
 *     `<ContactEmailCombobox>`
 *   - takes an optional personal message (max 1000 chars)
 *   - exposes a "Comp this seat" toggle ONLY when the target is paid
 *     (`target.isPaid`); default OFF
 *   - dispatches to the right backend endpoint based on `target.type`
 *   - surfaces per-row backend feedback (created / refreshed / skipped
 *     with an explained reason for each skip) so the organizer knows
 *     exactly what happened.
 *
 * Designed to be drop-in for both `EventAttendeesTab` and the course
 * `EnrollmentsTab` toolbars — one component, one source of truth.
 */

import { useState } from 'react';
import { Loader2, MailPlus } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/shared/ui/button';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/shared/ui/dialog';
import { Label } from '@/shared/ui/label';
import { Switch } from '@/shared/ui/switch';
import { Textarea } from '@/shared/ui/textarea';
import { inviteToCourse, inviteToEvent } from '@/api/invitations';
import type { InviteCreateResponse } from '@/api/invitations/types';
import { ContactEmailCombobox, type Chip as ChipState } from './ContactEmailCombobox';

export interface InviteTarget {
    type: 'event' | 'course';
    uuid: string;
    title: string;
    /** When true, surfaces the "Comp this seat" toggle. */
    isPaid: boolean;
}

export interface InviteLearnerDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    target: InviteTarget;
    /** Called once the API responds (with the per-row breakdown). Useful for
     *  refreshing the Invitations tab list. */
    onInvited?: (result: InviteCreateResponse) => void;
}

export function InviteLearnerDialog({
    open,
    onOpenChange,
    target,
    onInvited,
}: InviteLearnerDialogProps) {
    const [chips, setChips] = useState<ChipState[]>([]);
    const [message, setMessage] = useState('');
    const [comp, setComp] = useState(false);
    const [submitting, setSubmitting] = useState(false);

    const reset = () => {
        setChips([]);
        setMessage('');
        setComp(false);
    };

    const close = () => {
        reset();
        onOpenChange(false);
    };

    const validChips = chips.filter((c) => !c.invalid);
    const hasInvalid = chips.some((c) => c.invalid);
    const canSubmit = validChips.length > 0 && !hasInvalid && !submitting;

    const submit = async () => {
        if (!canSubmit) return;
        setSubmitting(true);
        const payload = {
            invitees: validChips.map((c) => ({
                contact_uuid: c.contact_uuid,
                email: c.contact_uuid ? undefined : c.email,
                full_name: c.full_name,
            })),
            personal_message: message,
            comp,
        };
        try {
            const apiCall = target.type === 'event' ? inviteToEvent : inviteToCourse;
            const result = await apiCall(target.uuid, payload);

            // One toast per outcome bucket — concise but specific. Skipped
            // rows with a reason show that reason inline so the organizer
            // doesn't have to chase it.
            const sentCount = result.created.length + result.refreshed.length;
            if (sentCount > 0) {
                toast.success(
                    sentCount === 1
                        ? `Invitation sent to ${result.created[0]?.email ?? result.refreshed[0]?.email}.`
                        : `Sent ${sentCount} invitation${sentCount === 1 ? '' : 's'}.`,
                );
            }
            if (result.skipped.length > 0) {
                for (const s of result.skipped) {
                    const detail =
                        s.reason === 'already_registered'
                            ? `${s.email} is already registered.`
                            : s.reason === 'invalid_email'
                              ? `${s.email}: ${s.detail || 'invalid email'}`
                              : `${s.email}: ${s.detail || s.reason}`;
                    toast.warning(detail);
                }
            }
            onInvited?.(result);
            close();
        } catch (err) {
            const detail =
                (err as { response?: { data?: { error?: { message?: string } } } })?.response?.data?.error?.message ||
                (err as Error)?.message ||
                'Failed to send invitations.';
            toast.error(detail);
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={(next) => (next ? onOpenChange(true) : close())}>
            <DialogContent className="max-w-xl">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <MailPlus className="h-5 w-5" />
                        Invite to {target.title}
                    </DialogTitle>
                    <DialogDescription>
                        Pick contacts from your address book or paste new email addresses
                        (comma, semicolon, or newline-separated). Each invitee receives an
                        email with a one-click acceptance link.
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4">
                    <div className="space-y-1.5">
                        <Label>Invitees</Label>
                        <ContactEmailCombobox value={chips} onChange={setChips} />
                    </div>

                    <div className="space-y-1.5">
                        <Label htmlFor="invite-message">
                            Personal message <span className="text-xs text-muted-foreground">(optional)</span>
                        </Label>
                        <Textarea
                            id="invite-message"
                            value={message}
                            onChange={(e) => setMessage(e.target.value.slice(0, 1000))}
                            placeholder={`Hi, I thought you'd find ${target.title} useful…`}
                            rows={3}
                            maxLength={1000}
                        />
                        <p className="text-xs text-muted-foreground">
                            {message.length}/1000 characters
                        </p>
                    </div>

                    {target.isPaid && (
                        <div className="flex items-start justify-between gap-3 rounded-md border border-dashed border-border bg-muted/30 p-3">
                            <div className="space-y-0.5">
                                <Label htmlFor="comp-seat" className="text-sm">
                                    Comp this seat
                                </Label>
                                <p className="text-xs text-muted-foreground">
                                    Grant a free seat to each invitee. Off (default) means
                                    they'll still need to pay to confirm.
                                </p>
                            </div>
                            <Switch id="comp-seat" checked={comp} onCheckedChange={setComp} />
                        </div>
                    )}
                </div>

                <DialogFooter className="gap-2">
                    <Button type="button" variant="outline" onClick={close} disabled={submitting}>
                        Cancel
                    </Button>
                    <Button type="button" onClick={submit} disabled={!canSubmit}>
                        {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        {submitting
                            ? 'Sending…'
                            : `Send ${validChips.length || ''} invitation${validChips.length === 1 ? '' : 's'}`.replace(
                                  /\s+/g,
                                  ' ',
                              )}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
