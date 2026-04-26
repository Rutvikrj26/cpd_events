import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getMyRegistrations, registerForEvent } from '@/api/registrations';
import type { Registration } from '@/api/registrations/types';
import { eventKeys } from './queryKeys';

/**
 * useMyRegistrations — current user's event registrations (My Learning).
 */
export function useMyRegistrations() {
    return useQuery({
        queryKey: eventKeys.myRegistrations(),
        queryFn: async () => (await getMyRegistrations()).results as Registration[],
        staleTime: 1000 * 30,
    });
}

/**
 * useRegisterForEvent — mutation to register the current user for an event.
 * Invalidates the user's registrations list and the event's attendee
 * count so dashboards re-render with the new state.
 */
export function useRegisterForEvent() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ eventUuid, payload }: { eventUuid: string; payload: any }) =>
            registerForEvent(eventUuid, payload),
        onSuccess: (_data, { eventUuid }) => {
            queryClient.invalidateQueries({ queryKey: eventKeys.myRegistrations() });
            queryClient.invalidateQueries({ queryKey: eventKeys.detail(eventUuid) });
        },
    });
}
