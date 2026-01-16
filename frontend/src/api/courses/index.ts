import client from '../client';
import {
    Course,
    CourseCreateRequest,
    Assignment,
    AssignmentSubmission,
    AssignmentSubmissionStaff,
    CourseAnnouncement,
} from './types';
import { PaginatedResponse, PaginationParams } from '../types';

export * from './types';

// ============================================
// Organization Courses (Admin/Course Manager)
// ============================================

export const getOrganizationCourses = async (orgSlug: string): Promise<Course[]> => {
    const response = await client.get<any>('/courses/', {
        params: { org: orgSlug }
    });
    return Array.isArray(response.data) ? response.data : response.data.results || [];
};

export const getOwnedCourses = async (): Promise<Course[]> => {
    const response = await client.get<any>('/courses/', {
        params: { owned: 'true' }
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

export const getCourseBySlug = async (
    slug: string,
    filters?: { org?: string; owned?: boolean }
): Promise<Course | null> => {
    const response = await client.get<any>('/courses/', {
        params: { slug, ...filters }
    });
    const results = Array.isArray(response.data) ? response.data : response.data.results;
    return results && results.length > 0 ? results[0] : null;
};

export const enrollInCourse = async (courseUuid: string): Promise<any> => {
    const response = await client.post('/enrollments/', {
        course_uuid: courseUuid
    });
    return response.data;
};

export const getEnrollments = async (): Promise<any[]> => {
    const response = await client.get<any[]>('/enrollments/');
    return Array.isArray(response.data) ? response.data : (response.data as any).results || [];
};

export const getMySubmissions = async (): Promise<AssignmentSubmission[]> => {
    const response = await client.get<any[]>('/submissions/');
    return Array.isArray(response.data) ? response.data : (response.data as any).results || [];
};

export const createSubmission = async (
    assignmentUuid: string,
    data: { content?: Record<string, any>; file_url?: string }
): Promise<AssignmentSubmission> => {
    const response = await client.post<AssignmentSubmission>('/submissions/', {
        assignment: assignmentUuid,
        ...data,
    });
    return response.data;
};

export const updateSubmission = async (
    submissionUuid: string,
    data: { content?: Record<string, any>; file_url?: string }
): Promise<AssignmentSubmission> => {
    const response = await client.patch<AssignmentSubmission>(`/submissions/${submissionUuid}/`, data);
    return response.data;
};

export const submitSubmission = async (submissionUuid: string): Promise<AssignmentSubmission> => {
    const response = await client.post<AssignmentSubmission>(`/submissions/${submissionUuid}/submit/`);
    return response.data;
};

export interface CourseProgress {
    course_uuid: string;
    course_title: string;
    enrollment: {
        uuid: string;
        status: string;
        progress_percent: number;
        completed_at?: string;
        certificate_issued?: boolean;
    };
    modules: Array<{
        module: {
            uuid: string;
            title: string;
            description?: string;
        };
        progress: {
            status: string;
            progress_percent: number;
        };
        is_available: boolean;
        content_progress: Array<{
            content: string;
            status: string;
            progress_percent: number;
            completed_at?: string;
        }>;
    }>;
}

export const getCourseProgress = async (courseUuid: string): Promise<CourseProgress> => {
    const response = await client.get<CourseProgress>(`/courses/${courseUuid}/progress/`);
    return response.data;
};

// ============================================
// Course Payments (Stripe Checkout)
// ============================================

export interface CheckoutSessionResponse {
    success: boolean;
    session_id: string;
    url: string;
    error?: string;
}

/**
 * Initiates a Stripe Checkout session for a paid course.
 * Returns a session_id and URL to redirect the user to Stripe.
 */
export const courseCheckout = async (
    courseUuid: string,
    successUrl: string,
    cancelUrl: string
): Promise<CheckoutSessionResponse> => {
    const response = await client.post<CheckoutSessionResponse>(`/courses/${courseUuid}/checkout/`, {
        success_url: successUrl,
        cancel_url: cancelUrl,
    });
    return response.data;
};

// ============================================
// Course Assignments
// ============================================

export const getCourseAssignments = async (courseUuid: string, moduleUuid: string): Promise<Assignment[]> => {
    const response = await client.get<any>(`/courses/${courseUuid}/modules/${moduleUuid}/assignments/`);
    return Array.isArray(response.data) ? response.data : response.data.results || [];
};

export const createCourseAssignment = async (
    courseUuid: string,
    moduleUuid: string,
    data: Partial<Assignment>
): Promise<Assignment> => {
    const response = await client.post<Assignment>(`/courses/${courseUuid}/modules/${moduleUuid}/assignments/`, data);
    return response.data;
};

export const updateCourseAssignment = async (
    courseUuid: string,
    moduleUuid: string,
    assignmentUuid: string,
    data: Partial<Assignment>
): Promise<Assignment> => {
    const response = await client.patch<Assignment>(
        `/courses/${courseUuid}/modules/${moduleUuid}/assignments/${assignmentUuid}/`,
        data
    );
    return response.data;
};

export const deleteCourseAssignment = async (
    courseUuid: string,
    moduleUuid: string,
    assignmentUuid: string
): Promise<void> => {
    await client.delete(`/courses/${courseUuid}/modules/${moduleUuid}/assignments/${assignmentUuid}/`);
};

// ============================================
// Course Announcements
// ============================================

export const getCourseAnnouncements = async (courseUuid: string): Promise<CourseAnnouncement[]> => {
    const response = await client.get<any>(`/courses/${courseUuid}/announcements/`);
    return Array.isArray(response.data) ? response.data : response.data.results || [];
};

export const createCourseAnnouncement = async (
    courseUuid: string,
    data: Pick<CourseAnnouncement, 'title' | 'body' | 'is_published'>
): Promise<CourseAnnouncement> => {
    const response = await client.post<CourseAnnouncement>(`/courses/${courseUuid}/announcements/`, data);
    return response.data;
};

export const updateCourseAnnouncement = async (
    courseUuid: string,
    announcementUuid: string,
    data: Partial<Pick<CourseAnnouncement, 'title' | 'body' | 'is_published'>>
): Promise<CourseAnnouncement> => {
    const response = await client.patch<CourseAnnouncement>(
        `/courses/${courseUuid}/announcements/${announcementUuid}/`,
        data
    );
    return response.data;
};

export const deleteCourseAnnouncement = async (courseUuid: string, announcementUuid: string): Promise<void> => {
    await client.delete(`/courses/${courseUuid}/announcements/${announcementUuid}/`);
};

// ============================================
// Course Submissions (Staff)
// ============================================

export const getCourseSubmissions = async (courseUuid: string): Promise<AssignmentSubmissionStaff[]> => {
    const response = await client.get<any>(`/courses/${courseUuid}/submissions/`);
    return Array.isArray(response.data) ? response.data : response.data.results || [];
};

export const gradeCourseSubmission = async (
    courseUuid: string,
    submissionUuid: string,
    data: { score?: number; feedback?: string; action: 'grade' | 'return' | 'approve' }
): Promise<AssignmentSubmissionStaff> => {
    const response = await client.post<AssignmentSubmissionStaff>(
        `/courses/${courseUuid}/submissions/${submissionUuid}/grade/`,
        data
    );
    return response.data;
};

// ============================================
// Public Courses (Browse/Catalog)
// ============================================

export interface PublicCourseListParams extends PaginationParams {
    search?: string;
    org?: string;
}

export const getPublicCourses = async (params?: PublicCourseListParams): Promise<PaginatedResponse<Course>> => {
    const response = await client.get<PaginatedResponse<Course>>('/courses/', { params });
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
