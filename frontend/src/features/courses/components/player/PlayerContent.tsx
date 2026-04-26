import { ContentViewer } from '../content-viewers/ContentViewer';
import { QuizTaker, type QuizResult } from '../content-viewers/QuizTaker';
import { AssignmentSubmissionForm } from './AssignmentSubmissionForm';
import { LockedModuleNotice } from './LockedModuleNotice';
import type { Assignment, AssignmentSubmission } from '@/api/courses/types';
import type { ContentWithProgress } from '../../hooks';

interface PlayerContentProps {
    activeContent: ContentWithProgress | null;
    activeAssignment: Assignment | null;
    /** True when the current item belongs to a locked module. */
    isLocked: boolean;
    contentProgressMap: Record<string, any>;
    /** Latest submission for the active assignment (if any). */
    latestSubmissionForActive?: AssignmentSubmission;
    onQuizComplete: (
        content: ContentWithProgress,
        result: QuizResult | undefined
    ) => void | Promise<void>;
}

/**
 * PlayerContent — main reading pane. Dispatches to the right viewer:
 *   - Locked module → `<LockedModuleNotice>`
 *   - Quiz content → `<QuizTaker>` (owns its own state machine)
 *   - Other read-only types → `<ContentViewer>` (text/video/document/lesson/external)
 *   - Assignment → `<AssignmentSubmissionForm>`
 */
export function PlayerContent({
    activeContent,
    activeAssignment,
    isLocked,
    contentProgressMap,
    latestSubmissionForActive,
    onQuizComplete,
}: PlayerContentProps) {
    if (isLocked) {
        return (
            <LockedModuleNotice
                title={activeContent?.title || activeAssignment?.title}
            />
        );
    }

    return (
        <div className="max-w-4xl mx-auto">
            {/* Read-only viewers (text, video, document, lesson, external)
                are dispatched by the shared <ContentViewer>. Quiz is rendered
                separately because it owns submission state. */}
            {activeContent && activeContent.content_type !== 'quiz' && (
                <ContentViewer content={activeContent as any} />
            )}

            {activeContent && activeContent.content_type === 'quiz' && (
                <QuizTaker
                    key={activeContent.uuid}
                    content={activeContent as any}
                    savedProgress={contentProgressMap[activeContent.uuid]?.last_position}
                    onComplete={(result) => onQuizComplete(activeContent, result)}
                />
            )}

            {activeAssignment && (
                <AssignmentSubmissionForm
                    key={activeAssignment.uuid}
                    assignment={activeAssignment}
                    latestSubmission={latestSubmissionForActive}
                />
            )}
        </div>
    );
}
