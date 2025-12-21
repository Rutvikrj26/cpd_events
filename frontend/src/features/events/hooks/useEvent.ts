import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/lib/queryClient';
import { getEvent } from '../services';
import type { Event } from '../types';

/**
 * Hook to fetch a single event by UUID
 */
export function useEvent(uuid: string | undefined) {
    return useQuery<Event, Error>({
        queryKey: queryKeys.events.detail(uuid ?? ''),
        queryFn: () => getEvent(uuid!),
        enabled: !!uuid, // Only fetch when uuid is provided
    });
}
