import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Plus, Calendar, MapPin, Users } from 'lucide-react';
import { getEvents, getPublicEvents } from '@/api/events';
import { Event } from '@/api/events/types';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { EventDiscovery } from '../public/EventDiscovery';

export const EventsPage = () => {
    const { user } = useAuth();
    const [events, setEvents] = useState<Event[]>([]);
    const [loading, setLoading] = useState(true);
    const isOrganizer = user?.account_type === 'organizer' || user?.account_type === 'admin';

    useEffect(() => {
        if (!isOrganizer) return; // Attendees use EventDiscovery component which handles its own fetching

        const fetchEvents = async () => {
            try {
                // Organizers see their own events for management
                const data = await getEvents();
                setEvents(data);
            } catch (error) {
                console.error("Failed to load events", error);
            } finally {
                setLoading(false);
            }
        };
        fetchEvents();
    }, [isOrganizer]);

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
                    <Link
                        key={event.uuid}
                        to={isOrganizer ? `/organizer/events/${event.uuid}/manage` : `/events/${event.slug || event.uuid}`}
                        className="group block"
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
                                {/* Fallback placeholder if image fails to load */}
                                <div className="absolute inset-0 flex items-center justify-center text-slate-300 hidden bg-muted">
                                    <Calendar size={48} />
                                </div>
                                <div className="absolute top-4 right-4 bg-card/90 px-2 py-1 rounded text-xs font-semibold uppercase">
                                    {event.status}
                                </div>
                            </div>
                            <div className="p-5">
                                <h3 className="font-bold text-lg text-foreground group-hover:text-blue-600 transition-colors">
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
        </div>
    );
};
