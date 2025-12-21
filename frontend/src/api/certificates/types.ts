export interface CertificateTemplate {
    uuid: string;
    name: string;
    description?: string;
    format?: 'html' | 'image';
    html_template?: string;
    background_image_url?: string;
    file_url?: string;
    file_type?: string;
    field_positions?: Record<string, any>;
    is_default: boolean;
    is_active?: boolean;
    version: number;
    usage_count: number;
    created_at: string;
    updated_at?: string;
}

export interface Certificate {
    uuid: string;
    registration_uuid?: string;
    template_uuid?: string;
    status: 'active' | 'revoked';
    verification_code: string;
    short_code: string;
    certificate_data: {
        attendee_name: string;
        event_title: string;
        event_date: string;
        cpd_credits?: string;
        cpd_type?: string;
        organizer_name?: string;
    };
    pdf_file_url?: string;
    issued_by_name?: string;
    issued_at: string;
    revoked_at?: string;
    revoked_by_name?: string;
    revocation_reason?: string;
    view_count: number;
    download_count: number;
    created_at: string;
}

export interface CertificateIssueRequest {
    registration_uuids?: string[];  // Specific registrations, or empty for all eligible
    template_uuid?: string;         // Override event's default template
    force?: boolean;                // Issue even if already has certificate
}

export interface CertificateSummary {
    total_eligible: number;
    total_issued: number;
    total_pending: number;
    total_revoked: number;
}
