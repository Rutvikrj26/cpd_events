import React from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Calendar, Award, Clock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/custom/PageHeader";
import { EventCard } from "@/components/custom/EventCard";
import { mockEvents, mockCertificates, mockStats } from "@/lib/mock-data";

export function AttendeeDashboard() {
  const registeredEvents = mockEvents.filter(e => e.isRegistered && e.status !== "completed");
  const recentCertificates = mockCertificates.slice(0, 3);
  const stats = mockStats.attendee;

  return (
    <div className="space-y-8">
      {/* Welcome & Stats */}
      <div className="space-y-6">
        <PageHeader 
          title="Dashboard" 
          description="Welcome back, Jane. Here's what's happening with your professional development."
          actions={
            <Link to="/events/browse">
               <Button>Browse Events</Button>
            </Link>
          }
        />
        
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatsCard 
            title="Total Credits" 
            value={stats.totalCredits} 
            subtitle={`of ${stats.requiredCredits} required`}
            icon={Award}
            trend="+4 this month"
          />
          <StatsCard 
            title="Certificates" 
            value={stats.certificates} 
            subtitle="Earned all time"
            icon={Award}
          />
          <StatsCard 
            title="Upcoming Events" 
            value={stats.upcomingEvents} 
            subtitle="Registered"
            icon={Calendar}
          />
          <StatsCard 
            title="Learning Hours" 
            value="32.5" 
            subtitle="This year"
            icon={Clock}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main Column */}
        <div className="lg:col-span-2 space-y-8">
          {/* Upcoming Events */}
          <section>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Your Upcoming Events</h2>
              <Link to="/events" className="text-sm font-medium text-blue-600 hover:text-blue-500 flex items-center">
                View all <ArrowRight className="ml-1 h-4 w-4" />
              </Link>
            </div>
            
            {registeredEvents.length > 0 ? (
              <div className="space-y-4">
                {registeredEvents.map(event => (
                  <EventCard key={event.id} event={event} variant="horizontal" showStatus />
                ))}
              </div>
            ) : (
              <Card className="bg-gray-50 border-dashed">
                <CardContent className="flex flex-col items-center justify-center py-10 text-center">
                  <Calendar className="h-10 w-10 text-gray-400 mb-3" />
                  <h3 className="text-sm font-medium text-gray-900">No upcoming events</h3>
                  <p className="mt-1 text-sm text-gray-500 max-w-sm mb-4">
                    You haven't registered for any upcoming events yet.
                  </p>
                  <Link to="/events/browse">
                    <Button variant="outline">Browse Events</Button>
                  </Link>
                </CardContent>
              </Card>
            )}
          </section>

          {/* Recommended Events (could be added here) */}
        </div>

        {/* Side Column */}
        <div className="space-y-8">
          {/* Recent Certificates */}
          <section>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Recent Certificates</h2>
              <Link to="/certificates" className="text-sm font-medium text-blue-600 hover:text-blue-500">
                View all
              </Link>
            </div>
            
            <Card>
              <CardContent className="p-0">
                <div className="divide-y divide-gray-100">
                  {recentCertificates.map((cert) => (
                    <div key={cert.id} className="p-4 hover:bg-gray-50 transition-colors">
                      <div className="flex items-start gap-3">
                        <div className="flex-shrink-0 bg-blue-50 rounded-lg p-2 text-blue-600">
                          <Award className="h-5 w-5" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-900 truncate">
                            {cert.eventTitle}
                          </p>
                          <p className="text-xs text-gray-500 mt-0.5">
                            Issued {new Date(cert.issueDate).toLocaleDateString()}
                          </p>
                          <div className="mt-2 flex items-center gap-2">
                             <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800">
                               {cert.credits} {cert.creditType}
                             </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="p-3 border-t border-gray-100 bg-gray-50 rounded-b-lg">
                  <Button variant="ghost" size="sm" className="w-full text-xs text-gray-500 h-8">
                    Download All
                  </Button>
                </div>
              </CardContent>
            </Card>
          </section>

          {/* Quick Actions or Upsell */}
          <Card className="bg-gradient-to-br from-blue-600 to-indigo-700 text-white border-none">
            <CardHeader>
              <CardTitle className="text-lg">Upgrade to Organizer?</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-blue-100 text-sm mb-4">
                Host your own events, issue certificates, and track attendance automatically.
              </p>
              <Button size="sm" className="w-full bg-white text-blue-600 hover:bg-blue-50 border-0">
                Learn More
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

function StatsCard({ title, value, subtitle, icon: Icon, trend }: any) {
  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-500">{title}</p>
            <div className="mt-2 flex items-baseline">
              <span className="text-3xl font-bold text-gray-900">{value}</span>
            </div>
          </div>
          <div className="p-3 bg-blue-50 rounded-lg">
            <Icon className="h-6 w-6 text-blue-600" />
          </div>
        </div>
        {(subtitle || trend) && (
          <div className="mt-4 flex items-center justify-between text-sm">
             {subtitle && <span className="text-gray-500">{subtitle}</span>}
             {trend && <span className="text-green-600 font-medium">{trend}</span>}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
