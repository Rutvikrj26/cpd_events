export interface Registration {
    uuid: string;
    event: string; // UUID or expanded object depending on serializer
    user: string;
    registration_date: string;
    status: 'pending' | 'confirmed' | 'cancelled' | 'attended';
    check_in_time?: string;
    custom_answers?: Record<string, any>;
}

export interface RegistrationCreateRequest {
    users?: { email: string; first_name: string; last_name: string }[];
    custom_answers?: Record<string, any>;
}

export interface LinkRegistrationRequest {
    email: string;
    token?: string; // If used
}
