/**
 * Helpers for consuming DRF paginated list responses.
 *
 * Every Django ModelViewSet `.list()` in this project goes through
 * `common.pagination.StandardPagination`, which wraps results as:
 *   { count, page, page_size, total_pages, next, previous, results: [...] }
 *
 * However, a handful of endpoints (custom `@action` methods, non-DRF views)
 * return a plain array. Clients should use `unwrapList` so both shapes work
 * the same way on the call site.
 */

export interface PaginatedResponse<T> {
    count: number;
    page?: number;
    page_size?: number;
    total_pages?: number;
    next: string | null;
    previous: string | null;
    results: T[];
}

/**
 * Normalises a list-endpoint response body into a plain array.
 * Accepts:
 *  - An array (already unwrapped, e.g. from a custom action)
 *  - A DRF paginated envelope with `.results`
 *  - `null` / `undefined` (returns `[]`)
 */
export function unwrapList<T>(data: unknown): T[] {
    if (Array.isArray(data)) return data as T[];
    if (data && typeof data === 'object' && Array.isArray((data as PaginatedResponse<T>).results)) {
        return (data as PaginatedResponse<T>).results;
    }
    return [];
}
