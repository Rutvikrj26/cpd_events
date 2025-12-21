import axios from 'axios';
import { getToken, removeToken } from '@/lib/auth'; // We'll keep auth helpers in lib for now or move them later if strictly modular
import { ApiErrorResponse } from './types';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const client = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

client.interceptors.request.use(
    (config) => {
        const token = getToken();
        if (token) {
            config.headers['Authorization'] = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

client.interceptors.response.use(
    (response) => response,
    (error) => {
        // Don't redirect for login 401s (just invalid credentials)
        if (error.response?.status === 401 && !error.config.url.includes('/auth/token/')) {
            removeToken();
            window.location.href = '/login';
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

            // If there are field-level details, format them
            if (details && typeof details === 'object') {
                const fieldErrors = Object.entries(details)
                    .map(([field, errors]) => `${field}: ${errors.join(', ')}`)
                    .join('; ');
                return fieldErrors || message || 'An error occurred';
            }

            return message || 'An error occurred';
        }
    }

    // Fallback for non-API errors
    if (error instanceof Error) {
        return error.message;
    }

    return 'An unexpected error occurred';
}

export default client;

