import React, { useEffect, useState } from 'react';
import { Link, useOutletContext } from 'react-router-dom';
import { Award, Eye, Calendar, Search, Filter } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { getEvents } from '@/api/events';
import { getEventCertificates } from '@/api/certificates';
import { Certificate } from '@/api/certificates/types';
import { Event } from '@/api/events/types';
import { toast } from 'sonner';
import { useAuth } from '@/contexts/AuthContext';
import { Subscription } from '@/api/billing/types';
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

interface CertificateWithEvent extends Certificate {
    eventTitle?: string;
}

type DashboardOutletContext = {
    subscription: Subscription | null;
};

export const OrganizerCertificatesPage = () => {
    const [certificates, setCertificates] = useState<CertificateWithEvent[]>([]);
    const [events, setEvents] = useState<Event[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedEvent, setSelectedEvent] = useState<string>('all');
    const [searchTerm, setSearchTerm] = useState('');

    const { user } = useAuth();
    const outletContext = useOutletContext<DashboardOutletContext | undefined>();
    const subscription = outletContext?.subscription ?? null;
    const { isOrganizer, isCourseManager } = getRoleFlags(user, subscription);

    // Course managers (LMS plan) don't have event access - they only manage templates
    const hasEventAccess = isOrganizer && !isCourseManager;

    useEffect(() => {
        const fetchData = async () => {
            try {
                // Only fetch events for organizers who have event access
                if (hasEventAccess) {
                    const eventsData = await getEvents();
                    setEvents(eventsData.results);

                    // Fetch certificates from all events
                    const allCerts: CertificateWithEvent[] = [];
                    for (const event of eventsData.results) {
                        try {
                            const certs = await getEventCertificates(event.uuid);
                            certs.forEach(cert => {
                                allCerts.push({
                                    ...cert,
                                    eventTitle: event.title,
                                });
                            });
                        } catch {
                            // Skip events with no certificates or errors
                        }
                    }
                    setCertificates(allCerts);
                }
                // For course managers, we just show templates (no event-based certificates)
            } catch (error) {
                console.error("Failed to load data", error);
                toast.error("Failed to load certificates");
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, [hasEventAccess]);

    // Filter certificates
    const filteredCertificates = certificates.filter(cert => {
        const matchesEvent = selectedEvent === 'all' || cert.event?.uuid === selectedEvent;
        const matchesSearch = searchTerm === '' ||
            (cert.registrant_name || cert.certificate_data?.recipient_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
            cert.short_code?.toLowerCase().includes(searchTerm.toLowerCase());
        return matchesEvent && matchesSearch;
    });

    if (loading) {
        return (
            <div className="p-8 flex items-center justify-center">
                <div className="animate-pulse text-muted-foreground">Loading certificates...</div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold text-foreground">Certificates</h1>
                <p className="text-muted-foreground mt-1">Manage issued certificates and templates</p>
            </div>

            <Tabs defaultValue="issued" className="w-full">
                <TabsList className="grid w-full grid-cols-2 max-w-[400px] mb-6">
                    <TabsTrigger value="issued">Issued Certificates</TabsTrigger>
                    <TabsTrigger value="templates">Templates</TabsTrigger>
                </TabsList>

                <TabsContent value="issued" className="space-y-6">
                    <div className="flex items-center justify-between">
                        <div>
                            <h2 className="text-xl font-semibold">Issued Certificates</h2>
                            <p className="text-sm text-muted-foreground">Tracking {certificates.length} certificates issued across events</p>
                        </div>
                    </div>

                    {/* Filters */}
                    {certificates.length > 0 && (
                        <div className="flex flex-col sm:flex-row gap-4">
                            <div className="relative flex-1 max-w-sm">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                <Input
                                    placeholder="Search by name or ID..."
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
                    )}

                    {filteredCertificates.length > 0 ? (
                        <div className="border rounded-lg overflow-hidden">
                            <Table>
                                <TableHeader>
                                    <TableRow className="bg-muted/50">
                                        <TableHead>Recipient</TableHead>
                                        <TableHead>Event</TableHead>
                                        <TableHead>Certificate ID</TableHead>
                                        <TableHead>Issued</TableHead>
                                        <TableHead>Status</TableHead>
                                        <TableHead className="text-right">Actions</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {filteredCertificates.map(cert => (
                                        <TableRow key={cert.uuid} className="hover:bg-muted/30">
                                            <TableCell>
                                                <div className="flex items-center gap-3">
                                                    <div className="h-8 w-8 bg-primary/10 text-primary rounded-full flex items-center justify-center shrink-0">
                                                        <Award size={14} />
                                                    </div>
                                                    <span className="font-medium">
                                                        {cert.registrant_name || cert.certificate_data?.recipient_name || 'Unknown'}
                                                    </span>
                                                </div>
                                            </TableCell>
                                            <TableCell>
                                                <span className="text-sm text-muted-foreground">
                                                    {cert.eventTitle || cert.event?.title || '-'}
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
                                                        year: 'numeric'
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
                                Certificates will appear here once you issue them to event attendees.
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

                <TabsContent value="templates">
                    <CertificateTemplatesList />
                </TabsContent>
            </Tabs>
        </div>
    );
};
