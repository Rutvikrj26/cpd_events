import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
    createModuleContent,
    updateModuleContent,
    deleteModuleContent,
} from '@/api/courses/modules';
import { courseKeys } from './queryKeys';

// ---------------------------------------------------------------------------
// Create content
// ---------------------------------------------------------------------------

export function useCreateContent(courseUuid: string | undefined) {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: ({
            moduleUuid,
            data,
        }: {
            moduleUuid: string;
            data: FormData;
        }) => createModuleContent(courseUuid!, moduleUuid, data),
        onSuccess: () => {
            if (courseUuid) {
                qc.invalidateQueries({ queryKey: courseKeys.modules(courseUuid) });
            }
        },
    });
}

// ---------------------------------------------------------------------------
// Update content
// ---------------------------------------------------------------------------

export function useUpdateContent(courseUuid: string | undefined) {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: ({
            moduleUuid,
            contentUuid,
            data,
        }: {
            moduleUuid: string;
            contentUuid: string;
            data: FormData;
        }) => updateModuleContent(courseUuid!, moduleUuid, contentUuid, data),
        onSuccess: (_result, vars) => {
            if (courseUuid) {
                qc.invalidateQueries({ queryKey: courseKeys.modules(courseUuid) });
                qc.invalidateQueries({ queryKey: courseKeys.moduleContents(vars.moduleUuid) });
            }
        },
    });
}

// ---------------------------------------------------------------------------
// Delete content
// ---------------------------------------------------------------------------

export function useDeleteContent(courseUuid: string | undefined) {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: ({
            moduleUuid,
            contentUuid,
        }: {
            moduleUuid: string;
            contentUuid: string;
        }) => deleteModuleContent(courseUuid!, moduleUuid, contentUuid),
        onSuccess: (_result, vars) => {
            if (courseUuid) {
                qc.invalidateQueries({ queryKey: courseKeys.modules(courseUuid) });
                qc.invalidateQueries({ queryKey: courseKeys.moduleContents(vars.moduleUuid) });
            }
        },
    });
}
