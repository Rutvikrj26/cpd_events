import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  Calendar,
  Clock,
  MapPin,
  User,
  Award,
  Share2,
  CheckCircle,
  AlertCircle,
  Video,
  Loader2
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { StatusBadge } from "@/components/custom/StatusBadge";
import { getPublicEvent } from "@/api/events";
import { Event } from "@/api/events/types";

export function EventDetail() {
  const { id } = useParams<{ id: string }>();
  const [event, setEvent] = useState<Event | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchEvent() {
      if (!id) return;
      try {
        const data = await getPublicEvent(id);
        setEvent(data);
      } catch (e: any) {
        console.error("Failed to fetch event", e);
        setError(e?.response?.data?.detail || "Event not found");
      } finally {
        setLoading(false);
      }
    }
    fetchEvent();
  }, [id]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (error || !event) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-foreground">Event Not Found</h2>
          <p className="text-muted-foreground mt-2">{error || "The event you're looking for doesn't exist."}</p>
          <Link to="/events/browse">
            <Button className="mt-4">Browse Events</Button>
          </Link>
        </div>
      </div>
    );
  }

  // Derive states from event data
  const isPast = new Date(event.starts_at) < new Date();
  const isRegistrationOpen = event.is_registration_open ?? event.registration_enabled;
  const organizerName = event.organizer?.display_name || event.organizer_name || event.owner?.display_name || "Unknown Organizer";

  // Calculate duration display
  const getDurationDisplay = () => {
    if (event.duration_minutes) {
      const hours = Math.floor(event.duration_minutes / 60);
      const mins = event.duration_minutes % 60;
      if (hours > 0 && mins > 0) return `${hours}h ${mins}m`;
      if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''}`;
      return `${mins} minutes`;
    }
    if (event.ends_at) {
      const start = new Date(event.starts_at);
      const end = new Date(event.ends_at);
      const diffMs = end.getTime() - start.getTime();
      const diffHours = Math.round(diffMs / (1000 * 60 * 60));
      return `${diffHours} hour${diffHours > 1 ? 's' : ''}`;
    }
    return "TBD";
  };

  return (
    <div className="bg-gray-50 min-h-screen pb-12">
      {/* Hero Header */}
      <div className="bg-card border-b border-border">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8 lg:py-12">
          <div className="flex flex-col lg:flex-row gap-8 items-start">
            <div className="flex-1 space-y-4">
              <div className="flex flex-wrap gap-2 items-center">
                <Badge variant="outline" className="text-blue-600 border-blue-200 bg-blue-50 capitalize">
                  {event.event_type}
                </Badge>
                {event.cpd_credits && Number(event.cpd_credits) > 0 && (
                  <Badge variant="outline" className="border-gray-300">
                    {event.cpd_type || 'CPD'} • {event.cpd_credits} Credits
                  </Badge>
                )}
              </div>

              <h1 className="text-3xl sm:text-4xl font-bold text-foreground tracking-tight">
                {event.title}
              </h1>

              <div className="flex flex-col sm:flex-row gap-4 sm:gap-8 text-muted-foreground pt-2">
                <div className="flex items-center gap-2">
                  <Calendar className="h-5 w-5 text-gray-400" />
                  <span className="text-sm font-medium">
                    {new Date(event.starts_at).toLocaleDateString(undefined, {
                      weekday: 'long',
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric'
                    })}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <Clock className="h-5 w-5 text-gray-400" />
                  <span className="text-sm font-medium">
                    {new Date(event.starts_at).toLocaleTimeString(undefined, {
                      hour: '2-digit',
                      minute: '2-digit'
                    })} ({getDurationDisplay()})
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <User className="h-5 w-5 text-gray-400" />
                  <span className="text-sm font-medium">
                    by <span className="text-foreground">{organizerName}</span>
                  </span>
                </div>
              </div>
            </div>

            <div className="flex gap-3">
              <Button variant="outline" size="icon">
                <Share2 className="h-4 w-4" />
              </Button>
              {isPast ? (
                <Button disabled>Event Ended</Button>
              ) : isRegistrationOpen ? (
                <Link to={`/events/${id}/register`}>
                  <Button size="lg" className="bg-blue-600 hover:bg-blue-700">
                    Register Now
                  </Button>
                </Link>
              ) : (
                <Button disabled>Registration Closed</Button>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-8">
            {/* Featured Image or Placeholder */}
            <div className="aspect-video w-full overflow-hidden rounded-xl border border-border shadow-sm bg-muted flex items-center justify-center">
              {event.featured_image_url || event.cover_image_url ? (
                <img
                  src={event.featured_image_url || event.cover_image_url}
                  alt={event.title}
                  className="h-full w-full object-cover"
                />
              ) : (
                <div className="text-gray-300">
                  <Calendar className="h-16 w-16" />
                </div>
              )}
            </div>

            <Tabs defaultValue="about" className="w-full">
              <TabsList className="w-full justify-start border-b border-border bg-transparent p-0 h-auto rounded-none space-x-8">
                <TabsTrigger
                  value="about"
                  className="rounded-none border-b-2 border-transparent px-0 py-3 data-[state=active]:border-blue-600 data-[state=active]:text-blue-600 data-[state=active]:bg-transparent shadow-none"
                >
                  About
                </TabsTrigger>
                <TabsTrigger
                  value="schedule"
                  className="rounded-none border-b-2 border-transparent px-0 py-3 data-[state=active]:border-blue-600 data-[state=active]:text-blue-600 data-[state=active]:bg-transparent shadow-none"
                >
                  Schedule
                </TabsTrigger>
              </TabsList>

              <TabsContent value="about" className="pt-6 space-y-6">
                <div>
                  <h3 className="text-xl font-semibold text-foreground mb-3">Event Description</h3>
                  <p className="text-gray-600 leading-relaxed whitespace-pre-line">
                    {event.description || event.short_description || "No description available."}
                  </p>
                </div>

                {event.cpd_credits && Number(event.cpd_credits) > 0 && (
                  <>
                    <Separator />
                    <div>
                      <h3 className="text-xl font-semibold text-foreground mb-4">CPD Credits</h3>
                      <div className="flex items-center gap-3 bg-amber-50 p-4 rounded-lg border border-amber-100">
                        <Award className="h-8 w-8 text-amber-600" />
                        <div>
                          <p className="font-medium text-foreground">{event.cpd_credits} {event.cpd_type || 'CPD'} Credits</p>
                          <p className="text-sm text-gray-600">Earn professional development credits upon completion</p>
                        </div>
                      </div>
                    </div>
                  </>
                )}
              </TabsContent>

              <TabsContent value="schedule" className="pt-6">
                <div className="text-center py-8 text-muted-foreground">
                  <Clock className="h-8 w-8 mx-auto mb-2 text-gray-300" />
                  <p>Detailed schedule will be available soon.</p>
                </div>
              </TabsContent>
            </Tabs>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            <Card className="shadow-md border-border">
              <CardHeader>
                <CardTitle>Registration</CardTitle>
                <CardDescription>Secure your spot today.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {(event.capacity || event.max_attendees) && (
                  <div className="flex justify-between items-center py-2 border-b border-gray-100">
                    <span className="text-gray-600">Capacity</span>
                    <span className="text-foreground">
                      {event.registration_count} / {event.capacity || event.max_attendees} registered
                    </span>
                  </div>
                )}

                {event.spots_remaining !== null && event.spots_remaining !== undefined && (
                  <div className="flex justify-between items-center py-2 border-b border-gray-100">
                    <span className="text-gray-600">Spots Remaining</span>
                    <span className="text-foreground font-semibold">
                      {event.spots_remaining}
                    </span>
                  </div>
                )}

                {isPast ? (
                  <div className="bg-gray-50 p-4 rounded-lg border border-gray-100 text-center">
                    <p className="font-medium text-gray-600">This event has ended</p>
                  </div>
                ) : isRegistrationOpen ? (
                  <Link to={`/events/${id}/register`}>
                    <Button className="w-full bg-blue-600 hover:bg-blue-700 text-lg py-6">
                      Register Now
                    </Button>
                  </Link>
                ) : (
                  <div className="bg-gray-50 p-4 rounded-lg border border-gray-100 text-center">
                    <p className="font-medium text-gray-600">Registration is closed</p>
                  </div>
                )}

                {event.registration_closes_at && !isPast && (
                  <p className="text-xs text-center text-muted-foreground">
                    Registration closes {new Date(event.registration_closes_at).toLocaleDateString()}
                  </p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Organizer</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded bg-blue-100 flex items-center justify-center text-blue-700 font-bold">
                    {organizerName.charAt(0)}
                  </div>
                  <div>
                    <div className="font-medium text-foreground">{organizerName}</div>
                    <div className="text-xs text-muted-foreground">Event Organizer</div>
                  </div>
                </div>
                <Button variant="outline" className="w-full text-xs h-8">Contact Organizer</Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Location</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-start gap-2 text-sm text-gray-600">
                  {event.format === 'online' ? (
                    <>
                      <Video className="h-4 w-4 shrink-0 mt-0.5" />
                      <div>
                        <p className="font-medium text-foreground">Online Event</p>
                        <p className="mt-1">Link provided upon registration</p>
                      </div>
                    </>
                  ) : event.format === 'hybrid' ? (
                    <>
                      <MapPin className="h-4 w-4 shrink-0 mt-0.5" />
                      <div>
                        <p className="font-medium text-foreground">Hybrid Event</p>
                        <p className="mt-1">In-person + Online options available</p>
                      </div>
                    </>
                  ) : (
                    <>
                      <MapPin className="h-4 w-4 shrink-0 mt-0.5" />
                      <div>
                        <p className="font-medium text-foreground">In-Person Event</p>
                        <p className="mt-1">Location details upon registration</p>
                      </div>
                    </>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
