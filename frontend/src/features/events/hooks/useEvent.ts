import { useQuery } from '@tanstack/react-query';
import { getEvent } from '../services';
import type { Event } from '../types';
import { eventKeys } from './queryKeys';

/**
 * useEvent — fetch a single event by UUID. Disabled when `uuid` is
 * undefined so consumers can call it before route params resolve.
 */
export function useEvent(uuid: string | undefined) {
    return useQuery<Event>({
        queryKey: uuid ? eventKeys.detail(uuid) : ['events', 'detail', 'noop'],
        queryFn: () => getEvent(uuid!),
        enabled: Boolean(uuid),
        staleTime: 1000 * 30,
    });
}
