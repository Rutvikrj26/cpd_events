import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getEvents } from '@/api/events';
import type { Event } from '@/api/events/types';
import { getOwnedCourses } from '@/api/courses';
import type { Course } from '@/api/courses/types';
import { dashboardKeys } from './queryKeys';

export interface OrganizerDashboardData {
    isLoading: boolean;
    isError: boolean;
    events: Event[];
    courses: Course[];
    /** 5 most recently created events for the activity table. */
    recentEvents: Event[];
    eventStats: {
        totalEvents: number;
        activeEvents: number;
        totalRegistrations: number;
        certificatesIssued: number;
    };
    courseStats: {
        totalCourses: number;
        publishedCourses: number;
        courseEnrollments: number;
        courseCompletions: number;
    };
}

export function useOrganizerDashboard({
    includeCourses,
}: {
    includeCourses: boolean;
}): OrganizerDashboardData {
    const eventsQuery = useQuery({
        queryKey: [...dashboardKeys.organizer(), 'events'],
        queryFn: async () => {
            try {
                const r = await getEvents();
                return r.results ?? [];
            } catch {
                return [] as Event[];
            }
        },
        staleTime: 1000 * 30,
    });

    const coursesQuery = useQuery({
        queryKey: [...dashboardKeys.organizer(), 'courses'],
        queryFn: async () => {
            try {
                return await getOwnedCourses();
            } catch {
                return [] as Course[];
            }
        },
        enabled: includeCourses,
    });

    const events = eventsQuery.data ?? [];
    const courses = coursesQuery.data ?? [];

    const recentEvents = useMemo(
        () =>
            [...events]
                .sort(
                    (a, b) =>
                        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
                )
                .slice(0, 5),
        [events]
    );

    const eventStats = useMemo(
        () => ({
            totalEvents: events.length,
            activeEvents: events.filter((e) =>
                ['published', 'live'].includes(e.status)
            ).length,
            totalRegistrations: events.reduce(
                (acc, e) => acc + (e.registration_count || 0),
                0
            ),
            certificatesIssued: events.reduce(
                (acc, e) => acc + (e.certificate_count || 0),
                0
            ),
        }),
        [events]
    );

    const courseStats = useMemo(
        () => ({
            totalCourses: courses.length,
            publishedCourses: courses.filter((c) => c.status === 'published').length,
            courseEnrollments: courses.reduce(
                (acc, c) => acc + (c.enrollment_count || 0),
                0
            ),
            courseCompletions: courses.reduce(
                (acc, c) => acc + (c.completion_count || 0),
                0
            ),
        }),
        [courses]
    );

    return {
        isLoading: eventsQuery.isLoading || (includeCourses && coursesQuery.isLoading),
        isError: eventsQuery.isError && (!includeCourses || coursesQuery.isError),
        events,
        courses,
        recentEvents,
        eventStats,
        courseStats,
    };
}
