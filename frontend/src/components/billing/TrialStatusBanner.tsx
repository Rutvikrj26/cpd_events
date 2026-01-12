import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertTriangle, Clock, Crown, XCircle, ArrowRight, CreditCard, Loader2 } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Subscription } from '@/api/billing/types';
import { createCheckoutSession } from '@/api/billing';
import { toast } from 'sonner';

interface TrialStatusBannerProps {
    subscription: Subscription | null;
}

export function TrialStatusBanner({ subscription }: TrialStatusBannerProps) {
    const [loading, setLoading] = useState(false);

    if (!subscription) return null;

    // Active paid subscription - no banner needed
    if (subscription.status === 'active' && !subscription.is_trialing && subscription.plan !== 'attendee') {
        return null;
    }

    // Trialing with payment method added - no banner needed (billing secured)
    if (subscription.is_trialing && subscription.has_payment_method) {
        return null;
    }

    const handleAddBilling = async () => {
        setLoading(true);
        try {
            // Redirect to Stripe Checkout to add billing and confirm subscription
            const result = await createCheckoutSession(
                subscription.plan || 'organizer',
                `${window.location.origin}/billing?checkout=success`,
                `${window.location.origin}/billing?checkout=canceled`
            );
            window.location.href = result.url;
        } catch (error: any) {
            toast.error(error?.response?.data?.error?.message || 'Failed to start checkout. Please try again.');
            setLoading(false);
        }
    };

    const isLmsPlan = subscription.plan === 'lms';
    const creationNoun = isLmsPlan ? 'courses' : 'events';
    const planLabel = subscription.plan_display || (isLmsPlan ? 'LMS' : 'Organizer');

    // Attendee plan - show upgrade prompt
    if (subscription.plan === 'attendee' && subscription.status === 'active') {
        return (
            <Alert className="bg-primary/5 border-primary/20">
                <Crown className="h-4 w-4 text-primary" />
                <AlertTitle className="text-sm font-medium">Attendee Plan</AlertTitle>
                <AlertDescription className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">
                        Upgrade to create more {creationNoun} and unlock paid features.
                    </span>
                    <Link to="/billing">
                        <Button size="sm" variant="outline" className="ml-4">
                            View Plans
                            <ArrowRight className="ml-1 h-3 w-3" />
                        </Button>
                    </Link>
                </AlertDescription>
            </Alert>
        );
    }

    // Trialing - show days remaining with Add Billing Details button
    if (subscription.is_trialing && subscription.days_until_trial_ends !== null) {
        const daysLeft = subscription.days_until_trial_ends;
        const isUrgent = daysLeft <= 7;

        return (
            <Alert className={isUrgent ? "bg-warning/10 border-warning/30" : "bg-success/10 border-success/30"}>
                <Clock className={`h-4 w-4 ${isUrgent ? 'text-warning' : 'text-success'}`} />
                <AlertTitle className="text-sm font-medium flex items-center gap-2">
                    {planLabel} Trial
                    <Badge variant={isUrgent ? "destructive" : "secondary"} className="text-xs">
                        {daysLeft} day{daysLeft !== 1 ? 's' : ''} left
                    </Badge>
                </AlertTitle>
                <AlertDescription className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">
                        {isUrgent
                            ? "Your trial is ending soon. Add billing details to keep your features."
                            : `You have full access to all ${planLabel} features. Add billing details to continue after trial.`
                        }
                    </span>
                    <Button
                        size="sm"
                        variant={isUrgent ? "default" : "outline"}
                        onClick={handleAddBilling}
                        disabled={loading}
                        className="ml-4"
                    >
                        {loading ? (
                            <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                        ) : (
                            <CreditCard className="h-3 w-3 mr-1" />
                        )}
                        Add Billing Details
                    </Button>
                </AlertDescription>
            </Alert>
        );
    }

    // Trial expired - in grace period
    if (subscription.is_in_grace_period) {
        return (
            <Alert variant="destructive" className="bg-destructive/10">
                <AlertTriangle className="h-4 w-4" />
                <AlertTitle className="text-sm font-medium">Trial Expired</AlertTitle>
                <AlertDescription className="flex items-center justify-between">
                    <span className="text-sm">
                        Your trial has ended. <strong>You can no longer create new {creationNoun}.</strong>
                        Add billing details to restore full access.
                    </span>
                    <Button
                        size="sm"
                        variant="destructive"
                        className="ml-4"
                        onClick={handleAddBilling}
                        disabled={loading}
                    >
                        {loading ? (
                            <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                        ) : (
                            <CreditCard className="h-3 w-3 mr-1" />
                        )}
                        Add Billing Details
                    </Button>
                </AlertDescription>
            </Alert>
        );
    }

    // Access blocked - after grace period
    if (subscription.is_access_blocked) {
        return (
            <Alert variant="destructive">
                <XCircle className="h-4 w-4" />
                <AlertTitle className="text-sm font-medium">Access Suspended</AlertTitle>
                <AlertDescription className="flex items-center justify-between">
                    <span className="text-sm">
                        Your subscription has expired. Please add billing details to regain access.
                    </span>
                    <Button
                        size="sm"
                        variant="destructive"
                        className="ml-4"
                        onClick={handleAddBilling}
                        disabled={loading}
                    >
                        {loading ? (
                            <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                        ) : (
                            <CreditCard className="h-3 w-3 mr-1" />
                        )}
                        Reactivate Account
                    </Button>
                </AlertDescription>
            </Alert>
        );
    }

    return null;
}
