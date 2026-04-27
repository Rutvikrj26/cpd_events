import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    getPrograms,
    getPublicPrograms,
    getProgram,
    getProgramBySlug,
    createProgram,
    updateProgram,
    deleteProgram,
    publishProgram,
    getMyProgramEnrollments,
} from '@/api/programs';
import type {
    Program,
    ProgramEnrollment,
    ProgramListItem,
    ProgramCreateRequest,
} from '@/api/programs/types';

export const programKeys = {
    all: ['programs'] as const,
    list: (params: object = {}) => [...programKeys.all, 'list', params] as const,
    publicList: (search?: string) =>
        [...programKeys.all, 'publicList', search ?? null] as const,
    detail: (uuid: string) => [...programKeys.all, 'detail', uuid] as const,
    bySlug: (slug: string, owned: boolean) =>
        [...programKeys.all, 'bySlug', slug, owned] as const,
    myEnrollments: () => [...programKeys.all, 'myEnrollments'] as const,
} as const;

export function useMyProgramEnrollments() {
    return useQuery<ProgramEnrollment[]>({
        queryKey: programKeys.myEnrollments(),
        queryFn: getMyProgramEnrollments,
        staleTime: 1000 * 30,
    });
}

export function usePrograms(params?: { owned?: boolean; search?: string }) {
    return useQuery<ProgramListItem[]>({
        queryKey: programKeys.list(params ?? {}),
        queryFn: () => getPrograms(params),
        staleTime: 1000 * 30,
    });
}

export function usePublicPrograms(search?: string) {
    return useQuery<ProgramListItem[]>({
        queryKey: programKeys.publicList(search),
        queryFn: () => getPublicPrograms(search),
        staleTime: 1000 * 30,
    });
}

export function useProgram(uuid: string | undefined) {
    return useQuery<Program>({
        queryKey: uuid ? programKeys.detail(uuid) : ['programs', 'detail', 'noop'],
        queryFn: () => getProgram(uuid!),
        enabled: Boolean(uuid),
    });
}

export function useProgramBySlug(slug: string | undefined, owned = false) {
    return useQuery({
        queryKey: slug ? programKeys.bySlug(slug, owned) : ['programs', 'bySlug', 'noop'],
        queryFn: () => getProgramBySlug(slug!, owned),
        enabled: Boolean(slug),
    });
}

export function useCreateProgram() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (data: ProgramCreateRequest) => createProgram(data),
        onSuccess: () => queryClient.invalidateQueries({ queryKey: programKeys.all }),
    });
}

export function useUpdateProgram() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ uuid, data }: { uuid: string; data: Partial<ProgramCreateRequest> }) =>
            updateProgram(uuid, data),
        onSuccess: (_data, { uuid }) => {
            queryClient.invalidateQueries({ queryKey: programKeys.all });
            queryClient.invalidateQueries({ queryKey: programKeys.detail(uuid) });
        },
    });
}

export function useDeleteProgram() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: deleteProgram,
        onSuccess: (_data, uuid) => {
            queryClient.invalidateQueries({ queryKey: programKeys.all });
            queryClient.removeQueries({ queryKey: programKeys.detail(uuid) });
        },
    });
}

export function usePublishProgram() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: publishProgram,
        onSuccess: () => queryClient.invalidateQueries({ queryKey: programKeys.all }),
    });
}
