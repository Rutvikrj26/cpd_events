import client from '../client';
import {
    LoginRequest,
    SignupRequest,
    AuthResponse,
    SignupResponse,
    User,
    UserSession,
    RefreshTokenRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    PasswordChangeRequest,
    NotificationPreferences
} from './types';

// Authentication
export const signup = async (data: SignupRequest): Promise<SignupResponse> => {
    const response = await client.post<SignupResponse>('/auth/signup/', data);
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

export const verifyEmail = async (token: string): Promise<SignupResponse> => {
    const response = await client.post<SignupResponse>('/auth/verify-email/', { token });
    return response.data;
};

export const resetPassword = async (data: PasswordResetRequest): Promise<void> => {
    await client.post('/auth/password-reset/', data);
};

export const confirmPasswordReset = async (data: PasswordResetConfirm): Promise<void> => {
    await client.post('/auth/password-reset/confirm/', data);
};

export const changePassword = async (data: PasswordChangeRequest): Promise<void> => {
    await client.post('/auth/password-change/', data);
};

// Resend verification email
export const resendVerificationEmail = async (email: string): Promise<{ message: string }> => {
    const response = await client.post<{ message: string }>('/auth/resend-verification/', { email });
    return response.data;
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

// Notification Preferences
export const getNotificationPreferences = async (): Promise<NotificationPreferences> => {
    const response = await client.get<NotificationPreferences>('/users/me/notifications/');
    return response.data;
};

export const updateNotificationPreferences = async (data: NotificationPreferences): Promise<NotificationPreferences> => {
    const response = await client.patch<NotificationPreferences>('/users/me/notifications/', data);
    return response.data;
};

// Onboarding
export const completeOnboarding = async (): Promise<{ message: string; onboarding_completed: boolean }> => {
    const response = await client.post<{ message: string; onboarding_completed: boolean }>('/users/me/onboarding/complete/');
    return response.data;
};

// Sessions
export const getUserSessions = async (): Promise<UserSession[]> => {
    const response = await client.get('/users/me/sessions/');
    const data = response.data;
    return Array.isArray(data) ? data : (data.results || []);
};

export const revokeSession = async (uuid: string): Promise<void> => {
    await client.delete(`/users/me/sessions/${uuid}/`);
};

export const logoutAllSessions = async (): Promise<void> => {
    await client.post('/users/me/sessions/logout-all/');
};

// Admin: Bulk Invite
export interface BulkInviteUser {
    email: string;
    full_name: string;
    role: string;
}

export interface BulkInviteResponse {
    invited: number;
    errors: Array<{ email: string; error: string }>;
}

export const bulkInviteUsers = async (users: BulkInviteUser[]): Promise<BulkInviteResponse> => {
    const response = await client.post<BulkInviteResponse>('/admin/users/bulk-invite/', { users });
    return response.data;
};

// Admin: Update User
export const updateAdminUser = async (uuid: string, data: { roles?: string[]; full_name?: string; is_active?: boolean }): Promise<any> => {
    const response = await client.patch(`/admin/users/${uuid}/`, data);
    return response.data;
};

// Data & Privacy
export const exportUserData = async (): Promise<Blob> => {
    const response = await client.post('/users/me/export-data/', {}, { responseType: 'blob' });
    return response.data;
};

export const deleteAccount = async (): Promise<void> => {
    await client.post('/users/me/delete-account/');
};
