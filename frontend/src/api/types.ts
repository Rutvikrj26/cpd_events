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

/**
 * Standard paginated response from the backend.
 * Matches common/pagination.py StandardPagination format.
 */
export interface PaginatedResponse<T> {
    count: number;
    page: number;
    page_size: number;
    total_pages: number;
    next: string | null;
    previous: string | null;
    results: T[];
}

/**
 * Pagination query parameters accepted by list endpoints.
 */
export interface PaginationParams {
    page?: number;
    page_size?: number;
}
