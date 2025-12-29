import React, { useState } from 'react';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
    AlertTriangle,
    Gift,
    PauseCircle,
    HelpCircle,
    ChevronRight,
    Loader2,
    CheckCircle,
    Calendar,
    Users,
    Award
} from 'lucide-react';
import { Subscription } from '@/api/billing/types';
import { cancelSubscription } from '@/api/billing';
import { toast } from 'sonner';

interface CancellationModalProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    subscription: Subscription;
    onCanceled: (updated: Subscription) => void;
}

type CancellationReason =
    | 'too_expensive'
    | 'not_using'
    | 'missing_features'
    | 'switching_provider'
    | 'temporary_pause'
    | 'other';

type Step = 'reason' | 'offer' | 'confirm' | 'feedback';

const REASONS: { value: CancellationReason; label: string; description: string }[] = [
    { value: 'too_expensive', label: 'Too expensive', description: "The price doesn't fit my budget" },
    { value: 'not_using', label: 'Not using it enough', description: 'I have fewer events than expected' },
    { value: 'missing_features', label: 'Missing features', description: "It doesn't have what I need" },
    { value: 'switching_provider', label: 'Switching to another provider', description: 'Found a better alternative' },
    { value: 'temporary_pause', label: 'Taking a break', description: 'I need to pause temporarily' },
    { value: 'other', label: 'Other reason', description: 'Something else' },
];

export function CancellationModal({
    open,
    onOpenChange,
    subscription,
    onCanceled
}: CancellationModalProps) {
    const [step, setStep] = useState<Step>('reason');
    const [reason, setReason] = useState<CancellationReason | null>(null);
    const [feedback, setFeedback] = useState('');
    const [processing, setProcessing] = useState(false);
    const [offerAccepted, setOfferAccepted] = useState(false);

    const resetAndClose = () => {
        setStep('reason');
        setReason(null);
        setFeedback('');
        setOfferAccepted(false);
        onOpenChange(false);
    };

    const handleReasonContinue = () => {
        if (!reason) return;

        // Show retention offer based on reason
        if (reason === 'too_expensive' || reason === 'temporary_pause' || reason === 'not_using') {
            setStep('offer');
        } else {
            setStep('confirm');
        }
    };

    const handleAcceptOffer = () => {
        setOfferAccepted(true);
        toast.success("Great! We've applied your discount. Thanks for staying!");
        resetAndClose();
    };

    const handleDeclineOffer = () => {
        setStep('confirm');
    };

    const handleConfirmCancel = async () => {
        setProcessing(true);
        try {
            const updated = await cancelSubscription(false);
            onCanceled(updated);
            setStep('feedback');
        } catch (error) {
            toast.error('Failed to cancel subscription. Please try again.');
        } finally {
            setProcessing(false);
        }
    };

    const handleSubmitFeedback = () => {
        // In a real app, you'd send this feedback to the backend
        console.log('Cancellation feedback:', { reason, feedback });
        toast.success('Thank you for your feedback');
        resetAndClose();
    };

    // Calculate what they'll lose
    const endDate = subscription.current_period_end
        ? new Date(subscription.current_period_end).toLocaleDateString()
        : 'the end of your billing period';

    return (
        <Dialog open={open} onOpenChange={(isOpen) => {
            if (!isOpen) resetAndClose();
            else onOpenChange(isOpen);
        }}>
            <DialogContent className="max-w-md">
                {/* STEP 1: Reason Selection */}
                {step === 'reason' && (
                    <>
                        <DialogHeader>
                            <DialogTitle>We're sorry to see you go</DialogTitle>
                            <DialogDescription>
                                Help us understand why you're canceling so we can improve.
                            </DialogDescription>
                        </DialogHeader>

                        <RadioGroup
                            value={reason || ''}
                            onValueChange={(val) => setReason(val as CancellationReason)}
                            className="space-y-3 mt-4"
                        >
                            {REASONS.map((r) => (
                                <div key={r.value} className="flex items-start space-x-3">
                                    <RadioGroupItem value={r.value} id={r.value} className="mt-1" />
                                    <Label htmlFor={r.value} className="flex-1 cursor-pointer">
                                        <span className="font-medium">{r.label}</span>
                                        <p className="text-sm text-muted-foreground">{r.description}</p>
                                    </Label>
                                </div>
                            ))}
                        </RadioGroup>

                        <div className="flex gap-3 mt-6">
                            <Button variant="outline" onClick={resetAndClose} className="flex-1">
                                Never mind
                            </Button>
                            <Button onClick={handleReasonContinue} disabled={!reason} className="flex-1">
                                Continue
                                <ChevronRight className="h-4 w-4 ml-1" />
                            </Button>
                        </div>
                    </>
                )}

                {/* STEP 2: Retention Offer */}
                {step === 'offer' && (
                    <>
                        <DialogHeader>
                            <DialogTitle className="flex items-center gap-2">
                                <Gift className="h-5 w-5 text-primary" />
                                Before you go...
                            </DialogTitle>
                            <DialogDescription>
                                We'd hate to lose you! Here's a special offer just for you.
                            </DialogDescription>
                        </DialogHeader>

                        <div className="mt-4 space-y-4">
                            {reason === 'too_expensive' && (
                                <div className="p-4 bg-primary/5 rounded-lg border border-primary/20 space-y-3">
                                    <div className="flex items-center gap-2 text-primary font-semibold">
                                        <Gift className="h-5 w-5" />
                                        50% Off for 3 Months
                                    </div>
                                    <p className="text-sm text-muted-foreground">
                                        Stay with us and pay only $15/month for the next 3 months.
                                        That's a savings of $45!
                                    </p>
                                    <Button onClick={handleAcceptOffer} className="w-full">
                                        <CheckCircle className="h-4 w-4 mr-2" />
                                        Accept This Offer
                                    </Button>
                                </div>
                            )}

                            {reason === 'temporary_pause' && (
                                <div className="p-4 bg-primary/5 rounded-lg border border-primary/20 space-y-3">
                                    <div className="flex items-center gap-2 text-primary font-semibold">
                                        <PauseCircle className="h-5 w-5" />
                                        Pause Instead of Cancel
                                    </div>
                                    <p className="text-sm text-muted-foreground">
                                        Pause your subscription for up to 3 months. Your events and data
                                        will be saved, and you won't be charged until you're ready.
                                    </p>
                                    <Button onClick={handleAcceptOffer} className="w-full">
                                        <PauseCircle className="h-4 w-4 mr-2" />
                                        Pause My Subscription
                                    </Button>
                                </div>
                            )}

                            {reason === 'not_using' && (
                                <div className="p-4 bg-primary/5 rounded-lg border border-primary/20 space-y-3">
                                    <div className="flex items-center gap-2 text-primary font-semibold">
                                        <HelpCircle className="h-5 w-5" />
                                        Need Help Getting Started?
                                    </div>
                                    <p className="text-sm text-muted-foreground">
                                        Book a free 15-minute onboarding call with our team. We'll help
                                        you set up your first event and show you tips to maximize value.
                                    </p>
                                    <Button onClick={handleAcceptOffer} className="w-full">
                                        <Calendar className="h-4 w-4 mr-2" />
                                        Book Free Onboarding
                                    </Button>
                                </div>
                            )}

                            <Button variant="ghost" onClick={handleDeclineOffer} className="w-full">
                                No thanks, continue canceling
                            </Button>
                        </div>
                    </>
                )}

                {/* STEP 3: Confirm Cancellation */}
                {step === 'confirm' && (
                    <>
                        <DialogHeader>
                            <DialogTitle className="flex items-center gap-2 text-destructive">
                                <AlertTriangle className="h-5 w-5" />
                                Confirm Cancellation
                            </DialogTitle>
                            <DialogDescription>
                                Your subscription will remain active until {endDate}.
                            </DialogDescription>
                        </DialogHeader>

                        <Alert variant="destructive" className="mt-4">
                            <AlertTriangle className="h-4 w-4" />
                            <AlertDescription>
                                <p className="font-medium mb-2">You'll lose access to:</p>
                                <ul className="text-sm space-y-1">
                                    <li className="flex items-center gap-2">
                                        <Calendar className="h-3 w-3" />
                                        Creating new events
                                    </li>
                                    <li className="flex items-center gap-2">
                                        <Users className="h-3 w-3" />
                                        Managing registrations
                                    </li>
                                    <li className="flex items-center gap-2">
                                        <Award className="h-3 w-3" />
                                        Issuing certificates
                                    </li>
                                </ul>
                            </AlertDescription>
                        </Alert>

                        <div className="flex gap-3 mt-6">
                            <Button variant="outline" onClick={resetAndClose} className="flex-1">
                                Keep Subscription
                            </Button>
                            <Button
                                variant="destructive"
                                onClick={handleConfirmCancel}
                                disabled={processing}
                                className="flex-1"
                            >
                                {processing ? (
                                    <>
                                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                        Canceling...
                                    </>
                                ) : (
                                    'Cancel Subscription'
                                )}
                            </Button>
                        </div>
                    </>
                )}

                {/* STEP 4: Feedback (Post-Cancellation) */}
                {step === 'feedback' && (
                    <>
                        <DialogHeader>
                            <DialogTitle>Subscription Canceled</DialogTitle>
                            <DialogDescription>
                                Your access continues until {endDate}. We'd love your feedback.
                            </DialogDescription>
                        </DialogHeader>

                        <div className="mt-4 space-y-4">
                            <Alert className="bg-muted">
                                <CheckCircle className="h-4 w-4 text-primary" />
                                <AlertDescription>
                                    You can reactivate anytime before {endDate} to keep your data.
                                </AlertDescription>
                            </Alert>

                            <div className="space-y-2">
                                <Label htmlFor="feedback">Any additional feedback? (Optional)</Label>
                                <Textarea
                                    id="feedback"
                                    placeholder="What could we have done better?"
                                    value={feedback}
                                    onChange={(e) => setFeedback(e.target.value)}
                                    rows={3}
                                />
                            </div>

                            <Button onClick={handleSubmitFeedback} className="w-full">
                                {feedback ? 'Submit Feedback & Close' : 'Close'}
                            </Button>
                        </div>
                    </>
                )}
            </DialogContent>
        </Dialog>
    );
}
