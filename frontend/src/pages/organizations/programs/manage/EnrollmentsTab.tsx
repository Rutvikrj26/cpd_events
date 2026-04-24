import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useToast } from '@/components/ui/use-toast';
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Loader2, Search, UserCircle, Mail, Calendar, RotateCcw } from 'lucide-react';
import { format } from 'date-fns';
import {
    PaymentBadge,
    formatPaymentAmount,
    type EnrollmentPayment,
} from '@/components/billing/PaymentBadge';
import {
    getProgramEnrollmentsRoster,
    programRefundEnrollment,
} from '@/api/programs';

interface ProgramEnrollmentRow {
    uuid: string;
    user_uuid: string;
    user_email: string;
    user_name?: string | null;
    status: 'pending' | 'active' | 'completed' | 'dropped';
    enrolled_at: string;
    started_at?: string | null;
    completed_at?: string | null;
    payment?: EnrollmentPayment;
}

interface EnrollmentsTabProps {
    programUuid: string;
}

const STATUS_BADGE: Record<string, { label: string; className?: string; variant?: 'secondary' | 'destructive' | 'outline' }> = {
    active: { label: 'Active', className: 'bg-blue-500' },
    completed: { label: 'Completed', className: 'bg-green-500' },
    pending: { label: 'Pending', variant: 'secondary' },
    dropped: { label: 'Dropped', variant: 'destructive' },
};

export function EnrollmentsTab({ programUuid }: EnrollmentsTabProps) {
    const { toast } = useToast();
    const [rows, setRows] = useState<ProgramEnrollmentRow[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [statusFilter, setStatusFilter] = useState<string>('all');

    const [refundTarget, setRefundTarget] = useState<ProgramEnrollmentRow | null>(null);
    const [refundReason, setRefundReason] = useState('');
    const [refundAmount, setRefundAmount] = useState('');
    const [submittingRefund, setSubmittingRefund] = useState(false);

    useEffect(() => {
        const load = async () => {
            setLoading(true);
            try {
                const data = await getProgramEnrollmentsRoster(programUuid);
                setRows(Array.isArray(data) ? (data as ProgramEnrollmentRow[]) : []);
            } catch (err: any) {
                console.error('Failed to fetch program enrollments', err);
                toast({
                    variant: 'destructive',
                    title: 'Error',
                    description: 'Failed to load program enrollments.',
                });
            } finally {
                setLoading(false);
            }
        };
        load();
    }, [programUuid, toast]);

    const filtered = rows.filter((row) => {
        const term = searchTerm.toLowerCase();
        const matchesSearch =
            row.user_email?.toLowerCase().includes(term) ||
            row.user_name?.toLowerCase().includes(term);
        const matchesStatus = statusFilter === 'all' || row.status === statusFilter;
        return matchesSearch && matchesStatus;
    });

    const openRefund = (row: ProgramEnrollmentRow) => {
        setRefundTarget(row);
        setRefundReason('');
        if (row.payment?.amount_cents) {
            setRefundAmount((row.payment.amount_cents / 100).toFixed(2));
        } else {
            setRefundAmount('');
        }
    };

    const submitRefund = async () => {
        if (!refundTarget || !refundReason.trim()) return;
        setSubmittingRefund(true);
        try {
            const fullCents = refundTarget.payment?.amount_cents ?? 0;
            const requestedDollars = parseFloat(refundAmount);
            const payload: {
                enrollment_uuid: string;
                reason: string;
                amount_cents?: number;
            } = {
                enrollment_uuid: refundTarget.uuid,
                reason: refundTarget.user_name
                    ? `[${refundTarget.user_name}] ${refundTarget.user_email}: ${refundReason.trim()}`
                    : `${refundTarget.user_email}: ${refundReason.trim()}`,
            };
            if (!isNaN(requestedDollars) && Math.round(requestedDollars * 100) < fullCents) {
                payload.amount_cents = Math.round(requestedDollars * 100);
            }
            const updated = await programRefundEnrollment(programUuid, payload);
            setRows((prev) =>
                prev.map((r) => (r.uuid === refundTarget.uuid ? { ...r, ...updated } : r)),
            );
            toast({
                title: 'Refund issued',
                description: 'Stripe refund created. Program enrollment dropped and member courses revoked.',
            });
            setRefundTarget(null);
        } catch (err: any) {
            const code = err?.response?.data?.error?.code;
            const msg = err?.response?.data?.error?.message || 'Refund failed.';
            toast({ variant: 'destructive', title: code ?? 'Refund failed', description: msg });
        } finally {
            setSubmittingRefund(false);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex flex-col sm:flex-row gap-4">
                <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                        placeholder="Search by name or email..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="pl-9"
                    />
                </div>
                <div className="flex gap-2 flex-wrap">
                    {['all', 'pending', 'active', 'completed', 'dropped'].map((s) => (
                        <Button
                            key={s}
                            variant={statusFilter === s ? 'default' : 'outline'}
                            size="sm"
                            onClick={() => setStatusFilter(s)}
                            className="capitalize"
                        >
                            {s}
                        </Button>
                    ))}
                </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Card>
                    <CardContent className="pt-4 text-center">
                        <p className="text-2xl font-bold">{rows.length}</p>
                        <p className="text-sm text-muted-foreground">Total</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="pt-4 text-center">
                        <p className="text-2xl font-bold text-blue-500">
                            {rows.filter((r) => r.status === 'active').length}
                        </p>
                        <p className="text-sm text-muted-foreground">Active</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="pt-4 text-center">
                        <p className="text-2xl font-bold text-green-500">
                            {rows.filter((r) => r.status === 'completed').length}
                        </p>
                        <p className="text-sm text-muted-foreground">Completed</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="pt-4 text-center">
                        <p className="text-2xl font-bold text-destructive">
                            {rows.filter((r) => r.status === 'dropped').length}
                        </p>
                        <p className="text-sm text-muted-foreground">Dropped</p>
                    </CardContent>
                </Card>
            </div>

            {filtered.length === 0 ? (
                <Card>
                    <CardContent className="py-12 text-center">
                        <UserCircle className="h-12 w-12 mx-auto text-muted-foreground/50 mb-4" />
                        <p className="text-muted-foreground">
                            {rows.length === 0 ? 'No enrollments yet' : 'No enrollments match your search'}
                        </p>
                    </CardContent>
                </Card>
            ) : (
                <Card>
                    <CardHeader>
                        <CardTitle>Enrolled Learners</CardTitle>
                        <CardDescription>{filtered.length} learner(s)</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="divide-y">
                            {filtered.map((row) => {
                                const canRefund = row.payment?.status === 'completed';
                                const statusConfig = STATUS_BADGE[row.status] ?? { label: row.status };
                                return (
                                    <div key={row.uuid} className="flex items-center justify-between py-4">
                                        <div className="flex items-center gap-4">
                                            <div className="h-10 w-10 rounded-full bg-muted flex items-center justify-center">
                                                <UserCircle className="h-6 w-6 text-muted-foreground" />
                                            </div>
                                            <div>
                                                <p className="font-medium">{row.user_name || 'Unknown Learner'}</p>
                                                <p className="text-sm text-muted-foreground flex items-center gap-1">
                                                    <Mail className="h-3 w-3" />
                                                    {row.user_email || 'No email'}
                                                </p>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-6">
                                            <div className="text-right">
                                                <PaymentBadge payment={row.payment} />
                                            </div>
                                            <div className="text-right">
                                                <p className="text-sm flex items-center gap-1">
                                                    <Calendar className="h-3 w-3" />
                                                    {row.enrolled_at ? format(new Date(row.enrolled_at), 'MMM d, yyyy') : 'N/A'}
                                                </p>
                                                <p className="text-xs text-muted-foreground">Enrolled</p>
                                            </div>
                                            <Badge
                                                className={statusConfig.className}
                                                variant={statusConfig.variant}
                                            >
                                                {statusConfig.label}
                                            </Badge>
                                            {canRefund && (
                                                <Button variant="outline" size="sm" onClick={() => openRefund(row)}>
                                                    <RotateCcw className="h-3 w-3 mr-1" />
                                                    Refund
                                                </Button>
                                            )}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </CardContent>
                </Card>
            )}

            <AlertDialog
                open={refundTarget !== null}
                onOpenChange={(open) => {
                    if (!open) setRefundTarget(null);
                }}
            >
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Refund program purchase</AlertDialogTitle>
                        <AlertDialogDescription>
                            {refundTarget?.payment?.amount_cents ? (
                                <>
                                    Refunding{' '}
                                    <span className="font-medium">{formatPaymentAmount(refundTarget.payment)}</span> to{' '}
                                    <span className="font-medium">{refundTarget?.user_email}</span>. A full refund drops the
                                    program enrollment and revokes access to every member course seeded by it. Direct
                                    enrollments the learner made outside this program are not affected.
                                </>
                            ) : (
                                'No payment found for this enrollment.'
                            )}
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <div className="space-y-3">
                        <div className="space-y-1">
                            <Label htmlFor="refund-amount">Amount (leave unchanged for full refund)</Label>
                            <Input
                                id="refund-amount"
                                type="number"
                                step="0.01"
                                min="0.01"
                                value={refundAmount}
                                onChange={(e) => setRefundAmount(e.target.value)}
                                disabled={submittingRefund}
                            />
                        </div>
                        <div className="space-y-1">
                            <Label htmlFor="refund-reason">Reason (required, recorded in audit log)</Label>
                            <Input
                                id="refund-reason"
                                placeholder="e.g. learner requested refund after module 1"
                                value={refundReason}
                                onChange={(e) => setRefundReason(e.target.value)}
                                disabled={submittingRefund}
                            />
                        </div>
                    </div>
                    <AlertDialogFooter>
                        <AlertDialogCancel disabled={submittingRefund}>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={(e) => {
                                e.preventDefault();
                                submitRefund();
                            }}
                            disabled={submittingRefund || !refundReason.trim()}
                        >
                            {submittingRefund && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                            Issue refund
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    );
}

export default EnrollmentsTab;
