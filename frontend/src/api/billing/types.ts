/**
 * Types matching the trimmed single-tenant billing backend.
 *
 * The frontend used to model a full SaaS subscription (plan strings, trial,
 * pending changes, per-period usage counters). That surface is gone — the
 * backend now exposes a simple institutional plan + per-user subscription
 * status. See ~/.claude/plans/lets-trace-through-the-calm-flute.md.
 */

export type SubscriptionStatus =
    | 'active'
    | 'canceled'
    | 'past_due'
    | 'unpaid'
    | 'incomplete'
    | 'paused';

export interface Subscription {
    uuid: string;
    plan_name: string | null;
    status: SubscriptionStatus;
    current_period_start: string | null;
    current_period_end: string | null;
    cancel_at_period_end: boolean;
    created_at: string;
}

export interface SubscriptionEnvelope {
    subscription: Subscription | null;
    pricing_model?: 'free' | 'per_item' | 'subscription' | 'hybrid';
}

/** Shape returned by GET /api/v1/public/pricing/ — InstitutionPlan rows. */
export interface InstitutionPlan {
    uuid: string;
    name: string;
    description: string;
    price_cents: number;
    price_display: string;
    billing_interval: 'month' | 'year';
    includes_all_courses: boolean;
    max_enrollments: number | null;
    is_active: boolean;
    is_featured: boolean;
    sort_order: number;
    features_list: string[];
    created_at: string;
    updated_at: string;
}
