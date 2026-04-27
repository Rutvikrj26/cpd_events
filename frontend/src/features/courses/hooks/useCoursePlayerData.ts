import { useMemo } from 'react';
import { useQuery, useQueries } from '@tanstack/react-query';
import {
    getCourse,
    getCourseProgress,
    getCourseAnnouncements,
    getCourseSessions,
    getEnrollments,
    getMySubmissions,
} from '@/api/courses';
import { getCourseModules, getModuleContents } from '@/api/courses/modules';
import type {
    Course,
    CourseModule,
    CourseAnnouncement,
    CourseSession,
    AssignmentSubmission,
} from '@/api/courses/types';
import { deriveProgressDisplay } from '@/lib/progress';
import { courseKeys } from './queryKeys';

export interface ContentWithProgress {
    uuid: string;
    title: string;
    content_type: 'text' | 'video' | 'document' | 'quiz' | 'lesson' | 'external';
    content_data?: any;
    file?: string;
    duration_minutes?: number;
    is_required: boolean;
    order: number;
    completed?: boolean;
}

export interface ModuleWithContents extends CourseModule {
    contents: ContentWithProgress[];
}

export interface CoursePlayerData {
    course: Course | undefined;
    modules: ModuleWithContents[];
    sessions: CourseSession[];
    announcements: CourseAnnouncement[];
    submissions: AssignmentSubmission[];
    completedContents: Set<string>;
    moduleAvailability: Record<string, boolean>;
    contentProgressMap: Record<string, any>;
    enrollmentStatus: string;
    enrollmentProgress: number;
    progressPercent: number;
    /** True if the learner is not enrolled in this course. */
    isNotEnrolled: boolean;
    isLoading: boolean;
    isError: boolean;
    isEnrollmentBlocked: boolean;
    isCourseNotFound: boolean;
}

/**
 * useCoursePlayerData — composite hook that bundles every fetch the
 * `<CoursePlayer>` shell needs into a single hook call.
 *
 * Access model:
 *   The course player has two "has access" paths:
 *     1. Learner with an enrollment in (`active`, `completed`).
 *     2. Staff (`course.user_role` is non-null — manager or instructor).
 *   `pending` / `dropped` / `expired` enrollments do NOT grant access. The
 *   backend rejects content fetches with 403 in those cases.
 *
 * Fetch ordering (data dependencies, not parallel-everything):
 *   1. Foundation (parallel): course detail (silent — 404/403 surface
 *      inline) + enrollments. Both are needed to compute access.
 *   2. Once we know access:
 *      - No access → bail. Don't fire any per-course secondary requests.
 *        Inline UI shows the "not enrolled" / "pending approval" state.
 *      - Access → fire progress, modules, announcements, sessions
 *        (live/hybrid only), submissions in parallel.
 *   3. Per-module content fetches WAIT for progress to settle, then run
 *      one query per *available* module. Locked modules are skipped — the
 *      backend rejects them with 403 and the global toast would fire on
 *      every one.
 *
 * If progress errors after we decided to fetch (rare staff-preview races),
 * we fall back to fetching every module — the backend's
 * ``can_manage``/``can_instruct`` paths in
 * ``learning.views.ModuleContentViewSet.get_queryset`` return the full
 * curriculum for those callers without running the prereq gate.
 */
export function useCoursePlayerData(courseUuid: string | undefined): CoursePlayerData {
    /* -------- Foundation: course detail + enrollments -------- */
    // These two are the only fetches that fire unconditionally (besides the
    // user-scoped submissions list). Together they answer "does the user
    // have access to this course?" — every other request is gated on that.

    const courseQuery = useQuery<Course>({
        queryKey: courseUuid ? courseKeys.detail(courseUuid) : ['courses', 'detail', 'noop'],
        queryFn: () => getCourse(courseUuid!, { silent: true }),
        enabled: Boolean(courseUuid),
        staleTime: 1000 * 30,
        retry: false,
    });

    const enrollmentsQuery = useQuery({
        queryKey: courseKeys.enrollments(),
        queryFn: getEnrollments,
        staleTime: 1000 * 60,
        retry: false,
    });

    /* -------- Access derivation -------- */
    // Two valid access paths:
    //   1. Staff: course.user_role is non-null (manager / instructor).
    //   2. Learner: enrollment for this course in {active, completed}.
    // pending / dropped / expired enrollments do NOT grant access — the
    // backend's ModuleContentViewSet.get_queryset returns 403 for those.
    const isStaff = Boolean((courseQuery.data as any)?.user_role);
    const enrollment = useMemo(() => {
        if (!enrollmentsQuery.data || !courseUuid) return undefined;
        return (enrollmentsQuery.data as any[]).find(
            (e: any) => e.course?.uuid === courseUuid,
        );
    }, [enrollmentsQuery.data, courseUuid]);
    const enrollmentGrantsAccess =
        enrollment != null && ['active', 'completed'].includes(enrollment.status);

    const foundationSettled =
        courseQuery.isFetched && enrollmentsQuery.isFetched;
    const hasAccess = foundationSettled && (isStaff || enrollmentGrantsAccess);

    /* -------- Secondary fetches — gated on hasAccess -------- */
    const progressQuery = useQuery({
        queryKey: courseUuid ? courseKeys.progress(courseUuid) : ['courses', 'progress', 'noop'],
        queryFn: () => getCourseProgress(courseUuid!),
        enabled: Boolean(courseUuid) && hasAccess,
        retry: false,
    });

    const modulesQuery = useQuery({
        queryKey: courseUuid ? courseKeys.modules(courseUuid) : ['courses', 'modules', 'noop'],
        queryFn: () => getCourseModules(courseUuid!),
        enabled: Boolean(courseUuid) && hasAccess,
        staleTime: 1000 * 30,
    });

    const announcementsQuery = useQuery({
        queryKey: courseUuid
            ? courseKeys.announcements(courseUuid)
            : ['courses', 'announcements', 'noop'],
        queryFn: () => getCourseAnnouncements(courseUuid!),
        enabled: Boolean(courseUuid) && hasAccess,
        staleTime: 1000 * 60,
    });

    const sessionsFromProgress = (progressQuery.data as any)?.sessions;
    const sessionsQuery = useQuery({
        queryKey: courseUuid ? courseKeys.sessions(courseUuid) : ['courses', 'sessions', 'noop'],
        queryFn: () => getCourseSessions(courseUuid!),
        enabled:
            Boolean(courseUuid) &&
            hasAccess &&
            (courseQuery.data?.format === 'live' || courseQuery.data?.format === 'hybrid') &&
            // The progress endpoint already returns sessions hydrated with
            // attendance/recording info for the current user. Prefer those —
            // only fall back to the anonymous list endpoint if progress failed.
            !Array.isArray(sessionsFromProgress),
        staleTime: 1000 * 30,
    });

    // Submissions are user-scoped (not course-scoped) and never 403, so we
    // can fetch them regardless of access. The course tab will filter to
    // the relevant course's assignments anyway.
    const submissionsQuery = useQuery<AssignmentSubmission[]>({
        queryKey: courseKeys.mySubmissions(),
        queryFn: getMySubmissions,
        staleTime: 1000 * 60,
    });

    /* -------- Module-content fetches via useQueries --------
     *
     * Strict ordering: progress must settle before we decide what to fetch.
     * - If progress returned data, the availability of each module is the
     *   value the backend reported (`is_available` per module).
     * - If progress errored, we treat every module as fetchable and let the
     *   backend permission check decide; this is the staff-preview path
     *   where the user has `can_manage` / `can_instruct` and the prereq
     *   gate is skipped server-side.
     * - While progress is still loading, we fetch nothing. This is the
     *   only correct default — the alternative ("default available") fired
     *   guaranteed 403s on every locked module.
     */
    const progressSettled = progressQuery.isFetched;

    const availabilityFromProgress = useMemo<Record<string, boolean>>(() => {
        const map: Record<string, boolean> = {};
        if (progressQuery.data?.modules) {
            progressQuery.data.modules.forEach((m: any) => {
                const mUuid = m.module?.uuid || m.module?.id;
                if (mUuid) map[mUuid] = Boolean(m.is_available);
            });
        } else if (progressQuery.isError && modulesQuery.data) {
            // Progress endpoint failed (e.g. staff preview without enrollment).
            // Mark every module as fetchable; the backend will gate via roles.
            modulesQuery.data.forEach((m: any) => {
                const mUuid = m.module?.uuid || m.uuid;
                if (mUuid) map[mUuid] = true;
            });
        }
        return map;
    }, [progressQuery.data, progressQuery.isError, modulesQuery.data]);

    const moduleUuidsToFetch = useMemo(() => {
        // Hard guard: never fire content fetches before progress has spoken.
        if (!progressSettled || !modulesQuery.data) return [] as string[];
        return modulesQuery.data
            .map((m: any) => m.module?.uuid || m.uuid)
            .filter((uuid: string) => uuid && availabilityFromProgress[uuid] === true);
    }, [progressSettled, modulesQuery.data, availabilityFromProgress]);

    const contentQueries = useQueries({
        queries: moduleUuidsToFetch.map((moduleUuid) => ({
            queryKey: courseKeys.moduleContents(moduleUuid),
            queryFn: () => getModuleContents(courseUuid!, moduleUuid),
            enabled: Boolean(courseUuid),
            staleTime: 1000 * 30,
            retry: false,
        })),
    });

    /* -------- Derived state -------- */
    const completedContents = useMemo(() => {
        const set = new Set<string>();
        progressQuery.data?.modules?.forEach((mod: any) => {
            mod.content_progress?.forEach((cp: any) => {
                if (cp.status === 'completed') set.add(cp.content);
            });
        });
        return set;
    }, [progressQuery.data]);

    const contentProgressMap = useMemo(() => {
        const map: Record<string, any> = {};
        progressQuery.data?.modules?.forEach((mod: any) => {
            mod.content_progress?.forEach((cp: any) => {
                map[cp.content] = cp;
            });
        });
        return map;
    }, [progressQuery.data]);

    const modules = useMemo<ModuleWithContents[]>(() => {
        if (!modulesQuery.data) return [];
        const contentsByModule: Record<string, ContentWithProgress[]> = {};
        moduleUuidsToFetch.forEach((mUuid, idx) => {
            const data = contentQueries[idx]?.data;
            if (Array.isArray(data)) {
                contentsByModule[mUuid] = [...data].sort(
                    (a: any, b: any) => a.order - b.order
                ) as ContentWithProgress[];
            }
        });
        const sorted = [...modulesQuery.data].sort((a: any, b: any) => a.order - b.order);
        return sorted.map((mod: any) => {
            const mUuid = mod.module?.uuid || mod.uuid;
            return {
                ...mod,
                contents: contentsByModule[mUuid] ?? [],
            } as ModuleWithContents;
        });
        // contentQueries identity changes every render — depending on the data
        // payloads (mapped above) keeps this stable.
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [modulesQuery.data, moduleUuidsToFetch, ...contentQueries.map((q) => q.data)]);

    /* -------- Sessions: prefer progress.sessions when available -------- */
    const sessions = useMemo<CourseSession[]>(() => {
        if (Array.isArray(sessionsFromProgress)) return sessionsFromProgress;
        if (Array.isArray(sessionsQuery.data)) {
            return sessionsQuery.data.filter((s) => s.is_published);
        }
        return [];
    }, [sessionsFromProgress, sessionsQuery.data]);

    /* -------- Submissions: scope to this course's assignments -------- */
    const submissions = useMemo<AssignmentSubmission[]>(() => {
        const all = submissionsQuery.data ?? [];
        const assignmentIds = modules
            .flatMap((mod) => mod.module?.assignments || [])
            .map((a) => a.uuid);
        if (assignmentIds.length === 0) return [];
        return all.filter((s) => assignmentIds.includes(s.assignment));
    }, [submissionsQuery.data, modules]);

    /* -------- Enrollment gating -------- */
    const enrollmentStatus = (progressQuery.data as any)?.enrollment?.status ?? '';
    const enrollmentProgress = (progressQuery.data as any)?.enrollment?.progress_percent ?? 0;

    const progressDisplay = deriveProgressDisplay({
        status: enrollmentStatus,
        progress_percent: enrollmentProgress,
    });

    // "Not enrolled" = foundation has settled AND we don't have access via
    // either path. Drives the inline "You are not enrolled / Pending
    // approval" banner. A pending/dropped/expired enrollment counts as
    // "not enrolled" for the purposes of accessing course content.
    const isNotEnrolled = foundationSettled && !hasAccess && !enrollmentsQuery.isError;

    /* -------- 403 / 404 sentinels -------- */
    const courseStatus = (courseQuery.error as any)?.response?.status;
    const isCourseNotFound = courseStatus === 404;
    // 403 on the course detail or progress endpoint indicates the user is not
    // enrolled (or has been removed). Match the legacy behavior of the page.
    const isEnrollmentBlocked =
        courseStatus === 403 || (progressQuery.error as any)?.response?.status === 403;

    return {
        course: courseQuery.data,
        modules,
        sessions,
        announcements: announcementsQuery.data ?? [],
        submissions,
        completedContents,
        moduleAvailability: availabilityFromProgress,
        contentProgressMap,
        enrollmentStatus,
        enrollmentProgress,
        progressPercent: progressDisplay.percent,
        isNotEnrolled,
        isLoading:
            // Foundation phase — must settle before we know if there's access.
            (Boolean(courseUuid) && !foundationSettled) ||
            // Once we know access, the secondary queries kick in.
            (hasAccess && modulesQuery.isLoading) ||
            (hasAccess && Boolean(courseUuid) && !progressSettled) ||
            // Wait for the per-module content queries to settle on first hydrate.
            (moduleUuidsToFetch.length > 0 &&
                contentQueries.some((q) => q.isLoading && q.fetchStatus !== 'idle')),
        isError: courseQuery.isError && courseStatus !== 403 && courseStatus !== 404,
        isEnrollmentBlocked,
        isCourseNotFound,
    };
}
