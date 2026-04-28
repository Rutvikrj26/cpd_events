import React, { useState } from 'react';
import { Award } from 'lucide-react';
import { Button } from '@/shared/ui/button';
import { Badge } from '@/shared/ui/badge';
import { Card } from '@/shared/ui/card';
import { Input } from '@/shared/ui/input';
import { ConfirmDialog } from '@/shared/ui/confirm-dialog';
import { toast } from 'sonner';
import { useEventAttendees, useIssueCertificates, useRevokeCertificate, useReissueCertificate } from '../../hooks';
import type { CertificateIssueResult } from '@/api/certificates';

interface EventCertificatesTabProps {
    eventUuid: string;
}

function summarizeIssueResult(result: CertificateIssueResult) {
    if (result.issued_count > 0 && result.skipped_count === 0) {
        toast.success(`Issued ${result.issued_count} certificate${result.issued_count === 1 ? '' : 's'}`);
    } else if (result.issued_count > 0 && result.skipped_count > 0) {
        toast.success(`Issued ${result.issued_count}, skipped ${result.skipped_count}`, {
            description: result.skipped
                .slice(0, 3)
                .map((s) => s.reason + (s.detail ? `: ${s.detail}` : ''))
                .join('\n'),
        });
    } else if (result.issued_count === 0 && result.skipped_count > 0) {
        toast.error(`No certificates issued — ${result.skipped_count} skipped`, {
            description: result.skipped
                .slice(0, 3)
                .map((s) => s.reason + (s.detail ? `: ${s.detail}` : ''))
                .join('\n'),
        });
    }
}

export function EventCertificatesTab({ eventUuid }: EventCertificatesTabProps) {
    const [revokeTarget, setRevokeTarget] = useState<any>(null);
    const [revokeReason, setRevokeReason] = useState('');

    const { data: attendees = [] } = useEventAttendees(eventUuid);
    const { mutate: issue } = useIssueCertificates(eventUuid);
    const { mutate: revoke, isPending: revokeLoading } = useRevokeCertificate(eventUuid);
    const { mutate: reissue } = useReissueCertificate(eventUuid);

    const activeAttendees = (attendees as any[]).filter((a) => a.status !== 'cancelled');
    // The "X verified attendees eligible" copy must mirror the actual issue-
    // gating predicate. The legacy `checkedInCount` prop included every
    // checked-in attendee regardless of whether they cleared the eligibility
    // criteria (attendance threshold, etc.), inflating the figure above the
    // number of rows that actually offered an "Issue" button.
    const eligibleCount = activeAttendees.filter(
        (a) => a.attendance_eligible && !a.certificate_uuid,
    ).length;

    const handleIssueCertificate = (registrationUuid: string) => {
        issue(
            { registration_uuids: [registrationUuid] },
            {
                onSuccess: (result) => summarizeIssueResult(result),
                onError: (e: any) =>
                    toast.error(e?.response?.data?.detail || 'Failed to issue certificate'),
            },
        );
    };

    const handleReissueCertificate = (registrationUuid: string) => {
        reissue(
            { registrationUuid },
            {
                onSuccess: (result) => summarizeIssueResult(result),
                onError: (e: any) =>
                    toast.error(e?.response?.data?.detail || 'Failed to re-issue certificate'),
            },
        );
    };

    const handleIssueAllCertificates = () => {
        issue(
            { issue_all_eligible: true },
            {
                onSuccess: (result) => summarizeIssueResult(result),
                onError: (e: any) =>
                    toast.error(e?.response?.data?.detail || 'Failed to issue certificates'),
            },
        );
    };

    const handleRevokeCertificate = () => {
        if (!revokeTarget?.certificate_uuid) return;
        revoke(
            { certificateUuid: revokeTarget.certificate_uuid, reason: revokeReason },
            {
                onSuccess: () => {
                    toast.success('Certificate revoked');
                    setRevokeTarget(null);
                    setRevokeReason('');
                },
                onError: (e: any) =>
                    toast.error(e?.response?.data?.detail || 'Failed to revoke certificate'),
            },
        );
    };

    return (
        <div className="space-y-4">
            <div className="flex justify-between items-center bg-info-subtle border border-info p-4 rounded-lg">
                <div className="flex gap-3">
                    <div className="bg-info/20 p-2 rounded-full h-10 w-10 flex items-center justify-center text-info">
                        <Award className="h-5 w-5" />
                    </div>
                    <div>
                        <h3 className="text-sm font-bold text-info">Ready to issue?</h3>
                        <p className="text-sm text-muted-foreground">
                            You have {eligibleCount} verified attendee{eligibleCount === 1 ? '' : 's'} eligible for certificates.
                        </p>
                    </div>
                </div>
                <Button onClick={handleIssueAllCertificates}>Issue All Certificates</Button>
            </div>

            <Card>
                <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-border">
                        <thead className="bg-muted/50">
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                                    Attendee
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                                    Eligibility
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                                    Certificate Status
                                </th>
                                <th className="px-6 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider">
                                    Action
                                </th>
                            </tr>
                        </thead>
                        <tbody className="bg-card divide-y divide-border">
                            {activeAttendees.map((attendee: any) => (
                                <tr key={attendee.uuid} className="hover:bg-muted/50">
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <div className="text-sm font-medium text-foreground">
                                            {attendee.full_name}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        {attendee.attendance_eligible ? (
                                            <Badge
                                                variant="outline"
                                                className="text-success bg-success-subtle border-success"
                                            >
                                                Eligible
                                            </Badge>
                                        ) : (
                                            <Badge
                                                variant="outline"
                                                className="text-muted-foreground bg-muted border-border"
                                            >
                                                Not Eligible
                                            </Badge>
                                        )}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">
                                        {attendee.certificate_uuid ? 'Issued' : 'Not Issued'}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-2">
                                        {attendee.certificate_uuid ? (
                                            <>
                                                <Button
                                                    size="sm"
                                                    variant="outline"
                                                    onClick={() => handleReissueCertificate(attendee.uuid)}
                                                >
                                                    Re-issue
                                                </Button>
                                                <Button
                                                    size="sm"
                                                    variant="outline"
                                                    className="text-destructive border-destructive hover:bg-destructive/10"
                                                    onClick={() => setRevokeTarget(attendee)}
                                                >
                                                    Revoke
                                                </Button>
                                            </>
                                        ) : attendee.attendance_eligible ? (
                                            // Hide the Issue button entirely when the attendee
                                            // doesn't qualify, rather than rendering it disabled.
                                            // A disabled button reads as "this row is also a
                                            // candidate, just blocked right now" and inflates
                                            // the eligible count in the organiser's mental model
                                            // — the UI now matches the data.
                                            <Button
                                                size="sm"
                                                variant="outline"
                                                onClick={() => handleIssueCertificate(attendee.uuid)}
                                            >
                                                Issue
                                            </Button>
                                        ) : null}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </Card>

            <ConfirmDialog
                open={!!revokeTarget}
                onOpenChange={(open) => {
                    if (!open) {
                        setRevokeTarget(null);
                        setRevokeReason('');
                    }
                }}
                title="Revoke Certificate"
                description={
                    <div className="space-y-3">
                        <p>
                            Are you sure you want to revoke the certificate for{' '}
                            <strong>{revokeTarget?.full_name}</strong>? This action can be undone by
                            reissuing.
                        </p>
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Reason for revocation</label>
                            <Input
                                value={revokeReason}
                                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                                    setRevokeReason(e.target.value)
                                }
                                placeholder="e.g. Attendance records corrected"
                            />
                        </div>
                    </div>
                }
                confirmLabel="Revoke Certificate"
                variant="destructive"
                isLoading={revokeLoading}
                onConfirm={handleRevokeCertificate}
            />
        </div>
    );
}
