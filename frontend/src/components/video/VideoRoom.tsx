import { useCallback, useState } from 'react';
import { Circle, ExternalLink, Loader2, PhoneOff } from 'lucide-react';
import { Button } from '@/shared/ui/button';
import { Badge } from '@/shared/ui/badge';
import { endMeeting } from '@/api/video';

/**
 * Thin Zoom CTA replacement for the previous LiveKit-embedded room.
 *
 * The platform now hands meetings off to the native Zoom client: the
 * backend returns a personalized registrant join URL (or the generic
 * meeting URL) on `ws_url`, and we open that in a new tab. Host
 * controls — captions, background effects, leave/end UX — are handled
 * inside Zoom itself; the only host-affordance we keep on our side is
 * the "End meeting" API call (terminates the session for everyone via
 * the backend), since attendees can't reach that from inside Zoom.
 *
 * Props are deliberately a superset of what the old LiveKit room
 * accepted so existing callers (JoinButton, lobby pages) keep working
 * without changes. Unused fields (token, waiting room, recording auto-
 * managed flags) are accepted and silently ignored.
 */
interface VideoRoomProps {
  /** LiveKit JWT — unused for Zoom, accepted for backwards compat. */
  token?: string;
  /** Zoom join URL. Backend places it on the same field LiveKit used. */
  serverUrl: string;
  roomName: string;
  roomUuid?: string;
  isHost?: boolean;
  /** LiveKit waiting-room flag — unused for Zoom, accepted for compat. */
  waiting?: boolean;
  waitingRoomEnabled?: boolean;
  recordingActive?: boolean;
  recordingAutoManaged?: boolean;
  onDisconnected?: () => void;
}

export function VideoRoom({
  serverUrl,
  roomName,
  roomUuid,
  isHost = false,
  recordingActive = false,
  onDisconnected,
}: VideoRoomProps) {
  const [endBusy, setEndBusy] = useState(false);
  const [endError, setEndError] = useState<string | null>(null);
  const [opened, setOpened] = useState(false);

  const handleOpenZoom = useCallback(() => {
    if (!serverUrl) return;
    window.open(serverUrl, '_blank', 'noopener,noreferrer');
    setOpened(true);
  }, [serverUrl]);

  const handleEnd = useCallback(async () => {
    if (!roomUuid) return;
    setEndBusy(true);
    setEndError(null);
    try {
      await endMeeting(roomUuid);
      onDisconnected?.();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to end the meeting.';
      setEndError(message);
    } finally {
      setEndBusy(false);
    }
  }, [roomUuid, onDisconnected]);

  return (
    <div
      className="flex h-full w-full flex-col items-center justify-center gap-6 bg-background p-8"
      data-room={roomName}
    >
      <div className="max-w-md text-center space-y-3">
        <h2 className="text-xl font-semibold">Your meeting is ready</h2>
        <p className="text-sm text-muted-foreground">
          Zoom will open in a new tab. Keep this window open to end the meeting
          when you're done.
        </p>
      </div>

      {recordingActive && isHost && (
        <Badge variant="destructive" className="gap-1">
          <span className="inline-flex h-2 w-2 rounded-full bg-red-200 animate-pulse" />
          Recording is on
        </Badge>
      )}

      <Button size="lg" className="gap-2" onClick={handleOpenZoom} disabled={!serverUrl}>
        <ExternalLink className="h-5 w-5" />
        {opened ? 'Re-open in Zoom' : 'Open in Zoom'}
      </Button>

      {opened && (
        <p className="text-xs text-muted-foreground">
          Didn't see Zoom open? Check your browser's pop-up blocker, or click the
          button again.
        </p>
      )}

      {isHost && roomUuid && (
        <div className="flex flex-col items-center gap-2 pt-4">
          <Button
            variant="destructive"
            size="sm"
            className="gap-2"
            onClick={handleEnd}
            disabled={endBusy}
            data-testid="end-meeting-confirm"
          >
            {endBusy ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <PhoneOff className="h-4 w-4" />
            )}
            End meeting for everyone
          </Button>
          {endError && <p className="text-xs text-destructive">{endError}</p>}
        </div>
      )}

      <Button variant="ghost" size="sm" onClick={onDisconnected} className="gap-2">
        <Circle className="h-3 w-3" />
        Close
      </Button>
    </div>
  );
}
