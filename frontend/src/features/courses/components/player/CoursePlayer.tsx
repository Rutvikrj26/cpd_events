import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { Award, Loader2 } from 'lucide-react';
import { Button } from '@/shared/ui/button';
import { useToast } from '@/shared/ui/use-toast';

import {
    useCoursePlayerBootstrap,
    isGranted,
    isPendingApproval,
    isRedirect,
    type CoursePlayerGranted,
} from '../../hooks/useCoursePlayerBootstrap';
import { useUpdateContentProgress, courseKeys } from '../../hooks';
import type { Assignment, AssignmentSubmission } from '@/api/courses/types';
import { PlayerSidebar } from './PlayerSidebar';
import { PlayerHeader } from './PlayerHeader';
import { PlayerContent } from './PlayerContent';
import { PlayerDialogs } from './PlayerDialogs';
import { PendingApprovalShell } from './PendingApprovalShell';
import type { CourseItem } from './types';
import type { QuizResult } from '../content-viewers/QuizTaker';

interface CoursePlayerProps {
    courseUuid: string;
    /** Pass-through from the page so we don't import features/auth. */
    currentUserUuid?: string;
}

/**
 * CoursePlayer — top-level orchestrator for the learner's course player.
 *
 * Bootstraps via a single typed fetch. The response is one of three
 * discriminated shapes (see `useCoursePlayerBootstrap`); we exhaustively
 * switch on `access.kind`:
 *
 *   - `granted`            → render the full <CoursePlayerGrantedShell />
 *   - `pending_approval`   → render <PendingApprovalShell />
 *   - `redirect_to_detail` → navigate to /courses/{slug}; the catalog page
 *                            handles the actual CTA (purchase / sign in /
 *                            "registration opens at ..." / etc.).
 *
 * No 6-fetch composition, no per-resource 403 spam, no boolean cascade
 * over four flags. The previous incarnation lived in
 * `useCoursePlayerData.ts` and is replaced wholesale by this hook + this
 * dispatcher.
 */
export function CoursePlayer({ courseUuid, currentUserUuid }: CoursePlayerProps) {
    const navigate = useNavigate();
    const { data, isLoading, isError } = useCoursePlayerBootstrap(courseUuid);

    /* ---- Loading / error sentinels ---- */
    if (isLoading) {
        return (
            <div className="flex h-[80vh] items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        );
    }
    if (isError || !data) {
        return (
            <div className="flex h-[80vh] flex-col items-center justify-center gap-4">
                <p className="text-muted-foreground">Course not found</p>
                <Button onClick={() => navigate('/registrations?tab=courses')}>
                    Back to My Courses
                </Button>
            </div>
        );
    }

    /* ---- Discriminated dispatch ---- */
    if (isPendingApproval(data)) {
        return <PendingApprovalShell data={data} />;
    }

    if (isRedirect(data)) {
        // The catalog page is the source of truth for the CTA in every
        // not-granted-but-not-pending case (paid, window closed, dropped,
        // expired, just-not-enrolled). Replace the route so the back
        // button doesn't bounce the user back into the player.
        navigate(`/courses/${data.access.slug}`, { replace: true });
        return null;
    }

    if (isGranted(data)) {
        return <CoursePlayerGrantedShell data={data} courseUuid={courseUuid} />;
    }

    // Exhaustiveness guard. If a new access kind ships and someone forgets
    // to update this dispatch, TypeScript narrows `data` to `never` and
    // this branch becomes a typecheck error at the assignment line above.
    const _exhaustive: never = data;
    return _exhaustive;
}

// =============================================================================
// Granted shell — the actual player UI, rendered only when access.kind === 'granted'.
// =============================================================================

interface GrantedShellProps {
    data: CoursePlayerGranted;
    courseUuid: string;
}

function getLatestSubmission(
    submissions: AssignmentSubmission[],
    assignmentUuid: string,
): AssignmentSubmission | undefined {
    return submissions
        .filter((s) => s.assignment === assignmentUuid)
        .sort((a, b) => (b.attempt_number || 0) - (a.attempt_number || 0))[0];
}

function CoursePlayerGrantedShell({ data, courseUuid }: GrantedShellProps) {
    const navigate = useNavigate();
    const { toast } = useToast();
    const queryClient = useQueryClient();
    const updateProgress = useUpdateContentProgress();

    /* ---- Derived view models from the bootstrap payload ----
     *
     * The bootstrap exposes `module_progress` as a flat array; we derive
     * the cross-cutting views the UI needs (availability map, completed
     * set, content_progress map) once instead of recomputing per-render.
     */
    const moduleAvailability = useMemo(() => {
        const map: Record<string, boolean> = {};
        for (const slice of data.module_progress) {
            map[slice.module_uuid] = slice.is_available;
        }
        return map;
    }, [data.module_progress]);

    const completedContents = useMemo(() => {
        const set = new Set<string>();
        for (const slice of data.module_progress) {
            for (const uuid of slice.completed_content_uuids) {
                set.add(uuid);
            }
        }
        return set;
    }, [data.module_progress]);

    const progressPercent = useMemo(() => {
        if (data.view_state?.kind === 'completed') return 100;
        if (data.view_state?.kind === 'in_progress') return data.view_state.percent ?? 0;
        return 0;
    }, [data.view_state]);

    // Reshape modules into the legacy `ModuleWithContents` shape the
    // PlayerSidebar still consumes — keeps that component's contract
    // stable while the hook layer changed underneath. Sidebar refactor
    // is a follow-up; not blocking the toast-spam fix.
    const modules = useMemo(
        () =>
            data.modules.map((m: any) => ({
                ...m,
                contents: m.module?.contents ?? [],
            })),
        [data.modules],
    );

    /* ---- Local UI state ---- */
    const [currentItem, setCurrentItem] = useState<CourseItem | null>(null);
    const [expandedModules, setExpandedModules] = useState<Record<string, boolean>>({});
    const [showAnnouncements, setShowAnnouncements] = useState(false);
    const [showDiscussion, setShowDiscussion] = useState(false);
    const hasAutoSelectedRef = useRef(false);

    /* ---- Auto-select first incomplete content on first hydrate ---- */
    useEffect(() => {
        if (hasAutoSelectedRef.current) return;
        if (modules.length === 0) return;

        let target: { content: any; moduleUuid: string } | null = null;
        for (const mod of modules) {
            const moduleUuid = mod.module?.uuid || mod.uuid;
            if (moduleAvailability[moduleUuid] === false) continue;
            for (const content of mod.contents || []) {
                if (!completedContents.has(content.uuid)) {
                    target = { content, moduleUuid };
                    break;
                }
            }
            if (target) break;
        }
        // Fallback: first content of first module that has any.
        if (!target) {
            const firstWith = modules.find((m: any) => (m.contents?.length ?? 0) > 0);
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
    }, [modules, moduleAvailability, completedContents]);

    /* ---- Selection handlers ---- */
    const toggleModule = (moduleUuid: string) => {
        setExpandedModules((prev) => ({ ...prev, [moduleUuid]: !prev[moduleUuid] }));
    };

    const selectContent = (content: any, moduleUuid: string) => {
        if (moduleAvailability[moduleUuid] === false) return;
        setCurrentItem({ type: 'content', item: content, moduleUuid });
    };

    const selectAssignment = (assignment: Assignment, moduleUuid: string) => {
        if (moduleAvailability[moduleUuid] === false) return;
        setCurrentItem({ type: 'assignment', item: assignment, moduleUuid });
    };

    /* ---- Progress / mark-complete ---- */
    const refreshAfterProgress = () => {
        // Mark-complete invalidates the bootstrap so the next paint reflects
        // newly-unlocked modules + updated view_state. The legacy narrow
        // `progress` and `modules` keys are no longer in the data flow.
        queryClient.invalidateQueries({
            queryKey: ['courses', 'player-bootstrap', courseUuid],
        });
        // Keep the legacy enrollments-list key fresh so the My Learning
        // page reflects status / completion changes when the user
        // navigates back.
        queryClient.invalidateQueries({ queryKey: courseKeys.enrollments() });
    };

    const advanceToNext = () => {
        if (!currentItem || currentItem.type !== 'content') return;
        const moduleIndex = modules.findIndex(
            (m: any) => (m.module?.uuid || m.uuid) === currentItem.moduleUuid,
        );
        const currentModule = modules[moduleIndex];
        const contentIndex =
            currentModule?.contents?.findIndex((c: any) => c.uuid === currentItem.item.uuid) ?? -1;

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
        for (let i = moduleIndex + 1; i < modules.length; i++) {
            const nextUuid = modules[i].module?.uuid || modules[i].uuid;
            if (
                moduleAvailability[nextUuid] !== false &&
                modules[i].contents &&
                modules[i].contents.length > 0
            ) {
                setCurrentItem({
                    type: 'content',
                    item: modules[i].contents[0],
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
            refreshAfterProgress();
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

    const handleQuizComplete = async (content: any, result: QuizResult | undefined) => {
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
        refreshAfterProgress();
    };

    /* ---- Active item / lock state ---- */
    const activeContent = currentItem?.type === 'content' ? currentItem.item : null;
    const activeAssignment = currentItem?.type === 'assignment' ? (currentItem.item as Assignment) : null;
    const isLocked = !!currentItem && moduleAvailability[currentItem.moduleUuid] === false;
    const isCurrentContentCompleted = !!activeContent && completedContents.has(activeContent.uuid);

    // Submissions are not yet returned in the bootstrap (Phase 1.5). For
    // now, the player surfaces the latest submission per assignment via a
    // separate side-fetch in PlayerContent. Pass an empty array — the
    // component already handles the empty case gracefully.
    const submissions: AssignmentSubmission[] = [];
    const latestSubmissionForActive = useMemo(
        () =>
            activeAssignment
                ? getLatestSubmission(submissions, activeAssignment.uuid)
                : undefined,
        [activeAssignment, submissions],
    );

    // contentProgressMap: legacy shape derived from module_progress slices.
    // Kept minimal for now — only the fields PlayerContent actually reads.
    const contentProgressMap = useMemo(() => {
        const map: Record<string, any> = {};
        for (const uuid of completedContents) {
            map[uuid] = { status: 'completed', progress_percent: 100 };
        }
        return map;
    }, [completedContents]);

    return (
        <div className="flex h-[calc(100vh-4rem)] overflow-hidden">
            <PlayerSidebar
                course={data.course as any}
                progressPercent={progressPercent}
                sessions={(data.sessions ?? []) as any}
                modules={modules as any}
                expandedModules={expandedModules}
                onToggleModule={toggleModule}
                completedContents={completedContents}
                moduleAvailability={moduleAvailability}
                submissions={submissions}
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
                                contentProgressMap={contentProgressMap}
                                latestSubmissionForActive={latestSubmissionForActive}
                                onQuizComplete={handleQuizComplete}
                            />
                        </div>
                    </>
                ) : (
                    <div className="flex-1 overflow-y-auto p-6">
                        <div className="max-w-4xl mx-auto">
                            {(data.course as any).format === 'live' && (data.sessions ?? []).length === 0 ? (
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
                                <div className="text-center py-12 text-muted-foreground">
                                    Select a module item from the sidebar to begin.
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>

            <PlayerDialogs
                courseUuid={courseUuid}
                currentUserUuid={undefined}
                announcements={data.announcements as any}
                showAnnouncements={showAnnouncements}
                onAnnouncementsOpenChange={setShowAnnouncements}
                showDiscussion={showDiscussion}
                onDiscussionOpenChange={setShowDiscussion}
            />
        </div>
    );
}
