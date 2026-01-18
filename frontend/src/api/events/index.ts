import client from '../client';
import { Event, EventCreateRequest, EventUpdateRequest, EventSession, EventCustomField } from './types';
import { PaginatedResponse, PaginationParams } from '../types';

// -- Organizer / Admin Routes --

export interface EventListParams extends PaginationParams {
    status?: string;
    search?: string;
}

export const getEvents = async (params?: EventListParams): Promise<PaginatedResponse<Event>> => {
    const response = await client.get<PaginatedResponse<Event>>('/events/', { params });
    // Handle both paginated and non-paginated responses for backwards compatibility
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

export const getEvent = async (uuid: string): Promise<Event> => {
    const response = await client.get<Event>(`/events/${uuid}/`);
    return response.data;
};

export const createEvent = async (data: EventCreateRequest): Promise<Event> => {
    const response = await client.post<Event>('/events/', data);
    return response.data;
};

export const updateEvent = async (uuid: string, data: EventUpdateRequest): Promise<Event> => {
    const response = await client.patch<Event>(`/events/${uuid}/`, data);
    return response.data;
};

export const deleteEvent = async (uuid: string): Promise<void> => {
    await client.delete(`/events/${uuid}/`);
};

// -- Nested: Sessions --

export const getEventSessions = async (eventUuid: string): Promise<EventSession[]> => {
    const response = await client.get<any>(`/events/${eventUuid}/sessions/`);
    return Array.isArray(response.data) ? response.data : response.data.results;
};

export const createEventSession = async (eventUuid: string, data: Partial<EventSession>): Promise<EventSession> => {
    const response = await client.post<EventSession>(`/events/${eventUuid}/sessions/`, data);
    return response.data;
};

export const updateEventSession = async (eventUuid: string, sessionUuid: string, data: Partial<EventSession>): Promise<EventSession> => {
    const response = await client.patch<EventSession>(`/events/${eventUuid}/sessions/${sessionUuid}/`, data);
    return response.data;
};

export const deleteEventSession = async (eventUuid: string, sessionUuid: string): Promise<void> => {
    await client.delete(`/events/${eventUuid}/sessions/${sessionUuid}/`);
};

// -- Nested: Custom Fields --

export const getEventCustomFields = async (eventUuid: string): Promise<EventCustomField[]> => {
    const response = await client.get<EventCustomField[]>(`/events/${eventUuid}/custom-fields/`);
    return response.data;
};

// -- Public Routes --

export interface PublicEventListParams extends PaginationParams {
    search?: string;
    event_type?: string;
    format?: string;
    is_free?: boolean;
}

export const getPublicEvents = async (params?: PublicEventListParams): Promise<PaginatedResponse<Event>> => {
    const response = await client.get<PaginatedResponse<Event>>('/public/events/', { params });
    // Handle both paginated and non-paginated responses for backwards compatibility
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

export const getPublicEvent = async (slug: string): Promise<Event> => {
    const response = await client.get<Event>(`/public/events/${slug}/`);
    return response.data;
};

// Get registrations for an event (organizer)
export const getEventRegistrations = async (eventUuid: string): Promise<any[]> => {
    const response = await client.get<any>(`/events/${eventUuid}/registrations/`);
    return Array.isArray(response.data) ? response.data : response.data.results || [];
};

export const checkInAttendee = async (eventUuid: string, registrationUuid: string, attended: boolean): Promise<any> => {
    const response = await client.patch<any>(`/events/${eventUuid}/registrations/${registrationUuid}/`, { attended });
    return response.data;
};

export const overrideAttendance = async (eventUuid: string, registrationUuid: string, eligible: boolean, reason: string): Promise<any> => {
    const response = await client.post<any>(`/events/${eventUuid}/registrations/${registrationUuid}/override-attendance/`, { eligible, reason });
    return response.data;
};

export const cancelEventRegistration = async (eventUuid: string, registrationUuid: string, reason?: string): Promise<any> => {
    const response = await client.post<any>(`/events/${eventUuid}/registrations/${registrationUuid}/cancel/`, { reason });
    return response.data;
};

export const refundEventRegistration = async (eventUuid: string, registrationUuid: string, reason?: string): Promise<any> => {
    const response = await client.post<any>(`/events/${eventUuid}/registrations/${registrationUuid}/refund/`, { reason });
    return response.data;
};

// Upload event featured image
export const uploadEventImage = async (eventUuid: string, imageFile: File): Promise<Event> => {
    const formData = new FormData();
    formData.append('image', imageFile);

    const response = await client.post<Event>(`/events/${eventUuid}/upload-image/`, formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
    });
    return response.data;
};

export const deleteEventImage = async (eventUuid: string): Promise<Event> => {
    const response = await client.delete<Event>(`/events/${eventUuid}/upload-image/`);
    return response.data;
};


// -- Attendance Reconciliation --

export interface UnmatchedParticipant {
    user_id: string;
    user_name: string;
    user_email: string;
    join_time: string;
    leave_time?: string;
    duration_minutes: number;
}

export const getUnmatchedParticipants = async (eventUuid: string): Promise<UnmatchedParticipant[]> => {
    const response = await client.get<UnmatchedParticipant[]>(`/events/${eventUuid}/unmatched_participants/`);
    return Array.isArray(response.data) ? response.data : [];
};

export const syncEventAttendance = async (eventUuid: string): Promise<{ task_id: string, status: string }> => {
    const response = await client.post<{ task_id: string, status: string }>(`/events/${eventUuid}/sync_attendance/`);
    return response.data;
};

export const matchParticipant = async (eventUuid: string, data: {
    registration_uuid: string;
    zoom_user_email?: string;
    zoom_user_name?: string;
    zoom_join_time?: string;
    attendance_minutes?: number;
}): Promise<void> => {
    await client.post(`/events/${eventUuid}/match_participant/`, data);
};

// Event actions
export { publishEvent, unpublishEvent, cancelEvent, duplicateEvent } from './actions';
