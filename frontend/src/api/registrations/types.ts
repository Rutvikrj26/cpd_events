export interface MinimalEvent {
    uuid: string;
    title: string;
    slug: string;
    starts_at: string;
    status: string;
    cpd_credit_value: number;
    cpd_credit_type: string;
}

export interface Registration {
    uuid: string;
    event: MinimalEvent;
    status: 'confirmed' | 'waitlisted' | 'cancelled';
    email: string;
    full_name: string;
    attended: boolean;
    attendance_percent: number;
    attendance_eligible: boolean;
    certificate_issued: boolean;
    certificate_issued_at?: string;
    allow_public_verification: boolean;
    waitlist_position?: number;
    promoted_from_waitlist_at?: string;
    zoom_join_url?: string;
    can_join: boolean;
    certificate_url?: string;
    created_at: string;
}

export interface RegistrationCreateRequest {
    users?: { email: string; first_name: string; last_name: string }[];
    custom_answers?: Record<string, any>;
}

export interface LinkRegistrationRequest {
    email: string;
    token?: string; // If used
}
