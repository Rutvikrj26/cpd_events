/**
 * Learning-invitation API client.
 *
 * Three families:
 *   - target-scoped (POST .../invite/, GET .../invitations/) for hosts.
 *   - row-scoped (POST /invitations/<uuid>/{resend,cancel}/) for hosts.
 *   - public (GET/POST /public/invitations/<uuid>/) for invitees.
 *
 * The public functions accept a `signedToken` parameter (the `?t=` value)
 * and pass it as a query param. The frontend reads `?t=` from the URL on
 * the AcceptInvitePage and forwards it through.
 */

import client from '../client';
import type {
    AcceptInvitationResponse,
    InviteCreatePayload,
    InviteCreateResponse,
    LearningInvitation,
    PublicInvitation,
} from './types';

// -----------------------------------------------------------------------
// Host-scoped (auth required)
// -----------------------------------------------------------------------

export const inviteToEvent = async (
    eventUuid: string,
    payload: InviteCreatePayload,
): Promise<InviteCreateResponse> => {
    const response = await client.post<InviteCreateResponse>(
        `/events/${eventUuid}/invite/`,
        payload,
    );
    return response.data;
};

export const inviteToCourse = async (
    courseUuid: string,
    payload: InviteCreatePayload,
): Promise<InviteCreateResponse> => {
    const response = await client.post<InviteCreateResponse>(
        `/courses/${courseUuid}/invite/`,
        payload,
    );
    return response.data;
};

export const listEventInvitations = async (
    eventUuid: string,
    statusFilter?: string,
): Promise<LearningInvitation[]> => {
    const response = await client.get<LearningInvitation[]>(
        `/events/${eventUuid}/invitations/`,
        { params: statusFilter ? { status: statusFilter } : undefined },
    );
    return response.data;
};

export const listCourseInvitations = async (
    courseUuid: string,
    statusFilter?: string,
): Promise<LearningInvitation[]> => {
    const response = await client.get<LearningInvitation[]>(
        `/courses/${courseUuid}/invitations/`,
        { params: statusFilter ? { status: statusFilter } : undefined },
    );
    return response.data;
};

export const resendInvitation = async (
    invitationUuid: string,
): Promise<{ sent: boolean; send_count: number }> => {
    const response = await client.post(`/invitations/${invitationUuid}/resend/`);
    return response.data;
};

export const cancelInvitation = async (
    invitationUuid: string,
): Promise<{ cancelled: boolean }> => {
    const response = await client.post(`/invitations/${invitationUuid}/cancel/`);
    return response.data;
};

// -----------------------------------------------------------------------
// Public (invitee-facing). The `?t=` token is the signed payload — never
// pass an unsigned uuid alone.
// -----------------------------------------------------------------------

export const getPublicInvitation = async (
    invitationUuid: string,
    signedToken: string,
): Promise<PublicInvitation> => {
    const response = await client.get<PublicInvitation>(
        `/public/invitations/${invitationUuid}/`,
        { params: { t: signedToken } },
    );
    return response.data;
};

export const acceptInvitation = async (
    invitationUuid: string,
    signedToken: string,
): Promise<AcceptInvitationResponse> => {
    const response = await client.post<AcceptInvitationResponse>(
        `/public/invitations/${invitationUuid}/accept/`,
        {},
        { params: { t: signedToken } },
    );
    return response.data;
};
