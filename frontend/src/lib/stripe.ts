import { loadStripe, Stripe } from '@stripe/stripe-js';

let stripePromise: Promise<Stripe | null> | null = null;

/**
 * Get the Stripe instance (singleton pattern).
 * Uses VITE_STRIPE_PUBLISHABLE_KEY from environment.
 */
export function getStripe(): Promise<Stripe | null> {
    if (!stripePromise) {
        const publishableKey = import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY;

        if (!publishableKey) {
            console.error('Missing VITE_STRIPE_PUBLISHABLE_KEY environment variable');
            return Promise.resolve(null);
        }

        stripePromise = loadStripe(publishableKey);
    }
    return stripePromise;
}
