import { useMemo } from "react";
import {
    Area,
    AreaChart,
    CartesianGrid,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from "recharts";
import { BarChart3 } from "lucide-react";

export type TrendBucket = "day" | "week" | "month";

export interface TrendPoint {
    date: string | null;
    primary: number;
    secondary?: number;
}

interface TrendChartProps {
    data: TrendPoint[];
    loading?: boolean;
    bucket: TrendBucket;
    primaryLabel: string;
    secondaryLabel?: string;
    /** Format secondary value (e.g., currency). Defaults to integer string. */
    formatSecondary?: (n: number) => string;
    emptyMessage?: string;
    height?: number;
}

const SHELL_CLASSES = "h-[300px] flex items-center justify-center bg-muted/30 rounded-lg border border-dashed text-muted-foreground";

export function TrendChart({
    data,
    loading,
    bucket,
    primaryLabel,
    secondaryLabel,
    formatSecondary,
    emptyMessage = "No data in this period",
    height = 300,
}: TrendChartProps) {
    const formattedData = useMemo(() => {
        return data
            .filter((d) => d.date)
            .map((d) => ({
                ...d,
                label: formatBucketLabel(d.date as string, bucket),
            }));
    }, [data, bucket]);

    if (loading) {
        return (
            <div className={SHELL_CLASSES} style={{ height }}>
                <div className="text-center">
                    <BarChart3 className="h-10 w-10 mx-auto mb-2 opacity-50" />
                    <p>Loading…</p>
                </div>
            </div>
        );
    }

    if (!formattedData.length) {
        return (
            <div className={SHELL_CLASSES} style={{ height }}>
                <div className="text-center">
                    <BarChart3 className="h-10 w-10 mx-auto mb-2 opacity-50" />
                    <p>{emptyMessage}</p>
                </div>
            </div>
        );
    }

    const hasSecondary = formattedData.some((d) => typeof d.secondary === "number");

    return (
        <div style={{ width: "100%", height }}>
            <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={formattedData} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
                    <defs>
                        <linearGradient id="trend-primary" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="hsl(var(--chart-1))" stopOpacity={0.6} />
                            <stop offset="100%" stopColor="hsl(var(--chart-1))" stopOpacity={0.05} />
                        </linearGradient>
                        <linearGradient id="trend-secondary" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="hsl(var(--chart-4))" stopOpacity={0.5} />
                            <stop offset="100%" stopColor="hsl(var(--chart-4))" stopOpacity={0.05} />
                        </linearGradient>
                    </defs>
                    <CartesianGrid stroke="hsl(var(--border))" strokeOpacity={0.4} vertical={false} />
                    <XAxis
                        dataKey="label"
                        tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }}
                        tickLine={false}
                        axisLine={false}
                        minTickGap={24}
                    />
                    <YAxis
                        yAxisId="left"
                        allowDecimals={false}
                        tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }}
                        tickLine={false}
                        axisLine={false}
                        width={36}
                    />
                    {hasSecondary && (
                        <YAxis
                            yAxisId="right"
                            orientation="right"
                            tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }}
                            tickLine={false}
                            axisLine={false}
                            width={56}
                            tickFormatter={(v) => (formatSecondary ? formatSecondary(v as number) : String(v))}
                        />
                    )}
                    <Tooltip
                        contentStyle={{
                            background: "hsl(var(--popover))",
                            border: "1px solid hsl(var(--border))",
                            borderRadius: 8,
                            fontSize: 12,
                            color: "hsl(var(--popover-foreground))",
                        }}
                        labelStyle={{ color: "hsl(var(--muted-foreground))", marginBottom: 4 }}
                        formatter={(value, name) => {
                            const num = typeof value === "number" ? value : Number(value);
                            if (name === secondaryLabel && formatSecondary && Number.isFinite(num)) {
                                return [formatSecondary(num), name];
                            }
                            return [value as number, name as string];
                        }}
                    />
                    <Area
                        yAxisId="left"
                        type="monotone"
                        dataKey="primary"
                        name={primaryLabel}
                        stroke="hsl(var(--chart-1))"
                        strokeWidth={2}
                        fill="url(#trend-primary)"
                    />
                    {hasSecondary && (
                        <Area
                            yAxisId="right"
                            type="monotone"
                            dataKey="secondary"
                            name={secondaryLabel ?? "Secondary"}
                            stroke="hsl(var(--chart-4))"
                            strokeWidth={2}
                            fill="url(#trend-secondary)"
                        />
                    )}
                </AreaChart>
            </ResponsiveContainer>
        </div>
    );
}

function formatBucketLabel(iso: string, bucket: TrendBucket): string {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    if (bucket === "month") {
        return d.toLocaleDateString(undefined, { month: "short", year: "2-digit" });
    }
    if (bucket === "week") {
        return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
    }
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}
