import client from '../client';

// =============================================================================
// Verify Session — CheckoutReturn polls this after Stripe redirects back.
// 200 = the CoursePurchase exists and is fulfilled (or refunded/etc).
// 202 = no row yet — webhook still in flight; the caller should poll again.
// =============================================================================

export type PurchaseKind = 'course' | 'program' | 'event';

export interface VerifySessionResponse {
    fulfilled: boolean;
    kind: PurchaseKind | null;
    payment_status: 'pending' | 'completed' | 'refunded' | 'failed' | 'unknown';
    amount_cents?: number;
    currency?: string;
    redirect_url?: string;
}

export const verifySession = async (sessionId: string): Promise<VerifySessionResponse> => {
    const response = await client.get<VerifySessionResponse>('/billing/verify-session/', {
        params: { session_id: sessionId },
        // 202 is expected while the webhook is in flight — don't toast it as an error.
        validateStatus: (s) => s === 200 || s === 202,
    });
    return response.data;
};

// =============================================================================
// Refund Purchase — the canonical refund endpoint.
// Replaced surface-specific actions (registration / course / program refund).
// Callers pass the CoursePurchase uuid; the backend cascades by kind.
// =============================================================================

export interface RefundPurchasePayload {
    reason: string;
    amount_cents?: number;
}

export interface RefundPurchaseResponse {
    purchase_uuid: string;
    kind: PurchaseKind;
    status: string;
    stripe_refund_id?: string;
    amount_cents?: number;
    partial: boolean;
}

export const refundPurchase = async (
    purchaseUuid: string,
    payload: RefundPurchasePayload,
): Promise<RefundPurchaseResponse> => {
    const response = await client.post<RefundPurchaseResponse>(
        `/billing/purchases/${purchaseUuid}/refund/`,
        payload,
    );
    return response.data;
};
