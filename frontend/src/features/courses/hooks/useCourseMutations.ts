import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
    createCourse,
    createCourseSession,
    deleteCourse,
    publishCourse,
    updateCourse,
} from '@/api/courses';
import type {
    Course,
    CourseCreateRequest,
    CourseSession,
    CourseSessionCreateRequest,
} from '@/api/courses/types';
import { courseKeys } from './queryKeys';

/**
 * Course-level CRUD mutations.
 *
 * Each mutation invalidates the narrowest correct scope: the owned-courses
 * list always (so dashboards refresh), and the per-course detail when an
 * existing course mutates.
 */

export function useCreateCourse() {
    const qc = useQueryClient();
    return useMutation<Course, unknown, CourseCreateRequest>({
        mutationFn: (data) => createCourse(data),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: courseKeys.owned() });
            qc.invalidateQueries({ queryKey: courseKeys.list() });
        },
    });
}

export function useUpdateCourse() {
    const qc = useQueryClient();
    return useMutation<
        Course,
        unknown,
        { uuid: string; data: Partial<CourseCreateRequest> }
    >({
        mutationFn: ({ uuid, data }) => updateCourse(uuid, data),
        onSuccess: (course, { uuid }) => {
            qc.invalidateQueries({ queryKey: courseKeys.owned() });
            qc.invalidateQueries({ queryKey: courseKeys.detail(uuid) });
            if (course?.slug) {
                qc.invalidateQueries({ queryKey: courseKeys.bySlug(course.slug) });
            }
        },
    });
}

export function useDeleteCourse() {
    const qc = useQueryClient();
    return useMutation<void, unknown, string>({
        mutationFn: (uuid) => deleteCourse(uuid),
        onSuccess: (_data, uuid) => {
            qc.invalidateQueries({ queryKey: courseKeys.owned() });
            qc.removeQueries({ queryKey: courseKeys.detail(uuid) });
        },
    });
}

export function usePublishCourse() {
    const qc = useQueryClient();
    return useMutation<Course, unknown, string>({
        mutationFn: (uuid) => publishCourse(uuid),
        onSuccess: (_data, uuid) => {
            qc.invalidateQueries({ queryKey: courseKeys.owned() });
            qc.invalidateQueries({ queryKey: courseKeys.detail(uuid) });
        },
    });
}

/**
 * Create a course session under an existing course.
 *
 * Used by CreateCoursePage immediately after the course is created to
 * persist the schedule produced by `<SessionScheduler>`.
 */
export function useCreateCourseSession() {
    const qc = useQueryClient();
    return useMutation<
        CourseSession,
        unknown,
        { courseUuid: string; data: CourseSessionCreateRequest }
    >({
        mutationFn: ({ courseUuid, data }) => createCourseSession(courseUuid, data),
        onSuccess: (_data, { courseUuid }) => {
            qc.invalidateQueries({ queryKey: courseKeys.sessions(courseUuid) });
        },
    });
}
