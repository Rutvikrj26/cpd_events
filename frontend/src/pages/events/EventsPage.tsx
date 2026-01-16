import React, { useEffect, useState } from 'react';
import { Link, useNavigate, useOutletContext } from 'react-router-dom';
import { Plus, Calendar, MapPin, Users, MoreVertical, Copy, Edit, Eye, Trash2, Loader2, Building2 } from 'lucide-react';
import { getEvents, getPublicEvents, deleteEvent } from '@/api/events';
import { duplicateEvent } from '@/api/events/actions';
import { Event } from '@/api/events/types';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { EventDiscovery } from '../public/EventDiscovery';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
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
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { Subscription } from '@/api/billing/types';
import { getRoleFlags } from '@/lib/role-utils';

type EventsOutletContext = {
    subscription: Subscription | null;
};

export const EventsPage = () => {
    const { user } = useAuth();
    const navigate = useNavigate();
    const outletContext = useOutletContext<EventsOutletContext | undefined>();
    const subscription = outletContext?.subscription ?? null;
    const [events, setEvents] = useState<Event[]>([]);
    const [loading, setLoading] = useState(true);
    const [duplicating, setDuplicating] = useState<string | null>(null);
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
    const [eventToDelete, setEventToDelete] = useState<Event | null>(null);
    const [deleting, setDeleting] = useState(false);
    const { isOrganizer } = getRoleFlags(user, subscription);

    const fetchEvents = async () => {
        try {
            const data = await getEvents();
            setEvents(data.results);
        } catch (error) {
            console.error("Failed to load events", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (!isOrganizer) return;
        fetchEvents();
    }, [isOrganizer]);

    const handleDuplicate = async (event: Event, e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setDuplicating(event.uuid);
        try {
            const newEvent = await duplicateEvent(event.uuid);
            toast.success(`Event duplicated! Opening "${newEvent.title}" for editing.`);
            // Navigate to edit the new event
            navigate(`/events/${newEvent.uuid}/edit`);
        } catch (error) {
            toast.error('Failed to duplicate event');
        } finally {
            setDuplicating(null);
        }
    };

    const handleDeleteClick = (event: Event, e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setEventToDelete(event);
        setDeleteDialogOpen(true);
    };

    const handleDeleteConfirm = async () => {
        if (!eventToDelete) return;
        setDeleting(true);
        try {
            await deleteEvent(eventToDelete.uuid);
            setEvents(prev => prev.filter(e => e.uuid !== eventToDelete.uuid));
            toast.success('Event deleted successfully');
        } catch (error) {
            toast.error('Failed to delete event');
        } finally {
            setDeleting(false);
            setDeleteDialogOpen(false);
            setEventToDelete(null);
        }
    };

    if (!isOrganizer) {
        return <EventDiscovery />;
    }

    if (loading) return <div className="p-8">Loading events...</div>;

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold text-foreground">
                        {isOrganizer ? 'My Events' : 'Browse Events'}
                    </h1>
                    <p className="text-muted-foreground">
                        {isOrganizer ? 'Manage your CPD events' : 'Discover upcoming CPD events'}
                    </p>
                </div>
                {isOrganizer && (
                    <Link to="/events/create">
                        <Button className="flex items-center gap-2">
                            <Plus size={16} /> Create Event
                        </Button>
                    </Link>
                )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {events.map((event) => (
                    <div key={event.uuid} className="group relative">
                        <Link
                            to={`/organizer/events/${event.uuid}/manage`}
                            className="block"
                        >
                            <div className="bg-card rounded-xl border border-border overflow-hidden hover:shadow-md transition-shadow">
                                <div className="h-48 bg-muted relative">
                                    {event.featured_image_url ? (
                                        <img
                                            src={event.featured_image_url}
                                            alt={event.title}
                                            className="w-full h-full object-cover transition-transform group-hover:scale-105"
                                            onError={(e) => {
                                                (e.target as HTMLImageElement).style.display = 'none';
                                                (e.target as HTMLImageElement).nextElementSibling?.classList.remove('hidden');
                                            }}
                                        />
                                    ) : (
                                        <div className="absolute inset-0 flex items-center justify-center text-slate-300">
                                            <Calendar size={48} />
                                        </div>
                                    )}
                                    <div className="absolute inset-0 flex items-center justify-center text-slate-300 hidden bg-muted">
                                        <Calendar size={48} />
                                    </div>
                                    <Badge
                                        variant={event.status === 'published' ? 'default' : event.status === 'draft' ? 'secondary' : 'outline'}
                                        className="absolute top-4 left-4"
                                    >
                                        {event.status}
                                    </Badge>
                                    {event.organization_info && (
                                        <Badge
                                            variant="outline"
                                            className="absolute top-4 right-16 bg-primary/10 text-primary border-primary/20 flex items-center gap-1"
                                        >
                                            <Building2 className="h-3 w-3" />
                                            {event.organization_info.name}
                                        </Badge>
                                    )}
                                </div>
                                <div className="p-5">
                                    <h3 className="font-bold text-lg text-foreground group-hover:text-blue-600 transition-colors pr-8">
                                        {event.title}
                                    </h3>
                                    <div className="mt-4 space-y-2 text-sm text-muted-foreground">
                                        <div className="flex items-center gap-2">
                                            <Calendar size={14} />
                                            <span>{new Date(event.starts_at).toLocaleDateString()}</span>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <MapPin size={14} />
                                            <span className="capitalize">{event.format}</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </Link>

                        {/* Actions Dropdown */}
                        <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    className="absolute top-4 right-4 h-8 w-8 bg-card/90 hover:bg-card shadow-sm"
                                    onClick={(e) => e.preventDefault()}
                                >
                                    {duplicating === event.uuid ? (
                                        <Loader2 className="h-4 w-4 animate-spin" />
                                    ) : (
                                        <MoreVertical className="h-4 w-4" />
                                    )}
                                </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end" className="w-48">
                                <DropdownMenuItem asChild>
                                    <Link to={`/organizer/events/${event.uuid}/manage`}>
                                        <Eye className="mr-2 h-4 w-4" />
                                        View & Manage
                                    </Link>
                                </DropdownMenuItem>
                                <DropdownMenuItem asChild>
                                    <Link to={`/events/${event.uuid}/edit`}>
                                        <Edit className="mr-2 h-4 w-4" />
                                        Edit Event
                                    </Link>
                                </DropdownMenuItem>
                                <DropdownMenuItem
                                    onClick={(e) => handleDuplicate(event, e as any)}
                                    disabled={duplicating === event.uuid}
                                >
                                    <Copy className="mr-2 h-4 w-4" />
                                    Duplicate Event
                                </DropdownMenuItem>
                                <DropdownMenuSeparator />
                                <DropdownMenuItem
                                    onClick={(e) => handleDeleteClick(event, e as any)}
                                    className="text-destructive focus:text-destructive"
                                >
                                    <Trash2 className="mr-2 h-4 w-4" />
                                    Delete Event
                                </DropdownMenuItem>
                            </DropdownMenuContent>
                        </DropdownMenu>
                    </div>
                ))}
                {events.length === 0 && (
                    <div className="col-span-full py-12 text-center text-muted-foreground bg-card rounded-xl border border-dashed border-slate-300">
                        {isOrganizer
                            ? "No events found. Create your first one!"
                            : "No upcoming events available. Check back later!"
                        }
                    </div>
                )}
            </div>

            {/* Delete Confirmation Dialog */}
            <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Delete Event</AlertDialogTitle>
                        <AlertDialogDescription>
                            Are you sure you want to delete "{eventToDelete?.title}"? This action cannot be undone.
                            All registrations and certificates associated with this event will also be deleted.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel disabled={deleting}>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={handleDeleteConfirm}
                            disabled={deleting}
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        >
                            {deleting ? (
                                <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    Deleting...
                                </>
                            ) : (
                                'Delete Event'
                            )}
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    );
};
