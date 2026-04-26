/**
 * Legacy token-storage shim.
 *
 * Tokens now live in `features/auth/store/authStore.ts` (Zustand,
 * persisted). These functions delegate so existing imperative callers
 * (e.g. `api/client.ts` interceptors) keep working unchanged. New code
 * should use the store / hooks directly.
 *
 * Slated for deletion once api/client.ts is refactored to import the
 * store directly (P3a follow-up).
 */
import { useAuthStore } from '@/features/auth/store/authStore';

export interface DecodedToken {
    user_uuid: string;
    exp: number;
    iat: number;
    jti: string;
}

export const setToken = (access: string, refresh?: string) => {
    useAuthStore.getState().setTokens(access, refresh);
};

export const getToken = () => useAuthStore.getState().accessToken;

export const getRefreshToken = () => useAuthStore.getState().refreshToken;

export const removeToken = () => useAuthStore.getState().clearTokens();

export const isTokenValid = (_token: string): boolean => {
    // Accept the parameter for backwards compatibility but always trust
    // the store's check, which decodes the JWT itself.
    return useAuthStore.getState().hasValidAccessToken();
};

export const getUserFromToken = () => {
    const uuid = useAuthStore.getState().getUserUuid();
    if (!uuid) return null;
    return { uuid };
};
