import {
    CheckCircle2,
    ChevronRight,
    Info,
    MessageSquare,
    MoreHorizontal,
    PanelLeftClose,
    PanelLeftOpen,
} from 'lucide-react';

import { Button } from '@/shared/ui/button';
import { Badge } from '@/shared/ui/badge';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '@/shared/ui/dropdown-menu';
import type { Assignment } from '@/api/courses/types';
import type { ContentWithProgress } from '../../hooks';

interface PlayerHeaderProps {
    activeContent: ContentWithProgress | null;
    activeAssignment: Assignment | null;
    isCurrentContentCompleted: boolean;
    hasAnnouncements: boolean;
    /** Module title for breadcrumb display. */
    moduleTitle?: string;
    sidebarCollapsed: boolean;
    onToggleSidebar: () => void;
    onOpenDiscussion: () => void;
    onOpenAnnouncements: () => void;
    onMarkComplete: () => void;
    onAdvanceToNext: () => void;
}

/**
 * PlayerHeader — top bar of the main content area.
 *
 * Layout (left-to-right):
 *   - Sidebar collapse toggle
 *   - Breadcrumb-style title: Module › Lesson + content-type badge
 *   - Right cluster: primary CTA (Mark Complete / Next) + overflow
 *     menu containing Discussion / Announcements
 *
 * Mark Complete is suppressed for quiz content (the QuizTaker owns that
 * flow itself — completing on a passing score).
 */
export function PlayerHeader({
    activeContent,
    activeAssignment,
    isCurrentContentCompleted,
    hasAnnouncements,
    moduleTitle,
    sidebarCollapsed,
    onToggleSidebar,
    onOpenDiscussion,
    onOpenAnnouncements,
    onMarkComplete,
    onAdvanceToNext,
}: PlayerHeaderProps) {
    const title = activeContent?.title ?? activeAssignment?.title;

    return (
        <div className="flex items-center justify-between gap-3 border-b bg-background px-4 py-3">
            <div className="flex min-w-0 items-center gap-3">
                <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 shrink-0 px-0"
                    onClick={onToggleSidebar}
                    aria-label={sidebarCollapsed ? 'Open sidebar' : 'Collapse sidebar'}
                >
                    {sidebarCollapsed ? (
                        <PanelLeftOpen className="h-4 w-4" />
                    ) : (
                        <PanelLeftClose className="h-4 w-4" />
                    )}
                </Button>
                <div className="min-w-0">
                    {moduleTitle && (
                        <div className="truncate text-xs uppercase tracking-wide text-muted-foreground">
                            {moduleTitle}
                        </div>
                    )}
                    <div className="flex items-center gap-2">
                        <h2 className="truncate text-lg font-semibold leading-tight">
                            {title}
                        </h2>
                        {activeContent && (
                            <Badge variant="outline" className="shrink-0 capitalize">
                                {activeContent.content_type}
                            </Badge>
                        )}
                        {activeAssignment && (
                            <Badge variant="outline" className="shrink-0">
                                Assignment
                            </Badge>
                        )}
                        {activeContent?.duration_minutes && (
                            <span className="hidden text-sm text-muted-foreground md:inline">
                                {activeContent.duration_minutes} min
                            </span>
                        )}
                    </div>
                </div>
            </div>

            <div className="flex shrink-0 items-center gap-2">
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

                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <Button
                            variant="ghost"
                            size="sm"
                            className="h-9 w-9 px-0"
                            aria-label="More actions"
                        >
                            <MoreHorizontal className="h-4 w-4" />
                        </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                        <DropdownMenuItem onSelect={onOpenDiscussion}>
                            <MessageSquare className="mr-2 h-4 w-4" />
                            Discussion
                        </DropdownMenuItem>
                        {hasAnnouncements && (
                            <>
                                <DropdownMenuSeparator />
                                <DropdownMenuItem onSelect={onOpenAnnouncements}>
                                    <Info className="mr-2 h-4 w-4" />
                                    Announcements
                                </DropdownMenuItem>
                            </>
                        )}
                    </DropdownMenuContent>
                </DropdownMenu>
            </div>
        </div>
    );
}
