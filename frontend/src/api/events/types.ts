export interface Event {
    uuid: string;
    title: string;
    slug: string;
    description: string;
    start_date: string;
    end_date: string;
    timezone: string;
    format: 'online' | 'in-person' | 'hybrid';
    status: 'draft' | 'published' | 'cancelled' | 'completed';
    organizer: string; // uuid
    registration_opens_at?: string;
    registration_closes_at?: string;
    created_at: string;
    updated_at: string;
    // Computed fields
    is_registration_open: boolean;
}

export interface EventCreateRequest {
    title: string;
    description: string;
    start_date: string;
    end_date: string;
    timezone: string;
    format: 'online' | 'in-person' | 'hybrid';
    registration_opens_at?: string;
    registration_closes_at?: string;
}

export interface EventUpdateRequest extends Partial<EventCreateRequest> {
    status?: 'draft' | 'published' | 'cancelled' | 'completed';
}

export interface EventSession {
    uuid: string;
    title: string;
    start_time: string;
    end_time: string;
    description?: string;
    location?: string;
    speaker_names?: string;
}

export interface EventCustomField {
    uuid: string;
    name: string;
    field_type: 'text' | 'number' | 'date' | 'select' | 'checkbox';
    is_required: boolean;
    options?: any; // JSON
}
