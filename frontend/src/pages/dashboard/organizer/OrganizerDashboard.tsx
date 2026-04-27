import { Link } from 'react-router-dom';
import {
    Activity,
    ArrowRight,
    Award,
    BookOpen,
    Building2,
    Calendar,
    CheckCircle2,
    GraduationCap,
    MoreHorizontal,
    Plus,
    Users,
} from 'lucide-react';
import { OnboardingChecklist } from '@/components/onboarding';
import { AdminLiveRoomsWidget } from '@/components/dashboard/AdminLiveRoomsWidget';
import { Button } from '@/shared/ui/button';
import { Card, CardContent } from '@/shared/ui/card';
import { Badge } from '@/shared/ui/badge';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuTrigger,
} from '@/shared/ui/dropdown-menu';
import { EmptyState } from '@/shared/ui/empty-state';
import { useAuth } from '@/features/auth';
import {
    HeroBand,
    MiniStat,
    SectionHeader,
    DashboardSkeleton,
    useOrganizerDashboard,
} from '@/features/dashboard';
import { getRoleFlags } from '@/lib/role-utils';
import { formatDate } from '@/lib/datetime';

const EVENT_STATUS_VARIANT: Record<string, 'success' | 'progress' | 'locked' | 'overdue' | 'secondary'> = {
    published: 'success',
    live: 'overdue',
    draft: 'secondary',
    completed: 'locked',
};

export function OrganizerDashboard() {
    const { user } = useAuth();
    const { isAdmin, isInstructor } = getRoleFlags(user);
    const dashboard = useOrganizerDashboard({ includeCourses: isInstructor });

    if (dashboard.isLoading) {
        return <DashboardSkeleton />;
    }

    const { eventStats, courseStats, recentEvents } = dashboard;

    return (
        <div className="space-y-block animate-in fade-in slide-in-from-bottom-4 duration-500">
            <HeroBand
                eyebrow={isAdmin ? 'Admin portal' : 'Organizer portal'}
                title={isAdmin ? 'Admin dashboard' : 'Organizer dashboard'}
                description="Manage your professional events, track attendance, and issue certificates."
                actions={[
                    {
                        label: <><Plus className="mr-2 h-4 w-4" /> Create event</>,
                        to: '/events/create',
                        primary: true,
                    },
                    { label: 'View all events', to: '/events' },
                ]}
            />

            {isAdmin && <AdminLiveRoomsWidget />}
            <OnboardingChecklist />

            {/* Event KPIs */}
            <div className="grid grid-cols-2 gap-tight lg:grid-cols-4">
                <MiniStat label="Total events" value={eventStats.totalEvents} icon={Calendar} tone="primary" />
                <MiniStat label="Active events" value={eventStats.activeEvents} icon={Activity} tone="success" />
                <MiniStat label="Registrations" value={eventStats.totalRegistrations} icon={Users} tone="muted" />
                <MiniStat label="Certificates" value={eventStats.certificatesIssued} icon={Award} tone="warning" />
            </div>

            {/* Course KPIs (instructor + admin only) */}
            {isInstructor && (
                <div className="grid grid-cols-2 gap-tight lg:grid-cols-4">
                    <MiniStat label="Total courses" value={courseStats.totalCourses} icon={BookOpen} tone="primary" />
                    <MiniStat label="Published" value={courseStats.publishedCourses} icon={CheckCircle2} tone="success" />
                    <MiniStat label="Enrollments" value={courseStats.courseEnrollments} icon={GraduationCap} tone="muted" />
                    <MiniStat label="Completions" value={courseStats.courseCompletions} icon={Award} tone="warning" />
                </div>
            )}

            <div className="grid grid-cols-1 gap-card lg:grid-cols-3">
                <div className="space-y-card lg:col-span-2">
                    <SectionHeader
                        title="Recent activity"
                        link={recentEvents.length > 0 ? { to: '/events', label: <>View all <ArrowRight className="ml-1 inline h-4 w-4" /></> } : undefined}
                    />

                    {recentEvents.length === 0 ? (
                        <EmptyState
                            tone="dashed"
                            icon={Calendar}
                            title="No events yet"
                            description="Create your first event to start engaging with your audience."
                            action={
                                <Button asChild>
                                    <Link to="/events/create">Create event</Link>
                                </Button>
                            }
                        />
                    ) : (
                        <Card elevation="rest" className="overflow-hidden">
                            <CardContent className="p-0">
                                <div className="overflow-x-auto">
                                    <table className="w-full text-left text-body">
                                        <thead className="border-b border-border bg-muted/40 text-caption font-medium uppercase tracking-wide text-muted-foreground">
                                            <tr>
                                                <th className="px-card py-3">Event name</th>
                                                <th className="px-card py-3">Date</th>
                                                <th className="px-card py-3">Status</th>
                                                <th className="px-card py-3 text-right">Registrations</th>
                                                <th className="w-[50px] px-card py-3" />
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-border">
                                            {recentEvents.map((event) => (
                                                <tr key={event.uuid} className="group transition-colors hover:bg-muted/40">
                                                    <td className="px-card py-3 font-medium text-foreground">
                                                        <div className="flex flex-col gap-1">
                                                            <Link
                                                                to={`/organizer/events/${event.uuid}/manage`}
                                                                className="block max-w-[200px] truncate transition-colors hover:text-primary sm:max-w-xs"
                                                            >
                                                                {event.title}
                                                            </Link>
                                                            {event.organization_info && (
                                                                <div className="flex items-center gap-1 text-caption text-muted-foreground">
                                                                    <Building2 className="h-3 w-3" />
                                                                    <span>{event.organization_info.name}</span>
                                                                </div>
                                                            )}
                                                        </div>
                                                    </td>
                                                    <td className="px-card py-3 text-muted-foreground">
                                                        {formatDate(event.starts_at, user)}
                                                    </td>
                                                    <td className="px-card py-3">
                                                        <Badge
                                                            variant={EVENT_STATUS_VARIANT[event.status] || 'secondary'}
                                                            className={`capitalize ${event.status === 'live' ? 'animate-pulse' : ''}`}
                                                        >
                                                            {event.status}
                                                        </Badge>
                                                    </td>
                                                    <td className="px-card py-3 text-right font-medium text-foreground tabular-nums">
                                                        {event.registration_count}
                                                    </td>
                                                    <td className="px-card py-3 text-right">
                                                        <DropdownMenu>
                                                            <DropdownMenuTrigger asChild>
                                                                <Button
                                                                    variant="ghost"
                                                                    size="icon"
                                                                    className="h-8 w-8 text-muted-foreground hover:text-foreground"
                                                                >
                                                                    <MoreHorizontal className="h-4 w-4" />
                                                                </Button>
                                                            </DropdownMenuTrigger>
                                                            <DropdownMenuContent align="end">
                                                                <DropdownMenuLabel>Actions</DropdownMenuLabel>
                                                                <DropdownMenuItem asChild>
                                                                    <Link to={`/organizer/events/${event.uuid}/manage`}>
                                                                        Manage event
                                                                    </Link>
                                                                </DropdownMenuItem>
                                                                <DropdownMenuItem asChild>
                                                                    <Link to={`/events/${event.uuid}/edit`}>Edit event</Link>
                                                                </DropdownMenuItem>
                                                            </DropdownMenuContent>
                                                        </DropdownMenu>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </CardContent>
                        </Card>
                    )}
                </div>

                <div className="space-y-card">
                    <SectionHeader title="Quick actions" />
                    <div className="space-y-tight">
                        <QuickAction icon={Plus} title="Create event" subtitle="Schedule a new webinar" to="/events/create" />
                        {isInstructor && (
                            <QuickAction
                                icon={BookOpen}
                                title="Create course"
                                subtitle="Build a new learning path"
                                to="/courses/manage/new"
                            />
                        )}
                        <QuickAction
                            icon={Users}
                            title="Attendees"
                            subtitle="View registered users"
                            to="/organizer/contacts"
                        />
                    </div>
                </div>
            </div>
        </div>
    );
}

function QuickAction({
    icon: IconComp,
    title,
    subtitle,
    to,
}: {
    icon: React.ComponentType<{ className?: string }>;
    title: string;
    subtitle: string;
    to: string;
}) {
    return (
        <Link
            to={to}
            className="group flex items-center gap-tight rounded-lg border border-border bg-card p-tight transition-colors hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/60"
        >
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary transition-colors group-hover:bg-primary/20">
                <IconComp className="h-4 w-4" />
            </div>
            <div className="min-w-0 flex-1">
                <div className="text-body font-semibold text-foreground transition-colors group-hover:text-primary">
                    {title}
                </div>
                <div className="text-caption text-muted-foreground">{subtitle}</div>
            </div>
            <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-primary" />
        </Link>
    );
}
