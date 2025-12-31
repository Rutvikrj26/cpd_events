import client from '../client';

export interface PayoutsStatus {
    connected: boolean;
    status: 'not_connected' | 'pending' | 'pending_verification' | 'restricted' | 'active';
    charges_enabled: boolean;
    stripe_id?: string;
    details?: {
        charges_enabled: boolean;
        details_submitted: boolean;
        payouts_enabled: boolean;
        requirements?: object;
    };
}

export interface PayoutsConnectResponse {
    url: string;
}

/**
 * Initiate Stripe Connect onboarding for the current user.
 * Returns a Stripe hosted onboarding URL.
 */
export const initiatePayoutsConnect = async (): Promise<PayoutsConnectResponse> => {
    const response = await client.post<PayoutsConnectResponse>('/users/me/payouts/connect/');
    return response.data;
};

/**
 * Get the current user's Stripe Connect payouts status.
 */
export const getPayoutsStatus = async (): Promise<PayoutsStatus> => {
    const response = await client.get<PayoutsStatus>('/users/me/payouts/status/');
    return response.data;
};
