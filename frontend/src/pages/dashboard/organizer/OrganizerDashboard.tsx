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
  Video,
  Settings
} from "lucide-react";
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
import { getZoomStatus, initiateZoomOAuth, disconnectZoom } from "@/api/integrations";
import { ZoomStatus } from "@/api/integrations/types";
import { toast } from "sonner";

export function OrganizerDashboard() {
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [zoomStatus, setZoomStatus] = useState<ZoomStatus | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const [eventsData, zoomData] = await Promise.all([
          getEvents(),
          getZoomStatus()
        ]);
        setEvents(eventsData);
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

  const stats = {
    totalEvents: events.length,
    activeEvents: events.filter(e => ['published', 'live'].includes(e.status)).length,
    totalRegistrations: events.reduce((acc, e) => acc + (e.registration_count || 0), 0),
    certificatesIssued: events.reduce((acc, e) => acc + (e.certificate_count || 0), 0),
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
        title="Organizer Dashboard"
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
                <div className="p-12 text-center bg-muted/30/50">
                  <div className="w-12 h-12 bg-card border border-border rounded-full flex items-center justify-center mx-auto mb-4 shadow-sm">
                    <Calendar className="h-6 w-6 text-slate-400" />
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
                    <thead className="bg-muted/30/80 border-b border-border text-muted-foreground font-medium">
                      <tr>
                        <th className="px-6 py-4">Event Name</th>
                        <th className="px-6 py-4">Date</th>
                        <th className="px-6 py-4">Status</th>
                        <th className="px-6 py-4 text-right">Registrations</th>
                        <th className="px-6 py-4 w-[50px]"></th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {recentEvents.map((event) => (
                        <tr key={event.uuid} className="group hover:bg-muted/30/50 transition-colors">
                          <td className="px-6 py-4 font-medium text-foreground">
                            <Link to={`/organizer/events/${event.uuid}/manage`} className="hover:text-primary transition-colors block truncate max-w-[200px] sm:max-w-xs">
                              {event.title}
                            </Link>
                          </td>
                          <td className="px-6 py-4 text-slate-600">
                            {new Date(event.starts_at).toLocaleDateString()}
                          </td>
                          <td className="px-6 py-4">
                            <Badge variant="outline" className={getStatusColor(event.status)}>
                              {event.status}
                            </Badge>
                          </td>
                          <td className="px-6 py-4 text-right font-medium text-slate-700">
                            {event.registration_count}
                          </td>
                          <td className="px-6 py-4 text-right">
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button variant="ghost" size="icon" className="h-8 w-8 text-slate-400 hover:text-slate-600">
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

          {/* Zoom Status */}
          <Card className={`border shadow-sm transition-all ${zoomStatus?.is_connected ? 'bg-card border-primary/20' : 'bg-card border-border'}`}>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center justify-between">
                <span>Zoom Integration</span>
                <span className={`relative flex h-2.5 w-2.5`}>
                  {zoomStatus?.is_connected && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary/50 opacity-75"></span>}
                  <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${zoomStatus?.is_connected ? 'bg-primary' : 'bg-muted-foreground'}`}></span>
                </span>
              </CardTitle>
              <CardDescription className={zoomStatus?.is_connected ? "text-primary/80" : "text-muted-foreground"}>
                {zoomStatus?.is_connected ? 'Automated meeting creation active' : 'Connect for auto-meetings'}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {zoomStatus?.is_connected ? (
                <>
                  <div className="flex items-center gap-3 mb-6 p-3 rounded-lg bg-secondary/50 border border-border">
                    <Video className="h-8 w-8 text-primary" />
                    <div className="overflow-hidden">
                      <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Connected Account</p>
                      <p className="text-sm font-semibold truncate hover:text-clip" title={zoomStatus.zoom_email}>{zoomStatus.zoom_email}</p>
                    </div>
                  </div>
                  <Button
                    size="sm"
                    variant="destructive"
                    className="w-full bg-destructive/10 hover:bg-destructive/20 text-destructive border border-destructive/20"
                    onClick={handleDisconnectZoom}
                  >
                    Disconnect Integration
                  </Button>
                </>
              ) : (
                <div className="text-center">
                  <div className="h-12 w-12 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-3">
                    <Video className="h-6 w-6 text-primary" />
                  </div>
                  <p className="text-sm text-muted-foreground mb-4">
                    Enable one-click Zoom meetings for your webinars and workshops.
                  </p>
                  <Button
                    size="sm"
                    className="w-full bg-primary hover:bg-primary/90"
                    onClick={handleConnectZoom}
                  >
                    Connect Zoom Account
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
