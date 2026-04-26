import type { Course } from '../courses/types';

export type ProgramStatus = 'draft' | 'published' | 'archived';

export interface ProgramCourseEntry {
    uuid: string;
    course: Course;
    order: number;
    is_required: boolean;
    created_at: string;
}

export interface Program {
    uuid: string;
    title: string;
    slug: string;
    description: string;
    short_description: string;
    featured_image_url?: string;
    effective_image_url: string;
    status: ProgramStatus;
    is_public: boolean;
    price_cents: number;
    currency: string;
    is_free: boolean;
    sum_individual_price_cents: number;
    bundle_savings_cents: number;
    /** Populated for the authenticated viewer: courses in this program that
     *  the viewer has already paid for individually. Used to warn against
     *  double-charging when purchasing the bundle. Empty list for anonymous
     *  or unauthenticated viewers. */
    already_paid_for_courses?: Array<{
        course_uuid: string;
        course_title: string;
        amount_cents: number;
        currency: string;
        purchased_at: string | null;
    }>;
    stripe_price_id?: string;
    course_count: number;
    enrollment_count: number;
    program_courses: ProgramCourseEntry[];
    created_at: string;
    updated_at?: string;
}

export interface ProgramListItem {
    uuid: string;
    title: string;
    slug: string;
    short_description: string;
    effective_image_url: string;
    status: ProgramStatus;
    is_public: boolean;
    price_cents: number;
    currency: string;
    is_free: boolean;
    course_count: number;
    enrollment_count: number;
    created_at: string;
}

export interface ProgramCreateRequest {
    title: string;
    slug?: string;
    description?: string;
    short_description?: string;
    featured_image_url?: string;
    status?: ProgramStatus;
    is_public?: boolean;
    price_cents?: number;
    currency?: string;
}

export interface ProgramEnrollmentCourse {
    uuid: string;
    title: string;
    slug: string;
    order: number;
    is_required: boolean;
    enrollment_status: 'pending' | 'active' | 'completed' | 'dropped' | null;
    progress_percent: number;
    completed_at: string | null;
}

export interface ProgramEnrollment {
    uuid: string;
    program: ProgramListItem;
    status: 'pending' | 'active' | 'completed' | 'dropped';
    enrolled_at: string;
    started_at?: string;
    completed_at?: string;
    course_enrollments_seeded: boolean;
    courses?: ProgramEnrollmentCourse[];
}

export interface ProgramCourseAddRequest {
    course_uuid: string;
    order?: number;
    is_required?: boolean;
}
