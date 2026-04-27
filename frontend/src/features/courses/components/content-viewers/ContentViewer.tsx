import { TextContentViewer } from './TextContentViewer';
import { VideoContentViewer } from './VideoContentViewer';
import { DocumentContentViewer } from './DocumentContentViewer';
import { LessonViewer } from './LessonViewer';
import { ExternalContentViewer } from './ExternalContentViewer';
import type { ContentViewerProps, ModuleContent } from './types';

/**
 * ContentViewer — type-driven dispatcher.
 *
 * Renders the right viewer for `content.content_type`. Quiz and
 * assignment have their own dedicated components (`QuizTaker`,
 * `AssignmentSubmissionForm`) because they own submission state and
 * grading flow; this dispatcher handles the read-only types only.
 */
export function ContentViewer({ content }: ContentViewerProps) {
    switch (content.content_type) {
        case 'text':
            return <TextContentViewer content={content} />;
        case 'video':
            return <VideoContentViewer content={content} />;
        case 'document':
            return <DocumentContentViewer content={content} />;
        case 'lesson':
            return <LessonViewer content={content} />;
        case 'external':
            return <ExternalContentViewer content={content} />;
        default:
            return null;
    }
}

export type { ContentViewerProps, ModuleContent };
