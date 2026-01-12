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
