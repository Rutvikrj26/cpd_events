import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Plus, Calendar, MapPin, Users, MoreVertical, Copy, Edit, Eye, Trash2, Loader2, Building2, Search } from 'lucide-react';
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
import { getRoleFlags } from '@/lib/role-utils';
import { getEventStatusStyle } from '@/lib/eventStatus';

export const EventsPage = () => {
    const { user } = useAuth();
    const navigate = useNavigate();
    const [events, setEvents] = useState<Event[]>([]);
    const [loading, setLoading] = useState(true);
    const [duplicating, setDuplicating] = useState<string | null>(null);
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
    const [eventToDelete, setEventToDelete] = useState<Event | null>(null);
    const [deleting, setDeleting] = useState(false);
    // Lightweight client-side filtering (QA F-16). The events list endpoint
    // already supports query params, but for the page sizes we ship today
    // local filtering is fast and simpler.
    const [searchQuery, setSearchQuery] = useState('');
    const [statusFilter, setStatusFilter] = useState<string>('all');
    const [formatFilter, setFormatFilter] = useState<string>('all');
    const { isOrganizer } = getRoleFlags(user);

    const visibleEvents = events.filter((e) => {
        if (statusFilter !== 'all' && e.status !== statusFilter) return false;
        if (formatFilter !== 'all' && e.format !== formatFilter) return false;
        if (searchQuery) {
            const q = searchQuery.toLowerCase();
            const hay = `${e.title ?? ''} ${e.short_description ?? ''} ${e.description ?? ''}`.toLowerCase();
            if (!hay.includes(q)) return false;
        }
        return true;
    });

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
                        {isOrganizer ? 'Manage Events' : 'Browse Events'}
                    </h1>
                    <p className="text-muted-foreground">
                        {isOrganizer ? 'Create, edit, and run your CPD events' : 'Discover upcoming CPD events'}
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

            {isOrganizer && events.length > 0 && (
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center mb-6">
                    <div className="relative flex-1 max-w-md">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
                        <input
                            type="text"
                            placeholder="Search events…"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full pl-9 pr-3 py-2 text-sm rounded-md border border-border bg-card focus:outline-none focus:ring-2 focus:ring-ring"
                        />
                    </div>
                    <select
                        value={statusFilter}
                        onChange={(e) => setStatusFilter(e.target.value)}
                        className="px-3 py-2 text-sm rounded-md border border-border bg-card focus:outline-none focus:ring-2 focus:ring-ring"
                    >
                        <option value="all">All statuses</option>
                        <option value="draft">Draft</option>
                        <option value="published">Published</option>
                        <option value="live">Live</option>
                        <option value="completed">Completed</option>
                        <option value="cancelled">Cancelled</option>
                    </select>
                    <select
                        value={formatFilter}
                        onChange={(e) => setFormatFilter(e.target.value)}
                        className="px-3 py-2 text-sm rounded-md border border-border bg-card focus:outline-none focus:ring-2 focus:ring-ring"
                    >
                        <option value="all">All formats</option>
                        <option value="online">Online</option>
                        <option value="in-person">In-person</option>
                        <option value="hybrid">Hybrid</option>
                    </select>
                    {(searchQuery || statusFilter !== 'all' || formatFilter !== 'all') && (
                        <button
                            type="button"
                            onClick={() => { setSearchQuery(''); setStatusFilter('all'); setFormatFilter('all'); }}
                            className="text-sm text-muted-foreground underline-offset-4 hover:underline"
                        >
                            Clear
                        </button>
                    )}
                </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {visibleEvents.map((event) => (
                    <div key={event.uuid} className="group relative h-full">
                        <Link
                            to={`/organizer/events/${event.uuid}/manage`}
                            className="block h-full"
                        >
                            <div className="bg-card rounded-xl border border-border overflow-hidden hover:shadow-md transition-shadow h-full flex flex-col">
                                <div
                                    className="h-48 relative shrink-0 bg-gradient-to-br from-primary/15 via-accent/10 to-primary/5"
                                    style={{
                                        // Hue cycles based on UUID first char so cards in the
                                        // same row look different. (QA F-14)
                                        backgroundImage: `linear-gradient(135deg, hsl(${(event.uuid?.charCodeAt(0) ?? 0) * 7 % 360} 60% 35% / 0.35), hsl(${(event.uuid?.charCodeAt(1) ?? 0) * 11 % 360} 60% 25% / 0.55))`,
                                    }}
                                >
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
                                        <div className="absolute inset-0 flex flex-col items-center justify-center text-white/85">
                                            <Calendar size={42} className="opacity-70" />
                                            <span className="mt-2 text-2xl font-bold tracking-tight uppercase opacity-70">
                                                {event.title?.charAt(0) ?? '?'}
                                            </span>
                                        </div>
                                    )}
                                    <div className="absolute inset-0 flex items-center justify-center text-slate-300 hidden bg-muted">
                                        <Calendar size={48} />
                                    </div>
                                    <Badge
                                        variant="outline"
                                        className={`absolute top-4 left-4 ${getEventStatusStyle(event.status).className}`}
                                    >
                                        {getEventStatusStyle(event.status).pulse && (
                                            <span className="mr-1 inline-block h-2 w-2 rounded-full bg-current animate-pulse" />
                                        )}
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
                                <div className="p-5 flex flex-col flex-grow">
                                    <h3 className="font-bold text-lg text-foreground group-hover:text-blue-600 transition-colors pr-8 line-clamp-2 min-h-[3.5rem]">
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
