import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Clock, X, Zap, ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { getSubscription } from '@/api/billing';
import { Subscription } from '@/api/billing/types';

interface TrialBannerProps {
    className?: string;
}

const DISMISSED_KEY = 'trial_banner_dismissed_until';

export function TrialBanner({ className }: TrialBannerProps) {
    const [subscription, setSubscription] = useState<Subscription | null>(null);
    const [loading, setLoading] = useState(true);
    const [dismissed, setDismissed] = useState(false);

    useEffect(() => {
        // Check if dismissed recently (within last 24 hours)
        const dismissedUntil = localStorage.getItem(DISMISSED_KEY);
        if (dismissedUntil && new Date(dismissedUntil) > new Date()) {
            setDismissed(true);
            setLoading(false);
            return;
        }

        async function fetchSubscription() {
            try {
                const data = await getSubscription();
                setSubscription(data);
            } catch {
                // Not an error if no subscription
            } finally {
                setLoading(false);
            }
        }

        fetchSubscription();
    }, []);

    const handleDismiss = () => {
        // Dismiss for 24 hours
        const tomorrow = new Date();
        tomorrow.setDate(tomorrow.getDate() + 1);
        localStorage.setItem(DISMISSED_KEY, tomorrow.toISOString());
        setDismissed(true);
    };

    if (loading || dismissed) {
        return null;
    }

    // Only show for trialing subscriptions
    if (!subscription || subscription.status !== 'trialing') {
        return null;
    }

    // Calculate days remaining
    const trialEnd = subscription.trial_ends_at
        ? new Date(subscription.trial_ends_at)
        : subscription.current_period_end
            ? new Date(subscription.current_period_end)
            : null;

    if (!trialEnd) {
        return null;
    }

    const now = new Date();
    const daysRemaining = Math.max(0, Math.ceil((trialEnd.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)));

    // Determine urgency level
    const isUrgent = daysRemaining <= 3;
    const isWarning = daysRemaining <= 7 && daysRemaining > 3;

    return (
        <div
            className={cn(
                "relative py-2 px-4 flex items-center justify-between gap-4 text-sm",
                isUrgent
                    ? "bg-red-500 text-white"
                    : isWarning
                        ? "bg-yellow-500 text-yellow-950"
                        : "bg-primary text-primary-foreground",
                className
            )}
        >
            <div className="flex items-center gap-3">
                <div className={cn(
                    "p-1.5 rounded-full",
                    isUrgent
                        ? "bg-red-400"
                        : isWarning
                            ? "bg-yellow-400"
                            : "bg-primary-foreground/20"
                )}>
                    <Clock className="h-4 w-4" />
                </div>
                <span>
                    {daysRemaining === 0 ? (
                        <strong>Your trial expires today!</strong>
                    ) : daysRemaining === 1 ? (
                        <strong>Your trial expires tomorrow!</strong>
                    ) : (
                        <>
                            <strong>{daysRemaining} days</strong> remaining in your Professional trial
                        </>
                    )}
                </span>
            </div>

            <div className="flex items-center gap-2">
                <Button
                    asChild
                    size="sm"
                    variant={isUrgent || isWarning ? "secondary" : "outline"}
                    className={cn(
                        "h-7 text-xs",
                        !isUrgent && !isWarning && "bg-primary-foreground/10 border-primary-foreground/20 text-primary-foreground hover:bg-primary-foreground/20"
                    )}
                >
                    <Link to="/billing">
                        <Zap className="h-3 w-3 mr-1" />
                        Upgrade Now
                        <ArrowRight className="h-3 w-3 ml-1" />
                    </Link>
                </Button>
                <button
                    onClick={handleDismiss}
                    className={cn(
                        "p-1 rounded-full transition-colors",
                        isUrgent
                            ? "hover:bg-red-400"
                            : isWarning
                                ? "hover:bg-yellow-400"
                                : "hover:bg-primary-foreground/20"
                    )}
                    aria-label="Dismiss"
                >
                    <X className="h-4 w-4" />
                </button>
            </div>
        </div>
    );
}
