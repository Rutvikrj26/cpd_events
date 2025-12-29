import axios from 'axios';
import { getToken, removeToken } from '@/lib/auth';
import { ApiErrorResponse } from './types';
import { toast } from 'sonner';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const client = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Public endpoints that should NOT include Authorization header
const PUBLIC_ENDPOINTS = [
    '/auth/signup/',
    '/auth/token/',
    '/auth/token/refresh/',
    '/auth/verify-email/',
    '/auth/password-reset/',
    '/auth/password-reset/confirm/',
    '/auth/zoom/login/',
    '/auth/zoom/callback/',
];

// Endpoints where we suppress global error toasts (they handle their own errors)
const SILENT_ERROR_ENDPOINTS: string[] = [];

client.interceptors.request.use(
    (config) => {
        // Skip adding Authorization header for public endpoints
        const isPublicEndpoint = PUBLIC_ENDPOINTS.some(
            endpoint => config.url?.includes(endpoint)
        );

        if (!isPublicEndpoint) {
            const token = getToken();
            if (token) {
                config.headers['Authorization'] = `Bearer ${token}`;
            }
        }
        return config;
    },
    (error) => Promise.reject(error)
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

            // If there are field-level details, format them nicely
            if (details && typeof details === 'object') {
                const fieldErrors = Object.entries(details)
                    .map(([field, errors]) => {
                        // Clean up field name (convert snake_case to Title Case)
                        const cleanField = field
                            .replace(/_/g, ' ')
                            .replace(/\b\w/g, l => l.toUpperCase());
                        return `${cleanField}: ${Array.isArray(errors) ? errors.join(', ') : errors}`;
                    })
                    .join('\n');
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

client.interceptors.response.use(
    (response) => response,
    (error) => {
        const isPublicEndpoint = PUBLIC_ENDPOINTS.some(
            endpoint => error.config?.url?.includes(endpoint)
        );

        const isSilentEndpoint = SILENT_ERROR_ENDPOINTS.some(
            endpoint => error.config?.url?.includes(endpoint)
        );

        // Handle 401 - redirect to login (except for public auth endpoints)
        if (error.response?.status === 401 && !isPublicEndpoint) {
            removeToken();
            window.location.href = '/login';
            return Promise.reject(error);
        }

        // Show toast for all API errors (unless endpoint is in silent list)
        if (error.response && !isSilentEndpoint) {
            const errorMessage = getApiErrorMessage(error);

            // Use different toast styles based on error type
            if (error.response.status >= 500) {
                toast.error('Server Error', {
                    description: 'Something went wrong on our end. Please try again later.',
                });
            } else if (error.response.status === 403) {
                toast.error('Access Denied', {
                    description: errorMessage,
                });
            } else if (error.response.status === 404) {
                toast.error('Not Found', {
                    description: errorMessage,
                });
            } else {
                // 400, 401, 422, etc.
                toast.error('Error', {
                    description: errorMessage,
                });
            }
        }

        return Promise.reject(error);
    }
);

export default client;
