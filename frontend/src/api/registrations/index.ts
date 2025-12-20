import client from '../client';
import { Registration, RegistrationCreateRequest, LinkRegistrationRequest } from './types';

// My Registrations (Attendee)
export const getMyRegistrations = async (): Promise<Registration[]> => {
    // registrations/urls.py is mounted at /api/v1/registrations/
    const response = await client.get<any>('/registrations/');
    return Array.isArray(response.data) ? response.data : response.data.results;
};

export const getMyRegistration = async (uuid: string): Promise<Registration> => {
    const response = await client.get<Registration>(`/registrations/${uuid}/`);
    return response.data;
};

// Link Registrations
export const linkRegistrations = async (data: LinkRegistrationRequest): Promise<void> => {
    await client.post('/users/me/link-registrations/', data);
};

// Public Registration
export const registerForEvent = async (eventUuid: string, data: RegistrationCreateRequest): Promise<Registration> => {
    // path('public/events/<uuid:event_uuid>/register/', ...)
    const response = await client.post<Registration>(`/public/events/${eventUuid}/register/`, data);
    return response.data;
};
