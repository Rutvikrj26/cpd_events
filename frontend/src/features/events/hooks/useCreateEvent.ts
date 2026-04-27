import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createEvent } from '../services';
import type { Event, EventCreateRequest } from '../types';
import { eventKeys } from './queryKeys';

/**
 * useCreateEvent — POST + automatic list invalidation.
 */
export function useCreateEvent() {
    const queryClient = useQueryClient();
    return useMutation<Event, Error, EventCreateRequest>({
        mutationFn: createEvent,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: eventKeys.all });
        },
    });
}
