import React, { useState } from 'react';
import { Plus, Trash2, Calendar, Clock, Edit2, Video, GripVertical } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter,
} from '@/components/ui/dialog';
import {
    Card,
    CardContent,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';

export interface SessionDraft {
    id: string; // temporary client ID
    title: string;
    description: string;
    starts_at: string;
    duration_minutes: number;
    timezone: string;
    session_type: 'live' | 'recorded' | 'hybrid';
    zoom_enabled: boolean;
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

const defaultSession = (): SessionDraft => ({
    id: generateId(),
    title: '',
    description: '',
    starts_at: '',
    duration_minutes: 60,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
    session_type: 'live',
    zoom_enabled: true,
    cpd_credits: 0,
    is_mandatory: true,
    minimum_attendance_percent: 80,
});

export function SessionScheduler({ sessions, onChange, disabled }: SessionSchedulerProps) {
    const [editingSession, setEditingSession] = useState<SessionDraft | null>(null);
    const [isDialogOpen, setIsDialogOpen] = useState(false);

    const handleAdd = () => {
        const newSession = defaultSession();
        setEditingSession(newSession);
        setIsDialogOpen(true);
    };

    const handleEdit = (session: SessionDraft) => {
        setEditingSession({ ...session });
        setIsDialogOpen(true);
    };

    const handleDelete = (id: string) => {
        onChange(sessions.filter(s => s.id !== id));
    };

    const handleSave = () => {
        if (!editingSession || !editingSession.title || !editingSession.starts_at) return;

        const exists = sessions.find(s => s.id === editingSession.id);
        if (exists) {
            onChange(sessions.map(s => s.id === editingSession.id ? editingSession : s));
        } else {
            onChange([...sessions, editingSession]);
        }
        setIsDialogOpen(false);
        setEditingSession(null);
    };

    const handleCancel = () => {
        setIsDialogOpen(false);
        setEditingSession(null);
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
                <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleAdd}
                    disabled={disabled}
                >
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
                                        <span className="w-6 text-center font-mono text-sm">
                                            {index + 1}
                                        </span>
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1">
                                            <span className="font-medium truncate">
                                                {session.title || 'Untitled Session'}
                                            </span>
                                            {session.zoom_enabled && (
                                                <Badge variant="secondary" className="text-xs">
                                                    <Video className="mr-1 h-3 w-3" />
                                                    Zoom
                                                </Badge>
                                            )}
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

            {/* Edit/Create Dialog */}
            <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
                <DialogContent className="sm:max-w-lg">
                    <DialogHeader>
                        <DialogTitle>
                            {sessions.find(s => s.id === editingSession?.id)
                                ? 'Edit Session'
                                : 'Add Session'}
                        </DialogTitle>
                    </DialogHeader>

                    {editingSession && (
                        <div className="space-y-4 py-4">
                            <div className="space-y-2">
                                <Label htmlFor="session-title">Session Title *</Label>
                                <Input
                                    id="session-title"
                                    placeholder="e.g., Week 1: Introduction"
                                    value={editingSession.title}
                                    onChange={(e) =>
                                        setEditingSession({ ...editingSession, title: e.target.value })
                                    }
                                />
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="session-desc">Description</Label>
                                <Textarea
                                    id="session-desc"
                                    placeholder="Brief description of this session"
                                    value={editingSession.description}
                                    onChange={(e) =>
                                        setEditingSession({ ...editingSession, description: e.target.value })
                                    }
                                    rows={2}
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label htmlFor="session-start">Start Date & Time *</Label>
                                    <Input
                                        id="session-start"
                                        type="datetime-local"
                                        value={editingSession.starts_at}
                                        onChange={(e) =>
                                            setEditingSession({ ...editingSession, starts_at: e.target.value })
                                        }
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="session-duration">Duration (minutes)</Label>
                                    <Input
                                        id="session-duration"
                                        type="number"
                                        min={15}
                                        step={15}
                                        value={editingSession.duration_minutes}
                                        onChange={(e) =>
                                            setEditingSession({
                                                ...editingSession,
                                                duration_minutes: parseInt(e.target.value) || 60,
                                            })
                                        }
                                    />
                                </div>
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="session-type">Session Type</Label>
                                <Select
                                    value={editingSession.session_type}
                                    onValueChange={(value: 'live' | 'recorded' | 'hybrid') =>
                                        setEditingSession({ ...editingSession, session_type: value })
                                    }
                                >
                                    <SelectTrigger>
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="live">Live Session</SelectItem>
                                        <SelectItem value="recorded">Recorded</SelectItem>
                                        <SelectItem value="hybrid">Hybrid</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="space-y-3 pt-2">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <Label>Enable Zoom Meeting</Label>
                                        <p className="text-xs text-muted-foreground">
                                            Automatically create a Zoom meeting
                                        </p>
                                    </div>
                                    <Switch
                                        checked={editingSession.zoom_enabled}
                                        onCheckedChange={(checked) =>
                                            setEditingSession({ ...editingSession, zoom_enabled: checked })
                                        }
                                    />
                                </div>

                                <div className="flex items-center justify-between">
                                    <div>
                                        <Label>Required for Completion</Label>
                                        <p className="text-xs text-muted-foreground">
                                            Students must attend to complete course
                                        </p>
                                    </div>
                                    <Switch
                                        checked={editingSession.is_mandatory}
                                        onCheckedChange={(checked) =>
                                            setEditingSession({ ...editingSession, is_mandatory: checked })
                                        }
                                    />
                                </div>
                            </div>

                            {editingSession.is_mandatory && (
                                <div className="space-y-2">
                                    <Label htmlFor="min-attendance">Minimum Attendance %</Label>
                                    <Input
                                        id="min-attendance"
                                        type="number"
                                        min={0}
                                        max={100}
                                        value={editingSession.minimum_attendance_percent}
                                        onChange={(e) =>
                                            setEditingSession({
                                                ...editingSession,
                                                minimum_attendance_percent: parseInt(e.target.value) || 80,
                                            })
                                        }
                                    />
                                    <p className="text-xs text-muted-foreground">
                                        Students must attend at least this percentage
                                    </p>
                                </div>
                            )}
                        </div>
                    )}

                    <DialogFooter>
                        <Button type="button" variant="outline" onClick={handleCancel}>
                            Cancel
                        </Button>
                        <Button
                            type="button"
                            onClick={handleSave}
                            disabled={!editingSession?.title || !editingSession?.starts_at}
                        >
                            {sessions.find(s => s.id === editingSession?.id) ? 'Save Changes' : 'Add Session'}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}

export default SessionScheduler;
