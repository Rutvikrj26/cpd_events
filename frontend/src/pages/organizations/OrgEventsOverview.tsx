import React, { useEffect, useState } from 'react';
import { Calendar, Loader2, Search } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import { StatusBadge } from '@/components/custom/StatusBadge';
import { getOrganizationEvents } from '@/api/organizations';
import { Event } from '@/api/events/types';

interface OrgEventsOverviewProps {
    orgUuid: string;
    canCreateEvents?: boolean;
}

const OrgEventsOverview: React.FC<OrgEventsOverviewProps> = ({ orgUuid, canCreateEvents = false }) => {
    const navigate = useNavigate();
    const [events, setEvents] = useState<Event[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [statusFilter, setStatusFilter] = useState('all');

    useEffect(() => {
        const loadEvents = async () => {
            if (!orgUuid) return;
            setIsLoading(true);
            setError(null);
            try {
                const data = await getOrganizationEvents(orgUuid);
                setEvents(data);
            } catch (err: any) {
                console.error('Failed to load organization events', err);
                setError(err?.message || 'Failed to load organization events');
                toast.error('Failed to load organization events');
            } finally {
                setIsLoading(false);
            }
        };

        loadEvents();
    }, [orgUuid]);

    const filteredEvents = events.filter(event => {
        const matchesSearch = event.title.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesStatus = statusFilter === 'all' || event.status === statusFilter;
        return matchesSearch && matchesStatus;
    });

    const formatEventDate = (startsAt?: string) => {
        if (!startsAt) {
            return { date: 'TBD', time: '' };
        }
        const parsed = new Date(startsAt);
        if (Number.isNaN(parsed.getTime())) {
            return { date: 'TBD', time: '' };
        }
        return {
            date: parsed.toLocaleDateString(),
            time: parsed.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };
    };

    return (
        <Card>
            <CardHeader className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                    <CardTitle>Organization Events</CardTitle>
                    <CardDescription>All events across organizers in this organization.</CardDescription>
                </div>
                {canCreateEvents && (
                    <Button onClick={() => navigate('/events/create')}>
                        Create Event
                    </Button>
                )}
            </CardHeader>
            <CardContent>
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                    <div className="relative w-full sm:max-w-sm">
                        <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                        <Input
                            placeholder="Search events..."
                            className="pl-8"
                            value={searchTerm}
                            onChange={(event) => setSearchTerm(event.target.value)}
                        />
                    </div>

                    <div className="w-full sm:w-48">
                        <Select value={statusFilter} onValueChange={setStatusFilter}>
                            <SelectTrigger>
                                <SelectValue placeholder="Filter by status" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="all">All Statuses</SelectItem>
                                <SelectItem value="draft">Draft</SelectItem>
                                <SelectItem value="published">Published</SelectItem>
                                <SelectItem value="live">Live</SelectItem>
                                <SelectItem value="completed">Completed</SelectItem>
                                <SelectItem value="cancelled">Cancelled</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                </div>

                <div className="mt-4">
                    {isLoading ? (
                        <div className="flex items-center justify-center py-12">
                            <Loader2 className="h-8 w-8 animate-spin text-primary" />
                        </div>
                    ) : error ? (
                        <div className="text-center py-12 text-muted-foreground">
                            <Calendar className="h-10 w-10 mx-auto mb-3 opacity-50" />
                            <p>{error}</p>
                        </div>
                    ) : (
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Event</TableHead>
                                    <TableHead>Organizer</TableHead>
                                    <TableHead>Status</TableHead>
                                    <TableHead>Starts</TableHead>
                                    <TableHead className="text-right">Registrations</TableHead>
                                    <TableHead className="text-right">Actions</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {filteredEvents.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={6} className="h-24 text-center text-muted-foreground">
                                            No events found.
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    filteredEvents.map((event) => {
                                        const startInfo = formatEventDate(event.starts_at);
                                        return (
                                            <TableRow key={event.uuid}>
                                                <TableCell>
                                                    <div className="font-medium">{event.title}</div>
                                                    <div className="text-xs text-muted-foreground">{event.slug}</div>
                                                </TableCell>
                                                <TableCell>
                                                    <div className="text-sm text-foreground">{event.owner_name || 'Unknown'}</div>
                                                </TableCell>
                                                <TableCell>
                                                    <StatusBadge status={event.status} />
                                                </TableCell>
                                                <TableCell>
                                                    <div className="text-sm text-foreground">{startInfo.date}</div>
                                                    {startInfo.time && (
                                                        <div className="text-xs text-muted-foreground">{startInfo.time}</div>
                                                    )}
                                                </TableCell>
                                                <TableCell className="text-right">
                                                    {event.registration_count}
                                                </TableCell>
                                                <TableCell className="text-right">
                                                    <Button variant="outline" size="sm" asChild>
                                                        <Link to={`/organizer/events/${event.uuid}/manage`}>
                                                            Manage
                                                        </Link>
                                                    </Button>
                                                </TableCell>
                                            </TableRow>
                                        );
                                    })
                                )}
                            </TableBody>
                        </Table>
                    )}
                </div>
            </CardContent>
        </Card>
    );
};

export default OrgEventsOverview;
