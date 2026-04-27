import { useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../store/authStore';
import { useCurrentUser } from './useCurrentUser';
import { useManifest } from './useManifest';
import { useDeployment } from './useDeployment';
import { useLogin, useCompleteLogin } from './useLogin';
import { useLogout } from './useLogout';
import { authKeys } from './queryKeys';
import type { User, LoginRequest } from '@/api/accounts/types';
import type { Manifest, DeploymentConfig } from '@/api/auth/manifest';

/**
 * useAuth — composite auth hook.
 *
 * Wraps the underlying Zustand store + RQ queries + RQ mutations behind
 * a single API surface that matches the legacy AuthContext shape, so
 * existing consumers (~34 files) work without changes.
 *
 * **Prefer the granular hooks** (`useCurrentUser`, `useManifest`,
 * `useLogin`, etc.) when writing new code — they re-render less and
 * compose better.
 */
export interface UseAuthReturn {
    user: User | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    manifest: Manifest | null;
    deployment: DeploymentConfig | null;

    login: (data: LoginRequest) => Promise<void>;
    completeLogin: (access: string, refresh: string) => Promise<void>;
    logout: () => void;

    hasRoute: (routeKey: string) => boolean;
    hasFeature: (feature: keyof Manifest['features']) => boolean;

    refreshUser: () => Promise<void>;
    refreshManifest: () => Promise<void>;

    /** Token setter retained for legacy callers (e.g. invitation flow). */
    setToken: (access: string, refresh: string) => void;
    /** No-op kept for shape compatibility. The store derives this. */
    setIsAuthenticated: (value: boolean) => void;
    /** No-op kept for shape compatibility. The query owns user state. */
    setUser: (user: User | null) => void;
    fetchManifest: () => Promise<void>;
}

export function useAuth(): UseAuthReturn {
    const accessToken = useAuthStore((s) => s.accessToken);
    const setTokens = useAuthStore((s) => s.setTokens);
    const queryClient = useQueryClient();

    const userQuery = useCurrentUser();
    const manifestQuery = useManifest();
    // Public deployment query — also useful for unauthenticated pages.
    const deploymentQuery = useDeployment({
        // Once we're authenticated, manifest carries the deployment too;
        // skip the public endpoint to save a round-trip.
        enabled: !accessToken,
    });

    const loginMut = useLogin();
    const completeLoginMut = useCompleteLogin();
    const logoutCallback = useLogout();

    const isAuthenticated = Boolean(accessToken);
    const manifest = manifestQuery.data ?? null;
    const deployment = manifest?.deployment ?? deploymentQuery.data ?? null;

    // isLoading semantics match the old context: true until we know
    // whether we have a session AND have hydrated the profile if so.
    const isLoading = isAuthenticated
        ? userQuery.isLoading || manifestQuery.isLoading
        : deploymentQuery.isLoading;

    return {
        user: userQuery.data ?? null,
        isAuthenticated,
        isLoading,
        manifest,
        deployment,

        login: async (data) => {
            await loginMut.mutateAsync(data);
        },
        completeLogin: async (access, refresh) => {
            await completeLoginMut.mutateAsync({ access, refresh });
        },
        logout: logoutCallback,

        hasRoute: (routeKey) => Boolean(manifest?.routes.includes(routeKey)),
        hasFeature: (feature) => Boolean(manifest?.features[feature]),

        refreshUser: async () => {
            await queryClient.invalidateQueries({ queryKey: authKeys.currentUser() });
        },
        refreshManifest: async () => {
            await queryClient.invalidateQueries({ queryKey: authKeys.manifest() });
        },

        setToken: (access, refresh) => setTokens(access, refresh),
        setIsAuthenticated: () => undefined, // derived from token presence
        setUser: () => undefined, // owned by RQ cache
        fetchManifest: async () => {
            await queryClient.invalidateQueries({ queryKey: authKeys.manifest() });
        },
    };
}
