import { useMutation, useQueryClient } from '@tanstack/react-query';
import { updateEvent, deleteEvent } from '../services';
import type { Event, EventUpdateRequest } from '../types';
import { eventKeys } from './queryKeys';

interface UpdateEventVariables {
    uuid: string;
    data: EventUpdateRequest;
}

/**
 * useUpdateEvent — PATCH + invalidate list + invalidate the specific
 * event's detail. Refetched automatically by any mounted consumer.
 */
export function useUpdateEvent() {
    const queryClient = useQueryClient();
    return useMutation<Event, Error, UpdateEventVariables>({
        mutationFn: ({ uuid, data }) => updateEvent(uuid, data),
        onSuccess: (_, { uuid }) => {
            queryClient.invalidateQueries({ queryKey: eventKeys.all });
            queryClient.invalidateQueries({ queryKey: eventKeys.detail(uuid) });
        },
    });
}

/**
 * useDeleteEvent — DELETE + remove from cache so a redirect away from
 * the now-gone detail page doesn't show stale data on bfcache hit.
 */
export function useDeleteEvent() {
    const queryClient = useQueryClient();
    return useMutation<void, Error, string>({
        mutationFn: deleteEvent,
        onSuccess: (_, uuid) => {
            queryClient.invalidateQueries({ queryKey: eventKeys.all });
            queryClient.removeQueries({ queryKey: eventKeys.detail(uuid) });
        },
    });
}
