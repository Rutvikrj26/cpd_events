/**
 * CPD API client
 */
import client from '../client';
import {
    CPDRequirement,
    CPDProgress,
    CPDRequirementCreate,
    CPDExportParams,
} from './types';

/**
 * List all CPD requirements for the current user.
 */
export const getCPDRequirements = async (): Promise<CPDRequirement[]> => {
    const response = await client.get<CPDRequirement[]>('/cpd-requirements/');
    return response.data;
};

/**
 * Get CPD progress summary.
 */
export const getCPDProgress = async (): Promise<CPDProgress> => {
    const response = await client.get<CPDProgress>('/cpd-requirements/progress/');
    return response.data;
};

/**
 * Get a specific CPD requirement.
 */
export const getCPDRequirement = async (uuid: string): Promise<CPDRequirement> => {
    const response = await client.get<CPDRequirement>(`/cpd-requirements/${uuid}/`);
    return response.data;
};

/**
 * Create a new CPD requirement.
 */
export const createCPDRequirement = async (data: CPDRequirementCreate): Promise<CPDRequirement> => {
    const response = await client.post<CPDRequirement>('/cpd-requirements/', data);
    return response.data;
};

/**
 * Update a CPD requirement.
 */
export const updateCPDRequirement = async (
    uuid: string,
    data: Partial<CPDRequirementCreate>
): Promise<CPDRequirement> => {
    const response = await client.patch<CPDRequirement>(`/cpd-requirements/${uuid}/`, data);
    return response.data;
};

/**
 * Delete a CPD requirement.
 */
export const deleteCPDRequirement = async (uuid: string): Promise<void> => {
    await client.delete(`/cpd-requirements/${uuid}/`);
};

/**
 * Export CPD report.
 * Returns a Blob for file download.
 */
export const exportCPDReport = async (params: CPDExportParams = {}): Promise<Blob> => {
    const response = await client.get('/cpd-requirements/export/', {
        params,
        responseType: 'blob',
    });
    return response.data;
};

/**
 * Download CPD report to user's device.
 */
export const downloadCPDReport = async (params: CPDExportParams = {}): Promise<void> => {
    const blob = await exportCPDReport(params);
    const format = params.export_format || 'json';
    const filename = `cpd_report_${new Date().toISOString().split('T')[0]}.${format}`;

    // Create download link
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
};
