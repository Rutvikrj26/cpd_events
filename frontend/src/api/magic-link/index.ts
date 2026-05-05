/**
 * Magic-link API client — registration claim + email sign-in.
 *
 * Three calls back the new flow:
 *
 *   - verifyMagicLink(uuid, token)        → for the page-load lookup that
 *                                            decides whether to render the
 *                                            set-password form (CLAIM) or
 *                                            auto-login (SIGN_IN).
 *   - acceptMagicLink(uuid, token, body)  → mutation: creates/updates
 *                                            the user and returns a JWT pair.
 *   - requestSignInLink(email)            → /login feature: emails a
 *                                            sign-in link if the email matches
 *                                            a User. Always returns 202.
 */

import client from '../client';
import type {
    MagicLinkAcceptResponse,
    MagicLinkVerifyResponse,
    SignInLinkRequestResponse,
} from './types';

export const verifyMagicLink = async (
    uuid: string,
    signedToken: string,
): Promise<MagicLinkVerifyResponse> => {
    const response = await client.post<MagicLinkVerifyResponse>(
        `/public/magic-link/${uuid}/verify/`,
        {},
        { params: { t: signedToken } },
    );
    return response.data;
};

export const acceptMagicLink = async (
    uuid: string,
    signedToken: string,
    body: { password?: string } = {},
): Promise<MagicLinkAcceptResponse> => {
    const response = await client.post<MagicLinkAcceptResponse>(
        `/public/magic-link/${uuid}/accept/`,
        body,
        { params: { t: signedToken } },
    );
    return response.data;
};

export const requestSignInLink = async (email: string): Promise<SignInLinkRequestResponse> => {
    const response = await client.post<SignInLinkRequestResponse>(
        `/auth/sign-in-link/`,
        { email },
    );
    return response.data;
};

/** Lost-the-email rescue. Re-issues a CLAIM link for any pending guest
 *  registration matching the email. Anti-enumeration response. */
export const findMyRegistration = async (email: string): Promise<SignInLinkRequestResponse> => {
    const response = await client.post<SignInLinkRequestResponse>(
        `/auth/find-my-registration/`,
        { email },
    );
    return response.data;
};

export type {
    MagicLinkAcceptResponse,
    MagicLinkPurpose,
    MagicLinkRegistrationSummary,
    MagicLinkStatus,
    MagicLinkVerifyResponse,
    SignInLinkRequestResponse,
} from './types';
