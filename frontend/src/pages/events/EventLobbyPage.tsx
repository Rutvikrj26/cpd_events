import { useEffect, useMemo, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Calendar, MapPin, Users, AlertCircle, ArrowLeft } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { JoinButton } from '@/components/video/JoinButton';
import { AddToCalendar } from '@/components/events/AddToCalendar';
import { EventCountdown } from '@/components/events/EventCountdown';
import { getPublicEvent, getRegistrationLobby, RegistrationLobbyResponse } from '@/api/events';
import type { Event } from '@/api/events/types';

interface LobbyData {
  event: Event;
  registration?: RegistrationLobbyResponse['registration'];
  isGuest: boolean;
}

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'long', timeStyle: 'short' });
}

export function EventLobbyPage() {
  const params = useParams();
  const eventUuid = params.id as string | undefined;
  const registrationUuid = params.registrationUuid as string | undefined;

  const [data, setData] = useState<LobbyData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    (async () => {
      try {
        if (registrationUuid) {
          const resp = await getRegistrationLobby(registrationUuid);
          if (!cancelled) setData({ event: resp.event, registration: resp.registration, isGuest: true });
        } else if (eventUuid) {
          // Public detail endpoint accepts both slug and uuid; this avoids
          // hitting the organizer-scoped /events/<uuid>/ endpoint, which 403s
          // for registered learners.
          const event = await getPublicEvent(eventUuid);
          if (!cancelled) setData({ event, isGuest: false });
        } else {
          if (!cancelled) setError('Missing event or registration identifier.');
        }
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : 'Failed to load event.';
        if (!cancelled) setError(message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [eventUuid, registrationUuid]);

  const description = useMemo(() => {
    if (!data) return '';
    return data.event.short_description || data.event.description || '';
  }, [data]);

  if (loading) {
    return (
      <div className="mx-auto max-w-3xl p-6 space-y-4">
        <Skeleton className="h-10 w-2/3" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <Card>
          <CardContent className="p-8 text-center space-y-3">
            <AlertCircle className="mx-auto h-10 w-10 text-rose-500" />
            <h1 className="text-xl font-semibold">Couldn't load this event</h1>
            <p className="text-sm text-muted-foreground">{error ?? 'Please check the link and try again.'}</p>
            <Button asChild variant="outline">
              <Link to="/my-events">
                <ArrowLeft className="mr-2 h-4 w-4" />
                My Events
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const { event, registration, isGuest } = data;
  const now = new Date();
  const starts = new Date(event.starts_at);
  const ends = new Date(event.ends_at);
  const isPast = now >= ends || event.status === 'completed' || event.status === 'closed';
  const isLive = event.status === 'live' || (now >= starts && now < ends);
  const isCancelled = event.status === 'cancelled';
  const canJoinNow = !isCancelled && (isLive || (starts.getTime() - now.getTime()) <= 15 * 60 * 1000);

  return (
    <div className="mx-auto max-w-3xl p-6 space-y-6">
      {!isGuest && (
        <div>
          <Button asChild variant="ghost" size="sm">
            <Link to="/my-events">
              <ArrowLeft className="mr-2 h-4 w-4" /> Back to My Events
            </Link>
          </Button>
        </div>
      )}

      <header className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">{event.title}</h1>
        {event.short_description && (
          <p className="text-muted-foreground">{event.short_description}</p>
        )}
      </header>

      <EventCountdown
        startsAt={event.starts_at}
        endsAt={event.ends_at}
        status={event.status}
        className="w-full max-w-md"
      />

      <Card>
        <CardContent className="p-6 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
            <div className="flex items-start gap-2">
              <Calendar className="mt-0.5 h-4 w-4 text-muted-foreground" />
              <div>
                <div className="font-medium">When</div>
                <div className="text-muted-foreground">
                  {fmtDate(event.starts_at)}
                  {event.timezone && ` (${event.timezone})`}
                </div>
                {event.duration_minutes && (
                  <div className="text-muted-foreground">{event.duration_minutes} min</div>
                )}
              </div>
            </div>
            {event.location && (
              <div className="flex items-start gap-2">
                <MapPin className="mt-0.5 h-4 w-4 text-muted-foreground" />
                <div>
                  <div className="font-medium">Where</div>
                  <div className="text-muted-foreground">{event.location}</div>
                </div>
              </div>
            )}
            {typeof event.registration_count === 'number' && (
              <div className="flex items-start gap-2">
                <Users className="mt-0.5 h-4 w-4 text-muted-foreground" />
                <div>
                  <div className="font-medium">Registered</div>
                  <div className="text-muted-foreground">{event.registration_count}{event.max_attendees ? ` / ${event.max_attendees}` : ''}</div>
                </div>
              </div>
            )}
          </div>

          <div className="flex flex-wrap gap-2 pt-2">
            {!isCancelled && !isPast && (
              <JoinButton
                eventUuid={event.uuid}
                label={isLive ? 'Join now' : canJoinNow ? 'Join now' : 'Join when live'}
                size="lg"
                className={!canJoinNow ? 'opacity-60 pointer-events-none' : ''}
              />
            )}
            <AddToCalendar
              title={event.title}
              startsAt={event.starts_at}
              endsAt={event.ends_at}
              description={description}
              location={event.location}
              size="lg"
            />
          </div>
          {!canJoinNow && !isPast && !isCancelled && (
            <p className="text-xs text-muted-foreground">
              The Join button activates 15 minutes before the event starts.
            </p>
          )}
        </CardContent>
      </Card>

      {description && (
        <Card>
          <CardContent className="p-6">
            <h2 className="font-semibold mb-2">About this event</h2>
            <p className="text-sm whitespace-pre-wrap text-muted-foreground">{description}</p>
          </CardContent>
        </Card>
      )}

      {registration && (
        <Card>
          <CardContent className="p-6 text-sm space-y-1">
            <h2 className="font-semibold mb-2">Your registration</h2>
            <div><span className="text-muted-foreground">Name:</span> {registration.full_name}</div>
            <div><span className="text-muted-foreground">Email:</span> {registration.email}</div>
            <div><span className="text-muted-foreground">Status:</span> <span className="capitalize">{registration.status}</span></div>
          </CardContent>
        </Card>
      )}

      {isPast && (
        <Card>
          <CardContent className="p-6 space-y-3">
            <h2 className="font-semibold">After the event</h2>
            <p className="text-sm text-muted-foreground">
              If a recording was published, you'll find it on your event page.
            </p>
            <Button asChild variant="outline" size="sm">
              <Link to={`/events/${event.uuid}/recording`}>View recording</Link>
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
