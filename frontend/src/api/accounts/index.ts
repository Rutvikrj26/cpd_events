import client from '../client';
import {
    LoginRequest,
    AuthResponse,
    SignupRequest,
    SignupResponse,
    User,
    UserSession,
    RefreshTokenRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    PasswordChangeRequest,
    NotificationPreferences
} from './types';

export const login = async (data: LoginRequest): Promise<AuthResponse> => {
    const response = await client.post<AuthResponse>('/auth/token/', data);
    return response.data;
};

export const signup = async (data: SignupRequest): Promise<SignupResponse> => {
    const response = await client.post<SignupResponse>('/auth/signup/', data);
    return response.data;
};

export const signInWithFirebase = async (idToken: string): Promise<AuthResponse> => {
    const response = await client.post<AuthResponse>('/auth/firebase/', { id_token: idToken });
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

// Email change (self-service)
export interface EmailChangeRequestPayload {
    current_password: string;
    new_email: string;
}

export const requestEmailChange = async (data: EmailChangeRequestPayload): Promise<{ pending_email: string; message: string }> => {
    const response = await client.post('/users/me/email-change/request/', data);
    return response.data;
};

export const confirmEmailChange = async (token: string): Promise<{ message: string }> => {
    const response = await client.post('/auth/email-change/confirm/', { token });
    return response.data;
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

export const bulkInviteUsers = async (invitations: BulkInviteUser[]): Promise<BulkInviteResponse> => {
    const response = await client.post<BulkInviteResponse>('/admin/users/bulk-invite/', { invitations });
    return response.data;
};

// Admin: Invite a single user
export interface InviteUserRequest {
    email: string;
    full_name: string;
    role: string;
    message?: string;
}

export interface UserInvitation {
    uuid: string;
    email: string;
    full_name: string;
    role: string;
    invited_by_name: string | null;
    status: 'pending' | 'accepted' | 'expired' | 'revoked';
    is_used: boolean;
    is_expired: boolean;
    expires_at: string;
    accepted_at: string | null;
    created_at: string;
    last_sent_at: string;
    resent_count: number;
    revoked_at: string | null;
}

export const inviteUser = async (data: InviteUserRequest): Promise<{ invitation: UserInvitation; message: string }> => {
    const response = await client.post<{ invitation: UserInvitation; message: string }>(
        '/admin/users/invite/',
        data,
    );
    return response.data;
};

// Admin: Invitation management
export interface ListInvitationsParams {
    status?: 'pending' | 'accepted' | 'expired' | 'revoked';
    search?: string;
    include_revoked?: boolean;
}

export const listInvitations = async (params: ListInvitationsParams = {}): Promise<UserInvitation[]> => {
    const response = await client.get('/admin/users/invitations/', { params });
    const data = response.data;
    return Array.isArray(data) ? data : (data.results || []);
};

export const resendInvitation = async (uuid: string): Promise<UserInvitation> => {
    const response = await client.post<{ invitation: UserInvitation }>(
        `/admin/users/invitations/${uuid}/resend/`,
    );
    return response.data.invitation;
};

export const revokeInvitation = async (uuid: string): Promise<UserInvitation> => {
    const response = await client.post<{ invitation: UserInvitation }>(
        `/admin/users/invitations/${uuid}/revoke/`,
    );
    return response.data.invitation;
};

// Admin: Update User
export const updateAdminUser = async (uuid: string, data: { roles?: string[]; full_name?: string; is_active?: boolean }): Promise<any> => {
    const response = await client.patch(`/admin/users/${uuid}/`, data);
    return response.data;
};

// Admin: Aggregated detail view
export interface AdminUserDetail {
    profile: {
        uuid: string;
        email: string;
        full_name: string;
        professional_title: string | null;
        organization_name: string | null;
        roles: string[];
        primary_role: 'learner' | 'organizer' | 'instructor' | 'admin';
        is_active: boolean;
        email_verified: boolean;
        last_login_at: string | null;
        created_at: string;
    };
    groups: string[];
    course_staff: Array<{
        uuid: string;
        course_uuid: string;
        course_slug?: string;
        course_title: string;
        role: string;
        created_at: string;
    }>;
    owned_events: Array<{ uuid: string; title: string; status: string; starts_at: string | null }>;
    owned_courses: Array<{ uuid: string; slug?: string; title: string; status: string }>;
    certificates: Array<{ uuid: string; short_code: string; title: string; issued_at: string | null }>;
    recent_activity: Array<{
        type: string;
        at: string;
        changed_by_name: string | null;
        summary: string;
        metadata: Record<string, unknown>;
    }>;
    pending_invitation: { uuid: string; status: string; expires_at: string } | null;
}

export const getAdminUserDetail = async (uuid: string): Promise<AdminUserDetail> => {
    const response = await client.get<AdminUserDetail>(`/admin/users/${uuid}/detail/`);
    return response.data;
};

export const deactivateAdminUser = async (uuid: string): Promise<{ is_active: boolean }> => {
    const response = await client.post(`/admin/users/${uuid}/deactivate/`);
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

// Unified learner accreditations feed (certificates + badges)
export interface AccreditationItem {
    kind: 'certificate' | 'badge';
    uuid: string;
    title: string;
    source_title: string;
    source_kind: 'event' | 'course' | null;
    issued_at: string;
    verification_code: string;
    verify_url: string | null;
    artifact_url: string | null;
    short_code: string;
}

export interface AccreditationsResponse {
    count: number;
    results: AccreditationItem[];
}

export const getMyAccreditations = async (): Promise<AccreditationsResponse> => {
    const response = await client.get<AccreditationsResponse>('/users/me/accreditations/');
    return response.data;
};
