import axios from 'axios';
import { getToken, getRefreshToken, setToken, removeToken } from '@/lib/auth';
import { ApiErrorResponse } from './types';
import { toast } from 'sonner';

/**
 * Error-handling conventions for this client
 * ------------------------------------------
 *
 * The response interceptor below auto-toasts only the kinds of errors that
 * are genuinely unexpected:
 *
 *   - **5xx**          — server bugs, never user-actionable. Always toast.
 *   - **Network**      — request never reached the server. Always toast.
 *   - **401**          — handled separately (token refresh + login redirect).
 *   - **4xx (others)** — domain conditions the calling component is
 *                        expected to handle inline (e.g. "already enrolled",
 *                        "pending approval", validation field errors).
 *                        Silent by default; opt-in via `toastOnError: true`.
 *
 * This was reversed during the typed-contract migration. Previously every
 * non-401 produced a toast, which meant pages with multiple legitimate 4xx
 * states (course player landing on a not-enrolled course, etc.) toast-spammed
 * users with redundant info already shown inline. The new default is "the
 * caller owns 4xx UX"; toast spam shows up only when the caller forgets, in
 * which case nothing flashes by accident.
 *
 * If a caller needs the legacy auto-toast for a specific 4xx — e.g. a fire-
 * and-forget mutation where there's no UI to surface the error inline —
 * pass `toastOnError: true` on the axios config.
 *
 * The legacy `silent: true` option still works for symmetry and for the
 * 5xx case (e.g. a polling endpoint that doesn't want to flash a server-
 * error toast on every retry).
 */
declare module 'axios' {
    export interface AxiosRequestConfig {
        // Force-suppress the global toast even for 5xx / network errors.
        // Use sparingly — meant for polling endpoints and similar where
        // transient failures are expected.
        silent?: boolean;
        // Opt INTO the global toast for 4xx domain errors. Use when the
        // caller has no UI to render the error inline (e.g. background
        // mutations triggered by keyboard shortcuts).
        toastOnError?: boolean;
    }
}

// Maximum length of the toast description. DRF errors that contain a
// stringified dict (e.g. SlugRelatedField rejecting a nested object) can
// balloon to several hundred chars; truncating keeps the toast readable.
const TOAST_DESCRIPTION_MAX = 240;

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const client = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Public endpoints that should NOT include Authorization header or trigger refresh
const PUBLIC_ENDPOINTS = [
    '/auth/token/',
    '/auth/token/refresh/',
    '/auth/verify-email/',
    '/auth/password-reset/',
    '/auth/password-reset/confirm/',
    '/auth/zoom/login/',
    '/auth/zoom/callback/',
    '/badges/issued/public/',
];

function isPublicEndpoint(url: string | undefined): boolean {
    return PUBLIC_ENDPOINTS.some(ep => url?.includes(ep));
}

// ---------- Token refresh queue ----------
// When the access token expires and multiple requests fail with 401 simultaneously,
// only ONE refresh request is sent. All others wait in the queue and retry with the new token.
let isRefreshing = false;
let failedQueue: { resolve: (token: string) => void; reject: (err: unknown) => void }[] = [];

function processQueue(error: unknown, token: string | null) {
    failedQueue.forEach(({ resolve, reject }) => {
        if (token) resolve(token);
        else reject(error);
    });
    failedQueue = [];
}

// ---------- Request interceptor ----------
client.interceptors.request.use(
    (config) => {
        if (!isPublicEndpoint(config.url)) {
            const token = getToken();
            if (token) {
                config.headers['Authorization'] = `Bearer ${token}`;
            }
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// ---------- Response interceptor ----------
client.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;

        // --- 401: attempt token refresh (except for public endpoints and retries) ---
        if (
            error.response?.status === 401 &&
            !isPublicEndpoint(originalRequest?.url) &&
            !originalRequest._retry
        ) {
            const refreshToken = getRefreshToken();
            if (!refreshToken) {
                removeToken();
                window.location.href = '/login';
                return Promise.reject(error);
            }

            if (isRefreshing) {
                // Another refresh is in flight — queue this request
                return new Promise<string>((resolve, reject) => {
                    failedQueue.push({ resolve, reject });
                }).then((newToken) => {
                    originalRequest.headers['Authorization'] = `Bearer ${newToken}`;
                    return client(originalRequest);
                });
            }

            isRefreshing = true;
            originalRequest._retry = true;

            try {
                const { data } = await axios.post(`${API_URL}/auth/token/refresh/`, {
                    refresh: refreshToken,
                });
                const newAccess: string = data.access;
                // If server rotated the refresh token, store the new one too
                setToken(newAccess, data.refresh ?? refreshToken);
                processQueue(null, newAccess);

                originalRequest.headers['Authorization'] = `Bearer ${newAccess}`;
                return client(originalRequest);
            } catch (refreshError) {
                processQueue(refreshError, null);
                removeToken();
                window.location.href = '/login';
                return Promise.reject(refreshError);
            } finally {
                isRefreshing = false;
            }
        }

        // --- Toast policy ---
        //
        // Default behaviour, by status class:
        //   5xx, network → always toast (real bugs)
        //   401         → no toast (refresh interceptor handled it above)
        //   4xx (other) → silent unless the caller opts in via
        //                 `toastOnError: true`
        //
        // Both opt-out (`silent: true`) and opt-in (`toastOnError: true`)
        // are honoured. See the JSDoc preamble at the top of this file.
        const silent = originalRequest?.silent === true;
        const toastOnError = originalRequest?.toastOnError === true;

        if (silent) {
            return Promise.reject(error);
        }

        if (!error.response) {
            // Network error — request never reached the server.
            toast.error('Network error', {
                description: 'Could not reach the server. Check your connection and try again.',
            });
            return Promise.reject(error);
        }

        const status = error.response.status;
        if (status >= 500) {
            toast.error('Server Error', {
                description: 'Something went wrong on our end. Please try again later.',
            });
        } else if (status === 401) {
            // Handled by the refresh chain above. No toast.
        } else if (toastOnError && !isPublicEndpoint(originalRequest?.url)) {
            // 4xx with explicit opt-in.
            const errorMessage = truncate(getApiErrorMessage(error), TOAST_DESCRIPTION_MAX);
            const title =
                status === 403 ? 'Access Denied'
                : status === 404 ? 'Not Found'
                : 'Error';
            toast.error(title, { description: errorMessage });
        }
        // else: 4xx without opt-in. The calling component owns the UX.

        return Promise.reject(error);
    }
);

/** Truncate a string with an ellipsis if it exceeds `max` chars. */
function truncate(text: string, max: number): string {
    if (text.length <= max) return text;
    return text.slice(0, max - 1).trimEnd() + '…';
}

/**
 * Extracts a user-friendly error message from an API error response.
 * Handles the standard backend error format: { error: { code, message, details } }
 *
 * Use this in any caller that opts out of the global toast (`silent: true`)
 * and wants to show its own error UI. For inline form-field errors, prefer
 * `formErrorsFromApi()` from `@/lib/form-errors` which returns a structured
 * `{ fieldErrors, formErrors }` object you can feed directly into a form.
 */
export function getApiErrorMessage(error: unknown): string {
    if (axios.isAxiosError(error) && error.response?.data) {
        const data = error.response.data as ApiErrorResponse;

        if (data.error) {
            const { message, details } = data.error;

            if (details && typeof details === 'object') {
                // DRF's non-field-errors live under `__all__` (and were
                // previously rendered as "All: …"). Treat those — plus
                // explicit `non_field_errors` — as un-prefixed messages so
                // the user sees a clean sentence.
                const NON_FIELD_KEYS = new Set(['__all__', 'all', 'non_field_errors']);
                const fieldErrors = Object.entries(details)
                    .map(([field, errors]) => {
                        const text = Array.isArray(errors) ? errors.join(', ') : String(errors);
                        if (NON_FIELD_KEYS.has(field.toLowerCase())) {
                            return text;
                        }
                        const cleanField = field
                            .replace(/_/g, ' ')
                            .replace(/\b\w/g, l => l.toUpperCase());
                        return `${cleanField}: ${text}`;
                    })
                    .join('\n');
                return fieldErrors || message || 'An error occurred';
            }

            return message || 'An error occurred';
        }
    }

    if (error instanceof Error) {
        return error.message;
    }

    return 'An unexpected error occurred';
}

export default client;
