import React, { useState, useMemo } from 'react';
import { useEventWizard } from '../EventWizardContext';
import { DateTimePicker } from '@/components/ui/date-time-picker';
import { Clock, Plus, Edit2, Trash2, GripVertical, Video, Users } from 'lucide-react';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { SessionEditor } from '../SessionEditor';
import { SessionFormData } from '@/api/events/types';

export const StepSchedule = () => {
    const { formData, updateFormData } = useEventWizard();

    // Session editor state
    const [sessionEditorOpen, setSessionEditorOpen] = useState(false);
    const [editingSession, setEditingSession] = useState<SessionFormData | null>(null);

    // Get sessions from form data
    const sessions = formData._sessions || [];

    // Calculate end time from start + duration (derived, not stored)
    const calculatedEndTime = useMemo(() => {
        if (!formData.starts_at || !formData.duration_minutes) return null;
        const start = new Date(formData.starts_at);
        if (isNaN(start.getTime())) return null;
        return new Date(start.getTime() + formData.duration_minutes * 60000);
    }, [formData.starts_at, formData.duration_minutes]);

    // Parse duration into hours and minutes for display
    const durationHours = Math.floor((formData.duration_minutes || 0) / 60);
    const durationMins = (formData.duration_minutes || 0) % 60;

    const handleStartChange = (value: string) => {
        updateFormData({ starts_at: value });
    };

    const handleDurationChange = (hours: number, mins: number) => {
        const totalMinutes = (hours * 60) + mins;
        if (totalMinutes >= 0) {
            updateFormData({ duration_minutes: totalMinutes });
        }
    };

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
        const timeFormat: Intl.DateTimeFormatOptions = { hour: 'numeric', minute: '2-digit' };
        return `${start.toLocaleTimeString(undefined, timeFormat)} - ${end.toLocaleTimeString(undefined, timeFormat)}`;
    };

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-300">
            <div className="space-y-2">
                <h2 className="text-xl font-semibold text-foreground">Schedule</h2>
                <p className="text-sm text-muted-foreground">When will your event take place?</p>
            </div>

            <div className="grid gap-6">
                {/* Start Date/Time */}
                <div className="space-y-2">
                    <DateTimePicker
                        label="Start Date & Time"
                        value={formData.starts_at}
                        onDateTimeChange={handleStartChange}
                    />
                </div>

                {/* Duration Input */}
                <div className="space-y-2">
                    <Label>Duration</Label>
                    <div className="flex items-center gap-3">
                        <div className="flex items-center gap-2">
                            <Input
                                type="number"
                                min={0}
                                max={24}
                                value={durationHours}
                                onChange={(e) => handleDurationChange(parseInt(e.target.value) || 0, durationMins)}
                                className="w-20 text-center"
                            />
                            <span className="text-muted-foreground">hours</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <Input
                                type="number"
                                min={0}
                                max={59}
                                step={5}
                                value={durationMins}
                                onChange={(e) => handleDurationChange(durationHours, parseInt(e.target.value) || 0)}
                                className="w-20 text-center"
                            />
                            <span className="text-muted-foreground">minutes</span>
                        </div>
                    </div>
                    {(formData.duration_minutes || 0) < 15 && (
                        <p className="text-xs text-red-500">Minimum 15 minutes required</p>
                    )}
                </div>

                {/* Calculated End Time & Summary */}
                <div className="flex items-center gap-4 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950/30 dark:to-indigo-950/30 rounded-lg border border-info">
                    <div className="h-12 w-12 rounded-full bg-neutral-card shadow-sm flex items-center justify-center text-blue-600">
                        <Clock className="h-6 w-6" />
                    </div>
                    <div className="flex-1">
                        <p className="text-sm font-medium text-muted-foreground">Event Time</p>
                        <p className="text-lg font-semibold text-foreground">
                            {formData.starts_at && calculatedEndTime ? (
                                <>
                                    {new Date(formData.starts_at).toLocaleString(undefined, {
                                        weekday: 'short',
                                        month: 'short',
                                        day: 'numeric',
                                        hour: 'numeric',
                                        minute: '2-digit'
                                    })}
                                    {' → '}
                                    {calculatedEndTime.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })}
                                </>
                            ) : (
                                <span className="text-muted-foreground">Set start time and duration</span>
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
                                                        {session.has_separate_zoom && (
                                                            <Badge variant="outline" className="shrink-0">
                                                                <Video className="h-3 w-3 mr-1" />
                                                                Separate Zoom
                                                            </Badge>
                                                        )}
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

                                                    {session.description && (
                                                        <p className="text-sm text-muted-foreground mt-1 line-clamp-1">
                                                            {session.description}
                                                        </p>
                                                    )}
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
