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
import { Button } from '@/shared/ui/button';
import { Progress } from '@/shared/ui/progress';
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
    assignmentUuid: string
): AssignmentSubmission | undefined {
    return submissions
        .filter((s) => s.assignment === assignmentUuid)
        .sort((a, b) => (b.attempt_number || 0) - (a.attempt_number || 0))[0];
}

/**
 * PlayerSidebar — left rail of the course player. Renders:
 *   - course header with back-button + title + progress bar
 *   - live-sessions list (live + hybrid courses with sessions)
 *   - module list with expandable content + assignment rows
 *
 * Pure presentational: every piece of state and every callback comes
 * from `<CoursePlayer>`. Locked modules dim and disable their toggle.
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
    onSelectContent,
    onSelectAssignment,
}: PlayerSidebarProps) {
    const navigate = useNavigate();
    const showSessions =
        (course.format === 'live' || course.format === 'hybrid') && sessions.length > 0;
    const showModules = course.format !== 'live';

    return (
        <div className="w-80 border-r bg-muted/30 flex flex-col">
            <div className="p-4 border-b bg-background">
                <Button
                    variant="ghost"
                    size="sm"
                    className="mb-2 -ml-2"
                    onClick={() => navigate('/registrations?tab=courses')}
                >
                    <ArrowLeft className="mr-2 h-4 w-4" />
                    Back to Courses
                </Button>
                <h1 className="font-semibold text-lg line-clamp-2">{course.title}</h1>
                <div className="mt-3">
                    <div className="flex justify-between text-sm mb-1">
                        <span className="text-muted-foreground">Progress</span>
                        <span className="font-medium">{progressPercent}%</span>
                    </div>
                    <Progress value={progressPercent} className="h-2" />
                </div>
            </div>

            {/* Sidebar — two-track for live/hybrid: sessions above modules.
                Pure-online courses skip the sessions group; pure-live skip
                modules. See docs/design/hybrid-course-experience.md §B. */}
            <div className="flex-1 overflow-y-auto">
                {showSessions && (
                    <div className="p-2 border-b">
                        <div className="px-3 py-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                            Live Sessions
                        </div>
                        {sessions.map((s) => {
                            const rec = (s as any).recording;
                            const ends = (s as any).ends_at
                                ? new Date((s as any).ends_at)
                                : new Date(
                                      new Date(s.starts_at).getTime() +
                                          (s.duration_minutes ?? 0) * 60_000
                                  );
                            const isPast = new Date() >= ends || s.status === 'completed';
                            const isInPerson = s.delivery_mode === 'in_person';
                            const showHostPill =
                                !!course.is_current_user_host && !isPast && !isInPerson;
                            return (
                                <div key={s.uuid} className="flex items-center gap-1 px-1">
                                    <div className="flex-1 min-w-0">
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
                                            state={s.status === 'live' ? 'live' : 'pre_event'}
                                            size="sm"
                                            variant="outline"
                                            className="shrink-0 h-7 px-2 text-xs"
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
                                completedContents.has(c.uuid)
                            );
                            const isLocked = moduleAvailability[moduleUuid] === false;
                            const isExpanded = !!expandedModules[moduleUuid];

                            return (
                                <div
                                    key={moduleUuid}
                                    className={`mb-2 ${isLocked ? 'opacity-60' : ''}`}
                                >
                                    <button
                                        onClick={() => !isLocked && onToggleModule(moduleUuid)}
                                        className={`w-full flex items-center gap-2 p-3 rounded-lg transition-colors text-left ${
                                            isLocked ? 'cursor-not-allowed' : 'hover:bg-muted'
                                        }`}
                                    >
                                        <ChevronRight
                                            className={`h-4 w-4 transition-transform ${
                                                isExpanded ? 'rotate-90' : ''
                                            }`}
                                        />
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2">
                                                {isLocked ? (
                                                    <Lock className="h-4 w-4 text-muted-foreground shrink-0" />
                                                ) : moduleCompleted ? (
                                                    <CheckCircle2 className="h-4 w-4 text-success shrink-0" />
                                                ) : (
                                                    <span className="w-5 h-5 rounded-full border-2 flex items-center justify-center text-xs font-medium shrink-0">
                                                        {modIdx + 1}
                                                    </span>
                                                )}
                                                <span className="font-medium truncate">
                                                    {moduleTitle}
                                                </span>
                                            </div>
                                            <span className="text-xs text-muted-foreground">
                                                {isLocked
                                                    ? 'Complete previous module to unlock'
                                                    : `${mod.contents?.length || 0} items`}
                                            </span>
                                        </div>
                                    </button>

                                    {isExpanded && mod.contents && (
                                        <div className="ml-4 pl-4 border-l">
                                            {mod.contents.map((content) => {
                                                const isActive =
                                                    currentItem?.type === 'content' &&
                                                    currentItem.item.uuid === content.uuid;
                                                const isCompleted = completedContents.has(
                                                    content.uuid
                                                );
                                                return (
                                                    <button
                                                        key={content.uuid}
                                                        onClick={() =>
                                                            onSelectContent(content, moduleUuid)
                                                        }
                                                        className={`w-full flex items-center gap-2 p-2 rounded-md text-left text-sm transition-colors ${
                                                            isActive
                                                                ? 'bg-primary/10 text-primary'
                                                                : 'hover:bg-muted'
                                                        }`}
                                                    >
                                                        {getContentIcon(
                                                            content.content_type,
                                                            isCompleted
                                                        )}
                                                        <span className="truncate flex-1">
                                                            {content.title}
                                                        </span>
                                                        {!content.is_required && (
                                                            <span className="text-[10px] text-muted-foreground shrink-0">
                                                                Optional
                                                            </span>
                                                        )}
                                                    </button>
                                                );
                                            })}

                                            {(mod.module?.assignments || []).map((assignment) => {
                                                const isActive =
                                                    currentItem?.type === 'assignment' &&
                                                    currentItem.item.uuid === assignment.uuid;
                                                const latest = getLatestSubmission(
                                                    submissions,
                                                    assignment.uuid
                                                );
                                                return (
                                                    <button
                                                        key={assignment.uuid}
                                                        onClick={() =>
                                                            onSelectAssignment(
                                                                assignment,
                                                                moduleUuid
                                                            )
                                                        }
                                                        className={`w-full flex items-center gap-2 p-2 rounded-md text-left text-sm transition-colors ${
                                                            isActive
                                                                ? 'bg-primary/10 text-primary'
                                                                : 'hover:bg-muted'
                                                        }`}
                                                    >
                                                        <ClipboardCheck className="h-4 w-4 text-warning" />
                                                        <span className="truncate flex-1">
                                                            {assignment.title}
                                                        </span>
                                                        <span className="text-xs text-muted-foreground">
                                                            {latest?.status_display ||
                                                                latest?.status ||
                                                                'Not started'}
                                                        </span>
                                                    </button>
                                                );
                                            })}
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
        </div>
    );
}
