export interface Event {
    uuid: string;
    slug: string;
    title: string;
    description: string;
    short_description: string;
    status: 'draft' | 'published' | 'live' | 'completed' | 'closed' | 'cancelled';
    event_type: string;
    format: 'online' | 'in-person' | 'hybrid';
    starts_at: string;
    ends_at: string;
    timezone: string;
    duration_minutes?: number;

    // Stats
    registration_count: number;
    attendee_count: number;
    waitlist_count: number;
    certificate_count?: number;
    spots_remaining?: number | null;

    // Registration
    registration_enabled: boolean;
    registration_opens_at?: string;
    registration_closes_at?: string;
    max_attendees?: number;
    capacity?: number; // Alias for max_attendees from backend
    is_registration_open?: boolean;

    // CPD (aliased fields from backend)
    cpd_credits?: number | string;
    cpd_type?: string;
    cpd_enabled?: boolean;

    // Certificates
    certificates_enabled?: boolean;
    auto_issue_certificates?: boolean;
    minimum_attendance_minutes?: number;
    minimum_attendance_percent?: number;

    // Branding
    featured_image_url?: string;

    // Misc
    is_public: boolean;
    owner_name?: string; // List view
    organizer_name?: string; // Public list view
    owner?: { uuid: string; display_name: string }; // Detail view
    organizer?: { uuid: string; display_name: string; logo_url?: string }; // Public detail view
    created_at: string;
    updated_at: string;
}

export interface EventCreateRequest {
    title: string;
    description: string;
    // Schema expects snake_case for some, but let's match what serializer expects
    // Based on Standard ModelSerializer:
    starts_at: string;
    duration_minutes: number;
    timezone: string;
    event_type: 'webinar' | 'workshop' | 'training' | 'lecture' | 'other';
    format: 'online' | 'in-person' | 'hybrid';

    short_description?: string;
    registration_enabled?: boolean;
    registration_opens_at?: string;
    registration_closes_at?: string;
    max_attendees?: number; // capacity

    // Pricing
    price?: number; // Backend doesn't have price field in Event model? 
    // Wait, checked Event model in Step 162. It DOES NOT have 'price'!
    // It has cpd_credit_value.
    // It seems price is missing from backend entirely? 
    // Or maybe it's managed via 'Ticket' model which I haven't seen?
    // User asked me originally to audit Zoom, but now I see a Price gap?
    // 'Registrations' usually link to 'TicketTypes' or similar if paid?
    // Registration model (viewed in Step 24 context mentions 'Registration' model).
    // I can't fix proper paid events now. I'll omit price from backend payload or send it as custom field?
    // The previous form had price.
    // I will comment it out or leave it optional but note it won't persist.

    // CPD
    cpd_credit_value?: number;
    cpd_credit_type?: string;
    cpd_enabled?: boolean;

    // Certificates
    certificates_enabled?: boolean;
    auto_issue_certificates?: boolean;
    certificate_template?: string | null;
    minimum_attendance_minutes?: number;
    minimum_attendance_percent?: number;

    // Zoom
    zoom_settings?: any;

    // Location (for in-person/hybrid events)
    location?: string;

    // Branding

    is_public?: boolean;
    custom_fields?: any[];

    // Frontend-only fields for Wizard state
    featured_image_url?: string;
    _imageFile?: File;
    _isImageRemoved?: boolean;
    uuid?: string;
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
