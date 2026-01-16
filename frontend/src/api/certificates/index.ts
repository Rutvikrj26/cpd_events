import client from '../client';
export * from './types';
import { Certificate, CertificateTemplate, CertificateIssueRequest, CertificateSummary } from './types';
import { PaginatedResponse, PaginationParams } from '../types';

// ============================================
// My Certificates (Attendee)
// ============================================

export const getMyCertificates = async (params?: PaginationParams): Promise<PaginatedResponse<Certificate>> => {
    const response = await client.get<PaginatedResponse<Certificate>>('/certificates/', { params });
    // Handle both paginated and non-paginated responses
    if (Array.isArray(response.data)) {
        return {
            count: response.data.length,
            page: 1,
            page_size: response.data.length,
            total_pages: 1,
            next: null,
            previous: null,
            results: response.data,
        };
    }
    return response.data;
};

export const getMyCertificate = async (uuid: string): Promise<Certificate> => {
    const response = await client.get<Certificate>(`/certificates/${uuid}/`);
    return response.data;
};

export const downloadCertificate = async (uuid: string): Promise<{ download_url: string }> => {
    const response = await client.post<{ download_url: string }>(`/certificates/${uuid}/download/`);
    return response.data;
};

// ============================================
// Certificate Templates (Organizer)
// ============================================

export const getCertificateTemplates = async (): Promise<CertificateTemplate[]> => {
    const response = await client.get<any>('/certificate-templates/');
    return Array.isArray(response.data) ? response.data : response.data.results || [];
};

export interface AvailableTemplatesResponse {
    own_count: number;
    shared_count: number;
    templates: CertificateTemplate[];
}

export const getAvailableCertificateTemplates = async (): Promise<AvailableTemplatesResponse> => {
    const response = await client.get<AvailableTemplatesResponse>('/certificate-templates/available/');
    return response.data;
};

export const getCertificateTemplate = async (uuid: string): Promise<CertificateTemplate> => {
    const response = await client.get<CertificateTemplate>(`/certificate-templates/${uuid}/`);
    return response.data;
};

export const createCertificateTemplate = async (data: Partial<CertificateTemplate>): Promise<CertificateTemplate> => {
    const response = await client.post<CertificateTemplate>('/certificate-templates/', data);
    return response.data;
};

export const updateCertificateTemplate = async (uuid: string, data: Partial<CertificateTemplate>): Promise<CertificateTemplate> => {
    const response = await client.patch<CertificateTemplate>(`/certificate-templates/${uuid}/`, data);
    return response.data;
};

export const deleteCertificateTemplate = async (uuid: string): Promise<void> => {
    await client.delete(`/certificate-templates/${uuid}/`);
};

export const setDefaultTemplate = async (uuid: string): Promise<CertificateTemplate> => {
    const response = await client.post<CertificateTemplate>(`/certificate-templates/${uuid}/set-default/`);
    return response.data;
};

export const uploadTemplateFile = async (uuid: string, file: File): Promise<{ file_url: string; file_size: number }> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await client.post<{ file_url: string; file_size: number }>(
        `/certificate-templates/${uuid}/upload/`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return response.data;
};

export interface FieldPosition {
    x: number;
    y: number;
    fontSize: number;
    fontFamily?: string;
}

export interface FieldPositions {
    first_name?: FieldPosition;
    last_name?: FieldPosition;
    cpd_hours?: FieldPosition;
    [key: string]: FieldPosition | undefined;
}

export const generateTemplatePreview = async (uuid: string, fieldPositions: FieldPositions): Promise<{ preview_url: string }> => {
    const response = await client.post<{ preview_url: string }>(
        `/certificate-templates/${uuid}/preview/`,
        { field_positions: fieldPositions }
    );
    return response.data;
};

export const saveFieldPositions = async (uuid: string, fieldPositions: FieldPositions): Promise<CertificateTemplate> => {
    const response = await client.patch<CertificateTemplate>(`/certificate-templates/${uuid}/`, {
        field_positions: fieldPositions
    });
    return response.data;
};

// ============================================
// Event Certificates (Organizer)
// ============================================

export const getEventCertificates = async (eventUuid: string): Promise<Certificate[]> => {
    const response = await client.get<any>(`/events/${eventUuid}/certificates/`);
    return Array.isArray(response.data) ? response.data : response.data.results || [];
};

export const issueCertificates = async (eventUuid: string, data: CertificateIssueRequest): Promise<{ issued: number; skipped: number }> => {
    const response = await client.post<{ issued: number; skipped: number }>(`/events/${eventUuid}/certificates/issue/`, data);
    return response.data;
};

export const revokeCertificate = async (eventUuid: string, certUuid: string, reason: string): Promise<Certificate> => {
    const response = await client.post<Certificate>(`/events/${eventUuid}/certificates/${certUuid}/revoke/`, { reason });
    return response.data;
};

export const getCertificateSummary = async (eventUuid: string): Promise<CertificateSummary> => {
    const response = await client.get<CertificateSummary>(`/events/${eventUuid}/certificates/summary/`);
    return response.data;
};

// ============================================
// Public Verification
// ============================================

export const verifyCertificate = async (code: string): Promise<Certificate> => {
    const response = await client.get<Certificate>(`/public/certificates/verify/${code}/`);
    return response.data;
};
