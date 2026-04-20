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
