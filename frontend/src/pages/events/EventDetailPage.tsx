import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getEvent, getEventSessions } from '@/api/events';
import { Event, EventSession } from '@/api/events/types';
import { Button } from '@/components/ui/button';
import { Calendar, MapPin, Clock, ArrowLeft } from 'lucide-react';

export const EventDetailPage = () => {
    const { uuid } = useParams();
    const [event, setEvent] = useState<Event | null>(null);
    const [sessions, setSessions] = useState<EventSession[]>([]);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState<'overview' | 'sessions' | 'learning'>('overview');

    useEffect(() => {
        if (!uuid) return;
        const fetchData = async () => {
            try {
                const eventData = await getEvent(uuid);
                setEvent(eventData);

                const sessionsData = await getEventSessions(uuid);
                setSessions(sessionsData);

            } catch (error) {
                console.error("Failed to fetch event", error);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, [uuid]);

    if (loading || !event) return <div className="p-8">Loading...</div>;

    return (
        <div className="space-y-6">
            <Link to="/events" className="flex items-center text-slate-500 hover:text-slate-900 transition-colors">
                <ArrowLeft size={16} className="mr-2" /> Back to Events
            </Link>

            <div className="bg-white rounded-xl shadow-sm border p-6 md:p-8">
                <div className="flex flex-col md:flex-row justify-between gap-4 md:items-start">
                    <div>
                        <span className="inline-block px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs uppercase font-bold tracking-wide mb-2">
                            {event.status}
                        </span>
                        <h1 className="text-3xl font-bold text-slate-900">{event.title}</h1>
                        <div className="flex flex-wrap gap-4 mt-4 text-slate-600">
                            <div className="flex items-center gap-2">
                                <Calendar size={18} />
                                <span>
                                    {new Date(event.start_date).toLocaleDateString()} - {new Date(event.end_date).toLocaleDateString()}
                                </span>
                            </div>
                            <div className="flex items-center gap-2 capitalize">
                                <MapPin size={18} />
                                <span>{event.format}</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <Clock size={18} />
                                <span>{event.timezone}</span>
                            </div>
                        </div>
                    </div>
                    {/* Actions */}
                    <div className="flex gap-2">
                        {/* If organizer */}
                        <Link to={`/events/${event.uuid}/edit`}>
                            <Button variant="outline">Edit Event</Button>
                        </Link>
                        {/* If registration open */}
                        {event.is_registration_open && (
                            <Button>Register Now</Button>
                        )}
                    </div>
                </div>
            </div>

            {/* Tabs */}
            <div className="border-b border-slate-200">
                <nav className="flex space-x-8">
                    {['overview', 'sessions', 'learning'].map((tab) => (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(tab as any)}
                            className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors capitalize ${activeTab === tab
                                    ? 'border-blue-500 text-blue-600'
                                    : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
                                }`}
                        >
                            {tab}
                        </button>
                    ))}
                </nav>
            </div>

            <div className="mt-6">
                {activeTab === 'overview' && (
                    <div className="bg-white p-6 rounded-xl border prose max-w-none">
                        <h3 className="text-xl font-bold mb-4">About the Event</h3>
                        <p className="whitespace-pre-line">{event.description}</p>
                    </div>
                )}

                {activeTab === 'sessions' && (
                    <div className="space-y-4">
                        <div className="flex justify-between items-center">
                            <h3 className="text-lg font-bold">Sessions</h3>
                            {/* Organizer Action */}
                            <Button size="sm" variant="outline"><PlusIcon size={16} className="mr-2" /> Add Session</Button>
                        </div>
                        {sessions.length === 0 ? (
                            <div className="text-slate-500 text-center py-8 bg-white border rounded-xl border-dashed">No sessions scheduled yet.</div>
                        ) : (
                            <div className="grid gap-4">
                                {sessions.map(session => (
                                    <div key={session.uuid} className="bg-white p-4 rounded-lg border flex justify-between items-center">
                                        <div>
                                            <h4 className="font-bold">{session.title}</h4>
                                            <p className="text-sm text-slate-500">
                                                {new Date(session.start_time).toLocaleTimeString()} - {new Date(session.end_time).toLocaleTimeString()}
                                            </p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {activeTab === 'learning' && (
                    <div className="text-slate-500 text-center py-12 bg-white rounded-xl border border-dashed">
                        Learning modules content will appear here.
                    </div>
                )}
            </div>
        </div>
    );
};

const PlusIcon = ({ size, className }: { size: number, className?: string }) => (
    <svg width={size} height={size} className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
);
