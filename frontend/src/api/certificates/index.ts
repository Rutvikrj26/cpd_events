import client from '../client';
import { Certificate, CertificateTemplate } from './types';

// Templates (Admin/Organizer)
export const getCertificateTemplates = async (): Promise<CertificateTemplate[]> => {
    const response = await client.get<CertificateTemplate[]>('/certificate-templates/');
    return response.data;
};

// Public Verification
export const verifyCertificate = async (code: string): Promise<Certificate> => {
    const response = await client.get<Certificate>(`/public/certificates/verify/${code}/`);
    return response.data;
};
