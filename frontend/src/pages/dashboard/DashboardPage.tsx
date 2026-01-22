import React from 'react';
import { useOutletContext } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { OrganizerDashboard } from './organizer/OrganizerDashboard';
import { CourseManagerDashboard } from './course-manager/CourseManagerDashboard';
import { AttendeeDashboard } from './attendee/AttendeeDashboard';
import { ProDashboard } from './pro/ProDashboard';
import { Subscription } from '@/api/billing/types';
import { getRoleFlags } from '@/lib/role-utils';

type DashboardOutletContext = {
    subscription: Subscription | null;
};

export const DashboardPage = () => {
    const { user } = useAuth();
    const outletContext = useOutletContext<DashboardOutletContext | undefined>();
    const subscription = outletContext?.subscription ?? null;
    const { isOrganizer, isCourseManager } = getRoleFlags(user, subscription);
    const isPro = subscription?.plan === 'pro';

    if (!user) {
        return <div className="p-8 text-center text-muted-foreground">Loading profile...</div>;
    }

    if (isPro) {
        return <ProDashboard />;
    }

    if (isOrganizer) {
        return <OrganizerDashboard />;
    }

    if (isCourseManager) {
        return <CourseManagerDashboard />;
    }

    return <AttendeeDashboard />;
};
