/**
 * SessionEditor — thin wrapper around SessionFormDialog scoped to event sessions.
 *
 * Translates between SessionFormData (event-session row, used elsewhere
 * in the wizard for ordering and persistence) and the shared
 * SessionFormValue. Event sessions enable speaker_names; everything
 * else (delivery_mode, min attendance, cpd credits) is course-only and
 * stays hidden here.
 */

import React from 'react';

import { SessionFormDialog, SessionFormValue } from '@/shared/ui/SessionFormDialog';
import { SessionFormData } from '@/api/events/types';

interface SessionEditorProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    session?: SessionFormData | null;
    onSave: (session: SessionFormData) => void;
    eventStartsAt?: string;
    sessionCount: number;
}

export const SessionEditor = ({
    open,
    onOpenChange,
    session,
    onSave,
    eventStartsAt,
    sessionCount,
}: SessionEditorProps) => {
    const value = React.useMemo<SessionFormValue | null>(() => {
        if (!session) return null;
        return {
            title: session.title,
            description: session.description || '',
            starts_at: session.starts_at,
            duration_minutes: session.duration_minutes,
            session_type: session.session_type,
            is_mandatory: session.is_mandatory,
            speaker_names: session.speaker_names || '',
        };
    }, [session]);

    const handleSave = (next: SessionFormValue) => {
        onSave({
            // Preserve fields the wizard manages outside this dialog —
            // order, is_published, uuid for existing rows.
            ...(session || {}),
            order: session?.order ?? sessionCount,
            is_published: session?.is_published ?? true,
            title: next.title,
            description: next.description,
            starts_at: next.starts_at,
            duration_minutes: next.duration_minutes,
            session_type: next.session_type,
            is_mandatory: next.is_mandatory,
            speaker_names: next.speaker_names || '',
        });
    };

    return (
        <SessionFormDialog
            open={open}
            onOpenChange={onOpenChange}
            value={value}
            onSave={handleSave}
            parentStartsAt={eventStartsAt}
            showSpeakerNames
            mandatoryLabel="Required for Certificate"
            mandatoryHelp="Attendees must complete this session"
        />
    );
};

export default SessionEditor;
