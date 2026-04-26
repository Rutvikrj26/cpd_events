import axios from 'axios';
import { getToken, getRefreshToken, setToken, removeToken } from '@/lib/auth';
import { ApiErrorResponse } from './types';
import { toast } from 'sonner';

declare module 'axios' {
    export interface AxiosRequestConfig {
        // When true, suppress the global error toast for this request.
        silent?: boolean;
    }
}

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

        // --- Toast notifications for non-401 errors ---
        // Callers can opt out by setting `silent: true` on the axios config.
        const silent = originalRequest?.silent === true;
        if (error.response && !isPublicEndpoint(originalRequest?.url) && !silent) {
            const errorMessage = getApiErrorMessage(error);

            if (error.response.status >= 500) {
                toast.error('Server Error', {
                    description: 'Something went wrong on our end. Please try again later.',
                });
            } else if (error.response.status === 403) {
                toast.error('Access Denied', { description: errorMessage });
            } else if (error.response.status === 404) {
                toast.error('Not Found', { description: errorMessage });
            } else if (error.response.status !== 401) {
                // 400, 422, etc. (skip 401 — already handled above)
                toast.error('Error', { description: errorMessage });
            }
        }

        return Promise.reject(error);
    }
);

/**
 * Extracts a user-friendly error message from an API error response.
 * Handles the standard backend error format: { error: { code, message, details } }
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
