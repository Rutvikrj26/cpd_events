import React, { useEffect, useState } from 'react';
import { getMyRegistrations, linkRegistrations } from '@/api/registrations';
import { Registration } from '@/api/registrations/types';
import { Calendar, CheckCircle, XCircle, Clock, Link2, RefreshCw, CreditCard, AlertCircle, DollarSign, MessageSquare, Star } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { FeedbackModal } from '@/components/feedback';
import { getRegistrationFeedback } from '@/api/feedback';
import { EventFeedback } from '@/api/feedback/types';

export const MyRegistrationsPage = () => {
    const [registrations, setRegistrations] = useState<Registration[]>([]);
    const [loading, setLoading] = useState(true);
    const [linking, setLinking] = useState(false);
    const navigate = useNavigate();

    // Feedback state
    const [feedbackModalOpen, setFeedbackModalOpen] = useState(false);
    const [selectedRegistration, setSelectedRegistration] = useState<Registration | null>(null);
    const [existingFeedback, setExistingFeedback] = useState<EventFeedback | null>(null);
    const [feedbackMap, setFeedbackMap] = useState<Record<string, boolean>>({});

    // Check which registrations have feedback
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

    const fetchRegistrations = async () => {
        try {
            const data = await getMyRegistrations();
            setRegistrations(data.results);
            // Check feedback status for past events
            checkFeedbackStatus(data.results);
        } catch (error) {
            console.error("Failed to load registrations", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchRegistrations();
    }, []);

    const handleOpenFeedback = async (reg: Registration) => {
        setSelectedRegistration(reg);
        // Check if feedback already exists
        const feedback = await getRegistrationFeedback(reg.uuid);
        setExistingFeedback(feedback);
        setFeedbackModalOpen(true);
    };

    const handleFeedbackSuccess = () => {
        // Update the feedback map
        if (selectedRegistration) {
            setFeedbackMap(prev => ({
                ...prev,
                [selectedRegistration.uuid]: true
            }));
        }
        setFeedbackModalOpen(false);
        setSelectedRegistration(null);
        setExistingFeedback(null);
    };

    const canLeaveFeedback = (reg: Registration) => {
        // Can leave feedback if:
        // 1. Event has passed OR marked as attended
        // 2. Registration is confirmed (not cancelled)
        const eventPassed = new Date(reg.event.starts_at) < new Date();
        return (eventPassed || reg.attended) && reg.status !== 'cancelled';
    };

    const handleLinkRegistrations = async () => {
        setLinking(true);
        try {
            const result = await linkRegistrations();
            if (result.linked_count > 0) {
                toast.success(`Found and linked ${result.linked_count} event${result.linked_count > 1 ? 's' : ''} to your account!`);
                await fetchRegistrations();
            } else {
                toast.info("No additional events found to link to your account.");
            }
        } catch (error) {
            console.error("Failed to link registrations", error);
            toast.error("Failed to link events. Please try again.");
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
                return null; // Free event, don't show badge
        }
    };

    const handleCompletePayment = (reg: Registration) => {
        // Navigate to the event registration page to complete payment
        navigate(`/events/${reg.event.uuid}/register?resume=${reg.uuid}`);
    };

    if (loading) return <div className="p-8">Loading registrations...</div>;

    return (
        <div className="space-y-6">
            <h1 className="text-3xl font-bold text-foreground">My Registrations</h1>

            <div className="bg-card rounded-xl border shadow-sm overflow-hidden">
                {registrations.length === 0 ? (
                    <div className="p-12 text-center text-muted-foreground">
                        You have not registered for any events yet. <Link to="/events" className="text-primary hover:underline">Browse Events</Link>
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
                                            {reg.event.starts_at && new Date(reg.event.starts_at).toLocaleDateString()}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 text-muted-foreground">
                                        {new Date(reg.created_at).toLocaleDateString()}
                                    </td>
                                    <td className="px-6 py-4">
                                        {getStatusBadge(reg.status)}
                                    </td>
                                    <td className="px-6 py-4">
                                        {getPaymentBadge(reg.payment_status)}
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="flex items-center gap-2">
                                            <Link to={`/events/${reg.event.slug || reg.event.uuid}`} className="text-primary hover:text-primary/80 font-medium text-xs">
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
                                                    variant={feedbackMap[reg.uuid] ? "ghost" : "outline"}
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

            {/* Link Events Section */}
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
                                Find & Link My Events
                            </>
                        )}
                    </Button>
                </CardContent>
            </Card>

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
