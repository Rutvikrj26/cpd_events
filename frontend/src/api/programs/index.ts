import client from '../client';
import type {
    Program,
    ProgramCourseAddRequest,
    ProgramCourseEntry,
    ProgramCreateRequest,
    ProgramEnrollment,
    ProgramListItem,
} from './types';

export * from './types';

const unwrap = <T>(data: any): T[] => {
    if (Array.isArray(data)) return data;
    return data?.results ?? [];
};

// ---- Listing & detail ----

export const getPrograms = async (params?: { owned?: boolean; search?: string }): Promise<ProgramListItem[]> => {
    const response = await client.get<any>('/programs/', { params });
    return unwrap<ProgramListItem>(response.data);
};

export const getPublicPrograms = async (search?: string): Promise<ProgramListItem[]> => {
    const response = await client.get<any>('/programs/', { params: search ? { search } : undefined });
    return unwrap<ProgramListItem>(response.data);
};

export const getProgram = async (uuid: string): Promise<Program> => {
    const response = await client.get<Program>(`/programs/${uuid}/`);
    return response.data;
};

export const getProgramBySlug = async (slug: string, owned = false): Promise<Program | null> => {
    const response = await client.get<any>('/programs/', {
        params: { slug, ...(owned ? { owned: 'true' } : {}) },
    });
    const items = unwrap<ProgramListItem>(response.data);
    if (items.length === 0) return null;
    const detail = await client.get<Program>(`/programs/${items[0].uuid}/`);
    return detail.data;
};

// ---- CRUD ----

export const createProgram = async (data: ProgramCreateRequest): Promise<Program> => {
    const response = await client.post<Program>('/programs/', data);
    return response.data;
};

export const updateProgram = async (uuid: string, data: Partial<ProgramCreateRequest>): Promise<Program> => {
    const response = await client.patch<Program>(`/programs/${uuid}/`, data);
    return response.data;
};

export const deleteProgram = async (uuid: string): Promise<void> => {
    await client.delete(`/programs/${uuid}/`);
};

export const publishProgram = async (uuid: string): Promise<Program> => {
    const response = await client.post<Program>(`/programs/${uuid}/publish/`);
    return response.data;
};

// ---- Member-course management ----

export const addProgramCourse = async (
    programUuid: string,
    payload: ProgramCourseAddRequest,
): Promise<ProgramCourseEntry> => {
    const response = await client.post<ProgramCourseEntry>(
        `/programs/${programUuid}/courses/`,
        payload,
    );
    return response.data;
};

export const updateProgramCourse = async (
    programUuid: string,
    entryUuid: string,
    payload: Partial<Pick<ProgramCourseAddRequest, 'order' | 'is_required'>>,
): Promise<ProgramCourseEntry> => {
    const response = await client.patch<ProgramCourseEntry>(
        `/programs/${programUuid}/courses/${entryUuid}/`,
        payload,
    );
    return response.data;
};

export const removeProgramCourse = async (programUuid: string, entryUuid: string): Promise<void> => {
    await client.delete(`/programs/${programUuid}/courses/${entryUuid}/`);
};

// ---- Enrollment ----

export const getMyProgramEnrollments = async (): Promise<ProgramEnrollment[]> => {
    const response = await client.get<any>('/program-enrollments/');
    return unwrap<ProgramEnrollment>(response.data);
};

export interface ProgramCheckoutResponse {
    success: boolean;
    session_id?: string;
    url?: string;
    error?: string;
}

export const programCheckout = async (
    programUuid: string,
    successUrl: string,
    cancelUrl: string,
): Promise<ProgramCheckoutResponse> => {
    const response = await client.post<ProgramCheckoutResponse>(
        `/programs/${programUuid}/checkout/`,
        { success_url: successUrl, cancel_url: cancelUrl },
    );
    return response.data;
};

/** One-click enroll for price-zero programs — no Stripe. */
export const programEnrollFree = async (programUuid: string): Promise<ProgramEnrollment> => {
    const response = await client.post<ProgramEnrollment>(`/programs/${programUuid}/enroll/`);
    return response.data;
};

/** Archive a program: hides it from discovery and blocks new enrollments.
 *  Existing learners keep access. */
export const archiveProgram = async (programUuid: string): Promise<Program> => {
    const response = await client.post<Program>(`/programs/${programUuid}/archive/`);
    return response.data;
};

/** Create or refresh the Stripe Product + Price for this program. */
export const syncProgramToStripe = async (programUuid: string): Promise<Program> => {
    const response = await client.post<Program>(`/programs/${programUuid}/sync-stripe/`);
    return response.data;
};

export interface ProgramAnalyticsResponse {
    summary: {
        total_enrollments: number;
        completions: number;
        completion_rate: number | null;
        gross_revenue_cents: number;
        refunds_cents: number;
        net_revenue_cents: number;
        purchase_count: number;
        refund_count: number;
    };
    trends: Array<{ date: string | null; count: number }>;
    status_breakdown: Array<{ label: string; count: number }>;
    recent_transactions: Array<{
        purchase_uuid: string;
        user_name: string;
        amount_cents: number;
        currency: string;
        status: string;
        created_at: string | null;
    }>;
}

export const getProgramAnalytics = async (
    programUuid: string,
    period: string = 'last-30-days',
): Promise<ProgramAnalyticsResponse> => {
    const response = await client.get<ProgramAnalyticsResponse>(
        `/programs/${programUuid}/analytics/`,
        { params: { period } },
    );
    return response.data;
};

export interface ProgramAnnouncement {
    uuid: string;
    title: string;
    body: string;
    is_published: boolean;
    created_at: string;
    created_by?: { full_name?: string; email?: string } | null;
}

export const listProgramAnnouncements = async (programUuid: string): Promise<ProgramAnnouncement[]> => {
    const response = await client.get<any>(`/programs/${programUuid}/announcements/`);
    const data = response.data;
    return Array.isArray(data) ? data : (data?.results ?? []);
};

export const createProgramAnnouncement = async (
    programUuid: string,
    payload: { title: string; body: string; is_published?: boolean },
): Promise<ProgramAnnouncement> => {
    const response = await client.post<ProgramAnnouncement>(
        `/programs/${programUuid}/announcements/`,
        payload,
    );
    return response.data;
};

export const deleteProgramAnnouncement = async (
    programUuid: string,
    announcementUuid: string,
): Promise<void> => {
    await client.delete(`/programs/${programUuid}/announcements/${announcementUuid}/`);
};

export interface ProgramDiscussionDigest {
    threads: Array<{
        uuid: string;
        title: string;
        reply_count: number;
        last_activity_at: string;
        author?: { full_name?: string; email?: string } | null;
        course?: { uuid: string; title: string; slug: string } | null;
    }>;
    member_course_count: number;
}

export const getProgramDiscussion = async (programUuid: string): Promise<ProgramDiscussionDigest> => {
    const response = await client.get<ProgramDiscussionDigest>(`/programs/${programUuid}/discussion/`);
    return response.data;
};

/** Staff roster for a program with per-learner payment info. */
export const getProgramEnrollmentsRoster = async (programUuid: string): Promise<any[]> => {
    const response = await client.get<any[]>(`/programs/${programUuid}/enrollments/`);
    return response.data;
};

// Program refunds moved to the unified billing endpoint:
//   import { refundPurchase } from '@/api/billing';
//   await refundPurchase(purchase_uuid, { reason, amount_cents? });
// The roster endpoint exposes purchase_uuid per row.
