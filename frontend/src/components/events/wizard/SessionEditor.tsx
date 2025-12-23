import React from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import ReactQuill from 'react-quill';
import 'react-quill/dist/quill.snow.css';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { DateTimePicker } from '@/components/ui/date-time-picker';
import { SessionFormData } from '@/api/events/types';

interface SessionEditorProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    session?: SessionFormData | null;
    onSave: (session: SessionFormData) => void;
    eventStartsAt?: string;
    sessionCount: number;
}

const defaultSession: SessionFormData = {
    title: '',
    description: '',
    speaker_names: '',
    order: 0,
    starts_at: '',
    duration_minutes: 60,
    session_type: 'live',
    has_separate_zoom: false,
    is_mandatory: true,
    is_published: true,
};

export const SessionEditor = ({
    open,
    onOpenChange,
    session,
    onSave,
    eventStartsAt,
    sessionCount
}: SessionEditorProps) => {
    const [formData, setFormData] = React.useState<SessionFormData>(defaultSession);
    const isEditing = !!session?.uuid || (session && session.order !== undefined);

    // Initialize form when session prop changes
    React.useEffect(() => {
        if (session) {
            setFormData(session);
        } else {
            // New session - default starts_at to event start time
            setFormData({
                ...defaultSession,
                starts_at: eventStartsAt || '',
                order: sessionCount,
            });
        }
    }, [session, eventStartsAt, sessionCount, open]);

    const handleChange = (field: keyof SessionFormData, value: any) => {
        setFormData(prev => ({ ...prev, [field]: value }));
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        onSave(formData);
        onOpenChange(false);
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[500px]">
                <DialogHeader>
                    <DialogTitle>{isEditing ? 'Edit Session' : 'Add Session'}</DialogTitle>
                    <DialogDescription>
                        {isEditing ? 'Update the session details below.' : 'Add a new session to your event agenda.'}
                    </DialogDescription>
                </DialogHeader>

                <form onSubmit={handleSubmit} className="space-y-4">
                    {/* Title */}
                    <div className="space-y-2">
                        <Label htmlFor="title">Session Title *</Label>
                        <Input
                            id="title"
                            value={formData.title}
                            onChange={(e) => handleChange('title', e.target.value)}
                            placeholder="e.g., Welcome & Keynote"
                            required
                        />
                    </div>

                    {/* Description */}
                    <div className="space-y-2">
                        <Label htmlFor="description">Description</Label>
                        <ReactQuill
                            theme="snow"
                            value={formData.description || ''}
                            onChange={(content: string) => handleChange('description', content)}
                            placeholder="Brief description of this session..."
                            className="bg-white mb-4"
                        />
                    </div>

                    {/* Speaker Names */}
                    <div className="space-y-2">
                        <Label htmlFor="speaker_names">Speaker(s)</Label>
                        <Input
                            id="speaker_names"
                            value={formData.speaker_names || ''}
                            onChange={(e) => handleChange('speaker_names', e.target.value)}
                            placeholder="e.g., Dr. Jane Smith, Prof. John Doe"
                        />
                        <p className="text-xs text-muted-foreground">Separate multiple speakers with commas</p>
                    </div>

                    {/* Timing Row */}
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <DateTimePicker
                                label="Start Time *"
                                value={formData.starts_at}
                                onDateTimeChange={(value) => handleChange('starts_at', value)}
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="duration">Duration (minutes) *</Label>
                            <Input
                                id="duration"
                                type="number"
                                min={5}
                                max={480}
                                value={formData.duration_minutes}
                                onChange={(e) => handleChange('duration_minutes', parseInt(e.target.value) || 60)}
                                required
                            />
                        </div>
                    </div>

                    {/* Session Type */}
                    <div className="space-y-2">
                        <Label htmlFor="session_type">Session Type</Label>
                        <Select
                            value={formData.session_type}
                            onValueChange={(value: 'live' | 'recorded' | 'hybrid') => handleChange('session_type', value)}
                        >
                            <SelectTrigger>
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="live">Live Session</SelectItem>
                                <SelectItem value="recorded">Recorded / On-demand</SelectItem>
                                <SelectItem value="hybrid">Hybrid</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>

                    {/* Toggles */}
                    <div className="space-y-3">
                        <div className="flex items-center justify-between">
                            <div className="space-y-0.5">
                                <Label>Separate Zoom Meeting</Label>
                                <p className="text-xs text-muted-foreground">Create a separate Zoom link for this session</p>
                            </div>
                            <Switch
                                checked={formData.has_separate_zoom}
                                onCheckedChange={(checked) => handleChange('has_separate_zoom', checked)}
                            />
                        </div>

                        <div className="flex items-center justify-between">
                            <div className="space-y-0.5">
                                <Label>Required for Certificate</Label>
                                <p className="text-xs text-muted-foreground">Attendees must complete this session</p>
                            </div>
                            <Switch
                                checked={formData.is_mandatory}
                                onCheckedChange={(checked) => handleChange('is_mandatory', checked)}
                            />
                        </div>
                    </div>

                    <DialogFooter>
                        <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                            Cancel
                        </Button>
                        <Button type="submit" disabled={!formData.title || !formData.starts_at}>
                            {isEditing ? 'Update Session' : 'Add Session'}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
};
