/**
 * Cache keys for the events feature.
 *
 * Kept here (rather than the global `lib/queryClient.ts`) so events-only
 * invalidations don't leak into other features' cache scopes.
 */
export const eventKeys = {
    all: ['events'] as const,
    list: (params: object = {}) => [...eventKeys.all, 'list', params] as const,
    publicList: (params: object = {}) =>
        [...eventKeys.all, 'publicList', params] as const,
    detail: (uuid: string) => [...eventKeys.all, 'detail', uuid] as const,
    sessions: (uuid: string) => [...eventKeys.all, 'sessions', uuid] as const,
    attendees: (uuid: string) => [...eventKeys.all, 'attendees', uuid] as const,
    registrations: () => [...eventKeys.all, 'registrations'] as const,
    myRegistrations: () => [...eventKeys.all, 'myRegistrations'] as const,
    feedback: (uuid: string) => [...eventKeys.all, 'feedback', uuid] as const,
} as const;
