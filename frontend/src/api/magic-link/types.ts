/**
 * Magic-link types — shared between registration claim + email sign-in flows.
 *
 * Mirrors the shape returned by `accounts/views.MagicLinkVerifyView`
 * (verify) and `accounts/views.MagicLinkAcceptView` (accept). Keep these
 * in sync with the backend response shape.
 */

export type MagicLinkPurpose = 'registration_claim' | 'sign_in';
export type MagicLinkStatus = 'pending' | 'accepted' | 'expired' | 'cancelled';

export interface MagicLinkRegistrationSummary {
    uuid: string;
    status: string;
    payment_status: string;
    event_title: string;
    event_uuid: string;
    event_slug: string | null;
    event_starts_at: string | null;
    total_amount: string;
    currency: string;
}

/** Response from POST /public/magic-link/<uuid>/verify/. */
export interface MagicLinkVerifyResponse {
    status: MagicLinkStatus;
    purpose: MagicLinkPurpose;
    email: string;
    expires_at: string;
    user_exists: boolean;
    registration_summary: MagicLinkRegistrationSummary | null;
}

/** Response from POST /public/magic-link/<uuid>/accept/. */
export interface MagicLinkAcceptResponse {
    access: string;
    refresh: string;
    user: {
        uuid: string;
        email: string;
        full_name: string;
        roles: string[];
    };
    redirect_url: string;
    purpose: MagicLinkPurpose;
}

/** Response from POST /auth/sign-in-link/. */
export interface SignInLinkRequestResponse {
    message: string;
}

export type MagicLinkErrorCode =
    | 'INVALID_TOKEN'
    | 'LINK_EXPIRED'
    | 'LINK_CANCELLED'
    | 'LINK_ALREADY_ACCEPTED'
    | 'PASSWORD_TOO_SHORT'
    | 'NO_ACCOUNT'
    | 'INVALID_PURPOSE';
