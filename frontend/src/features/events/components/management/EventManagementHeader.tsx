import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Clock, Trash2 } from 'lucide-react';
import { Button } from '@/shared/ui/button';
import { PageHeader } from '@/components/custom/PageHeader';
import { StatusBadge } from '@/components/custom/StatusBadge';
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
    AlertDialogTrigger,
} from '@/shared/ui/alert-dialog';
import { JoinButton } from '@/components/video/JoinButton';
import { toast } from 'sonner';
import { usePublishEvent, useUnpublishEvent, useDeleteEventMutation } from '../../hooks';
import type { Event } from '../../types';

interface EventStats {
    registered: number;
    checkedIn: number;
    issued: number;
    feedbackCount: number;
}

interface EventManagementHeaderProps {
    event: Event;
    stats: EventStats;
    isLive: boolean;
    hasStarted: boolean;
}

export function EventManagementHeader({
    event,
    stats,
    isLive,
    hasStarted,
}: EventManagementHeaderProps) {
    const navigate = useNavigate();
    const isEventHost = !!event.is_current_user_host;

    const { mutate: publish, isPending: publishing } = usePublishEvent(event.uuid);
    const { mutate: unpublish, isPending: unpublishing } = useUnpublishEvent(event.uuid);
    const { mutate: deleteEv, isPending: deleting } = useDeleteEventMutation(event.uuid);

    const handlePublish = () => {
        publish(undefined, {
            onSuccess: () => toast.success("Event published successfully! It's now visible to the public."),
            onError: (e: any) =>
                toast.error(e?.response?.data?.message ?? 'Failed to publish event'),
        });
    };

    const handleUnpublish = () => {
        if (hasStarted) {
            toast.error('Cannot convert to draft after event has started');
            return;
        }
        unpublish(undefined, {
            onSuccess: () => toast.success('Event reverted to draft.'),
            onError: (e: any) =>
                toast.error(e?.response?.data?.message ?? 'Failed to revert to draft'),
        });
    };

    const handleDelete = () => {
        deleteEv(undefined, {
            onSuccess: () => {
                toast.success(`"${event.title}" has been deleted.`);
                navigate('/events');
            },
            onError: (e: any) =>
                toast.error(e?.response?.data?.message ?? 'Failed to delete event'),
        });
    };

    return (
        <>
            {isLive && isEventHost && (
                <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3">
                    <span className="flex items-center gap-2 text-sm font-medium text-destructive">
                        <span className="relative flex h-2 w-2">
                            <span className="absolute inline-flex h-full w-full rounded-full bg-destructive opacity-75 animate-ping" />
                            <span className="relative inline-flex h-2 w-2 rounded-full bg-destructive" />
                        </span>
                        Event is live now
                    </span>
                    <JoinButton eventUuid={event.uuid} role="host" state="live" size="sm" />
                </div>
            )}

            <PageHeader
                title={event.title}
                description={`Manage registrations and attendance for your ${event.format ? `${event.format} event` : 'event'}.`}
                actions={
                    <div className="flex gap-2">
                        {event.status === 'draft' && !hasStarted && (
                            <Button
                                onClick={handlePublish}
                                disabled={publishing}
                                className="bg-success hover:bg-success/90 text-white"
                            >
                                {publishing ? 'Publishing...' : 'Publish Event'}
                            </Button>
                        )}
                        {event.status === 'published' && !hasStarted && (
                            <Button
                                onClick={handleUnpublish}
                                disabled={unpublishing}
                                variant="outline"
                                className="text-warning border-warning hover:bg-warning-subtle"
                            >
                                {unpublishing ? 'Updating...' : 'Convert to Draft'}
                            </Button>
                        )}
                        {hasStarted ? (
                            <Button variant="outline" disabled title="Event has started">
                                Edit Event
                            </Button>
                        ) : (
                            <Link to={`/events/${event.uuid}/edit`}>
                                <Button variant="outline">Edit Event</Button>
                            </Link>
                        )}
                        <Link to={`/events/${event.slug || event.uuid}/details`}>
                            <Button>View Public Page</Button>
                        </Link>
                        <AlertDialog>
                            <AlertDialogTrigger asChild>
                                <Button
                                    variant="outline"
                                    className="text-destructive border-destructive hover:bg-destructive/10 hover:text-destructive"
                                >
                                    <Trash2 className="h-4 w-4 mr-2" />
                                    Delete
                                </Button>
                            </AlertDialogTrigger>
                            <AlertDialogContent>
                                <AlertDialogHeader>
                                    <AlertDialogTitle>Delete Event</AlertDialogTitle>
                                    <AlertDialogDescription asChild>
                                        <div className="space-y-2">
                                            <p>
                                                Are you sure you want to delete{' '}
                                                <strong>{event.title}</strong>? This action cannot be undone.
                                            </p>
                                            {(stats.registered > 0 ||
                                                stats.issued > 0 ||
                                                stats.feedbackCount > 0) && (
                                                <div className="rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">
                                                    <div className="font-medium mb-1">
                                                        Removing this event will also delete:
                                                    </div>
                                                    <ul className="list-disc pl-5 space-y-0.5">
                                                        {stats.registered > 0 && (
                                                            <li>
                                                                {stats.registered} registration
                                                                {stats.registered === 1 ? '' : 's'}
                                                            </li>
                                                        )}
                                                        {stats.issued > 0 && (
                                                            <li>
                                                                {stats.issued} issued certificate
                                                                {stats.issued === 1 ? '' : 's'}
                                                            </li>
                                                        )}
                                                        {stats.checkedIn > 0 && (
                                                            <li>
                                                                {stats.checkedIn} attendance record
                                                                {stats.checkedIn === 1 ? '' : 's'}
                                                            </li>
                                                        )}
                                                        {stats.feedbackCount > 0 && (
                                                            <li>
                                                                {stats.feedbackCount} feedback response
                                                                {stats.feedbackCount === 1 ? '' : 's'}
                                                            </li>
                                                        )}
                                                    </ul>
                                                    {stats.issued > 0 && (
                                                        <p className="mt-2 text-xs">
                                                            Certificates that have already been published may
                                                            have been added to learners' transcripts.
                                                        </p>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    </AlertDialogDescription>
                                </AlertDialogHeader>
                                <AlertDialogFooter>
                                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                                    <AlertDialogAction
                                        onClick={handleDelete}
                                        disabled={deleting}
                                        className="bg-destructive hover:bg-destructive/90"
                                    >
                                        {deleting ? 'Deleting...' : 'Delete Event'}
                                    </AlertDialogAction>
                                </AlertDialogFooter>
                            </AlertDialogContent>
                        </AlertDialog>
                    </div>
                }
            >
                <div className="flex flex-wrap items-center gap-4 mt-4 text-sm text-muted-foreground">
                    <StatusBadge status={event.status} />
                    <div className="flex items-center gap-1">
                        <Clock className="h-4 w-4" />
                        {new Date(event.starts_at).toLocaleDateString()}
                    </div>
                    <div>•</div>
                    <div>{event.capacity ?? 'Unlimited'} Capacity</div>
                </div>
            </PageHeader>
        </>
    );
}
