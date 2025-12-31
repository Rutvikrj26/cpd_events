import React, { useState } from "react";
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

export function ReportsPage() {
    const [period, setPeriod] = useState("last-30-days");

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
                    value="$12,450"
                    icon={DollarSign}
                    trend={{ value: 15, label: "from last month", positive: true }}
                />
                <DashboardStat
                    title="Total Attendees"
                    value="2,340"
                    icon={Users}
                    trend={{ value: 5, label: "from last month", positive: true }}
                />
                <DashboardStat
                    title="Events Hosted"
                    value="12"
                    icon={Calendar}
                    trend={{ value: 2, label: "new this month", positive: true }}
                />
                <DashboardStat
                    title="Avg. Satisfaction"
                    value="4.8/5.0"
                    icon={TrendingUp}
                    trend={{ value: 0.2, label: "based on feedback", positive: true }}
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
                        {/* Placeholder for Chart */}
                        <div className="h-[300px] flex items-center justify-center bg-muted/50 rounded-lg border border-dashed text-muted-foreground">
                            <div className="text-center">
                                <BarChart3 className="h-10 w-10 mx-auto mb-2 opacity-50" />
                                <p>Chart Visualization Placeholder</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
                <Card className="col-span-3">
                    <CardHeader>
                        <CardTitle>Ticket Sales by Type</CardTitle>
                        <CardDescription>
                            Distribution of General vs VIP tickets.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        {/* Placeholder for Pie Chart */}
                        <div className="h-[300px] flex items-center justify-center bg-muted/50 rounded-lg border border-dashed text-muted-foreground">
                            <div className="text-center">
                                <div className="h-32 w-32 rounded-full border-8 border-primary/20 border-t-primary mx-auto mb-4 opacity-75"></div>
                                <p>Distribution Chart Placeholder</p>
                            </div>
                        </div>
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
                        {[1, 2, 3, 4, 5].map((i) => (
                            <div key={i} className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/30 transition-colors">
                                <div className="flex items-center gap-4">
                                    <div className="h-10 w-10 bg-green-100 text-green-600 rounded-full flex items-center justify-center font-bold">
                                        $
                                    </div>
                                    <div>
                                        <p className="font-medium text-foreground">Ticket Sale #{1000 + i}</p>
                                        <p className="text-xs text-muted-foreground">Professional Development Summit 2024</p>
                                    </div>
                                </div>
                                <div className="text-right">
                                    <p className="font-bold text-foreground">+$150.00</p>
                                    <p className="text-xs text-muted-foreground">Today, 2:30 PM</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
