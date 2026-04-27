import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { getPublicCourses, type PublicCourseListParams } from '@/api/courses';
import { courseKeys } from './queryKeys';

/**
 * usePublicCourses — paginated public catalog query. Uses
 * `keepPreviousData` so paging doesn't blank the grid mid-flight.
 */
export function usePublicCourses(params?: PublicCourseListParams) {
    return useQuery({
        queryKey: courseKeys.publicList(params ?? {}),
        queryFn: () => getPublicCourses(params),
        placeholderData: keepPreviousData,
        staleTime: 1000 * 30,
    });
}
