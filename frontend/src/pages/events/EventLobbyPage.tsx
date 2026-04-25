import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { AlertCircle, ArrowLeft } from 'lucide-react';
import { Link } from 'react-router-dom';

import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { JoinButton } from '@/components/video/JoinButton';
import { LiveSessionLobby } from '@/components/live/LiveSessionLobby';
import { getPublicEvent, getRegistrationLobby, RegistrationLobbyResponse } from '@/api/events';
import type { Event } from '@/api/events/types';

interface LobbyData {
  event: Event;
  registration?: RegistrationLobbyResponse['registration'];
  isGuest: boolean;
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
    <LiveSessionLobby
      title={event.title}
      description={description}
      startsAt={event.starts_at}
      endsAt={event.ends_at}
      timezone={event.timezone}
      durationMinutes={event.duration_minutes ?? 60}
      location={event.location}
      registrationCount={typeof event.registration_count === 'number' ? event.registration_count : undefined}
      maxAttendees={event.max_attendees}
      status={event.status as any}
      canJoinNow={canJoinNow}
      isPast={isPast}
      joinSlot={
        !isCancelled && !isPast ? (
          <JoinButton
            eventUuid={event.uuid}
            label={isLive ? 'Join now' : canJoinNow ? 'Join now' : 'Join when live'}
            size="lg"
            className={!canJoinNow ? 'opacity-60 pointer-events-none' : ''}
          />
        ) : null
      }
      backLink={isGuest ? { to: '/', label: 'Home' } : { to: '/my-events', label: 'Back to My Events' }}
      recordingLink={isPast ? { to: `/events/${event.uuid}/recording` } : undefined}
      additionalCards={
        registration && (
          <Card>
            <CardContent className="p-6 text-sm space-y-1">
              <h2 className="font-semibold mb-2">Your registration</h2>
              <div><span className="text-muted-foreground">Name:</span> {registration.full_name}</div>
              <div><span className="text-muted-foreground">Email:</span> {registration.email}</div>
              <div><span className="text-muted-foreground">Status:</span> <span className="capitalize">{registration.status}</span></div>
            </CardContent>
          </Card>
        )
      }
    />
  );
}
