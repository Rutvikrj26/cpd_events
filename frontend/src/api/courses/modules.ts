import client from '../client';
import { CourseModule, CourseCreateRequest } from './types';

// We reuse existing types but might need generic Module types if not already exported
// Assuming types define CourseModule structure.

export interface CreateModuleRequest {
    title: string;
    description?: string;
    order?: number;
    course_uuid: string;
}

export interface UpdateModuleRequest {
    title?: string;
    description?: string;
    order?: number;
    is_published?: boolean;
}

export const getCourseModules = async (courseUuid: string): Promise<CourseModule[]> => {
    const response = await client.get<any>(`/courses/${courseUuid}/modules/`);
    return Array.isArray(response.data) ? response.data : response.data.results;
};

export const createCourseModule = async (courseUuid: string, data: Partial<CreateModuleRequest>): Promise<CourseModule> => {
    const response = await client.post<CourseModule>(`/courses/${courseUuid}/modules/`, {
        ...data,
        course_uuid: courseUuid,
    });
    return response.data;
};

export const updateCourseModule = async (courseUuid: string, moduleUuid: string, data: UpdateModuleRequest): Promise<CourseModule> => {
    // Note: The backend uses a custom 'update_content' action or standard patch?
    // We implemented 'update_content' action for content updates, but standard patch might work for order/linking?
    // Let's use the standard endpoint first, or the specific action if needed.
    // Based on views.py: patch -> update_content action for content, or standard for link?
    // The viewset was a bit mixed. Let's try standard patch first for now.
    // Wait, views.py shows `update_content` action for PATCH.
    const response = await client.patch<CourseModule>(`/courses/${courseUuid}/modules/${moduleUuid}/`, data);
    return response.data;
};

export const deleteCourseModule = async (courseUuid: string, moduleUuid: string): Promise<void> => {
    await client.delete(`/courses/${courseUuid}/modules/${moduleUuid}/`);
};

// Content Management
// We can reuse the existing Learning/Module endpoints if regular EventModule permissions allow it, 
// OR use the new nested routes we just created.

export const createModuleContent = async (courseUuid: string, moduleUuid: string, data: any): Promise<any> => {
    const isFormData = data instanceof FormData;
    const config = isFormData ? { headers: { 'Content-Type': 'multipart/form-data' } } : {};
    const response = await client.post(`/courses/${courseUuid}/modules/${moduleUuid}/contents/`, data, config);
    return response.data;
};

export const getModuleContents = async (courseUuid: string, moduleUuid: string): Promise<any[]> => {
    const response = await client.get(`/courses/${courseUuid}/modules/${moduleUuid}/contents/`);
    return Array.isArray(response.data) ? response.data : response.data.results;
};

export const updateModuleContent = async (courseUuid: string, moduleUuid: string, contentUuid: string, data: any): Promise<any> => {
    const isFormData = data instanceof FormData;
    const config = isFormData ? { headers: { 'Content-Type': 'multipart/form-data' } } : {};
    const response = await client.patch(`/courses/${courseUuid}/modules/${moduleUuid}/contents/${contentUuid}/`, data, config);
    return response.data;
};
