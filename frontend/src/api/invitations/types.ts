/**
 * Learning-invitation types — shared between event and course invite flows.
 *
 * Mirrors the shape returned by `accounts/serializers.py` (LearningInvitationSerializer
 * + PublicInvitationSerializer). Keep these in sync when adding fields.
 */

export type InvitationTargetType = 'event' | 'course';
export type InvitationStatus = 'pending' | 'accepted' | 'expired' | 'cancelled';

export interface LearningInvitation {
    uuid: string;
    target_type: InvitationTargetType;
    target_uuid: string | null;
    target_title: string | null;
    email: string;
    full_name: string;
    contact_uuid: string | null;
    personal_message: string;
    comp: boolean;
    status: InvitationStatus;
    send_count: number;
    last_sent_at: string | null;
    expires_at: string;
    accepted_at: string | null;
    created_at: string;
    invited_by_name: string;
}

/** One row in the bulk-invite request body. Either `contact_uuid` OR `email`. */
export interface InviteeInput {
    contact_uuid?: string;
    email?: string;
    full_name?: string;
}

export interface InviteCreatePayload {
    invitees: InviteeInput[];
    personal_message?: string;
    /** Only meaningful when target is paid. Defaults false on the backend. */
    comp?: boolean;
}

export interface InviteCreateResponse {
    invitations: LearningInvitation[];
    created: Array<{ email: string; invitation_uuid: string }>;
    refreshed: Array<{ email: string; invitation_uuid: string }>;
    skipped: Array<{ email: string; reason: string; detail: string }>;
}

/** Public invite — fewer fields, exposed by `/public/invitations/:uuid/`. */
export interface PublicInvitation {
    uuid: string;
    target_type: InvitationTargetType;
    target_uuid: string;
    target_title: string;
    target_slug: string | null;
    target_is_paid: boolean;
    email: string;
    full_name: string;
    personal_message: string;
    comp: boolean;
    status: InvitationStatus;
    expired: boolean;
    expires_at: string;
    invited_by_name: string;
}

export interface AcceptInvitationResponse {
    redirect_url: string;
    target_type: InvitationTargetType;
    target_uuid: string;
    already_accepted?: boolean;
}

export interface AcceptRequiresSignupResponse {
    requires_signup: true;
    prefill_email: string;
    invitation_uuid: string;
}

export interface AcceptWrongEmailResponse {
    wrong_email: true;
    invitee_email: string;
    current_email: string;
}
