import type { TrendBucket, TrendPoint } from "./TrendChart";

interface DailyRow {
    date: string | null;
    primary: number;
    secondary?: number;
}

export function bucketForPeriod(period: string): TrendBucket {
    if (period === "last-90-days") return "week";
    if (period === "this-year") return "month";
    return "day";
}

/**
 * Roll daily rows into the target bucket. Sums primary and secondary; the
 * bucket's representative date is the start of the week (Mon) or month.
 */
export function bucketTrend(rows: DailyRow[], bucket: TrendBucket): TrendPoint[] {
    if (bucket === "day") {
        return rows.map((r) => ({ date: r.date, primary: r.primary, secondary: r.secondary }));
    }

    const grouped = new Map<string, { date: string; primary: number; secondary: number; hasSecondary: boolean }>();
    for (const row of rows) {
        if (!row.date) continue;
        const d = new Date(row.date);
        if (Number.isNaN(d.getTime())) continue;
        const key = bucket === "week" ? weekStartIso(d) : monthStartIso(d);
        const entry = grouped.get(key) ?? { date: key, primary: 0, secondary: 0, hasSecondary: false };
        entry.primary += row.primary;
        if (typeof row.secondary === "number") {
            entry.secondary += row.secondary;
            entry.hasSecondary = true;
        }
        grouped.set(key, entry);
    }

    return Array.from(grouped.values())
        .sort((a, b) => a.date.localeCompare(b.date))
        .map((e) => ({
            date: e.date,
            primary: e.primary,
            secondary: e.hasSecondary ? e.secondary : undefined,
        }));
}

function weekStartIso(d: Date): string {
    const x = new Date(d);
    const day = x.getDay();
    const diff = (day === 0 ? -6 : 1 - day);
    x.setDate(x.getDate() + diff);
    x.setHours(0, 0, 0, 0);
    return x.toISOString().slice(0, 10);
}

function monthStartIso(d: Date): string {
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-01`;
}
