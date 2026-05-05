/**
 * SessionScheduler — inline list of course session drafts (used in
 * CreateCoursePage). The list rendering stays here; the add/edit
 * dialog is the shared SessionFormDialog so courses inherit the same
 * rich-text + DateTimePicker UX as events.
 *
 * Course-creation drafts use a temporary client-side id (`SessionDraft.id`)
 * to track unsaved rows; we translate to/from the shared
 * `SessionFormValue` shape at the dialog boundary.
 */

import React, { useState } from 'react';
import { Plus, Trash2, Calendar, Clock, Edit2, GripVertical } from 'lucide-react';

import { Button } from '@/shared/ui/button';
import { Label } from '@/shared/ui/label';
import { Card, CardContent } from '@/shared/ui/card';
import { Badge } from '@/shared/ui/badge';
import { SessionFormDialog, SessionFormValue } from '@/shared/ui/SessionFormDialog';

export interface SessionDraft {
    id: string; // temporary client ID
    title: string;
    description: string;
    starts_at: string;
    duration_minutes: number;
    timezone: string;
    session_type: 'live' | 'recorded' | 'hybrid';
    cpd_credits: number;
    is_mandatory: boolean;
    minimum_attendance_percent: number;
}

interface SessionSchedulerProps {
    sessions: SessionDraft[];
    onChange: (sessions: SessionDraft[]) => void;
    disabled?: boolean;
}

const generateId = () => Math.random().toString(36).substring(2, 9);

const draftFromForm = (existing: SessionDraft | null, form: SessionFormValue): SessionDraft => ({
    id: existing?.id ?? generateId(),
    title: form.title,
    description: form.description,
    starts_at: form.starts_at,
    duration_minutes: form.duration_minutes,
    timezone: existing?.timezone ?? Intl.DateTimeFormat().resolvedOptions().timeZone ?? 'UTC',
    session_type: form.session_type,
    cpd_credits: form.cpd_credits ?? 0,
    is_mandatory: form.is_mandatory,
    minimum_attendance_percent: form.minimum_attendance_percent ?? 80,
});

const formFromDraft = (s: SessionDraft): SessionFormValue => ({
    title: s.title,
    description: s.description,
    starts_at: s.starts_at,
    duration_minutes: s.duration_minutes,
    session_type: s.session_type,
    is_mandatory: s.is_mandatory,
    cpd_credits: s.cpd_credits,
    minimum_attendance_percent: s.minimum_attendance_percent,
});

export function SessionScheduler({ sessions, onChange, disabled }: SessionSchedulerProps) {
    const [editingId, setEditingId] = useState<string | null>(null);
    const [isDialogOpen, setIsDialogOpen] = useState(false);

    const editingSession = editingId ? sessions.find((s) => s.id === editingId) : null;

    const handleAdd = () => {
        setEditingId(null);
        setIsDialogOpen(true);
    };

    const handleEdit = (session: SessionDraft) => {
        setEditingId(session.id);
        setIsDialogOpen(true);
    };

    const handleDelete = (id: string) => {
        onChange(sessions.filter((s) => s.id !== id));
    };

    const handleSave = (form: SessionFormValue) => {
        if (editingSession) {
            onChange(sessions.map((s) => (s.id === editingSession.id ? draftFromForm(editingSession, form) : s)));
        } else {
            onChange([...sessions, draftFromForm(null, form)]);
        }
        setEditingId(null);
    };

    const formatDateTime = (isoString: string) => {
        if (!isoString) return 'Not set';
        const date = new Date(isoString);
        return date.toLocaleString(undefined, {
            dateStyle: 'medium',
            timeStyle: 'short',
        });
    };

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <Label className="text-base font-medium">Live Sessions</Label>
                <Button type="button" variant="outline" size="sm" onClick={handleAdd} disabled={disabled}>
                    <Plus className="mr-2 h-4 w-4" />
                    Add Session
                </Button>
            </div>

            {sessions.length === 0 ? (
                <div className="border rounded-lg p-8 text-center text-muted-foreground">
                    <Calendar className="mx-auto h-8 w-8 mb-2 opacity-50" />
                    <p className="text-sm">No sessions scheduled yet.</p>
                    <p className="text-xs mt-1">Add live sessions for your hybrid course.</p>
                </div>
            ) : (
                <div className="space-y-2">
                    {sessions.map((session, index) => (
                        <Card key={session.id} className="bg-muted/30">
                            <CardContent className="p-4">
                                <div className="flex items-start gap-3">
                                    <div className="flex items-center gap-2 text-muted-foreground">
                                        <GripVertical className="h-4 w-4" />
                                        <span className="w-6 text-center font-mono text-sm">{index + 1}</span>
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1">
                                            <span className="font-medium truncate">
                                                {session.title || 'Untitled Session'}
                                            </span>
                                            {session.is_mandatory && (
                                                <Badge variant="outline" className="text-xs">
                                                    Required
                                                </Badge>
                                            )}
                                        </div>
                                        <div className="flex items-center gap-4 text-sm text-muted-foreground">
                                            <span className="flex items-center gap-1">
                                                <Calendar className="h-3 w-3" />
                                                {formatDateTime(session.starts_at)}
                                            </span>
                                            <span className="flex items-center gap-1">
                                                <Clock className="h-3 w-3" />
                                                {session.duration_minutes} min
                                            </span>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-1">
                                        <Button
                                            type="button"
                                            variant="ghost"
                                            size="icon"
                                            onClick={() => handleEdit(session)}
                                            disabled={disabled}
                                        >
                                            <Edit2 className="h-4 w-4" />
                                        </Button>
                                        <Button
                                            type="button"
                                            variant="ghost"
                                            size="icon"
                                            onClick={() => handleDelete(session.id)}
                                            disabled={disabled}
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

            <SessionFormDialog
                open={isDialogOpen}
                onOpenChange={(v) => {
                    setIsDialogOpen(v);
                    if (!v) setEditingId(null);
                }}
                value={editingSession ? formFromDraft(editingSession) : null}
                onSave={handleSave}
                showCpdCredits
                showMinAttendance
                mandatoryLabel="Required for Completion"
                mandatoryHelp="Students must attend to complete the course"
            />
        </div>
    );
}

export default SessionScheduler;
