import { useEffect, useMemo, useState } from 'react';
import { formatDistanceToNow } from 'date-fns';
import { Award, BadgeCheck, Loader2, Search } from 'lucide-react';
import { toast } from 'sonner';

import { PageHeader } from '@/components/custom/PageHeader';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { getOrganizationCertificates } from '@/api/certificates';
import { getIssuedBadgesByMe } from '@/api/badges';

type Kind = 'certificate' | 'badge';
type SourceKind = 'event' | 'course';

type IssuedAccreditation = {
    key: string;
    kind: Kind;
    source_kind: SourceKind | null;
    source_title: string;
    recipient_name: string;
    recipient_email?: string;
    template_name: string;
    short_code: string;
    status: 'active' | 'revoked';
    issued_at: string;
};

type KindFilter = 'all' | Kind;
type SourceFilter = 'all' | SourceKind;

export function OrganizerAccreditationsPage() {
    const [items, setItems] = useState<IssuedAccreditation[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [kindFilter, setKindFilter] = useState<KindFilter>('all');
    const [sourceFilter, setSourceFilter] = useState<SourceFilter>('all');

    useEffect(() => {
        let cancelled = false;
        setLoading(true);

        Promise.all([
            getOrganizationCertificates().catch((err) => {
                console.error('Failed to load issued certificates', err);
                return { count: 0, results: [] };
            }),
            getIssuedBadgesByMe().catch((err) => {
                console.error('Failed to load issued badges', err);
                return { count: 0, results: [] } as any;
            }),
        ])
            .then(([certs, badges]) => {
                if (cancelled) return;

                const certItems: IssuedAccreditation[] = (certs.results ?? []).map((c) => {
                    const sourceKind: SourceKind | null =
                        c.event?.title ? 'event' : c.certificate_data?.event_title ? 'event' : null;
                    return {
                        key: `cert-${c.uuid}`,
                        kind: 'certificate',
                        source_kind: sourceKind,
                        source_title:
                            c.event?.title ??
                            c.event_title ??
                            c.certificate_data?.event_title ??
                            '—',
                        recipient_name:
                            c.registrant_name ??
                            c.certificate_data?.attendee_name ??
                            c.certificate_data?.recipient_name ??
                            '—',
                        template_name: c.certificate_data?.event_title ?? 'Certificate',
                        short_code: c.short_code,
                        status: c.status,
                        issued_at: c.issued_at,
                    };
                });

                const badgeResults = (badges.results ?? []) as {
                    uuid: string;
                    template_name: string;
                    recipient_name: string;
                    verification_code: string;
                    short_code: string;
                    status: 'active' | 'revoked';
                    issued_at: string;
                    event_title?: string;
                    course_title?: string;
                }[];
                const badgeItems: IssuedAccreditation[] = badgeResults.map((b) => ({
                    key: `badge-${b.uuid}`,
                    kind: 'badge',
                    source_kind: b.course_title ? 'course' : b.event_title ? 'event' : null,
                    source_title: b.course_title ?? b.event_title ?? '—',
                    recipient_name: b.recipient_name,
                    template_name: b.template_name,
                    short_code: b.short_code,
                    status: b.status,
                    issued_at: b.issued_at,
                }));

                const tsOf = (s: string | undefined) => {
                    if (!s) return 0;
                    const t = new Date(s).getTime();
                    return Number.isNaN(t) ? 0 : t;
                };
                const merged = [...certItems, ...badgeItems].sort(
                    (a, b) => tsOf(b.issued_at) - tsOf(a.issued_at)
                );
                setItems(merged);
            })
            .catch(() => {
                toast.error('Failed to load accreditations.');
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
            if (sourceFilter !== 'all' && item.source_kind !== sourceFilter) return false;
            if (!term) return true;
            return (
                item.template_name.toLowerCase().includes(term) ||
                item.source_title.toLowerCase().includes(term) ||
                item.recipient_name.toLowerCase().includes(term) ||
                item.short_code.toLowerCase().includes(term)
            );
        });
    }, [items, search, kindFilter, sourceFilter]);

    const counts = useMemo(() => {
        const certs = items.filter((i) => i.kind === 'certificate').length;
        const badges = items.filter((i) => i.kind === 'badge').length;
        const revoked = items.filter((i) => i.status === 'revoked').length;
        return { total: items.length, certs, badges, revoked };
    }, [items]);

    return (
        <div className="space-y-6">
            <PageHeader
                title="Accreditations"
                description="Certificates and badges you've issued from events and courses."
            />

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
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
                <Card>
                    <CardContent className="pt-6">
                        <p className="text-sm text-muted-foreground">Revoked</p>
                        <p className="text-3xl font-semibold text-foreground">{counts.revoked}</p>
                    </CardContent>
                </Card>
            </div>

            <div className="flex flex-col sm:flex-row gap-3">
                <div className="relative flex-1">
                    <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                        placeholder="Search by recipient, event, course, or code…"
                        className="pl-9"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                    />
                </div>
                <Select value={kindFilter} onValueChange={(v) => setKindFilter(v as KindFilter)}>
                    <SelectTrigger className="w-full sm:w-44">
                        <SelectValue placeholder="Type" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="all">All types</SelectItem>
                        <SelectItem value="certificate">Certificates</SelectItem>
                        <SelectItem value="badge">Badges</SelectItem>
                    </SelectContent>
                </Select>
                <Select value={sourceFilter} onValueChange={(v) => setSourceFilter(v as SourceFilter)}>
                    <SelectTrigger className="w-full sm:w-44">
                        <SelectValue placeholder="Source" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="all">All sources</SelectItem>
                        <SelectItem value="event">From events</SelectItem>
                        <SelectItem value="course">From courses</SelectItem>
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
                                ? "No accreditations issued yet."
                                : 'No accreditations match your filter.'}
                        </p>
                        {items.length === 0 && (
                            <p className="text-sm mt-1">
                                Issue certificates and badges from your events and courses to see them here.
                            </p>
                        )}
                    </CardContent>
                </Card>
            ) : (
                <div className="grid gap-3">
                    {filtered.map((item) => (
                        <IssuedRow key={item.key} item={item} />
                    ))}
                </div>
            )}
        </div>
    );
}

function IssuedRow({ item }: { item: IssuedAccreditation }) {
    const issued = item.issued_at ? new Date(item.issued_at) : null;
    const issuedValid = issued !== null && !Number.isNaN(issued.getTime());
    const isBadge = item.kind === 'badge';
    const Icon = isBadge ? BadgeCheck : Award;

    return (
        <Card>
            <CardContent className="py-4">
                <div className="flex items-start gap-4">
                    <div
                        className={`h-10 w-10 rounded-full flex items-center justify-center shrink-0 ${
                            isBadge ? 'bg-primary/10 text-primary' : 'bg-warning-subtle text-warning'
                        }`}
                    >
                        <Icon className="h-5 w-5" />
                    </div>
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                            <h3 className="font-semibold text-foreground truncate">{item.template_name}</h3>
                            <Badge variant="secondary" className="capitalize">
                                {item.kind}
                            </Badge>
                            {item.source_kind && (
                                <Badge variant="outline" className="capitalize">
                                    {item.source_kind}
                                </Badge>
                            )}
                            {item.status === 'revoked' && (
                                <Badge variant="destructive">Revoked</Badge>
                            )}
                        </div>
                        <p className="text-sm text-muted-foreground mt-1 truncate">
                            Issued to <span className="text-foreground">{item.recipient_name}</span>
                            {' · '}
                            <span>{item.source_title}</span>
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">
                            {issuedValid && (
                                <>
                                    {formatDistanceToNow(issued!, { addSuffix: true })}
                                    {' · '}
                                    {issued!.toLocaleDateString(undefined, {
                                        month: 'short',
                                        day: 'numeric',
                                        year: 'numeric',
                                    })}
                                    {' · '}
                                </>
                            )}
                            Code <span className="font-mono">{item.short_code}</span>
                        </p>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}
