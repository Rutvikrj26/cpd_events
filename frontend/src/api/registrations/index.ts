import client from '../client';
import {
    ConfirmPaymentResponse,
    Registration,
    RegistrationCreateRequest,
    RegistrationPaymentIntentRequest,
    RegistrationResponse,
} from './types';
import { PaginatedResponse, PaginationParams } from '../types';

// My Registrations (Attendee)
export const getMyRegistrations = async (params?: PaginationParams): Promise<PaginatedResponse<Registration>> => {
    const response = await client.get<PaginatedResponse<Registration>>('/registrations/', { params });
    // Handle both paginated and non-paginated responses
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

// Resume payment for a pending registration
export const getRegistrationPaymentIntent = async (
    registrationUuid: string,
    data?: RegistrationPaymentIntentRequest
): Promise<RegistrationResponse> => {
    const response = await client.post<RegistrationResponse>(
        `/public/registrations/${registrationUuid}/payment-intent/`,
        data
    );
    return response.data;
};

// Confirm payment after Stripe.js succeeds
export const confirmRegistrationPayment = async (registrationUuid: string): Promise<ConfirmPaymentResponse> => {
    const response = await client.post<ConfirmPaymentResponse>(`/public/registrations/${registrationUuid}/confirm-payment/`);
    return response.data;
};
