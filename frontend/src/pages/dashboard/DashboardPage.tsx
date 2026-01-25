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
    const { isOrganizer, isCourseManager, isAdmin } = getRoleFlags(user, subscription);
    const isPro = subscription?.plan === 'pro';

    if (!user) {
        return <div className="p-8 text-center text-muted-foreground">Loading profile...</div>;
    }

    // Admin accounts see Pro dashboard (full features) for testing purposes
    // Note: Admins get isOrganizer and isCourseManager flags (see role-utils.ts:38-39)
    // but explicit check here ensures admins without subscriptions see the right view
    if (isAdmin && !subscription) {
        return <ProDashboard />;
    }

    // Pro plan gets combined organizer + course manager dashboard
    if (isPro) {
        return <ProDashboard />;
    }

    // Organizer plan gets event management dashboard
    // Note: Admin users also get this flag (see role-utils.ts:38)
    if (isOrganizer) {
        return <OrganizerDashboard />;
    }

    // LMS plan gets course management dashboard
    // Note: Admin users also get this flag (see role-utils.ts:39)
    if (isCourseManager) {
        return <CourseManagerDashboard />;
    }

    // Default: Attendee plan (or no subscription) gets learning dashboard
    // Note: Users without subscriptions fall through to attendee view
    return <AttendeeDashboard />;
};
