export type CourseFormat = 'online' | 'hybrid';

export interface Course {
    uuid: string;
    organization: string | null;
    organization_name?: string;
    organization_logo_url?: string;
    title: string;
    slug: string;
    description: string;
    short_description: string;
    featured_image?: string;
    featured_image_url?: string;
    cpd_credits: string | number;
    cpd_type: string;
    status: 'draft' | 'published' | 'archived';
    is_public: boolean;

    // Pricing & Payments
    price_cents: number;
    currency: string;
    stripe_product_id?: string;
    stripe_price_id?: string;

    // Computed property (from backend)
    is_free: boolean;

    // Format (Self-Paced vs Hybrid)
    format: CourseFormat;

    // Virtual/Live Session Settings (for Hybrid courses)
    zoom_meeting_id?: string;
    zoom_meeting_url?: string;
    zoom_meeting_password?: string;
    zoom_webinar_id?: string;
    zoom_registrant_id?: string;
    live_session_start?: string;
    live_session_end?: string;
    live_session_timezone?: string;

    // Limits
    enrollment_open: boolean;
    max_enrollments?: number | null;
    enrollment_requires_approval: boolean;

    // Completion
    estimated_hours: string | number;
    passing_score: number;

    // Certificates
    certificates_enabled: boolean;
    certificate_template?: string | null;
    auto_issue_certificates: boolean;

    // Stats
    enrollment_count: number;
    completion_count: number;
    module_count: number;

    created_at: string;
    updated_at?: string;

    // Relations
    organization_slug?: string;
    modules?: CourseModule[];
}

export interface CourseCreateRequest {
    organization_slug?: string;
    title: string;
    slug?: string;
    description?: string;
    short_description?: string;
    featured_image_url?: string;
    cpd_credits?: number;
    cpd_type?: string;
    status?: 'draft' | 'published';
    is_public?: boolean;
    price_cents?: number;
    enrollment_open?: boolean;
    max_enrollments?: number;
    estimated_hours?: number;
    passing_score?: number;
    certificates_enabled?: boolean;
    certificate_template?: string;
    // Format & Virtual fields
    format?: CourseFormat;
    zoom_meeting_id?: string;
    zoom_meeting_url?: string;
    zoom_meeting_password?: string;
    zoom_webinar_id?: string;
    live_session_start?: string;
    live_session_end?: string;
    live_session_timezone?: string;
}

export interface Assignment {
    uuid: string;
    title: string;
    description?: string;
    instructions?: string;
    due_days_after_release?: number;
    max_score?: number;
    passing_score?: number;
    allow_resubmission?: boolean;
    max_attempts?: number;
    submission_type?: 'text' | 'file' | 'url' | 'mixed';
    submission_type_display?: string;
    rubric?: Record<string, any>;
    created_at?: string;
    updated_at?: string;
}

export interface AssignmentSubmission {
    uuid: string;
    assignment: string;
    assignment_title?: string;
    status: 'draft' | 'submitted' | 'in_review' | 'needs_revision' | 'graded' | 'approved';
    status_display?: string;
    attempt_number: number;
    submitted_at?: string;
    content?: Record<string, any>;
    file_url?: string;
    score?: number;
    feedback?: string;
    graded_at?: string;
    is_passing?: boolean;
    created_at?: string;
    updated_at?: string;
}

export interface AssignmentSubmissionStaff extends AssignmentSubmission {
    user_uuid: string;
    user_email: string;
    user_name?: string;
}

export interface CourseAnnouncement {
    uuid: string;
    title: string;
    body: string;
    is_published: boolean;
    created_by_name?: string;
    created_by_email?: string;
    created_at: string;
    updated_at?: string;
}

export interface EventModule {
    uuid: string;
    title: string;
    description: string;
    content_count: number;
    assignment_count: number;
    cpd_credits: string | number;
    contents?: any[];
    assignments?: Assignment[];
}

export interface CourseModule {
    uuid: string;
    module: EventModule;
    order: number;
    is_required: boolean;
    created_at: string;
    updated_at: string;
}

export interface CourseEnrollment {
    uuid: string;
    course: Course;
    status: 'active' | 'completed' | 'dropped';
    enrolled_at: string;
    started_at?: string;
    completed_at?: string;
    progress_percent: number;
    modules_completed: number;
    certificate_issued: boolean;
    certificate_issued_at?: string;
}
