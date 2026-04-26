import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { jwtDecode } from 'jwt-decode';

/**
 * Auth store — single source of truth for tokens and derived auth state.
 *
 * Replaces the imperative `lib/auth.ts` localStorage shim and the
 * `setToken / setIsAuthenticated` setters that AuthContext exposed.
 *
 * Server-side data (user, manifest, deployment) lives in React Query —
 * NOT here. This store only owns:
 *   - access + refresh token strings
 *   - a memoized `isAuthenticated` flag derived from token validity
 *
 * Anything that needs the user's profile should call `useCurrentUser()`.
 * Anything that needs RBAC should call `useManifest()`.
 */

interface DecodedToken {
    user_uuid: string;
    exp: number;
    iat: number;
    jti: string;
}

interface AuthStateData {
    accessToken: string | null;
    refreshToken: string | null;
}

interface AuthStateActions {
    /** Persist a new token pair (after login or refresh). */
    setTokens: (access: string, refresh?: string) => void;
    /** Wipe tokens (logout / refresh failure). */
    clearTokens: () => void;
    /** Token-validity check used by interceptors and route guards. */
    hasValidAccessToken: () => boolean;
    /** Subject UUID encoded in the JWT, when present. */
    getUserUuid: () => string | null;
}

type AuthState = AuthStateData & AuthStateActions;

const STORAGE_KEY = 'accredit-auth';
// Legacy keys used by lib/auth.ts before the store existed. Migrated once
// at module load so existing sessions don't get logged out by the cutover.
const LEGACY_ACCESS_KEY = 'cpd_auth_token';
const LEGACY_REFRESH_KEY = 'cpd_refresh_token';

function migrateLegacyTokens(): { access: string | null; refresh: string | null } {
    if (typeof window === 'undefined') return { access: null, refresh: null };
    try {
        // If the new store already has data, leave it alone.
        if (window.localStorage.getItem(STORAGE_KEY)) {
            return { access: null, refresh: null };
        }
        const access = window.localStorage.getItem(LEGACY_ACCESS_KEY);
        const refresh = window.localStorage.getItem(LEGACY_REFRESH_KEY);
        if (access || refresh) {
            window.localStorage.removeItem(LEGACY_ACCESS_KEY);
            window.localStorage.removeItem(LEGACY_REFRESH_KEY);
        }
        return { access, refresh };
    } catch {
        return { access: null, refresh: null };
    }
}

const legacy = migrateLegacyTokens();

export const useAuthStore = create<AuthState>()(
    persist(
        (set, get) => ({
            accessToken: legacy.access,
            refreshToken: legacy.refresh,
            setTokens: (access, refresh) =>
                set({
                    accessToken: access,
                    refreshToken: refresh ?? get().refreshToken,
                }),
            clearTokens: () =>
                set({
                    accessToken: null,
                    refreshToken: null,
                }),
            hasValidAccessToken: () => {
                const token = get().accessToken;
                if (!token) return false;
                try {
                    const decoded = jwtDecode<DecodedToken>(token);
                    return decoded.exp * 1000 > Date.now();
                } catch {
                    return false;
                }
            },
            getUserUuid: () => {
                const token = get().accessToken;
                if (!token) return null;
                try {
                    const decoded = jwtDecode<DecodedToken>(token);
                    return decoded.user_uuid ?? null;
                } catch {
                    return null;
                }
            },
        }),
        {
            name: STORAGE_KEY,
            partialize: (state) => ({
                accessToken: state.accessToken,
                refreshToken: state.refreshToken,
            }),
        }
    )
);

/* ------------------------------------------------------------------ */
/* Selectors                                                           */
/* ------------------------------------------------------------------ */

/** Convenience selector — drives ProtectedRoute + the route guard. */
export const useIsAuthenticated = () =>
    useAuthStore((s) => Boolean(s.accessToken) && s.hasValidAccessToken());
