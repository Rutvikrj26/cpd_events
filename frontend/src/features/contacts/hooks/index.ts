import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    getContacts,
    createContact,
    updateContact,
    deleteContact,
    getTags,
    createTag,
    updateTag,
    deleteTag,
} from '@/api/contacts';
import type { Contact } from '@/api/contacts';

export const contactKeys = {
    all: ['contacts'] as const,
    list: (params: object = {}) => [...contactKeys.all, 'list', params] as const,
    detail: (uuid: string) => [...contactKeys.all, 'detail', uuid] as const,
    tags: () => [...contactKeys.all, 'tags'] as const,
} as const;

export function useContacts(params?: Record<string, string>) {
    return useQuery({
        queryKey: contactKeys.list(params ?? {}),
        queryFn: async () => (await getContacts(params)).results as Contact[],
        staleTime: 1000 * 30,
    });
}

export function useCreateContact() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: createContact,
        onSuccess: () => queryClient.invalidateQueries({ queryKey: contactKeys.all }),
    });
}

export function useUpdateContact() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ uuid, data }: { uuid: string; data: Parameters<typeof updateContact>[1] }) =>
            updateContact(uuid, data),
        onSuccess: () => queryClient.invalidateQueries({ queryKey: contactKeys.all }),
    });
}

export function useDeleteContact() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: deleteContact,
        onSuccess: () => queryClient.invalidateQueries({ queryKey: contactKeys.all }),
    });
}

export function useTags() {
    return useQuery({
        queryKey: contactKeys.tags(),
        queryFn: async () => (await getTags()).results,
        staleTime: 1000 * 60,
    });
}

export function useCreateTag() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: createTag,
        onSuccess: () => queryClient.invalidateQueries({ queryKey: contactKeys.tags() }),
    });
}

export function useUpdateTag() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ uuid, data }: { uuid: string; data: Parameters<typeof updateTag>[1] }) =>
            updateTag(uuid, data),
        onSuccess: () => queryClient.invalidateQueries({ queryKey: contactKeys.tags() }),
    });
}

export function useDeleteTag() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: deleteTag,
        onSuccess: () => queryClient.invalidateQueries({ queryKey: contactKeys.tags() }),
    });
}
