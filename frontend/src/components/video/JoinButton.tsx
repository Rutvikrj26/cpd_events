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

interface JoinButtonProps {
  eventUuid?: string;
  courseUuid?: string;
  sessionUuid?: string;
  label?: string;
  variant?: 'default' | 'outline' | 'secondary';
  size?: 'default' | 'sm' | 'lg';
  className?: string;
  /**
   * Disable the button with a contextual reason. Common values:
   *   "not_provisioned" — VideoRoom is still being set up
   *   "ended"           — event has finished, no joining
   *   "not_yet"         — too early to join (lobby decides this)
   */
  disabledReason?: 'not_provisioned' | 'ended' | 'not_yet' | null;
}

const DISABLED_LABELS: Record<NonNullable<JoinButtonProps['disabledReason']>, string> = {
  not_provisioned: 'Setting up room…',
  ended: 'Event ended',
  not_yet: 'Join when live',
};

export function JoinButton({
  eventUuid,
  courseUuid,
  sessionUuid,
  label = 'Join Video',
  variant = 'default',
  size = 'default',
  className,
  disabledReason = null,
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
  } | null>(null);

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
      // Surface room-not-ready messages from the backend.
      const message = err instanceof Error ? err.message : 'Failed to join video room';
      const friendly = /not configured|not ready|provision/i.test(message)
        ? 'The video room isn\'t ready yet — please try again in a moment.'
        : message;
      setError(friendly);
    } finally {
      setLoading(false);
    }
  };

  const effectiveLabel = disabledReason ? DISABLED_LABELS[disabledReason] : label;
  const isDisabled = loading || disabledReason !== null;

  return (
    <>
      <Button
        variant={variant}
        size={size}
        className={className}
        onClick={handleJoin}
        disabled={isDisabled}
        title={disabledReason === 'not_provisioned' ? 'Refresh in a moment.' : undefined}
      >
        {loading ? (
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        ) : disabledReason ? (
          <AlertCircle className="mr-2 h-4 w-4" />
        ) : (
          <Video className="mr-2 h-4 w-4" />
        )}
        {effectiveLabel}
      </Button>

      {error && (
        <p className="text-sm text-destructive mt-1">{error}</p>
      )}

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
              onDisconnected={() => setVideoSession(null)}
            />
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
