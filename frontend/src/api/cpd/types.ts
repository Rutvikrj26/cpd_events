/**
 * CPD tracking types
 */

export interface CPDRequirement {
    uuid: string;
    cpd_type: string;
    cpd_type_display: string;
    annual_requirement: number;
    period_type: 'calendar_year' | 'fiscal_year' | 'rolling_12';
    period_type_display: string;
    fiscal_year_start_month: number;
    fiscal_year_start_day: number;
    licensing_body: string;
    license_number: string;
    notes: string;
    is_active: boolean;
    earned_credits: string;
    completion_percent: number;
    credits_remaining: string;
    period_bounds: {
        start: string;
        end: string;
    };
    created_at: string;
    updated_at: string;
}

export interface CPDProgress {
    total_requirements: number;
    completed_requirements: number;
    in_progress_requirements: number;
    total_credits_earned: number;
    requirements: CPDRequirement[];
}

export interface CPDRequirementCreate {
    cpd_type: string;
    cpd_type_display?: string;
    annual_requirement: number;
    period_type?: 'calendar_year' | 'fiscal_year' | 'rolling_12';
    fiscal_year_start_month?: number;
    fiscal_year_start_day?: number;
    licensing_body?: string;
    license_number?: string;
    notes?: string;
}

export interface CPDExportParams {
    export_format?: 'json' | 'csv' | 'txt';
    start_date?: string;
    end_date?: string;
    cpd_type?: string;
}

export interface CPDTransaction {
    uuid: string;
    user_email: string;
    user_full_name: string;
    transaction_type: 'earned' | 'manual_adjustment' | 'expired' | 'revoked';
    transaction_type_display: string;
    credits: string;
    balance_after: string;
    notes: string;
    cpd_type: string;
    certificate: string | null;
    certificate_short_code: string | null;
    created_by: string | null;
    created_by_email: string | null;
    metadata: Record<string, any>;
    created_at: string;
}

export interface CPDTransactionSummary {
    current_balance: number;
    total_earned: number;
    total_adjusted: number;
    total_revoked: number;
    total_expired: number;
    transaction_count: number;
    first_transaction_date: string | null;
    latest_transaction_date: string | null;
}
