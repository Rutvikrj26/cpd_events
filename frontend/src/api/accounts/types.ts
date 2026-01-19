export interface User {
    uuid: string;
    email: string;
    full_name: string;
    account_type: 'attendee' | 'organizer' | 'course_manager' | 'admin';
    email_verified?: boolean;
    onboarding_completed?: boolean;
    is_active: boolean;
    date_joined: string;
    profile_image?: string;
    // Organizer profile fields (from UserSerializer)
    organization_name?: string;
    organizer_website?: string;
    organizer_logo_url?: string;
    organizer_bio?: string;
    gst_hst_number?: string;
}


export interface LoginRequest {
    email: string; // Backend uses 'email' field for auth
    password: string;
}

export interface SignupRequest {
    email: string;
    password: string;
    password_confirm: string;
    full_name: string;
    account_type?: 'attendee' | 'organizer' | 'course_manager';
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

export interface OrganizerProfile {
    organization_name: string;
    bio?: string;
    website?: string;
}

export interface UpgradeOrganizerRequest {
    organization_name: string;
    bio?: string;
    website?: string;
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
    notify_certificate_issued: boolean;
    notify_marketing: boolean;
}
