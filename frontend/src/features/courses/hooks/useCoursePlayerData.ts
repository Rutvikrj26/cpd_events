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
 * `<CoursePlayer>` shell needs into a single hook call. Replaces the
 * 180-line imperative useEffect that the page used to run.
 *
 * Fetch order (parallel where possible):
 *   1. Course detail (silent — 404 surfaces inline, not a toast).
 *   2. Enrollments — used to gate access (redirect non-enrolled).
 *   3. Course progress — modules availability + content_progress.
 *   4. Course modules.
 *   5. Module contents — one query per available module via `useQueries`,
 *      so RQ caches each `moduleContents(uuid)` independently. Locked
 *      modules skip the fetch (would 403 anyway).
 *   6. Announcements + sessions + submissions in parallel.
 */
export function useCoursePlayerData(courseUuid: string | undefined): CoursePlayerData {
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

    const progressQuery = useQuery({
        queryKey: courseUuid ? courseKeys.progress(courseUuid) : ['courses', 'progress', 'noop'],
        queryFn: () => getCourseProgress(courseUuid!),
        enabled: Boolean(courseUuid),
        retry: false,
    });

    const modulesQuery = useQuery({
        queryKey: courseUuid ? courseKeys.modules(courseUuid) : ['courses', 'modules', 'noop'],
        queryFn: () => getCourseModules(courseUuid!),
        enabled: Boolean(courseUuid),
        staleTime: 1000 * 30,
    });

    const announcementsQuery = useQuery({
        queryKey: courseUuid
            ? courseKeys.announcements(courseUuid)
            : ['courses', 'announcements', 'noop'],
        queryFn: () => getCourseAnnouncements(courseUuid!),
        enabled: Boolean(courseUuid),
        staleTime: 1000 * 60,
    });

    const sessionsFromProgress = (progressQuery.data as any)?.sessions;
    const sessionsQuery = useQuery({
        queryKey: courseUuid ? courseKeys.sessions(courseUuid) : ['courses', 'sessions', 'noop'],
        queryFn: () => getCourseSessions(courseUuid!),
        enabled:
            Boolean(courseUuid) &&
            (courseQuery.data?.format === 'live' || courseQuery.data?.format === 'hybrid') &&
            // The progress endpoint already returns sessions hydrated with
            // attendance/recording info for the current user. Prefer those —
            // only fall back to the anonymous list endpoint if progress failed.
            !Array.isArray(sessionsFromProgress),
        staleTime: 1000 * 30,
    });

    const submissionsQuery = useQuery<AssignmentSubmission[]>({
        queryKey: courseKeys.mySubmissions(),
        queryFn: getMySubmissions,
        staleTime: 1000 * 60,
    });

    /* -------- Module-content fetches via useQueries -------- */
    // Compute availability from progress (or default-true if progress failed).
    const availabilityFromProgress = useMemo<Record<string, boolean>>(() => {
        const map: Record<string, boolean> = {};
        if (progressQuery.data?.modules) {
            progressQuery.data.modules.forEach((m: any) => {
                const mUuid = m.module?.uuid || m.module?.id;
                if (mUuid) map[mUuid] = m.is_available;
            });
        } else if (modulesQuery.data) {
            modulesQuery.data.forEach((m: any) => {
                const mUuid = m.module?.uuid || m.uuid;
                if (mUuid) map[mUuid] = true;
            });
        }
        return map;
    }, [progressQuery.data, modulesQuery.data]);

    const moduleUuidsToFetch = useMemo(() => {
        if (!modulesQuery.data) return [] as string[];
        return modulesQuery.data
            .map((m: any) => m.module?.uuid || m.uuid)
            .filter((uuid: string) => uuid && availabilityFromProgress[uuid] !== false);
    }, [modulesQuery.data, availabilityFromProgress]);

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

    const isNotEnrolled = useMemo(() => {
        // Only assert "not enrolled" once both course + enrollments have
        // resolved successfully. If enrollments errored (e.g. staff preview),
        // allow access.
        if (!courseQuery.data || !enrollmentsQuery.data) return false;
        if (enrollmentsQuery.isError) return false;
        const enrolled = (enrollmentsQuery.data as any[]).some(
            (e: any) =>
                e.course?.uuid === courseUuid &&
                ['active', 'completed'].includes(e.status)
        );
        return !enrolled;
    }, [courseUuid, courseQuery.data, enrollmentsQuery.data, enrollmentsQuery.isError]);

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
            courseQuery.isLoading ||
            modulesQuery.isLoading ||
            (Boolean(courseUuid) && progressQuery.isLoading) ||
            // Wait for the per-module content queries to settle on first hydrate
            (moduleUuidsToFetch.length > 0 &&
                contentQueries.some((q) => q.isLoading && q.fetchStatus !== 'idle')),
        isError: courseQuery.isError && courseStatus !== 403 && courseStatus !== 404,
        isEnrollmentBlocked,
        isCourseNotFound,
    };
}
