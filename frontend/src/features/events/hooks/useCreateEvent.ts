import { useMutation, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '@/lib/queryClient';
import { createEvent } from '../services';
import type { Event, EventCreateRequest } from '../types';

/**
 * Hook for creating a new event with automatic cache invalidation
 */
export function useCreateEvent() {
    const queryClient = useQueryClient();

    return useMutation<Event, Error, EventCreateRequest>({
        mutationFn: createEvent,
        onSuccess: () => {
            // Invalidate events list to refetch
            queryClient.invalidateQueries({ queryKey: queryKeys.events.list() });
        },
    });
}
