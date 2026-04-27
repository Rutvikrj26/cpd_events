import { useQuery } from '@tanstack/react-query';
import { getCourseAnnouncements } from '@/api/courses';
import { courseKeys } from './queryKeys';

export function useCourseAnnouncements(courseUuid: string | undefined) {
    return useQuery({
        queryKey: courseUuid
            ? courseKeys.announcements(courseUuid)
            : ['courses', 'announcements', 'noop'],
        queryFn: () => getCourseAnnouncements(courseUuid!),
        enabled: Boolean(courseUuid),
        staleTime: 1000 * 60,
    });
}
