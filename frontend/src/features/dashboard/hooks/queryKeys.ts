export const dashboardKeys = {
    all: ['dashboard'] as const,
    attendee: () => [...dashboardKeys.all, 'attendee'] as const,
    instructor: () => [...dashboardKeys.all, 'instructor'] as const,
    organizer: () => [...dashboardKeys.all, 'organizer'] as const,
} as const;
