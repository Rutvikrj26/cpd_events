import client from '../client';
import { Registration, RegistrationCreateRequest, RegistrationResponse } from './types';

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

// Link Registrations - Links guest registrations to the current user's account
export const linkRegistrations = async (): Promise<{ linked_count: number; message: string }> => {
    const response = await client.post<{ linked_count: number; message: string }>('/registrations/users/me/link-registrations/');
    return response.data;
};

// Public Registration
// Returns RegistrationResponse which may include client_secret for paid events
export const registerForEvent = async (eventUuid: string, data: RegistrationCreateRequest): Promise<RegistrationResponse> => {
    // path('public/events/<uuid:event_uuid>/register/', ...)
    const response = await client.post<RegistrationResponse>(`/public/events/${eventUuid}/register/`, data);
    return response.data;
};
