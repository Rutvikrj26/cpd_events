import React, { useCallback, useEffect, useState } from 'react';
import { Award, Loader2, RefreshCcw } from 'lucide-react';
import { Button } from '@/shared/ui/button';
import { Badge } from '@/shared/ui/badge';
import { Card } from '@/shared/ui/card';
import { toast } from 'sonner';
import client from '@/api/client';
import {
    issueCertificatesGeneric,
    revokeCertificateDirect,
    CertificateIssueResult,
} from '@/api/certificates';

interface CourseEnrollmentRow {
    uuid: string;
    user_name?: string | null;
    user_email: string;
    status: string;
    progress_percent: number;
    certificate_issued: boolean;
    completed_at?: string;
}

interface CertificatesTabProps {
    courseUuid: string;
}

export function CertificatesTab({ courseUuid }: CertificatesTabProps) {
    const [enrollments, setEnrollments] = useState<CourseEnrollmentRow[]>([]);
    const [loading, setLoading] = useState(true);
    const [busyUuid, setBusyUuid] = useState<string | null>(null);

    const loadEnrollments = useCallback(async () => {
        setLoading(true);
        try {
            const response = await client.get(`/courses/${courseUuid}/enrollments/`);
            const data = Array.isArray(response.data)
                ? response.data
                : response.data.results || [];
            setEnrollments(data);
        } catch (error) {
            console.error('Failed to load enrollments', error);
            toast.error('Failed to load enrollments');
        } finally {
            setLoading(false);
        }
    }, [courseUuid]);

    useEffect(() => {
        loadEnrollments();
    }, [loadEnrollments]);

    const summarize = (result: CertificateIssueResult) => {
        if (result.issued_count > 0 && result.skipped_count === 0) {
            toast.success(`Issued ${result.issued_count} certificate${result.issued_count === 1 ? '' : 's'}`);
        } else if (result.issued_count > 0 && result.skipped_count > 0) {
            toast.success(`Issued ${result.issued_count}, skipped ${result.skipped_count}`, {
                description: result.skipped
                    .slice(0, 3)
                    .map(s => s.reason + (s.detail ? `: ${s.detail}` : ''))
                    .join('\n'),
            });
        } else if (result.skipped_count > 0) {
            toast.error('No certificates issued', {
                description: result.skipped
                    .slice(0, 3)
                    .map(s => s.reason + (s.detail ? `: ${s.detail}` : ''))
                    .join('\n'),
            });
        }
    };

    const handleIssue = async (enrollmentUuid: string, force = false) => {
        setBusyUuid(enrollmentUuid);
        try {
            const result = await issueCertificatesGeneric({
                course_enrollment_uuids: [enrollmentUuid],
                force,
            });
            summarize(result);
            await loadEnrollments();
        } catch (error: any) {
            toast.error(error?.response?.data?.detail || 'Failed to issue certificate');
        } finally {
            setBusyUuid(null);
        }
    };

    const handleRevoke = async (enrollmentUuid: string) => {
        const reason = window.prompt('Reason for revocation?');
        if (!reason) return;
        setBusyUuid(enrollmentUuid);
        try {
            // Fetch the enrollment's current certificate UUID via a single list query.
            const resp = await client.get('/certificates/organization/', {
                params: { course: courseUuid, search: enrollmentUuid },
            });
            const cert = (resp.data.results || []).find(
                (c: any) => c.course_enrollment?.uuid === enrollmentUuid && c.status === 'active'
            );
            if (!cert) {
                // Fall back to finding by the enrollment's user/email via the issued flag.
                const row = enrollments.find(e => e.uuid === enrollmentUuid);
                const fallback = (resp.data.results || []).find(
                    (c: any) =>
                        c.certificate_data?.attendee_email === row?.user_email &&
                        c.status === 'active'
                );
                if (!fallback) {
                    toast.error('Could not find an active certificate for this enrollment');
                    return;
                }
                await revokeCertificateDirect(fallback.uuid, reason);
            } else {
                await revokeCertificateDirect(cert.uuid, reason);
            }
            toast.success('Certificate revoked');
            await loadEnrollments();
        } catch (error: any) {
            toast.error(error?.response?.data?.detail || 'Failed to revoke certificate');
        } finally {
            setBusyUuid(null);
        }
    };

    // Status is the only authoritative completion signal (see
    // frontend/src/lib/progress.ts). progress_percent>=100 alone means
    // "awaiting review", not completed — those enrollments don't yet have
    // a certificate to issue/revoke.
    const completed = enrollments.filter(e => e.status === 'completed');

    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        );
    }

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <div>
                    <h3 className="text-lg font-semibold">Course certificates</h3>
                    <p className="text-sm text-muted-foreground">
                        Issue, re-issue, or revoke certificates for learners who have completed the course.
                    </p>
                </div>
                <Button variant="outline" size="sm" onClick={loadEnrollments}>
                    <RefreshCcw className="h-4 w-4 mr-2" /> Refresh
                </Button>
            </div>

            {completed.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 bg-muted/30 rounded-lg border border-dashed">
                    <Award className="h-10 w-10 text-muted-foreground mb-3" />
                    <p className="text-sm text-muted-foreground">
                        No learners have completed this course yet.
                    </p>
                </div>
            ) : (
                <Card>
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-border">
                            <thead className="bg-muted/50">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Learner</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Completed</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Status</th>
                                    <th className="px-6 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="bg-card divide-y divide-border">
                                {completed.map(row => (
                                    <tr key={row.uuid} className="hover:bg-muted/30">
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="text-sm font-medium text-foreground">
                                                {row.user_name || row.user_email}
                                            </div>
                                            <div className="text-xs text-muted-foreground">{row.user_email}</div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">
                                            {row.completed_at
                                                ? new Date(row.completed_at).toLocaleDateString()
                                                : '—'}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            {row.certificate_issued ? (
                                                <Badge variant="outline" className="text-success bg-success-subtle border-success">
                                                    Issued
                                                </Badge>
                                            ) : (
                                                <Badge variant="outline" className="text-muted-foreground bg-muted">
                                                    Not issued
                                                </Badge>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-2">
                                            {row.certificate_issued ? (
                                                <>
                                                    <Button
                                                        size="sm"
                                                        variant="outline"
                                                        disabled={busyUuid === row.uuid}
                                                        onClick={() => handleIssue(row.uuid, true)}
                                                    >
                                                        Re-issue
                                                    </Button>
                                                    <Button
                                                        size="sm"
                                                        variant="outline"
                                                        className="text-destructive border-destructive hover:bg-destructive/10"
                                                        disabled={busyUuid === row.uuid}
                                                        onClick={() => handleRevoke(row.uuid)}
                                                    >
                                                        Revoke
                                                    </Button>
                                                </>
                                            ) : (
                                                <Button
                                                    size="sm"
                                                    variant="outline"
                                                    disabled={busyUuid === row.uuid}
                                                    onClick={() => handleIssue(row.uuid)}
                                                >
                                                    Issue
                                                </Button>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </Card>
            )}
        </div>
    );
}
