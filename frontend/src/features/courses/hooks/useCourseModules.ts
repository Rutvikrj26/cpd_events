import { useQuery } from '@tanstack/react-query';
import { getCourseModules, getModuleContents } from '@/api/courses/modules';
import { courseKeys } from './queryKeys';

export function useCourseModules(courseUuid: string | undefined) {
    return useQuery({
        queryKey: courseUuid
            ? courseKeys.modules(courseUuid)
            : ['courses', 'modules', 'noop'],
        queryFn: () => getCourseModules(courseUuid!),
        enabled: Boolean(courseUuid),
        staleTime: 1000 * 30,
    });
}

export function useModuleContents(courseUuid: string | undefined, moduleUuid: string | undefined) {
    return useQuery({
        queryKey:
            courseUuid && moduleUuid
                ? courseKeys.moduleContents(moduleUuid)
                : ['courses', 'moduleContents', 'noop'],
        queryFn: () => getModuleContents(courseUuid!, moduleUuid!),
        enabled: Boolean(courseUuid && moduleUuid),
    });
}
