import { CheckCircle2, ChevronRight, Info, MessageSquare } from 'lucide-react';
import { Button } from '@/shared/ui/button';
import { Badge } from '@/shared/ui/badge';
import type { Assignment } from '@/api/courses/types';
import type { ContentWithProgress } from '../../hooks';

interface PlayerHeaderProps {
    activeContent: ContentWithProgress | null;
    activeAssignment: Assignment | null;
    isCurrentContentCompleted: boolean;
    hasAnnouncements: boolean;
    onOpenDiscussion: () => void;
    onOpenAnnouncements: () => void;
    onMarkComplete: () => void;
    onAdvanceToNext: () => void;
}

/**
 * PlayerHeader — top bar of the main content area. Shows:
 *   - title + content-type badge of the active item
 *   - duration (when present)
 *   - Discussion / Announcements / Mark Complete / Next buttons
 *
 * Mark Complete is suppressed for quiz content (the QuizTaker owns that
 * flow itself — completing on a passing score).
 */
export function PlayerHeader({
    activeContent,
    activeAssignment,
    isCurrentContentCompleted,
    hasAnnouncements,
    onOpenDiscussion,
    onOpenAnnouncements,
    onMarkComplete,
    onAdvanceToNext,
}: PlayerHeaderProps) {
    return (
        <div className="p-4 border-b flex items-center justify-between bg-background">
            <div>
                <h2 className="text-xl font-semibold">
                    {activeContent ? activeContent.title : activeAssignment?.title}
                </h2>
                <div className="flex items-center gap-2 mt-1">
                    {activeContent && (
                        <Badge variant="outline" className="capitalize">
                            {activeContent.content_type}
                        </Badge>
                    )}
                    {activeAssignment && (
                        <Badge variant="outline" className="capitalize">
                            Assignment
                        </Badge>
                    )}
                    {activeContent?.duration_minutes && (
                        <span className="text-sm text-muted-foreground">
                            {activeContent.duration_minutes} min
                        </span>
                    )}
                </div>
            </div>
            <div className="flex gap-2">
                <Button variant="outline" onClick={onOpenDiscussion}>
                    <MessageSquare className="mr-2 h-4 w-4" />
                    Discussion
                </Button>
                {hasAnnouncements && (
                    <Button variant="outline" onClick={onOpenAnnouncements}>
                        <Info className="mr-2 h-4 w-4" />
                        Announcements
                    </Button>
                )}
                {activeContent &&
                    !isCurrentContentCompleted &&
                    activeContent.content_type !== 'quiz' && (
                        <Button onClick={onMarkComplete}>
                            <CheckCircle2 className="mr-2 h-4 w-4" />
                            Mark Complete
                        </Button>
                    )}
                {activeContent && isCurrentContentCompleted && (
                    <Button variant="outline" onClick={onAdvanceToNext}>
                        Next
                        <ChevronRight className="ml-2 h-4 w-4" />
                    </Button>
                )}
            </div>
        </div>
    );
}
