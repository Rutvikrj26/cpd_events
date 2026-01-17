import client from '../client';
import { BadgeTemplate, IssuedBadge } from './types';
import { PaginatedResponse } from '../types';

// Re-export types
export type { BadgeTemplate, IssuedBadge };

// Templates
export const getBadgeTemplates = async (): Promise<PaginatedResponse<BadgeTemplate>> => {
    const response = await client.get<PaginatedResponse<BadgeTemplate>>('/badges/templates/');
    return response.data;
};

export const createBadgeTemplate = async (data: FormData | Partial<BadgeTemplate>) => {
    const isFormData = data instanceof FormData;
    const response = await client.post<BadgeTemplate>('/badges/templates/', data, {
        headers: isFormData ? { 'Content-Type': 'multipart/form-data' } : {},
    });
    return response.data;
};

export const updateBadgeTemplate = async (uuid: string, data: Partial<BadgeTemplate>) => {
    const response = await client.patch<BadgeTemplate>(`/badges/templates/${uuid}/`, data);
    return response.data;
};

export const deleteBadgeTemplate = async (uuid: string) => {
    await client.delete(`/badges/templates/${uuid}/`);
};

export const uploadBadgeTemplateImage = async (uuid: string, file: File) => {
    const formData = new FormData();
    formData.append('start_image', file);
    const response = await client.patch<BadgeTemplate>(`/badges/templates/${uuid}/`, formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
    });
    return response.data;
};

// Issued Badges
export const getMyBadges = async (): Promise<PaginatedResponse<IssuedBadge>> => {
    const response = await client.get<PaginatedResponse<IssuedBadge>>('/badges/issued/');
    return response.data;
};

export const getBadgeByCode = async (code: string) => {
    const response = await client.get<IssuedBadge>(`/badges/issued/public/?code=${code}`);
    return response.data;
};

export const getIssuedBadgesByMe = async (): Promise<PaginatedResponse<IssuedBadge>> => {
    const response = await client.get<PaginatedResponse<IssuedBadge>>('/badges/issued/?issued_by_me=true');
    return response.data;
};
