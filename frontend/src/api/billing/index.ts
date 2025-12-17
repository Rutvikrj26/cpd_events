import client from '../client';
import { Subscription, Invoice } from './types';

export const getSubscription = async (): Promise<Subscription> => {
    // Assuming list returns one or specific endpoint used. 
    // ViewSet: router.register(r'subscription', SubscriptionViewSet)
    // Maps to /api/v1/subscription/
    const response = await client.get<Subscription>('/subscription/');
    return response.data;
};

export const getInvoices = async (): Promise<Invoice[]> => {
    const response = await client.get<Invoice[]>('/invoices/');
    return response.data;
};

export const createCheckoutSession = async (priceId: string): Promise<{ url: string }> => {
    const response = await client.post<{ url: string }>('/billing/checkout/', { price_id: priceId });
    return response.data;
};

export const getBillingPortal = async (): Promise<{ url: string }> => {
    const response = await client.post<{ url: string }>('/billing/portal/');
    return response.data;
};
