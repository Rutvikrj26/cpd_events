import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    listInvitations,
    getAdminUserDetail,
    updateAdminUser,
} from '@/api/accounts';

export const adminKeys = {
    all: ['admin'] as const,
    invitations: () => [...adminKeys.all, 'invitations'] as const,
    userDetail: (uuid: string) => [...adminKeys.all, 'userDetail', uuid] as const,
} as const;

export function useInvitations() {
    return useQuery({
        queryKey: adminKeys.invitations(),
        queryFn: () => listInvitations(),
        staleTime: 1000 * 30,
    });
}

export function useAdminUserDetail(uuid: string | undefined) {
    return useQuery({
        queryKey: uuid ? adminKeys.userDetail(uuid) : ['admin', 'userDetail', 'noop'],
        queryFn: () => getAdminUserDetail(uuid!),
        enabled: Boolean(uuid),
    });
}

export function useUpdateAdminUser() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({
            uuid,
            data,
        }: {
            uuid: string;
            data: { roles?: string[]; full_name?: string; is_active?: boolean };
        }) => updateAdminUser(uuid, data),
        onSuccess: (_data, { uuid }) => {
            queryClient.invalidateQueries({ queryKey: adminKeys.userDetail(uuid) });
            queryClient.invalidateQueries({ queryKey: adminKeys.all });
        },
    });
}
