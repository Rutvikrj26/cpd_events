import { useState } from 'react';
import { Video, Loader2, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from '@/components/ui/dialog';
import { joinEventVideo, joinCourseSessionVideo } from '@/api/video';
import { VideoRoom } from './VideoRoom';

export type JoinRole = 'host' | 'attendee';
export type JoinState =
  | 'pre_event'
  | 'in_window'
  | 'live'
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
  /** Surface a tooltip when disabled so users understand why. */
  disabledReason?: string;
}

function resolve(role: JoinRole, state: JoinState): Resolved {
  if (state === 'provisioning') return { label: 'Setting up room…', enabled: false, disabledReason: 'Refresh in a moment.' };
  if (state === 'cancelled') return { label: 'Cancelled', enabled: false };
  if (state === 'past_no_recording') return { label: 'Recording unavailable', enabled: false };
  if (state === 'past_recording') return { label: 'Watch recording', enabled: true };

  if (role === 'host') {
    if (state === 'live') return { label: 'Join as host', enabled: true };
    return { label: 'Start meeting', enabled: true };
  }

  // attendee
  if (state === 'pre_event') return { label: 'Join when live', enabled: false, disabledReason: 'Opens 15 minutes before start.' };
  return { label: 'Join now', enabled: true };
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
  const [videoSession, setVideoSession] = useState<{
    token: string;
    ws_url: string;
    room_name: string;
    room_uuid?: string;
    is_host?: boolean;
    waiting?: boolean;
    waiting_room_enabled?: boolean;
    recording_active?: boolean;
    recording_enabled_default?: boolean;
  } | null>(null);

  const { label, enabled, disabledReason } = resolve(role, state);

  const handleJoin = async () => {
    setLoading(true);
    setError(null);
    try {
      let response;
      if (eventUuid) {
        response = await joinEventVideo(eventUuid);
      } else if (courseUuid && sessionUuid) {
        response = await joinCourseSessionVideo(courseUuid, sessionUuid);
      } else {
        throw new Error('No event or course session specified');
      }
      setVideoSession(response);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to join video room';
      const friendly = /not configured|not ready|provision/i.test(message)
        ? "The video room isn't ready yet — please try again in a moment."
        : message;
      setError(friendly);
    } finally {
      setLoading(false);
    }
  };

  const isDisabled = loading || !enabled;

  return (
    <>
      <Button
        variant={variant}
        size={size}
        className={className}
        onClick={handleJoin}
        disabled={isDisabled}
        title={disabledReason}
      >
        {loading ? (
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        ) : !enabled ? (
          <AlertCircle className="mr-2 h-4 w-4" />
        ) : (
          <Video className="mr-2 h-4 w-4" />
        )}
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
