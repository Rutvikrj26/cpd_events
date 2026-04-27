import { useQuery, type UseQueryOptions } from '@tanstack/react-query';
import { getManifest, type Manifest } from '@/api/auth/manifest';
import { useAuthStore } from '../store/authStore';
import { authKeys } from './queryKeys';

/**
 * useManifest — fetches the user's RBAC manifest (routes + features +
 * deployment config). Drives ProtectedRoute and the sidebar.
 *
 * Disabled without a token — public pages don't need it.
 */
export function useManifest(
    options?: Omit<UseQueryOptions<Manifest, Error, Manifest, ReturnType<typeof authKeys.manifest>>, 'queryKey' | 'queryFn' | 'enabled'>
) {
    const enabled = useAuthStore((s) => Boolean(s.accessToken));
    return useQuery({
        queryKey: authKeys.manifest(),
        queryFn: getManifest,
        enabled,
        // Manifest changes only when the user's roles/org change — stale
        // for a full session is fine.
        staleTime: 1000 * 60 * 15,
        ...options,
    });
}
