/**
 * TypeScript types for Organizations API.
 */

// ============================================================================
// Organization Types
// ============================================================================

export type OrganizationRole = 'owner' | 'admin' | 'manager' | 'member';

export type OrganizationPlan = 'free' | 'team' | 'business' | 'enterprise';

export type SubscriptionStatus = 'active' | 'trialing' | 'past_due' | 'canceled' | 'unpaid';

export interface OrganizationSubscription {
    plan: OrganizationPlan;
    plan_display: string;
    status: SubscriptionStatus;
    status_display: string;
    included_seats: number;
    additional_seats: number;
    total_seats: number;
    active_organizer_seats: number;
    available_seats: number;
    seat_price_cents: number;
    events_created_this_period: number;
    courses_created_this_period: number;
    current_period_start: string | null;
    current_period_end: string | null;
    trial_ends_at: string | null;
}

export interface OrganizationListItem {
    uuid: string;
    name: string;
    slug: string;
    logo_url: string;
    is_active: boolean;
    is_verified: boolean;
    members_count: number;
    events_count: number;
    user_role: OrganizationRole | null;
}

export interface Organization {
    uuid: string;
    name: string;
    slug: string;
    description: string;
    logo_url: string;
    website: string;
    primary_color: string;
    secondary_color: string;
    contact_email: string;
    contact_phone: string;
    is_active: boolean;
    is_verified: boolean;
    members_count: number;
    events_count: number;
    courses_count: number;
    user_role: OrganizationRole | null;
    subscription: OrganizationSubscription | null;
    created_by_name: string;
    created_at: string;
    updated_at: string;
    stripe_connect_id?: string;
    stripe_account_status?: string;
    stripe_charges_enabled?: boolean;
}

export interface OrganizationCreateRequest {
    name: string;
    description?: string;
    logo_url?: string;
    website?: string;
    primary_color?: string;
    contact_email?: string;
}

export interface OrganizationUpdateRequest {
    name?: string;
    description?: string;
    logo_url?: string;
    website?: string;
    primary_color?: string;
    secondary_color?: string;
    contact_email?: string;
    contact_phone?: string;
}

// ============================================================================
// Membership Types
// ============================================================================

export interface OrganizationMember {
    uuid: string;
    user_uuid: string;
    user_email: string;
    user_name: string;
    role: OrganizationRole;
    title: string;
    is_active: boolean;
    accepted_at: string | null;
    linked_from_individual: boolean;
    invited_by_name: string | null;
    created_at: string;
}

export interface InviteMemberRequest {
    email: string;
    role: OrganizationRole;
    title?: string;
}

export interface UpdateMemberRequest {
    role?: OrganizationRole;
    title?: string;
}

// ============================================================================
// Linking Types
// ============================================================================

export interface LinkableDataSummary {
    events_count: number;
    templates_count: number;
    has_linkable_data: boolean;
}

export interface CreateOrgFromAccountRequest {
    name?: string;
    slug?: string;
    transfer_data?: boolean;
}

export interface LinkOrganizerRequest {
    organizer_email?: string;
    role?: OrganizationRole;
    transfer_data?: boolean;
}

export interface LinkResult {
    detail: string;
    events_transferred: number;
    templates_transferred: number;
}

// ============================================================================
// Stripe Connect Types
// ============================================================================

export interface StripeConnectResponse {
    url: string;
}

export interface StripeStatusResponse {
    details_submitted: boolean;
    charges_enabled: boolean;
    payouts_enabled: boolean;
    default_currency: string;
    requirements: {
        currently_due: string[];
        past_due: string[];
        eventually_due: string[];
    };
}
