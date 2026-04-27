import { useQuery, type UseQueryOptions } from '@tanstack/react-query';
import { getDeploymentConfig, type DeploymentConfig } from '@/api/auth/manifest';
import { authKeys } from './queryKeys';

/**
 * useDeployment — public-facing deployment config (institution branding,
 * registration mode). No auth required, so this can fire on cold-load.
 *
 * Backed by the same data the authenticated manifest exposes; we expose
 * a separate hook because public pages (login, signup) need it before
 * any token exists.
 */
export function useDeployment(
    options?: Omit<UseQueryOptions<DeploymentConfig, Error, DeploymentConfig, ReturnType<typeof authKeys.deployment>>, 'queryKey' | 'queryFn'>
) {
    return useQuery({
        queryKey: authKeys.deployment(),
        queryFn: getDeploymentConfig,
        // Deployment config is set once per tenant; rarely changes.
        staleTime: 1000 * 60 * 30,
        ...options,
    });
}
