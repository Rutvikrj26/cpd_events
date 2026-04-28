import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { AlertCircle, ArrowLeft } from 'lucide-react';
import { Link } from 'react-router-dom';

import { Button } from '@/shared/ui/button';
import { Card, CardContent } from '@/shared/ui/card';
import { Skeleton } from '@/shared/ui/skeleton';
import { JoinButton, type JoinState } from '@/components/video/JoinButton';
import { LiveSessionLobby } from '@/components/live/LiveSessionLobby';
import { getPublicEvent, getRegistrationLobby, RegistrationLobbyResponse } from '@/api/events';
import { useEventActiveMeeting } from '@/hooks/useEventActiveMeeting';
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

  // Poll the backend every 10s for the lifecycle status of the most
  // recent VideoRoom on this content object. The endpoint returns a
  // canonical status (`none` / `scheduled` / `active` / `ended`) that
  // maps directly onto the lobby's JoinState — no client-side
  // bookkeeping required. Without this, after a host ended a meeting
  // the lobby would fall back to "Start meeting" copy that suggests
  // no session has happened yet (lifecycle ambiguity bug).
  //
  // Hoisted ABOVE the loading/error early returns to keep hook order
  // stable across renders (React's Rules of Hooks). The `enabled`
  // flag gates actual fetching: we don't poll until the event has
  // loaded, hasJoinUi is true, and the user isn't a public guest
  // (guest polling endpoint takes a registration_uuid query param —
  // small follow-up).
  const eventForPoll = data?.event ?? null;
  const isPastForPoll = !!(
    eventForPoll &&
    (new Date() >= new Date(eventForPoll.ends_at) ||
      eventForPoll.status === 'completed' ||
      eventForPoll.status === 'closed' ||
      eventForPoll.status === 'cancelled')
  );
  const pollEnabled =
    !!eventForPoll && !data?.isGuest && !isPastForPoll && !!eventForPoll.video_enabled;
  const { status: meetingStatus } = useEventActiveMeeting(eventForPoll?.uuid, {
    enabled: pollEnabled,
  });

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
              <Link to="/registrations?tab=events">
                <ArrowLeft className="mr-2 h-4 w-4" />
                My Learning
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
  const isCancelled = event.status === 'cancelled';
  const inWindow =
    !isCancelled && !isPast && (starts.getTime() - now.getTime()) <= 15 * 60 * 1000;
  // Server-computed signal: owner OR listed speaker OR platform admin —
  // anyone trusted to start the room. Hosts can start any time
  // (the 15-min attendee window doesn't apply to them).
  const isHost = !!event.is_current_user_host;
  const hasJoinUi = !isCancelled && !isPast && !!event.video_enabled;

  // Map the backend's canonical lifecycle status onto the JoinButton's
  // state enum. `scheduled` is special: the host can rejoin their own
  // pending room (it's "their" meeting) but attendees keep waiting
  // until the room actually goes ACTIVE on first participant connect.
  const joinState: JoinState =
    isCancelled ? 'cancelled'
    : isPast    ? 'past_recording'  // no disambiguation; recording link below covers both
    : meetingStatus === 'active'    ? 'meeting_live'
    : meetingStatus === 'scheduled' ? (isHost ? 'meeting_live' : 'awaiting_host')
    : meetingStatus === 'ended'     ? 'meeting_ended'
    // status === 'none' — no VideoRoom has been created yet.
    : (isHost || inWindow)          ? 'awaiting_host'
    : 'pre_event';

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
      // Pass real meeting state so the countdown pill stops showing
      // "Live now" when no meeting is actually running. The JoinButton
      // is the single source of truth for the join action; the pill
      // should agree, not contradict it.
      meetingActive={meetingStatus === 'active' || meetingStatus === 'scheduled'}
      canJoinNow={inWindow || meetingStatus === 'active' || meetingStatus === 'scheduled'}
      isPast={isPast}
      joinSlot={
        hasJoinUi ? (
          <JoinButton
            eventUuid={event.uuid}
            role={isHost ? 'host' : 'attendee'}
            state={joinState}
            size="lg"
          />
        ) : null
      }
      backLink={isGuest ? { to: '/', label: 'Home' } : { to: '/registrations?tab=events', label: 'Back to My Learning' }}
      recordingLink={isPast ? { to: `/events/${event.uuid}/recording` } : undefined}
      additionalCards={
        <>
          {!isCancelled && !isPast && !event.video_enabled && (
            <Card>
              <CardContent className="p-6 text-sm text-muted-foreground">
                {event.format === 'in_person'
                  ? 'This is an in-person event. See the location details above for joining instructions.'
                  : 'Video conferencing is not yet set up for this event. The organizer will share joining instructions before the session starts.'}
              </CardContent>
            </Card>
          )}
          {/* Surface the captions+recording posture before the user joins.
              The transcription chip serves a dual purpose: (1) "you'll
              see captions" for accessibility-first users; (2) consent
              notice for medical content — speech is being converted to
              text and stored. Combined with the existing recording
              indicator, this is the lobby-side consent banner. */}
          {!isCancelled && !isPast && event.video_enabled && event.transcription_enabled && (
            <Card>
              <CardContent className="p-6 text-sm">
                <h2 className="font-semibold mb-2">Live captions</h2>
                <p className="text-muted-foreground">
                  This session will be transcribed in real time. Captions are
                  available in the meeting via the <strong>Captions</strong>{' '}
                  toggle. A searchable transcript will be available after the
                  session ends.
                </p>
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
        </>
      }
    />
  );
}
