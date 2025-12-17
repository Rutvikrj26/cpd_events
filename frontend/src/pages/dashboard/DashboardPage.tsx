import React, { useEffect, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { getMyRegistrations } from '@/api/registrations';
import { getEvents } from '@/api/events';

export const DashboardPage = () => {
    const { user } = useAuth();
    const [stats, setStats] = useState({ totalEvents: 0, upcoming: 0 });

    useEffect(() => {
        const fetchData = async () => {
            // Fetch some stats based on role
            // Simplified for now
        };
        fetchData();
    }, [user]);

    return (
        <div className="space-y-6">
            <h1 className="text-3xl font-bold text-slate-900">
                Welcome back, {user?.full_name || user?.email}
            </h1>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100">
                    <h3 className="text-sm font-medium text-slate-500 uppercase tracking-wider">Account Type</h3>
                    <p className="text-2xl font-bold mt-2 capitalize">{user?.account_type || 'User'}</p>
                </div>
                {/* Add more widgets */}
            </div>
        </div>
    );
};
