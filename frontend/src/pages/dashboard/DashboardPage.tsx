import React from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { OrganizerDashboard } from './organizer/OrganizerDashboard';
import { CourseManagerDashboard } from './course-manager/CourseManagerDashboard';
import { AttendeeDashboard } from './attendee/AttendeeDashboard';
import { getRoleFlags } from '@/lib/role-utils';

export const DashboardPage = () => {
    const { user } = useAuth();
    const { isEducator, isCourseManager } = getRoleFlags(user);

    if (!user) {
        return <div className="p-8 text-center text-muted-foreground">Loading profile...</div>;
    }

    if (isEducator) {
        return <OrganizerDashboard />;
    }

    if (isCourseManager) {
        return <CourseManagerDashboard />;
    }

    return <AttendeeDashboard />;
};
