import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/lib/queryClient';
import { getEvents, getPublicEvents } from '../services';
import { PaginatedResponse } from '@/api/types';
import type { Event } from '../types';

/**
 * Hook to fetch all events for the current user (organizer view)
 */
export function useEvents() {
    return useQuery<PaginatedResponse<Event>, Error, Event[]>({
        queryKey: queryKeys.events.list(),
        queryFn: () => getEvents(),
        select: (data) => data.results,
    });
}

/**
 * Hook to fetch public events (discovery view)
 */
export function usePublicEvents() {
    return useQuery<PaginatedResponse<Event>, Error, Event[]>({
        queryKey: queryKeys.events.public(),
        queryFn: () => getPublicEvents(),
        select: (data) => data.results,
    });
}
