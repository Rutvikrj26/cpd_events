/**
 * Shared API types for consistent error handling.
 * Matches the backend's custom exception handler format in common/exceptions.py.
 */

/**
 * The structure of the 'error' object within an API error response.
 */
export interface ApiErrorPayload {
    code: string;
    message: string;
    details?: Record<string, string[]> | null;
}

/**
 * The full API error response wrapper.
 */
export interface ApiErrorResponse {
    error: ApiErrorPayload;
}
