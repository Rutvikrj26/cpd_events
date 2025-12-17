export interface Module {
    uuid: string;
    event: string;
    title: string;
    description: string;
    order: number;
    is_published: boolean;
}

export interface ModuleContent {
    uuid: string;
    module: string;
    title: string;
    content_type: 'video' | 'document' | 'quiz';
    file?: string;
    url?: string;
    order: number;
}

export interface Assignment {
    uuid: string;
    module: string;
    title: string;
    description: string;
    due_date?: string;
    points: number;
}
