// Common/shared types
// Add any cross-feature types here

export interface PaginatedResponse<T> {
    count: number;
    next: string | null;
    previous: string | null;
    results: T[];
}

export interface ApiError {
    message: string;
    code?: string;
    details?: Record<string, string[]>;
}
