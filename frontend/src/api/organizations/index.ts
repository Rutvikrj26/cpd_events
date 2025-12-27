/**
 * Organizations API functions.
 */
import client from '../client';
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
 * Update a member's role or title.
 */
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
 * Accept an organization invitation.
 */
export const acceptInvitation = async (token: string): Promise<{ detail: string; organization: OrganizationListItem }> => {
    const response = await client.post<any>(`${BASE_URL}/accept-invite/${token}/`);
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
