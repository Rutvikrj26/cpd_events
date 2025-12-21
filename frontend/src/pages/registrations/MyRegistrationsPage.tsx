import React, { useEffect, useState } from 'react';
import { getMyRegistrations } from '@/api/registrations';
import { Registration } from '@/api/registrations/types';
import { Calendar, CheckCircle, XCircle, Clock } from 'lucide-react';
import { Link } from 'react-router-dom';

export const MyRegistrationsPage = () => {
    const [registrations, setRegistrations] = useState<Registration[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchRegistrations = async () => {
            try {
                const data = await getMyRegistrations();
                setRegistrations(data);
            } catch (error) {
                console.error("Failed to load registrations", error);
            } finally {
                setLoading(false);
            }
        };
        fetchRegistrations();
    }, []);

    const getStatusBadge = (status: string) => {
        switch (status) {
            case 'confirmed': return <span className="inline-flex items-center text-green-700 bg-green-50 px-2 py-1 rounded-md text-xs font-medium"><CheckCircle size={12} className="mr-1" /> Confirmed</span>;
            case 'attended': return <span className="inline-flex items-center text-blue-700 bg-blue-50 px-2 py-1 rounded-md text-xs font-medium"><CheckCircle size={12} className="mr-1" /> Attended</span>;
            case 'cancelled': return <span className="inline-flex items-center text-red-700 bg-red-50 px-2 py-1 rounded-md text-xs font-medium"><XCircle size={12} className="mr-1" /> Cancelled</span>;
            default: return <span className="inline-flex items-center text-yellow-700 bg-yellow-50 px-2 py-1 rounded-md text-xs font-medium"><Clock size={12} className="mr-1" /> Pending</span>;
        }
    };

    if (loading) return <div className="p-8">Loading registrations...</div>;

    return (
        <div className="space-y-6">
            <h1 className="text-3xl font-bold text-foreground">My Registrations</h1>

            <div className="bg-card rounded-xl border shadow-sm overflow-hidden">
                {registrations.length === 0 ? (
                    <div className="p-12 text-center text-muted-foreground">
                        You have not registered for any events yet. <Link to="/events" className="text-blue-600 hover:underline">Browse Events</Link>
                    </div>
                ) : (
                    <table className="w-full text-left text-sm">
                        <thead className="bg-muted/30 border-b">
                            <tr>
                                <th className="px-6 py-4 font-medium text-muted-foreground">Event</th>
                                <th className="px-6 py-4 font-medium text-muted-foreground">Date Registered</th>
                                <th className="px-6 py-4 font-medium text-muted-foreground">Status</th>
                                <th className="px-6 py-4 font-medium text-muted-foreground">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                            {registrations.map(reg => (
                                <tr key={reg.uuid} className="hover:bg-muted/30 transition-colors">
                                    <td className="px-6 py-4">
                                        <div className="font-semibold text-foreground">
                                            {reg.event.title}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 text-slate-600">
                                        {new Date(reg.created_at).toLocaleDateString()}
                                    </td>
                                    <td className="px-6 py-4">
                                        {getStatusBadge(reg.status)}
                                    </td>
                                    <td className="px-6 py-4">
                                        <Link to={`/events/${reg.event.uuid}`} className="text-blue-600 hover:text-blue-800 font-medium text-xs">
                                            View Event
                                        </Link>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    );
};
