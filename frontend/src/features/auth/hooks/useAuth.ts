import { useCallback, useMemo } from 'react';
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

    // Stabilize the function returns. These are commonly destructured by
    // consumers and dropped into `useEffect` dependency arrays — recreating
    // them every render causes infinite re-render/refetch loops at the
    // call site. Scope each callback to the smallest state it actually
    // reads so identity only changes when the underlying data changes.
    const loginAsync = loginMut.mutateAsync;
    const completeLoginAsync = completeLoginMut.mutateAsync;

    const login = useCallback(async (data: LoginRequest) => {
        await loginAsync(data);
    }, [loginAsync]);

    const completeLogin = useCallback(async (access: string, refresh: string) => {
        await completeLoginAsync({ access, refresh });
    }, [completeLoginAsync]);

    const hasRoute = useCallback(
        (routeKey: string) => Boolean(manifest?.routes.includes(routeKey)),
        [manifest],
    );
    const hasFeature = useCallback(
        (feature: keyof Manifest['features']) => Boolean(manifest?.features[feature]),
        [manifest],
    );

    const refreshUser = useCallback(async () => {
        await queryClient.invalidateQueries({ queryKey: authKeys.currentUser() });
    }, [queryClient]);
    const refreshManifest = useCallback(async () => {
        await queryClient.invalidateQueries({ queryKey: authKeys.manifest() });
    }, [queryClient]);
    const fetchManifest = refreshManifest;

    const setToken = useCallback(
        (access: string, refresh: string) => setTokens(access, refresh),
        [setTokens],
    );
    // No-ops kept for shape compatibility — stable identity regardless.
    const setIsAuthenticated = useCallback(() => undefined, []);
    const setUser = useCallback(() => undefined, []);

    // Memoize the return object so consumers that destructure it (or pass
    // it whole into deps) see stable identity unless the underlying state
    // actually changes.
    return useMemo<UseAuthReturn>(() => ({
        user: userQuery.data ?? null,
        isAuthenticated,
        isLoading,
        manifest,
        deployment,

        login,
        completeLogin,
        logout: logoutCallback,

        hasRoute,
        hasFeature,

        refreshUser,
        refreshManifest,

        setToken,
        setIsAuthenticated,
        setUser,
        fetchManifest,
    }), [
        userQuery.data,
        isAuthenticated,
        isLoading,
        manifest,
        deployment,
        login,
        completeLogin,
        logoutCallback,
        hasRoute,
        hasFeature,
        refreshUser,
        refreshManifest,
        setToken,
        setIsAuthenticated,
        setUser,
        fetchManifest,
    ]);
}
