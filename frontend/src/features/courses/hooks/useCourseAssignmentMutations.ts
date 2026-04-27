import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
    createCourseAssignment,
    updateCourseAssignment,
    deleteCourseAssignment,
} from '@/api/courses';
import type { Assignment } from '@/api/courses/types';
import { courseKeys } from './queryKeys';

// ---------------------------------------------------------------------------
// Create assignment
// ---------------------------------------------------------------------------

export function useCreateAssignment(courseUuid: string | undefined) {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: ({
            moduleUuid,
            data,
        }: {
            moduleUuid: string;
            data: Partial<Assignment>;
        }) => createCourseAssignment(courseUuid!, moduleUuid, data),
        onSuccess: (_result, vars) => {
            if (courseUuid) {
                qc.invalidateQueries({ queryKey: courseKeys.modules(courseUuid) });
                qc.invalidateQueries({
                    queryKey: courseKeys.assignments(courseUuid, vars.moduleUuid),
                });
            }
        },
    });
}

// ---------------------------------------------------------------------------
// Update assignment
// ---------------------------------------------------------------------------

export function useUpdateAssignment(courseUuid: string | undefined) {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: ({
            moduleUuid,
            assignmentUuid,
            data,
        }: {
            moduleUuid: string;
            assignmentUuid: string;
            data: Partial<Assignment>;
        }) => updateCourseAssignment(courseUuid!, moduleUuid, assignmentUuid, data),
        onSuccess: (_result, vars) => {
            if (courseUuid) {
                qc.invalidateQueries({ queryKey: courseKeys.modules(courseUuid) });
                qc.invalidateQueries({
                    queryKey: courseKeys.assignments(courseUuid, vars.moduleUuid),
                });
            }
        },
    });
}

// ---------------------------------------------------------------------------
// Delete assignment
// ---------------------------------------------------------------------------

export function useDeleteAssignment(courseUuid: string | undefined) {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: ({
            moduleUuid,
            assignmentUuid,
        }: {
            moduleUuid: string;
            assignmentUuid: string;
        }) => deleteCourseAssignment(courseUuid!, moduleUuid, assignmentUuid),
        onSuccess: (_result, vars) => {
            if (courseUuid) {
                qc.invalidateQueries({ queryKey: courseKeys.modules(courseUuid) });
                qc.invalidateQueries({
                    queryKey: courseKeys.assignments(courseUuid, vars.moduleUuid),
                });
            }
        },
    });
}
