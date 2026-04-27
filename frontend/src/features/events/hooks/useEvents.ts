import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { getEvents, getPublicEvents } from '../services';
import type { Event } from '../types';
import { eventKeys } from './queryKeys';

/**
 * useEvents — organizer/admin event list. Server returns paginated;
 * `select` flattens to just `.results` so consumers get an array.
 */
export function useEvents() {
    return useQuery({
        queryKey: eventKeys.list(),
        queryFn: () => getEvents(),
        select: (data) => data.results as Event[],
        staleTime: 1000 * 30,
    });
}

/**
 * usePublicEvents — public discovery list. Same shape as useEvents
 * but hits the unauthenticated endpoint.
 */
export function usePublicEvents() {
    return useQuery({
        queryKey: eventKeys.publicList(),
        queryFn: () => getPublicEvents(),
        select: (data) => data.results as Event[],
        placeholderData: keepPreviousData,
        staleTime: 1000 * 30,
    });
}
