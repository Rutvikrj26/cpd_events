import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Plus,
  Calendar,
  Users,
  Award,
  ArrowRight,
  MoreHorizontal,
  Activity,
  Building2,
  BookOpen,
  GraduationCap,
  CheckCircle2,
} from "lucide-react";
import { OnboardingChecklist } from "@/components/onboarding";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Badge } from "@/components/ui/badge";
import { DashboardStat } from "@/components/dashboard/DashboardStats";
import { PageHeader } from "@/components/ui/page-header";
import { getEvents } from "@/api/events";
import { Event } from "@/api/events/types";
import { getOwnedCourses } from "@/api/courses";
import { Course } from "@/api/courses/types";
import { useAuth } from "@/contexts/AuthContext";
import { getRoleFlags } from "@/lib/role-utils";
import { formatDate } from "@/lib/datetime";
import { toast } from "sonner";

export function OrganizerDashboard() {
  const { user } = useAuth();
  const { isAdmin, isInstructor } = getRoleFlags(user);
  const [events, setEvents] = useState<Event[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    async function fetchData() {
      try {
        // Instructors (and admins) also get course stats. Pure organizers skip the call.
        const [eventsData, coursesData] = await Promise.all([
          getEvents().catch((err) => {
            console.error("Failed to fetch events", err);
            return { results: [] } as any;
          }),
          isInstructor
            ? getOwnedCourses().catch((err) => {
                console.error("Failed to fetch courses", err);
                return [];
              })
            : Promise.resolve([] as Course[]),
        ]);
        setEvents(eventsData.results ?? []);
        setCourses(coursesData ?? []);
      } catch (error) {
        console.error("Failed to fetch dashboard data", error);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [isInstructor]);

  const stats = {
    totalEvents: events.length,
    activeEvents: events.filter(e => ['published', 'live'].includes(e.status)).length,
    totalRegistrations: events.reduce((acc, e) => acc + (e.registration_count || 0), 0),
    certificatesIssued: events.reduce((acc, e) => acc + (e.certificate_count || 0), 0),
    totalCourses: courses.length,
    publishedCourses: courses.filter(c => c.status === 'published').length,
    courseEnrollments: courses.reduce((acc, c) => acc + (c.enrollment_count || 0), 0),
    courseCompletions: courses.reduce((acc, c) => acc + (c.completion_count || 0), 0),
  };

  const recentEvents = [...events]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 5);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'published': return 'bg-primary/10 text-primary hover:bg-primary/20 border-primary/20';
      case 'live': return 'bg-destructive/10 text-destructive hover:bg-destructive/20 border-destructive/20 animate-pulse';
      case 'draft': return 'bg-muted text-muted-foreground hover:bg-muted/80 border-border';
      case 'completed': return 'bg-secondary text-secondary-foreground hover:bg-secondary/80 border-secondary-foreground/20';
      default: return 'bg-muted text-muted-foreground hover:bg-muted/80 border-border';
    }
  };

  if (loading) {
    return <div className="p-8 flex items-center justify-center min-h-[50vh] text-muted-foreground animate-pulse">Loading dashboard...</div>;
  }

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <PageHeader
        title={isAdmin ? 'Admin Dashboard' : 'Organizer Dashboard'}
        description="Manage your professional events, track attendance, and issue certificates."
        actions={
          <Button asChild size="lg" className="shadow-sm">
            <Link to="/events/create">
              <Plus className="mr-2 h-4 w-4" />
              Create New Event
            </Link>
          </Button>
        }
      />

      {/* Onboarding Checklist */}
      <OnboardingChecklist />

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <DashboardStat
          title="Total Events"
          value={stats.totalEvents}
          icon={Calendar}
          description="All time"
        />
        <DashboardStat
          title="Active Events"
          value={stats.activeEvents}
          icon={Activity}
          description="Currently live or published"
        />
        <DashboardStat
          title="Total Registrations"
          value={stats.totalRegistrations}
          icon={Users}
          description="Across all events"
        />
        <DashboardStat
          title="Certificates Issued"
          value={stats.certificatesIssued}
          icon={Award}
          description="Total certificates awarded"
        />
      </div>

      {/* Courses lens — shown to instructors (admins always count). Hidden for pure organizers. */}
      {isInstructor && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <DashboardStat
            title="Total Courses"
            value={stats.totalCourses}
            icon={BookOpen}
            description="All time"
          />
          <DashboardStat
            title="Published Courses"
            value={stats.publishedCourses}
            icon={CheckCircle2}
            description="Visible to learners"
          />
          <DashboardStat
            title="Course Enrollments"
            value={stats.courseEnrollments}
            icon={GraduationCap}
            description="Across all courses"
          />
          <DashboardStat
            title="Course Completions"
            value={stats.courseCompletions}
            icon={Award}
            description="Learners finished"
          />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Recent Events Table - Takes up 2/3 width */}
        <div className="lg:col-span-2 space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold tracking-tight text-foreground">Recent Activity</h2>
            <Button variant="ghost" size="sm" asChild className="text-primary">
              <Link to="/events">
                View All <ArrowRight className="ml-1 h-4 w-4" />
              </Link>
            </Button>
          </div>

          <Card className="border-border/60 shadow-sm overflow-hidden">
            <CardContent className="p-0">
              {recentEvents.length === 0 ? (
                <div className="p-12 text-center bg-muted/50">
                  <div className="w-12 h-12 bg-card border border-border rounded-full flex items-center justify-center mx-auto mb-4 shadow-sm">
                    <Calendar className="h-6 w-6 text-muted-foreground" />
                  </div>
                  <h3 className="text-lg font-medium text-foreground">No events found</h3>
                  <p className="text-muted-foreground mt-1 max-w-sm mx-auto mb-6">
                    Get started by creating your first event to engage with your audience.
                  </p>
                  <Button asChild variant="outline">
                    <Link to="/events/create">Create Event</Link>
                  </Button>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-left">
                    <thead className="bg-muted/80 border-b border-border text-muted-foreground font-medium">
                      <tr>
                        <th className="px-6 py-4">Event Name</th>
                        <th className="px-6 py-4">Date</th>
                        <th className="px-6 py-4">Status</th>
                        <th className="px-6 py-4 text-right">Registrations</th>
                        <th className="px-6 py-4 w-[50px]"></th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {recentEvents.map((event) => (
                        <tr key={event.uuid} className="group hover:bg-muted/50 transition-colors">
                          <td className="px-6 py-4 font-medium text-foreground">
                            <div className="flex flex-col gap-1">
                              <Link to={`/organizer/events/${event.uuid}/manage`} className="hover:text-primary transition-colors block truncate max-w-[200px] sm:max-w-xs">
                                {event.title}
                              </Link>
                              {event.organization_info && (
                                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                                  <Building2 className="h-3 w-3" />
                                  <span>{event.organization_info.name}</span>
                                </div>
                              )}
                            </div>
                          </td>
                          <td className="px-6 py-4 text-muted-foreground">
                            {formatDate(event.starts_at, user)}
                          </td>
                          <td className="px-6 py-4">
                            <Badge variant="outline" className={getStatusColor(event.status)}>
                              {event.status}
                            </Badge>
                          </td>
                          <td className="px-6 py-4 text-right font-medium text-foreground">
                            {event.registration_count}
                          </td>
                          <td className="px-6 py-4 text-right">
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground">
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

        {/* Sidebar Actions */}
        <div className="space-y-6">
          {/* Quick Actions */}
          <Card className="border-border/60 shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">Quick Actions</CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-1 gap-2">
              <Button variant="outline" className="justify-start h-auto py-3 px-4 border-border hover:bg-muted/30 hover:text-primary transition-all group" asChild>
                <Link to="/events/create">
                  <div className="bg-primary/10 p-2 rounded-md mr-3 group-hover:bg-primary/20 transition-colors">
                    <Plus className="h-4 w-4 text-primary" />
                  </div>
                  <div className="text-left">
                    <span className="font-semibold block text-foreground group-hover:text-primary">Create Event</span>
                    <span className="text-xs text-muted-foreground font-normal">Schedule a new webinar</span>
                  </div>
                </Link>
              </Button>
              {isInstructor && (
                <Button variant="outline" className="justify-start h-auto py-3 px-4 border-border hover:bg-muted/30 hover:text-primary transition-all group" asChild>
                  <Link to="/courses/manage/new">
                    <div className="bg-primary/10 p-2 rounded-md mr-3 group-hover:bg-primary/20 transition-colors">
                      <BookOpen className="h-4 w-4 text-primary" />
                    </div>
                    <div className="text-left">
                      <span className="font-semibold block text-foreground group-hover:text-primary">Create Course</span>
                      <span className="text-xs text-muted-foreground font-normal">Build a new learning path</span>
                    </div>
                  </Link>
                </Button>
              )}
              <Button variant="outline" className="justify-start h-auto py-3 px-4 border-border hover:bg-muted/30 hover:text-primary transition-all group" asChild>
                <Link to="/organizer/contacts">
                  <div className="bg-primary/10 p-2 rounded-md mr-3 group-hover:bg-primary/20 transition-colors">
                    <Users className="h-4 w-4 text-primary" />
                  </div>
                  <div className="text-left">
                    <span className="font-semibold block text-foreground group-hover:text-primary">Attendees</span>
                    <span className="text-xs text-muted-foreground font-normal">View registered users</span>
                  </div>
                </Link>
              </Button>
            </CardContent>
          </Card>

        </div>
      </div>
    </div>
  );
}
