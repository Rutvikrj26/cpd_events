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
  Loader2,
  Building2,
  Globe,
  Mail,
  ArrowRight
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { StatusBadge } from "@/components/custom/StatusBadge";
import { getPublicEvent, getPublicEvents } from "@/api/events";
import { getMyRegistrations } from "@/api/registrations";
import { Event } from "@/api/events/types";
import { Registration } from "@/api/registrations/types";
import { useAuth } from "@/contexts/AuthContext";

export function EventDetail() {
  const { id } = useParams<{ id: string }>();
  const { isAuthenticated, user } = useAuth();
  const [event, setEvent] = useState<Event | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [userRegistration, setUserRegistration] = useState<Registration | null>(null);
  const [checkingRegistration, setCheckingRegistration] = useState(false);
  const [relatedEvents, setRelatedEvents] = useState<Event[]>([]);
  const [loadingRelated, setLoadingRelated] = useState(false);

  // Derived state
  const isAlreadyRegistered = userRegistration !== null;

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

  // Check if authenticated user is already registered
  useEffect(() => {
    async function checkRegistration() {
      if (!isAuthenticated || !event) return;

      setCheckingRegistration(true);
      try {
        const registrations = await getMyRegistrations();
        const myReg = registrations.find(
          reg => reg.event.uuid === event.uuid && reg.status !== 'cancelled'
        );
        setUserRegistration(myReg || null);
      } catch (e) {
        console.error("Failed to check registration status", e);
      } finally {
        setCheckingRegistration(false);
      }
    }
    checkRegistration();
  }, [isAuthenticated, event]);

  // Fetch related events from same organization
  useEffect(() => {
    async function fetchRelatedEvents() {
      if (!event?.organization_info?.slug) return;

      setLoadingRelated(true);
      try {
        const allEvents = await getPublicEvents();
        // Filter for same organization, exclude current event
        const orgEvents = allEvents
          .filter(e =>
            e.organization_info?.slug === event.organization_info?.slug &&
            e.uuid !== event.uuid
          )
          .slice(0, 3); // Show up to 3 related events
        setRelatedEvents(orgEvents);
      } catch (e) {
        console.error("Failed to fetch related events", e);
      } finally {
        setLoadingRelated(false);
      }
    }
    fetchRelatedEvents();
  }, [event]);

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

  // Check if current user is the organizer (check both nested objects as per API variant)
  const isOrganizer = isAuthenticated && (user?.uuid === event.owner?.uuid || user?.uuid === event.organizer?.uuid);

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

  // Render the registration button based on state
  const renderRegistrationButton = (isLarge = false) => {
    if (isOrganizer) {
      return (
        <Link to={`/organizer/events/${event.uuid}/manage`}>
          <Button
            size={isLarge ? "lg" : "default"}
            className={`${isLarge ? 'w-full py-6 text-lg' : ''} bg-slate-800 hover:bg-slate-900`}
          >
            Manage Event
          </Button>
        </Link>
      );
    }

    if (isPast) {
      return <Button disabled>Event Ended</Button>;
    }

    if (isAlreadyRegistered) {
      return (
        <Link to="/registrations">
          <Button
            size={isLarge ? "lg" : "default"}
            variant="outline"
            className={`${isLarge ? 'w-full py-6 text-lg' : ''} border-green-200 bg-green-50 text-green-700 hover:bg-green-100`}
          >
            <CheckCircle className="mr-2 h-4 w-4" />
            Already Registered
          </Button>
        </Link>
      );
    }

    if (isRegistrationOpen) {
      return (
        <Link to={`/events/${id}/register`}>
          <Button
            size={isLarge ? "lg" : "default"}
            className={`${isLarge ? 'w-full py-6 text-lg' : ''} bg-blue-600 hover:bg-blue-700`}
          >
            Register Now
          </Button>
        </Link>
      );
    }

    return <Button disabled>Registration Closed</Button>;
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
                {isAlreadyRegistered && (
                  <Badge variant="outline" className="border-green-200 bg-green-50 text-green-700">
                    <CheckCircle className="mr-1 h-3 w-3" />
                    Registered
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
              <Button
                variant="outline"
                size="icon"
                onClick={async () => {
                  const shareUrl = window.location.href;
                  const shareData = {
                    title: event.title,
                    text: `Check out this event: ${event.title}`,
                    url: shareUrl,
                  };

                  try {
                    if (navigator.share) {
                      await navigator.share(shareData);
                    } else {
                      await navigator.clipboard.writeText(shareUrl);
                      alert('Link copied to clipboard!');
                    }
                  } catch (err) {
                    // User cancelled or error
                    console.log('Share cancelled or failed:', err);
                  }
                }}
              >
                <Share2 className="h-4 w-4" />
              </Button>
              {renderRegistrationButton()}
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
              {event.featured_image_url ? (
                <img
                  src={event.featured_image_url}
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
                <div className="space-y-6">
                  <h3 className="text-xl font-semibold text-foreground">Event Schedule</h3>

                  {/* Event Date & Time Overview */}
                  <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950/30 dark:to-indigo-950/30 p-6 rounded-xl border border-blue-100 dark:border-blue-900">
                    <div className="flex flex-col md:flex-row md:items-center gap-6">
                      {/* Date Block */}
                      <div className="flex items-center gap-4">
                        <div className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm text-center min-w-[80px]">
                          <div className="text-3xl font-bold text-blue-600">
                            {new Date(event.starts_at).getDate()}
                          </div>
                          <div className="text-sm text-muted-foreground uppercase">
                            {new Date(event.starts_at).toLocaleDateString(undefined, { month: 'short' })}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {new Date(event.starts_at).getFullYear()}
                          </div>
                        </div>
                        <div>
                          <div className="text-lg font-semibold text-foreground">
                            {new Date(event.starts_at).toLocaleDateString(undefined, { weekday: 'long' })}
                          </div>
                          <div className="flex items-center gap-2 text-muted-foreground mt-1">
                            <Clock className="h-4 w-4" />
                            <span>
                              {new Date(event.starts_at).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })}
                              {' - '}
                              {new Date(event.ends_at).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })}
                            </span>
                          </div>
                          {event.timezone && (
                            <div className="text-sm text-muted-foreground mt-1">
                              {event.timezone}
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Duration & Format */}
                      <div className="md:ml-auto flex flex-wrap gap-4">
                        {event.duration_minutes && (
                          <div className="bg-white dark:bg-gray-800 px-4 py-2 rounded-lg shadow-sm">
                            <div className="text-xs text-muted-foreground uppercase">Duration</div>
                            <div className="font-semibold text-foreground">
                              {event.duration_minutes >= 60
                                ? `${Math.floor(event.duration_minutes / 60)}h ${event.duration_minutes % 60 > 0 ? `${event.duration_minutes % 60}m` : ''}`
                                : `${event.duration_minutes}m`}
                            </div>
                          </div>
                        )}
                        <div className="bg-white dark:bg-gray-800 px-4 py-2 rounded-lg shadow-sm">
                          <div className="text-xs text-muted-foreground uppercase">Format</div>
                          <div className="font-semibold text-foreground capitalize flex items-center gap-1">
                            {event.format === 'online' && <Video className="h-4 w-4 text-blue-600" />}
                            {event.format === 'in-person' && <MapPin className="h-4 w-4 text-green-600" />}
                            {event.format === 'hybrid' && <><Video className="h-4 w-4 text-blue-600" /><span>+</span><MapPin className="h-4 w-4 text-green-600" /></>}
                            {event.format}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Location if available */}
                    {event.location && (
                      <div className="mt-4 pt-4 border-t border-blue-100 dark:border-blue-900">
                        <div className="flex items-start gap-2 text-muted-foreground">
                          <MapPin className="h-4 w-4 mt-0.5 text-green-600" />
                          <span>{event.location}</span>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Sessions (if multi-session event) */}
                  {event.is_multi_session && event.sessions && event.sessions.length > 0 && (
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <h4 className="text-lg font-medium text-foreground">Agenda</h4>
                        <Badge variant="outline">{event.sessions.length} session{event.sessions.length > 1 ? 's' : ''}</Badge>
                      </div>

                      <div className="space-y-3">
                        {event.sessions.map((session, index) => {
                          const startTime = new Date(session.starts_at);
                          const endTime = session.ends_at ? new Date(session.ends_at) : new Date(startTime.getTime() + (session.duration_minutes * 60000));
                          const timeFormat: Intl.DateTimeFormatOptions = { hour: 'numeric', minute: '2-digit' };

                          return (
                            <div key={session.uuid || index} className="bg-card rounded-xl border border-border overflow-hidden hover:shadow-md transition-shadow">
                              <div className="flex">
                                {/* Time sidebar */}
                                <div className="w-24 shrink-0 bg-muted/50 p-4 flex flex-col items-center justify-center text-center border-r border-border">
                                  <div className="text-lg font-bold text-foreground">
                                    {startTime.toLocaleTimeString(undefined, timeFormat)}
                                  </div>
                                  <div className="text-xs text-muted-foreground">
                                    {session.duration_minutes >= 60
                                      ? `${Math.floor(session.duration_minutes / 60)}h${session.duration_minutes % 60 > 0 ? ` ${session.duration_minutes % 60}m` : ''}`
                                      : `${session.duration_minutes}m`}
                                  </div>
                                </div>

                                {/* Main content */}
                                <div className="flex-1 p-4">
                                  <div className="flex items-start justify-between gap-3">
                                    <div className="flex-1 min-w-0">
                                      <h5 className="font-semibold text-foreground">{session.title}</h5>
                                      {session.speaker_names && (
                                        <p className="text-sm text-blue-600 mt-1">{session.speaker_names}</p>
                                      )}
                                      {session.description && (
                                        <p className="text-sm text-muted-foreground mt-2 line-clamp-2">{session.description}</p>
                                      )}
                                    </div>
                                    {session.is_mandatory && (
                                      <Badge className="shrink-0 bg-amber-100 text-amber-700 hover:bg-amber-100">Required</Badge>
                                    )}
                                  </div>
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Hide single session block for multi-session events */}
                  {!event.is_multi_session && (
                    <div className="text-center py-6 text-muted-foreground">
                      <p className="text-sm">This is a single-session event. See event times above.</p>
                    </div>
                  )}
                </div>
              </TabsContent>
            </Tabs>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            <Card className="shadow-md border-border">
              <CardHeader>
                <CardTitle>{isOrganizer ? "Event Management" : "Registration"}</CardTitle>
                <CardDescription>
                  {isOrganizer
                    ? "Manage your event details and registrations."
                    : isAlreadyRegistered
                      ? "You're registered for this event!"
                      : "Secure your spot today."}
                </CardDescription>
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

                {renderRegistrationButton(true)}

                {event.registration_closes_at && !isPast && !isAlreadyRegistered && (
                  <p className="text-xs text-center text-muted-foreground">
                    Registration closes {new Date(event.registration_closes_at).toLocaleDateString()}
                  </p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">
                  {event.organization_info ? 'Organized By' : 'Organizer'}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {event.organization_info ? (
                  <>
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded bg-primary/10 flex items-center justify-center text-primary font-bold">
                        {event.organization_info.logo_url ? (
                          <img
                            src={event.organization_info.logo_url}
                            alt={event.organization_info.name}
                            className="h-full w-full object-cover rounded"
                          />
                        ) : (
                          <Building2 className="h-5 w-5" />
                        )}
                      </div>
                      <div className="flex-1">
                        <div className="font-medium text-foreground">{event.organization_info.name}</div>
                        <div className="text-xs text-muted-foreground">Organization</div>
                      </div>
                    </div>
                    <div className="space-y-2">
                      <Link to={`/organizations/${event.organization_info.slug}/public`}>
                        <Button variant="outline" className="w-full text-xs h-8">
                          <Building2 className="h-3 w-3 mr-1" />
                          View Profile
                        </Button>
                      </Link>
                    </div>
                  </>
                ) : (
                  <>
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
                  </>
                )}
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
                      <div className="flex-1">
                        <p className="font-medium text-foreground">Online Event</p>
                        {isAlreadyRegistered && userRegistration?.zoom_join_url ? (
                          <div className="mt-2 space-y-2">
                            <a
                              href={userRegistration.zoom_join_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
                            >
                              <Video className="h-4 w-4" />
                              Join Meeting
                            </a>
                            <p className="text-xs text-muted-foreground">
                              You'll also receive meeting details and reminders via email from Zoom
                            </p>
                          </div>
                        ) : isAlreadyRegistered ? (
                          <div className="mt-1 space-y-1">
                            <p className="text-green-600">Meeting link will be available closer to the event date</p>
                            <p className="text-xs text-muted-foreground">Check your email for the Zoom meeting invitation</p>
                          </div>
                        ) : (
                          <p className="mt-1">Link provided upon registration</p>
                        )}
                      </div>
                    </>
                  ) : event.format === 'hybrid' ? (
                    <>
                      <MapPin className="h-4 w-4 shrink-0 mt-0.5" />
                      <div className="flex-1">
                        <p className="font-medium text-foreground">Hybrid Event</p>
                        {isAlreadyRegistered && userRegistration?.zoom_join_url ? (
                          <div className="mt-2 space-y-2">
                            <a
                              href={userRegistration.zoom_join_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
                            >
                              <Video className="h-4 w-4" />
                              Join Online
                            </a>
                            <p className="text-xs text-muted-foreground">
                              You'll also receive meeting details and reminders via email from Zoom
                            </p>
                          </div>
                        ) : isAlreadyRegistered ? (
                          <div className="mt-1 space-y-1">
                            <p className="text-green-600">Details will be available closer to the event date</p>
                            <p className="text-xs text-muted-foreground">Check your email for the Zoom meeting invitation</p>
                          </div>
                        ) : (
                          <p className="mt-1">In-person + Online options available</p>
                        )}
                      </div>
                    </>
                  ) : (
                    <>
                      <MapPin className="h-4 w-4 shrink-0 mt-0.5" />
                      <div>
                        <p className="font-medium text-foreground">In-Person Event</p>
                        {isAlreadyRegistered ? (
                          <p className="mt-1 text-green-600">Location details sent to your email</p>
                        ) : (
                          <p className="mt-1">Location details upon registration</p>
                        )}
                      </div>
                    </>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* More from Organization */}
        {event.organization_info && relatedEvents.length > 0 && (
          <div className="mt-16">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-2xl font-bold text-foreground">
                  More from {event.organization_info.name}
                </h2>
                <p className="text-muted-foreground mt-1">
                  Explore other events from this organization
                </p>
              </div>
              <Link to={`/organizations/${event.organization_info.slug}/public`}>
                <Button variant="outline">
                  View All
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {relatedEvents.map((relatedEvent) => (
                <Card key={relatedEvent.uuid} className="group hover:shadow-lg transition-shadow">
                  <CardContent className="p-0">
                    <div className="aspect-video bg-muted rounded-t-lg overflow-hidden">
                      {relatedEvent.featured_image_url ? (
                        <img
                          src={relatedEvent.featured_image_url}
                          alt={relatedEvent.title}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-primary/10 to-primary/5">
                          <Calendar className="h-16 w-16 text-primary/30" />
                        </div>
                      )}
                    </div>
                    <div className="p-4 space-y-3">
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Calendar className="h-4 w-4" />
                        <span>
                          {new Date(relatedEvent.starts_at).toLocaleDateString(undefined, {
                            month: 'short',
                            day: 'numeric',
                            year: 'numeric'
                          })}
                        </span>
                      </div>
                      <h3 className="font-semibold text-foreground line-clamp-2 group-hover:text-primary transition-colors">
                        {relatedEvent.title}
                      </h3>
                      {relatedEvent.short_description && (
                        <p className="text-sm text-muted-foreground line-clamp-2">
                          {relatedEvent.short_description}
                        </p>
                      )}
                      <div className="flex items-center justify-between pt-2">
                        {relatedEvent.cpd_credits && Number(relatedEvent.cpd_credits) > 0 && (
                          <Badge variant="outline" className="text-xs">
                            <Award className="h-3 w-3 mr-1" />
                            {relatedEvent.cpd_credits} CPD
                          </Badge>
                        )}
                        <Link to={`/events/${relatedEvent.slug || relatedEvent.uuid}`} className="ml-auto">
                          <Button variant="ghost" size="sm" className="text-xs">
                            View Details
                            <ArrowRight className="ml-1 h-3 w-3" />
                          </Button>
                        </Link>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

