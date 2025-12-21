import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/lib/queryClient';
import { getEvents, getPublicEvents } from '../services';
import type { Event } from '../types';

/**
 * Hook to fetch all events for the current user (organizer view)
 */
export function useEvents() {
    return useQuery<Event[], Error>({
        queryKey: queryKeys.events.list(),
        queryFn: getEvents,
    });
}

/**
 * Hook to fetch public events (discovery view)
 */
export function usePublicEvents() {
    return useQuery<Event[], Error>({
        queryKey: queryKeys.events.public(),
        queryFn: getPublicEvents,
    });
}
