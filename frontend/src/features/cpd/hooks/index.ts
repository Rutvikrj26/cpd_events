import { useQuery } from '@tanstack/react-query';
import { getCPDProgress, getCPDRequirements } from '@/api/cpd';

export const cpdKeys = {
    all: ['cpd'] as const,
    progress: () => [...cpdKeys.all, 'progress'] as const,
    requirements: () => [...cpdKeys.all, 'requirements'] as const,
} as const;

export function useCPDProgress() {
    return useQuery({
        queryKey: cpdKeys.progress(),
        queryFn: getCPDProgress,
        staleTime: 1000 * 60,
    });
}

export function useCPDRequirements() {
    return useQuery({
        queryKey: cpdKeys.requirements(),
        queryFn: getCPDRequirements,
        staleTime: 1000 * 60 * 5,
    });
}
