import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Plus, Layers, BookOpen, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { PageHeader } from '@/components/ui/page-header';
import { getPrograms, type ProgramListItem } from '@/api/programs';

const OrgProgramsPage: React.FC = () => {
    const navigate = useNavigate();
    const [programs, setPrograms] = useState<ProgramListItem[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let cancelled = false;
        const load = async () => {
            try {
                const data = await getPrograms({ owned: true });
                if (!cancelled) setPrograms(data);
            } catch (err) {
                console.error('Failed to load programs', err);
            } finally {
                if (!cancelled) setLoading(false);
            }
        };
        load();
        return () => {
            cancelled = true;
        };
    }, []);

    const formatPrice = (cents: number, currency: string): string => {
        if (cents === 0) return 'Free';
        try {
            return new Intl.NumberFormat(undefined, { style: 'currency', currency }).format(cents / 100);
        } catch {
            return `${currency} ${(cents / 100).toFixed(2)}`;
        }
    };

    return (
        <div className="container mx-auto py-8 px-4 max-w-6xl">
            <PageHeader
                title="Programs"
                description="Bundle courses and offer them at a discount."
                actions={
                    <Button onClick={() => navigate('/programs/manage/new')}>
                        <Plus className="mr-2 h-4 w-4" /> New program
                    </Button>
                }
            />

            <div className="mt-6">
                {loading ? (
                    <div className="flex justify-center py-12">
                        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                    </div>
                ) : programs.length === 0 ? (
                    <Card>
                        <CardContent className="py-12 text-center space-y-3">
                            <Layers className="h-10 w-10 mx-auto text-muted-foreground/50" />
                            <p className="text-muted-foreground">No programs yet.</p>
                            <Button variant="outline" onClick={() => navigate('/programs/manage/new')}>
                                Create your first program
                            </Button>
                        </CardContent>
                    </Card>
                ) : (
                    <div className="grid gap-3">
                        {programs.map(p => (
                            <Card key={p.uuid} className="hover:bg-accent/50 transition-colors">
                                <Link to={`/programs/manage/${p.slug}`} className="block">
                                    <CardContent className="p-4 flex items-center gap-4">
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2">
                                                <h3 className="font-medium">{p.title}</h3>
                                                <Badge
                                                    variant={p.status === 'published' ? 'default' : 'secondary'}
                                                    className="capitalize"
                                                >
                                                    {p.status}
                                                </Badge>
                                            </div>
                                            {p.short_description && (
                                                <p className="text-sm text-muted-foreground line-clamp-1 mt-1">
                                                    {p.short_description}
                                                </p>
                                            )}
                                            <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                                                <span className="flex items-center gap-1">
                                                    <BookOpen className="h-3.5 w-3.5" />
                                                    {p.course_count} course{p.course_count === 1 ? '' : 's'}
                                                </span>
                                                <span>{p.enrollment_count} enrolled</span>
                                            </div>
                                        </div>
                                        <div className="text-sm font-medium">
                                            {formatPrice(p.price_cents, p.currency)}
                                        </div>
                                    </CardContent>
                                </Link>
                            </Card>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default OrgProgramsPage;
