import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { PageHeader } from '@/components/ui/page-header';
import { useToast } from '@/components/ui/use-toast';
import { Loader2, RotateCcw, AlertTriangle, RefreshCcw, ExternalLink } from 'lucide-react';
import client from '@/api/client';
import { formatDistanceToNow } from 'date-fns';

// ---- Types matching backend serializers ----
type StripeEvent = {
    event_id: string;
    event_type: string;
    received_at: string;
    processed_at: string | null;
    error: string;
};

type Dispute = {
    uuid: string;
    stripe_dispute_id: string;
    stripe_charge_id: string;
    stripe_payment_intent_id: string;
    status: string;
    reason: string;
    amount_cents: number;
    currency: string;
    amount_display: string;
    evidence_due_by: string | null;
    submitted_at: string | null;
    closed_at: string | null;
    outcome: string;
    created_at: string;
    registration_uuid: string | null;
    course_purchase_uuid: string | null;
};

type DriftFinding = {
    kind: string;
    entity: string;
    stripe_id: string;
    detail: Record<string, unknown>;
};

type ReconcileResult = {
    findings: DriftFinding[];
    summary: { since: string; total: number; by_kind: Record<string, number> };
};

const OPEN_DISPUTE_STATES = new Set([
    'needs_response',
    'under_review',
    'warning_needs_response',
    'warning_under_review',
]);

export function BillingAdminPage() {
    return (
        <div className="container mx-auto max-w-7xl py-6 space-y-6">
            <PageHeader
                title="Billing & Stripe"
                description="Admin-only view of Stripe webhook events, disputes, and reconciliation against the local DB."
            />
            <Tabs defaultValue="events">
                <TabsList>
                    <TabsTrigger value="events">Stripe Events</TabsTrigger>
                    <TabsTrigger value="disputes">Disputes</TabsTrigger>
                    <TabsTrigger value="reconcile">Reconcile</TabsTrigger>
                </TabsList>
                <TabsContent value="events">
                    <StripeEventsTab />
                </TabsContent>
                <TabsContent value="disputes">
                    <DisputesTab />
                </TabsContent>
                <TabsContent value="reconcile">
                    <ReconcileTab />
                </TabsContent>
            </Tabs>
        </div>
    );
}

// ---------------------------------------------------------------------------
// Stripe Events tab
// ---------------------------------------------------------------------------

function StripeEventsTab() {
    const { toast } = useToast();
    const [events, setEvents] = useState<StripeEvent[]>([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState<'all' | 'errored' | 'unprocessed'>('all');
    const [retrying, setRetrying] = useState<string | null>(null);

    const load = async () => {
        setLoading(true);
        try {
            const params: Record<string, string> = {};
            if (filter === 'errored') params.errored = '1';
            if (filter === 'unprocessed') params.unprocessed = '1';
            const resp = await client.get<StripeEvent[]>('/admin/billing/stripe-events/', { params });
            setEvents(resp.data);
        } catch (err: any) {
            toast({ variant: 'destructive', title: 'Failed to load', description: err?.message ?? 'Unknown error' });
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        load();
    }, [filter]);

    const retry = async (eventId: string) => {
        setRetrying(eventId);
        try {
            await client.post(`/admin/billing/stripe-events/${eventId}/retry/`);
            toast({ title: 'Retry queued', description: 'Event re-enqueued for processing.' });
            await load();
        } catch (err: any) {
            const msg = err?.response?.data?.error?.message || err?.message || 'Retry failed.';
            toast({ variant: 'destructive', title: 'Retry failed', description: msg });
        } finally {
            setRetrying(null);
        }
    };

    return (
        <Card className="mt-4">
            <CardHeader className="flex-row items-start justify-between space-y-0">
                <div>
                    <CardTitle>Stripe Events</CardTitle>
                    <CardDescription>
                        Webhook idempotency table. Retry re-runs the handler chain (idempotent on every write).
                    </CardDescription>
                </div>
                <div className="flex items-center gap-2">
                    {(['all', 'errored', 'unprocessed'] as const).map((f) => (
                        <Button
                            key={f}
                            variant={filter === f ? 'default' : 'outline'}
                            size="sm"
                            onClick={() => setFilter(f)}
                            className="capitalize"
                        >
                            {f}
                        </Button>
                    ))}
                    <Button variant="ghost" size="sm" onClick={load} disabled={loading}>
                        <RefreshCcw className="h-4 w-4" />
                    </Button>
                </div>
            </CardHeader>
            <CardContent>
                {loading ? (
                    <div className="flex justify-center py-8">
                        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                    </div>
                ) : events.length === 0 ? (
                    <p className="text-sm text-muted-foreground text-center py-8">
                        No Stripe events match the current filter.
                    </p>
                ) : (
                    <div className="divide-y">
                        {events.map((ev) => (
                            <div key={ev.event_id} className="py-3 flex items-center justify-between gap-4">
                                <div className="min-w-0 flex-1">
                                    <div className="flex items-center gap-2">
                                        <span className="font-mono text-xs text-muted-foreground truncate">
                                            {ev.event_id}
                                        </span>
                                        <Badge variant="secondary" className="text-xs">
                                            {ev.event_type}
                                        </Badge>
                                        {ev.error ? (
                                            <Badge variant="destructive" className="text-xs">
                                                Error
                                            </Badge>
                                        ) : ev.processed_at ? (
                                            <Badge className="bg-emerald-600 text-xs">Processed</Badge>
                                        ) : (
                                            <Badge className="bg-amber-500 text-black text-xs">Pending</Badge>
                                        )}
                                    </div>
                                    <p
                                        className="text-xs text-muted-foreground mt-1"
                                        title={new Date(ev.received_at).toISOString()}
                                    >
                                        Received {formatDistanceToNow(new Date(ev.received_at), { addSuffix: true })}
                                    </p>
                                    {ev.error ? (
                                        <p className="text-xs text-destructive mt-1 font-mono truncate">{ev.error}</p>
                                    ) : null}
                                </div>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => retry(ev.event_id)}
                                    disabled={retrying === ev.event_id}
                                >
                                    {retrying === ev.event_id && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}
                                    Retry
                                </Button>
                            </div>
                        ))}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}

// ---------------------------------------------------------------------------
// Disputes tab
// ---------------------------------------------------------------------------

function DisputesTab() {
    const { toast } = useToast();
    const [disputes, setDisputes] = useState<Dispute[]>([]);
    const [loading, setLoading] = useState(true);
    const [openOnly, setOpenOnly] = useState(false);

    useEffect(() => {
        const load = async () => {
            setLoading(true);
            try {
                const params: Record<string, string> = {};
                if (openOnly) params.open = '1';
                const resp = await client.get<Dispute[]>('/admin/billing/disputes/', { params });
                setDisputes(resp.data);
            } catch (err: any) {
                toast({ variant: 'destructive', title: 'Failed to load disputes', description: err?.message });
            } finally {
                setLoading(false);
            }
        };
        load();
    }, [openOnly, toast]);

    const openCount = disputes.filter((d) => OPEN_DISPUTE_STATES.has(d.status)).length;

    return (
        <Card className="mt-4">
            <CardHeader className="flex-row items-start justify-between space-y-0">
                <div>
                    <CardTitle>Disputes</CardTitle>
                    <CardDescription>
                        Stripe chargebacks and disputes. {openCount > 0 && (
                            <span className="text-destructive font-medium">{openCount} open — respond before the evidence deadline.</span>
                        )}
                    </CardDescription>
                </div>
                <Button variant={openOnly ? 'default' : 'outline'} size="sm" onClick={() => setOpenOnly(!openOnly)}>
                    Open only
                </Button>
            </CardHeader>
            <CardContent>
                {loading ? (
                    <div className="flex justify-center py-8">
                        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                    </div>
                ) : disputes.length === 0 ? (
                    <p className="text-sm text-muted-foreground text-center py-8">
                        No disputes {openOnly ? 'currently open' : 'on record'}.
                    </p>
                ) : (
                    <div className="divide-y">
                        {disputes.map((d) => {
                            const isOpen = OPEN_DISPUTE_STATES.has(d.status);
                            const dueSoon =
                                d.evidence_due_by &&
                                isOpen &&
                                new Date(d.evidence_due_by).getTime() - Date.now() < 3 * 24 * 3600 * 1000;
                            return (
                                <div key={d.uuid} className="py-3 flex items-start justify-between gap-4">
                                    <div className="min-w-0 flex-1">
                                        <div className="flex items-center gap-2 flex-wrap">
                                            <span className="font-mono text-xs text-muted-foreground">
                                                {d.stripe_dispute_id}
                                            </span>
                                            <Badge variant={isOpen ? 'destructive' : 'outline'} className="text-xs capitalize">
                                                {d.status.replace(/_/g, ' ')}
                                            </Badge>
                                            <Badge variant="secondary" className="text-xs capitalize">
                                                {d.reason.replace(/_/g, ' ')}
                                            </Badge>
                                            {dueSoon && (
                                                <Badge className="bg-amber-500 text-black text-xs">
                                                    <AlertTriangle className="h-3 w-3 mr-1" />
                                                    Evidence due soon
                                                </Badge>
                                            )}
                                        </div>
                                        <p className="text-sm mt-1 font-medium">{d.amount_display}</p>
                                        {d.evidence_due_by && isOpen && (
                                            <p
                                                className="text-xs text-muted-foreground mt-1"
                                                title={new Date(d.evidence_due_by).toISOString()}
                                            >
                                                Evidence due{' '}
                                                {formatDistanceToNow(new Date(d.evidence_due_by), { addSuffix: true })}
                                            </p>
                                        )}
                                        {d.outcome && (
                                            <p className="text-xs text-muted-foreground mt-1 capitalize">Outcome: {d.outcome}</p>
                                        )}
                                    </div>
                                    <a
                                        href={`https://dashboard.stripe.com/disputes/${d.stripe_dispute_id}`}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="shrink-0"
                                    >
                                        <Button variant="outline" size="sm">
                                            Stripe
                                            <ExternalLink className="h-3 w-3 ml-1" />
                                        </Button>
                                    </a>
                                </div>
                            );
                        })}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}

// ---------------------------------------------------------------------------
// Reconcile tab
// ---------------------------------------------------------------------------

function ReconcileTab() {
    const { toast } = useToast();
    const [hours, setHours] = useState<number>(72);
    const [result, setResult] = useState<ReconcileResult | null>(null);
    const [running, setRunning] = useState(false);

    const run = async () => {
        setRunning(true);
        try {
            const resp = await client.post<ReconcileResult>('/admin/billing/reconcile/', { hours });
            setResult(resp.data);
            toast({
                title: 'Reconciliation complete',
                description: `${resp.data.summary.total} drift finding(s) since ${new Date(resp.data.summary.since).toLocaleString()}.`,
            });
        } catch (err: any) {
            const msg = err?.response?.data?.error?.message || err?.message || 'Reconcile failed.';
            toast({ variant: 'destructive', title: 'Reconcile failed', description: msg });
        } finally {
            setRunning(false);
        }
    };

    return (
        <Card className="mt-4">
            <CardHeader>
                <CardTitle>Reconciliation</CardTitle>
                <CardDescription>
                    Runs a drift check against Stripe for the last N hours. Compares local state against Stripe's CheckoutSessions,
                    PaymentIntents, Refunds, and Disputes.
                </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="flex items-end gap-3">
                    <div className="flex-1 max-w-[200px] space-y-1">
                        <label className="text-sm font-medium" htmlFor="recon-hours">
                            Look back (hours)
                        </label>
                        <Input
                            id="recon-hours"
                            type="number"
                            min="1"
                            max="720"
                            value={hours}
                            onChange={(e) => setHours(parseInt(e.target.value) || 72)}
                            disabled={running}
                        />
                    </div>
                    <Button onClick={run} disabled={running}>
                        {running ? (
                            <>
                                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                Running...
                            </>
                        ) : (
                            <>
                                <RotateCcw className="h-4 w-4 mr-2" />
                                Run reconciliation
                            </>
                        )}
                    </Button>
                </div>
                {result && (
                    <div className="space-y-3">
                        <div className="flex items-center gap-4 flex-wrap">
                            <Badge variant={result.summary.total === 0 ? 'outline' : 'destructive'}>
                                {result.summary.total} drift finding{result.summary.total === 1 ? '' : 's'}
                            </Badge>
                            {Object.entries(result.summary.by_kind).map(([k, v]) => (
                                <Badge key={k} variant="secondary" className="capitalize">
                                    {k.replace(/_/g, ' ')}: {v}
                                </Badge>
                            ))}
                        </div>
                        {result.findings.length > 0 ? (
                            <div className="divide-y rounded-md border">
                                {result.findings.map((f, i) => (
                                    <div key={`${f.stripe_id}-${i}`} className="p-3 space-y-1">
                                        <div className="flex items-center gap-2 flex-wrap">
                                            <Badge variant="destructive" className="capitalize">
                                                {f.kind.replace(/_/g, ' ')}
                                            </Badge>
                                            <Badge variant="secondary">{f.entity}</Badge>
                                            <span className="font-mono text-xs text-muted-foreground">{f.stripe_id}</span>
                                        </div>
                                        <pre className="text-xs text-muted-foreground bg-muted/40 rounded p-2 overflow-x-auto">
                                            {JSON.stringify(f.detail, null, 2)}
                                        </pre>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <p className="text-sm text-muted-foreground">No drift — local state matches Stripe.</p>
                        )}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}

export default BillingAdminPage;
