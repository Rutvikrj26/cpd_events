import React, { useEffect, useState } from 'react';
import { getMyRegistrations, linkRegistrations } from '@/api/registrations';
import { Registration } from '@/api/registrations/types';
import { getEnrollments } from '@/api/courses';
import {
    Calendar,
    CheckCircle,
    XCircle,
    Clock,
    Link2,
    RefreshCw,
    CreditCard,
    AlertCircle,
    DollarSign,
    MessageSquare,
    Star,
    Loader2,
    BookOpen,
    Award,
    ArrowRight,
} from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import {
    Card,
    CardContent,
    CardDescription,
    CardFooter,
    CardHeader,
    CardTitle,
} from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import { FeedbackModal } from '@/components/feedback';
import { getRegistrationFeedback } from '@/api/feedback';
import { useAuth } from '@/contexts/AuthContext';
import { formatDate } from '@/lib/datetime';
import { EventFeedback } from '@/api/feedback/types';
import { format } from 'date-fns';

export const MyLearningPage = () => {
    const { user } = useAuth();
    const [registrations, setRegistrations] = useState<Registration[]>([]);
    const [enrollments, setEnrollments] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [linking, setLinking] = useState(false);
    const navigate = useNavigate();

    // Feedback state
    const [feedbackModalOpen, setFeedbackModalOpen] = useState(false);
    const [selectedRegistration, setSelectedRegistration] = useState<Registration | null>(null);
    const [existingFeedback, setExistingFeedback] = useState<EventFeedback | null>(null);
    const [feedbackMap, setFeedbackMap] = useState<Record<string, boolean>>({});

    const checkFeedbackStatus = async (regs: Registration[]) => {
        const pastEvents = regs.filter(r =>
            r.attended || new Date(r.event.starts_at) < new Date()
        );

        const feedbackChecks = await Promise.all(
            pastEvents.map(async (reg) => {
                const feedback = await getRegistrationFeedback(reg.uuid);
                return { uuid: reg.uuid, hasFeedback: !!feedback };
            })
        );

        const map: Record<string, boolean> = {};
        feedbackChecks.forEach(({ uuid, hasFeedback }) => {
            map[uuid] = hasFeedback;
        });
        setFeedbackMap(map);
    };

    const fetchAll = async () => {
        try {
            const [regsResp, enrolls] = await Promise.all([
                getMyRegistrations(),
                getEnrollments(),
            ]);
            setRegistrations(regsResp.results);
            setEnrollments(enrolls);
            checkFeedbackStatus(regsResp.results);
        } catch (error) {
            console.error('Failed to load learning data', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchAll();
    }, []);

    const handleOpenFeedback = async (reg: Registration) => {
        setSelectedRegistration(reg);
        const feedback = await getRegistrationFeedback(reg.uuid);
        setExistingFeedback(feedback);
        setFeedbackModalOpen(true);
    };

    const handleFeedbackSuccess = () => {
        if (selectedRegistration) {
            setFeedbackMap(prev => ({
                ...prev,
                [selectedRegistration.uuid]: true,
            }));
        }
        setFeedbackModalOpen(false);
        setSelectedRegistration(null);
        setExistingFeedback(null);
    };

    const canLeaveFeedback = (reg: Registration) => {
        // Event ended = either an explicit actual_end_at, or
        // starts_at + duration_minutes is in the past. Live events whose
        // start has passed but end has not should NOT yet allow feedback.
        const now = Date.now();
        const startMs = new Date(reg.event.starts_at).getTime();
        const durationMs = (reg.event.duration_minutes ?? 0) * 60_000;
        const explicitEnd = reg.event.actual_end_at
            ? new Date(reg.event.actual_end_at).getTime()
            : null;
        const eventEnded = explicitEnd
            ? explicitEnd < now
            : startMs + durationMs < now;
        return eventEnded && reg.status !== 'cancelled';
    };

    const handleLinkRegistrations = async () => {
        setLinking(true);
        try {
            const result = await linkRegistrations();
            if (result.linked_count > 0) {
                toast.success(`Found and linked ${result.linked_count} event${result.linked_count > 1 ? 's' : ''} to your account!`);
                await fetchAll();
            } else {
                toast.info('No additional events found to link to your account.');
            }
        } catch (error) {
            console.error('Failed to link registrations', error);
            toast.error('Failed to link events. Please try again.');
        } finally {
            setLinking(false);
        }
    };

    const getStatusBadge = (status: string) => {
        switch (status) {
            case 'confirmed': return <span className="inline-flex items-center text-green-700 bg-green-50 px-2 py-1 rounded-md text-xs font-medium"><CheckCircle size={12} className="mr-1" /> Confirmed</span>;
            case 'attended': return <span className="inline-flex items-center text-blue-700 bg-blue-50 px-2 py-1 rounded-md text-xs font-medium"><CheckCircle size={12} className="mr-1" /> Attended</span>;
            case 'cancelled': return <span className="inline-flex items-center text-red-700 bg-red-50 px-2 py-1 rounded-md text-xs font-medium"><XCircle size={12} className="mr-1" /> Cancelled</span>;
            case 'waitlisted': return <span className="inline-flex items-center text-yellow-700 bg-yellow-50 px-2 py-1 rounded-md text-xs font-medium"><Clock size={12} className="mr-1" /> Waitlisted</span>;
            case 'pending': return <span className="inline-flex items-center text-amber-700 bg-amber-50 px-2 py-1 rounded-md text-xs font-medium"><Clock size={12} className="mr-1" /> Pending Payment</span>;
            default: return <span className="inline-flex items-center text-muted-foreground bg-muted px-2 py-1 rounded-md text-xs font-medium"><Clock size={12} className="mr-1" /> Pending</span>;
        }
    };

    const getPaymentBadge = (paymentStatus: string) => {
        switch (paymentStatus) {
            case 'paid':
                return <Badge variant="outline" className="text-green-700 border-green-300 bg-green-50"><DollarSign size={10} className="mr-1" /> Paid</Badge>;
            case 'pending':
                return <Badge variant="outline" className="text-yellow-700 border-yellow-300 bg-yellow-50"><Clock size={10} className="mr-1" /> Payment Pending</Badge>;
            case 'failed':
                return <Badge variant="outline" className="text-red-700 border-red-300 bg-red-50"><AlertCircle size={10} className="mr-1" /> Payment Failed</Badge>;
            case 'refunded':
                return <Badge variant="outline" className="text-purple-700 border-purple-300 bg-purple-50"><DollarSign size={10} className="mr-1" /> Refunded</Badge>;
            case 'na':
            default:
                return null;
        }
    };

    const handleCompletePayment = (reg: Registration) => {
        navigate(`/events/${reg.event.uuid}/register?resume=${reg.uuid}`);
    };

    if (loading) {
        return (
            <div className="flex h-[50vh] items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <h1 className="text-3xl font-bold text-foreground">My Learning</h1>

            <Tabs defaultValue="events" className="w-full">
                <TabsList>
                    <TabsTrigger value="events">Events ({registrations.length})</TabsTrigger>
                    <TabsTrigger value="courses">Courses ({enrollments.length})</TabsTrigger>
                </TabsList>

                <TabsContent value="events" className="space-y-6">
                    <div className="bg-card rounded-xl border shadow-sm overflow-hidden">
                        {registrations.length === 0 ? (
                            <div className="p-12 text-center text-muted-foreground">
                                You have not registered for any events yet.
                            </div>
                        ) : (
                            <table className="w-full text-left text-sm">
                                <thead className="bg-muted/30 border-b">
                                    <tr>
                                        <th className="px-6 py-4 font-medium text-muted-foreground">Event</th>
                                        <th className="px-6 py-4 font-medium text-muted-foreground">Date Registered</th>
                                        <th className="px-6 py-4 font-medium text-muted-foreground">Status</th>
                                        <th className="px-6 py-4 font-medium text-muted-foreground">Payment</th>
                                        <th className="px-6 py-4 font-medium text-muted-foreground">Actions</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-border">
                                    {registrations.map(reg => (
                                        <tr key={reg.uuid} className="hover:bg-muted/30 transition-colors">
                                            <td className="px-6 py-4">
                                                <div className="font-semibold text-foreground">
                                                    {reg.event.title}
                                                </div>
                                                <div className="text-xs text-muted-foreground mt-1">
                                                    {formatDate(reg.event.starts_at, user)}
                                                </div>
                                            </td>
                                            <td className="px-6 py-4 text-muted-foreground">
                                                {formatDate(reg.created_at, user)}
                                            </td>
                                            <td className="px-6 py-4">{getStatusBadge(reg.status)}</td>
                                            <td className="px-6 py-4">{getPaymentBadge(reg.payment_status)}</td>
                                            <td className="px-6 py-4">
                                                <div className="flex items-center gap-2">
                                                    <Link to={`/events/${reg.event.slug || reg.event.uuid}/details`} className="text-primary hover:text-primary/80 font-medium text-xs">
                                                        View Event
                                                    </Link>
                                                    {reg.status === 'pending' && (reg.payment_status === 'pending' || reg.payment_status === 'refunded') && (
                                                        <Button
                                                            size="sm"
                                                            variant="outline"
                                                            className="text-xs h-7"
                                                            onClick={() => handleCompletePayment(reg)}
                                                        >
                                                            <CreditCard size={12} className="mr-1" />
                                                            Pay Now
                                                        </Button>
                                                    )}
                                                    {reg.status === 'pending' && reg.payment_status === 'failed' && (
                                                        <Button
                                                            size="sm"
                                                            variant="destructive"
                                                            className="text-xs h-7"
                                                            onClick={() => handleCompletePayment(reg)}
                                                        >
                                                            <AlertCircle size={12} className="mr-1" />
                                                            Retry Payment
                                                        </Button>
                                                    )}
                                                    {canLeaveFeedback(reg) && (
                                                        <Button
                                                            size="sm"
                                                            variant={feedbackMap[reg.uuid] ? 'ghost' : 'outline'}
                                                            className="text-xs h-7"
                                                            onClick={() => handleOpenFeedback(reg)}
                                                        >
                                                            {feedbackMap[reg.uuid] ? (
                                                                <>
                                                                    <Star size={12} className="mr-1 fill-yellow-400 text-yellow-400" />
                                                                    Edit Feedback
                                                                </>
                                                            ) : (
                                                                <>
                                                                    <MessageSquare size={12} className="mr-1" />
                                                                    Leave Feedback
                                                                </>
                                                            )}
                                                        </Button>
                                                    )}
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )}
                    </div>

                    <Separator className="my-6" />

                    <Card className="border-dashed">
                        <CardHeader className="pb-3">
                            <div className="flex items-center gap-2">
                                <Link2 className="h-5 w-5 text-muted-foreground" />
                                <CardTitle className="text-base">Missing Events?</CardTitle>
                            </div>
                            <CardDescription>
                                If you registered for events before creating your account, or used the same email on a different device,
                                we can find and link those registrations to your account.
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <Button
                                variant="outline"
                                onClick={handleLinkRegistrations}
                                disabled={linking}
                            >
                                {linking ? (
                                    <>
                                        <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                                        Searching...
                                    </>
                                ) : (
                                    <>
                                        <RefreshCw className="h-4 w-4 mr-2" />
                                        Find &amp; Link My Events
                                    </>
                                )}
                            </Button>
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="courses">
                    {enrollments.length === 0 ? (
                        <div className="text-center py-12 border rounded-lg bg-muted/20">
                            <BookOpen className="mx-auto h-12 w-12 text-muted-foreground/50 mb-4" />
                            <h3 className="text-lg font-medium mb-2">No courses yet</h3>
                            <p className="text-muted-foreground">
                                You haven't enrolled in any courses yet.
                            </p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            {enrollments.map((enrollment) => {
                                const isComplete = enrollment.status === 'completed' || enrollment.progress_percent >= 100;
                                return (
                                    <Card key={enrollment.uuid} className="flex flex-col h-full hover:shadow-md transition-shadow">
                                        <CardHeader className="pb-4">
                                            <div className="flex justify-between items-start mb-2">
                                                <Badge variant={enrollment.status === 'completed' ? 'default' : enrollment.progress_percent >= 100 ? 'outline' : 'secondary'}>
                                                    {enrollment.status === 'completed' ? 'Completed' : enrollment.progress_percent >= 100 ? 'Awaiting Review' : 'In Progress'}
                                                </Badge>
                                                {enrollment.certificate_issued && (
                                                    <div title="Certificate Earned">
                                                        <Award className="h-5 w-5 text-amber-500" />
                                                    </div>
                                                )}
                                            </div>
                                            <CardTitle className="line-clamp-2 leading-tight">
                                                {enrollment.course?.title}
                                            </CardTitle>
                                            <CardDescription className="line-clamp-1">
                                                {enrollment.course?.organization_name}
                                            </CardDescription>
                                        </CardHeader>
                                        <CardContent className="pb-4 flex-grow">
                                            <div className="space-y-4">
                                                <div className="space-y-2">
                                                    <div className="flex justify-between text-sm">
                                                        <span className="text-muted-foreground">Progress</span>
                                                        <span className="font-medium">{enrollment.progress_percent}%</span>
                                                    </div>
                                                    <Progress value={enrollment.progress_percent} className="h-2" />
                                                </div>
                                                <div className="text-xs text-muted-foreground flex justify-between">
                                                    <span>
                                                        Started: {enrollment.started_at ? format(new Date(enrollment.started_at), 'MMM d, yyyy') : 'Not started'}
                                                    </span>
                                                    {enrollment.completed_at && (
                                                        <span>Finished: {format(new Date(enrollment.completed_at), 'MMM d, yyyy')}</span>
                                                    )}
                                                </div>
                                            </div>
                                        </CardContent>
                                        <CardFooter className="pt-0 flex gap-2">
                                            <Button className="flex-1" asChild>
                                                <Link to={`/learn/${enrollment.course?.uuid}`}>
                                                    {isComplete ? 'Review' : 'Continue'}
                                                    <ArrowRight className="ml-2 h-4 w-4" />
                                                </Link>
                                            </Button>
                                            {enrollment.certificate_issued && (
                                                <Button
                                                    variant="outline"
                                                    size="icon"
                                                    onClick={() => navigate('/certificates')}
                                                    title="View Certificate"
                                                >
                                                    <Award className="h-4 w-4" />
                                                </Button>
                                            )}
                                        </CardFooter>
                                    </Card>
                                );
                            })}
                        </div>
                    )}
                </TabsContent>
            </Tabs>

            {/* Feedback Modal */}
            {selectedRegistration && (
                <FeedbackModal
                    open={feedbackModalOpen}
                    onOpenChange={setFeedbackModalOpen}
                    eventUuid={selectedRegistration.event.uuid}
                    registrationUuid={selectedRegistration.uuid}
                    eventTitle={selectedRegistration.event.title}
                    existingFeedback={existingFeedback}
                    onSuccess={handleFeedbackSuccess}
                />
            )}
        </div>
    );
};
