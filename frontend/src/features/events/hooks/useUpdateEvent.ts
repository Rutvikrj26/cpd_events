import { useMutation, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '@/lib/queryClient';
import { updateEvent, deleteEvent } from '../services';
import type { Event, EventUpdateRequest } from '../types';

interface UpdateEventVariables {
    uuid: string;
    data: EventUpdateRequest;
}

/**
 * Hook for updating an event with automatic cache invalidation
 */
export function useUpdateEvent() {
    const queryClient = useQueryClient();

    return useMutation<Event, Error, UpdateEventVariables>({
        mutationFn: ({ uuid, data }) => updateEvent(uuid, data),
        onSuccess: (_, { uuid }) => {
            // Invalidate both the list and the specific event
            queryClient.invalidateQueries({ queryKey: queryKeys.events.list() });
            queryClient.invalidateQueries({ queryKey: queryKeys.events.detail(uuid) });
        },
    });
}

/**
 * Hook for deleting an event with automatic cache invalidation
 */
export function useDeleteEvent() {
    const queryClient = useQueryClient();

    return useMutation<void, Error, string>({
        mutationFn: deleteEvent,
        onSuccess: (_, uuid) => {
            // Invalidate list and remove the specific event from cache
            queryClient.invalidateQueries({ queryKey: queryKeys.events.list() });
            queryClient.removeQueries({ queryKey: queryKeys.events.detail(uuid) });
        },
    });
}
