import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/shared/ui/card';
import { Button } from '@/shared/ui/button';
import { Badge } from '@/shared/ui/badge';
import { Input } from '@/shared/ui/input';
import { deriveProgressDisplay } from '@/lib/progress';
import { Label } from '@/shared/ui/label';
import { useToast } from '@/shared/ui/use-toast';
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from '@/shared/ui/alert-dialog';
import { Loader2, Search, UserCircle, Mail, Calendar, RotateCcw } from 'lucide-react';
import { format } from 'date-fns';
import client from '@/api/client';
import {
    PaymentBadge,
    formatPaymentAmount,
    type EnrollmentPayment,
} from '@/components/billing/PaymentBadge';

interface CourseEnrollment {
    uuid: string;
    user_uuid: string;
    user_email: string;
    user_name?: string | null;
    status: 'active' | 'completed' | 'dropped' | 'pending';
    enrolled_at: string;
    started_at?: string;
    completed_at?: string;
    progress_percent: number;
    certificate_issued?: boolean;
    payment?: EnrollmentPayment;
    via_program?: {
        program_uuid: string;
        program_title: string;
        program_slug: string;
        program_enrollment_uuid: string;
    } | null;
}


interface EnrollmentsTabProps {
    courseUuid: string;
}

export function EnrollmentsTab({ courseUuid }: EnrollmentsTabProps) {
    const { toast } = useToast();
    const [enrollments, setEnrollments] = useState<CourseEnrollment[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [statusFilter, setStatusFilter] = useState<string>('all');

    useEffect(() => {
        const fetchEnrollments = async () => {
            try {
                // Call the course enrollments endpoint
                const response = await client.get(`/courses/${courseUuid}/enrollments/`);
                const data = Array.isArray(response.data) ? response.data : response.data.results || [];
                setEnrollments(data);
            } catch (error) {
                console.error('Failed to fetch enrollments:', error);
                toast({
                    variant: 'destructive',
                    title: 'Error',
                    description: 'Failed to load enrollments.',
                });
            } finally {
                setLoading(false);
            }
        };

        fetchEnrollments();
    }, [courseUuid, toast]);

    // Refund dialog state
    const [refundTarget, setRefundTarget] = useState<CourseEnrollment | null>(null);
    const [refundReason, setRefundReason] = useState('');
    const [refundAmount, setRefundAmount] = useState('');
    const [submittingRefund, setSubmittingRefund] = useState(false);

    // Filter enrollments
    const filteredEnrollments = enrollments.filter(enrollment => {
        const matchesSearch =
            enrollment.user_email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
            enrollment.user_name?.toLowerCase().includes(searchTerm.toLowerCase());

        const matchesStatus = statusFilter === 'all' || enrollment.status === statusFilter;

        return matchesSearch && matchesStatus;
    });

    const openRefund = (enrollment: CourseEnrollment) => {
        setRefundTarget(enrollment);
        setRefundReason('');
        // Default amount = full amount paid, shown in dollars; admin can edit down for partial
        if (enrollment.payment?.amount_cents) {
            setRefundAmount((enrollment.payment.amount_cents / 100).toFixed(2));
        } else {
            setRefundAmount('');
        }
    };

    const submitRefund = async () => {
        if (!refundTarget || !refundReason.trim()) return;
        setSubmittingRefund(true);
        try {
            const body: Record<string, any> = {
                enrollment_uuid: refundTarget.uuid,
                reason: refundTarget.user_name
                    ? `[${refundTarget.user_name}] ${refundTarget.user_email}: ${refundReason.trim()}`
                    : `${refundTarget.user_email}: ${refundReason.trim()}`,
            };
            const fullCents = refundTarget.payment?.amount_cents ?? 0;
            const requestedDollars = parseFloat(refundAmount);
            if (!isNaN(requestedDollars) && Math.round(requestedDollars * 100) < fullCents) {
                body.amount_cents = Math.round(requestedDollars * 100);
            }
            const resp = await client.post(`/courses/${courseUuid}/refund-enrollment/`, body);
            setEnrollments((prev) =>
                prev.map((e) => (e.uuid === refundTarget.uuid ? { ...e, ...resp.data } : e)),
            );
            toast({ title: 'Refund issued', description: 'Stripe refund created and enrollment updated.' });
            setRefundTarget(null);
        } catch (err: any) {
            const code = err?.response?.data?.error?.code;
            const msg = err?.response?.data?.error?.message || 'Refund failed.';
            toast({ variant: 'destructive', title: code ?? 'Refund failed', description: msg });
        } finally {
            setSubmittingRefund(false);
        }
    };

    const getStatusBadge = (status: string) => {
        switch (status) {
            case 'completed':
                return <Badge className="bg-green-500">Completed</Badge>;
            case 'active':
                return <Badge className="bg-blue-500">Active</Badge>;
            case 'dropped':
                return <Badge variant="destructive">Dropped</Badge>;
            case 'pending':
                return <Badge variant="secondary">Pending</Badge>;
            default:
                return <Badge variant="outline">{status}</Badge>;
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
            {/* Filters */}
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
                <div className="flex gap-2">
                    {['all', 'active', 'completed', 'pending', 'dropped'].map((status) => (
                        <Button
                            key={status}
                            variant={statusFilter === status ? 'default' : 'outline'}
                            size="sm"
                            onClick={() => setStatusFilter(status)}
                            className="capitalize"
                        >
                            {status}
                        </Button>
                    ))}
                </div>
            </div>

            {/* Stats Summary */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Card>
                    <CardContent className="pt-4 text-center">
                        <p className="text-2xl font-bold">{enrollments.length}</p>
                        <p className="text-sm text-muted-foreground">Total</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="pt-4 text-center">
                        <p className="text-2xl font-bold text-blue-500">
                            {enrollments.filter(e => e.status === 'active').length}
                        </p>
                        <p className="text-sm text-muted-foreground">Active</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="pt-4 text-center">
                        <p className="text-2xl font-bold text-green-500">
                            {enrollments.filter(e => e.status === 'completed').length}
                        </p>
                        <p className="text-sm text-muted-foreground">Completed</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="pt-4 text-center">
                        <p className="text-2xl font-bold text-amber-500">
                            {enrollments.filter(e => e.certificate_issued).length}
                        </p>
                        <p className="text-sm text-muted-foreground">Certified</p>
                    </CardContent>
                </Card>
            </div>

            {/* Enrollments List */}
            {filteredEnrollments.length === 0 ? (
                <Card>
                    <CardContent className="py-12 text-center">
                        <UserCircle className="h-12 w-12 mx-auto text-muted-foreground/50 mb-4" />
                        <p className="text-muted-foreground">
                            {enrollments.length === 0
                                ? 'No enrollments yet'
                                : 'No enrollments match your search'}
                        </p>
                    </CardContent>
                </Card>
            ) : (
                <Card>
                    <CardHeader>
                        <CardTitle>Enrolled Learners</CardTitle>
                        <CardDescription>{filteredEnrollments.length} learner(s)</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="divide-y">
                            {filteredEnrollments.map((enrollment) => {
                                // Program-seeded rows must be refunded at the program level; suppress
                                // the course-level Refund button and point the admin to the program.
                                const isViaProgram = Boolean(enrollment.via_program);
                                const canRefund = !isViaProgram && enrollment.payment?.status === 'completed';
                                return (
                                    <div key={enrollment.uuid} className="flex items-center justify-between py-4">
                                        <div className="flex items-center gap-4">
                                            <div className="h-10 w-10 rounded-full bg-muted flex items-center justify-center">
                                                <UserCircle className="h-6 w-6 text-muted-foreground" />
                                            </div>
                                            <div>
                                                <p className="font-medium">
                                                    {enrollment.user_name || 'Unknown Learner'}
                                                </p>
                                                <p className="text-sm text-muted-foreground flex items-center gap-1">
                                                    <Mail className="h-3 w-3" />
                                                    {enrollment.user_email || 'No email'}
                                                </p>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-6">
                                            <div className="text-right">
                                                <PaymentBadge payment={enrollment.payment} />
                                                {isViaProgram && enrollment.via_program && (
                                                    <a
                                                        href={`/programs/manage/${enrollment.via_program.program_slug}?tab=enrollments`}
                                                        className="block text-xs text-primary hover:underline mt-1"
                                                    >
                                                        Refund on program →
                                                    </a>
                                                )}
                                            </div>
                                            <div className="text-right">
                                                <p className="text-sm font-medium">{deriveProgressDisplay(enrollment).percent}%</p>
                                                <p className="text-xs text-muted-foreground">Progress</p>
                                            </div>
                                            <div className="text-right">
                                                <p className="text-sm flex items-center gap-1">
                                                    <Calendar className="h-3 w-3" />
                                                    {enrollment.enrolled_at
                                                        ? format(new Date(enrollment.enrolled_at), 'MMM d, yyyy')
                                                        : 'N/A'}
                                                </p>
                                                <p className="text-xs text-muted-foreground">Enrolled</p>
                                            </div>
                                            {getStatusBadge(enrollment.status)}
                                            {canRefund && (
                                                <Button
                                                    variant="outline"
                                                    size="sm"
                                                    onClick={() => openRefund(enrollment)}
                                                >
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
                        <AlertDialogTitle>Refund course purchase</AlertDialogTitle>
                        <AlertDialogDescription>
                            {refundTarget?.payment?.amount_cents ? (
                                <>
                                    Refunding{' '}
                                    <span className="font-medium">{formatPaymentAmount(refundTarget.payment)}</span> to{' '}
                                    <span className="font-medium">{refundTarget?.user_email}</span>. Stripe will reverse the
                                    original charge; a full refund also drops the enrollment.
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
