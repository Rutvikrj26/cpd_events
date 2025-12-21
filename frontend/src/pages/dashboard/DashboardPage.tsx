import React from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { OrganizerDashboard } from './organizer/OrganizerDashboard';
import { AttendeeDashboard } from './attendee/AttendeeDashboard';

export const DashboardPage = () => {
    const { user } = useAuth();

    if (!user) {
        return <div className="p-8 text-center text-muted-foreground">Loading profile...</div>;
    }

    if (user.account_type === 'organizer') {
        return <OrganizerDashboard />;
    }

    return <AttendeeDashboard />;
};
