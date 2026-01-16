import client from '../client';

/**
 * Get Google OAuth authorization URL
 */
export const getGoogleAuthUrl = async (): Promise<{ url: string }> => {
    const response = await client.get<{ url: string }>('/auth/google/login/');
    return response.data;
};

/**
 * Initiate Google Sign-In flow
 * Redirects user to Google OAuth consent screen
 */
export const initiateGoogleSignIn = async (): Promise<void> => {
    const { url } = await getGoogleAuthUrl();
    window.location.href = url;
};
