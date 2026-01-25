import React, { useState, useEffect, useCallback } from 'react';
import { Plus, Calendar, Video, Edit2, Trash2, Users, Eye, EyeOff, AlertTriangle, Link2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import {
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from '@/components/ui/tooltip';
import {
    Alert,
    AlertDescription,
    AlertTitle,
} from '@/components/ui/alert';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
    DialogFooter,
} from '@/components/ui/dialog';
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import {
    getCourseSessions,
    createCourseSession,
    updateCourseSession,
    deleteCourseSession,
    publishCourseSession,
    unpublishCourseSession
} from '@/api/courses';
import { CourseSession, CourseSessionCreateRequest } from '@/api/courses/types';
import { SessionAttendanceReconciliation } from '@/components/courses/SessionAttendanceReconciliation';
import { toast } from 'sonner';
import { getZoomStatus, initiateZoomOAuth } from '@/api/integrations';

interface SessionsTabProps {
    courseUuid: string;
}

interface SessionFormData {
    title: string;
    description: string;
    starts_at: string;
    duration_minutes: number;
    session_type: 'live' | 'recorded' | 'hybrid';
    zoom_enabled: boolean;
    zoom_meeting_id: string;
    zoom_password: string;
    is_mandatory: boolean;
    minimum_attendance_percent: number;
}

export function SessionsTab({ courseUuid }: SessionsTabProps) {
    const [sessions, setSessions] = useState<CourseSession[]>([]);
    const [loading, setLoading] = useState(true);
    const [zoomConnected, setZoomConnected] = useState<boolean | null>(null);
    const [manageDialogOpen, setManageDialogOpen] = useState(false);
    const [reconcileSession, setReconcileSession] = useState<CourseSession | null>(null);
    const [editingSession, setEditingSession] = useState<CourseSession | null>(null);
    const [deletingId, setDeletingId] = useState<string | null>(null);

    // Form State
    const [formData, setFormData] = useState<SessionFormData>({
        title: '',
        description: '',
        starts_at: '',
        duration_minutes: 60,
        session_type: 'live',
        zoom_enabled: true,
        zoom_meeting_id: '',
        zoom_password: '',
        is_mandatory: false,
        minimum_attendance_percent: 80,
    });

    const checkZoomStatus = useCallback(async () => {
        try {
            const status = await getZoomStatus();
            setZoomConnected(status.is_connected);
        } catch (e) {
            console.error('Failed to check Zoom status', e);
            // Default to true to avoid nagging if API fails? Or false?
            // False is safer to prompt connection.
            setZoomConnected(false);
        }
    }, []);

    const fetchSessions = useCallback(async () => {
        try {
            setLoading(true);
            const [data] = await Promise.all([
                getCourseSessions(courseUuid),
                checkZoomStatus()
            ]);
            // Sort by start date
            data.sort((a, b) => new Date(a.starts_at).getTime() - new Date(b.starts_at).getTime());
            setSessions(data);
        } catch (error) {
            console.error('Failed to fetch sessions:', error);
            toast.error('Failed to load sessions');
        } finally {
            setLoading(false);
        }
    }, [courseUuid, checkZoomStatus]);

    useEffect(() => {
        fetchSessions();
    }, [fetchSessions]);

    const handleConnectZoom = async () => {
        try {
            const authUrl = await initiateZoomOAuth();
            window.location.href = authUrl;
        } catch (e) {
            console.error('Failed to initiate Zoom connection', e);
            toast.error('Failed to connect to Zoom');
        }
    };

    const handleOpenAdd = () => {
        setEditingSession(null);
        setFormData({
            title: '',
            description: '',
            starts_at: '',
            duration_minutes: 60,
            session_type: 'live',
            zoom_enabled: true,
            zoom_meeting_id: '',
            zoom_password: '',
            is_mandatory: false,
            minimum_attendance_percent: 80,
        });
        setManageDialogOpen(true);
    };

    const handleOpenEdit = (session: CourseSession) => {
        setEditingSession(session);
        
        // Convert ISO datetime to datetime-local format (YYYY-MM-DDTHH:mm)
        let datetimeLocalValue = '';
        if (session.starts_at) {
            try {
                const date = new Date(session.starts_at);
                // Format to YYYY-MM-DDTHH:mm (required for datetime-local input)
                datetimeLocalValue = date.toISOString().slice(0, 16);
            } catch (e) {
                console.error('Failed to parse session start time:', e);
            }
        }
        
        setFormData({
            title: session.title,
            description: session.description || '',
            starts_at: datetimeLocalValue,
            duration_minutes: session.duration_minutes,
            session_type: session.session_type,
            // If ID exists OR error exists, we assume it was meant to be enabled
            zoom_enabled: Boolean(session.zoom_meeting_id) || Boolean(session.zoom_error),
            zoom_meeting_id: session.zoom_meeting_id || '',
            zoom_password: session.zoom_password || '',
            is_mandatory: session.is_mandatory,
            minimum_attendance_percent: session.minimum_attendance_percent,
        });
        setManageDialogOpen(true);
    };

    const handleSave = async () => {
        if (!formData.title || !formData.starts_at) {
            toast.error('Please fill in required fields (Title, Start Time)');
            return;
        }

        const payload: CourseSessionCreateRequest = {
            title: formData.title,
            description: formData.description,
            starts_at: formData.starts_at,
            duration_minutes: formData.duration_minutes,
            session_type: formData.session_type,
            is_mandatory: formData.is_mandatory,
            minimum_attendance_percent: formData.minimum_attendance_percent,
            zoom_settings: { enabled: formData.zoom_enabled },
            zoom_meeting_id: formData.zoom_meeting_id || undefined,
            zoom_password: formData.zoom_password || undefined,
        };

        try {
            if (editingSession) {
                await updateCourseSession(courseUuid, editingSession.uuid, payload);
                toast.success('Session updated');
            } else {
                await createCourseSession(courseUuid, payload);
                toast.success('Session created');
            }
            setManageDialogOpen(false);
            fetchSessions();
        } catch (error: any) {
            console.error('Failed to save session:', error);
            toast.error(error?.response?.data?.message || 'Failed to save session');
        }
    };

    const handleDelete = async () => {
        if (!deletingId) return;
        try {
            await deleteCourseSession(courseUuid, deletingId);
            toast.success('Session deleted');
            setDeletingId(null);
            fetchSessions();
        } catch (_error) {
            toast.error('Failed to delete session');
        }
    };

    const handleTogglePublish = async (session: CourseSession) => {
        try {
            if (session.is_published) {
                await unpublishCourseSession(courseUuid, session.uuid);
                toast.success('Session unpublished');
            } else {
                await publishCourseSession(courseUuid, session.uuid);
                toast.success('Session published');
            }
            fetchSessions();
        } catch (_error) {
            toast.error('Failed to update status');
        }
    };


    return (
        <div className="space-y-6">
            {!loading && zoomConnected === false && (
                <Alert variant="destructive" className="bg-warning-subtle border-warning text-warning">
                    <AlertTriangle className="h-4 w-4 icon-warning" />
                    <AlertTitle>Zoom Not Connected</AlertTitle>
                    <AlertDescription className="mt-2 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                        <span>
                            To automatically create meetings and track attendance, you must connect your Zoom account.
                        </span>
                        <Button size="sm" variant="outline" className="border-warning-muted hover:bg-warning-subtle" onClick={handleConnectZoom}>
                            <Link2 className="h-4 w-4 mr-2" />
                            Connect Zoom
                        </Button>
                    </AlertDescription>
                </Alert>
            )}

            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div>
                    <h2 className="text-lg font-medium">Course Sessions</h2>
                    <p className="text-sm text-muted-foreground">Manage live and hybrid sessions for this course.</p>
                </div>
                <Button onClick={handleOpenAdd}>
                    <Plus className="mr-2 h-4 w-4" />
                    Add Session
                </Button>
            </div>

            {sessions.length === 0 && !loading ? (
                <Card>
                    <CardContent className="py-12 flex flex-col items-center justify-center text-center">
                        <Calendar className="h-12 w-12 text-muted-foreground mb-4" />
                        <h3 className="text-lg font-medium mb-1">No sessions scheduled</h3>
                        <p className="text-sm text-muted-foreground max-w-sm mb-4">
                            Create your first session to get started with hybrid learning events.
                        </p>
                        <Button onClick={handleOpenAdd} variant="outline">
                            Schedule Session
                        </Button>
                    </CardContent>
                </Card>
            ) : (
                <div className="border rounded-md">
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>Title</TableHead>
                                <TableHead>Date & Time</TableHead>
                                <TableHead>Duration</TableHead>
                                <TableHead>Type</TableHead>
                                <TableHead>Status</TableHead>
                                <TableHead className="text-right">Actions</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {sessions.map((session) => (
                                <TableRow key={session.uuid}>
                                    <TableCell className="font-medium">
                                        {session.title}
                                        {session.is_mandatory && (
                                            <Badge variant="secondary" className="ml-2 text-[10px] h-4">Mandatory</Badge>
                                        )}
                                    </TableCell>
                                    <TableCell>
                                        {new Date(session.starts_at).toLocaleString()}
                                    </TableCell>
                                    <TableCell>{session.duration_minutes} min</TableCell>
                                    <TableCell className="capitalize">
                                        <div className="flex items-center gap-2">
                                            {session.session_type === 'live' && <Video className="h-3 w-3" />}
                                            {session.session_type}
                                            {(session.zoom_error || (session.session_type === 'live' && !session.zoom_meeting_id)) && (
                                                <TooltipProvider>
                                                    <Tooltip>
                                                        <TooltipTrigger asChild>
                                                            <div className="text-amber-500 cursor-help">
                                                                <AlertTriangle className="h-4 w-4" />
                                                            </div>
                                                        </TooltipTrigger>
                                                        <TooltipContent>
                                                            <p className="max-w-xs">{session.zoom_error || 'No Zoom meeting linked. Check creator Zoom connection.'}</p>
                                                        </TooltipContent>
                                                    </Tooltip>
                                                </TooltipProvider>
                                            )}
                                        </div>
                                    </TableCell>
                                    <TableCell>
                                        <Badge variant={session.is_published ? 'default' : 'outline'}>
                                            {session.is_published ? 'Published' : 'Draft'}
                                        </Badge>
                                    </TableCell>
                                    <TableCell className="text-right">
                                        <div className="flex items-center justify-end gap-2">
                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                onClick={() => handleTogglePublish(session)}
                                                title={session.is_published ? "Unpublish" : "Publish"}
                                            >
                                                {session.is_published ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
                                            </Button>

                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                onClick={() => setReconcileSession(session)}
                                                title="Attendance Reconciliation"
                                            >
                                                <Users className="h-4 w-4" />
                                            </Button>

                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                onClick={() => handleOpenEdit(session)}
                                            >
                                                <Edit2 className="h-4 w-4" />
                                            </Button>

                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                className="text-destructive hover:bg-destructive/90"
                                                onClick={() => setDeletingId(session.uuid)}
                                            >
                                                <Trash2 className="h-4 w-4" />
                                            </Button>
                                        </div>
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </div>
            )}

            {/* Manage Dialog (Add/Edit) */}
            <Dialog open={manageDialogOpen} onOpenChange={setManageDialogOpen}>
                <DialogContent className="sm:max-w-lg">
                    <DialogHeader>
                        <DialogTitle>{editingSession ? 'Edit' : 'Schedule'} Session</DialogTitle>
                        <DialogDescription>
                            Configure the session details and Zoom integration.
                        </DialogDescription>
                    </DialogHeader>

                    <div className="space-y-4 py-4 max-h-[60vh] overflow-y-auto px-1">
                        <div className="space-y-2">
                            <Label htmlFor="title">Title</Label>
                            <Input
                                id="title"
                                value={formData.title}
                                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                                placeholder="e.g. Introduction & Key Concepts"
                            />
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="starts_at">Start Time</Label>
                                <Input
                                    id="starts_at"
                                    type="datetime-local"
                                    value={formData.starts_at}
                                    onChange={(e) => setFormData({ ...formData, starts_at: e.target.value })}
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="duration">Duration (min)</Label>
                                <Input
                                    id="duration"
                                    type="number"
                                    min="15"
                                    value={formData.duration_minutes}
                                    onChange={(e) => setFormData({ ...formData, duration_minutes: parseInt(e.target.value) || 0 })}
                                />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="description">Description (Optional)</Label>
                            <Textarea
                                id="description"
                                value={formData.description}
                                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                            />
                        </div>

                        <div className="space-y-2">
                            <Label>Session Type</Label>
                            <Select
                                value={formData.session_type}
                                onValueChange={(val: any) => setFormData({ ...formData, session_type: val })}
                            >
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="live">Live (Zoom)</SelectItem>
                                    <SelectItem value="hybrid">Hybrid (In-person + Zoom)</SelectItem>
                                    <SelectItem value="recorded">Recorded / Webinar</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="flex items-center justify-between pt-2">
                            <div className="space-y-0.5">
                                <Label>Enable Zoom Meeting</Label>
                                <p className="text-xs text-muted-foreground">Auto-create Zoom meeting</p>
                            </div>
                            <Switch
                                checked={formData.zoom_enabled}
                                onCheckedChange={(checked) => setFormData({ ...formData, zoom_enabled: checked })}
                            />
                        </div>

                        {(formData.zoom_enabled || formData.session_type === 'live') && (
                            <div className="border-l-2 border-primary/20 pl-4 space-y-3">
                                <div className="space-y-1">
                                    <Label htmlFor="zoom_meeting_id" className="text-xs">Zoom Meeting ID (Optional)</Label>
                                    <Input
                                        id="zoom_meeting_id"
                                        placeholder="Leave blank to auto-create"
                                        value={formData.zoom_meeting_id}
                                        onChange={(e) => setFormData({ ...formData, zoom_meeting_id: e.target.value })}
                                        className="h-8"
                                    />
                                    <p className="text-[10px] text-muted-foreground">Normally auto-generated. Enter manually only if using an external meeting.</p>
                                </div>
                                <div className="space-y-1">
                                    <Label htmlFor="zoom_password" className="text-xs">Passcode (Optional)</Label>
                                    <Input
                                        id="zoom_password"
                                        value={formData.zoom_password}
                                        onChange={(e) => setFormData({ ...formData, zoom_password: e.target.value })}
                                        className="h-8"
                                    />
                                </div>
                            </div>
                        )}

                        <div className="flex items-center justify-between pt-2">
                            <div className="space-y-0.5">
                                <Label>Mandatory Session</Label>
                                <p className="text-xs text-muted-foreground">Learners must attend to complete</p>
                            </div>
                            <Switch
                                checked={formData.is_mandatory}
                                onCheckedChange={(checked) => setFormData({ ...formData, is_mandatory: checked })}
                            />
                        </div>
                    </div>

                    <DialogFooter>
                        <Button variant="outline" onClick={() => setManageDialogOpen(false)}>Cancel</Button>
                        <Button onClick={handleSave}>Save Session</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Reconciliation Dialog */}
            <Dialog open={!!reconcileSession} onOpenChange={(open) => !open && setReconcileSession(null)}>
                <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle>Attendance Reconciliation</DialogTitle>
                        <DialogDescription>
                            Match Zoom participants to enrolled learners for "{reconcileSession?.title}".
                        </DialogDescription>
                    </DialogHeader>
                    {reconcileSession && (
                        <SessionAttendanceReconciliation
                            courseUuid={courseUuid}
                            sessionUuid={reconcileSession.uuid}
                            onReconciled={() => {
                                // Maybe refresh logic if needed
                            }}
                        />
                    )}
                </DialogContent>
            </Dialog>

            {/* Delete Alert */}
            <AlertDialog open={!!deletingId} onOpenChange={(open) => !open && setDeletingId(null)}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Delete Session?</AlertDialogTitle>
                        <AlertDialogDescription>
                            This will permanently delete this session and all associated attendance records. This cannot be undone.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction className="bg-destructive hover:bg-destructive/90" onClick={handleDelete}>
                            Delete
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    );
}
