import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    ArrowLeft,
    CheckCircle2,
    Circle,
    FileText,
    Video,
    File,
    ChevronRight,
    ExternalLink,
    ClipboardCheck,
    Lock,
} from 'lucide-react';

import { cn } from '@/lib/utils';
import { Button } from '@/shared/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/shared/ui/tooltip';
import { LiveSessionRow } from '@/components/live/LiveSessionRow';
import { JoinButton } from '@/components/video/JoinButton';
import type {
    Assignment,
    AssignmentSubmission,
    Course,
    CourseSession,
} from '@/api/courses/types';
import type { ContentWithProgress, ModuleWithContents } from '../../hooks';
import type { CourseItem } from './types';

interface PlayerSidebarProps {
    course: Course;
    progressPercent: number;
    sessions: CourseSession[];
    modules: ModuleWithContents[];
    expandedModules: Record<string, boolean>;
    onToggleModule: (moduleUuid: string) => void;
    completedContents: Set<string>;
    moduleAvailability: Record<string, boolean>;
    submissions: AssignmentSubmission[];
    currentItem: CourseItem | null;
    /** When true, renders an icon-rail (w-14) instead of the full panel. */
    collapsed?: boolean;
    onSelectContent: (content: ContentWithProgress, moduleUuid: string) => void;
    onSelectAssignment: (assignment: Assignment, moduleUuid: string) => void;
}

function getContentIcon(type: string, completed: boolean) {
    if (completed) return <CheckCircle2 className="h-4 w-4 text-success" />;
    switch (type) {
        case 'video':
            return <Video className="h-4 w-4 text-info" />;
        case 'text':
            return <FileText className="h-4 w-4 text-warning" />;
        case 'document':
            return <File className="h-4 w-4 text-primary" />;
        case 'lesson':
            return <FileText className="h-4 w-4 text-success" />;
        case 'external':
            return <ExternalLink className="h-4 w-4 text-info" />;
        default:
            return <Circle className="h-4 w-4 text-muted-foreground" />;
    }
}

function getLatestSubmission(
    submissions: AssignmentSubmission[],
    assignmentUuid: string,
): AssignmentSubmission | undefined {
    return submissions
        .filter((s) => s.assignment === assignmentUuid)
        .sort((a, b) => (b.attempt_number || 0) - (a.attempt_number || 0))[0];
}

/**
 * PlayerSidebar — left rail of the course player.
 *
 * Two display modes:
 *   - Expanded (w-72): course header (back button + title) on top,
 *     scrollable module/session list below. Sticky module headers keep
 *     context while scrolling long lessons.
 *   - Collapsed (w-14): icon-rail showing completion dots per module,
 *     with hover tooltips. Click a module dot to expand the sidebar
 *     focused on that module.
 *
 * The active item auto-scrolls into view when `currentItem` changes,
 * so jumping to a deep lesson via "Next" doesn't leave the user
 * scrolling to find it.
 */
export function PlayerSidebar({
    course,
    progressPercent,
    sessions,
    modules,
    expandedModules,
    onToggleModule,
    completedContents,
    moduleAvailability,
    submissions,
    currentItem,
    collapsed = false,
    onSelectContent,
    onSelectAssignment,
}: PlayerSidebarProps) {
    const navigate = useNavigate();
    const showSessions =
        (course.format === 'live' || course.format === 'hybrid') && sessions.length > 0;
    const showModules = course.format !== 'live';
    const activeRowRef = useRef<HTMLButtonElement>(null);

    /* Auto-scroll the active item into view whenever the selection changes.
       `block: 'nearest'` avoids jarring jumps when the row is already
       on-screen. */
    useEffect(() => {
        if (!currentItem) return;
        const id = window.setTimeout(() => {
            activeRowRef.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        }, 50);
        return () => window.clearTimeout(id);
    }, [currentItem]);

    if (collapsed) {
        return (
            <CollapsedRail
                modules={modules}
                completedContents={completedContents}
                moduleAvailability={moduleAvailability}
                progressPercent={progressPercent}
                currentItem={currentItem}
            />
        );
    }

    // Suppress unused-import lint for `progressPercent` in expanded mode —
    // the sticky course progress bar in CoursePlayer is the source of truth
    // for the percent, so we don't render a duplicate in the sidebar.
    void progressPercent;

    return (
        <aside className="flex w-72 shrink-0 flex-col border-r bg-muted/30">
            <div className="border-b bg-background p-3">
                <Button
                    variant="ghost"
                    size="sm"
                    className="-ml-2 mb-1.5 h-8"
                    onClick={() => navigate('/registrations?tab=courses')}
                >
                    <ArrowLeft className="mr-2 h-4 w-4" />
                    Back to Courses
                </Button>
                <h1 className="line-clamp-2 text-base font-semibold leading-snug">
                    {course.title}
                </h1>
            </div>

            <div className="flex-1 overflow-y-auto">
                {showSessions && (
                    <div className="border-b p-2">
                        <div className="px-3 py-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                            Live Sessions
                        </div>
                        {sessions.map((s) => {
                            const rec = (s as any).recording;
                            const ends = (s as any).ends_at
                                ? new Date((s as any).ends_at)
                                : new Date(
                                      new Date(s.starts_at).getTime() +
                                          (s.duration_minutes ?? 0) * 60_000,
                                  );
                            const isPast = new Date() >= ends || s.status === 'completed';
                            const isInPerson = s.delivery_mode === 'in_person';
                            const showHostPill =
                                !!course.is_current_user_host && !isPast && !isInPerson;
                            return (
                                <div key={s.uuid} className="flex items-center gap-1 px-1">
                                    <div className="min-w-0 flex-1">
                                        <LiveSessionRow
                                            session={s as any}
                                            onClick={() => {
                                                const target =
                                                    isPast && rec
                                                        ? `/courses/${course.slug}/sessions/${s.uuid}/recording`
                                                        : `/courses/${course.slug}/sessions/${s.uuid}/lobby`;
                                                navigate(target);
                                            }}
                                        />
                                    </div>
                                    {showHostPill && (
                                        <JoinButton
                                            courseUuid={course.uuid}
                                            sessionUuid={s.uuid}
                                            role="host"
                                            state={
                                                s.status === 'live'
                                                    ? 'meeting_live'
                                                    : 'awaiting_host'
                                            }
                                            size="sm"
                                            variant="outline"
                                            className="h-7 shrink-0 px-2 text-xs"
                                        />
                                    )}
                                </div>
                            );
                        })}
                    </div>
                )}

                {showModules && (
                    <div className="p-2">
                        {modules.map((mod, modIdx) => {
                            const moduleUuid = mod.module?.uuid || mod.uuid;
                            const moduleTitle = mod.module?.title || `Module ${modIdx + 1}`;
                            const moduleCompleted = mod.contents?.every((c) =>
                                completedContents.has(c.uuid),
                            );
                            const isLocked = moduleAvailability[moduleUuid] === false;
                            const isExpanded = !!expandedModules[moduleUuid];
                            const containsActive =
                                currentItem?.moduleUuid === moduleUuid;

                            return (
                                <div
                                    key={moduleUuid}
                                    className={cn('mb-1', isLocked && 'opacity-60')}
                                >
                                    {/* Sticky module header — stays pinned at the top
                                        of its scroll region while the user reads down
                                        a long content list. */}
                                    <button
                                        onClick={() => !isLocked && onToggleModule(moduleUuid)}
                                        className={cn(
                                            'sticky top-0 z-10 flex w-full items-center gap-2 rounded-md bg-muted/30 px-2 py-2 text-left backdrop-blur-sm transition-colors',
                                            isLocked
                                                ? 'cursor-not-allowed'
                                                : 'hover:bg-muted',
                                            containsActive && 'bg-muted',
                                        )}
                                    >
                                        <ChevronRight
                                            className={cn(
                                                'h-3.5 w-3.5 shrink-0 transition-transform',
                                                isExpanded && 'rotate-90',
                                            )}
                                        />
                                        <div className="flex min-w-0 flex-1 items-center gap-2">
                                            {isLocked ? (
                                                <Lock className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                                            ) : moduleCompleted ? (
                                                <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-success" />
                                            ) : (
                                                <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full border-2 text-[10px] font-medium">
                                                    {modIdx + 1}
                                                </span>
                                            )}
                                            <span className="truncate text-sm font-medium">
                                                {moduleTitle}
                                            </span>
                                        </div>
                                        <span className="shrink-0 text-[11px] text-muted-foreground">
                                            {isLocked ? '🔒' : `${mod.contents?.length || 0}`}
                                        </span>
                                    </button>

                                    {isExpanded && mod.contents && (
                                        <div className="ml-3 border-l pl-3 pt-0.5">
                                            {mod.contents.map((content) => {
                                                const isActive =
                                                    currentItem?.type === 'content' &&
                                                    currentItem.item.uuid === content.uuid;
                                                const isCompleted = completedContents.has(
                                                    content.uuid,
                                                );
                                                return (
                                                    <button
                                                        key={content.uuid}
                                                        ref={isActive ? activeRowRef : undefined}
                                                        onClick={() =>
                                                            onSelectContent(content, moduleUuid)
                                                        }
                                                        className={cn(
                                                            'flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors',
                                                            isActive
                                                                ? 'bg-primary/10 text-primary'
                                                                : 'hover:bg-muted',
                                                        )}
                                                    >
                                                        {getContentIcon(
                                                            content.content_type,
                                                            isCompleted,
                                                        )}
                                                        <span className="flex-1 truncate">
                                                            {content.title}
                                                        </span>
                                                        {!content.is_required && (
                                                            <span className="shrink-0 text-[10px] text-muted-foreground">
                                                                Optional
                                                            </span>
                                                        )}
                                                    </button>
                                                );
                                            })}

                                            {(mod.module?.assignments || []).map(
                                                (assignment) => {
                                                    const isActive =
                                                        currentItem?.type === 'assignment' &&
                                                        currentItem.item.uuid ===
                                                            assignment.uuid;
                                                    const latest = getLatestSubmission(
                                                        submissions,
                                                        assignment.uuid,
                                                    );
                                                    return (
                                                        <button
                                                            key={assignment.uuid}
                                                            ref={
                                                                isActive ? activeRowRef : undefined
                                                            }
                                                            onClick={() =>
                                                                onSelectAssignment(
                                                                    assignment,
                                                                    moduleUuid,
                                                                )
                                                            }
                                                            className={cn(
                                                                'flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors',
                                                                isActive
                                                                    ? 'bg-primary/10 text-primary'
                                                                    : 'hover:bg-muted',
                                                            )}
                                                        >
                                                            <ClipboardCheck className="h-4 w-4 text-warning" />
                                                            <span className="flex-1 truncate">
                                                                {assignment.title}
                                                            </span>
                                                            <span className="text-xs text-muted-foreground">
                                                                {latest?.status_display ||
                                                                    latest?.status ||
                                                                    'Not started'}
                                                            </span>
                                                        </button>
                                                    );
                                                },
                                            )}
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
        </aside>
    );
}

/* -------- Collapsed icon rail --------------------------------------- */

interface CollapsedRailProps {
    modules: ModuleWithContents[];
    completedContents: Set<string>;
    moduleAvailability: Record<string, boolean>;
    progressPercent: number;
    currentItem: CourseItem | null;
}

function CollapsedRail({
    modules,
    completedContents,
    moduleAvailability,
    progressPercent,
    currentItem,
}: CollapsedRailProps) {
    return (
        <TooltipProvider delayDuration={200}>
            <aside className="flex w-14 shrink-0 flex-col items-center gap-1 border-r bg-muted/30 px-2 py-3">
                <div
                    className="mb-2 flex h-8 w-8 items-center justify-center rounded-full border-2 border-primary text-[10px] font-semibold tabular-nums text-primary"
                    aria-label={`${progressPercent}% complete`}
                >
                    {progressPercent}
                </div>
                {modules.map((mod, modIdx) => {
                    const moduleUuid = mod.module?.uuid || mod.uuid;
                    const moduleTitle = mod.module?.title || `Module ${modIdx + 1}`;
                    const moduleCompleted = mod.contents?.every((c) =>
                        completedContents.has(c.uuid),
                    );
                    const isLocked = moduleAvailability[moduleUuid] === false;
                    const isActive = currentItem?.moduleUuid === moduleUuid;
                    return (
                        <Tooltip key={moduleUuid}>
                            <TooltipTrigger asChild>
                                <div
                                    className={cn(
                                        'flex h-8 w-8 items-center justify-center rounded-full border text-xs font-medium',
                                        isLocked && 'opacity-50',
                                        moduleCompleted
                                            ? 'border-success bg-success/10 text-success'
                                            : 'border-border bg-background',
                                        isActive && 'ring-2 ring-primary ring-offset-1',
                                    )}
                                >
                                    {isLocked ? (
                                        <Lock className="h-3.5 w-3.5" />
                                    ) : moduleCompleted ? (
                                        <CheckCircle2 className="h-3.5 w-3.5" />
                                    ) : (
                                        modIdx + 1
                                    )}
                                </div>
                            </TooltipTrigger>
                            <TooltipContent side="right">
                                <span className="font-medium">{moduleTitle}</span>
                                {isLocked && (
                                    <span className="ml-2 text-muted-foreground">Locked</span>
                                )}
                            </TooltipContent>
                        </Tooltip>
                    );
                })}
            </aside>
        </TooltipProvider>
    );
}
