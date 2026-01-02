import client from '../client';
import { Event, EventCreateRequest, EventUpdateRequest, EventSession, EventCustomField } from './types';

// -- Organizer / Admin Routes --

export const getEvents = async (): Promise<Event[]> => {
    const response = await client.get<any>('/events/');
    return Array.isArray(response.data) ? response.data : response.data.results;
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

export const getPublicEvents = async (): Promise<Event[]> => {
    const response = await client.get<any>('/public/events/');
    return Array.isArray(response.data) ? response.data : response.data.results;
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

// Event actions
export { publishEvent, unpublishEvent, cancelEvent, duplicateEvent } from './actions';
