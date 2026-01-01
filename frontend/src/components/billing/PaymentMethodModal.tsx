import React, { useState, useEffect } from 'react';
import { Elements, CardElement, useStripe, useElements } from '@stripe/react-stripe-js';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, CreditCard, CheckCircle, Calendar } from 'lucide-react';
import { getStripe } from '@/lib/stripe';
import { createSetupIntent, addPaymentMethod } from '@/api/billing';
import { Subscription } from '@/api/billing/types';

interface PaymentMethodModalProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    subscription: Subscription | null;
    onSuccess?: () => void;
}

const CARD_ELEMENT_OPTIONS = {
    style: {
        base: {
            fontSize: '16px',
            color: '#1a1a2e',
            fontFamily: 'Inter, system-ui, sans-serif',
            '::placeholder': {
                color: '#9ca3af',
            },
        },
        invalid: {
            color: '#ef4444',
        },
    },
    // Hide postal code - we handle North American (US/Canada) without it
    hidePostalCode: true,
};

function PaymentForm({
    clientSecret,
    trialEndsAt,
    subscription,
    onSuccess,
    onClose
}: {
    clientSecret: string;
    trialEndsAt: string | null;
    subscription: Subscription | null;
    onSuccess?: () => void;
    onClose: () => void;
}) {
    const stripe = useStripe();
    const elements = useElements();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!stripe || !elements) return;

        const cardElement = elements.getElement(CardElement);
        if (!cardElement) return;

        setLoading(true);
        setError(null);

        try {
            const { setupIntent, error: setupError } = await stripe.confirmCardSetup(clientSecret, {
                payment_method: {
                    card: cardElement,
                },
            });

            if (setupError) {
                setError(setupError.message || 'Failed to save payment method');
                setLoading(false);
                return;
            }

            if (setupIntent?.payment_method) {
                // Save to backend
                await addPaymentMethod(setupIntent.payment_method as string, true);
                setSuccess(true);
            }
        } catch (err: any) {
            setError(err.message || 'Failed to save payment method');
        } finally {
            setLoading(false);
        }
    };

    // Calculate next billing date
    const getNextBillingDate = () => {
        if (trialEndsAt) {
            return new Date(trialEndsAt).toLocaleDateString('en-US', {
                month: 'long',
                day: 'numeric',
                year: 'numeric',
            });
        }
        // Default to 30 days from now
        const date = new Date();
        date.setDate(date.getDate() + 30);
        return date.toLocaleDateString('en-US', {
            month: 'long',
            day: 'numeric',
            year: 'numeric',
        });
    };

    if (success) {
        return (
            <div className="py-8 text-center space-y-6">
                <div className="mx-auto w-16 h-16 bg-success/10 rounded-full flex items-center justify-center">
                    <CheckCircle className="h-8 w-8 text-success" />
                </div>
                <div>
                    <h3 className="text-xl font-semibold text-foreground mb-2">Payment Method Added!</h3>
                    <p className="text-muted-foreground">Your billing details have been saved securely.</p>
                </div>

                <div className="bg-muted/50 rounded-lg p-4 space-y-3">
                    <div className="flex items-center justify-between">
                        <span className="text-sm text-muted-foreground">Current Plan</span>
                        <span className="font-medium text-foreground capitalize">
                            {subscription?.plan || 'Organizer'}
                        </span>
                    </div>
                    <div className="flex items-center justify-between">
                        <span className="text-sm text-muted-foreground">Monthly Price</span>
                        <span className="font-medium text-foreground">$30/month</span>
                    </div>
                    <div className="border-t border-border pt-3 flex items-center justify-between">
                        <span className="text-sm text-muted-foreground flex items-center gap-2">
                            <Calendar className="h-4 w-4" />
                            Next Billing Date
                        </span>
                        <span className="font-semibold text-primary">{getNextBillingDate()}</span>
                    </div>
                </div>

                <p className="text-xs text-muted-foreground">
                    You'll continue to enjoy full access during your trial.
                    Your first charge will be on {getNextBillingDate()}.
                </p>

                <Button onClick={() => { onSuccess?.(); onClose(); }} className="w-full">
                    Done
                </Button>
            </div>
        );
    }

    return (
        <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-4">
                <div className="space-y-2">
                    <label className="text-sm font-medium text-foreground">Card Details</label>
                    <div className="border border-input rounded-md p-3 bg-background focus-within:ring-2 focus-within:ring-primary/20 focus-within:border-primary transition-all">
                        <CardElement options={CARD_ELEMENT_OPTIONS} />
                    </div>
                </div>

                {error && (
                    <Alert variant="destructive">
                        <AlertDescription>{error}</AlertDescription>
                    </Alert>
                )}

                <div className="bg-muted/50 rounded-lg p-4 space-y-2">
                    <div className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground">Plan</span>
                        <span className="font-medium capitalize">{subscription?.plan || 'Organizer'} - $30/mo</span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground">First billing date</span>
                        <span className="font-medium text-primary">{getNextBillingDate()}</span>
                    </div>
                </div>

                <p className="text-xs text-muted-foreground text-center">
                    Your card won't be charged until your trial ends. Cancel anytime.
                </p>
            </div>

            <div className="flex gap-3">
                <Button type="button" variant="outline" className="flex-1" onClick={onClose} disabled={loading}>
                    Cancel
                </Button>
                <Button type="submit" className="flex-1" disabled={loading || !stripe}>
                    {loading ? (
                        <>
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            Saving...
                        </>
                    ) : (
                        <>
                            <CreditCard className="h-4 w-4 mr-2" />
                            Add Payment Method
                        </>
                    )}
                </Button>
            </div>
        </form>
    );
}

export function PaymentMethodModal({ open, onOpenChange, subscription, onSuccess }: PaymentMethodModalProps) {
    const [clientSecret, setClientSecret] = useState<string | null>(null);
    const [trialEndsAt, setTrialEndsAt] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [stripePromise] = useState(() => getStripe());

    useEffect(() => {
        if (open && !clientSecret) {
            setLoading(true);
            setError(null);

            createSetupIntent()
                .then((data) => {
                    setClientSecret(data.client_secret);
                    setTrialEndsAt(data.trial_ends_at);
                })
                .catch((err) => {
                    setError(err.message || 'Failed to initialize payment form');
                })
                .finally(() => {
                    setLoading(false);
                });
        }
    }, [open, clientSecret]);

    const handleClose = () => {
        onOpenChange(false);
        // Reset state after close animation
        setTimeout(() => {
            setClientSecret(null);
            setTrialEndsAt(null);
            setError(null);
        }, 300);
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-md">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <CreditCard className="h-5 w-5 text-primary" />
                        Add Billing Details
                    </DialogTitle>
                    <DialogDescription>
                        Securely save your payment method to continue after your trial.
                    </DialogDescription>
                </DialogHeader>

                {loading && (
                    <div className="py-12 text-center">
                        <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto mb-4" />
                        <p className="text-muted-foreground">Loading payment form...</p>
                    </div>
                )}

                {error && !loading && (
                    <Alert variant="destructive">
                        <AlertDescription>{error}</AlertDescription>
                    </Alert>
                )}

                {clientSecret && stripePromise && !loading && (
                    <Elements stripe={stripePromise} options={{ clientSecret }}>
                        <PaymentForm
                            clientSecret={clientSecret}
                            trialEndsAt={trialEndsAt}
                            subscription={subscription}
                            onSuccess={onSuccess}
                            onClose={handleClose}
                        />
                    </Elements>
                )}
            </DialogContent>
        </Dialog>
    );
}
