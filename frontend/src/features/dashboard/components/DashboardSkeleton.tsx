/**
 * DashboardSkeleton — first-paint placeholder while role-specific data
 * is loading. Mirrors the canonical hero / stat strip / two-column
 * layout so the page doesn't visually jump on hydrate.
 */
export function DashboardSkeleton() {
    return (
        <div className="space-y-block">
            <div className="h-48 rounded-2xl bg-muted animate-pulse" />
            <div className="grid grid-cols-2 gap-tight lg:grid-cols-4">
                {Array.from({ length: 4 }).map((_, i) => (
                    <div key={i} className="h-20 rounded-lg bg-muted animate-pulse" />
                ))}
            </div>
            <div className="grid grid-cols-1 gap-card lg:grid-cols-3">
                <div className="h-64 rounded-xl bg-muted animate-pulse lg:col-span-2" />
                <div className="h-64 rounded-xl bg-muted animate-pulse" />
            </div>
        </div>
    );
}
