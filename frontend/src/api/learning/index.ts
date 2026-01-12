import client from '../client';
import { Module, ModuleContent, Assignment } from './types';

// -- Student Actions --

export const getMyLearning = async (): Promise<any[]> => {
    const response = await client.get<any[]>('/learning/');
    return response.data;
};

export interface ContentProgressUpdate {
    progress_percent?: number;
    time_spent?: number;
    position?: Record<string, any>;
    completed?: boolean;
}

export const updateContentProgress = async (
    contentUuid: string,
    data: ContentProgressUpdate = { progress_percent: 100, completed: true }
): Promise<void> => {
    const payload = {
        progress_percent: data.progress_percent ?? 100,
        time_spent: data.time_spent ?? 0,
        position: data.position,
        completed: data.completed ?? data.progress_percent === 100,
    };
    await client.post(`/learning/progress/content/${contentUuid}/`, payload);
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
