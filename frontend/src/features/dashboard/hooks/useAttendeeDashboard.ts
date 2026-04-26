import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getMyRegistrations } from '@/api/registrations';
import type { Registration } from '@/api/registrations/types';
import { getMyCertificates } from '@/api/certificates';
import type { Certificate } from '@/api/certificates/types';
import { getEnrollments } from '@/api/courses';
import { dashboardKeys } from './queryKeys';

/**
 * Active enrollment shape — matches whichever fields the backend
 * surfaces for /enrollments/. Loose-typed because the backend response
 * is heterogeneous depending on the user's roles.
 */
interface EnrollmentLike {
    uuid: string;
    course?: { uuid?: string; title?: string; format?: string; progress_percent?: number };
    course_uuid?: string;
    course_title?: string;
    status?: string;
    progress_percent?: number;
    last_accessed_at?: string;
    updated_at?: string;
    created_at?: string;
}

export interface ResumeCandidate {
    enrollmentUuid: string;
    courseUuid: string;
    courseTitle: string;
    progressPercent: number;
    lastAccessedAt: string | null;
    format?: string;
}

export interface AttendeeDashboardData {
    isLoading: boolean;
    isError: boolean;
    /** All confirmed event registrations. */
    confirmedRegistrations: Registration[];
    /** Future registrations only, sorted ascending by start date. */
    upcomingRegistrations: Registration[];
    /** Issued + valid certificates, newest first, capped at 3. */
    recentCertificates: Certificate[];
    /** Course to surface in the "Continue where you left off" hero. */
    resumeTarget: ResumeCandidate | null;
    /** Headline KPIs for the stat strip. */
    stats: {
        totalCredits: number;
        certificates: number;
        upcomingEvents: number;
        activeCourses: number;
    };
}

function pickResumeCandidate(enrollments: EnrollmentLike[]): ResumeCandidate | null {
    const active = enrollments
        .filter((e) => {
            const status = (e.status || '').toString().toUpperCase();
            return status === 'ACTIVE' || status === 'IN_PROGRESS' || status === 'PENDING';
        })
        .map<ResumeCandidate>((e) => ({
            enrollmentUuid: e.uuid,
            courseUuid: e.course?.uuid || e.course_uuid || '',
            courseTitle: e.course?.title || e.course_title || 'Continue your course',
            progressPercent: Number(e.progress_percent ?? e.course?.progress_percent ?? 0),
            lastAccessedAt: e.last_accessed_at || e.updated_at || e.created_at || null,
            format: e.course?.format,
        }))
        .filter((c) => c.courseUuid);

    if (active.length === 0) return null;
    active.sort((a, b) => {
        const aTime = a.lastAccessedAt ? new Date(a.lastAccessedAt).getTime() : 0;
        const bTime = b.lastAccessedAt ? new Date(b.lastAccessedAt).getTime() : 0;
        return bTime - aTime;
    });
    return active[0];
}

/**
 * useAttendeeDashboard — combines registrations, certificates, and
 * enrollments for the learner dashboard. All three queries share a
 * single feature key so invalidating `dashboardKeys.attendee()` refreshes
 * the page in one shot.
 */
export function useAttendeeDashboard(): AttendeeDashboardData {
    const registrationsQuery = useQuery({
        queryKey: [...dashboardKeys.attendee(), 'registrations'],
        queryFn: async () => (await getMyRegistrations()).results,
    });

    const certificatesQuery = useQuery({
        queryKey: [...dashboardKeys.attendee(), 'certificates'],
        queryFn: async () => {
            try {
                const r = await getMyCertificates();
                return r.results ?? [];
            } catch {
                return [] as Certificate[];
            }
        },
    });

    const enrollmentsQuery = useQuery<EnrollmentLike[]>({
        queryKey: [...dashboardKeys.attendee(), 'enrollments'],
        queryFn: async () => {
            try {
                return (await getEnrollments()) as EnrollmentLike[];
            } catch {
                return [];
            }
        },
    });

    const registrations = registrationsQuery.data ?? [];
    const certificates = certificatesQuery.data ?? [];
    const enrollments = enrollmentsQuery.data ?? [];

    const confirmedRegistrations = useMemo(
        () => registrations.filter((r) => r.status === 'confirmed'),
        [registrations]
    );

    const upcomingRegistrations = useMemo(
        () =>
            confirmedRegistrations
                .filter((r) => new Date(r.event.starts_at) > new Date())
                .sort(
                    (a, b) =>
                        new Date(a.event.starts_at).getTime() -
                        new Date(b.event.starts_at).getTime()
                ),
        [confirmedRegistrations]
    );

    const recentCertificates = useMemo(
        () =>
            certificates
                .filter((c) => c.is_valid !== false && c.status !== 'revoked')
                .sort((a, b) => {
                    const aDate = new Date(
                        (a as any).issued_at || (a as any).created_at || 0
                    ).getTime();
                    const bDate = new Date(
                        (b as any).issued_at || (b as any).created_at || 0
                    ).getTime();
                    return bDate - aDate;
                })
                .slice(0, 3),
        [certificates]
    );

    const resumeTarget = useMemo(() => pickResumeCandidate(enrollments), [enrollments]);

    const stats = useMemo(
        () => ({
            totalCredits: confirmedRegistrations
                .filter((r) => r.attended || new Date(r.event.starts_at) <= new Date())
                .reduce((acc, r) => acc + Number(r.event.cpd_credit_value || 0), 0),
            certificates: certificates.filter(
                (c) => c.is_valid !== false && c.status !== 'revoked'
            ).length,
            upcomingEvents: confirmedRegistrations.filter(
                (r) => new Date(r.event.starts_at) > new Date()
            ).length,
            activeCourses: enrollments.filter((e) => {
                const s = (e.status || '').toString().toUpperCase();
                return s === 'ACTIVE' || s === 'IN_PROGRESS';
            }).length,
        }),
        [confirmedRegistrations, certificates, enrollments]
    );

    return {
        isLoading:
            registrationsQuery.isLoading ||
            certificatesQuery.isLoading ||
            enrollmentsQuery.isLoading,
        isError:
            registrationsQuery.isError &&
            certificatesQuery.isError &&
            enrollmentsQuery.isError,
        confirmedRegistrations,
        upcomingRegistrations,
        recentCertificates,
        resumeTarget,
        stats,
    };
}
