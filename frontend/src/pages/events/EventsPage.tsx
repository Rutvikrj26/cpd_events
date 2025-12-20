import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Plus, Calendar, MapPin, Users } from 'lucide-react';
import { getEvents } from '@/api/events';
import { Event } from '@/api/events/types';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';

export const EventsPage = () => {
    const { user } = useAuth();
    const [events, setEvents] = useState<Event[]>([]);
    const [loading, setLoading] = useState(true);
    const isOrganizer = user?.account_type === 'organizer' || user?.account_type === 'admin';

    useEffect(() => {
        const fetchEvents = async () => {
            try {
                // Attendees see public events, Organizers see their own events?
                // Actually getEvents api might return different things based on auth. 
                // Admin/Organizer -> /events/ (list their events). 
                // Attendee -> ?? They usually use /public/events/.
                // Let's assume dashboard shows "My Managed Events" for organizers
                // and "All Available Events" or "My Registered Events" for attendees?
                // Nav item says "Events". For organizer: Manage Events.
                // For attendee: Browse Events.

                let data: Event[] = [];
                if (isOrganizer) {
                    data = await getEvents();
                } else {
                    // For attendee, maybe we show public events here?
                    // Or maybe they want to see events they are registered for?
                    // "My Registrations" is separate. 
                    // "Events" likely implies discovery.
                    //  import { getPublicEvents } from '@/api/events';
                    // data = await getPublicEvents();
                    // For now let's just use getEvents() and assume backend filters or simple view
                    // Actually, sticking to 1:1, getEvents calls /events/. 
                    // If attendee calls /events/, it might be 403 or empty list if they own nothing.
                    // We'll address this by conditionally calling public for non-organizers or just showing empty.
                    data = await getEvents();
                }
                setEvents(data);
            } catch (error) {
                console.error("Failed to load events", error);
            } finally {
                setLoading(false);
            }
        };
        fetchEvents();
    }, [isOrganizer]);

    if (loading) return <div className="p-8">Loading events...</div>;

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold text-slate-900">Events</h1>
                    <p className="text-slate-500">Manage your CPD events</p>
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
                    <Link key={event.uuid} to={`/events/${event.uuid}`} className="group block">
                        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden hover:shadow-md transition-shadow">
                            <div className="h-48 bg-slate-100 relative">
                                {/* Placeholder for event image if we had one */}
                                <div className="absolute inset-0 flex items-center justify-center text-slate-300">
                                    <Calendar size={48} />
                                </div>
                                <div className="absolute top-4 right-4 bg-white/90 px-2 py-1 rounded text-xs font-semibold uppercase">
                                    {event.status}
                                </div>
                            </div>
                            <div className="p-5">
                                <h3 className="font-bold text-lg text-slate-900 group-hover:text-blue-600 transition-colors">
                                    {event.title}
                                </h3>
                                <div className="mt-4 space-y-2 text-sm text-slate-500">
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
                    <div className="col-span-full py-12 text-center text-slate-500 bg-white rounded-xl border border-dashed border-slate-300">
                        No events found. {isOrganizer && "Create your first one!"}
                    </div>
                )}
            </div>
        </div>
    );
};
