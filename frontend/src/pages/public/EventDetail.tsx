import React, { useEffect, useState } from "react";
import { getInitials } from "@/lib/initials";
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
  ArrowRight,
  ShieldCheck,
} from "lucide-react";
import { Button } from "@/shared/ui/button";
import { Badge } from "@/shared/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/shared/ui/card";
import { Separator } from "@/shared/ui/separator";
import { Avatar, AvatarFallback, AvatarImage } from "@/shared/ui/avatar";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/shared/ui/tabs";
import { StatusBadge } from "@/components/custom/StatusBadge";
import { JoinButton, type JoinState } from "@/components/video/JoinButton";
import { useEventActiveMeeting } from "@/hooks/useEventActiveMeeting";
import { getPublicEvent, getPublicEvents } from "@/api/events";
import { getMyRegistrations } from "@/api/registrations";
import { Event } from "@/api/events/types";
import { Registration } from "@/api/registrations/types";
import { useAuth } from "@/features/auth";
import { sanitizeHtml, hasVisibleContent } from "@/lib/sanitize";

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
  const hasRegistration = userRegistration !== null;
  const isPendingPayment = Boolean(
    userRegistration &&
    (userRegistration.payment_status === 'pending' || userRegistration.status === 'pending')
  );
  const isWaitlisted = userRegistration?.status === 'waitlisted';
  const isConfirmedRegistration = Boolean(userRegistration && userRegistration.status === 'confirmed' && !isPendingPayment);

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
        const myReg = registrations.results.find(
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
        const orgEvents = allEvents.results
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

  // Poll the *real* meeting state every 10s so the "live now" pill
  // below reflects whether anyone's actually in a meeting — not just
  // whether we're inside the event's scheduled window. Without this
  // distinction the pill would say "Event is live now" + "Join as
  // host" for the entire scheduled window, even after the host ended
  // the meeting (and the join button would 409 because no room is
  // active).
  //
  // Hoisted ABOVE the loading/error early returns so React's hook
  // order stays stable across renders. The `enabled` flag gates
  // actual fetching so we don't burn polls during the loading state
  // or for non-host / past / non-online viewers.
  const eventForPoll = event;
  const isPastForPoll = !!(
    eventForPoll &&
    (eventForPoll.ends_at
      ? new Date(eventForPoll.ends_at) < new Date()
      : new Date(eventForPoll.starts_at) < new Date())
  );
  const eventStartedForPoll = !!(
    eventForPoll && new Date(eventForPoll.starts_at) <= new Date()
  );
  const isEventOwnerForPoll =
    !!eventForPoll &&
    isAuthenticated &&
    (user?.uuid === eventForPoll.owner?.uuid || user?.uuid === eventForPoll.organizer?.uuid);
  const isEventHostForPoll =
    !!eventForPoll &&
    isAuthenticated &&
    (eventForPoll.is_current_user_host ?? isEventOwnerForPoll);
  const enableMeetingPoll =
    !!eventForPoll &&
    isEventHostForPoll &&
    eventStartedForPoll &&
    !isPastForPoll &&
    (eventForPoll.format === 'online' || eventForPoll.format === 'hybrid');
  const { status: meetingStatus } = useEventActiveMeeting(eventForPoll?.uuid, {
    enabled: enableMeetingPoll,
  });

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error || !event) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="h-12 w-12 text-destructive mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-foreground">Event Not Found</h2>
          <p className="text-muted-foreground mt-2">{error || "The event you're looking for doesn't exist."}</p>
          <Link to="/events">
            <Button className="mt-4">Browse Events</Button>
          </Link>
        </div>
      </div>
    );
  }

  // Derive states from event data (mirrors the *ForPoll values above
  // — kept duplicated rather than reused so the post-load values are
  // free of the `event && …` defensive checks).
  const isPast = isPastForPoll;
  const eventStarted = eventStartedForPoll;
  const isRegistrationOpen = event.is_registration_open ?? event.registration_enabled;
  const organizerName = event.organizer?.display_name || event.organizer_name || event.owner?.display_name || "Unknown Organizer";
  const isEventOwner = isEventOwnerForPoll;
  const isEventHost = isEventHostForPoll;
  const meetingActive = meetingStatus === 'active' || meetingStatus === 'scheduled';
  const headerJoinState: JoinState =
    meetingStatus === 'active' ? 'meeting_live'
    : meetingStatus === 'scheduled' ? 'meeting_live'
    : meetingStatus === 'ended' ? 'meeting_ended'
    : 'awaiting_host';
  const meetingPillCopy =
    meetingStatus === 'active' ? 'Meeting in progress'
    : meetingStatus === 'scheduled' ? 'Meeting starting…'
    : meetingStatus === 'ended' ? 'No meeting in progress'
    : 'Within scheduled window';

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
    if (isEventOwner) {
      return (
        <Link to={`/organizer/events/${event.uuid}/manage`}>
          <Button
            size={isLarge ? "lg" : "default"}
            className={`${isLarge ? 'w-full py-6 text-lg' : ''}`}
            variant="default"
          >
            Manage Event
          </Button>
        </Link>
      );
    }

    if (isPast) {
      return (
        <Button disabled>
          {event.status === 'completed' ? 'Event Completed' : 'Event Ended'}
        </Button>
      );
    }

    if (hasRegistration) {
      if (isPendingPayment) {
        return (
          <Link to={`/events/${id}/register?resume=${userRegistration?.uuid}`}>
            <Button
              size={isLarge ? "lg" : "default"}
              className={`${isLarge ? 'w-full py-6 text-lg' : ''} bg-warning text-foreground hover:bg-warning/90`}
            >
              <AlertCircle className="mr-2 h-4 w-4" />
              Complete Payment
            </Button>
          </Link>
        );
      }

      if (isWaitlisted) {
        return (
          <Link to="/registrations">
            <Button
              size={isLarge ? "lg" : "default"}
              variant="outline"
              className={`${isLarge ? 'w-full py-6 text-lg' : ''} border-warning bg-warning-subtle text-warning hover:bg-warning-subtle/80`}
            >
              <AlertCircle className="mr-2 h-4 w-4" />
              On the Waitlist
            </Button>
          </Link>
        );
      }

      return (
        <Link to="/registrations">
          <Button
            size={isLarge ? "lg" : "default"}
            variant="outline"
            className={`${isLarge ? 'w-full py-6 text-lg' : ''} border-success bg-success-subtle text-success hover:bg-success-subtle/80`}
          >
            <CheckCircle className="mr-2 h-4 w-4" />
            Already Registered
          </Button>
        </Link>
      );
    }

    if (isRegistrationOpen) {
      const wrapClass = isLarge ? 'w-full' : 'inline-flex flex-col items-start';
      const next = encodeURIComponent(`/events/${id}/details`);
      return (
        <div className={wrapClass}>
          <Link to={`/events/${id}/register`}>
            <Button
              size={isLarge ? "lg" : "default"}
              className={isLarge ? 'w-full py-6 text-lg' : ''}
            >
              Register Now
            </Button>
          </Link>
          {!isAuthenticated && (
            <p className={`text-xs text-muted-foreground mt-2 ${isLarge ? 'text-center w-full' : ''}`}>
              Already registered?{' '}
              <Link to={`/login?returnUrl=${next}`} className="text-primary underline-offset-2 hover:underline">
                Sign in
              </Link>
              {' '}to see your status.
            </p>
          )}
        </div>
      );
    }

    return <Button disabled>Registration Closed</Button>;
  };

  const nextUrl = encodeURIComponent(`/events/${id}/details`);

  return (
    <div className="bg-background min-h-screen pb-12">
      {/* Mini auth bar — this route doesn't sit inside PublicLayout, so an
          anon visitor would otherwise have no nav at all. */}
      {!isAuthenticated && (
        <div className="border-b border-border bg-card">
          <div className="container mx-auto flex items-center justify-between gap-4 px-4 py-2 sm:px-6 lg:px-8">
            <Link to="/discover/events" className="text-sm text-muted-foreground hover:text-foreground">
              ← Browse events
            </Link>
            <div className="flex items-center gap-2">
              <Link to={`/login?returnUrl=${nextUrl}`}>
                <Button size="sm" variant="ghost">Sign in</Button>
              </Link>
              <Link to={`/signup?returnUrl=${nextUrl}`}>
                <Button size="sm" variant="outline">Create account</Button>
              </Link>
            </div>
          </div>
        </div>
      )}
      {/* Hero Header */}
      <div className="bg-card border-b border-border">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8 lg:py-12">
          <div className="flex flex-col lg:flex-row gap-8 items-start">
            <div className="flex-1 space-y-4">
              <div className="flex flex-wrap gap-2 items-center">
                <Badge variant="outline" className="text-info border-info bg-info-subtle capitalize">
                  {event.event_type}
                </Badge>
                {event.cpd_credits && Number(event.cpd_credits) > 0 && (
                  <Badge variant="outline" className="border-border">
                    {event.cpd_type || 'CPD'} • {event.cpd_credits} Credits
                  </Badge>
                )}
                {hasRegistration && (
                  <>
                    {isPendingPayment ? (
                      <Badge variant="outline" className="border-warning bg-warning-subtle text-warning">
                        <AlertCircle className="mr-1 h-3 w-3" />
                        Payment Pending
                      </Badge>
                    ) : isWaitlisted ? (
                      <Badge variant="outline" className="border-warning bg-warning-subtle text-warning">
                        <AlertCircle className="mr-1 h-3 w-3" />
                        Waitlisted
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="border-success bg-success-subtle text-success">
                        <CheckCircle className="mr-1 h-3 w-3" />
                        Registered
                      </Badge>
                    )}
                  </>
                )}
              </div>

              <h1 className="text-3xl sm:text-4xl font-bold text-foreground tracking-tight">
                {event.title}
              </h1>

              {isEventHost && eventStarted && !isPast && (event.format === 'online' || event.format === 'hybrid') && (
                <div
                  className={`flex flex-wrap items-center gap-3 rounded-lg border px-4 py-3 ${
                    meetingActive
                      ? 'border-destructive/40 bg-destructive/10'
                      : 'border-muted-foreground/20 bg-muted/40'
                  }`}
                >
                  <span
                    className={`flex items-center gap-2 text-sm font-medium ${
                      meetingActive ? 'text-destructive' : 'text-muted-foreground'
                    }`}
                  >
                    {meetingActive && (
                      <span className="relative flex h-2 w-2">
                        <span className="absolute inline-flex h-full w-full rounded-full bg-destructive opacity-75 animate-ping" />
                        <span className="relative inline-flex h-2 w-2 rounded-full bg-destructive" />
                      </span>
                    )}
                    {meetingPillCopy}
                  </span>
                  <JoinButton
                    eventUuid={event.uuid}
                    role="host"
                    state={headerJoinState}
                    size="sm"
                  />
                </div>
              )}

              <div className="flex flex-col sm:flex-row gap-4 sm:gap-8 text-muted-foreground pt-2">
                <div className="flex items-center gap-2">
                  <Calendar className="h-5 w-5 text-muted-foreground" />
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
                  <Clock className="h-5 w-5 text-muted-foreground" />
                  <span className="text-sm font-medium">
                    {new Date(event.starts_at).toLocaleTimeString(undefined, {
                      hour: '2-digit',
                      minute: '2-digit'
                    })} ({getDurationDisplay()})
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <User className="h-5 w-5 text-muted-foreground" />
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
        {/* Grid items default to `min-width: auto`; on a long unbroken
            description that lets the left column push past its track and
            the page picks up a horizontal scrollbar. `min-w-0` on the
            grid + the column anchors widths to the grid template. */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 min-w-0">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-8 min-w-0">
            {/* Featured Image or Placeholder */}
            <div className="aspect-video w-full overflow-hidden rounded-xl border border-border shadow-sm bg-muted flex items-center justify-center">
              {event.featured_image_url ? (
                <img
                  src={event.featured_image_url}
                  alt={event.title}
                  className="h-full w-full object-cover"
                />
              ) : (
                <div className="text-muted-foreground">
                  <Calendar className="h-16 w-16" />
                </div>
              )}
            </div>

            <Tabs defaultValue="about" className="w-full">
              <TabsList className="w-full justify-start border-b border-border bg-transparent p-0 h-auto rounded-none space-x-8">
                <TabsTrigger
                  value="about"
                  className="rounded-none border-b-2 border-transparent px-0 py-3 data-[state=active]:border-primary data-[state=active]:text-primary data-[state=active]:bg-transparent shadow-none"
                >
                  About
                </TabsTrigger>
                <TabsTrigger
                  value="schedule"
                  className="rounded-none border-b-2 border-transparent px-0 py-3 data-[state=active]:border-primary data-[state=active]:text-primary data-[state=active]:bg-transparent shadow-none"
                >
                  Schedule
                </TabsTrigger>
              </TabsList>

              <TabsContent value="about" className="pt-6 space-y-6 min-w-0">
                <div className="min-w-0">
                  <h3 className="text-xl font-semibold text-foreground mb-3">Event Description</h3>
                  {hasVisibleContent(event.description) ? (
                    // The rich-text can carry long unbroken strings (URLs,
                    // identifiers, certificate codes) and wide embedded
                    // elements (tables, images, code blocks). Constrain
                    // every common offender so the page never picks up a
                    // horizontal scrollbar.
                    <div
                      className="text-muted-foreground leading-relaxed prose prose-sm dark:prose-invert max-w-none break-words [&_img]:max-w-full [&_img]:h-auto [&_table]:max-w-full [&_table]:block [&_table]:overflow-x-auto [&_pre]:max-w-full [&_pre]:overflow-x-auto"
                      dangerouslySetInnerHTML={{ __html: sanitizeHtml(event.description) }}
                    />
                  ) : event.short_description ? (
                    <p className="text-muted-foreground leading-relaxed break-words">{event.short_description}</p>
                  ) : (
                    <p className="text-muted-foreground leading-relaxed italic">No description available.</p>
                  )}
                </div>

                {event.cpd_credits && Number(event.cpd_credits) > 0 && (
                  <>
                    <Separator />
                    <div>
                      <h3 className="text-xl font-semibold text-foreground mb-4">CPD Credits</h3>
                      <div className="flex items-center gap-3 bg-warning-subtle p-4 rounded-lg border border-warning">
                        <Award className="h-8 w-8 text-warning" />
                        <div>
                          <p className="font-medium text-foreground">{event.cpd_credits} {event.cpd_type || 'CPD'} Credits</p>
                          <p className="text-sm text-muted-foreground">Earn professional development credits upon completion</p>
                        </div>
                      </div>
                    </div>
                  </>
                )}

                <Separator />
                <div>
                  <h3 className="text-xl font-semibold text-foreground mb-4">Verifiable Certificate</h3>
                  <div className="flex items-center justify-between gap-3 bg-info-subtle p-4 rounded-lg border border-info">
                    <div className="flex items-center gap-3">
                      <ShieldCheck className="h-8 w-8 text-info" />
                      <div>
                        <p className="font-medium text-foreground">Certificate of completion</p>
                        <p className="text-sm text-muted-foreground">
                          Eligible attendees receive a verifiable certificate. Anyone can verify any certificate using its code.
                        </p>
                      </div>
                    </div>
                    <Link to="/verify">
                      <Button variant="outline" size="sm">Verify a certificate</Button>
                    </Link>
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="schedule" className="pt-6">
                <div className="space-y-6">
                  <h3 className="text-xl font-semibold text-foreground">Event Schedule</h3>

                  {/* Event Date & Time Overview */}
                  <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950/30 dark:to-indigo-950/30 p-6 rounded-xl border border-info">
                    {(() => {
                      const startDate = new Date(event.starts_at);
                      const endDate = event.ends_at ? new Date(event.ends_at) : null;
                      const isMultiDay = !!endDate && (
                        startDate.getFullYear() !== endDate.getFullYear() ||
                        startDate.getMonth() !== endDate.getMonth() ||
                        startDate.getDate() !== endDate.getDate()
                      );
                      const timeFmt: Intl.DateTimeFormatOptions = { hour: 'numeric', minute: '2-digit' };

                      const DateBlock = ({ d }: { d: Date }) => (
                        <div className="bg-neutral-card rounded-xl p-4 shadow-sm text-center min-w-[80px]">
                          <div className="text-3xl font-bold text-primary">{d.getDate()}</div>
                          <div className="text-sm text-muted-foreground uppercase">
                            {d.toLocaleDateString(undefined, { month: 'short' })}
                          </div>
                          <div className="text-xs text-muted-foreground">{d.getFullYear()}</div>
                        </div>
                      );

                      return (
                        <div className="flex flex-col md:flex-row md:items-center gap-6">
                          {/* Date Block(s) — show start → end pair when multi-day. */}
                          <div className="flex items-center gap-4">
                            <DateBlock d={startDate} />
                            {isMultiDay && endDate && (
                              <>
                                <span className="text-muted-foreground text-2xl">→</span>
                                <DateBlock d={endDate} />
                              </>
                            )}
                            <div>
                              <div className="text-lg font-semibold text-foreground">
                                {isMultiDay && endDate
                                  ? `${startDate.toLocaleDateString(undefined, { weekday: 'long' })} – ${endDate.toLocaleDateString(undefined, { weekday: 'long' })}`
                                  : startDate.toLocaleDateString(undefined, { weekday: 'long' })}
                              </div>
                              <div className="flex items-center gap-2 text-muted-foreground mt-1">
                                <Clock className="h-4 w-4" />
                                <span>
                                  {startDate.toLocaleTimeString(undefined, timeFmt)}
                                  {' → '}
                                  {endDate
                                    ? (isMultiDay
                                        ? endDate.toLocaleString(undefined, { weekday: 'short', month: 'short', day: 'numeric', ...timeFmt })
                                        : endDate.toLocaleTimeString(undefined, timeFmt))
                                    : '—'}
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
                          <div className="bg-neutral-card px-4 py-2 rounded-lg shadow-sm">
                            <div className="text-xs text-muted-foreground uppercase">Duration</div>
                            <div className="font-semibold text-foreground">
                              {event.duration_minutes >= 60
                                ? `${Math.floor(event.duration_minutes / 60)}h ${event.duration_minutes % 60 > 0 ? `${event.duration_minutes % 60}m` : ''}`
                                : `${event.duration_minutes}m`}
                            </div>
                          </div>
                        )}
                        <div className="bg-card px-4 py-2 rounded-lg shadow-sm">
                          <div className="text-xs text-muted-foreground uppercase">Format</div>
                          <div className="font-semibold text-foreground capitalize flex items-center gap-1">
                            {event.format === 'online' && <Video className="h-4 w-4 text-info" />}
                            {event.format === 'in-person' && <MapPin className="h-4 w-4 text-success" />}
                            {event.format === 'hybrid' && <><Video className="h-4 w-4 text-info" /><span>+</span><MapPin className="h-4 w-4 text-success" /></>}
                            {event.format}
                          </div>
                        </div>
                      </div>
                    </div>
                      );
                    })()}

                    {/* Location if available */}
                    {event.location && (
                      <div className="mt-4 pt-4 border-t border-info">
                        <div className="flex items-start gap-2 text-muted-foreground">
                          <MapPin className="h-4 w-4 mt-0.5 text-success" />
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
                                {/* Time sidebar — surface the session's date as
                                    well when the event spans multiple days, otherwise
                                    "10:00 AM" is ambiguous between Day 1 and Day 2. */}
                                {(() => {
                                  const eventStart = new Date(event.starts_at);
                                  const sameDayAsEventStart =
                                    eventStart.getFullYear() === startTime.getFullYear() &&
                                    eventStart.getMonth() === startTime.getMonth() &&
                                    eventStart.getDate() === startTime.getDate();
                                  const eventEnd = event.ends_at ? new Date(event.ends_at) : null;
                                  const isEventMultiDay = !!eventEnd && (
                                    eventStart.getFullYear() !== eventEnd.getFullYear() ||
                                    eventStart.getMonth() !== eventEnd.getMonth() ||
                                    eventStart.getDate() !== eventEnd.getDate()
                                  );
                                  return (
                                    <div className="w-24 shrink-0 bg-muted/50 p-4 flex flex-col items-center justify-center text-center border-r border-border">
                                      {isEventMultiDay && (
                                        <div className={`text-[11px] uppercase tracking-wide ${sameDayAsEventStart ? 'text-muted-foreground' : 'text-primary font-semibold'}`}>
                                          {startTime.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })}
                                        </div>
                                      )}
                                      <div className="text-lg font-bold text-foreground">
                                        {startTime.toLocaleTimeString(undefined, timeFormat)}
                                      </div>
                                      <div className="text-xs text-muted-foreground">
                                        {session.duration_minutes >= 60
                                          ? `${Math.floor(session.duration_minutes / 60)}h${session.duration_minutes % 60 > 0 ? ` ${session.duration_minutes % 60}m` : ''}`
                                          : `${session.duration_minutes}m`}
                                      </div>
                                    </div>
                                  );
                                })()}

                                {/* Main content */}
                                <div className="flex-1 p-4">
                                  <div className="flex items-start justify-between gap-3">
                                    <div className="flex-1 min-w-0">
                                      <h5 className="font-semibold text-foreground">{session.title}</h5>
                                      {session.speaker_names && (
                                        <p className="text-sm text-info mt-1">{session.speaker_names}</p>
                                      )}
                                      {session.description && hasVisibleContent(session.description) && (
                                        // Rich-text payload — sanitize and render as
                                        // HTML, the same path the event description uses.
                                        // line-clamp-2 keeps the row compact; click-to-
                                        // expand can be a follow-up.
                                        <div
                                          className="text-sm text-muted-foreground mt-2 line-clamp-2 prose prose-sm dark:prose-invert max-w-none break-words [&_p]:m-0 [&_strong]:!bg-transparent [&_span]:!bg-transparent"
                                          dangerouslySetInnerHTML={{ __html: sanitizeHtml(session.description) }}
                                        />
                                      )}
                                    </div>
                                    {session.is_mandatory && (
                                      <Badge className="shrink-0 bg-warning-subtle text-warning hover:bg-warning-subtle">Required</Badge>
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
                <CardTitle>{isEventOwner ? "Event Management" : "Registration"}</CardTitle>
                <CardDescription>
                  {isEventOwner
                    ? "Manage your event details and registrations."
                    : isPendingPayment
                      ? "Payment pending — complete payment to confirm."
                      : isWaitlisted
                        ? "You're on the waitlist for this event."
                        : hasRegistration
                          ? "You're registered for this event!"
                          : "Secure your spot today."}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {(event.capacity || event.max_attendees) && (
                  <div className="flex justify-between items-center py-2 border-b border-border">
                    <span className="text-muted-foreground">Capacity</span>
                    <span className="text-foreground">
                      {event.registration_count} / {event.capacity || event.max_attendees} registered
                    </span>
                  </div>
                )}

                {!isPast && event.spots_remaining !== null && event.spots_remaining !== undefined && (
                  <div className="flex justify-between items-center py-2 border-b border-border">
                    <span className="text-muted-foreground">Spots Remaining</span>
                    <span className="text-foreground font-semibold">
                      {event.spots_remaining}
                    </span>
                  </div>
                )}

                {renderRegistrationButton(true)}

                {event.registration_closes_at && !isPast && !hasRegistration && (
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
                      <Link to="/discover/events">
                        <Button variant="outline" className="w-full text-xs h-8">
                          <Building2 className="h-3 w-3 mr-1" />
                          Browse Events
                        </Button>
                      </Link>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded bg-info-subtle flex items-center justify-center text-info font-bold">
                        {getInitials(organizerName)}
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
                <div className="flex items-start gap-2 text-sm text-muted-foreground">
                  {event.format === 'online' ? (
                    <>
                      <Video className="h-4 w-4 shrink-0 mt-0.5" />
                      <div className="flex-1">
                        <p className="font-medium text-foreground">Online Event</p>
                        {isPast ? (
                          <div className="mt-1 space-y-1">
                            <p className="text-muted-foreground">This session has ended.</p>
                            {/* For confirmed registrants + hosts, point at the
                                consolidated My Learning page rather than
                                embedding a player here. Keeps the recording UX
                                in one place; the My Learning Events tab gates
                                the Watch Recording button on actual
                                availability per user. */}
                            {(isConfirmedRegistration || isEventHost) && (
                              <p className="text-xs text-muted-foreground">
                                If a recording is available, you can watch it from{' '}
                                <Link
                                  to="/registrations?tab=events"
                                  className="text-primary underline-offset-2 hover:underline"
                                >
                                  My Learning
                                </Link>
                                .
                              </p>
                            )}
                          </div>
                        ) : (isConfirmedRegistration || isEventHost) ? (
                          <div className="mt-2 space-y-2">
                            {isEventHost ? (
                              <JoinButton
                                eventUuid={event.uuid}
                                size="sm"
                                role="host"
                                // Same real-meeting-state derivation as the
                                // header pill — see headerJoinState above.
                                // Without this the Location box's "Start
                                // meeting" / "Join as host" CTA fires
                                // /meetings/join/ for non-existent rooms
                                // (HTTP 409) when no meeting is live but
                                // we're inside the event's scheduled window.
                                state={headerJoinState}
                              />
                            ) : (
                              <Button size="sm" asChild>
                                <Link to={`/events/${event.uuid}/lobby`}>
                                  <Video className="h-3 w-3 mr-1" /> Go to lobby
                                </Link>
                              </Button>
                            )}
                            <p className="text-xs text-muted-foreground">
                              {isEventHost ? "You'll join as host" : "Check your email for meeting details"}
                            </p>
                          </div>
                        ) : isPendingPayment ? (
                          <div className="mt-1 space-y-1">
                            <p className="text-warning">Complete payment to receive meeting details</p>
                          </div>
                        ) : isWaitlisted ? (
                          <div className="mt-1 space-y-1">
                            <p className="text-warning">You're on the waitlist</p>
                            <p className="text-xs text-muted-foreground">We'll email you if a spot opens up</p>
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
                        {(isConfirmedRegistration || isEventHost) ? (
                          <div className="mt-2 space-y-2">
                            {isEventHost ? (
                              <JoinButton
                                eventUuid={event.uuid}
                                size="sm"
                                role="host"
                                // Same real-meeting-state derivation as the
                                // header pill — see headerJoinState above.
                                // Without this the Location box's "Start
                                // meeting" / "Join as host" CTA fires
                                // /meetings/join/ for non-existent rooms
                                // (HTTP 409) when no meeting is live but
                                // we're inside the event's scheduled window.
                                state={headerJoinState}
                              />
                            ) : (
                              <Button size="sm" asChild>
                                <Link to={`/events/${event.uuid}/lobby`}>
                                  <Video className="h-3 w-3 mr-1" /> Go to lobby
                                </Link>
                              </Button>
                            )}
                            <p className="text-xs text-muted-foreground">
                              {isEventHost ? "You'll join as host" : "Check your email for meeting details"}
                            </p>
                          </div>
                        ) : isPendingPayment ? (
                          <div className="mt-1 space-y-1">
                            <p className="text-warning">Complete payment to receive event details</p>
                          </div>
                        ) : isWaitlisted ? (
                          <div className="mt-1 space-y-1">
                            <p className="text-warning">You're on the waitlist</p>
                            <p className="text-xs text-muted-foreground">We'll email you if a spot opens up</p>
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
                        {isConfirmedRegistration ? (
                          <p className="mt-1 text-success">Location details sent to your email</p>
                        ) : isPendingPayment ? (
                          <p className="mt-1 text-warning">Complete payment to receive location details</p>
                        ) : isWaitlisted ? (
                          <p className="mt-1 text-warning">You're on the waitlist for location details</p>
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
              <Link to="/discover/events">
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
                        <Link to={`/events/${relatedEvent.slug || relatedEvent.uuid}/details`} className="ml-auto">
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
