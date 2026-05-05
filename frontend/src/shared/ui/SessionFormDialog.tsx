/**
 * SessionFormDialog — shared add/edit dialog for event sessions, course
 * sessions (draft), and course sessions (managed).
 *
 * Each call site previously rolled its own dialog with subtly different
 * fields and progressively-worse UX (events had rich-text + a date
 * picker; courses had a plain textarea + a raw `datetime-local`). This
 * collapses the three implementations into one and elevates all surfaces
 * to the better UX. Fields that don't apply to a given surface are
 * hidden via the `show*` flags.
 *
 * Field map:
 *   title             — always
 *   description       — always (rich text)
 *   speaker_names     — events only            (showSpeakerNames)
 *   starts_at         — always (date+time picker)
 *   duration_minutes  — always
 *   session_type      — always (live / recorded / hybrid)
 *   delivery_mode     — courses (manage)       (showDeliveryMode)
 *   is_mandatory      — always
 *   minimum_attendance_percent — courses        (showMinAttendance)
 *   cpd_credits       — courses (draft)        (showCpdCredits)
 *
 * The dialog operates on a superset shape (`SessionFormValue`); each
 * call site translates between its own row type and this shape at the
 * `value` / `onSave` boundary.
 */

import React from 'react';
import ReactQuill from 'react-quill-new';
import 'react-quill-new/dist/quill.snow.css';

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/shared/ui/dialog';
import { Button } from '@/shared/ui/button';
import { Input } from '@/shared/ui/input';
import { Label } from '@/shared/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/ui/select';
import { Switch } from '@/shared/ui/switch';
import { DateTimePicker } from '@/shared/ui/date-time-picker';

export type SessionType = 'live' | 'recorded' | 'hybrid';
export type DeliveryMode = 'online' | 'in_person' | 'hybrid';

export interface SessionFormValue {
    // Common
    title: string;
    description: string;
    starts_at: string;
    duration_minutes: number;
    session_type: SessionType;
    is_mandatory: boolean;

    // Surface-specific (optional)
    speaker_names?: string;
    delivery_mode?: DeliveryMode;
    minimum_attendance_percent?: number;
    cpd_credits?: number;
}

export interface SessionFormDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    /** Current row, or null when creating a new one. */
    value: SessionFormValue | null;
    onSave: (value: SessionFormValue) => void;

    /** Default `starts_at` when creating a new session (e.g. parent
     *  event's `starts_at`). Ignored when editing an existing row. */
    parentStartsAt?: string;

    /** Field visibility — opt-in per call site. */
    showSpeakerNames?: boolean;
    showDeliveryMode?: boolean;
    showMinAttendance?: boolean;
    showCpdCredits?: boolean;

    /** Copy overrides for the mandatory toggle (events vs courses use
     *  different language: "Required for Certificate" vs "Required for
     *  Completion" vs "Mandatory Session"). */
    mandatoryLabel?: string;
    mandatoryHelp?: string;

    /** Override the dialog title verb. Defaults to "Add Session" / "Edit Session". */
    addTitle?: string;
    editTitle?: string;
}

const DEFAULT_VALUE: SessionFormValue = {
    title: '',
    description: '',
    starts_at: '',
    duration_minutes: 60,
    session_type: 'live',
    is_mandatory: true,
    speaker_names: '',
    delivery_mode: 'online',
    minimum_attendance_percent: 80,
    cpd_credits: 0,
};

function isEmptyRichText(html: string | null | undefined): boolean {
    if (!html) return true;
    const plain = html
        .replace(/<br\s*\/?>/gi, '')
        .replace(/<[^>]*>/g, '')
        .replace(/&nbsp;/g, '')
        .trim();
    return plain.length === 0;
}

export function SessionFormDialog({
    open,
    onOpenChange,
    value,
    onSave,
    parentStartsAt,
    showSpeakerNames = false,
    showDeliveryMode = false,
    showMinAttendance = false,
    showCpdCredits = false,
    mandatoryLabel = 'Required',
    mandatoryHelp = 'Attendees must complete this session',
    addTitle = 'Add Session',
    editTitle = 'Edit Session',
}: SessionFormDialogProps) {
    const [form, setForm] = React.useState<SessionFormValue>(DEFAULT_VALUE);
    const isEditing = !!value;

    React.useEffect(() => {
        if (!open) return;
        if (value) {
            // Merge with DEFAULT_VALUE so optional fields the call site
            // doesn't manage (e.g. delivery_mode for events) still have
            // sensible defaults if a flag is later turned on.
            setForm({ ...DEFAULT_VALUE, ...value });
        } else {
            setForm({ ...DEFAULT_VALUE, starts_at: parentStartsAt || '' });
        }
    }, [open, value, parentStartsAt]);

    const update = <K extends keyof SessionFormValue>(field: K, fieldValue: SessionFormValue[K]) => {
        setForm((prev) => ({ ...prev, [field]: fieldValue }));
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        onSave({
            ...form,
            description: isEmptyRichText(form.description) ? '' : form.description,
        });
        onOpenChange(false);
    };

    const canSubmit = !!form.title && !!form.starts_at && form.duration_minutes >= 15;

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[560px] max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>{isEditing ? editTitle : addTitle}</DialogTitle>
                    <DialogDescription>
                        {isEditing
                            ? 'Update the session details below.'
                            : 'Add a session with its time, type, and any required attendance rules.'}
                    </DialogDescription>
                </DialogHeader>

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div className="space-y-2">
                        <Label htmlFor="sfd-title">Session Title *</Label>
                        <Input
                            id="sfd-title"
                            value={form.title}
                            onChange={(e) => update('title', e.target.value)}
                            placeholder="e.g., Welcome &amp; Keynote"
                            required
                        />
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="sfd-description">Description</Label>
                        <ReactQuill
                            theme="snow"
                            value={form.description || ''}
                            onChange={(content: string) => update('description', content)}
                            placeholder="Brief description of this session..."
                            className="mb-4"
                        />
                    </div>

                    {showSpeakerNames && (
                        <div className="space-y-2">
                            <Label htmlFor="sfd-speakers">Speaker(s)</Label>
                            <Input
                                id="sfd-speakers"
                                value={form.speaker_names || ''}
                                onChange={(e) => update('speaker_names', e.target.value)}
                                placeholder="e.g., Dr. Jane Smith, Prof. John Doe"
                            />
                            <p className="text-xs text-muted-foreground">Separate multiple speakers with commas.</p>
                        </div>
                    )}

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <DateTimePicker
                                label="Start Date &amp; Time *"
                                value={form.starts_at}
                                onDateTimeChange={(v) => update('starts_at', v)}
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="sfd-duration">Duration (minutes) *</Label>
                            <Input
                                id="sfd-duration"
                                type="number"
                                min={15}
                                step={5}
                                value={form.duration_minutes}
                                onChange={(e) => update('duration_minutes', parseInt(e.target.value, 10) || 0)}
                                required
                            />
                            {form.duration_minutes > 0 && form.duration_minutes < 15 && (
                                <p className="text-xs text-destructive">Minimum 15 minutes.</p>
                            )}
                        </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label htmlFor="sfd-session-type">Session Type</Label>
                            <Select
                                value={form.session_type}
                                onValueChange={(v: SessionType) => update('session_type', v)}
                            >
                                <SelectTrigger id="sfd-session-type">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="live">Live</SelectItem>
                                    <SelectItem value="recorded">Recorded / On-demand</SelectItem>
                                    <SelectItem value="hybrid">Hybrid</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        {showDeliveryMode && (
                            <div className="space-y-2">
                                <Label htmlFor="sfd-delivery-mode">Delivery Mode</Label>
                                <Select
                                    value={form.delivery_mode || 'online'}
                                    onValueChange={(v: DeliveryMode) => update('delivery_mode', v)}
                                >
                                    <SelectTrigger id="sfd-delivery-mode">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="online">Online</SelectItem>
                                        <SelectItem value="in_person">In Person</SelectItem>
                                        <SelectItem value="hybrid">Hybrid (in-person + remote)</SelectItem>
                                    </SelectContent>
                                </Select>
                                <p className="text-xs text-muted-foreground">In-person sessions skip video-room provisioning.</p>
                            </div>
                        )}
                    </div>

                    <div className="flex items-center justify-between rounded-md border bg-muted/30 px-3 py-2">
                        <div className="space-y-0.5 pr-3">
                            <Label className="font-medium">{mandatoryLabel}</Label>
                            <p className="text-xs text-muted-foreground">{mandatoryHelp}</p>
                        </div>
                        <Switch
                            checked={form.is_mandatory}
                            onCheckedChange={(checked) => update('is_mandatory', checked)}
                        />
                    </div>

                    {showMinAttendance && form.is_mandatory && (
                        <div className="space-y-2">
                            <Label htmlFor="sfd-min-attendance">Minimum Attendance %</Label>
                            <Input
                                id="sfd-min-attendance"
                                type="number"
                                min={0}
                                max={100}
                                value={form.minimum_attendance_percent ?? 80}
                                onChange={(e) =>
                                    update(
                                        'minimum_attendance_percent',
                                        Math.max(0, Math.min(100, parseInt(e.target.value, 10) || 0)),
                                    )
                                }
                            />
                            <p className="text-xs text-muted-foreground">Attendees must reach this share of the session length.</p>
                        </div>
                    )}

                    {showCpdCredits && (
                        <div className="space-y-2">
                            <Label htmlFor="sfd-cpd-credits">CPD Credits</Label>
                            <Input
                                id="sfd-cpd-credits"
                                type="number"
                                min={0}
                                step={0.25}
                                value={form.cpd_credits ?? 0}
                                onChange={(e) => update('cpd_credits', parseFloat(e.target.value) || 0)}
                            />
                            <p className="text-xs text-muted-foreground">Credits awarded for completing this session.</p>
                        </div>
                    )}

                    <DialogFooter>
                        <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                            Cancel
                        </Button>
                        <Button type="submit" disabled={!canSubmit}>
                            {isEditing ? editTitle : addTitle}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}

export default SessionFormDialog;
