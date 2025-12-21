import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Calendar, Search, Loader2, Award, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { PageHeader } from "@/components/custom/PageHeader";
import { getMyRegistrations } from "@/api/registrations";
import { Registration } from "@/api/registrations/types";

export function MyEvents() {
  const [registrations, setRegistrations] = useState<Registration[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = React.useState("");

  useEffect(() => {
    async function fetchRegistrations() {
      try {
        const data = await getMyRegistrations();
        setRegistrations(data);
      } catch (error) {
        console.error("Failed to load registrations", error);
      } finally {
        setLoading(false);
      }
    }
    fetchRegistrations();
  }, []);

  // Filter by upcoming vs past based on event start date
  const now = new Date();
  const upcomingRegistrations = registrations.filter(r =>
    new Date(r.event.starts_at) >= now && r.status !== 'cancelled'
  );
  const pastRegistrations = registrations.filter(r =>
    new Date(r.event.starts_at) < now || r.status === 'cancelled'
  );

  const filterRegistrations = (regs: Registration[]) => {
    return regs.filter(r =>
      r.event.title.toLowerCase().includes(searchTerm.toLowerCase())
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="My Events"
        description="View your upcoming schedule and past event history."
        actions={
          <Link to="/events/browse">
            <Button>Browse New Events</Button>
          </Link>
        }
      />

      <Tabs defaultValue="upcoming" className="w-full">
        <div className="flex flex-col sm:flex-row justify-between items-center gap-4 mb-6">
          <TabsList>
            <TabsTrigger value="upcoming">Upcoming ({upcomingRegistrations.length})</TabsTrigger>
            <TabsTrigger value="past">Past ({pastRegistrations.length})</TabsTrigger>
          </TabsList>

          <div className="relative w-full sm:w-64">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-gray-400" />
            <Input
              placeholder="Search my events..."
              className="pl-9"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
        </div>

        <TabsContent value="upcoming" className="mt-0">
          {filterRegistrations(upcomingRegistrations).length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filterRegistrations(upcomingRegistrations).map(reg => (
                <RegistrationCard key={reg.uuid} registration={reg} />
              ))}
            </div>
          ) : (
            <EmptyState tab="upcoming" />
          )}
        </TabsContent>

        <TabsContent value="past" className="mt-0">
          {filterRegistrations(pastRegistrations).length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filterRegistrations(pastRegistrations).map(reg => (
                <RegistrationCard key={reg.uuid} registration={reg} isPast />
              ))}
            </div>
          ) : (
            <EmptyState tab="past" />
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}

function RegistrationCard({ registration, isPast = false }: { registration: Registration; isPast?: boolean }) {
  const event = registration.event;

  return (
    <Card className="overflow-hidden hover:shadow-md transition-shadow">
      <div className="h-32 bg-gradient-to-br from-blue-50 to-slate-100 relative flex items-center justify-center">
        <Calendar className="h-8 w-8 text-slate-300" />
        <div className="absolute top-3 right-3">
          <Badge variant={registration.status === 'confirmed' ? 'default' : 'secondary'} className="capitalize">
            {registration.status}
          </Badge>
        </div>
      </div>
      <CardContent className="p-4 space-y-3">
        <div>
          <h3 className="font-semibold text-gray-900 line-clamp-2">{event.title}</h3>
          <p className="text-sm text-gray-500 mt-1">
            {new Date(event.starts_at).toLocaleDateString(undefined, {
              weekday: 'short',
              month: 'short',
              day: 'numeric',
              year: 'numeric'
            })}
          </p>
        </div>

        {event.cpd_credit_value > 0 && (
          <div className="flex items-center gap-1 text-xs text-amber-600">
            <Award className="h-3 w-3" />
            <span>{event.cpd_credit_value} {event.cpd_credit_type || 'CPD'} Credits</span>
          </div>
        )}

        <div className="flex gap-2 pt-2">
          <Link to={`/events/${event.slug || event.uuid}`} className="flex-1">
            <Button variant="outline" size="sm" className="w-full">
              View Event
            </Button>
          </Link>
          {registration.can_join && registration.zoom_join_url && (
            <a href={registration.zoom_join_url} target="_blank" rel="noopener noreferrer">
              <Button size="sm" className="bg-blue-600 hover:bg-blue-700">
                <ExternalLink className="h-3 w-3 mr-1" /> Join
              </Button>
            </a>
          )}
          {isPast && registration.certificate_issued && registration.certificate_url && (
            <a href={registration.certificate_url} target="_blank" rel="noopener noreferrer">
              <Button size="sm" variant="outline">
                <Award className="h-3 w-3 mr-1" /> Certificate
              </Button>
            </a>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function EmptyState({ tab }: { tab: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 bg-gray-50 rounded-lg border border-dashed border-gray-200">
      <div className="h-12 w-12 bg-gray-100 rounded-full flex items-center justify-center mb-4 text-gray-400">
        <Calendar className="h-6 w-6" />
      </div>
      <h3 className="text-lg font-medium text-gray-900 mb-1">
        No {tab} events found
      </h3>
      <p className="text-gray-500 text-center max-w-sm mb-6">
        {tab === "upcoming"
          ? "You haven't registered for any upcoming events yet."
          : "You haven't attended any events yet."}
      </p>
      {tab === "upcoming" && (
        <Link to="/events/browse">
          <Button>Browse Events</Button>
        </Link>
      )}
    </div>
  );
}
