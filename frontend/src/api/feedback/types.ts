export interface EventFeedback {
    uuid: string;
    event: string; // Event UUID
    registration: string; // Registration UUID
    rating: number; // 1-5
    content_quality_rating: number; // 1-5
    speaker_rating: number; // 1-5
    comments?: string;
    is_anonymous: boolean;
    created_at: string;
    attendee_name: string; // "Anonymous" if is_anonymous is true
}

export interface EventFeedbackCreateRequest {
    event: string; // Event UUID
    registration: string; // Registration UUID
    rating: number; // 1-5
    content_quality_rating: number; // 1-5
    speaker_rating: number; // 1-5
    comments?: string;
    is_anonymous?: boolean;
}

export interface EventFeedbackUpdateRequest {
    rating?: number;
    content_quality_rating?: number;
    speaker_rating?: number;
    comments?: string;
    is_anonymous?: boolean;
}

export interface FeedbackSummary {
    total_count: number;
    average_rating: number;
    average_content_quality: number;
    average_speaker_rating: number;
    rating_distribution: {
        1: number;
        2: number;
        3: number;
        4: number;
        5: number;
    };
}
