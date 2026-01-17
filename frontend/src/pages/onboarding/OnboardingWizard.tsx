import React, { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Rocket,
    User,
    Video,
    Calendar,
    BookOpen,
    ArrowRight,
    ArrowLeft,
    Check,
    Crown,
    Loader2,
    ExternalLink,
    Building2,
    CreditCard
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { useAuth } from '@/contexts/AuthContext';
import { updateProfile, completeOnboarding } from '@/api/accounts';
import { initiateZoomOAuth, getZoomStatus } from '@/api/integrations';
import { ZoomStatus } from '@/api/integrations/types';
import { createCheckoutSession } from '@/api/billing';
import { getSubscription } from '@/api/billing';
import { Subscription } from '@/api/billing/types';
import { toast } from 'sonner';

interface OnboardingWizardProps {
    onComplete?: () => void;
}

export function OnboardingWizard({ onComplete }: OnboardingWizardProps) {
    const navigate = useNavigate();
    const { user, refreshManifest, refreshUser } = useAuth();
    const [searchParams, setSearchParams] = useSearchParams();
    const [currentStep, setCurrentStep] = useState(() => {
        const stepParam = searchParams.get('step');
        return stepParam ? parseInt(stepParam, 10) : 0;
    });
    const [isLoading, setIsLoading] = useState(false);

    // Profile state
    const [profileData, setProfileData] = useState({
        organization_name: user?.organization_name || '',
        full_name: user?.full_name || '',
    });

    // Zoom state
    const [zoomStatus, setZoomStatus] = useState<ZoomStatus | null>(null);
    const [zoomChecked, setZoomChecked] = useState(false);

    // Billing state
    const [subscription, setSubscription] = useState<Subscription | null>(null);
    const [billingChecked, setBillingChecked] = useState(false);
    const [addingPayment, setAddingPayment] = useState(false);

    const isLmsOnly = subscription?.plan === 'lms' || (!subscription && user?.account_type === 'course_manager');
    const isAttendee = user?.account_type === 'attendee';
    const planLabel = subscription?.plan_display || (isLmsOnly ? 'LMS' : isAttendee ? 'Free' : 'Organizer');

    const steps = isAttendee
        ? [
            { id: 'welcome', title: 'Welcome', icon: Rocket },
            { id: 'complete', title: 'Get Started', icon: Calendar },
        ]
        : isLmsOnly
            ? [
                { id: 'welcome', title: 'Welcome', icon: Rocket },
                { id: 'profile', title: 'Your Profile', icon: User },
                { id: 'billing', title: 'Billing', icon: CreditCard },
                { id: 'complete', title: 'Get Started', icon: BookOpen },
            ]
            : [
                { id: 'welcome', title: 'Welcome', icon: Rocket },
                { id: 'profile', title: 'Your Profile', icon: User },
                { id: 'billing', title: 'Billing', icon: CreditCard },
                { id: 'integrations', title: 'Integrations', icon: Video },
                { id: 'complete', title: 'Get Started', icon: Calendar },
            ];

    const progress = ((currentStep + 1) / steps.length) * 100;
    const stepId = steps[currentStep]?.id;
    const getStepIndex = (id: string) => steps.findIndex(step => step.id === id);

    const nextStep = () => {
        if (currentStep < steps.length - 1) {
            setCurrentStep(prev => prev + 1);
        }
    };

    const prevStep = () => {
        if (currentStep > 0) {
            setCurrentStep(prev => prev - 1);
        }
    };

    const handleProfileSubmit = async () => {
        setIsLoading(true);
        try {
            await updateProfile({
                organization_name: profileData.organization_name,
                full_name: profileData.full_name,
            });
            toast.success("Profile updated!");
            nextStep();
        } catch (error) {
            toast.error("Failed to update profile");
        } finally {
            setIsLoading(false);
        }
    };

    const checkZoomStatus = async () => {
        try {
            const status = await getZoomStatus();
            setZoomStatus(status);
            setZoomChecked(true);
        } catch {
            setZoomChecked(true);
        }
    };

    const checkBillingStatus = async () => {
        try {
            const sub = await getSubscription();
            setSubscription(sub);
            setBillingChecked(true);
        } catch {
            setBillingChecked(true);
        }
    };

    const handleConnectZoom = async () => {
        try {
            const url = await initiateZoomOAuth();
            // Store that we're in onboarding so callback can redirect back
            const stepIndex = getStepIndex('integrations');
            if (stepIndex >= 0) {
                sessionStorage.setItem('onboarding_redirect', `/onboarding?step=${stepIndex}`);
            }
            window.location.href = url;
        } catch (error) {
            toast.error("Failed to initiate Zoom connection");
        }
    };

    const handleAddPayment = async () => {
        setAddingPayment(true);
        try {
            // Store current onboarding step so we can return after Stripe
            const stepIndex = getStepIndex('billing');
            if (stepIndex >= 0) {
                sessionStorage.setItem('onboarding_redirect', `/onboarding?step=${stepIndex}`);
            }
            const result = await createCheckoutSession(
                subscription?.plan || 'organizer',
                `${window.location.origin}/onboarding?step=${getStepIndex('billing')}&checkout=success`,
                `${window.location.origin}/onboarding?step=${getStepIndex('billing')}&checkout=canceled`
            );
            window.location.href = result.url;
        } catch (error: any) {
            toast.error(error?.response?.data?.error?.message || 'Failed to start checkout.');
            setAddingPayment(false);
        }
    };

    const handleComplete = async () => {
        try {
            // Mark onboarding as complete on the backend
            await completeOnboarding();
            // Refresh user state and manifest to reflect the change
            await Promise.all([refreshUser(), refreshManifest()]);
            toast.success("You're all set! Welcome aboard.");

            if (onComplete) {
                onComplete();
            } else {
                navigate('/dashboard');
            }
        } catch (error) {
            // If API fails, still navigate to dashboard
            console.error('Failed to complete onboarding:', error);
            navigate('/dashboard');
        }
    };

    // Sync currentStep with URL
    React.useEffect(() => {
        setSearchParams({ step: currentStep.toString() }, { replace: true });
    }, [currentStep, setSearchParams]);

    // Load zoom status when reaching integrations step
    React.useEffect(() => {
        if (stepId === 'integrations' && !zoomChecked) {
            checkZoomStatus();
        }
    }, [stepId, zoomChecked]);

    // Load billing status when reaching billing step
    React.useEffect(() => {
        // Fetch subscription data on mount for non-attendees (needed for trial days on welcome step)
        if (!isAttendee && !billingChecked) {
            checkBillingStatus();
        }
    }, [isAttendee, billingChecked]);

    // Handle checkout success/canceled return from Stripe
    React.useEffect(() => {
        const checkoutStatus = searchParams.get('checkout');
        const sessionId = searchParams.get('session_id');

        if (checkoutStatus === 'success' && sessionId) {
            // Call confirmCheckout to sync subscription from Stripe
            (async () => {
                try {
                    // Import confirmCheckout from billing API
                    const { confirmCheckout } = await import('@/api/billing');

                    // Confirm checkout with Stripe session ID - this syncs the subscription
                    const updatedSub = await confirmCheckout(sessionId);
                    setSubscription(updatedSub);
                    setBillingChecked(true);

                    // Payment method is now confirmed, advance to next step
                    toast.success('Payment method added successfully!');
                    // Clear the checkout params and advance to the next step (integrations for organizers)
                    const nextStepIndex = getStepIndex('billing') + 1;
                    setSearchParams({ step: nextStepIndex.toString() }, { replace: true });
                    setCurrentStep(nextStepIndex);
                } catch (error: any) {
                    console.error('Failed to confirm checkout:', error);
                    toast.error(error?.response?.data?.error?.message || 'Failed to confirm payment. Please try again.');
                    // Still try to refresh subscription status
                    try {
                        const sub = await getSubscription();
                        setSubscription(sub);
                        setBillingChecked(true);
                    } catch {
                        // ignore
                    }
                    // Clear checkout params but stay on billing step
                    setSearchParams({ step: currentStep.toString() }, { replace: true });
                }
            })();
        } else if (checkoutStatus === 'success' && !sessionId) {
            // Fallback: checkout=success but no session_id (shouldn't happen but handle gracefully)
            console.warn('Checkout success but no session_id in URL');
            (async () => {
                try {
                    const sub = await getSubscription();
                    setSubscription(sub);
                    setBillingChecked(true);
                    if (sub?.has_payment_method) {
                        toast.success('Payment method added!');
                        // Advance to the next step (integrations for organizers)
                        const nextStepIndex = getStepIndex('billing') + 1;
                        setSearchParams({ step: nextStepIndex.toString() }, { replace: true });
                        setCurrentStep(nextStepIndex);
                    }
                } catch (error) {
                    console.error('Failed to refresh subscription:', error);
                }
            })();
        } else if (checkoutStatus === 'canceled') {
            toast.info('Checkout was canceled. You can try again or skip for now.');
            // Clear the checkout param
            setSearchParams({ step: currentStep.toString() }, { replace: true });
        }
    }, [searchParams]);

    return (
        <div className="min-h-screen bg-gradient-to-br from-background to-muted/30 flex items-center justify-center p-4">
            <div className="w-full max-w-2xl">
                {/* Progress Header */}
                <div className="mb-8">
                    <div className="flex items-center justify-between mb-4">
                        {steps.map((step, index) => {
                            const Icon = step.icon;
                            const isComplete = index < currentStep;
                            const isCurrent = index === currentStep;

                            return (
                                <div
                                    key={step.id}
                                    className={`flex items-center gap-2 ${isCurrent ? 'text-primary' : isComplete ? 'text-success' : 'text-muted-foreground'
                                        }`}
                                >
                                    <div className={`
                                        w-10 h-10 rounded-full flex items-center justify-center
                                        ${isCurrent ? 'bg-primary text-primary-foreground' :
                                            isComplete ? 'bg-success text-success-foreground' :
                                                'bg-muted'}
                                    `}>
                                        {isComplete ? <Check className="h-5 w-5" /> : <Icon className="h-5 w-5" />}
                                    </div>
                                    <span className="hidden sm:block text-sm font-medium">{step.title}</span>
                                </div>
                            );
                        })}
                    </div>
                    <Progress value={progress} className="h-2" />
                </div>

                {/* Step Content */}
                <AnimatePresence mode="wait">
                    <motion.div
                        key={currentStep}
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -20 }}
                        transition={{ duration: 0.3 }}
                    >
                        <Card className="border-2">
                            {/* Step 0: Welcome */}
                            {stepId === 'welcome' && (
                                <>
                                    <CardHeader className="text-center pb-2">
                                        <div className="mx-auto bg-primary/10 rounded-full p-4 w-20 h-20 flex items-center justify-center mb-4">
                                            <Rocket className="h-10 w-10 text-primary" />
                                        </div>
                                        <CardTitle className="text-2xl">Welcome to Accredit! 🎉</CardTitle>
                                        <CardDescription className="text-base">
                                            {isAttendee
                                                ? "You're all set to discover professional development opportunities"
                                                : isLmsOnly
                                                    ? "Let's get you set up to launch impactful courses"
                                                    : "Let's get you set up to create amazing CPD events"}
                                        </CardDescription>
                                    </CardHeader>
                                    <CardContent className="space-y-6 text-center">
                                        {isAttendee ? (
                                            <>
                                                <div className="grid grid-cols-3 gap-4 text-center">
                                                    <div className="p-4 bg-muted/30 rounded-lg">
                                                        <div className="h-8 w-8 mx-auto rounded-lg bg-primary/10 flex items-center justify-center mb-2">
                                                            <Calendar className="h-4 w-4 text-primary" />
                                                        </div>
                                                        <div className="text-sm font-medium text-foreground">Browse Events</div>
                                                        <div className="text-xs text-muted-foreground">Find CPD opportunities</div>
                                                    </div>
                                                    <div className="p-4 bg-muted/30 rounded-lg">
                                                        <div className="h-8 w-8 mx-auto rounded-lg bg-accent/10 flex items-center justify-center mb-2">
                                                            <BookOpen className="h-4 w-4 text-accent" />
                                                        </div>
                                                        <div className="text-sm font-medium text-foreground">Take Courses</div>
                                                        <div className="text-xs text-muted-foreground">Learn at your pace</div>
                                                    </div>
                                                    <div className="p-4 bg-muted/30 rounded-lg">
                                                        <div className="h-8 w-8 mx-auto rounded-lg bg-success/10 flex items-center justify-center mb-2">
                                                            <Check className="h-4 w-4 text-success" />
                                                        </div>
                                                        <div className="text-sm font-medium text-foreground">Earn Certificates</div>
                                                        <div className="text-xs text-muted-foreground">Track your CPD</div>
                                                    </div>
                                                </div>
                                            </>
                                        ) : (
                                            <>
                                                <div className="bg-primary/5 rounded-lg p-4 border border-primary/20">
                                                    <div className="flex items-center justify-center gap-2 text-primary font-medium mb-1">
                                                        <Crown className="h-4 w-4" />
                                                        <span>Professional Trial Active</span>
                                                    </div>
                                                    <p className="text-sm text-muted-foreground">
                                                        You have {subscription?.days_until_trial_ends ?? '...'} days of full access to all features
                                                    </p>
                                                </div>

                                                <div className="grid grid-cols-2 gap-4 text-center">
                                                    <div className="p-4 bg-muted/30 rounded-lg">
                                                        <div className="text-2xl font-bold text-primary">∞</div>
                                                        <div className="text-sm text-muted-foreground">
                                                            {isLmsOnly ? 'Courses' : 'Events'}
                                                        </div>
                                                    </div>
                                                    <div className="p-4 bg-muted/30 rounded-lg">
                                                        <div className="text-2xl font-bold text-primary">∞</div>
                                                        <div className="text-sm text-muted-foreground">Certificates</div>
                                                    </div>
                                                </div>
                                            </>
                                        )}

                                        <Button size="lg" onClick={nextStep} className="w-full">
                                            {isAttendee ? "Let's Go!" : "Let's Get Started"}
                                            <ArrowRight className="ml-2 h-4 w-4" />
                                        </Button>
                                    </CardContent>
                                </>
                            )}

                            {/* Step 1: Profile */}
                            {stepId === 'profile' && (
                                <>
                                    <CardHeader className="text-center pb-2">
                                        <div className="mx-auto bg-primary/10 rounded-full p-4 w-16 h-16 flex items-center justify-center mb-2">
                                            <Building2 className="h-8 w-8 text-primary" />
                                        </div>
                                        <CardTitle>Set Up Your Profile</CardTitle>
                                        <CardDescription>
                                            {isLmsOnly
                                                ? 'This info will appear on your courses and certificates'
                                                : 'This info will appear on your events and certificates'}
                                        </CardDescription>
                                    </CardHeader>
                                    <CardContent className="space-y-4">
                                        <div className="space-y-2">
                                            <Label htmlFor="full_name">Your Name</Label>
                                            <Input
                                                id="full_name"
                                                value={profileData.full_name}
                                                onChange={e => setProfileData(prev => ({ ...prev, full_name: e.target.value }))}
                                                placeholder="Dr. Jane Smith"
                                            />
                                        </div>

                                        <div className="space-y-2">
                                            <Label htmlFor="organization_name">
                                                {isLmsOnly ? 'Organization / Brand (Optional)' : 'Organization / Company Name'}
                                            </Label>
                                            <Input
                                                id="organization_name"
                                                value={profileData.organization_name}
                                                onChange={e => setProfileData(prev => ({ ...prev, organization_name: e.target.value }))}
                                                placeholder="Healthcare Training Institute"
                                            />
                                            <p className="text-xs text-muted-foreground">
                                                {isLmsOnly ? 'Shown on course certificates and landing pages' : 'This will be shown as the event organizer'}
                                            </p>
                                        </div>

                                        <div className="flex gap-3 pt-4">
                                            <Button variant="outline" onClick={prevStep}>
                                                <ArrowLeft className="mr-2 h-4 w-4" />
                                                Back
                                            </Button>
                                            <Button
                                                className="flex-1"
                                                onClick={handleProfileSubmit}
                                                disabled={isLoading || !profileData.full_name || (!isLmsOnly && !profileData.organization_name)}
                                            >
                                                {isLoading ? (
                                                    <Loader2 className="h-4 w-4 animate-spin" />
                                                ) : (
                                                    <>
                                                        Continue
                                                        <ArrowRight className="ml-2 h-4 w-4" />
                                                    </>
                                                )}
                                            </Button>
                                        </div>
                                    </CardContent>
                                </>
                            )}

                            {/* Step 2: Integrations (Zoom) */}
                            {stepId === 'integrations' && (
                                <>
                                    <CardHeader className="text-center pb-2">
                                        <div className="mx-auto bg-blue-100 rounded-full p-4 w-16 h-16 flex items-center justify-center mb-2">
                                            <Video className="h-8 w-8 text-blue-600" />
                                        </div>
                                        <CardTitle>Connect Zoom</CardTitle>
                                        <CardDescription>
                                            Enable automatic meeting creation and attendance tracking
                                        </CardDescription>
                                    </CardHeader>
                                    <CardContent className="space-y-4">
                                        {!zoomChecked ? (
                                            <div className="flex justify-center py-8">
                                                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                                            </div>
                                        ) : zoomStatus?.is_connected ? (
                                            <div className="bg-success/10 border border-success/30 rounded-lg p-4 text-center">
                                                <Check className="h-8 w-8 text-success mx-auto mb-2" />
                                                <p className="font-medium text-success">Zoom Connected!</p>
                                                <p className="text-sm text-muted-foreground mt-1">
                                                    {zoomStatus.zoom_email}
                                                </p>
                                            </div>
                                        ) : (
                                            <div className="space-y-4">
                                                <div className="bg-muted/30 rounded-lg p-4 space-y-2">
                                                    <h4 className="font-medium">Why connect Zoom?</h4>
                                                    <ul className="text-sm text-muted-foreground space-y-1">
                                                        <li className="flex items-center gap-2">
                                                            <Check className="h-4 w-4 text-primary" />
                                                            Auto-create Zoom meetings for events
                                                        </li>
                                                        <li className="flex items-center gap-2">
                                                            <Check className="h-4 w-4 text-primary" />
                                                            Track attendance automatically
                                                        </li>
                                                        <li className="flex items-center gap-2">
                                                            <Check className="h-4 w-4 text-primary" />
                                                            Issue certificates based on attendance
                                                        </li>
                                                    </ul>
                                                </div>

                                                <Button
                                                    className="w-full bg-blue-600 hover:bg-blue-700"
                                                    onClick={handleConnectZoom}
                                                >
                                                    <Video className="mr-2 h-4 w-4" />
                                                    Connect Zoom Account
                                                    <ExternalLink className="ml-2 h-4 w-4" />
                                                </Button>
                                            </div>
                                        )}

                                        <div className="flex gap-3 pt-4">
                                            <Button variant="outline" onClick={prevStep}>
                                                <ArrowLeft className="mr-2 h-4 w-4" />
                                                Back
                                            </Button>
                                            <Button className="flex-1" onClick={nextStep}>
                                                {zoomStatus?.is_connected ? 'Continue' : 'Skip for Now'}
                                                <ArrowRight className="ml-2 h-4 w-4" />
                                            </Button>
                                        </div>
                                    </CardContent>
                                </>
                            )}



                            {/* Step 3: Billing (Optional) */}
                            {stepId === 'billing' && (
                                <>
                                    <CardHeader className="text-center pb-2">
                                        <div className="mx-auto bg-primary/10 rounded-full p-4 w-16 h-16 flex items-center justify-center mb-2">
                                            <CreditCard className="h-8 w-8 text-primary" />
                                        </div>
                                        <CardTitle>Add Billing Details</CardTitle>
                                        <CardDescription>
                                            Optional - Add your payment method now or anytime later
                                        </CardDescription>
                                    </CardHeader>
                                    <CardContent className="space-y-4">
                                        {!billingChecked ? (
                                            <div className="flex justify-center py-8">
                                                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                                            </div>
                                        ) : subscription?.has_payment_method ? (
                                            <div className="bg-success/10 border border-success/30 rounded-lg p-4 text-center">
                                                <Check className="h-8 w-8 text-success mx-auto mb-2" />
                                                <p className="font-medium text-success">Billing Details Added!</p>
                                                <p className="text-sm text-muted-foreground mt-1">
                                                    You're all set for automatic billing after your trial
                                                </p>
                                            </div>
                                        ) : (
                                            <div className="space-y-4">
                                                <div className="bg-muted/30 rounded-lg p-4 space-y-3">
                                                    <div className="flex items-center justify-between">
                                                        <span className="text-sm text-muted-foreground">Plan</span>
                                                        <span className="font-medium">{planLabel} Plan</span>
                                                    </div>
                                                    <div className="flex items-center justify-between">
                                                        <span className="text-sm text-muted-foreground">Trial ends</span>
                                                        <Badge variant="secondary">{subscription?.days_until_trial_ends ?? '...'} days remaining</Badge>
                                                    </div>
                                                    <p className="text-xs text-muted-foreground pt-2 border-t">
                                                        Your card won't be charged until your trial ends. Cancel anytime.
                                                    </p>
                                                </div>

                                                <Button
                                                    className="w-full"
                                                    onClick={handleAddPayment}
                                                    disabled={addingPayment}
                                                >
                                                    {addingPayment ? (
                                                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                                    ) : (
                                                        <CreditCard className="mr-2 h-4 w-4" />
                                                    )}
                                                    Add Payment Method
                                                </Button>
                                            </div>
                                        )}

                                        <div className="flex gap-3 pt-4">
                                            <Button variant="outline" onClick={prevStep}>
                                                <ArrowLeft className="mr-2 h-4 w-4" />
                                                Back
                                            </Button>
                                            <Button className="flex-1" onClick={nextStep}>
                                                {subscription?.has_payment_method ? 'Continue' : 'Skip for Now'}
                                                <ArrowRight className="ml-2 h-4 w-4" />
                                            </Button>
                                        </div>
                                    </CardContent>
                                </>
                            )}

                            {/* Step 4: Complete */}
                            {stepId === 'complete' && (
                                <>
                                    <CardHeader className="text-center pb-2">
                                        <div className="mx-auto bg-success/10 rounded-full p-4 w-20 h-20 flex items-center justify-center mb-4">
                                            <Check className="h-10 w-10 text-success" />
                                        </div>
                                        <CardTitle className="text-2xl">You're All Set! 🎉</CardTitle>
                                        <CardDescription className="text-base">
                                            Your account is ready. What would you like to do first?
                                        </CardDescription>
                                    </CardHeader>
                                    <CardContent className="space-y-4">
                                        <div className="grid gap-3">
                                            {isAttendee ? (
                                                <>
                                                    <Button
                                                        size="lg"
                                                        className="w-full h-auto py-4"
                                                        onClick={() => {
                                                            handleComplete();
                                                            navigate('/events/browse');
                                                        }}
                                                    >
                                                        <Calendar className="mr-3 h-5 w-5" />
                                                        <div className="text-left">
                                                            <div className="font-medium">Browse Events</div>
                                                            <div className="text-xs opacity-80">Find CPD opportunities</div>
                                                        </div>
                                                        <ArrowRight className="ml-auto h-5 w-5" />
                                                    </Button>

                                                    <Button
                                                        variant="outline"
                                                        size="lg"
                                                        className="w-full h-auto py-4"
                                                        onClick={() => {
                                                            handleComplete();
                                                            navigate('/courses');
                                                        }}
                                                    >
                                                        <BookOpen className="mr-3 h-5 w-5 text-muted-foreground" />
                                                        <div className="text-left">
                                                            <div className="font-medium">Explore Courses</div>
                                                            <div className="text-xs text-muted-foreground">Learn at your own pace</div>
                                                        </div>
                                                        <ArrowRight className="ml-auto h-5 w-5" />
                                                    </Button>
                                                </>
                                            ) : (
                                                <>
                                                    <Button
                                                        size="lg"
                                                        className="w-full h-auto py-4"
                                                        onClick={() => {
                                                            handleComplete();
                                                            navigate(isLmsOnly ? '/courses/manage/new' : '/events/create');
                                                        }}
                                                    >
                                                        {isLmsOnly ? (
                                                            <BookOpen className="mr-3 h-5 w-5" />
                                                        ) : (
                                                            <Calendar className="mr-3 h-5 w-5" />
                                                        )}
                                                        <div className="text-left">
                                                            <div className="font-medium">
                                                                {isLmsOnly ? 'Create Your First Course' : 'Create Your First Event'}
                                                            </div>
                                                            <div className="text-xs opacity-80">
                                                                {isLmsOnly ? 'Launch your first learning experience' : 'Start engaging your audience'}
                                                            </div>
                                                        </div>
                                                        <ArrowRight className="ml-auto h-5 w-5" />
                                                    </Button>

                                                    <Button
                                                        variant="outline"
                                                        size="lg"
                                                        className="w-full h-auto py-4"
                                                        onClick={handleComplete}
                                                    >
                                                        <Rocket className="mr-3 h-5 w-5 text-muted-foreground" />
                                                        <div className="text-left">
                                                            <div className="font-medium">Explore Dashboard</div>
                                                            <div className="text-xs text-muted-foreground">Get familiar with the platform</div>
                                                        </div>
                                                        <ArrowRight className="ml-auto h-5 w-5" />
                                                    </Button>
                                                </>
                                            )}
                                        </div>
                                    </CardContent>
                                </>
                            )}
                        </Card>
                    </motion.div>
                </AnimatePresence>
            </div>


        </div>
    );
}
