import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
    createCourseModule,
    updateCourseModule,
    deleteCourseModule,
} from '@/api/courses/modules';
import type { UpdateModuleRequest } from '@/api/courses/modules';
import { courseKeys } from './queryKeys';

// ---------------------------------------------------------------------------
// Create
// ---------------------------------------------------------------------------

export function useCreateModule(courseUuid: string | undefined) {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (data: { title: string; description?: string }) =>
            createCourseModule(courseUuid!, { ...data, course_uuid: courseUuid! }),
        onSuccess: () => {
            if (courseUuid) {
                qc.invalidateQueries({ queryKey: courseKeys.modules(courseUuid) });
            }
        },
    });
}

// ---------------------------------------------------------------------------
// Update
// ---------------------------------------------------------------------------

export function useUpdateModule(courseUuid: string | undefined) {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: ({ moduleUuid, data }: { moduleUuid: string; data: UpdateModuleRequest }) =>
            updateCourseModule(courseUuid!, moduleUuid, data),
        onSuccess: () => {
            if (courseUuid) {
                qc.invalidateQueries({ queryKey: courseKeys.modules(courseUuid) });
            }
        },
    });
}

// ---------------------------------------------------------------------------
// Delete
// ---------------------------------------------------------------------------

export function useDeleteModule(courseUuid: string | undefined) {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (moduleUuid: string) => deleteCourseModule(courseUuid!, moduleUuid),
        onSuccess: () => {
            if (courseUuid) {
                qc.invalidateQueries({ queryKey: courseKeys.modules(courseUuid) });
            }
        },
    });
}

// ---------------------------------------------------------------------------
// Reorder (visual-only drag backing — optimistic update via invalidation)
// ---------------------------------------------------------------------------

export function useReorderModules(courseUuid: string | undefined) {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: ({
            moduleUuid,
            order,
        }: {
            moduleUuid: string;
            order: number;
        }) => updateCourseModule(courseUuid!, moduleUuid, { order }),
        onSuccess: () => {
            if (courseUuid) {
                qc.invalidateQueries({ queryKey: courseKeys.modules(courseUuid) });
            }
        },
    });
}
