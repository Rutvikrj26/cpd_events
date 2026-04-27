import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { Award, Loader2 } from 'lucide-react';
import { Button } from '@/shared/ui/button';
import { useToast } from '@/shared/ui/use-toast';
import {
    useCoursePlayerData,
    useUpdateContentProgress,
    courseKeys,
} from '../../hooks';
import type {
    ContentWithProgress,
    ModuleWithContents,
} from '../../hooks';
import type { Assignment, AssignmentSubmission } from '@/api/courses/types';
import { PlayerSidebar } from './PlayerSidebar';
import { PlayerHeader } from './PlayerHeader';
import { PlayerContent } from './PlayerContent';
import { PlayerDialogs } from './PlayerDialogs';
import type { CourseItem } from './types';
import type { QuizResult } from '../content-viewers/QuizTaker';

interface CoursePlayerProps {
    courseUuid: string;
    /** Pass-through from the page so we don't import features/auth. */
    currentUserUuid?: string;
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
 * CoursePlayer — top-level orchestrator for the learner's course player.
 *
 * Owns:
 *   - `currentItem` (active content/assignment + module)
 *   - dialog open flags (announcements, discussion)
 *   - module-row expansion state
 *
 * Server state is delegated to `useCoursePlayerData` (one composite hook
 * that fans out to the existing per-resource RQ hooks). Mark-complete
 * goes through `useUpdateContentProgress` so progress invalidates
 * automatically.
 */
export function CoursePlayer({ courseUuid, currentUserUuid }: CoursePlayerProps) {
    const navigate = useNavigate();
    const { toast } = useToast();
    const queryClient = useQueryClient();
    const data = useCoursePlayerData(courseUuid);
    const updateProgress = useUpdateContentProgress();

    /* ---- Local UI state ---- */
    const [currentItem, setCurrentItem] = useState<CourseItem | null>(null);
    const [expandedModules, setExpandedModules] = useState<Record<string, boolean>>({});
    const [showAnnouncements, setShowAnnouncements] = useState(false);
    const [showDiscussion, setShowDiscussion] = useState(false);
    const hasAutoSelectedRef = useRef(false);

    /* ---- Auto-select first incomplete content on first hydrate ---- */
    useEffect(() => {
        if (hasAutoSelectedRef.current) return;
        if (data.isLoading) return;
        if (data.modules.length === 0) return;

        let target: { content: ContentWithProgress; moduleUuid: string } | null = null;
        for (const mod of data.modules) {
            const moduleUuid = mod.module?.uuid || mod.uuid;
            if (data.moduleAvailability[moduleUuid] === false) continue;
            for (const content of mod.contents || []) {
                if (!data.completedContents.has(content.uuid)) {
                    target = { content, moduleUuid };
                    break;
                }
            }
            if (target) break;
        }
        // Fallback: first content of first module that has any.
        if (!target) {
            const firstWith = data.modules.find((m) => (m.contents?.length ?? 0) > 0);
            if (firstWith && firstWith.contents?.[0]) {
                target = {
                    content: firstWith.contents[0],
                    moduleUuid: firstWith.module?.uuid || firstWith.uuid,
                };
            }
        }
        if (target) {
            setCurrentItem({
                type: 'content',
                item: target.content,
                moduleUuid: target.moduleUuid,
            });
            setExpandedModules({ [target.moduleUuid]: true });
        }
        hasAutoSelectedRef.current = true;
    }, [data.isLoading, data.modules, data.moduleAvailability, data.completedContents]);

    /* ---- Selection handlers ---- */
    const toggleModule = (moduleUuid: string) => {
        setExpandedModules((prev) => ({ ...prev, [moduleUuid]: !prev[moduleUuid] }));
    };

    const selectContent = (content: ContentWithProgress, moduleUuid: string) => {
        if (data.moduleAvailability[moduleUuid] === false) return;
        setCurrentItem({ type: 'content', item: content, moduleUuid });
    };

    const selectAssignment = (assignment: Assignment, moduleUuid: string) => {
        if (data.moduleAvailability[moduleUuid] === false) return;
        setCurrentItem({ type: 'assignment', item: assignment, moduleUuid });
    };

    /* ---- Progress / mark-complete ---- */
    const refreshProgress = () => {
        queryClient.invalidateQueries({ queryKey: courseKeys.progress(courseUuid) });
        // Newly unlocked modules need their content list — invalidate the
        // module-tree key, useQueries picks the new module ids up.
        queryClient.invalidateQueries({ queryKey: courseKeys.modules(courseUuid) });
    };

    const advanceToNext = () => {
        if (!currentItem || currentItem.type !== 'content') return;
        const moduleIndex = data.modules.findIndex(
            (m) => (m.module?.uuid || m.uuid) === currentItem.moduleUuid
        );
        const currentModule = data.modules[moduleIndex];
        const contentIndex =
            currentModule?.contents?.findIndex((c) => c.uuid === currentItem.item.uuid) ?? -1;

        // Next content in same module
        if (currentModule?.contents && contentIndex < currentModule.contents.length - 1) {
            setCurrentItem({
                type: 'content',
                item: currentModule.contents[contentIndex + 1],
                moduleUuid: currentItem.moduleUuid,
            });
            return;
        }
        // First content of next available module
        for (let i = moduleIndex + 1; i < data.modules.length; i++) {
            const nextUuid = data.modules[i].module?.uuid || data.modules[i].uuid;
            if (
                data.moduleAvailability[nextUuid] !== false &&
                data.modules[i].contents &&
                data.modules[i].contents.length > 0
            ) {
                setCurrentItem({
                    type: 'content',
                    item: data.modules[i].contents[0],
                    moduleUuid: nextUuid,
                });
                setExpandedModules({ [nextUuid]: true });
                return;
            }
        }
        // Course complete!
        toast({
            title: '🎉 Congratulations!',
            description: 'You have completed all course content!',
        });
    };

    const markComplete = async () => {
        if (!currentItem || currentItem.type !== 'content') return;
        try {
            await updateProgress.mutateAsync({
                contentUuid: currentItem.item.uuid,
                data: { progress_percent: 100, completed: true, courseUuid },
            } as any);
            toast({
                title: 'Progress saved!',
                description: 'Content marked as complete.',
            });
            advanceToNext();
        } catch (error) {
            console.error('Failed to update progress:', error);
            toast({
                variant: 'destructive',
                title: 'Error',
                description: 'Failed to save progress.',
            });
        }
    };

    const handleQuizComplete = async (
        content: ContentWithProgress,
        result: QuizResult | undefined
    ) => {
        try {
            await updateProgress.mutateAsync({
                contentUuid: content.uuid,
                data: {
                    progress_percent: 100,
                    completed: true,
                    position: result
                        ? {
                              quiz_answers: result.answers,
                              score: result.score,
                              passed: true,
                          }
                        : undefined,
                    courseUuid,
                },
            } as any);
        } catch (error) {
            console.error('Failed to save quiz progress:', error);
        }
        refreshProgress();
    };

    /* ---- Derived view models ---- */
    const activeContent =
        currentItem?.type === 'content' ? (currentItem.item as ContentWithProgress) : null;
    const activeAssignment =
        currentItem?.type === 'assignment' ? (currentItem.item as Assignment) : null;
    const isLocked =
        !!currentItem && data.moduleAvailability[currentItem.moduleUuid] === false;
    const isCurrentContentCompleted = !!activeContent && data.completedContents.has(activeContent.uuid);
    const latestSubmissionForActive = useMemo(
        () =>
            activeAssignment
                ? getLatestSubmission(data.submissions, activeAssignment.uuid)
                : undefined,
        [activeAssignment, data.submissions]
    );

    /* ---- Loading / error / empty states ---- */
    if (data.isLoading) {
        return (
            <div className="flex h-[80vh] items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        );
    }

    if (data.isCourseNotFound || !data.course) {
        return (
            <div className="flex h-[80vh] flex-col items-center justify-center gap-4">
                <p className="text-muted-foreground">Course not found</p>
                <Button onClick={() => navigate('/registrations?tab=courses')}>
                    Back to My Courses
                </Button>
            </div>
        );
    }

    if (data.isEnrollmentBlocked) {
        return (
            <div className="flex h-[80vh] flex-col items-center justify-center gap-4 text-center">
                <p className="text-muted-foreground">You are not enrolled in this course yet.</p>
                <div className="flex gap-2">
                    <Button onClick={() => navigate('/registrations?tab=courses')}>
                        Back to My Courses
                    </Button>
                    {data.course.slug && (
                        <Button
                            variant="outline"
                            onClick={() => navigate(`/courses/${data.course!.slug}`)}
                        >
                            View Course Page
                        </Button>
                    )}
                </div>
            </div>
        );
    }

    // Match the legacy redirect for non-enrolled learners hitting /learn/...
    if (data.isNotEnrolled) {
        navigate(`/courses/${data.course.slug || courseUuid}`, { replace: true });
        return null;
    }

    return (
        <div className="flex h-[calc(100vh-4rem)] overflow-hidden">
            <PlayerSidebar
                course={data.course}
                progressPercent={data.progressPercent}
                sessions={data.sessions}
                modules={data.modules as ModuleWithContents[]}
                expandedModules={expandedModules}
                onToggleModule={toggleModule}
                completedContents={data.completedContents}
                moduleAvailability={data.moduleAvailability}
                submissions={data.submissions}
                currentItem={currentItem}
                onSelectContent={selectContent}
                onSelectAssignment={selectAssignment}
            />

            <div className="flex-1 flex flex-col overflow-hidden">
                {activeContent || activeAssignment ? (
                    <>
                        <PlayerHeader
                            activeContent={activeContent}
                            activeAssignment={activeAssignment}
                            isCurrentContentCompleted={isCurrentContentCompleted}
                            hasAnnouncements={data.announcements.length > 0}
                            onOpenDiscussion={() => setShowDiscussion(true)}
                            onOpenAnnouncements={() => setShowAnnouncements(true)}
                            onMarkComplete={markComplete}
                            onAdvanceToNext={advanceToNext}
                        />
                        <div className="flex-1 overflow-y-auto p-6">
                            <PlayerContent
                                activeContent={activeContent}
                                activeAssignment={activeAssignment}
                                isLocked={isLocked}
                                contentProgressMap={data.contentProgressMap}
                                latestSubmissionForActive={latestSubmissionForActive}
                                onQuizComplete={handleQuizComplete}
                            />
                        </div>
                    </>
                ) : (
                    <div className="flex-1 overflow-y-auto p-6">
                        <div className="max-w-4xl mx-auto">
                            {/* Sessions are rendered in the sidebar (two-track
                                layout). The empty-state branch only fires for
                                pure-live courses with no sessions yet — keep
                                that, drop the duplicate SessionsPanel render. */}
                            {data.course.format === 'live' && data.sessions.length === 0 ? (
                                <div className="text-center py-12">
                                    <Award className="h-16 w-16 mx-auto text-muted-foreground/50 mb-4" />
                                    <h3 className="text-lg font-medium mb-2">
                                        No sessions scheduled yet
                                    </h3>
                                    <p className="text-muted-foreground">
                                        Live sessions will appear here once the instructor schedules them.
                                    </p>
                                </div>
                            ) : (
                                <div className="text-center py-12">
                                    <Award className="h-16 w-16 mx-auto text-muted-foreground/50 mb-4" />
                                    <h3 className="text-lg font-medium mb-2">
                                        {data.sessions.length > 0
                                            ? 'Continue Learning'
                                            : 'No content selected'}
                                    </h3>
                                    <p className="text-muted-foreground">
                                        {data.course.format === 'live'
                                            ? 'Join an upcoming live session above, or watch a past recording.'
                                            : data.sessions.length > 0
                                              ? 'Join a live session above or select a lesson from the sidebar.'
                                              : 'Select a lesson from the sidebar to begin.'}
                                    </p>
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>

            <PlayerDialogs
                courseUuid={courseUuid}
                currentUserUuid={currentUserUuid}
                announcements={data.announcements}
                showAnnouncements={showAnnouncements}
                onAnnouncementsOpenChange={setShowAnnouncements}
                showDiscussion={showDiscussion}
                onDiscussionOpenChange={setShowDiscussion}
            />
        </div>
    );
}
