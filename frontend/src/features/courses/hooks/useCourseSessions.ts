import { useQuery } from '@tanstack/react-query';
import { getCourseSessions } from '@/api/courses';
import { courseKeys } from './queryKeys';

export function useCourseSessions(courseUuid: string | undefined) {
    return useQuery({
        queryKey: courseUuid
            ? courseKeys.sessions(courseUuid)
            : ['courses', 'sessions', 'noop'],
        queryFn: () => getCourseSessions(courseUuid!),
        enabled: Boolean(courseUuid),
        staleTime: 1000 * 30,
    });
}
