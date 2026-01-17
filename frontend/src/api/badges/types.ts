export interface BadgeTemplate {
    uuid: string;
    name: string;
    description?: string;
    start_image: string; // URL
    width_px: number;
    height_px: number;
    field_positions?: Record<string, any>;
    is_active: boolean;
    is_shared: boolean;
    created_at: string;
    updated_at: string;
}

export interface IssuedBadge {
    uuid: string;
    template: string; // uuid
    template_name: string;
    recipient_name: string;
    image_url: string;
    verification_code: string;
    short_code: string;
    status: 'active' | 'revoked';
    issued_at: string;
    event_title?: string;
    course_title?: string;
    badge_data?: Record<string, any>;
}
