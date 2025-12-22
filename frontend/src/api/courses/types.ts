export interface Course {
    uuid: string;
    organization: string;
    organization_name?: string;
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
    is_free: boolean;
    price_cents: number;
    currency: string;

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
    organization_slug: string;
    title: string;
    slug?: string;
    description?: string;
    short_description?: string;
    featured_image_url?: string;
    cpd_credits?: number;
    cpd_type?: string;
    status?: 'draft' | 'published';
    is_public?: boolean;
    is_free?: boolean;
    price_cents?: number;
    enrollment_open?: boolean;
    max_enrollments?: number;
    estimated_hours?: number;
    passing_score?: number;
    certificates_enabled?: boolean;
    certificate_template?: string;
}

export interface EventModule {
    uuid: string;
    title: string;
    description: string;
    content_count: number;
    assignment_count: number;
    cpd_credits: string | number;
    contents?: any[]; // Allow contents here
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
