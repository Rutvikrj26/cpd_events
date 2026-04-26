import React, { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { Search, Layers, BookOpen } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { PublicLayout } from "@/components/layout/PublicLayout";
import { getPublicPrograms, ProgramListItem } from "@/api/programs";

const formatPrice = (cents: number, currency: string): string => {
    if (cents === 0) return 'Free';
    const value = cents / 100;
    try {
        return new Intl.NumberFormat(undefined, { style: 'currency', currency }).format(value);
    } catch {
        return `${currency} ${value.toFixed(2)}`;
    }
};

export function ProgramDiscoveryPage() {
    const [search, setSearch] = useState('');
    const [programs, setPrograms] = useState<ProgramListItem[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchPrograms = useCallback(async () => {
        setLoading(true);
        try {
            const data = await getPublicPrograms(search || undefined);
            setPrograms(
                data.filter(p => p.status === 'published' && p.is_public),
            );
        } catch (err) {
            console.error('Failed to load programs', err);
        } finally {
            setLoading(false);
        }
    }, [search]);

    useEffect(() => {
        fetchPrograms();
    }, [fetchPrograms]);

    return (
        <PublicLayout>
            <div className="container mx-auto py-8 px-4 max-w-7xl">
                <PageHeader
                    title="Programs"
                    description="Curated bundles of courses — buy the whole program at a discount."
                />

            <div className="my-6 flex gap-2">
                <div className="relative flex-1 max-w-md">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                        className="pl-9"
                        placeholder="Search programs"
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                    />
                </div>
            </div>

            {loading ? (
                <div className="text-center py-16 text-muted-foreground">Loading…</div>
            ) : programs.length === 0 ? (
                <div className="text-center py-16">
                    <Layers className="h-12 w-12 mx-auto text-muted-foreground/50 mb-3" />
                    <p className="text-muted-foreground">
                        {search ? 'No programs match your search.' : 'No programs are available yet.'}
                    </p>
                </div>
            ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                    {programs.map(program => (
                        <Card key={program.uuid} className="overflow-hidden hover:shadow-md transition-shadow">
                            <Link to={`/programs/${program.slug}`} className="block">
                                {program.effective_image_url ? (
                                    <img
                                        src={program.effective_image_url}
                                        alt={program.title}
                                        className="w-full h-40 object-cover"
                                    />
                                ) : (
                                    <div className="w-full h-40 bg-gradient-to-br from-primary/10 to-primary/5 flex items-center justify-center">
                                        <Layers className="h-12 w-12 text-primary/40" />
                                    </div>
                                )}
                                <CardContent className="p-4 space-y-3">
                                    <div className="flex items-start justify-between gap-2">
                                        <h3 className="font-semibold text-lg line-clamp-2">
                                            {program.title}
                                        </h3>
                                        <Badge variant="secondary">Program</Badge>
                                    </div>
                                    {program.short_description && (
                                        <p className="text-sm text-muted-foreground line-clamp-2">
                                            {program.short_description}
                                        </p>
                                    )}
                                    <div className="flex items-center justify-between text-sm">
                                        <span className="flex items-center gap-1 text-muted-foreground">
                                            <BookOpen className="h-3.5 w-3.5" />
                                            {program.course_count} course{program.course_count === 1 ? '' : 's'}
                                        </span>
                                        <span className="font-medium">
                                            {formatPrice(program.price_cents, program.currency)}
                                        </span>
                                    </div>
                                </CardContent>
                            </Link>
                        </Card>
                    ))}
                </div>
            )}
            </div>
        </PublicLayout>
    );
}

export default ProgramDiscoveryPage;
