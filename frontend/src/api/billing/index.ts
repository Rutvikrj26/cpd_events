import client from '../client';
import { InstitutionPlan, Subscription, SubscriptionEnvelope } from './types';

/**
 * GET /api/v1/billing/my-subscription/
 *
 * Returns either the user's Subscription row or an envelope with a null
 * subscription + the institution's pricing_model. Callers should tolerate
 * both shapes.
 */
export const getSubscription = async (): Promise<Subscription | null> => {
    const response = await client.get<Subscription | SubscriptionEnvelope>('/billing/my-subscription/');
    const data = response.data as SubscriptionEnvelope & Partial<Subscription>;
    if (data && 'subscription' in data) {
        return (data as SubscriptionEnvelope).subscription;
    }
    return (data as Subscription) ?? null;
};

/**
 * GET /api/v1/public/pricing/
 *
 * Public, unauthenticated. Returns active InstitutionPlan rows for the
 * pricing page. DRF pagination is enabled globally, so this endpoint returns
 * a `{ results: InstitutionPlan[] }` envelope.
 */
export const getPublicPricing = async (): Promise<InstitutionPlan[]> => {
    const response = await client.get<InstitutionPlan[] | { results: InstitutionPlan[] }>(
        '/public/pricing/'
    );
    const data = response.data;
    if (Array.isArray(data)) return data;
    return data?.results ?? [];
};

/**
 * POST /api/v1/billing/subscribe/
 *
 * Returns a Stripe Checkout Session URL for subscribing to a plan.
 * Frontend should redirect to the returned ``url``.
 */
export const startSubscriptionCheckout = async (
    planUuid: string,
): Promise<{ session_id: string; url: string }> => {
    const response = await client.post<{ session_id: string; url: string }>(
        '/billing/subscribe/',
        { plan_uuid: planUuid },
    );
    return response.data;
};

/**
 * POST /api/v1/billing/portal/
 *
 * Returns a Stripe Customer Portal URL for self-serve billing management
 * (cancel, resume, update card, view invoices, switch plans). Frontend
 * should redirect to the returned ``url``.
 */
export const openCustomerPortal = async (returnUrl?: string): Promise<{ url: string }> => {
    const response = await client.post<{ url: string }>('/billing/portal/', {
        return_url: returnUrl,
    });
    return response.data;
};
