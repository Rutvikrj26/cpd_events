import { loadStripe, Stripe } from '@stripe/stripe-js';

const stripePromises: Record<string, Promise<Stripe | null>> = {};

/**
 * Get the Stripe instance (singleton pattern).
 * Uses VITE_STRIPE_PUBLISHABLE_KEY from environment.
 */
export function getStripe(stripeAccountId?: string): Promise<Stripe | null> {
    const publishableKey = import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY;

    if (!publishableKey) {
        console.error('Missing VITE_STRIPE_PUBLISHABLE_KEY environment variable');
        return Promise.resolve(null);
    }

    const key = stripeAccountId || 'platform';
    if (!stripePromises[key]) {
        stripePromises[key] = loadStripe(
            publishableKey,
            stripeAccountId ? { stripeAccount: stripeAccountId } : undefined
        );
    }
    return stripePromises[key];
}
