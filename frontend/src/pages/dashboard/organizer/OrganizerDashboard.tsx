import React from "react";
import { Link } from "react-router-dom";
import { 
  Plus, 
  Calendar, 
  Users, 
  Award, 
  ArrowRight,
  MoreHorizontal
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/custom/PageHeader";
import { StatusBadge } from "@/components/custom/StatusBadge";
import { mockStats, mockEvents } from "@/lib/mock-data";

export function OrganizerDashboard() {
  const stats = mockStats.organizer;
  const recentEvents = mockEvents.slice(0, 3); // Just grabbing some events for the list

  return (
    <div className="space-y-8">
      <PageHeader 
        title="Organizer Dashboard" 
        description="Overview of your events and community activity."
        actions={
          <Link to="/organizer/events/new">
             <Button className="bg-blue-600 hover:bg-blue-700">
               <Plus className="mr-2 h-4 w-4" /> Create Event
             </Button>
          </Link>
        }
      />

      {/* Stats Overview */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatsCard 
          title="Total Events" 
          value={stats.totalEvents} 
          icon={Calendar}
        />
        <StatsCard 
          title="Active Events" 
          value={stats.activeEvents} 
          icon={Calendar}
          className="bg-blue-50 border-blue-100"
          valueClassName="text-blue-700"
        />
        <StatsCard 
          title="Total Attendees" 
          value={stats.totalAttendees} 
          icon={Users}
        />
        <StatsCard 
          title="Certificates Issued" 
          value={stats.certificatesIssued} 
          icon={Award}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main Column - Recent Events */}
        <div className="lg:col-span-2 space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">Recent Events</h2>
            <Link to="/organizer/events" className="text-sm font-medium text-blue-600 hover:text-blue-500 flex items-center">
              View All <ArrowRight className="ml-1 h-4 w-4" />
            </Link>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Event</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Registered</th>
                    <th className="px-6 py-3 relative"><span className="sr-only">Actions</span></th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {recentEvents.map((event) => (
                    <tr key={event.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">{event.title}</div>
                        <div className="text-xs text-gray-500">{event.type}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {new Date(event.startDate).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <StatusBadge status={event.status} />
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                        {event.attendees} / {event.capacity}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <Link to={`/organizer/events/${event.id}`} className="text-blue-600 hover:text-blue-900">
                           Manage
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Side Column - Activity / Tasks */}
        <div className="space-y-6">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base font-semibold">Action Items</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-4">
                <li className="flex gap-3">
                  <div className="flex-shrink-0 h-8 w-8 rounded-full bg-yellow-100 flex items-center justify-center">
                    <Users className="h-4 w-4 text-yellow-600" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-900">Review Attendance</p>
                    <p className="text-xs text-gray-500">Advanced Cardiology Symposium</p>
                    <Button variant="link" className="p-0 h-auto text-xs text-blue-600 mt-1">Review Now</Button>
                  </div>
                </li>
                <li className="flex gap-3">
                  <div className="flex-shrink-0 h-8 w-8 rounded-full bg-green-100 flex items-center justify-center">
                    <Award className="h-4 w-4 text-green-600" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-900">Issue Certificates</p>
                    <p className="text-xs text-gray-500">15 eligible attendees pending</p>
                    <Button variant="link" className="p-0 h-auto text-xs text-blue-600 mt-1">Issue All</Button>
                  </div>
                </li>
              </ul>
            </CardContent>
          </Card>

          <Card className="bg-gray-900 text-white border-none">
            <CardHeader>
              <CardTitle className="text-base">Zoom Integration</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between mb-4">
                 <div className="flex items-center gap-2 text-sm text-gray-300">
                    <div className="h-2 w-2 rounded-full bg-green-400"></div>
                    Connected
                 </div>
                 <Button variant="ghost" size="sm" className="h-6 text-xs text-gray-400 hover:text-white">Settings</Button>
              </div>
              <p className="text-xs text-gray-400">
                 Meetings will be automatically created for new events.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

function StatsCard({ title, value, icon: Icon, className, valueClassName }: any) {
  return (
    <Card className={className}>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-500">{title}</p>
            <div className="mt-2 flex items-baseline">
              <span className={`text-3xl font-bold text-gray-900 ${valueClassName}`}>{value}</span>
            </div>
          </div>
          <div className="p-3 bg-gray-50 rounded-lg">
            <Icon className="h-6 w-6 text-gray-600" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
