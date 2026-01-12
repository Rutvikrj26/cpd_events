import React, { useEffect, useMemo, useState } from "react";
import {
    BarChart3,
    TrendingUp,
    Users,
    DollarSign,
    Calendar,
    Download
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { DashboardStat } from "@/components/dashboard/DashboardStats";
import { getReports, ReportsResponse } from "@/api/reports";
import { toast } from "sonner";
import { formatDistanceToNow } from "date-fns";

export function ReportsPage() {
    const [period, setPeriod] = useState("last-30-days");
    const [reports, setReports] = useState<ReportsResponse | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const load = async () => {
            setLoading(true);
            try {
                const data = await getReports(period);
                setReports(data);
            } catch (error: any) {
                console.error("Failed to load reports:", error);
                toast.error(error?.message || "Failed to load reports.");
            } finally {
                setLoading(false);
            }
        };
        load();
    }, [period]);

    const currency = reports?.summary.currency || "USD";
    const currencyFormatter = useMemo(() => (
        new Intl.NumberFormat("en-US", { style: "currency", currency })
    ), [currency]);

    const trendMax = useMemo(() => {
        if (!reports?.trends.length) {
            return 1;
        }
        return Math.max(...reports.trends.map(t => t.registrations), 1);
    }, [reports?.trends]);

    return (
        <div className="space-y-6">
            <PageHeader
                title="Reports & Analytics"
                description="Gain insights into your event performance and attendee engagement."
                actions={
                    <div className="flex items-center gap-2">
                        <Select value={period} onValueChange={setPeriod}>
                            <SelectTrigger className="w-[180px]">
                                <SelectValue placeholder="Select period" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="last-7-days">Last 7 days</SelectItem>
                                <SelectItem value="last-30-days">Last 30 days</SelectItem>
                                <SelectItem value="last-90-days">Last 3 months</SelectItem>
                                <SelectItem value="this-year">This Year</SelectItem>
                            </SelectContent>
                        </Select>
                        <Button variant="outline">
                            <Download className="mr-2 h-4 w-4" /> Export Report
                        </Button>
                    </div>
                }
            />

            {/* KPI Cards */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <DashboardStat
                    title="Total Revenue"
                    value={loading ? "--" : currencyFormatter.format((reports?.summary.total_revenue_cents || 0) / 100)}
                    icon={DollarSign}
                    trend={{ value: 0, label: "current period", positive: true }}
                />
                <DashboardStat
                    title="Total Attendees"
                    value={loading ? "--" : String(reports?.summary.total_attendees || 0)}
                    icon={Users}
                    trend={{ value: 0, label: "current period", positive: true }}
                />
                <DashboardStat
                    title="Events Hosted"
                    value={loading ? "--" : String(reports?.summary.events_hosted || 0)}
                    icon={Calendar}
                    trend={{ value: 0, label: "current period", positive: true }}
                />
                <DashboardStat
                    title="Avg. Satisfaction"
                    value={loading ? "--" : reports?.summary.avg_rating ? `${reports.summary.avg_rating}/5.0` : "N/A"}
                    icon={TrendingUp}
                    trend={{ value: 0, label: "based on feedback", positive: true }}
                />
            </div>

            {/* Charts Section */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
                <Card className="col-span-4">
                    <CardHeader>
                        <CardTitle>Registration Trends</CardTitle>
                        <CardDescription>
                            Number of registrations over time.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="pl-2">
                        {loading ? (
                            <div className="h-[300px] flex items-center justify-center bg-muted/50 rounded-lg border border-dashed text-muted-foreground">
                                <div className="text-center">
                                    <BarChart3 className="h-10 w-10 mx-auto mb-2 opacity-50" />
                                    <p>Loading trends...</p>
                                </div>
                            </div>
                        ) : reports?.trends.length ? (
                            <div className="space-y-3">
                                {reports.trends.map((trend, index) => (
                                    <div key={trend.date || index} className="flex items-center gap-3">
                                        <div className="w-20 text-xs text-muted-foreground">
                                            {trend.date ? new Date(trend.date).toLocaleDateString() : "Unknown"}
                                        </div>
                                        <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                                            <div
                                                className="h-full bg-primary"
                                                style={{ width: `${(trend.registrations / trendMax) * 100}%` }}
                                            />
                                        </div>
                                        <div className="w-16 text-xs text-muted-foreground text-right">
                                            {trend.registrations}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="h-[300px] flex items-center justify-center bg-muted/50 rounded-lg border border-dashed text-muted-foreground">
                                <div className="text-center">
                                    <BarChart3 className="h-10 w-10 mx-auto mb-2 opacity-50" />
                                    <p>No registrations yet</p>
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>
                <Card className="col-span-3">
                    <CardHeader>
                        <CardTitle>Ticket Sales by Status</CardTitle>
                        <CardDescription>
                            Paid, free, and refunded registrations.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        {loading ? (
                            <div className="h-[300px] flex items-center justify-center bg-muted/50 rounded-lg border border-dashed text-muted-foreground">
                                <div className="text-center">
                                    <div className="h-32 w-32 rounded-full border-8 border-primary/20 border-t-primary mx-auto mb-4 opacity-75"></div>
                                    <p>Loading breakdown...</p>
                                </div>
                            </div>
                        ) : reports?.ticket_breakdown.length ? (
                            <div className="space-y-4">
                                {reports.ticket_breakdown.map((item) => (
                                    <div key={item.label} className="flex items-center justify-between text-sm">
                                        <span className="text-muted-foreground">{item.label}</span>
                                        <span className="font-semibold">{item.count}</span>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="h-[300px] flex items-center justify-center bg-muted/50 rounded-lg border border-dashed text-muted-foreground">
                                <div className="text-center">
                                    <div className="h-32 w-32 rounded-full border-8 border-primary/20 border-t-primary mx-auto mb-4 opacity-75"></div>
                                    <p>No registrations yet</p>
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>

            {/* Recent Transactions / Detailed List */}
            <Card>
                <CardHeader>
                    <CardTitle>Recent Transactions</CardTitle>
                    <CardDescription>Latest financial activity from ticket sales.</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="space-y-4">
                        {loading ? (
                            <div className="text-sm text-muted-foreground">Loading transactions...</div>
                        ) : reports?.recent_transactions.length ? (
                            reports.recent_transactions.map((txn) => (
                                <div key={txn.registration_uuid} className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/30 transition-colors">
                                    <div className="flex items-center gap-4">
                                        <div className="h-10 w-10 bg-green-100 text-green-600 rounded-full flex items-center justify-center font-bold">
                                            $
                                        </div>
                                        <div>
                                            <p className="font-medium text-foreground">Ticket Sale</p>
                                            <p className="text-xs text-muted-foreground">{txn.event_title}</p>
                                        </div>
                                    </div>
                                    <div className="text-right">
                                        <p className="font-bold text-foreground">
                                            {currencyFormatter.format(txn.amount_cents / 100)}
                                        </p>
                                        <p className="text-xs text-muted-foreground">
                                            {formatDistanceToNow(new Date(txn.created_at), { addSuffix: true })}
                                        </p>
                                    </div>
                                </div>
                            ))
                        ) : (
                            <div className="text-sm text-muted-foreground">No transactions yet.</div>
                        )}
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
