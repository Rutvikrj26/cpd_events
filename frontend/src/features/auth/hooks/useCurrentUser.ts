import { useQuery, type UseQueryOptions } from '@tanstack/react-query';
import { getCurrentUser } from '@/api/accounts';
import type { User } from '@/api/accounts/types';
import { useAuthStore } from '../store/authStore';
import { authKeys } from './queryKeys';

/**
 * useCurrentUser — fetch the authenticated user's profile.
 *
 * Disabled when there's no valid token, so it doesn't fire 401s on
 * cold-start of public pages.
 */
export function useCurrentUser(
    options?: Omit<UseQueryOptions<User, Error, User, ReturnType<typeof authKeys.currentUser>>, 'queryKey' | 'queryFn' | 'enabled'>
) {
    const enabled = useAuthStore((s) => Boolean(s.accessToken));
    return useQuery({
        queryKey: authKeys.currentUser(),
        queryFn: getCurrentUser,
        enabled,
        // Profile data rarely changes mid-session; don't thrash the network
        // on every focus.
        staleTime: 1000 * 60 * 5,
        ...options,
    });
}
