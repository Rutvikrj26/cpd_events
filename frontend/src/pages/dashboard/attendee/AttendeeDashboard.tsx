import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Calendar, Award, Clock, Video, GraduationCap, ExternalLink, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { DashboardStat } from "@/components/dashboard/DashboardStats";
import { PageHeader } from "@/components/ui/page-header";
import { getMyRegistrations } from "@/api/registrations";
import { Registration } from "@/api/registrations/types";
import { useAuth } from "@/contexts/AuthContext";

export function AttendeeDashboard() {
  const { user } = useAuth();
  const [registrations, setRegistrations] = useState<Registration[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchRegistrations() {
      try {
        const data = await getMyRegistrations();
        setRegistrations(data);
      } catch (error) {
        console.error("Failed to fetch registrations", error);
      } finally {
        setLoading(false);
      }
    }
    fetchRegistrations();
  }, []);

  const stats = {
    totalCredits: registrations.reduce((acc, r) => acc + (r.event.cpd_credit_value || 0), 0),
    certificates: registrations.filter(r => r.certificate_issued_at).length,
    upcomingEvents: registrations.filter(r => new Date(r.event.starts_at) > new Date()).length,
    learningHours: registrations.reduce((acc, r) => acc + (r.event.cpd_credit_value || 0), 0),
  };

  const upcomingRegistrations = registrations
    .filter(r => new Date(r.event.starts_at) > new Date())
    .sort((a, b) => new Date(a.event.starts_at).getTime() - new Date(b.event.starts_at).getTime());

  const recentCertificates = registrations
    .filter(r => r.certificate_issued_at)
    .sort((a, b) => new Date(b.certificate_issued_at!).getTime() - new Date(a.certificate_issued_at!).getTime())
    .slice(0, 3);

  if (loading) {
    return <div className="p-8 flex items-center justify-center min-h-[50vh] text-muted-foreground animate-pulse">Loading dashboard...</div>;
  }

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">

      {/* Welcome Header */}
      <div className="relative overflow-hidden rounded-xl bg-gradient-to-r from-blue-600 to-indigo-700 p-8 text-white shadow-lg">
        <div className="relative z-10">
          <h1 className="text-3xl font-bold tracking-tight">Welcome back, {user?.first_name || 'Professional'}!</h1>
          <p className="mt-2 text-blue-100 max-w-xl">
            Track your professional development, manage upcoming events, and view your earned certificates.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Button asChild variant="secondary" className="font-semibold shadow-sm">
              <Link to="/events">Browse Events</Link>
            </Button>
            <Button asChild variant="outline" className="bg-transparent text-white border-white/30 hover:bg-card/10 hover:text-white hover:border-white/50">
              <Link to="/profile">View Profile</Link>
            </Button>
          </div>
        </div>
        {/* Decorative background element */}
        <div className="absolute top-0 right-0 -mt-10 -mr-10 h-64 w-64 rounded-full bg-card/10 blur-3xl"></div>
        <div className="absolute bottom-0 right-20 -mb-10 h-40 w-40 rounded-full bg-blue-400/20 blur-2xl"></div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <DashboardStat
          title="Total Credits"
          value={stats.totalCredits}
          icon={Award}
          description="CPD credits earned"
          className="border-indigo-100 bg-indigo-50/30"
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
          title="Learning Hours"
          value={stats.learningHours}
          icon={Clock}
          description="Total time invested"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main Column: Upcoming Events */}
        <div className="lg:col-span-2 space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold tracking-tight text-foreground">Your Upcoming Events</h2>
            {upcomingRegistrations.length > 0 && (
              <Button variant="link" asChild className="text-primary p-0 h-auto font-medium">
                <Link to="/my-registrations">View All</Link>
              </Button>
            )}
          </div>

          {upcomingRegistrations.length === 0 ? (
            <Card className="border-dashed border-2 bg-muted/30/50 shadow-none border-border">
              <CardContent className="flex flex-col items-center justify-center p-12 text-center">
                <div className="p-4 bg-card rounded-full shadow-sm mb-4">
                  <Calendar className="h-8 w-8 text-slate-400" />
                </div>
                <h3 className="text-lg font-medium text-foreground">No upcoming events</h3>
                <p className="text-muted-foreground mt-2 max-w-sm">
                  You haven't registered for any upcoming events yet. Explore our catalog to find your next learning opportunity.
                </p>
                <Button asChild className="mt-6">
                  <Link to="/events">Browse Events Catalog</Link>
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {upcomingRegistrations.map((reg) => (
                <div key={reg.uuid} className="group relative overflow-hidden rounded-xl border border-border/60 bg-card p-5 shadow-sm transition-all hover:shadow-md hover:border-blue-200">
                  <div className="flex flex-col sm:flex-row gap-5">
                    {/* Date Badge */}
                    <div className="flex flex-col items-center justify-center rounded-lg bg-blue-50 p-3 min-w-[80px] text-center border border-blue-100/50">
                      <span className="text-xs font-bold uppercase text-blue-600">
                        {new Date(reg.event.starts_at).toLocaleString('default', { month: 'short' })}
                      </span>
                      <span className="text-2xl font-bold text-blue-700">
                        {new Date(reg.event.starts_at).getDate()}
                      </span>
                      <span className="text-xs text-blue-600/80 mt-1 font-medium">
                        {new Date(reg.event.starts_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>

                    {/* Event Details */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between">
                        <div>
                          <h3 className="text-lg font-bold text-foreground group-hover:text-blue-700 transition-colors line-clamp-1">
                            <Link to={`/events/${reg.event.slug || reg.event.uuid}`}>
                              <span className="absolute inset-0" aria-hidden="true" />
                              {reg.event.title}
                            </Link>
                          </h3>
                          <div className="flex flex-wrap items-center gap-2 mt-2">
                            <Badge variant="secondary" className="text-xs font-medium">
                              {reg.event.event_type}
                            </Badge>
                            <span className="text-slate-300 text-xs">•</span>
                            <span className="text-xs font-medium text-muted-foreground flex items-center">
                              <Award className="h-3 w-3 mr-1 text-amber-500" />
                              {reg.event.cpd_credit_value} CPD Credits
                            </span>
                          </div>
                        </div>
                        <Button variant="ghost" size="icon" className="shrink-0 z-10 relative text-slate-400 hover:text-primary hover:bg-blue-50">
                          <ExternalLink className="h-4 w-4" />
                        </Button>
                      </div>

                      {/* Action Area */}
                      <div className="mt-4 flex items-center gap-3 relative z-10">
                        <Button size="sm" className="h-8 shadow-sm">
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

        {/* Side Column: Certificates & Upsell */}
        <div className="space-y-6">
          {/* Recent Certificates */}
          <Card className="border-border/60 shadow-sm">
            <CardHeader className="pb-3 border-b border-slate-50">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <Award className="h-4 w-4 text-amber-500" />
                Recent Certificates
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-4">
              {recentCertificates.length === 0 ? (
                <div className="text-center py-6 text-muted-foreground text-sm">
                  No certificates earned yet.
                </div>
              ) : (
                <ul className="space-y-4">
                  {recentCertificates.map(reg => (
                    <li key={reg.uuid} className="flex gap-3 items-start pb-3 border-b border-slate-50 last:border-0 last:pb-0">
                      <div className="mt-0.5 bg-amber-50 p-2 rounded-md text-amber-600 shrink-0 border border-amber-100">
                        <Award size={16} />
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-foreground line-clamp-1">{reg.event.title}</p>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          Issued {new Date(reg.certificate_issued_at!).toLocaleDateString()}
                        </p>
                        <Button variant="link" size="sm" className="h-auto p-0 text-xs mt-1 text-blue-600 font-medium">
                          Download PDF
                        </Button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
              <Button variant="ghost" className="w-full mt-4 text-xs h-8 text-muted-foreground hover:text-foreground" asChild>
                <Link to="/my-certificates">View All Certificates <ArrowRight className="h-3 w-3 ml-1" /></Link>
              </Button>
            </CardContent>
          </Card>

          {/* Organizer Upsell */}
          <Card className="bg-slate-900 text-white border-none overflow-hidden relative shadow-lg">
            <div className="absolute top-0 right-0 p-4 opacity-10">
              <Users size={100} />
            </div>
            <CardHeader className="relative z-10">
              <CardTitle className="text-lg">Host Your Own Events</CardTitle>
              <CardDescription className="text-slate-300">
                Ready to share your knowledge?
              </CardDescription>
            </CardHeader>
            <CardContent className="relative z-10">
              <p className="text-sm text-slate-300 mb-4 font-medium">
                Upgrade to an Organizer account to create events, issue certificates, and track attendance automatically.
              </p>
              <Button className="w-full bg-card text-foreground hover:bg-muted font-bold border-0" size="sm">
                Become an Organizer
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
