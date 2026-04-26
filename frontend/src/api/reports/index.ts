import client from '@/api/client';

export interface ReportSummary {
    total_revenue_cents: number;
    total_attendees: number;
    events_hosted: number;
    avg_rating: number | null;
    currency: string;
}

export interface ReportTrend {
    date: string | null;
    registrations: number;
    revenue_cents: number;
}

export interface TicketBreakdown {
    label: string;
    count: number;
}

export interface RecentTransaction {
    registration_uuid: string;
    event_title: string;
    amount_cents: number;
    currency: string;
    created_at: string;
}

export interface ReportsResponse {
    summary: ReportSummary;
    trends: ReportTrend[];
    ticket_breakdown: TicketBreakdown[];
    recent_transactions: RecentTransaction[];
}

export const getReports = async (period: string): Promise<ReportsResponse> => {
    const response = await client.get<ReportsResponse>('/events/reports/', {
        params: { period },
    });
    return response.data;
};

// ============================================
// Course / Program reports (Phase 6)
// ============================================

export interface LearningSummary {
    total_enrollments: number;
    completions: number;
    completion_rate: number | null;
    courses_published?: number;
    programs_published?: number;
    gross_revenue_cents?: number;
    refunds_cents?: number;
    net_revenue_cents?: number;
    purchase_count?: number;
    refund_count?: number;
}

export interface RecentTransaction {
    purchase_uuid: string;
    course_title?: string;
    program_title?: string;
    user_name: string;
    amount_cents: number;
    currency: string;
    status: string;
    created_at: string | null;
}

export interface LearningTrendPoint {
    date: string | null;
    count: number;
}

export interface LearningStatusBreakdown {
    label: string;
    count: number;
}

export interface RecentCourseEnrollment {
    enrollment_uuid: string;
    course_title: string;
    user_name: string;
    progress_percent: number;
    status: string;
    enrolled_at: string;
}

export interface RecentProgramEnrollment {
    enrollment_uuid: string;
    program_title: string;
    user_name: string;
    status: string;
    enrolled_at: string;
}

export interface LearningTopItem {
    uuid: string;
    title: string;
    enrollments: number;
}

export interface CourseReportsResponse {
    summary: LearningSummary;
    trends: LearningTrendPoint[];
    status_breakdown: LearningStatusBreakdown[];
    recent_enrollments: RecentCourseEnrollment[];
    top_courses: LearningTopItem[];
    recent_transactions?: RecentTransaction[];
}

export interface ProgramReportsResponse {
    summary: LearningSummary;
    trends: LearningTrendPoint[];
    status_breakdown: LearningStatusBreakdown[];
    recent_enrollments: RecentProgramEnrollment[];
    top_programs: LearningTopItem[];
}

export const getCourseReports = async (period: string): Promise<CourseReportsResponse> => {
    const response = await client.get<CourseReportsResponse>('/courses/reports/', {
        params: { period },
    });
    return response.data;
};

export const getProgramReports = async (period: string): Promise<ProgramReportsResponse> => {
    const response = await client.get<ProgramReportsResponse>('/programs/reports/', {
        params: { period },
    });
    return response.data;
};
