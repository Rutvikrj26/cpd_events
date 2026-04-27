import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { formatDistanceToNow } from 'date-fns';
import { Award, BadgeCheck, Download, ExternalLink, Loader2, Search } from 'lucide-react';
import { toast } from 'sonner';

import { PageHeader } from '@/components/custom/PageHeader';
import { Button } from '@/shared/ui/button';
import { Card, CardContent } from '@/shared/ui/card';
import { Input } from '@/shared/ui/input';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/shared/ui/select';
import { Badge } from '@/shared/ui/badge';
import { AccreditationItem, getMyAccreditations } from '@/api/accounts';

type KindFilter = 'all' | 'certificate' | 'badge';

export function MyAccreditationsPage() {
    const [items, setItems] = useState<AccreditationItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [kindFilter, setKindFilter] = useState<KindFilter>('all');

    useEffect(() => {
        let cancelled = false;
        setLoading(true);
        getMyAccreditations()
            .then((data) => !cancelled && setItems(data.results))
            .catch((err) => {
                console.error(err);
                toast.error('Failed to load your accreditations.');
            })
            .finally(() => !cancelled && setLoading(false));
        return () => {
            cancelled = true;
        };
    }, []);

    const filtered = useMemo(() => {
        const term = search.trim().toLowerCase();
        return items.filter((item) => {
            if (kindFilter !== 'all' && item.kind !== kindFilter) return false;
            if (!term) return true;
            return (
                item.title.toLowerCase().includes(term) ||
                item.source_title.toLowerCase().includes(term) ||
                item.short_code.toLowerCase().includes(term)
            );
        });
    }, [items, search, kindFilter]);

    const counts = useMemo(() => {
        const certs = items.filter((i) => i.kind === 'certificate').length;
        const badges = items.filter((i) => i.kind === 'badge').length;
        return { total: items.length, certs, badges };
    }, [items]);

    return (
        <div className="space-y-6">
            <PageHeader
                title="My Accreditations"
                description="Certificates and badges you've earned across events and courses."
            />

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <Card>
                    <CardContent className="pt-6">
                        <p className="text-sm text-muted-foreground">Total</p>
                        <p className="text-3xl font-semibold text-foreground">{counts.total}</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="pt-6">
                        <p className="text-sm text-muted-foreground">Certificates</p>
                        <p className="text-3xl font-semibold text-foreground">{counts.certs}</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="pt-6">
                        <p className="text-sm text-muted-foreground">Badges</p>
                        <p className="text-3xl font-semibold text-foreground">{counts.badges}</p>
                    </CardContent>
                </Card>
            </div>

            <div className="flex flex-col sm:flex-row gap-3">
                <div className="relative flex-1">
                    <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                        placeholder="Search by event, course, title, or code…"
                        className="pl-9"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                    />
                </div>
                <Select value={kindFilter} onValueChange={(v) => setKindFilter(v as KindFilter)}>
                    <SelectTrigger className="w-full sm:w-44">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="all">All types</SelectItem>
                        <SelectItem value="certificate">Certificates</SelectItem>
                        <SelectItem value="badge">Badges</SelectItem>
                    </SelectContent>
                </Select>
            </div>

            {loading ? (
                <div className="flex items-center justify-center py-16">
                    <Loader2 className="h-5 w-5 animate-spin mr-2" /> Loading…
                </div>
            ) : filtered.length === 0 ? (
                <Card>
                    <CardContent className="py-12 text-center text-muted-foreground">
                        <Award className="h-12 w-12 mx-auto text-muted-foreground/40 mb-3" />
                        <p className="font-medium">
                            {items.length === 0
                                ? "You haven't earned any accreditations yet."
                                : 'No accreditations match your filter.'}
                        </p>
                        {items.length === 0 && (
                            <p className="text-sm mt-1">
                                Attend events or complete courses to start earning.
                            </p>
                        )}
                    </CardContent>
                </Card>
            ) : (
                <div className="grid gap-3">
                    {filtered.map((item) => (
                        <AccreditationRow key={`${item.kind}-${item.uuid}`} item={item} />
                    ))}
                </div>
            )}
        </div>
    );
}

function AccreditationRow({ item }: { item: AccreditationItem }) {
    const issued = new Date(item.issued_at);
    const isBadge = item.kind === 'badge';
    const Icon = isBadge ? BadgeCheck : Award;

    const detailHref = isBadge
        ? `/badges/verify/${item.verification_code}`
        : `/verify/${item.verification_code}`;

    return (
        <Card>
            <CardContent className="py-4">
                <div className="flex items-start gap-4">
                    <div
                        className={`h-10 w-10 rounded-full flex items-center justify-center shrink-0 ${
                            isBadge
                                ? 'bg-primary/10 text-primary'
                                : 'bg-warning-subtle text-warning'
                        }`}
                    >
                        <Icon className="h-5 w-5" />
                    </div>
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                            <h3 className="font-semibold text-foreground truncate">
                                {item.title}
                            </h3>
                            <Badge variant="secondary" className="capitalize">
                                {item.kind}
                            </Badge>
                            {item.source_kind && (
                                <Badge variant="outline" className="capitalize">
                                    {item.source_kind}
                                </Badge>
                            )}
                        </div>
                        {item.source_title && (
                            <p className="text-sm text-muted-foreground mt-1 truncate">
                                {item.source_title}
                            </p>
                        )}
                        <p className="text-xs text-muted-foreground mt-1">
                            Issued {formatDistanceToNow(issued, { addSuffix: true })}
                            {' · '}
                            {issued.toLocaleDateString(undefined, {
                                month: 'short',
                                day: 'numeric',
                                year: 'numeric',
                            })}
                            {' · '}
                            Code <span className="font-mono">{item.short_code}</span>
                        </p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                        {item.artifact_url && (
                            <Button
                                variant="outline"
                                size="sm"
                                asChild
                                title={isBadge ? 'Download badge' : 'Download certificate'}
                            >
                                <a
                                    href={item.artifact_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                >
                                    <Download className="h-4 w-4 mr-1" />
                                    Download
                                </a>
                            </Button>
                        )}
                        <Button variant="ghost" size="sm" asChild>
                            <Link to={detailHref}>
                                <ExternalLink className="h-4 w-4 mr-1" />
                                View
                            </Link>
                        </Button>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}
