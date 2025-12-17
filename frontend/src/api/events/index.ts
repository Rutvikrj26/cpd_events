import client from '../client';
import { Event, EventCreateRequest, EventUpdateRequest, EventSession, EventCustomField } from './types';

// -- Organizer / Admin Routes --

export const getEvents = async (): Promise<Event[]> => {
    const response = await client.get<Event[]>('/events/');
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
    const response = await client.get<EventSession[]>(`/events/${eventUuid}/sessions/`);
    return response.data;
};

export const createEventSession = async (eventUuid: string, data: Partial<EventSession>): Promise<EventSession> => {
    const response = await client.post<EventSession>(`/events/${eventUuid}/sessions/`, data);
    return response.data;
};

// -- Nested: Custom Fields --

export const getEventCustomFields = async (eventUuid: string): Promise<EventCustomField[]> => {
    const response = await client.get<EventCustomField[]>(`/events/${eventUuid}/custom-fields/`);
    return response.data;
};

// -- Public Routes --

export const getPublicEvents = async (): Promise<Event[]> => {
    const response = await client.get<Event[]>('/public/events/');
    return response.data;
};

export const getPublicEvent = async (slug: string): Promise<Event> => {
    const response = await client.get<Event>(`/public/events/${slug}/`);
    return response.data;
};
