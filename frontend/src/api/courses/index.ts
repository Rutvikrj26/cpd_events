import client from '../client';
import { Course, CourseCreateRequest } from './types';

export * from './types';

// ============================================
// Organization Courses (Manager)
// ============================================

export const getOrganizationCourses = async (orgSlug: string): Promise<Course[]> => {
    const response = await client.get<any>('/courses/', {
        params: { org: orgSlug }
    });
    return Array.isArray(response.data) ? response.data : response.data.results || [];
};

export const getCourse = async (uuid: string): Promise<Course> => {
    const response = await client.get<Course>(`/courses/${uuid}/`);
    return response.data;
};

export const createCourse = async (data: CourseCreateRequest): Promise<Course> => {
    const response = await client.post<Course>('/courses/', data);
    return response.data;
};

export const updateCourse = async (uuid: string, data: Partial<CourseCreateRequest>): Promise<Course> => {
    const response = await client.patch<Course>(`/courses/${uuid}/`, data);
    return response.data;
};

export const deleteCourse = async (uuid: string): Promise<void> => {
    await client.delete(`/courses/${uuid}/`);
};

export const publishCourse = async (uuid: string): Promise<Course> => {
    const response = await client.post<Course>(`/courses/${uuid}/publish/`);
    return response.data;
};

export const getCourseBySlug = async (slug: string): Promise<Course | null> => {
    const response = await client.get<any>('/courses/', {
        params: { slug }
    });
    const results = Array.isArray(response.data) ? response.data : response.data.results;
    return results && results.length > 0 ? results[0] : null;
};

export const enrollInCourse = async (courseUuid: string): Promise<any> => {
    const response = await client.post('/course-enrollments/', {
        course_uuid: courseUuid
    });
    return response.data;
};

export const getEnrollments = async (): Promise<any[]> => {
    const response = await client.get<any[]>('/enrollments/');
    return Array.isArray(response.data) ? response.data : (response.data as any).results || [];
};

// ============================================
// Public Courses (Browse/Catalog)
// ============================================

export const getPublicCourses = async (filters?: { search?: string; org?: string }): Promise<Course[]> => {
    const response = await client.get<any>('/courses/', {
        params: {
            ...filters,
        }
    });
    return Array.isArray(response.data) ? response.data : response.data.results || [];
};
