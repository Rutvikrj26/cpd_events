import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Calendar, Award, Clock, Video, GraduationCap, ExternalLink, Users, BookOpen, PlayCircle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { DashboardStat } from "@/components/dashboard/DashboardStats";
import { PageHeader } from "@/components/ui/page-header";
import { DashboardSkeleton } from "@/components/ui/page-skeleton";
import { getMyRegistrations } from "@/api/registrations";
import { getEnrollments } from "@/api/courses";
import { Registration } from "@/api/registrations/types";
import { useAuth } from "@/contexts/AuthContext";

export function AttendeeDashboard() {
  const { user } = useAuth();
  const [registrations, setRegistrations] = useState<Registration[]>([]);
  const [enrollments, setEnrollments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const [registrationsData, enrollmentsData] = await Promise.all([
          getMyRegistrations(),
          getEnrollments().catch(() => [])
        ]);
        setRegistrations(registrationsData.results);
        setEnrollments(enrollmentsData);
      } catch (error) {
        console.error("Failed to fetch dashboard data", error);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  const stats = {
    totalCredits: registrations.reduce((acc, r) => acc + Number(r.event.cpd_credit_value || 0), 0) +
      enrollments.reduce((acc, e) => acc + (e.course?.cpd_credit_value || 0), 0),
    certificates: registrations.filter(r => r.certificate_issued).length +
      enrollments.filter(e => e.certificate_issued).length,
    upcomingEvents: registrations.filter(r => new Date(r.event.starts_at) > new Date()).length,
    activeCourses: enrollments.filter(e => e.status !== 'completed').length,
  };

  const upcomingRegistrations = registrations
    .filter(r => new Date(r.event.starts_at) > new Date())
    .sort((a, b) => new Date(a.event.starts_at).getTime() - new Date(b.event.starts_at).getTime());

  const recentCertificates = registrations
    .filter(r => r.certificate_issued)
    .sort((a, b) => new Date(b.certificate_issued_at || 0).getTime() - new Date(a.certificate_issued_at || 0).getTime())
    .slice(0, 3);

  if (loading) {
    return <DashboardSkeleton />;
  }

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">

      {/* Welcome Header */}
      <div className="relative overflow-hidden rounded-xl bg-gradient-to-r from-primary to-primary/80 p-8 text-white shadow-lg">
        <div className="relative z-10">
          <h1 className="text-3xl font-bold tracking-tight">Welcome back, {user?.full_name?.split(' ')[0] || 'Professional'}!</h1>
          <p className="mt-2 text-primary-foreground/90 max-w-xl">
            Track your professional development, manage upcoming events, and view your earned certificates.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Button asChild variant="secondary" className="font-semibold shadow-sm">
              <Link to="/my-events">My Events</Link>
            </Button>
            <Button asChild variant="outline" className="bg-transparent text-white border-white/30 hover:bg-card/10 hover:text-white hover:border-white/50">
              <Link to="/settings">View Profile</Link>
            </Button>
          </div>
        </div>
        {/* Decorative background element */}
        <div className="absolute top-0 right-0 -mt-10 -mr-10 h-64 w-64 rounded-full bg-card/10 blur-3xl"></div>
        <div className="absolute bottom-0 right-20 -mb-10 h-40 w-40 rounded-full bg-primary/20 blur-2xl"></div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <DashboardStat
          title="Total Credits"
          value={stats.totalCredits}
          icon={Award}
          description="CPD credits earned"
          className="border-primary/10 bg-primary/5"
        />
        <DashboardStat
          title="Certificates"
          value={stats.certificates}
          icon={GraduationCap}
          description="Earned & Ready"
        />
        <DashboardStat
          title="Upcoming Events"
          value={stats.upcomingEvents}
          icon={Calendar}
          description="Registered events"
        />
        <DashboardStat
          title="Active Courses"
          value={stats.activeCourses}
          icon={BookOpen}
          description="In progress"
        />
      </div>

      <div className="space-y-8">
        {/* Main Column: Active Courses & Upcoming Events */}
        <div className="space-y-8">

          {/* Active Courses Section */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold tracking-tight text-foreground flex items-center gap-2">
                <BookOpen className="h-5 w-5 text-primary" />
                Pick Up Where You Left Off
              </h2>
              {enrollments.length > 0 && (
                <Button variant="ghost" size="sm" asChild className="text-primary">
                  <Link to="/my-courses">View All <ArrowRight className="ml-1 h-4 w-4" /></Link>
                </Button>
              )}
            </div>

            {enrollments.filter(e => e.status !== 'completed').length === 0 ? (
              <Card className="border-dashed border-2 bg-muted/30 shadow-none border-border">
                <CardContent className="flex flex-col items-center justify-center p-8 text-center">
                  <div className="p-3 bg-muted rounded-full mb-3">
                    <BookOpen className="h-6 w-6 text-muted-foreground" />
                  </div>
                  <p className="text-muted-foreground max-w-sm text-sm">
                    You don't have any active courses.
                  </p>
                </CardContent>
              </Card>
            ) : (
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {enrollments.filter(e => e.status !== 'completed').slice(0, 3).map(enrollment => (
                  <div key={enrollment.uuid} className="group relative overflow-hidden rounded-xl border border-border bg-card p-4 shadow-sm transition-all hover:shadow-md hover:border-primary/20">
                    <div className="flex flex-col gap-4">
                      <div className="flex items-start gap-4">
                        <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                          <BookOpen className="h-5 w-5 text-primary" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <h3 className="text-sm font-semibold truncate pr-2">
                            <Link to={`/courses/${enrollment.course?.slug}/learn`} className="hover:underline">
                              {enrollment.course?.title}
                            </Link>
                          </h3>
                          <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                            <span className="flex items-center gap-1">
                              <Clock className="h-3 w-3" />
                              {enrollment.progress_percent}%
                            </span>
                          </div>
                        </div>
                      </div>
                      <div className="space-y-2">
                        <div className="h-1.5 w-full bg-secondary rounded-full overflow-hidden">
                          <div
                            className="h-full bg-primary rounded-full transition-all duration-500"
                            style={{ width: `${enrollment.progress_percent}%` }}
                          />
                        </div>
                        <Button size="sm" className="w-full h-8 text-xs" asChild>
                          <Link to={`/courses/${enrollment.course?.slug}/learn`}>
                            <PlayCircle className="mr-2 h-3 w-3" />
                            Resume
                          </Link>
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold tracking-tight text-foreground">Your Upcoming Events</h2>
              {upcomingRegistrations.length > 0 && (
                <Button variant="link" asChild className="text-primary p-0 h-auto font-medium">
                  <Link to="/registrations">View All</Link>
                </Button>
              )}
            </div>
          </div>

          {upcomingRegistrations.length === 0 ? (
            <Card className="border-dashed border-2 bg-muted/50 shadow-none border-border">
              <CardContent className="flex flex-col items-center justify-center p-12 text-center">
                <div className="p-4 bg-card rounded-full shadow-sm mb-4">
                  <Calendar className="h-8 w-8 text-muted-foreground" />
                </div>
                <h3 className="text-lg font-medium text-foreground">No upcoming events</h3>
                <p className="text-muted-foreground mt-2 max-w-sm">
                  You haven't registered for any upcoming events yet.
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {upcomingRegistrations.map((reg) => (
                <div key={reg.uuid} className="group relative overflow-hidden rounded-xl border border-border/60 bg-card p-5 shadow-sm transition-all hover:shadow-md hover:border-primary/20">
                  <div className="flex flex-col sm:flex-row gap-5">
                    {/* Date Badge */}
                    <div className="flex flex-col items-center justify-center rounded-lg bg-primary/10 p-3 min-w-[80px] text-center border border-primary/20">
                      <span className="text-xs font-bold uppercase text-primary">
                        {new Date(reg.event.starts_at).toLocaleString('default', { month: 'short' })}
                      </span>
                      <span className="text-2xl font-bold text-primary">
                        {new Date(reg.event.starts_at).getDate()}
                      </span>
                      <span className="text-xs text-primary/80 mt-1 font-medium">
                        {new Date(reg.event.starts_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>

                    {/* Event Details */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between">
                        <div>
                          <h3 className="text-lg font-bold text-foreground group-hover:text-primary transition-colors line-clamp-1">
                            <Link to={`/events/${reg.event.slug || reg.event.uuid}`}>
                              <span className="absolute inset-0" aria-hidden="true" />
                              {reg.event.title}
                            </Link>
                          </h3>
                          <div className="flex flex-wrap items-center gap-2 mt-2">
                            <Badge variant="secondary" className="text-xs font-medium">
                              {reg.event.event_type}
                            </Badge>
                            <span className="text-muted-foreground/60 text-xs">•</span>
                            <span className="text-xs font-medium text-muted-foreground flex items-center">
                              <Award className="h-3 w-3 mr-1 text-amber-500" />
                              {reg.event.cpd_credit_value} CPD Credits
                            </span>
                          </div>
                        </div>
                        <Button variant="ghost" size="icon" className="shrink-0 z-10 relative text-muted-foreground hover:text-primary hover:bg-primary/10">
                          <ExternalLink className="h-4 w-4" />
                        </Button>
                      </div>

                      {/* Action Area */}
                      <div className="mt-4 flex items-center gap-3 relative z-10">
                        <Button
                          size="sm"
                          className="h-8 shadow-sm"
                          disabled={!reg.can_join || !reg.zoom_join_url}
                          onClick={() => reg.zoom_join_url && window.open(reg.zoom_join_url, '_blank')}
                        >
                          Join Session
                        </Button>
                        <Button variant="outline" size="sm" className="h-8" asChild>
                          <Link to={`/events/${reg.event.slug || reg.event.uuid}`}>View Details</Link>
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

    </div>
  );
}
