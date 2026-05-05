import React, { useState, useEffect, useCallback } from 'react';
import { Plus, Calendar, Video, Edit2, Trash2, Users, Eye, EyeOff } from 'lucide-react';
import { Button } from '@/shared/ui/button';
import { Card, CardContent } from '@/shared/ui/card';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/shared/ui/table';
import { Badge } from '@/shared/ui/badge';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from '@/shared/ui/dialog';
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from '@/shared/ui/alert-dialog';
import { SessionFormDialog, SessionFormValue } from '@/shared/ui/SessionFormDialog';
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

interface SessionsTabProps {
    courseUuid: string;
}

export function SessionsTab({ courseUuid }: SessionsTabProps) {
    const [sessions, setSessions] = useState<CourseSession[]>([]);
    const [loading, setLoading] = useState(true);
    const [manageDialogOpen, setManageDialogOpen] = useState(false);
    const [reconcileSession, setReconcileSession] = useState<CourseSession | null>(null);
    const [editingSession, setEditingSession] = useState<CourseSession | null>(null);
    const [deletingId, setDeletingId] = useState<string | null>(null);

    const fetchSessions = useCallback(async () => {
        try {
            setLoading(true);
            const data = await getCourseSessions(courseUuid);
            // Sort by start date
            data.sort((a, b) => new Date(a.starts_at).getTime() - new Date(b.starts_at).getTime());
            setSessions(data);
        } catch (error) {
            console.error('Failed to fetch sessions:', error);
            toast.error('Failed to load sessions');
        } finally {
            setLoading(false);
        }
    }, [courseUuid]);

    useEffect(() => {
        fetchSessions();
    }, [fetchSessions]);

    const handleOpenAdd = () => {
        setEditingSession(null);
        setManageDialogOpen(true);
    };

    const handleOpenEdit = (session: CourseSession) => {
        setEditingSession(session);
        setManageDialogOpen(true);
    };

    const editingValue = React.useMemo<SessionFormValue | null>(() => {
        if (!editingSession) return null;
        return {
            title: editingSession.title,
            description: editingSession.description || '',
            starts_at: editingSession.starts_at,
            duration_minutes: editingSession.duration_minutes,
            session_type: editingSession.session_type,
            is_mandatory: editingSession.is_mandatory,
            delivery_mode: editingSession.delivery_mode || 'online',
            minimum_attendance_percent: editingSession.minimum_attendance_percent,
        };
    }, [editingSession]);

    const handleSave = async (form: SessionFormValue) => {
        const payload: CourseSessionCreateRequest = {
            title: form.title,
            description: form.description,
            starts_at: form.starts_at,
            duration_minutes: form.duration_minutes,
            session_type: form.session_type,
            delivery_mode: form.delivery_mode || 'online',
            is_mandatory: form.is_mandatory,
            minimum_attendance_percent: form.minimum_attendance_percent ?? 80,
        };

        try {
            if (editingSession) {
                await updateCourseSession(courseUuid, editingSession.uuid, payload);
                toast.success('Session updated');
            } else {
                await createCourseSession(courseUuid, payload);
                toast.success('Session created');
            }
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
                                        <div className="flex items-center gap-2 flex-wrap">
                                            {session.session_type === 'live' && <Video className="h-3 w-3" />}
                                            <span>{session.session_type}</span>
                                            {session.delivery_mode && session.delivery_mode !== 'online' && (
                                                <Badge variant="outline" className="text-[10px] h-4 capitalize">
                                                    {session.delivery_mode === 'in_person' ? 'In person' : session.delivery_mode}
                                                </Badge>
                                            )}
                                        </div>
                                    </TableCell>
                                    <TableCell>
                                        <div className="flex items-center gap-2 flex-wrap">
                                            <Badge variant={session.is_published ? 'default' : 'outline'}>
                                                {session.is_published ? 'Published' : 'Draft'}
                                            </Badge>
                                            {session.status === 'cancelled' && (
                                                <Badge variant="destructive" className="text-[10px] h-4">Cancelled</Badge>
                                            )}
                                            {session.status === 'completed' && (
                                                <Badge variant="secondary" className="text-[10px] h-4">Past</Badge>
                                            )}
                                        </div>
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
            <SessionFormDialog
                open={manageDialogOpen}
                onOpenChange={(open) => {
                    setManageDialogOpen(open);
                    if (!open) setEditingSession(null);
                }}
                value={editingValue}
                onSave={handleSave}
                showDeliveryMode
                showMinAttendance
                mandatoryLabel="Mandatory Session"
                mandatoryHelp="Learners must attend to complete"
            />

            {/* Reconciliation Dialog */}
            <Dialog open={!!reconcileSession} onOpenChange={(open) => !open && setReconcileSession(null)}>
                <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle>Attendance Reconciliation</DialogTitle>
                        <DialogDescription>
                            Match participants to enrolled learners for "{reconcileSession?.title}".
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
