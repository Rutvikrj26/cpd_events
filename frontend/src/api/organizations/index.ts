/**
 * Organizations API functions.
 */
import client from '../client';
import type { Course } from '../courses/types';
import type { Event } from '../events/types';
import type {
    Organization,
    OrganizationListItem,
    OrganizationCreateRequest,
    OrganizationUpdateRequest,
    OrganizationMember,
    InviteMemberRequest,
    UpdateMemberRequest,
    LinkableDataSummary,
    CreateOrgFromAccountRequest,
    LinkOrganizerRequest,
    LinkResult,
} from './types';

const BASE_URL = '/organizations';

// ============================================================================
// Organization CRUD
// ============================================================================

/**
 * List all organizations the current user belongs to.
 */
export const getOrganizations = async (): Promise<OrganizationListItem[]> => {
    const response = await client.get<any>(`${BASE_URL}/`);
    return Array.isArray(response.data) ? response.data : response.data.results || [];
};

/**
 * Get organization details by UUID.
 */
export const getOrganization = async (uuid: string): Promise<Organization> => {
    const response = await client.get<Organization>(`${BASE_URL}/${uuid}/`);
    return response.data;
};

/**
 * Get organization details by slug.
 */
export const getOrganizationBySlug = async (slug: string): Promise<Organization> => {
    // The backend uses UUID, so we need to list and find
    const orgs = await getOrganizations();
    const org = orgs.find(o => o.slug === slug);
    if (!org) {
        throw new Error('Organization not found');
    }
    return getOrganization(org.uuid);
};

/**
 * Create a new organization.
 */
export const createOrganization = async (data: OrganizationCreateRequest): Promise<Organization> => {
    const response = await client.post<Organization>(`${BASE_URL}/`, data);
    return response.data;
};

/**
 * Update an organization.
 */
export const updateOrganization = async (uuid: string, data: OrganizationUpdateRequest): Promise<Organization> => {
    const response = await client.patch<Organization>(`${BASE_URL}/${uuid}/`, data);
    return response.data;
};

/**
 * Delete an organization (soft delete).
 */
export const deleteOrganization = async (uuid: string): Promise<void> => {
    await client.delete(`${BASE_URL}/${uuid}/`);
};

// ============================================================================
// Organization Oversight
// ============================================================================

/**
 * List all events for an organization (admin oversight).
 */
export const getOrganizationEvents = async (orgUuid: string): Promise<Event[]> => {
    const response = await client.get<any>(`${BASE_URL}/${orgUuid}/events/`);
    return Array.isArray(response.data) ? response.data : response.data.results || [];
};

/**
 * List all courses for an organization (admin oversight).
 */
export const getOrganizationCoursesOverview = async (orgUuid: string): Promise<Course[]> => {
    const response = await client.get<any>(`${BASE_URL}/${orgUuid}/courses/`);
    return Array.isArray(response.data) ? response.data : response.data.results || [];
};

// ============================================================================
// Member Management
// ============================================================================

/**
 * List members of an organization.
 */
export const getOrganizationMembers = async (orgUuid: string): Promise<OrganizationMember[]> => {
    const response = await client.get<OrganizationMember[]>(`${BASE_URL}/${orgUuid}/members/`);
    return response.data;
};

/**
 * Invite a new member to the organization.
 */
export const inviteMember = async (orgUuid: string, data: InviteMemberRequest): Promise<{ detail: string; invitation_token: string }> => {
    const response = await client.post<any>(`${BASE_URL}/${orgUuid}/members/invite/`, data);
    return response.data;
};
/**
 * Lookup a user by email before inviting.
 */
export const lookupUser = async (orgUuid: string, email: string): Promise<{ found: boolean; user?: { email: string; full_name: string } }> => {
    const response = await client.get<any>(`${BASE_URL}/${orgUuid}/members/lookup/`, {
        params: { email },
    });
    return response.data;
};

export const updateMember = async (orgUuid: string, memberUuid: string, data: UpdateMemberRequest): Promise<OrganizationMember> => {
    const response = await client.patch<OrganizationMember>(`${BASE_URL}/${orgUuid}/members/${memberUuid}/`, data);
    return response.data;
};

/**
 * Remove a member from the organization.
 */
export const removeMember = async (orgUuid: string, memberUuid: string): Promise<void> => {
    await client.delete(`${BASE_URL}/${orgUuid}/members/${memberUuid}/remove/`);
};

/**
 * Get invitation details before accepting.
 */
export interface InvitationDetails {
    organization: {
        uuid: string;
        name: string;
        slug: string;
        logo_url: string;
    };
    role: string;
    role_display: string;
    billing_payer?: 'organization' | 'organizer' | null;
    requires_subscription?: boolean;
    invited_by: string;
    invited_by_email: string | null;
    invitation_email: string;
}

export const getInvitationDetails = async (token: string): Promise<InvitationDetails> => {
    const response = await client.get<InvitationDetails>(`${BASE_URL}/accept-invite/${token}/`);
    return response.data;
};

/**
 * Accept an organization invitation.
 */
export const acceptInvitation = async (token: string): Promise<{ detail: string; organization: OrganizationListItem }> => {
    const response = await client.post<any>(`${BASE_URL}/accept-invite/${token}/`);
    return response.data;
};

/**
 * Pending invitation details.
 */
export interface PendingInvitation {
    token: string;
    organization: {
        uuid: string;
        name: string;
        slug: string;
        logo_url: string;
    };
    role: string;
    role_display: string;
    invited_by: string;
    invited_at: string | null;
}

/**
 * Get current user's pending organization invitations.
 */
export const getMyInvitations = async (): Promise<PendingInvitation[]> => {
    const response = await client.get<PendingInvitation[]>(`${BASE_URL}/my-invitations/`);
    return response.data;
};

// ============================================================================
// Linking (Individual Organizer → Organization)
// ============================================================================

/**
 * Preview what data would be linked from current user's account.
 */
export const getLinkableDataPreview = async (): Promise<LinkableDataSummary> => {
    const response = await client.get<LinkableDataSummary>(`${BASE_URL}/create-from-account/`);
    return response.data;
};

/**
 * Create a new organization from the current user's organizer account.
 * Transfers existing events and templates.
 */
export const createOrgFromAccount = async (data?: CreateOrgFromAccountRequest): Promise<Organization> => {
    const response = await client.post<Organization>(`${BASE_URL}/create-from-account/`, data || {});
    return response.data;
};

/**
 * Link an organizer's data to an existing organization.
 */
export const linkOrganizerToOrg = async (orgUuid: string, data?: LinkOrganizerRequest): Promise<LinkResult> => {
    const response = await client.post<LinkResult>(`${BASE_URL}/${orgUuid}/link-organizer/`, data || {});
    return response.data;
};

// ============================================================================
// Stripe Connect
// ============================================================================

import { StripeConnectResponse, StripeStatusResponse } from './types';

/**
 * Initiate Stripe Connect onboarding.
 */
export const connectStripe = async (orgUuid: string): Promise<StripeConnectResponse> => {
    const response = await client.post<StripeConnectResponse>(`${BASE_URL}/${orgUuid}/stripe/connect/`);
    return response.data;
};

/**
 * Get Stripe Connect account status.
 */
export const getStripeStatus = async (orgUuid: string): Promise<StripeStatusResponse> => {
    const response = await client.get<StripeStatusResponse>(`${BASE_URL}/${orgUuid}/stripe/status/`);
    return response.data;
};

// ============================================================================
// Invitation Management
// ============================================================================

/**
 * Accept an organization invitation
 */
export const acceptOrganizationInvitation = async (token: string): Promise<{ detail: string; organization: OrganizationListItem }> => {
    const response = await client.post<{ detail: string; organization: OrganizationListItem }>(`${BASE_URL}/accept-invite/${token}/`);
    return response.data;
};

// ============================================================================
// Public Organization Profiles
// ============================================================================

/**
 * Get public organization profile by slug (no authentication required).
 */
export const getPublicOrganizationProfile = async (slug: string): Promise<Organization> => {
    const response = await client.get<Organization>(`${BASE_URL}/public/${slug}/`);
    return response.data;
};

/**
 * List public organizations (directory).
 */
export const getPublicOrganizations = async (query?: string): Promise<Organization[]> => {
    const response = await client.get<Organization[]>(`${BASE_URL}/public/`, {
        params: query ? { q: query } : undefined,
    });
    return response.data;
};

// ============================================================================
// Billing & Plans
// ============================================================================

/**
 * Get available organization plans.
 */
export const getOrganizationPlans = async (): Promise<Record<string, any>> => {
    const response = await client.get<Record<string, any>>(`${BASE_URL}/plans/`);
    return response.data;
};

/**
 * Upgrade organization subscription.
 */
export const upgradeOrganizationSubscription = async (uuid: string, plan: string): Promise<{ url: string }> => {
    const response = await client.post<{ url: string }>(`${BASE_URL}/${uuid}/subscription/upgrade/`, { plan });
    return response.data;
};

/**
 * Confirm organization subscription checkout.
 */
export const confirmOrganizationSubscription = async (uuid: string, sessionId: string): Promise<{ status: string }> => {
    const response = await client.post<{ status: string }>(`${BASE_URL}/${uuid}/subscription/confirm/`, { session_id: sessionId });
    return response.data;
};

/**
 * Create Stripe customer portal session for organization.
 */
export const createOrganizationPortalSession = async (uuid: string): Promise<{ url: string }> => {
    const response = await client.post<{ url: string }>(`${BASE_URL}/${uuid}/portal/`, {
        return_url: window.location.href,
    });
    return response.data;
};

/**
 * Add seats to organization subscription.
 */
export const addOrganizationSeats = async (uuid: string, seats: number): Promise<{ detail: string; total_seats: number; additional_seats: number }> => {
    const response = await client.post<any>(`${BASE_URL}/${uuid}/subscription/add-seats/`, { seats });
    return response.data;
};

/**
 * Remove seats from organization subscription.
 */
export const removeOrganizationSeats = async (uuid: string, seats: number): Promise<{ detail: string; total_seats: number; additional_seats: number }> => {
    const response = await client.post<any>(`${BASE_URL}/${uuid}/subscription/remove-seats/`, { seats });
    return response.data;
};

// ============================================================================
// Re-export types
// ============================================================================

export type {
    Organization,
    OrganizationListItem,
    OrganizationRole,
    OrganizationPlan,
    OrganizationSubscription,
    OrganizationMember,
} from './types';
