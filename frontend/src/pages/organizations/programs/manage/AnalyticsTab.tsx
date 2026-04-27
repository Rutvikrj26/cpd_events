import React, { useEffect, useMemo, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/shared/ui/card';
import { Button } from '@/shared/ui/button';
import { Badge } from '@/shared/ui/badge';
import { useToast } from '@/shared/ui/use-toast';
import { Loader2, DollarSign, RotateCcw, TrendingUp, GraduationCap, Award, Percent } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import {
    getProgramAnalytics,
    type ProgramAnalyticsResponse,
} from '@/api/programs';

const PERIODS: Array<{ value: string; label: string }> = [
    { value: 'last-7-days', label: 'Last 7 days' },
    { value: 'last-30-days', label: 'Last 30 days' },
    { value: 'last-90-days', label: 'Last 90 days' },
    { value: 'this-year', label: 'This year' },
];

function formatCurrency(cents: number, currency = 'USD'): string {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency,
    }).format((cents ?? 0) / 100);
}

export function AnalyticsTab({ programUuid }: { programUuid: string }) {
    const { toast } = useToast();
    const [period, setPeriod] = useState('last-30-days');
    const [data, setData] = useState<ProgramAnalyticsResponse | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        setLoading(true);
        getProgramAnalytics(programUuid, period)
            .then(setData)
            .catch((err) => {
                toast({
                    variant: 'destructive',
                    title: 'Failed to load analytics',
                    description: err?.message,
                });
            })
            .finally(() => setLoading(false));
    }, [programUuid, period, toast]);

    const trendMax = useMemo(() => {
        if (!data?.trends.length) return 1;
        return Math.max(...data.trends.map((t) => t.count), 1);
    }, [data?.trends]);

    if (loading && !data) {
        return (
            <div className="flex items-center justify-center py-12">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
        );
    }

    const s = data?.summary;

    return (
        <div className="space-y-6">
            <div className="flex flex-wrap gap-2 justify-end">
                {PERIODS.map((p) => (
                    <Button
                        key={p.value}
                        variant={period === p.value ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => setPeriod(p.value)}
                    >
                        {p.label}
                    </Button>
                ))}
            </div>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <StatCard
                    icon={DollarSign}
                    label="Gross revenue"
                    value={formatCurrency(s?.gross_revenue_cents ?? 0)}
                    sub={`${s?.purchase_count ?? 0} purchases`}
                />
                <StatCard
                    icon={RotateCcw}
                    label="Refunds"
                    value={formatCurrency(s?.refunds_cents ?? 0)}
                    sub={`${s?.refund_count ?? 0} refunds`}
                />
                <StatCard
                    icon={TrendingUp}
                    label="Net revenue"
                    value={formatCurrency(s?.net_revenue_cents ?? 0)}
                />
                <StatCard
                    icon={GraduationCap}
                    label="Total enrollments"
                    value={String(s?.total_enrollments ?? 0)}
                />
            </div>

            <div className="grid gap-4 md:grid-cols-3">
                <StatCard
                    icon={Award}
                    label="Completions"
                    value={String(s?.completions ?? 0)}
                />
                <StatCard
                    icon={Percent}
                    label="Completion rate"
                    value={s?.completion_rate != null ? `${s.completion_rate}%` : 'N/A'}
                />
                <Card>
                    <CardContent className="pt-6">
                        <p className="text-sm text-muted-foreground">Status breakdown</p>
                        <div className="space-y-1 mt-2">
                            {(data?.status_breakdown ?? []).map((b) => (
                                <div key={b.label} className="flex justify-between text-sm">
                                    <span>{b.label}</span>
                                    <span className="font-medium">{b.count}</span>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle>Enrollment trends</CardTitle>
                    <CardDescription>New program enrollments over the selected period.</CardDescription>
                </CardHeader>
                <CardContent>
                    {data?.trends.length ? (
                        <div className="space-y-2">
                            {data.trends.map((t) => (
                                <div key={t.date ?? 'unknown'} className="flex items-center gap-3 text-sm">
                                    <span className="text-xs text-muted-foreground w-24">
                                        {t.date ? new Date(t.date).toLocaleDateString() : 'Unknown'}
                                    </span>
                                    <div className="flex-1 bg-muted/40 rounded h-3 overflow-hidden">
                                        <div
                                            className="bg-emerald-600 h-full"
                                            style={{ width: `${(t.count / trendMax) * 100}%` }}
                                        />
                                    </div>
                                    <span className="font-mono text-xs w-10 text-right">{t.count}</span>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <p className="text-sm text-muted-foreground">No enrollments in this period.</p>
                    )}
                </CardContent>
            </Card>

            <Card>
                <CardHeader>
                    <CardTitle>Recent transactions</CardTitle>
                </CardHeader>
                <CardContent>
                    {data?.recent_transactions?.length ? (
                        <div className="divide-y">
                            {data.recent_transactions.map((t) => (
                                <div key={t.purchase_uuid} className="py-3 flex items-center justify-between">
                                    <div>
                                        <p className="font-medium text-sm">{t.user_name}</p>
                                        <p className="text-xs text-muted-foreground">
                                            {t.created_at
                                                ? formatDistanceToNow(new Date(t.created_at), { addSuffix: true })
                                                : '—'}
                                        </p>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <Badge
                                            className={
                                                t.status === 'completed'
                                                    ? 'bg-emerald-600'
                                                    : t.status === 'refunded'
                                                      ? 'bg-purple-500'
                                                      : ''
                                            }
                                            variant={
                                                t.status === 'completed' || t.status === 'refunded'
                                                    ? undefined
                                                    : 'secondary'
                                            }
                                        >
                                            {t.status}
                                        </Badge>
                                        <span className="font-medium">
                                            {formatCurrency(t.amount_cents, t.currency?.toUpperCase())}
                                        </span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <p className="text-sm text-muted-foreground">No transactions in this period.</p>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}

function StatCard({
    icon: Icon,
    label,
    value,
    sub,
}: {
    icon: React.ComponentType<{ className?: string }>;
    label: string;
    value: string;
    sub?: string;
}) {
    return (
        <Card>
            <CardContent className="pt-6">
                <div className="flex items-start justify-between">
                    <div>
                        <p className="text-sm text-muted-foreground">{label}</p>
                        <p className="text-2xl font-bold">{value}</p>
                        {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
                    </div>
                    <Icon className="h-4 w-4 text-muted-foreground" />
                </div>
            </CardContent>
        </Card>
    );
}

export default AnalyticsTab;
