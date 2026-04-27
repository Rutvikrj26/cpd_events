import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    getNotifications,
    markNotificationRead,
    markAllNotificationsRead,
    deleteNotification,
} from '@/api/notifications';

export const notificationKeys = {
    all: ['notifications'] as const,
    list: (params: object = {}) => [...notificationKeys.all, 'list', params] as const,
} as const;

export function useNotifications(params?: { unreadOnly?: boolean }) {
    const apiParams = params?.unreadOnly ? { status: 'unread' as const } : undefined;
    return useQuery({
        queryKey: notificationKeys.list(params ?? {}),
        queryFn: () => getNotifications(apiParams),
        // Refetch on focus so the bell badge updates when the user
        // returns from another tab.
        refetchOnWindowFocus: true,
        staleTime: 1000 * 30,
    });
}

export function useMarkNotificationRead() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (uuid: string) => markNotificationRead(uuid),
        onSuccess: () =>
            queryClient.invalidateQueries({ queryKey: notificationKeys.all }),
    });
}

export function useMarkAllNotificationsRead() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: markAllNotificationsRead,
        onSuccess: () =>
            queryClient.invalidateQueries({ queryKey: notificationKeys.all }),
    });
}

export function useDeleteNotification() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (uuid: string) => deleteNotification(uuid),
        onSuccess: () =>
            queryClient.invalidateQueries({ queryKey: notificationKeys.all }),
    });
}
