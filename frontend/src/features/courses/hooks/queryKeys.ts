/**
 * Cache keys for the courses feature.
 *
 * Hierarchy: ['courses', resource, ...args]. Always invalidate the
 * narrowest scope that's correct — e.g. invalidating
 * `courseKeys.modules(uuid)` after a module reorder, not `.all`.
 */
export const courseKeys = {
    all: ['courses'] as const,
    // Course-level
    list: () => [...courseKeys.all, 'list'] as const,
    publicList: (params: object = {}) =>
        [...courseKeys.all, 'publicList', params] as const,
    owned: () => [...courseKeys.all, 'owned'] as const,
    detail: (uuid: string) => [...courseKeys.all, 'detail', uuid] as const,
    bySlug: (slug: string) => [...courseKeys.all, 'bySlug', slug] as const,
    // Module / content
    modules: (courseUuid: string) =>
        [...courseKeys.all, 'modules', courseUuid] as const,
    moduleContents: (moduleUuid: string) =>
        [...courseKeys.all, 'moduleContents', moduleUuid] as const,
    // Progress / enrollment
    progress: (courseUuid: string) =>
        [...courseKeys.all, 'progress', courseUuid] as const,
    enrollments: () => [...courseKeys.all, 'enrollments'] as const,
    courseEnrollments: (courseUuid: string) =>
        [...courseKeys.all, 'courseEnrollments', courseUuid] as const,
    // Submissions
    mySubmissions: () => [...courseKeys.all, 'mySubmissions'] as const,
    submissions: (courseUuid: string) =>
        [...courseKeys.all, 'submissions', courseUuid] as const,
    assignments: (courseUuid: string, moduleUuid: string) =>
        [...courseKeys.all, 'assignments', courseUuid, moduleUuid] as const,
    // Announcements / sessions / staff
    announcements: (courseUuid: string) =>
        [...courseKeys.all, 'announcements', courseUuid] as const,
    sessions: (courseUuid: string) =>
        [...courseKeys.all, 'sessions', courseUuid] as const,
    staff: (courseUuid: string) =>
        [...courseKeys.all, 'staff', courseUuid] as const,
    attendanceStats: (courseUuid: string) =>
        [...courseKeys.all, 'attendanceStats', courseUuid] as const,
} as const;
