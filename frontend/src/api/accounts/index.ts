import client from '../client';
import {
    LoginRequest,
    SignupRequest,
    AuthResponse,
    User,
    RefreshTokenRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    UpgradeOrganizerRequest
} from './types';

// Authentication
export const signup = async (data: SignupRequest): Promise<User> => {
    const response = await client.post<User>('/auth/signup/', data);
    return response.data;
};

export const login = async (data: LoginRequest): Promise<AuthResponse> => {
    const response = await client.post<AuthResponse>('/auth/token/', data);
    return response.data;
};

export const refreshToken = async (data: RefreshTokenRequest): Promise<{ access: string }> => {
    const response = await client.post<{ access: string }>('/auth/token/refresh/', data);
    return response.data;
};

export const verifyEmail = async (token: string): Promise<void> => {
    await client.post('/auth/verify-email/', { token });
};

export const resetPassword = async (data: PasswordResetRequest): Promise<void> => {
    await client.post('/auth/password-reset/', data);
};

export const confirmPasswordReset = async (data: PasswordResetConfirm): Promise<void> => {
    await client.post('/auth/password-reset/confirm/', data);
};

// Current User
export const getCurrentUser = async (): Promise<User> => {
    const response = await client.get<User>('/users/me/');
    return response.data;
};

export const updateProfile = async (data: Partial<User>): Promise<User> => {
    const response = await client.patch<User>('/users/me/', data);
    return response.data;
};

export const upgradeToOrganizer = async (data: UpgradeOrganizerRequest): Promise<void> => {
    await client.post('/users/me/upgrade/', data);
};
