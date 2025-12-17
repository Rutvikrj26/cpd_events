export interface Subscription {
    uuid: string;
    plan: string;
    status: 'active' | 'canceled' | 'past_due';
    current_period_end: string;
}

export interface Invoice {
    uuid: string;
    amount_due: number;
    status: 'paid' | 'open' | 'void';
    pdf_url?: string;
}
