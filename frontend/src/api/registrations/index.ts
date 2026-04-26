import client from '../client';
import {
    Registration,
    RegistrationCreateRequest,
    RegistrationResponse,
    StartCheckoutResponse,
} from './types';
import { PaginatedResponse, PaginationParams } from '../types';

// My Registrations (Attendee)
export const getMyRegistrations = async (params?: PaginationParams): Promise<PaginatedResponse<Registration>> => {
    const response = await client.get<PaginatedResponse<Registration>>('/registrations/', { params });
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

export const getMyRegistration = async (uuid: string): Promise<Registration> => {
    const response = await client.get<Registration>(`/registrations/${uuid}/`);
    return response.data;
};

// Link guest registrations to the current user's account.
export const linkRegistrations = async (): Promise<{ linked_count: number; message: string }> => {
    const response = await client.post<{ linked_count: number; message: string }>('/registrations/users/me/link-registrations/');
    return response.data;
};

// Public Registration — paid events come back with ``checkout_url``.
export const registerForEvent = async (
    eventUuid: string,
    data: RegistrationCreateRequest,
): Promise<RegistrationResponse> => {
    const response = await client.post<RegistrationResponse>(`/public/events/${eventUuid}/register/`, data);
    return response.data;
};

// Resume a PENDING paid registration — returns a fresh Stripe Checkout URL.
export const startRegistrationCheckout = async (registrationUuid: string): Promise<StartCheckoutResponse> => {
    const response = await client.post<StartCheckoutResponse>(
        `/public/registrations/${registrationUuid}/start-checkout/`,
    );
    return response.data;
};
