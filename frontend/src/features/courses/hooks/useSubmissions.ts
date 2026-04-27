import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
    getMySubmissions,
    createSubmission,
    updateSubmission,
    submitSubmission,
} from '@/api/courses';
import { updateContentProgress } from '@/api/learning';
import type { AssignmentSubmission } from '@/api/courses/types';
import { courseKeys } from './queryKeys';

/* ------------------------------------------------------------------ */
/* My submissions (learner view)                                       */
/* ------------------------------------------------------------------ */

export function useMySubmissions() {
    return useQuery<AssignmentSubmission[]>({
        queryKey: courseKeys.mySubmissions(),
        queryFn: getMySubmissions,
        staleTime: 1000 * 60,
    });
}

/* ------------------------------------------------------------------ */
/* Submission CRUD                                                     */
/* ------------------------------------------------------------------ */

export function useCreateSubmission() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({
            assignmentUuid,
            data,
        }: {
            assignmentUuid: string;
            data: { content?: Record<string, any>; file_url?: string };
        }) => createSubmission(assignmentUuid, data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: courseKeys.mySubmissions() });
        },
    });
}

export function useUpdateSubmission() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({
            submissionUuid,
            data,
        }: {
            submissionUuid: string;
            data: { content?: Record<string, any>; file_url?: string };
        }) => updateSubmission(submissionUuid, data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: courseKeys.mySubmissions() });
        },
    });
}

export function useFinalizeSubmission() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (submissionUuid: string) => submitSubmission(submissionUuid),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: courseKeys.mySubmissions() });
        },
    });
}

/* ------------------------------------------------------------------ */
/* Per-content progress                                                */
/* ------------------------------------------------------------------ */

export function useUpdateContentProgress() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({
            contentUuid,
            data,
        }: {
            contentUuid: string;
            data: any;
        }) => updateContentProgress(contentUuid, data),
        onSuccess: (_data, variables) => {
            // Coarsest invalidation — caller passes courseUuid via meta if known.
            const courseUuid = (variables as any).courseUuid as string | undefined;
            if (courseUuid) {
                queryClient.invalidateQueries({
                    queryKey: courseKeys.progress(courseUuid),
                });
            } else {
                // Fallback: invalidate everything course-shaped.
                queryClient.invalidateQueries({ queryKey: courseKeys.all });
            }
        },
    });
}
