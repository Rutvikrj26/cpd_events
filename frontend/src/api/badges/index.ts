import client from '../client';
import { BadgeTemplate, IssuedBadge } from './types';

// Templates
export const getBadgeTemplates = async () => {
    const response = await client.get<BadgeTemplate[]>('/api/v1/badges/templates/');
    return response.data;
};

export const createBadgeTemplate = async (data: Partial<BadgeTemplate>) => {
    const response = await client.post<BadgeTemplate>('/api/v1/badges/templates/', data);
    return response.data;
};

export const updateBadgeTemplate = async (uuid: string, data: Partial<BadgeTemplate>) => {
    const response = await client.patch<BadgeTemplate>(`/api/v1/badges/templates/${uuid}/`, data);
    return response.data;
};

export const deleteBadgeTemplate = async (uuid: string) => {
    await client.delete(`/api/v1/badges/templates/${uuid}/`);
};

export const uploadBadgeTemplateImage = async (uuid: string, file: File) => {
    const formData = new FormData();
    formData.append('start_image', file);
    const response = await client.patch<BadgeTemplate>(`/api/v1/badges/templates/${uuid}/`, formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
    });
    return response.data;
};

// Issued Badges
export const getMyBadges = async () => {
    const response = await client.get<IssuedBadge[]>('/api/v1/badges/issued/');
    return response.data;
};

export const getBadgeByCode = async (code: string) => {
    const response = await client.get<IssuedBadge>(`/api/v1/badges/issued/public/?code=${code}`);
    return response.data;
};

export const getIssuedBadgesByMe = async () => {
    const response = await client.get<IssuedBadge[]>('/api/v1/badges/issued/?issued_by_me=true');
    return response.data;
};
