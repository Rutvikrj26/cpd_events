export interface MinimalEvent {
    uuid: string;
    title: string;
    slug: string;
    starts_at: string;
    status: string;
    event_type?: string;
    cpd_credit_value: number;
    cpd_credit_type: string;
    price?: number;
    currency?: string;
    is_free?: boolean;
}

export interface Registration {
    uuid: string;
    event: MinimalEvent;
    status: 'pending' | 'confirmed' | 'waitlisted' | 'cancelled';
    payment_status: 'pending' | 'paid' | 'failed' | 'refunded' | 'na';
    amount_paid?: number;
    platform_fee_amount?: number;
    total_amount?: number;
    email: string;
    full_name: string;
    attended: boolean;
    attendance_percent: number;
    attendance_eligible: boolean;
    certificate_issued: boolean;
    certificate_issued_at?: string;
    allow_public_verification: boolean;
    waitlist_position?: number;
    promoted_from_waitlist_at?: string;
    zoom_join_url?: string;
    can_join: boolean;
    certificate_url?: string;
    created_at: string;
}

export interface RegistrationCreateRequest {
    email: string;
    full_name: string;
    professional_title?: string;
    organization_name?: string;
    custom_field_responses?: Record<string, any>;
    allow_public_verification?: boolean;
    promo_code?: string;
}

/**
 * Response from public registration endpoint.
 * For paid events, includes client_secret for Stripe payment.
 */
export interface RegistrationResponse extends Registration {
    registration_uuid?: string;
    client_secret?: string;
    amount?: number;
    currency?: string;
    requires_payment?: boolean;
    ticket_price?: number;
    platform_fee?: number;
    stripe_account_id?: string;
    // Promo code info
    promo_code?: string;
    original_price?: string;
    discount_amount?: string;
    final_price?: string;
}

export interface ConfirmPaymentResponse {
    status: 'paid' | 'processing' | 'failed' | 'event_full' | 'error';
    registration_uuid?: string;
    amount_paid?: number;
    message?: string;
}
