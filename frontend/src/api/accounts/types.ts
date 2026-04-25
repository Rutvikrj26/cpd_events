export interface User {
    uuid: string;
    email: string;
    full_name: string;
    roles: string[];
    primary_role: 'learner' | 'organizer' | 'instructor' | 'admin';
    email_verified?: boolean;
    onboarding_completed?: boolean;
    is_active: boolean;
    date_joined: string;
    profile_image?: string;
    organization_name?: string;
    professional_title?: string;
    bio?: string;
    timezone?: string;
    pending_email?: string;
    gst_hst_number?: string;
}


export interface LoginRequest {
    email: string;
    password: string;
}

export interface SignupRequest {
    email: string;
    password: string;
    password_confirm: string;
    full_name: string;
    professional_title?: string;
    organization_name?: string;
}

export interface RefreshTokenRequest {
    refresh: string;
}

export interface PasswordResetRequest {
    email: string;
}

export interface PasswordResetConfirm {
    token: string;
    new_password: string;
    new_password_confirm: string;
}

export interface AuthResponse {
    access: string;
    refresh: string;
    user?: User;
}

export interface SignupResponse {
    message: string;
    access?: string;
    refresh?: string;
    user?: User;
}

export interface PasswordChangeRequest {
    current_password: string;
    new_password: string;
    new_password_confirm: string;
}

export interface NotificationPreferences {
    notify_event_reminders: boolean;
    notify_event_updates: boolean;
    notify_certificate_issued: boolean;
    notify_badges: boolean;
    notify_recordings: boolean;
    notify_course_progress: boolean;
}

export interface UserSession {
    uuid: string;
    session_key: string;
    ip_address: string;
    user_agent: string;
    device_type: string;
    last_activity_at: string;
    expires_at: string;
    is_active: boolean;
}

// Admin types
export interface AdminUserCreate {
    email: string;
    full_name: string;
    password: string;
    roles: string[];
    professional_title?: string;
    organization_name?: string;
}

export interface AdminUserUpdate {
    full_name?: string;
    professional_title?: string;
    organization_name?: string;
    is_active?: boolean;
    roles?: string[];
}

export interface InviteUserRequest {
    email: string;
    full_name: string;
    role: string;
    message?: string;
}

export interface AcceptInvitationRequest {
    token: string;
    password: string;
    password_confirm: string;
}

export interface UserInvitation {
    uuid: string;
    email: string;
    full_name: string;
    role: string;
    invited_by_name: string | null;
    is_used: boolean;
    is_expired: boolean;
    expires_at: string;
    accepted_at: string | null;
    created_at: string;
}
