import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Plus,
  Calendar,
  Users,
  Award,
  ArrowRight,
  MoreHorizontal,
  Activity
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
import { getEvents } from "@/api/events";
import { Event } from "@/api/events/types";
import { getZoomStatus, initiateZoomOAuth, disconnectZoom } from "@/api/integrations";
import { ZoomStatus } from "@/api/integrations/types";
import { toast } from "@/components/ui/use-toast";

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
      toast({
        title: "Connection Failed",
        description: "Could not initiate Zoom connection.",
        variant: "destructive",
      });
    }
  };

  const handleDisconnectZoom = async () => {
    try {
      await disconnectZoom();
      setZoomStatus({ is_connected: false });
      toast({
        title: "Disconnected",
        description: "Zoom account has been disconnected.",
      });
    } catch (error) {
      toast({
        title: "Disconnect Failed",
        description: "Could not disconnect Zoom account.",
        variant: "destructive",
      });
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
      case 'published': return 'bg-blue-100 text-blue-800 hover:bg-blue-100/80';
      case 'live': return 'bg-green-100 text-green-800 hover:bg-green-100/80';
      case 'draft': return 'bg-slate-100 text-slate-800 hover:bg-slate-100/80';
      case 'completed': return 'bg-purple-100 text-purple-800 hover:bg-purple-100/80';
      default: return 'bg-gray-100 text-gray-800 hover:bg-gray-100/80';
    }
  };

  if (loading) {
    return <div className="p-8 flex items-center justify-center min-h-[50vh] text-slate-500">Loading dashboard...</div>;
  }

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Header Section */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">Organizer Dashboard</h1>
          <p className="text-muted-foreground mt-1">Manage your events and track performance.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm">
            <Calendar className="mr-2 h-4 w-4" />
            Calendar
          </Button>
          <Button asChild size="sm" className="bg-primary hover:bg-primary/90">
            <Link to="/events/create">
              <Plus className="mr-2 h-4 w-4" />
              Create Event
            </Link>
          </Button>
        </div>
      </div>

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
          className="border-blue-100 bg-blue-50/30"
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
            <h2 className="text-xl font-semibold tracking-tight">Recent Events</h2>
            <Button variant="ghost" size="sm" asChild>
              <Link to="/events" className="text-primary hover:text-primary/80">
                View All <ArrowRight className="ml-1 h-4 w-4" />
              </Link>
            </Button>
          </div>

          <Card className="border-slate-200 shadow-sm">
            <CardContent className="p-0">
              {recentEvents.length === 0 ? (
                <div className="p-12 text-center">
                  <div className="w-12 h-12 bg-slate-50 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Calendar className="h-6 w-6 text-slate-400" />
                  </div>
                  <h3 className="text-lg font-medium text-slate-900">No events found</h3>
                  <p className="text-slate-500 mt-1 max-w-sm mx-auto">
                    Get started by creating your first event to engage with your audience.
                  </p>
                  <Button asChild className="mt-6" variant="outline">
                    <Link to="/events/create">Create Event</Link>
                  </Button>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-left">
                    <thead className="bg-slate-50 border-b border-slate-100 text-slate-500 font-medium">
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
                        <tr key={event.uuid} className="group hover:bg-slate-50 transition-colors">
                          <td className="px-6 py-4 font-medium text-slate-900">
                            <Link to={`/events/${event.uuid}`} className="hover:text-primary hover:underline block truncate max-w-[200px] sm:max-w-xs">
                              {event.title}
                            </Link>
                          </td>
                          <td className="px-6 py-4 text-slate-600">
                            {new Date(event.starts_at).toLocaleDateString()}
                          </td>
                          <td className="px-6 py-4">
                            <Badge variant="secondary" className={getStatusColor(event.status)}>
                              {event.status}
                            </Badge>
                          </td>
                          <td className="px-6 py-4 text-right font-medium text-slate-700">
                            {event.registration_count}
                          </td>
                          <td className="px-6 py-4 text-right">
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button variant="ghost" size="icon" className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity">
                                  <MoreHorizontal className="h-4 w-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                <DropdownMenuLabel>Actions</DropdownMenuLabel>
                                <DropdownMenuItem asChild>
                                  <Link to={`/events/${event.uuid}`}>View Details</Link>
                                </DropdownMenuItem>
                                <DropdownMenuItem asChild>
                                  <Link to={`/events/${event.uuid}/edit`}>Edit Event</Link>
                                </DropdownMenuItem>
                                <DropdownMenuSeparator />
                                <DropdownMenuItem className="text-red-600">Delete</DropdownMenuItem>
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
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Quick Actions</CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-1 gap-2">
              <Button variant="outline" className="justify-start h-auto py-3" asChild>
                <Link to="/events/create">
                  <Plus className="mr-2 h-4 w-4 text-primary" />
                  <span>Create New Event</span>
                </Link>
              </Button>
              <Button variant="outline" className="justify-start h-auto py-3">
                <Users className="mr-2 h-4 w-4 text-blue-500" />
                <span>View All Attendees</span>
              </Button>
              <Button variant="outline" className="justify-start h-auto py-3">
                <Award className="mr-2 h-4 w-4 text-amber-500" />
                <span>Manage Certificates</span>
              </Button>
            </CardContent>
          </Card>

          {/* Zoom Status */}
          <Card className="bg-slate-900 text-slate-50 border-slate-800">
            <CardHeader>
              <CardTitle className="text-lg flex items-center">
                <div className={`w-2 h-2 rounded-full mr-2 ${zoomStatus?.is_connected ? 'bg-green-500 animate-pulse' : 'bg-slate-500'}`}></div>
                Zoom Integration
              </CardTitle>
              <CardDescription className="text-slate-400">
                Status: {zoomStatus?.is_connected ? 'Connected' : 'Not Connected'}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {zoomStatus?.is_connected ? (
                <>
                  <p className="text-sm text-slate-300 mb-4">
                    Connected as <span className="font-medium text-white">{zoomStatus.zoom_email}</span>.
                    Meetings will be automatically created.
                  </p>
                  <Button
                    size="sm"
                    variant="destructive"
                    className="w-full bg-red-900/50 hover:bg-red-900/80 text-red-100"
                    onClick={handleDisconnectZoom}
                  >
                    Disconnect
                  </Button>
                </>
              ) : (
                <>
                  <p className="text-sm text-slate-300 mb-4">
                    Connect your Zoom account to automatically create meetings for your events.
                  </p>
                  <Button
                    size="sm"
                    variant="secondary"
                    className="w-full"
                    onClick={handleConnectZoom}
                  >
                    Connect Zoom
                  </Button>
                </>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
