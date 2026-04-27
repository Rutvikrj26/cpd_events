/**
 * Shared content-viewer prop type. Every viewer accepts the same
 * `ModuleContent` shape so the player can dispatch by `content_type`.
 *
 * Loosely typed because backend payloads in `content_data` are
 * heterogeneous per type (a quiz has questions, a video has urls).
 */
export interface ModuleContent {
    uuid: string;
    title: string;
    content_type: 'text' | 'video' | 'document' | 'quiz' | 'lesson' | 'external';
    content_data?: any;
    file?: string;
    duration_minutes?: number;
    is_required: boolean;
    order: number;
}

export interface ContentViewerProps {
    content: ModuleContent;
}
