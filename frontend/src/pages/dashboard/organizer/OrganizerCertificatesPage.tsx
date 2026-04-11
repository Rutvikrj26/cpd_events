import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Award, Eye, Calendar, Search, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { getEvents } from '@/api/events';
import { getOrganizationCertificates } from '@/api/certificates';
import { Certificate } from '@/api/certificates/types';
import { Event } from '@/api/events/types';
import { toast } from 'sonner';
import { useAuth } from '@/contexts/AuthContext';
import { getRoleFlags } from '@/lib/role-utils';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { CertificateTemplatesList } from "@/components/certificates/CertificateTemplatesList";

export const OrganizerCertificatesPage = () => {
    const { user } = useAuth();
    const { isAdmin, isEducator, isCourseManager } = getRoleFlags(user);

    // Course managers (who are NOT also educators/admins) see templates only.
    // Admins and educators always see the issued-certificates listing.
    const hasIssuedCertsAccess = isAdmin || (isEducator && !isCourseManager);

    const [certificates, setCertificates] = useState<Certificate[]>([]);
    const [events, setEvents] = useState<Event[]>([]);
    const [loading, setLoading] = useState(hasIssuedCertsAccess);
    const [selectedEvent, setSelectedEvent] = useState<string>('all');
    const [searchTerm, setSearchTerm] = useState('');

    useEffect(() => {
        if (!hasIssuedCertsAccess) return;

        let cancelled = false;
        const run = async () => {
            setLoading(true);
            try {
                const [certsResp, eventsResp] = await Promise.all([
                    getOrganizationCertificates({
                        search: searchTerm || undefined,
                        event: selectedEvent !== 'all' ? selectedEvent : undefined,
                    }),
                    events.length === 0 ? getEvents() : Promise.resolve({ results: events } as any),
                ]);
                if (cancelled) return;
                setCertificates(certsResp.results);
                if (events.length === 0) {
                    setEvents(eventsResp.results);
                }
            } catch (error) {
                console.error('Failed to load certificates', error);
                toast.error('Failed to load certificates');
            } finally {
                if (!cancelled) setLoading(false);
            }
        };

        // Debounce the search / event filter so we don't hammer the endpoint.
        const handle = window.setTimeout(run, 200);
        return () => {
            cancelled = true;
            window.clearTimeout(handle);
        };
        // events.length intentionally captured to avoid refetching the event list each change
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [hasIssuedCertsAccess, searchTerm, selectedEvent]);

    const defaultTab = hasIssuedCertsAccess ? 'issued' : 'templates';

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold text-foreground">Certificates</h1>
                <p className="text-muted-foreground mt-1">Manage issued certificates and templates</p>
            </div>

            <Tabs defaultValue={defaultTab} className="w-full">
                <TabsList
                    className={`grid w-full max-w-[400px] mb-6 ${
                        hasIssuedCertsAccess ? 'grid-cols-2' : 'grid-cols-1'
                    }`}
                >
                    {hasIssuedCertsAccess && (
                        <TabsTrigger value="issued">Issued Certificates</TabsTrigger>
                    )}
                    <TabsTrigger value="templates">Templates</TabsTrigger>
                </TabsList>

                {hasIssuedCertsAccess && (
                    <TabsContent value="issued" className="space-y-6">
                        <div className="flex items-center justify-between">
                            <div>
                                <h2 className="text-xl font-semibold">Issued Certificates</h2>
                                <p className="text-sm text-muted-foreground">
                                    Tracking {certificates.length} certificate{certificates.length === 1 ? '' : 's'} across your institution's events
                                </p>
                            </div>
                        </div>

                        <div className="flex flex-col sm:flex-row gap-4">
                            <div className="relative flex-1 max-w-sm">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                <Input
                                    placeholder="Search by name or code..."
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                    className="pl-9"
                                />
                            </div>
                            <Select value={selectedEvent} onValueChange={setSelectedEvent}>
                                <SelectTrigger className="w-[200px]">
                                    <SelectValue placeholder="All Events" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">All Events</SelectItem>
                                    {events.map(event => (
                                        <SelectItem key={event.uuid} value={event.uuid}>
                                            {event.title}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>

                        {loading ? (
                            <div className="flex items-center justify-center py-16">
                                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                            </div>
                        ) : certificates.length > 0 ? (
                            <div className="border rounded-lg overflow-hidden">
                                <Table>
                                    <TableHeader>
                                        <TableRow className="bg-muted/50">
                                            <TableHead>Recipient</TableHead>
                                            <TableHead>Event / Course</TableHead>
                                            <TableHead>Certificate ID</TableHead>
                                            <TableHead>Issued</TableHead>
                                            <TableHead>Status</TableHead>
                                            <TableHead className="text-right">Actions</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {certificates.map(cert => (
                                            <TableRow key={cert.uuid} className="hover:bg-muted/30">
                                                <TableCell>
                                                    <div className="flex items-center gap-3">
                                                        <div className="h-8 w-8 bg-primary/10 text-primary rounded-full flex items-center justify-center shrink-0">
                                                            <Award size={14} />
                                                        </div>
                                                        <span className="font-medium">
                                                            {cert.registrant_name || cert.certificate_data?.recipient_name || cert.certificate_data?.attendee_name || 'Unknown'}
                                                        </span>
                                                    </div>
                                                </TableCell>
                                                <TableCell>
                                                    <span className="text-sm text-muted-foreground">
                                                        {cert.event_title || cert.event?.title || cert.certificate_data?.event_title || '-'}
                                                    </span>
                                                </TableCell>
                                                <TableCell>
                                                    <code className="text-sm bg-muted px-2 py-1 rounded font-mono">
                                                        {cert.short_code}
                                                    </code>
                                                </TableCell>
                                                <TableCell>
                                                    <span className="text-sm">
                                                        {new Date(cert.created_at).toLocaleDateString('en-US', {
                                                            month: 'short',
                                                            day: 'numeric',
                                                            year: 'numeric',
                                                        })}
                                                    </span>
                                                </TableCell>
                                                <TableCell>
                                                    {cert.status === 'revoked' ? (
                                                        <Badge variant="destructive">Revoked</Badge>
                                                    ) : (
                                                        <Badge variant="outline" className="text-primary border-primary/20 bg-primary/5">
                                                            Active
                                                        </Badge>
                                                    )}
                                                </TableCell>
                                                <TableCell className="text-right">
                                                    <Button
                                                        variant="ghost"
                                                        size="sm"
                                                        className="h-8"
                                                        onClick={() => window.open(`/verify/${cert.short_code}`, '_blank')}
                                                    >
                                                        <Eye size={14} className="mr-1" />
                                                        View
                                                    </Button>
                                                </TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </div>
                        ) : (
                            <div className="flex flex-col items-center justify-center py-20 bg-muted/30 rounded-lg border border-dashed">
                                <div className="h-16 w-16 bg-muted rounded-full flex items-center justify-center mb-4 text-muted-foreground">
                                    <Award size={32} />
                                </div>
                                <h3 className="text-lg font-medium text-foreground mb-1">No certificates issued yet</h3>
                                <p className="text-muted-foreground text-center max-w-sm">
                                    Certificates will appear here once they are issued to event attendees or course graduates.
                                </p>
                                <Link to="/events" className="mt-4">
                                    <Button variant="outline">
                                        <Calendar size={16} className="mr-2" />
                                        Go to Events
                                    </Button>
                                </Link>
                            </div>
                        )}
                    </TabsContent>
                )}

                <TabsContent value="templates">
                    <CertificateTemplatesList />
                </TabsContent>
            </Tabs>
        </div>
    );
};
