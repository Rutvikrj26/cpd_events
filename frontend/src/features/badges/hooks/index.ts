import { useQuery } from '@tanstack/react-query';
import { getMyBadges, getBadgeByCode, getBadgeTemplates } from '@/api/badges';
import type { IssuedBadge, BadgeTemplate } from '@/api/badges/types';

export const badgeKeys = {
    all: ['badges'] as const,
    myList: () => [...badgeKeys.all, 'mine'] as const,
    publicByCode: (code: string) => [...badgeKeys.all, 'publicByCode', code] as const,
    templates: () => [...badgeKeys.all, 'templates'] as const,
} as const;

export function useMyBadges() {
    return useQuery({
        queryKey: badgeKeys.myList(),
        queryFn: async () => (await getMyBadges()).results as IssuedBadge[],
        staleTime: 1000 * 60,
    });
}

export function useBadgeByCode(code: string | undefined) {
    return useQuery({
        queryKey: code ? badgeKeys.publicByCode(code) : ['badges', 'publicByCode', 'noop'],
        queryFn: () => getBadgeByCode(code!),
        enabled: Boolean(code),
    });
}

export function useBadgeTemplates() {
    return useQuery({
        queryKey: badgeKeys.templates(),
        queryFn: async () => (await getBadgeTemplates()).results as BadgeTemplate[],
        staleTime: 1000 * 60 * 5,
    });
}
