/**
 * Query keys for the auth feature. Keep all auth-related cache keys
 * centralized so invalidations are exact and refactor-safe.
 */
export const authKeys = {
    all: ['auth'] as const,
    currentUser: () => [...authKeys.all, 'currentUser'] as const,
    manifest: () => [...authKeys.all, 'manifest'] as const,
    deployment: () => [...authKeys.all, 'deployment'] as const,
} as const;
