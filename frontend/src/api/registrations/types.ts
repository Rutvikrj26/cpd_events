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
    duration_minutes?: number;
    actual_end_at?: string | null;
    /** True iff at least one *published* VideoRecording exists. Visible
     *  to all viewers; drives the public-facing recording state. */
    has_published_recording?: boolean;
    /** Number of published recordings — drives the "1 of N" picker. */
    published_recordings_count?: number;
    /** True iff the **current user** can watch any recording for this
     *  event right now. Equals `has_published_recording` for learners,
     *  but also true for hosts/admins when only unpublished recordings
     *  exist (so they can preview before publishing). Drives the My
     *  Learning "Watch Recording" button visibility. */
    has_recording?: boolean;
}

export interface Registration {
    uuid: string;
    event: MinimalEvent;
    status: 'pending' | 'confirmed' | 'waitlisted' | 'cancelled';
    payment_status: 'pending' | 'paid' | 'failed' | 'refunded' | 'na';
    amount_paid?: number;
    tax_amount?: number;
    total_amount?: number;
    stripe_checkout_session_id?: string;
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
}

/**
 * Response from public registration endpoint.
 * Paid events include ``checkout_url`` — the frontend redirects there.
 */
export interface RegistrationResponse extends Registration {
    registration_uuid?: string;
    requires_payment?: boolean;
    checkout_url?: string;
    checkout_session_id?: string;
    amount?: number;
    ticket_price?: number;
    currency?: string;
    message?: string;
}

export interface StartCheckoutResponse {
    registration_uuid: string;
    session_id: string;
    url: string;
    status: string;
    amount_paid: number;
    currency: string;
}
