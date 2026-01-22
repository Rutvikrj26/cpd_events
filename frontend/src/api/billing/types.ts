export interface Subscription {
    uuid: string;
    plan: 'attendee' | 'organizer' | 'lms' | 'pro';
    plan_display: string;
    status: 'active' | 'trialing' | 'canceled' | 'past_due' | 'unpaid' | 'incomplete' | 'paused';
    status_display: string;
    is_active: boolean;
    is_trialing: boolean;
    is_trial_expired: boolean;
    is_in_grace_period: boolean;
    is_access_blocked: boolean;
    can_create_events: boolean;
    can_create_courses: boolean;
    days_until_trial_ends: number | null;
    subscription_status_display: string;
    limits: {
        events_per_month: number | null;
        courses_per_month: number | null;
        certificates_per_month: number | null;
        max_attendees_per_event: number | null;
    };
    billing_interval: 'month' | 'year';
    pending_plan?: 'attendee' | 'organizer' | 'lms' | 'pro' | null;
    pending_billing_interval?: 'month' | 'year' | null;
    pending_change_at?: string | null;
    current_period_start: string | null;
    current_period_end: string | null;
    trial_ends_at: string | null;
    cancel_at_period_end: boolean;
    canceled_at: string | null;
    events_created_this_period: number;
    courses_created_this_period: number;
    certificates_issued_this_period: number;
    stripe_subscription_id?: string | null;
    stripe_customer_id?: string | null;
    has_payment_method?: boolean;
    created_at: string;
    updated_at: string;
}

export interface Invoice {
    uuid: string;
    amount_due: number;
    amount_display?: string;
    status: 'paid' | 'open' | 'void' | 'draft' | 'uncollectible';
    pdf_url?: string;
    invoice_pdf_url?: string;
    period_start?: string;
    period_end?: string;
    created_at?: string;
}

export interface PaymentMethod {
    uuid: string;
    card_brand: string;
    card_last4: string;
    card_exp_month: number;
    card_exp_year: number;
    is_default: boolean;
    is_expired: boolean;
    card_display: string;
    billing_name: string;
    billing_email: string;
    created_at: string;
}

// ============================================================================
// Public Pricing API Types (from backend)
// ============================================================================

export interface PricingPrice {
    uuid: string;
    amount_cents: number;
    amount_display: string;
    currency: string;
    billing_interval: 'month' | 'year';
}

export interface PricingProduct {
    uuid: string;
    name: string;
    description: string;
    plan: string;
    plan_display: string;
    trial_days: number;
    show_contact_sales: boolean;
    features: string[];
    feature_limits: {
        events_per_month: number | null;
        courses_per_month: number | null;
        certificates_per_month: number | null;
        max_attendees_per_event: number | null;
    };
    prices: PricingPrice[];
}
