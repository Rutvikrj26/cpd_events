import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            staleTime: 1000 * 60 * 5, // 5 minutes
            gcTime: 1000 * 60 * 30, // 30 minutes (formerly cacheTime)
            retry: 1,
            refetchOnWindowFocus: true,
        },
        mutations: {
            retry: 0,
        },
    },
});

// Query keys for consistency
export const queryKeys = {
    events: {
        all: ['events'] as const,
        list: () => [...queryKeys.events.all, 'list'] as const,
        detail: (uuid: string) => [...queryKeys.events.all, 'detail', uuid] as const,
        public: () => [...queryKeys.events.all, 'public'] as const,
    },
    registrations: {
        all: ['registrations'] as const,
        list: () => [...queryKeys.registrations.all, 'list'] as const,
        forEvent: (eventUuid: string) => [...queryKeys.registrations.all, 'event', eventUuid] as const,
    },
    certificates: {
        all: ['certificates'] as const,
        list: () => [...queryKeys.certificates.all, 'list'] as const,
    },
    user: {
        profile: ['user', 'profile'] as const,
    },
} as const;
