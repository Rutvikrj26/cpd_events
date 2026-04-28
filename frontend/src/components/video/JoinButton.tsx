import { useState } from 'react';
import { Video, Loader2, AlertCircle } from 'lucide-react';
import { Button } from '@/shared/ui/button';
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from '@/shared/ui/dialog';
import {
  joinCourseSessionMeeting,
  joinEventMeeting,
  startCourseSessionMeeting,
  startEventMeeting,
} from '@/api/video';
import type { JoinVideoResponse } from '@/api/video/types';
import { VideoRoom } from './VideoRoom';

export type JoinRole = 'host' | 'attendee';

/**
 * Lifecycle states the lobby can be in. The Zoom-style flow has six
 * states an authenticated user can land in (plus three terminal ones
 * for ended/cancelled events). The lobby derives this state from
 * (a) the event's schedule and (b) a polling query against
 * `/meetings/active/`.
 *
 *   pre_event       — attendee sees the event before the join window
 *                     opens (>15min before start). Disabled.
 *   awaiting_host   — within window, host hasn't started the meeting yet.
 *                     Host: "Start meeting"; attendee: "Waiting for host".
 *   meeting_live    — host has clicked Start; the room is ACTIVE.
 *                     Host: "Join as host"; attendee: "Join now".
 *   meeting_ended   — last meeting session has ended; event window
 *                     still open. Host: "Start a new meeting";
 *                     attendee: "Meeting has ended".
 *   past_recording  — event over, recording playable.
 *   past_no_recording — event over, no recording.
 *   cancelled       — event cancelled.
 *   provisioning    — backend is still warming up the room.
 */
export type JoinState =
  | 'pre_event'
  | 'awaiting_host'
  | 'meeting_live'
  | 'meeting_ended'
  | 'past_recording'
  | 'past_no_recording'
  | 'provisioning'
  | 'cancelled';

interface JoinButtonProps {
  eventUuid?: string;
  courseUuid?: string;
  sessionUuid?: string;
  role: JoinRole;
  state: JoinState;
  variant?: 'default' | 'outline' | 'secondary';
  size?: 'default' | 'sm' | 'lg';
  className?: string;
}

interface Resolved {
  label: string;
  enabled: boolean;
  action: 'start' | 'join' | 'noop';
  /** Surface a tooltip when disabled so users understand why. */
  disabledReason?: string;
  /** Optional spinner to render alongside disabled buttons (e.g. waiting for host). */
  spinner?: boolean;
}

function resolve(role: JoinRole, state: JoinState): Resolved {
  if (state === 'provisioning')
    return { label: 'Setting up room…', enabled: false, action: 'noop', disabledReason: 'Refresh in a moment.' };
  if (state === 'cancelled')
    return { label: 'Cancelled', enabled: false, action: 'noop' };
  if (state === 'past_no_recording')
    return { label: 'Recording unavailable', enabled: false, action: 'noop' };
  if (state === 'past_recording')
    return { label: 'Watch recording', enabled: true, action: 'noop' };

  if (role === 'host') {
    if (state === 'meeting_live') return { label: 'Join as host', enabled: true, action: 'join' };
    if (state === 'meeting_ended') return { label: 'Start a new meeting', enabled: true, action: 'start' };
    // pre_event or awaiting_host — host can start at any time.
    return { label: 'Start meeting', enabled: true, action: 'start' };
  }

  // attendee
  if (state === 'pre_event')
    return {
      label: 'Join when live',
      enabled: false,
      action: 'noop',
      disabledReason: 'Opens 15 minutes before start.',
    };
  if (state === 'awaiting_host')
    return {
      label: 'Waiting for host…',
      enabled: false,
      action: 'noop',
      disabledReason: 'The host hasn’t started the meeting yet.',
      spinner: true,
    };
  if (state === 'meeting_ended')
    return { label: 'Meeting has ended', enabled: false, action: 'noop' };
  // meeting_live
  return { label: 'Join now', enabled: true, action: 'join' };
}

export function JoinButton({
  eventUuid,
  courseUuid,
  sessionUuid,
  role,
  state,
  variant = 'default',
  size = 'default',
  className,
}: JoinButtonProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [videoSession, setVideoSession] = useState<JoinVideoResponse | null>(null);

  const { label, enabled, action, disabledReason, spinner } = resolve(role, state);

  const handleClick = async () => {
    if (action === 'noop') return;
    setLoading(true);
    setError(null);
    try {
      let response: JoinVideoResponse;
      if (action === 'start') {
        if (eventUuid) {
          response = await startEventMeeting(eventUuid);
        } else if (courseUuid && sessionUuid) {
          response = await startCourseSessionMeeting(courseUuid, sessionUuid);
        } else {
          throw new Error('Missing event or course session identifier.');
        }
      } else {
        // action === 'join'
        if (eventUuid) {
          response = await joinEventMeeting(eventUuid);
        } else if (courseUuid && sessionUuid) {
          response = await joinCourseSessionMeeting(courseUuid, sessionUuid);
        } else {
          throw new Error('Missing event or course session identifier.');
        }
      }
      setVideoSession(response);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to join the meeting.';
      // The "no_active_meeting" 409 happens when an attendee races a
      // host's End. Translate to friendly copy; the lobby's polling
      // loop will flip the button back to "Waiting for host" on next tick.
      const friendly = /no_active_meeting/i.test(message)
        ? "The host hasn’t started the meeting yet."
        : /not.?registered|not.?enrolled/i.test(message)
          ? "You're not registered for this event."
          : /host.?only/i.test(message)
            ? 'Only the host can start the meeting.'
            : /video.?not.?enabled/i.test(message)
              ? "Video conferencing isn't enabled for this event."
              : message;
      setError(friendly);
    } finally {
      setLoading(false);
    }
  };

  const isDisabled = loading || !enabled;
  const Icon = loading ? Loader2 : spinner ? Loader2 : !enabled ? AlertCircle : Video;
  const iconClass = `mr-2 h-4 w-4 ${loading || spinner ? 'animate-spin' : ''}`;

  return (
    <>
      <Button
        variant={variant}
        size={size}
        className={className}
        onClick={handleClick}
        disabled={isDisabled}
        title={disabledReason}
      >
        <Icon className={iconClass} />
        {label}
      </Button>

      {error && <p className="text-sm text-destructive mt-1">{error}</p>}

      <Dialog
        open={!!videoSession}
        onOpenChange={(open) => {
          if (!open) setVideoSession(null);
        }}
      >
        <DialogContent className="max-w-6xl h-[85vh] p-0" hideCloseButton>
          <DialogTitle className="sr-only">Video Room</DialogTitle>
          {videoSession && (
            <VideoRoom
              token={videoSession.token}
              serverUrl={videoSession.ws_url}
              roomName={videoSession.room_name}
              roomUuid={videoSession.room_uuid}
              isHost={videoSession.is_host}
              waiting={videoSession.waiting}
              waitingRoomEnabled={videoSession.waiting_room_enabled}
              recordingActive={videoSession.recording_active}
              recordingAutoManaged={!!videoSession.recording_enabled_default}
              onDisconnected={() => setVideoSession(null)}
            />
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
