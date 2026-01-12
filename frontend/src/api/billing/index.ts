import client from '../client';
import { Subscription, Invoice, PaymentMethod, PricingProduct } from './types';

export const getSubscription = async (): Promise<Subscription> => {
    const response = await client.get('/subscription/');
    // Handle paginated response, list, or single object
    const data = response.data;
    if (Array.isArray(data)) {
        return data[0] || null;
    }
    if (data.results && Array.isArray(data.results)) {
        return data.results[0] || null;
    }
    return data;
};

export const getInvoices = async (): Promise<Invoice[]> => {
    const response = await client.get('/invoices/');
    // Handle both paginated response and direct array
    const data = response.data;
    return Array.isArray(data) ? data : (data.results || []);
};

interface CheckoutResponse {
    session_id: string;
    url: string;
}

export const createCheckoutSession = async (
    plan: string,
    successUrl: string,
    cancelUrl: string,
    billingInterval: 'month' | 'year' = 'month'
): Promise<CheckoutResponse> => {
    const response = await client.post<CheckoutResponse>('/billing/checkout/', {
        plan,
        success_url: successUrl,
        cancel_url: cancelUrl,
        billing_interval: billingInterval,
    });
    return response.data;
};

export const getBillingPortal = async (returnUrl?: string): Promise<{ url: string }> => {
    const response = await client.post<{ url: string }>('/billing/portal/', {
        return_url: returnUrl || window.location.href,
    });
    return response.data;
};

export const cancelSubscription = async (immediate: boolean = false, reason?: string): Promise<Subscription> => {
    const response = await client.post<Subscription>('/subscription/cancel/', {
        immediate,
        reason,
    });
    return response.data;
};

export const reactivateSubscription = async (): Promise<Subscription> => {
    const response = await client.post<Subscription>('/subscription/reactivate/');
    return response.data;
};

export const updateSubscription = async (
    plan: string,
    immediate: boolean = true,
    billingInterval: 'month' | 'year' = 'month'
): Promise<Subscription> => {
    const response = await client.put<Subscription>('/subscription/', {
        plan,
        immediate,
        billing_interval: billingInterval,
    });
    return response.data;
};

export const syncSubscription = async (): Promise<Subscription> => {
    const response = await client.post<Subscription>('/subscription/sync/');
    return response.data;
};

/**
 * Confirm checkout session completion.
 * Called after returning from Stripe Checkout.
 * Atomically syncs subscription from Stripe.
 */
export const confirmCheckout = async (sessionId: string): Promise<Subscription> => {
    const response = await client.post<Subscription>('/subscription/confirm-checkout/', {
        session_id: sessionId,
    });
    return response.data;
};

// Payment Method APIs (view/delete only - adding handled by Stripe Portal)
export const getPaymentMethods = async (): Promise<PaymentMethod[]> => {
    const response = await client.get('/payment-methods/');
    const data = response.data;
    return Array.isArray(data) ? data : (data.results || []);
};

export const deletePaymentMethod = async (uuid: string): Promise<void> => {
    await client.delete(`/payment-methods/${uuid}/`);
};

export const setDefaultPaymentMethod = async (uuid: string): Promise<PaymentMethod> => {
    const response = await client.post<PaymentMethod>(`/payment-methods/${uuid}/set-default/`);
    return response.data;
};

// ============================================================================
// Public Pricing API (no authentication required)
// ============================================================================

/**
 * Fetch current pricing from backend (configured in Django Admin).
 * This is a public endpoint - no authentication required.
 * Returns all active pricing products with their prices.
 */
export const getPublicPricing = async (): Promise<PricingProduct[]> => {
    const response = await client.get<PricingProduct[]>('/public/pricing/');
    return response.data;
};
