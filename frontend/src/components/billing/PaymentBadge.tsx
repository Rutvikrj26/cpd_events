import React from 'react';
import { Badge } from '@/components/ui/badge';

export type PaymentStatus =
    | 'free'
    | 'comp'
    | 'pending'
    | 'completed'
    | 'refunded'
    | 'failed'
    | 'via_program';

export interface EnrollmentPayment {
    status: PaymentStatus;
    amount_cents?: number;
    currency?: string;
    purchase_uuid?: string;
    stripe_payment_intent_id?: string;
    created_at?: string;
}

export function formatPaymentAmount(payment: EnrollmentPayment | undefined): string {
    if (!payment?.amount_cents || !payment.currency) return '';
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: payment.currency.toUpperCase(),
    }).format(payment.amount_cents / 100);
}

/**
 * Badge that summarizes the payment state of an enrollment row.
 * Shared between course + program rosters so the pill styling stays in
 * one place.
 */
export function PaymentBadge({ payment }: { payment: EnrollmentPayment | undefined }) {
    const s = payment?.status ?? 'free';
    switch (s) {
        case 'completed':
            return <Badge className="bg-emerald-600">{`Paid ${formatPaymentAmount(payment)}`}</Badge>;
        case 'refunded':
            return <Badge className="bg-purple-500">Refunded</Badge>;
        case 'pending':
            return <Badge variant="secondary">Payment pending</Badge>;
        case 'failed':
            return <Badge variant="destructive">Payment failed</Badge>;
        case 'comp':
            return <Badge className="bg-amber-500 text-black">Comp</Badge>;
        case 'via_program':
            return <Badge className="bg-indigo-500">Via program</Badge>;
        default:
            return <Badge variant="outline">Free</Badge>;
    }
}
