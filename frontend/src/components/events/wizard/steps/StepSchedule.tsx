import React, { useState, useMemo } from 'react';
import { useEventWizard } from '../EventWizardContext';
import { DateTimePicker } from '@/shared/ui/date-time-picker';
import { Clock, Plus, Edit2, Trash2, GripVertical, Users } from 'lucide-react';
import { Label } from '@/shared/ui/label';
import { Switch } from '@/shared/ui/switch';
import { Button } from '@/shared/ui/button';
import { Card, CardContent } from '@/shared/ui/card';
import { Badge } from '@/shared/ui/badge';
import { SessionEditor } from '../SessionEditor';
import { SessionFormData } from '@/api/events/types';

// The wizard form state stores `starts_at` + `duration_minutes` (matching
// the backend write contract). The picker UX exposes start + end. These
// helpers keep the conversion in one place.
function endsAtFromForm(startsAt: string | undefined, durationMinutes: number | undefined): string {
    if (!startsAt || !durationMinutes) return '';
    const start = new Date(startsAt);
    if (isNaN(start.getTime())) return '';
    const end = new Date(start.getTime() + durationMinutes * 60000);
    // datetime-local expects "YYYY-MM-DDTHH:mm" in local time. The
    // DateTimePicker component normalises whichever string it gets back
    // through its own onDateTimeChange path, so an ISO string is fine
    // here too.
    return end.toISOString();
}

function durationMinutesFromRange(startsAt: string, endsAt: string): number {
    const start = new Date(startsAt).getTime();
    const end = new Date(endsAt).getTime();
    if (isNaN(start) || isNaN(end)) return 0;
    return Math.max(0, Math.round((end - start) / 60000));
}

export const StepSchedule = () => {
    const { formData, updateFormData } = useEventWizard();

    // Session editor state
    const [sessionEditorOpen, setSessionEditorOpen] = useState(false);
    const [editingSession, setEditingSession] = useState<SessionFormData | null>(null);

    // Get sessions from form data
    const sessions = formData._sessions || [];

    // Derived end-time string for the picker. We don't persist `ends_at`;
    // the form state continues to write `duration_minutes` so the API
    // contract is unchanged. End is recomputed on every render from
    // (starts_at, duration_minutes).
    const endsAtValue = useMemo(
        () => endsAtFromForm(formData.starts_at, formData.duration_minutes),
        [formData.starts_at, formData.duration_minutes],
    );

    const calculatedEndTime = useMemo(() => {
        if (!endsAtValue) return null;
        const d = new Date(endsAtValue);
        return isNaN(d.getTime()) ? null : d;
    }, [endsAtValue]);

    const handleStartChange = (value: string) => {
        // Preserve duration when start moves: the user shifted the event,
        // they didn't redefine its length. We only re-derive duration
        // when the END picker changes.
        updateFormData({ starts_at: value });
    };

    const handleEndChange = (value: string) => {
        if (!formData.starts_at || !value) return;
        const minutes = durationMinutesFromRange(formData.starts_at, value);
        updateFormData({ duration_minutes: minutes });
    };

    // Validation surfaces — both shown inline under the End picker.
    const endsBeforeStart = useMemo(() => {
        if (!formData.starts_at || !endsAtValue) return false;
        return new Date(endsAtValue).getTime() < new Date(formData.starts_at).getTime();
    }, [formData.starts_at, endsAtValue]);
    const tooShort = (formData.duration_minutes || 0) < 15;

    const handleMultiSessionToggle = (enabled: boolean) => {
        updateFormData({ is_multi_session: enabled });
        if (!enabled) {
            updateFormData({ _sessions: [] });
        }
    };

    const handleAddSession = () => {
        setEditingSession(null);
        setSessionEditorOpen(true);
    };

    const handleEditSession = (session: SessionFormData) => {
        setEditingSession(session);
        setSessionEditorOpen(true);
    };

    const handleSaveSession = (session: SessionFormData) => {
        const existingSessions = formData._sessions || [];
        const existingIndex = existingSessions.findIndex(
            s => s.order === session.order && s.title === editingSession?.title
        );

        if (existingIndex >= 0) {
            const updated = [...existingSessions];
            updated[existingIndex] = session;
            updateFormData({ _sessions: updated });
        } else {
            updateFormData({ _sessions: [...existingSessions, session] });
        }
    };

    const handleDeleteSession = (index: number) => {
        const updated = [...sessions];
        updated.splice(index, 1);
        updated.forEach((s, i) => s.order = i);
        updateFormData({ _sessions: updated });
    };

    const formatSessionTime = (startsAt: string, durationMins: number) => {
        const start = new Date(startsAt);
        if (isNaN(start.getTime())) return '';
        const end = new Date(start.getTime() + durationMins * 60000);
        const dateFormat: Intl.DateTimeFormatOptions = {
            weekday: 'short',
            month: 'short',
            day: 'numeric',
        };
        const timeFormat: Intl.DateTimeFormatOptions = { hour: 'numeric', minute: '2-digit' };
        return `${start.toLocaleDateString(undefined, dateFormat)} · ${start.toLocaleTimeString(undefined, timeFormat)} – ${end.toLocaleTimeString(undefined, timeFormat)}`;
    };

    const stripHtml = (html: string) =>
        html
            .replace(/<br\s*\/?>/gi, ' ')
            .replace(/<[^>]*>/g, '')
            .replace(/&nbsp;/g, ' ')
            .trim();

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-300">
            <div className="space-y-2">
                <h2 className="text-xl font-semibold text-foreground">Schedule</h2>
                <p className="text-sm text-muted-foreground">When will your event take place?</p>
            </div>

            <div className="grid gap-6 sm:grid-cols-2">
                {/* Start Date/Time */}
                <div className="space-y-2">
                    <DateTimePicker
                        label="Start Date & Time"
                        value={formData.starts_at}
                        onDateTimeChange={handleStartChange}
                    />
                </div>

                {/* End Date/Time */}
                <div className="space-y-2">
                    <DateTimePicker
                        label="End Date & Time"
                        value={endsAtValue}
                        onDateTimeChange={handleEndChange}
                    />
                    {endsBeforeStart ? (
                        <p className="text-xs text-red-500">End must be after start.</p>
                    ) : tooShort && (formData.duration_minutes || 0) > 0 ? (
                        <p className="text-xs text-red-500">Event must run at least 15 minutes.</p>
                    ) : null}
                </div>
            </div>

            <div className="grid gap-6">
                {/* Calculated End Time & Summary */}
                <div className="flex items-center gap-4 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950/30 dark:to-indigo-950/30 rounded-lg border border-info">
                    <div className="h-12 w-12 rounded-full bg-neutral-card shadow-sm flex items-center justify-center text-blue-600">
                        <Clock className="h-6 w-6" />
                    </div>
                    <div className="flex-1">
                        <p className="text-sm font-medium text-muted-foreground">Event Time</p>
                        <p className="text-lg font-semibold text-foreground">
                            {formData.starts_at && calculatedEndTime ? (() => {
                                const start = new Date(formData.starts_at);
                                const sameDay =
                                    start.getFullYear() === calculatedEndTime.getFullYear() &&
                                    start.getMonth() === calculatedEndTime.getMonth() &&
                                    start.getDate() === calculatedEndTime.getDate();
                                const startFmt: Intl.DateTimeFormatOptions = {
                                    weekday: 'short',
                                    month: 'short',
                                    day: 'numeric',
                                    hour: 'numeric',
                                    minute: '2-digit',
                                };
                                // Same-day events: collapse the end side to time-only
                                // (showing the date twice is noise). Multi-day: show
                                // the full end date so the range reads correctly.
                                const endFmt: Intl.DateTimeFormatOptions = sameDay
                                    ? { hour: 'numeric', minute: '2-digit' }
                                    : startFmt;
                                return (
                                    <>
                                        {start.toLocaleString(undefined, startFmt)}
                                        {' → '}
                                        {calculatedEndTime.toLocaleString(undefined, endFmt)}
                                    </>
                                );
                            })() : (
                                <span className="text-muted-foreground">Set start and end time</span>
                            )}
                        </p>
                    </div>
                    <div className="text-right">
                        <p className="text-xs text-muted-foreground uppercase">Timezone</p>
                        <p className="font-medium text-foreground">{formData.timezone}</p>
                    </div>
                </div>

                {/* Multi-Session Toggle */}
                <div className="flex items-center justify-between p-4 bg-card rounded-lg border border-border">
                    <div className="space-y-0.5">
                        <Label className="text-base font-medium">Multiple Sessions / Agenda</Label>
                        <p className="text-sm text-muted-foreground">
                            Add individual sessions with speakers, times, and descriptions
                        </p>
                    </div>
                    <Switch
                        checked={formData.is_multi_session || false}
                        onCheckedChange={handleMultiSessionToggle}
                    />
                </div>

                {/* Sessions List */}
                {formData.is_multi_session && (
                    <div className="space-y-4">
                        <div className="flex items-center justify-between">
                            <h3 className="text-lg font-medium text-foreground">Sessions</h3>
                            <Button onClick={handleAddSession} size="sm">
                                <Plus className="h-4 w-4 mr-2" />
                                Add Session
                            </Button>
                        </div>

                        {sessions.length === 0 ? (
                            <Card className="border-dashed">
                                <CardContent className="py-8 text-center text-muted-foreground">
                                    <Clock className="h-8 w-8 mx-auto mb-2 opacity-50" />
                                    <p>No sessions added yet.</p>
                                    <p className="text-sm">Click "Add Session" to create your event agenda.</p>
                                </CardContent>
                            </Card>
                        ) : (
                            <div className="space-y-3">
                                {sessions.map((session, index) => (
                                    <Card key={index} className="hover:shadow-md transition-shadow">
                                        <CardContent className="p-4">
                                            <div className="flex items-start gap-3">
                                                <div className="flex items-center text-muted-foreground pt-1">
                                                    <GripVertical className="h-4 w-4" />
                                                </div>

                                                <div className="flex-1 min-w-0">
                                                    <div className="flex items-center gap-2 mb-1">
                                                        <h4 className="font-semibold text-foreground truncate">
                                                            {session.title}
                                                        </h4>
                                                        {session.is_mandatory && (
                                                            <Badge variant="secondary" className="shrink-0">
                                                                Required
                                                            </Badge>
                                                        )}
                                                    </div>

                                                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                                                        <span className="flex items-center gap-1">
                                                            <Clock className="h-3 w-3" />
                                                            {formatSessionTime(session.starts_at, session.duration_minutes)}
                                                        </span>
                                                        {session.speaker_names && (
                                                            <span className="flex items-center gap-1">
                                                                <Users className="h-3 w-3" />
                                                                {session.speaker_names}
                                                            </span>
                                                        )}
                                                    </div>

                                                    {(() => {
                                                        const plain = session.description ? stripHtml(session.description) : '';
                                                        return plain ? (
                                                            <p className="text-sm text-muted-foreground mt-1 line-clamp-1">
                                                                {plain}
                                                            </p>
                                                        ) : null;
                                                    })()}
                                                </div>

                                                <div className="flex items-center gap-1 shrink-0">
                                                    <Button
                                                        variant="ghost"
                                                        size="icon"
                                                        onClick={() => handleEditSession(session)}
                                                    >
                                                        <Edit2 className="h-4 w-4" />
                                                    </Button>
                                                    <Button
                                                        variant="ghost"
                                                        size="icon"
                                                        onClick={() => handleDeleteSession(index)}
                                                        className="text-destructive hover:text-destructive"
                                                    >
                                                        <Trash2 className="h-4 w-4" />
                                                    </Button>
                                                </div>
                                            </div>
                                        </CardContent>
                                    </Card>
                                ))}
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Session Editor Dialog */}
            <SessionEditor
                open={sessionEditorOpen}
                onOpenChange={setSessionEditorOpen}
                session={editingSession}
                onSave={handleSaveSession}
                eventStartsAt={formData.starts_at}
                sessionCount={sessions.length}
            />
        </div>
    );
};
