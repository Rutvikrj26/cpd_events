export type FeedbackFieldType =
    | 'rating'
    | 'text'
    | 'textarea'
    | 'select'
    | 'multiselect'
    | 'checkbox'
    | 'radio'
    | 'date'
    | 'number';

export interface FeedbackField {
    uuid: string;
    label: string;
    field_type: FeedbackFieldType;
    required: boolean;
    placeholder?: string;
    help_text?: string;
    options?: string[];
    min_value?: number | null;
    max_value?: number | null;
    order: number;
    created_at?: string;
}

export interface FeedbackFieldInput {
    label: string;
    field_type: FeedbackFieldType;
    required?: boolean;
    placeholder?: string;
    help_text?: string;
    options?: string[];
    min_value?: number | null;
    max_value?: number | null;
    order?: number;
}

export interface FeedbackFieldResponse {
    uuid: string;
    field_uuid: string;
    field_label: string;
    field_type: FeedbackFieldType;
    field_order: number;
    value: unknown;
}

export interface EventFeedback {
    uuid: string;
    event: string;
    session?: string | null;
    registration: string;
    is_anonymous: boolean;
    created_at: string;
    attendee_name: string;
    field_responses: FeedbackFieldResponse[];
}

export interface EventFeedbackCreateRequest {
    event: string;
    session?: string | null;
    registration: string;
    is_anonymous?: boolean;
    responses: Record<string, unknown>;
}

export interface EventFeedbackUpdateRequest {
    is_anonymous?: boolean;
    responses?: Record<string, unknown>;
}

export interface FeedbackSummary {
    total_count: number;
    per_field: Array<{
        field_uuid: string;
        field_label: string;
        field_type: FeedbackFieldType;
        average?: number;
        distribution?: Record<string, number>;
        responses: number;
    }>;
}
