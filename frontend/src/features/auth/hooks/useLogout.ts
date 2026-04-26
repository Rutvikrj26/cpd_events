import { useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../store/authStore';

/**
 * useLogout — clear tokens, evict the React Query cache, navigate home.
 *
 * Returns a stable callback. Not a mutation because the operation is
 * client-only (no server side-effect required).
 */
export function useLogout() {
    const clearTokens = useAuthStore((s) => s.clearTokens);
    const queryClient = useQueryClient();

    return useCallback(() => {
        clearTokens();
        queryClient.clear();
        // Hard nav to /login so any in-flight subscriptions / sockets get
        // torn down by a fresh page load.
        if (typeof window !== 'undefined') {
            window.location.href = '/login';
        }
    }, [clearTokens, queryClient]);
}
