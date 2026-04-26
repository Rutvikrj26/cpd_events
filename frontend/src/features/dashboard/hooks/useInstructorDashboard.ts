import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getOwnedCourses } from '@/api/courses';
import type { Course } from '@/api/courses/types';
import { dashboardKeys } from './queryKeys';

export interface InstructorDashboardData {
    isLoading: boolean;
    isError: boolean;
    courses: Course[];
    /** 5 most recently created courses for the table on the dashboard. */
    recentCourses: Course[];
    stats: {
        totalCourses: number;
        publishedCourses: number;
        totalEnrollments: number;
        totalCompletions: number;
    };
}

export function useInstructorDashboard(): InstructorDashboardData {
    const coursesQuery = useQuery({
        queryKey: [...dashboardKeys.instructor(), 'courses'],
        queryFn: getOwnedCourses,
        staleTime: 1000 * 60, // 1 minute — instructor often edits + reloads
    });

    const courses = coursesQuery.data ?? [];

    const recentCourses = useMemo(
        () =>
            [...courses]
                .sort(
                    (a, b) =>
                        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
                )
                .slice(0, 5),
        [courses]
    );

    const stats = useMemo(
        () => ({
            totalCourses: courses.length,
            publishedCourses: courses.filter((c) => c.status === 'published').length,
            totalEnrollments: courses.reduce(
                (acc, c) => acc + (c.enrollment_count || 0),
                0
            ),
            totalCompletions: courses.reduce(
                (acc, c) => acc + (c.completion_count || 0),
                0
            ),
        }),
        [courses]
    );

    return {
        isLoading: coursesQuery.isLoading,
        isError: coursesQuery.isError,
        courses,
        recentCourses,
        stats,
    };
}
