import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    getCourse,
    getCourseBySlug,
    getOwnedCourses,
    enrollInCourse,
    getEnrollments,
    getCourseProgress,
    type CourseProgress,
} from '@/api/courses';
import type { Course } from '@/api/courses/types';
import { courseKeys } from './queryKeys';

/* ------------------------------------------------------------------ */
/* Course detail                                                       */
/* ------------------------------------------------------------------ */

export function useCourse(uuid: string | undefined, options?: { silent?: boolean }) {
    return useQuery({
        queryKey: uuid ? courseKeys.detail(uuid) : ['courses', 'detail', 'noop'],
        queryFn: () => getCourse(uuid!, options),
        enabled: Boolean(uuid),
        staleTime: 1000 * 30,
    });
}

export function useCourseBySlug(slug: string | undefined) {
    return useQuery({
        queryKey: slug ? courseKeys.bySlug(slug) : ['courses', 'bySlug', 'noop'],
        queryFn: () => getCourseBySlug(slug!),
        enabled: Boolean(slug),
        staleTime: 1000 * 30,
    });
}

/* ------------------------------------------------------------------ */
/* Course progress (per-enrollment)                                    */
/* ------------------------------------------------------------------ */

export function useCourseProgress(uuid: string | undefined) {
    return useQuery<CourseProgress>({
        queryKey: uuid ? courseKeys.progress(uuid) : ['courses', 'progress', 'noop'],
        queryFn: () => getCourseProgress(uuid!),
        enabled: Boolean(uuid),
    });
}

/* ------------------------------------------------------------------ */
/* Enrollments                                                         */
/* ------------------------------------------------------------------ */

export function useEnrollments() {
    return useQuery({
        queryKey: courseKeys.enrollments(),
        queryFn: getEnrollments,
        staleTime: 1000 * 60,
    });
}

export function useEnrollInCourse() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (courseUuid: string) => enrollInCourse(courseUuid),
        onSuccess: (_, courseUuid) => {
            queryClient.invalidateQueries({ queryKey: courseKeys.enrollments() });
            queryClient.invalidateQueries({ queryKey: courseKeys.progress(courseUuid) });
            queryClient.invalidateQueries({ queryKey: courseKeys.detail(courseUuid) });
        },
    });
}

/* ------------------------------------------------------------------ */
/* Owned courses (instructor / admin view)                             */
/* ------------------------------------------------------------------ */

export function useOwnedCourses() {
    return useQuery<Course[]>({
        queryKey: courseKeys.owned(),
        queryFn: getOwnedCourses,
        staleTime: 1000 * 30,
    });
}
