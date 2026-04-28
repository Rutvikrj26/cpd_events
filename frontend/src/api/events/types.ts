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

    // Multi-session
    is_multi_session?: boolean;

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

    // Badges
    badges_enabled?: boolean;
    auto_issue_badges?: boolean;
    badge_template?: string | null;

    // Pricing
    price?: number;
    currency?: string;
    is_free?: boolean;

    // Branding
    featured_image_url?: string;

    // Location
    location?: string;

    // Sessions (for multi-session events)
    sessions?: EventSession[];

    // Custom registration fields
    custom_fields?: EventCustomField[];

    // Misc
    is_public: boolean;
    is_current_user_host?: boolean; // Server-computed: owner | listed speaker | platform admin
    video_enabled?: boolean;        // Server-computed from video_settings.enabled
    transcription_enabled?: boolean; // Server-computed from video_settings.transcription_enabled
    /**
     * Most-recent AVAILABLE recording for this event (if any). Populated by
     * `EventDetailSerializer.get_latest_recording`. Includes unpublished
     * rows so hosts/admins can preview before publishing.
     */
    latest_recording?: {
        uuid: string;
        status: string;
        storage_path?: string;
        duration_seconds?: number;
        duration_display?: string;
        recording_end?: string | null;
        is_published: boolean;
    } | null;
    owner_name?: string; // List view
    organizer_name?: string; // Public list view
    owner?: { uuid: string; display_name: string }; // Detail view
    organizer?: { uuid: string; display_name: string; logo_url?: string }; // Public detail view

    // Organization (if event belongs to an organization)
    organization_info?: {
        uuid: string;
        name: string;
        slug: string;
        logo_url: string | null;
        primary_color?: string;
    };

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
    event_type: 'webinar' | 'workshop' | 'training' | 'lecture' | 'seminar' | 'other';
    format: 'online' | 'in-person' | 'hybrid';

    short_description?: string;
    registration_enabled?: boolean;
    registration_opens_at?: string;
    registration_closes_at?: string;
    max_attendees?: number; // capacity

    // Pricing
    price?: number;
    currency?: string;
    is_free?: boolean;

    // Organization (optional - for creating events under an organization)
    organization?: string; // UUID

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

    // Badges
    badges_enabled?: boolean;
    auto_issue_badges?: boolean;
    badge_template?: string | null;

    // Location (for in-person/hybrid events)
    location?: string;

    // Video conferencing
    video_settings?: {
        enabled: boolean;
        recording_enabled: boolean;
        auto_publish_recording?: boolean;
        screen_share: boolean;
        waiting_room_enabled?: boolean;
    };

    // Branding

    is_public?: boolean;
    custom_fields?: any[];

    // Frontend-only fields for Wizard state
    featured_image_url?: string;
    _imageFile?: File;
    _isImageRemoved?: boolean;
    uuid?: string;

    // Multi-session wizard state
    is_multi_session?: boolean;
    _sessions?: SessionFormData[];  // Frontend-only: sessions to save after event creation
}

export interface EventUpdateRequest extends Partial<EventCreateRequest> {
    status?: 'draft' | 'published' | 'cancelled' | 'completed';
}

export interface EventSession {
    uuid?: string;
    title: string;
    description?: string;
    speaker_names?: string;
    order: number;

    // Timing
    starts_at: string;
    ends_at?: string;  // Read-only, calculated
    duration_minutes: number;
    timezone?: string;

    // Session type
    session_type: 'live' | 'recorded' | 'hybrid';

    // CPD
    cpd_credits?: number;

    // Attendance
    minimum_attendance_percent?: number;

    // Status
    is_mandatory: boolean;
    is_published: boolean;
    is_past?: boolean;

    // Timestamps
    created_at?: string;
    updated_at?: string;
}

// For wizard form state - allows partial data before save
export interface SessionFormData {
    uuid?: string;
    title: string;
    description?: string;
    speaker_names?: string;
    order: number;
    starts_at: string;
    duration_minutes: number;
    session_type: 'live' | 'recorded' | 'hybrid';
    is_mandatory: boolean;
    is_published: boolean;
}

export type EventCustomFieldType =
    | 'text'
    | 'textarea'
    | 'select'
    | 'multiselect'
    | 'checkbox'
    | 'radio'
    | 'date'
    | 'number';

export interface EventCustomField {
    uuid: string;
    label: string;
    field_type: EventCustomFieldType;
    required: boolean;
    placeholder?: string;
    help_text?: string;
    options?: string[];
    min_value?: number | null;
    max_value?: number | null;
    order: number;
    created_at?: string;
}

export interface EventCustomFieldInput {
    label: string;
    field_type: EventCustomFieldType;
    required?: boolean;
    placeholder?: string;
    help_text?: string;
    options?: string[];
    min_value?: number | null;
    max_value?: number | null;
    order?: number;
}
