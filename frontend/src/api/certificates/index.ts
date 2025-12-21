import client from '../client';
import { Certificate, CertificateTemplate, CertificateIssueRequest, CertificateSummary } from './types';

// ============================================
// My Certificates (Attendee)
// ============================================

export const getMyCertificates = async (): Promise<Certificate[]> => {
    const response = await client.get<any>('/certificates/');
    return Array.isArray(response.data) ? response.data : response.data.results;
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
    const response = await client.post<CertificateTemplate>(`/certificate-templates/${uuid}/set_default/`);
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
