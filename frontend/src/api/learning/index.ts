import client from '../client';
import { Module, ModuleContent, Assignment } from './types';

// -- Student Actions --

export const getMyLearning = async (): Promise<any[]> => {
    const response = await client.get<any[]>('/learning/');
    return response.data;
};

export const updateContentProgress = async (contentUuid: string): Promise<void> => {
    await client.post(`/learning/progress/content/${contentUuid}/`);
};

// -- Organizer Actions (Nested in Events) --
// /events/<uuid:event_uuid>/modules/

export const getEventModules = async (eventUuid: string): Promise<Module[]> => {
    const response = await client.get<Module[]>(`/events/${eventUuid}/modules/`);
    return response.data;
};

export const createEventModule = async (eventUuid: string, data: Partial<Module>): Promise<Module> => {
    const response = await client.post<Module>(`/events/${eventUuid}/modules/`, data);
    return response.data;
};

export const publishModule = async (eventUuid: string, moduleUuid: string): Promise<void> => {
    await client.post(`/events/${eventUuid}/modules/${moduleUuid}/publish/`);
};
