import { useEffect, useMemo, useState } from "react";
import {
    TrendingUp,
    Users,
    DollarSign,
    Calendar,
    Download,
    BookOpen,
    GraduationCap,
    Award,
    CheckCircle2,
    Percent,
    RotateCcw,
} from "lucide-react";
import { TrendChart } from "@/components/charts/TrendChart";
import { bucketForPeriod, bucketTrend } from "@/components/charts/bucketTrend";

function formatCurrency(cents: number, currency: string = "USD"): string {
    return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency,
    }).format((cents ?? 0) / 100);
}
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { DashboardStat } from "@/components/dashboard/DashboardStats";
import {
    getReports,
    getCourseReports,
    getProgramReports,
    ReportsResponse,
    CourseReportsResponse,
    ProgramReportsResponse,
    LearningTopItem,
} from "@/api/reports";
import { useAuth } from "@/contexts/AuthContext";
import { getRoleFlags } from "@/lib/role-utils";
import { toast } from "sonner";
import { formatDistanceToNow } from "date-fns";

type ReportTab = "events" | "courses" | "programs";

export function ReportsPage() {
    const { user } = useAuth();
    const { isOrganizer, isInstructor } = getRoleFlags(user);
    const [period, setPeriod] = useState("last-30-days");
    const [tab, setTab] = useState<ReportTab>(isOrganizer ? "events" : "courses");

    return (
        <div className="space-y-6">
            <PageHeader
                title="Reports & Analytics"
                description="Gain insights across events, courses, and programs."
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

            <Tabs value={tab} onValueChange={(v) => setTab(v as ReportTab)}>
                <TabsList>
                    {isOrganizer && <TabsTrigger value="events">Events</TabsTrigger>}
                    {isInstructor && <TabsTrigger value="courses">Courses</TabsTrigger>}
                    {isInstructor && <TabsTrigger value="programs">Programs</TabsTrigger>}
                </TabsList>

                {isOrganizer && (
                    <TabsContent value="events" className="mt-6 space-y-6">
                        <EventsTab period={period} />
                    </TabsContent>
                )}
                {isInstructor && (
                    <TabsContent value="courses" className="mt-6 space-y-6">
                        <CoursesTab period={period} />
                    </TabsContent>
                )}
                {isInstructor && (
                    <TabsContent value="programs" className="mt-6 space-y-6">
                        <ProgramsTab period={period} />
                    </TabsContent>
                )}
            </Tabs>
        </div>
    );
}

// ============================================================
// Events tab — preserves the pre-Phase-6 KPI set.
// ============================================================

function EventsTab({ period }: { period: string }) {
    const [reports, setReports] = useState<ReportsResponse | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        setLoading(true);
        getReports(period)
            .then(setReports)
            .catch((err) => {
                console.error(err);
                toast.error(err?.message || "Failed to load event reports.");
            })
            .finally(() => setLoading(false));
    }, [period]);

    const currency = reports?.summary.currency || "USD";
    const currencyFormatter = useMemo(
        () => new Intl.NumberFormat("en-US", { style: "currency", currency }),
        [currency],
    );
    const compactCurrencyFormatter = useMemo(
        () => new Intl.NumberFormat("en-US", {
            style: "currency",
            currency,
            notation: "compact",
            maximumFractionDigits: 1,
        }),
        [currency],
    );

    const bucket = bucketForPeriod(period);
    const trendData = useMemo(
        () =>
            bucketTrend(
                (reports?.trends ?? []).map((t) => ({
                    date: t.date,
                    primary: t.registrations,
                    secondary: (t.revenue_cents ?? 0) / 100,
                })),
                bucket,
            ),
        [reports?.trends, bucket],
    );

    return (
        <>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <DashboardStat
                    title="Total Revenue"
                    value={loading ? "--" : currencyFormatter.format((reports?.summary.total_revenue_cents || 0) / 100)}
                    icon={DollarSign}
                />
                <DashboardStat
                    title="Total Attendees"
                    value={loading ? "--" : String(reports?.summary.total_attendees || 0)}
                    icon={Users}
                />
                <DashboardStat
                    title="Events Hosted"
                    value={loading ? "--" : String(reports?.summary.events_hosted || 0)}
                    icon={Calendar}
                />
                <DashboardStat
                    title="Avg. Satisfaction"
                    value={loading ? "--" : reports?.summary.avg_rating ? `${reports.summary.avg_rating}/5.0` : "N/A"}
                    icon={TrendingUp}
                />
            </div>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
                <Card className="col-span-4">
                    <CardHeader>
                        <CardTitle>Registrations & Revenue</CardTitle>
                        <CardDescription>
                            {bucketDescription(bucket, "Registration count and gross revenue")}
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="pl-2">
                        <TrendChart
                            data={trendData}
                            loading={loading}
                            bucket={bucket}
                            primaryLabel="Registrations"
                            secondaryLabel="Revenue"
                            formatSecondary={(v) => compactCurrencyFormatter.format(v)}
                            emptyMessage="No registrations yet"
                        />
                    </CardContent>
                </Card>
                <Card className="col-span-3">
                    <CardHeader>
                        <CardTitle>Ticket Sales by Status</CardTitle>
                        <CardDescription>Paid, free, and refunded registrations.</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <KeyValueList
                            loading={loading}
                            rows={reports?.ticket_breakdown ?? []}
                            emptyMessage="No registrations yet"
                        />
                    </CardContent>
                </Card>
            </div>

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
                                        <div className="h-10 w-10 bg-green-100 text-green-600 rounded-full flex items-center justify-center font-bold">$</div>
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
        </>
    );
}

// ============================================================
// Courses tab
// ============================================================

function CoursesTab({ period }: { period: string }) {
    const [reports, setReports] = useState<CourseReportsResponse | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        setLoading(true);
        getCourseReports(period)
            .then(setReports)
            .catch((err) => {
                console.error(err);
                toast.error(err?.response?.data?.detail || err?.message || "Failed to load course reports.");
            })
            .finally(() => setLoading(false));
    }, [period]);

    const bucket = bucketForPeriod(period);
    const trendData = useMemo(
        () =>
            bucketTrend(
                (reports?.trends ?? []).map((t) => ({ date: t.date, primary: t.count })),
                bucket,
            ),
        [reports?.trends, bucket],
    );

    const grossCents = reports?.summary.gross_revenue_cents ?? 0;
    const refundCents = reports?.summary.refunds_cents ?? 0;
    const netCents = reports?.summary.net_revenue_cents ?? 0;

    return (
        <>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <DashboardStat
                    title="Gross Revenue"
                    value={loading ? "--" : formatCurrency(grossCents)}
                    icon={DollarSign}
                    description={`${reports?.summary.purchase_count ?? 0} purchases`}
                />
                <DashboardStat
                    title="Refunds"
                    value={loading ? "--" : formatCurrency(refundCents)}
                    icon={RotateCcw}
                    description={`${reports?.summary.refund_count ?? 0} refunds`}
                />
                <DashboardStat
                    title="Net Revenue"
                    value={loading ? "--" : formatCurrency(netCents)}
                    icon={TrendingUp}
                />
                <DashboardStat
                    title="Total Enrollments"
                    value={loading ? "--" : String(reports?.summary.total_enrollments ?? 0)}
                    icon={GraduationCap}
                />
            </div>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                <DashboardStat
                    title="Completions"
                    value={loading ? "--" : String(reports?.summary.completions ?? 0)}
                    icon={Award}
                />
                <DashboardStat
                    title="Completion Rate"
                    value={loading ? "--" : reports?.summary.completion_rate != null ? `${reports.summary.completion_rate}%` : "N/A"}
                    icon={Percent}
                />
                <DashboardStat
                    title="Published Courses"
                    value={loading ? "--" : String(reports?.summary.courses_published ?? 0)}
                    icon={BookOpen}
                />
            </div>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
                <Card className="col-span-4">
                    <CardHeader>
                        <CardTitle>Enrollment Trends</CardTitle>
                        <CardDescription>{bucketDescription(bucket, "New course enrollments")}</CardDescription>
                    </CardHeader>
                    <CardContent className="pl-2">
                        <TrendChart
                            data={trendData}
                            loading={loading}
                            bucket={bucket}
                            primaryLabel="Enrollments"
                            emptyMessage="No enrollments yet"
                        />
                    </CardContent>
                </Card>
                <Card className="col-span-3">
                    <CardHeader>
                        <CardTitle>Enrollment Status</CardTitle>
                        <CardDescription>Active, completed, and dropped enrollments.</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <KeyValueList
                            loading={loading}
                            rows={reports?.status_breakdown ?? []}
                            emptyMessage="No enrollments yet"
                        />
                    </CardContent>
                </Card>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
                <TopItemsCard
                    title="Top Courses"
                    description="Courses by enrollments in the selected period."
                    loading={loading}
                    items={reports?.top_courses ?? []}
                />
                <Card>
                    <CardHeader>
                        <CardTitle>Recent Enrollments</CardTitle>
                        <CardDescription>Latest learners who joined your courses.</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-3">
                            {loading ? (
                                <div className="text-sm text-muted-foreground">Loading enrollments...</div>
                            ) : reports?.recent_enrollments.length ? (
                                reports.recent_enrollments.map((enr) => (
                                    <div key={enr.enrollment_uuid} className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/30 transition-colors">
                                        <div className="flex items-center gap-3 min-w-0">
                                            <div className="h-9 w-9 bg-primary/10 text-primary rounded-full flex items-center justify-center shrink-0">
                                                <GraduationCap className="h-4 w-4" />
                                            </div>
                                            <div className="min-w-0">
                                                <p className="font-medium text-foreground truncate">{enr.user_name}</p>
                                                <p className="text-xs text-muted-foreground truncate">{enr.course_title}</p>
                                            </div>
                                        </div>
                                        <div className="text-right shrink-0 ml-3">
                                            <p className="text-xs text-muted-foreground capitalize">{enr.status}</p>
                                            <p className="text-xs text-muted-foreground">
                                                {formatDistanceToNow(new Date(enr.enrolled_at), { addSuffix: true })}
                                            </p>
                                        </div>
                                    </div>
                                ))
                            ) : (
                                <div className="text-sm text-muted-foreground">No enrollments yet.</div>
                            )}
                        </div>
                    </CardContent>
                </Card>
            </div>
        </>
    );
}

// ============================================================
// Programs tab
// ============================================================

function ProgramsTab({ period }: { period: string }) {
    const [reports, setReports] = useState<ProgramReportsResponse | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        setLoading(true);
        getProgramReports(period)
            .then(setReports)
            .catch((err) => {
                console.error(err);
                toast.error(err?.response?.data?.detail || err?.message || "Failed to load program reports.");
            })
            .finally(() => setLoading(false));
    }, [period]);

    const bucket = bucketForPeriod(period);
    const trendData = useMemo(
        () =>
            bucketTrend(
                (reports?.trends ?? []).map((t) => ({ date: t.date, primary: t.count })),
                bucket,
            ),
        [reports?.trends, bucket],
    );

    return (
        <>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <DashboardStat
                    title="Total Enrollments"
                    value={loading ? "--" : String(reports?.summary.total_enrollments ?? 0)}
                    icon={GraduationCap}
                />
                <DashboardStat
                    title="Completions"
                    value={loading ? "--" : String(reports?.summary.completions ?? 0)}
                    icon={Award}
                />
                <DashboardStat
                    title="Completion Rate"
                    value={loading ? "--" : reports?.summary.completion_rate != null ? `${reports.summary.completion_rate}%` : "N/A"}
                    icon={Percent}
                />
                <DashboardStat
                    title="Published Programs"
                    value={loading ? "--" : String(reports?.summary.programs_published ?? 0)}
                    icon={CheckCircle2}
                />
            </div>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
                <Card className="col-span-4">
                    <CardHeader>
                        <CardTitle>Enrollment Trends</CardTitle>
                        <CardDescription>{bucketDescription(bucket, "New program enrollments")}</CardDescription>
                    </CardHeader>
                    <CardContent className="pl-2">
                        <TrendChart
                            data={trendData}
                            loading={loading}
                            bucket={bucket}
                            primaryLabel="Enrollments"
                            emptyMessage="No enrollments yet"
                        />
                    </CardContent>
                </Card>
                <Card className="col-span-3">
                    <CardHeader>
                        <CardTitle>Enrollment Status</CardTitle>
                        <CardDescription>Active, completed, and dropped enrollments.</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <KeyValueList
                            loading={loading}
                            rows={reports?.status_breakdown ?? []}
                            emptyMessage="No enrollments yet"
                        />
                    </CardContent>
                </Card>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
                <TopItemsCard
                    title="Top Programs"
                    description="Programs by enrollments in the selected period."
                    loading={loading}
                    items={reports?.top_programs ?? []}
                />
                <Card>
                    <CardHeader>
                        <CardTitle>Recent Enrollments</CardTitle>
                        <CardDescription>Latest learners who joined your programs.</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-3">
                            {loading ? (
                                <div className="text-sm text-muted-foreground">Loading enrollments...</div>
                            ) : reports?.recent_enrollments.length ? (
                                reports.recent_enrollments.map((enr) => (
                                    <div key={enr.enrollment_uuid} className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/30 transition-colors">
                                        <div className="flex items-center gap-3 min-w-0">
                                            <div className="h-9 w-9 bg-primary/10 text-primary rounded-full flex items-center justify-center shrink-0">
                                                <BookOpen className="h-4 w-4" />
                                            </div>
                                            <div className="min-w-0">
                                                <p className="font-medium text-foreground truncate">{enr.user_name}</p>
                                                <p className="text-xs text-muted-foreground truncate">{enr.program_title}</p>
                                            </div>
                                        </div>
                                        <div className="text-right shrink-0 ml-3">
                                            <p className="text-xs text-muted-foreground capitalize">{enr.status}</p>
                                            <p className="text-xs text-muted-foreground">
                                                {formatDistanceToNow(new Date(enr.enrolled_at), { addSuffix: true })}
                                            </p>
                                        </div>
                                    </div>
                                ))
                            ) : (
                                <div className="text-sm text-muted-foreground">No enrollments yet.</div>
                            )}
                        </div>
                    </CardContent>
                </Card>
            </div>
        </>
    );
}

// ============================================================
// Shared presentational helpers
// ============================================================

function bucketDescription(bucket: "day" | "week" | "month", base: string): string {
    if (bucket === "month") return `${base} (monthly).`;
    if (bucket === "week") return `${base} (weekly).`;
    return `${base} (daily).`;
}

function KeyValueList({
    loading,
    rows,
    emptyMessage,
}: {
    loading: boolean;
    rows: { label: string; count: number }[];
    emptyMessage: string;
}) {
    if (loading) {
        return (
            <div className="h-[300px] flex items-center justify-center bg-muted/50 rounded-lg border border-dashed text-muted-foreground">
                <div className="text-center">
                    <div className="h-32 w-32 rounded-full border-8 border-primary/20 border-t-primary mx-auto mb-4 opacity-75" />
                    <p>Loading...</p>
                </div>
            </div>
        );
    }
    if (!rows.length) {
        return <div className="text-sm text-muted-foreground">{emptyMessage}</div>;
    }
    return (
        <div className="space-y-4">
            {rows.map((item) => (
                <div key={item.label} className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">{item.label}</span>
                    <span className="font-semibold">{item.count}</span>
                </div>
            ))}
        </div>
    );
}

function TopItemsCard({
    title,
    description,
    loading,
    items,
}: {
    title: string;
    description: string;
    loading: boolean;
    items: LearningTopItem[];
}) {
    return (
        <Card>
            <CardHeader>
                <CardTitle>{title}</CardTitle>
                <CardDescription>{description}</CardDescription>
            </CardHeader>
            <CardContent>
                {loading ? (
                    <div className="text-sm text-muted-foreground">Loading...</div>
                ) : items.length === 0 ? (
                    <div className="text-sm text-muted-foreground">No activity in this period.</div>
                ) : (
                    <div className="space-y-3">
                        {items.map((item, idx) => (
                            <div key={item.uuid} className="flex items-center justify-between text-sm">
                                <div className="flex items-center gap-3 min-w-0">
                                    <span className="w-6 text-right text-muted-foreground">{idx + 1}.</span>
                                    <span className="truncate text-foreground">{item.title}</span>
                                </div>
                                <span className="shrink-0 text-xs text-muted-foreground ml-3">
                                    {item.enrollments} enrollments
                                </span>
                            </div>
                        ))}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
