import React, { useState } from 'react';
import {
    PaymentElement,
    Elements,
    useStripe,
    useElements,
} from '@stripe/react-stripe-js';
import { getStripe } from '@/lib/stripe';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, CreditCard, AlertCircle, CheckCircle } from 'lucide-react';

interface PaymentFormProps {
    clientSecret: string;
    amount: number;
    currency: string;
    onSuccess: () => void;
    onError: (error: string) => void;
}

/**
 * Inner form component that uses Stripe hooks.
 */
function CheckoutForm({ amount, currency, onSuccess, onError }: Omit<PaymentFormProps, 'clientSecret'>) {
    const stripe = useStripe();
    const elements = useElements();
    const [isProcessing, setIsProcessing] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!stripe || !elements) {
            return;
        }

        setIsProcessing(true);
        setError(null);

        const { error: submitError } = await elements.submit();
        if (submitError) {
            setError(submitError.message || 'Payment failed');
            setIsProcessing(false);
            return;
        }

        const { error: confirmError, paymentIntent } = await stripe.confirmPayment({
            elements,
            confirmParams: {
                return_url: `${window.location.origin}/registration/success`,
            },
            redirect: 'if_required',
        });

        if (confirmError) {
            setError(confirmError.message || 'Payment confirmation failed');
            onError(confirmError.message || 'Payment failed');
            setIsProcessing(false);
        } else if (paymentIntent?.status === 'succeeded') {
            onSuccess();
        } else {
            // Handle other statuses like 'requires_action'
            setError('Payment requires additional action');
            setIsProcessing(false);
        }
    };

    const formattedAmount = new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: currency.toUpperCase(),
    }).format(amount);

    return (
        <form onSubmit={handleSubmit} className="space-y-4">
            <div className="bg-muted/30 rounded-lg p-4 border">
                <div className="flex items-center justify-between mb-4">
                    <span className="text-sm font-medium text-muted-foreground">Amount Due</span>
                    <span className="text-xl font-bold text-foreground">{formattedAmount}</span>
                </div>
                <PaymentElement
                    options={{
                        layout: 'tabs',
                    }}
                />
            </div>

            {error && (
                <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>{error}</AlertDescription>
                </Alert>
            )}

            <Button
                type="submit"
                disabled={!stripe || isProcessing}
                className="w-full py-6 text-lg bg-primary hover:bg-primary/90"
            >
                {isProcessing ? (
                    <>
                        <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                        Processing Payment...
                    </>
                ) : (
                    <>
                        <CreditCard className="mr-2 h-5 w-5" />
                        Pay {formattedAmount}
                    </>
                )}
            </Button>

            <p className="text-xs text-center text-muted-foreground">
                Payments are securely processed by Stripe. Your card details are never stored on our servers.
            </p>
        </form>
    );
}

/**
 * Payment form wrapper that initializes Stripe Elements.
 */
export function PaymentForm({ clientSecret, amount, currency, onSuccess, onError }: PaymentFormProps) {
    const stripePromise = getStripe();

    const options = {
        clientSecret,
        appearance: {
            theme: 'stripe' as const,
            variables: {
                colorPrimary: '#4F7B62', // Match sage-700
                borderRadius: '8px',
            },
        },
    };

    return (
        <Elements stripe={stripePromise} options={options}>
            <CheckoutForm
                amount={amount}
                currency={currency}
                onSuccess={onSuccess}
                onError={onError}
            />
        </Elements>
    );
}

/**
 * Payment success display component.
 */
export function PaymentSuccess() {
    return (
        <div className="text-center py-8">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <CheckCircle className="h-8 w-8 text-green-600" />
            </div>
            <h3 className="text-xl font-bold text-foreground mb-2">Payment Successful!</h3>
            <p className="text-muted-foreground">
                Your registration has been confirmed. Check your email for details.
            </p>
        </div>
    );
}
