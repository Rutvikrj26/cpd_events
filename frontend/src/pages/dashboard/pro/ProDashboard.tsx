import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
    Plus,
    Calendar,
    Users,
    Award,
    ArrowRight,
    MoreHorizontal,
    Video,
    Zap,
    BookOpen,
} from "lucide-react";
import { OnboardingChecklist } from "@/components/onboarding";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { DashboardStat } from "@/components/dashboard/DashboardStats";
import { PageHeader } from "@/components/ui/page-header";
import { DashboardSkeleton } from "@/components/ui/page-skeleton";
import { ZoomIntegrationCard } from "@/components/dashboard/ZoomIntegrationCard";
import { QuickActionsCard, QuickAction } from "@/components/dashboard/QuickActionsCard";
import { getEvents } from "@/api/events";
import { Event } from "@/api/events/types";
import { getOwnedCourses } from "@/api/courses";
import { Course } from "@/api/courses/types";
import { getZoomStatus, initiateZoomOAuth, disconnectZoom } from "@/api/integrations";
import { ZoomStatus } from "@/api/integrations/types";
import { toast } from "sonner";
import { useAuth } from "@/contexts/AuthContext";

export function ProDashboard() {
    const { user } = useAuth();
    const [events, setEvents] = useState<Event[]>([]);
    const [courses, setCourses] = useState<Course[]>([]);
    const [loading, setLoading] = useState(true);
    const [zoomStatus, setZoomStatus] = useState<ZoomStatus | null>(null);

    useEffect(() => {
        async function fetchData() {
            try {
                const [eventsData, coursesData, zoomData] = await Promise.all([
                    getEvents(),
                    getOwnedCourses(),
                    getZoomStatus().catch(() => null),
                ]);
                setEvents(eventsData.results);
                setCourses(coursesData);
                setZoomStatus(zoomData);
            } catch (error) {
                console.error("Failed to fetch dashboard data", error);
            } finally {
                setLoading(false);
            }
        }
        fetchData();
    }, []);

    const handleConnectZoom = async () => {
        try {
            const url = await initiateZoomOAuth();
            window.location.href = url;
        } catch (error) {
            toast.error("Connection Failed: Could not initiate Zoom connection.");
        }
    };

    const handleDisconnectZoom = async () => {
        try {
            await disconnectZoom();
            setZoomStatus({ is_connected: false });
            toast.success("Zoom account has been disconnected.");
        } catch (error) {
            toast.error("Disconnect Failed: Could not disconnect Zoom account.");
        }
    };

    const eventStats = {
        activeEvents: events.filter(e => ['published', 'live'].includes(e.status)).length,
        totalRegistrations: events.reduce((acc, e) => acc + (e.registration_count || 0), 0),
    };

    const courseStats = {
        publishedCourses: courses.filter((course) => course.status === 'published').length,
        totalEnrollments: courses.reduce((acc, course) => acc + (course.enrollment_count || 0), 0),
    };

    const totalCertificates =
        events.reduce((acc, e) => acc + (e.certificate_count || 0), 0) +
        courses.reduce((acc, c) => acc + (c.completion_count || 0), 0);

    if (loading) {
        return <DashboardSkeleton />;
    }


    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <PageHeader
                title="Creator Dashboard"
                description="Manage your professional events and courses from one central hub."
                actions={
                    <div className="flex gap-3">
                        <Button asChild variant="outline" size="sm">
                            <Link to="/courses/manage/new">
                                <Plus className="mr-2 h-4 w-4" />
                                New Course
                            </Link>
                        </Button>
                        <Button asChild size="sm">
                            <Link to="/events/create">
                                <Plus className="mr-2 h-4 w-4" />
                                New Event
                            </Link>
                        </Button>
                    </div>
                }
            />

            <OnboardingChecklist />

            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <DashboardStat
                    title="Active Events"
                    value={eventStats.activeEvents}
                    icon={Calendar}
                    description="Live & Published"
                />
                <DashboardStat
                    title="Active Courses"
                    value={courseStats.publishedCourses}
                    icon={BookOpen}
                    description="Published content"
                />
                <DashboardStat
                    title="Total Learners"
                    value={eventStats.totalRegistrations + courseStats.totalEnrollments}
                    icon={Users}
                    description="Registrations & Enrollments"
                />
                <DashboardStat
                    title="Certificates Issued"
                    value={totalCertificates}
                    icon={Award}
                    description="Total impact"
                />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <div className="lg:col-span-2 space-y-8">

                    {/* Recent Events Section */}
                    <div className="space-y-4">
                        <div className="flex items-center justify-between">
                            <h2 className="text-xl font-bold tracking-tight text-foreground flex items-center gap-2">
                                <Calendar className="h-5 w-5 text-primary" />
                                Recent Events
                            </h2>
                            <Button variant="ghost" size="sm" asChild className="text-primary">
                                <Link to="/events">View All <ArrowRight className="ml-1 h-4 w-4" /></Link>
                            </Button>
                        </div>
                        <Card className="border-border/60 shadow-sm overflow-hidden">
                            <CardContent className="p-0">
                                {events.length === 0 ? (
                                    <div className="p-8 text-center bg-muted/50">
                                        <p className="text-muted-foreground">No events yet. Create one to get started!</p>
                                    </div>
                                ) : (
                                    <div className="overflow-x-auto">
                                        <table className="w-full text-sm text-left">
                                            <thead className="bg-muted/80 border-b border-border text-muted-foreground font-medium">
                                                <tr>
                                                    <th className="px-6 py-3">Event</th>
                                                    <th className="px-6 py-3">Status</th>
                                                    <th className="px-6 py-3 text-right">Registrations</th>
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-border">
                                                {events.slice(0, 3).map(event => (
                                                    <tr key={event.uuid} className="group hover:bg-muted/50 transition-colors">
                                                        <td className="px-6 py-3 font-medium">
                                                            <Link to={`/organizer/events/${event.uuid}/manage`} className="hover:text-primary transition-colors block truncate max-w-[200px]">
                                                                {event.title}
                                                            </Link>
                                                        </td>
                                                        <td className="px-6 py-3">
                                                            <Badge variant="outline" className="capitalize">{event.status}</Badge>
                                                        </td>
                                                        <td className="px-6 py-3 text-right">{event.registration_count}</td>
                                                        <td className="px-6 py-3 w-[50px]">
                                                            <DropdownMenu>
                                                                <DropdownMenuTrigger asChild>
                                                                    <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground" aria-label="Event actions">
                                                                        <MoreHorizontal className="h-4 w-4" />
                                                                    </Button>
                                                                </DropdownMenuTrigger>
                                                                <DropdownMenuContent align="end">
                                                                    <DropdownMenuLabel>Actions</DropdownMenuLabel>
                                                                    <DropdownMenuItem asChild>
                                                                        <Link to={`/organizer/events/${event.uuid}/manage`}>Manage Event</Link>
                                                                    </DropdownMenuItem>
                                                                    <DropdownMenuItem asChild>
                                                                        <Link to={`/events/${event.uuid}/edit`}>Edit Event</Link>
                                                                    </DropdownMenuItem>
                                                                </DropdownMenuContent>
                                                            </DropdownMenu>
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </div>

                    {/* Recent Courses Section */}
                    <div className="space-y-4">
                        <div className="flex items-center justify-between">
                            <h2 className="text-xl font-bold tracking-tight text-foreground flex items-center gap-2">
                                <BookOpen className="h-5 w-5 text-primary" />
                                Recent Courses
                            </h2>
                            <Button variant="ghost" size="sm" asChild className="text-primary">
                                <Link to="/courses/manage">View All <ArrowRight className="ml-1 h-4 w-4" /></Link>
                            </Button>
                        </div>
                        <Card className="border-border/60 shadow-sm overflow-hidden">
                            <CardContent className="p-0">
                                {courses.length === 0 ? (
                                    <div className="p-8 text-center bg-muted/50">
                                        <p className="text-muted-foreground">No courses yet. Create one to build your library!</p>
                                    </div>
                                ) : (
                                    <div className="overflow-x-auto">
                                        <table className="w-full text-sm text-left">
                                            <thead className="bg-muted/80 border-b border-border text-muted-foreground font-medium">
                                                <tr>
                                                    <th className="px-6 py-3">Course</th>
                                                    <th className="px-6 py-3">Status</th>
                                                    <th className="px-6 py-3 text-right">Enrollments</th>
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-border">
                                                {courses.slice(0, 3).map(course => (
                                                    <tr key={course.uuid} className="group hover:bg-muted/50 transition-colors">
                                                        <td className="px-6 py-3 font-medium">
                                                            <Link to={`/courses/manage/${course.slug}`} className="hover:text-primary transition-colors block truncate max-w-[200px]">
                                                                {course.title}
                                                            </Link>
                                                        </td>
                                                        <td className="px-6 py-3">
                                                            <Badge variant="outline" className="capitalize">{course.status}</Badge>
                                                        </td>
                                                        <td className="px-6 py-3 text-right">{course.enrollment_count}</td>
                                                        <td className="px-6 py-3 w-[50px]">
                                                            <DropdownMenu>
                                                                <DropdownMenuTrigger asChild>
                                                                    <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground" aria-label="Course actions">
                                                                        <MoreHorizontal className="h-4 w-4" />
                                                                    </Button>
                                                                </DropdownMenuTrigger>
                                                                <DropdownMenuContent align="end">
                                                                    <DropdownMenuLabel>Actions</DropdownMenuLabel>
                                                                    <DropdownMenuItem asChild>
                                                                        <Link to={`/courses/manage/${course.slug}`}>Manage Course</Link>
                                                                    </DropdownMenuItem>
                                                                </DropdownMenuContent>
                                                            </DropdownMenu>
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </div>

                </div>

                {/* Sidebar Actions */}
                <div className="space-y-6">
                    <Card className="border-border/60 shadow-sm">
                        <CardHeader className="pb-3">
                            <CardTitle className="text-lg">Quick Actions</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <QuickActionsCard actions={[
                                {
                                    to: "/events/create",
                                    icon: Calendar,
                                    label: "Create Event",
                                    description: "Schedule a webinar"
                                },
                                {
                                    to: "/courses/manage/new",
                                    icon: BookOpen,
                                    label: "Create Course",
                                    description: "Build a new course"
                                },
                                {
                                    to: "/organizer/contacts",
                                    icon: Users,
                                    label: "Audience",
                                    description: "Manage contacts"
                                }
                            ]} />
                        </CardContent>
                    </Card>

                    <ZoomIntegrationCard
                        zoomStatus={zoomStatus}
                        onConnect={handleConnectZoom}
                        onDisconnect={handleDisconnectZoom}
                    />
                </div>
            </div>
        </div>
    );
}
