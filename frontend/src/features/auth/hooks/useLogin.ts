import { useMutation, useQueryClient } from '@tanstack/react-query';
import { login as apiLogin } from '@/api/accounts';
import type { LoginRequest } from '@/api/accounts/types';
import { useAuthStore } from '../store/authStore';
import { authKeys } from './queryKeys';

/**
 * useLogin — credentials → tokens → cache hydration.
 *
 * Mutation, not a query, because logging in has side effects (token
 * persistence + cache invalidation). Pages call `mutateAsync(data)` and
 * await the resulting promise to navigate on success or surface the
 * error.
 */
export function useLogin() {
    const setTokens = useAuthStore((s) => s.setTokens);
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (data: LoginRequest) => {
            const { access, refresh } = await apiLogin(data);
            setTokens(access, refresh);
            // Force re-fetch of user + manifest on next render.
            await queryClient.invalidateQueries({ queryKey: authKeys.all });
            return { access, refresh };
        },
    });
}

/**
 * useCompleteLogin — finish a login when tokens were obtained
 * out-of-band (Firebase, invitation acceptance, email verification).
 * Same hydration semantics as `useLogin`.
 */
export function useCompleteLogin() {
    const setTokens = useAuthStore((s) => s.setTokens);
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async ({ access, refresh }: { access: string; refresh: string }) => {
            setTokens(access, refresh);
            await queryClient.invalidateQueries({ queryKey: authKeys.all });
        },
    });
}
