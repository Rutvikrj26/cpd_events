import React from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { OrganizerDashboard } from './organizer/OrganizerDashboard';
import { InstructorDashboard } from './instructor/InstructorDashboard';
import { AttendeeDashboard } from './attendee/AttendeeDashboard';
import { getRoleFlags } from '@/lib/role-utils';

export const DashboardPage = () => {
    const { user } = useAuth();
    const { isOrganizer, isInstructor } = getRoleFlags(user);

    if (!user) {
        return <div className="p-8 text-center text-muted-foreground">Loading profile...</div>;
    }

    if (isOrganizer) {
        return <OrganizerDashboard />;
    }

    if (isInstructor) {
        return <InstructorDashboard />;
    }

    return <AttendeeDashboard />;
};
