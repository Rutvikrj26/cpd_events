import { useQuery } from '@tanstack/react-query';
import {
    getMyCertificates,
    getMyCertificate,
    downloadCertificate,
} from '@/api/certificates';
import type { Certificate } from '@/api/certificates/types';

export const certificateKeys = {
    all: ['certificates'] as const,
    myList: () => [...certificateKeys.all, 'mine'] as const,
    detail: (uuid: string) => [...certificateKeys.all, 'detail', uuid] as const,
    downloadUrl: (uuid: string) => [...certificateKeys.all, 'downloadUrl', uuid] as const,
} as const;

export function useMyCertificates() {
    return useQuery({
        queryKey: certificateKeys.myList(),
        queryFn: async () => (await getMyCertificates()).results as Certificate[],
        staleTime: 1000 * 60,
    });
}

export function useCertificate(uuid: string | undefined) {
    return useQuery({
        queryKey: uuid ? certificateKeys.detail(uuid) : ['certificates', 'detail', 'noop'],
        queryFn: () => getMyCertificate(uuid!),
        enabled: Boolean(uuid),
    });
}

export function useCertificateDownloadUrl(uuid: string | undefined) {
    return useQuery({
        queryKey: uuid ? certificateKeys.downloadUrl(uuid) : ['certificates', 'download', 'noop'],
        queryFn: () => downloadCertificate(uuid!),
        enabled: false, // fire on demand only
    });
}
