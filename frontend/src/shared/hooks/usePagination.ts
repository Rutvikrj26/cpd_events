import { useState, useCallback, useMemo } from 'react';
import { PaginatedResponse } from '@/api/types';

/**
 * Pagination state returned by usePagination hook.
 */
export interface PaginationState {
    page: number;
    pageSize: number;
    totalPages: number;
    totalCount: number;
    hasNextPage: boolean;
    hasPrevPage: boolean;
}

/**
 * Options for the usePagination hook.
 */
export interface UsePaginationOptions {
    initialPage?: number;
    initialPageSize?: number;
}

/**
 * Hook for managing pagination state.
 * Works with PaginatedResponse from the API.
 */
export function usePagination(options: UsePaginationOptions = {}) {
    const { initialPage = 1, initialPageSize = 20 } = options;

    const [page, setPage] = useState(initialPage);
    const [pageSize, setPageSize] = useState(initialPageSize);
    const [totalPages, setTotalPages] = useState(1);
    const [totalCount, setTotalCount] = useState(0);

    /**
     * Update pagination state from API response.
     */
    const updateFromResponse = useCallback(<T>(response: PaginatedResponse<T>) => {
        setPage(response.page);
        setPageSize(response.page_size);
        setTotalPages(response.total_pages);
        setTotalCount(response.count);
    }, []);

    /**
     * Go to a specific page.
     */
    const goToPage = useCallback((newPage: number) => {
        if (newPage >= 1 && newPage <= totalPages) {
            setPage(newPage);
        }
    }, [totalPages]);

    /**
     * Go to the next page.
     */
    const nextPage = useCallback(() => {
        if (page < totalPages) {
            setPage((p) => p + 1);
        }
    }, [page, totalPages]);

    /**
     * Go to the previous page.
     */
    const prevPage = useCallback(() => {
        if (page > 1) {
            setPage((p) => p - 1);
        }
    }, [page]);

    /**
     * Change page size and reset to page 1.
     */
    const changePageSize = useCallback((newSize: number) => {
        setPageSize(newSize);
        setPage(1);
    }, []);

    /**
     * Reset pagination to initial state.
     */
    const reset = useCallback(() => {
        setPage(initialPage);
        setPageSize(initialPageSize);
        setTotalPages(1);
        setTotalCount(0);
    }, [initialPage, initialPageSize]);

    const state: PaginationState = useMemo(() => ({
        page,
        pageSize,
        totalPages,
        totalCount,
        hasNextPage: page < totalPages,
        hasPrevPage: page > 1,
    }), [page, pageSize, totalPages, totalCount]);

    return {
        ...state,
        goToPage,
        nextPage,
        prevPage,
        changePageSize,
        reset,
        updateFromResponse,
    };
}

export type UsePaginationReturn = ReturnType<typeof usePagination>;
