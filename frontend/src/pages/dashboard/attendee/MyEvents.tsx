import React from "react";
import { Link } from "react-router-dom";
import { Calendar, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PageHeader } from "@/components/custom/PageHeader";
import { EventCard } from "@/components/custom/EventCard";
import { mockEvents } from "@/lib/mock-data";

export function MyEvents() {
  const [searchTerm, setSearchTerm] = React.useState("");

  const allRegistered = mockEvents.filter(e => e.isRegistered);
  const upcomingEvents = allRegistered.filter(e => e.status !== "completed" && e.status !== "cancelled");
  const pastEvents = allRegistered.filter(e => e.status === "completed");

  const filterEvents = (events: typeof mockEvents) => {
    return events.filter(e => e.title.toLowerCase().includes(searchTerm.toLowerCase()));
  };

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
            <TabsTrigger value="upcoming">Upcoming ({upcomingEvents.length})</TabsTrigger>
            <TabsTrigger value="past">Past ({pastEvents.length})</TabsTrigger>
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
          {filterEvents(upcomingEvents).length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filterEvents(upcomingEvents).map(event => (
                <EventCard key={event.id} event={event} showStatus />
              ))}
            </div>
          ) : (
            <EmptyState tab="upcoming" />
          )}
        </TabsContent>

        <TabsContent value="past" className="mt-0">
          {filterEvents(pastEvents).length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filterEvents(pastEvents).map(event => (
                <EventCard key={event.id} event={event} showStatus />
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
