import {
  LiveKitRoom,
  RoomAudioRenderer,
  GridLayout,
  ParticipantTile,
  ControlBar,
  Chat,
  useLocalParticipant,
  useParticipants,
  useRoomContext,
  useTracks,
} from '@livekit/components-react';
import '@livekit/components-styles';
import { Track } from 'livekit-client';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { AlertCircle, Captions, Circle, LogOut, Loader2, MessageSquare, PhoneOff, UserCheck, UserX, X } from 'lucide-react';
import { Card, CardContent } from '@/shared/ui/card';
import { Button } from '@/shared/ui/button';
import { Badge } from '@/shared/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/shared/ui/dialog';
import { BackgroundEffectsPicker } from '@/components/video/BackgroundEffectsPicker';
import { CaptionOverlay } from '@/components/video/CaptionOverlay';
import { useAuth } from '@/features/auth';
import {
  admitParticipant,
  denyParticipant,
  endMeeting,
  startRoomRecording,
  stopRoomRecording,
} from '@/api/video';

interface VideoRoomProps {
  token: string;
  serverUrl: string;
  roomName: string;
  roomUuid?: string;
  isHost?: boolean;
  waiting?: boolean;
  waitingRoomEnabled?: boolean;
  recordingActive?: boolean;
  recordingAutoManaged?: boolean;
  onDisconnected?: () => void;
}

export function VideoRoom({
  token,
  serverUrl,
  roomName,
  roomUuid,
  isHost = false,
  waiting: initialWaiting = false,
  waitingRoomEnabled = false,
  recordingActive: initialRecordingActive = false,
  recordingAutoManaged = false,
  onDisconnected,
}: VideoRoomProps) {
  const [error, setError] = useState<string | null>(null);

  if (error) {
    return (
      <Card className="border-destructive">
        <CardContent className="flex flex-col items-center gap-4 p-8">
          <AlertCircle className="h-12 w-12 text-destructive" />
          <p className="text-sm text-muted-foreground">{error}</p>
          <Button variant="outline" onClick={() => setError(null)}>
            Try Again
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="h-full w-full flex flex-col overflow-hidden bg-background" data-room={roomName}>
      <LiveKitRoom
        token={token}
        serverUrl={serverUrl}
        connect={true}
        onDisconnected={onDisconnected}
        onError={(err) => {
          console.error('LiveKit error:', err);
          setError(err?.message || 'Failed to connect to video room');
        }}
        className="h-full w-full flex flex-col"
      >
        <RoomAudioRenderer />
        <RoomContent
          isHost={isHost}
          initialWaiting={initialWaiting}
          waitingRoomEnabled={waitingRoomEnabled}
          roomUuid={roomUuid}
          initialRecordingActive={initialRecordingActive}
          recordingAutoManaged={recordingAutoManaged}
        />
      </LiveKitRoom>
    </div>
  );
}

interface RoomContentProps {
  isHost: boolean;
  initialWaiting: boolean;
  waitingRoomEnabled: boolean;
  roomUuid?: string;
  initialRecordingActive: boolean;
  recordingAutoManaged: boolean;
}

function RoomContent({
  isHost,
  initialWaiting,
  waitingRoomEnabled,
  roomUuid,
  initialRecordingActive,
  recordingAutoManaged,
}: RoomContentProps) {
  const { localParticipant } = useLocalParticipant();
  const [chatOpen, setChatOpen] = useState(false);
  // Per-user caption preference. Stored under the user's uuid so two
  // users on the same browser don't share state. Captions are an
  // accessibility setting — once a user enables them, we want it to
  // stick across meetings, not be a per-meeting decision.
  const { user } = useAuth();
  const captionsKey = user?.uuid ? `accredit:captions:${user.uuid}` : null;
  const [captionsEnabled, setCaptionsEnabled] = useState(() => {
    if (!captionsKey) return false;
    try {
      return window.localStorage.getItem(captionsKey) === '1';
    } catch {
      return false;
    }
  });
  const handleToggleCaptions = useCallback(() => {
    setCaptionsEnabled((prev) => {
      const next = !prev;
      if (captionsKey) {
        try {
          window.localStorage.setItem(captionsKey, next ? '1' : '0');
        } catch {
          // localStorage can be disabled in private mode; falling back
          // to in-memory state is fine — the user can re-toggle next
          // session if needed.
        }
      }
      return next;
    });
  }, [captionsKey]);

  // Track whether the local (non-host) attendee has been admitted.
  // Starts `true` (admitted) unless the server told us they're waiting.
  const [admitted, setAdmitted] = useState(!initialWaiting);

  // When a waiting attendee's canPublish flips to true, they've been admitted.
  useEffect(() => {
    if (!initialWaiting || isHost) return;
    const perms = localParticipant.permissions;
    if (perms?.canPublish && perms?.canSubscribe) {
      setAdmitted(true);
    }
  }, [localParticipant.permissions, initialWaiting, isHost]);

  // Subscribe to only published screen-share / camera tracks for grid.
  const allTracks = useTracks(
    [
      { source: Track.Source.Camera, withPlaceholder: true },
      { source: Track.Source.ScreenShare, withPlaceholder: false },
    ],
    { onlySubscribed: false }
  );

  // Filter out service participants from the visible grid.
  //
  // The transcription agent (`accredit-agent`, livekit-agents framework)
  // joins as a regular participant — it subscribes to audio for STT but
  // never publishes camera or mic. With `withPlaceholder: true` above,
  // every non-publishing participant gets a blank tile labelled with
  // their identity, so the agent shows up as a ghost tile labelled
  // `agent-AJ_xxx`. The framework auto-prefixes its job participants
  // with `agent-` (or `AGENT-` in some versions); filtering on that
  // prefix is sufficient and future-proofs against any other system
  // participants we add later (recording bots, monitor tools, etc.).
  //
  // We don't try to set `hidden=true` on the agent server-side because
  // the LiveKit Python agent SDK doesn't expose a clean knob for it
  // and the frontend filter is the more robust ownership boundary
  // — the UI decides what to render in its grid; the agent worker
  // doesn't need to know about UI concerns.
  const tracks = useMemo(
    () =>
      allTracks.filter((t) => {
        const id = t.participant?.identity ?? '';
        return !/^agent[-_]/i.test(id);
      }),
    [allTracks]
  );

  if (!isHost && !admitted) {
    return <WaitingRoomView />;
  }

  return (
    <div className="flex h-full w-full flex-col">
      <TopBar
        isHost={isHost}
        roomUuid={roomUuid}
        initialRecordingActive={initialRecordingActive}
        recordingAutoManaged={recordingAutoManaged}
        waitingRoomEnabled={waitingRoomEnabled}
        onToggleChat={() => setChatOpen((v) => !v)}
        chatOpen={chatOpen}
        captionsEnabled={captionsEnabled}
        onToggleCaptions={handleToggleCaptions}
      />

      <div className="flex flex-1 min-h-0 overflow-hidden">
        <div className="flex flex-1 min-w-0 flex-col relative">
          <div className="flex-1 min-h-0 overflow-hidden">
            <GridLayout tracks={tracks} className="h-full w-full">
              <ParticipantTile />
            </GridLayout>
          </div>
          {/* Captions sit absolutely above the grid so they overlay the
              video without shifting the ControlBar. The overlay is
              pointer-events-none so clicks pass through to participant
              tiles. */}
          <CaptionOverlay enabled={captionsEnabled} />
          {/* `data-lk-theme="default"` injects the CSS variables the
              prefab ControlBar (and especially the .lk-device-menu
              popover) reads for background, border, and shadow. Without
              it the Microphone / Camera dropdowns render transparent and
              are barely visible against the video grid. Scoped to this
              wrapper so it doesn't leak dark colors into our chat
              sidebar or the rest of the app. */}
          {/* Bottom action row: device controls + our custom Leave.
              We disable the prefab Leave (`leave: false`) so we can run
              our own host-aware confirmation flow — see HostAwareLeaveButton.
              Without this, hosts who click LiveKit's stock Leave just
              disconnect with no warning, even though the backend's
              last-host-leave handler will end the meeting for everyone
              ~immediately after. The custom button surfaces that intent
              before the click commits. */}
          <div
            data-lk-theme="default"
            className="contents"
          >
            <div className="flex items-center gap-2 border-t border-border bg-[var(--lk-control-bg)] px-2 py-2">
              <div className="flex-1">
                <ControlBar
                  controls={{ chat: false, microphone: true, camera: true, screenShare: true, leave: false }}
                  className="!border-0 !p-0"
                />
              </div>
              <HostAwareLeaveButton roomUuid={roomUuid} />
            </div>
          </div>
        </div>

        {chatOpen && (
          <aside className="w-80 shrink-0 border-l border-border bg-background flex flex-col min-h-0">
            <div className="flex items-center justify-between p-2 border-b border-border">
              <span className="text-sm font-medium">Messages</span>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={() => setChatOpen(false)}
                aria-label="Close chat"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
            <div
              className={[
                'flex-1 min-h-0 overflow-hidden flex flex-col',
                // LiveKit's prefab Chat is styled for a fixed drawer; force
                // it to fill its container and drop decorative chrome that
                // duplicates our own (its own "Messages" header, border, etc).
                '[&_.lk-chat]:!static',
                '[&_.lk-chat]:!max-w-none',
                '[&_.lk-chat]:!border-0',
                '[&_.lk-chat]:!w-full',
                '[&_.lk-chat]:!h-full',
                '[&_.lk-chat]:!flex',
                '[&_.lk-chat]:!flex-col',
                '[&_.lk-chat]:!bg-transparent',
                '[&_.lk-chat-header]:!hidden',
                '[&_.lk-chat-messages]:!flex-1',
                '[&_.lk-chat-messages]:!overflow-y-auto',
                '[&_.lk-chat-messages]:!px-3',
                '[&_.lk-chat-messages]:!py-2',
                '[&_.lk-chat-form]:!p-2',
                '[&_.lk-chat-form]:!gap-2',
                '[&_.lk-chat-form]:!border-t',
                '[&_.lk-chat-form]:!border-border',
                '[&_.lk-chat-form-input]:!flex-1',
                '[&_.lk-chat-form-input]:!min-w-0',
              ].join(' ')}
            >
              <Chat />
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}

function WaitingRoomView() {
  return (
    <div className="flex h-full w-full items-center justify-center p-8">
      <div className="max-w-md text-center space-y-4">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-muted">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
        <h3 className="text-lg font-semibold">Waiting to be admitted</h3>
        <p className="text-sm text-muted-foreground">
          The host will let you in shortly. Please keep this window open.
        </p>
      </div>
    </div>
  );
}

interface TopBarProps {
  isHost: boolean;
  roomUuid?: string;
  initialRecordingActive: boolean;
  recordingAutoManaged: boolean;
  waitingRoomEnabled: boolean;
  onToggleChat: () => void;
  chatOpen: boolean;
  captionsEnabled: boolean;
  onToggleCaptions: () => void;
}

function TopBar({
  isHost,
  roomUuid,
  initialRecordingActive,
  recordingAutoManaged,
  waitingRoomEnabled,
  onToggleChat,
  chatOpen,
  captionsEnabled,
  onToggleCaptions,
}: TopBarProps) {
  const [recording, setRecording] = useState(initialRecordingActive);
  const [recordingBusy, setRecordingBusy] = useState(false);
  const [recordingError, setRecordingError] = useState<string | null>(null);

  const participants = useParticipants();
  const waitingParticipants = useMemo(
    () =>
      participants.filter(
        (p) => !p.isLocal && (p.permissions?.canPublish === false || p.permissions?.canSubscribe === false)
      ),
    [participants]
  );

  const [admitBusy, setAdmitBusy] = useState<Record<string, boolean>>({});

  const handleToggleRecording = useCallback(async () => {
    if (!roomUuid) {
      setRecordingError('Room id missing');
      return;
    }
    setRecordingBusy(true);
    setRecordingError(null);
    try {
      if (recording) {
        await stopRoomRecording(roomUuid);
        setRecording(false);
      } else {
        await startRoomRecording(roomUuid);
        setRecording(true);
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Recording action failed';
      setRecordingError(message);
    } finally {
      setRecordingBusy(false);
    }
  }, [roomUuid, recording]);

  const handleAdmit = useCallback(
    async (identity: string) => {
      if (!roomUuid) return;
      setAdmitBusy((s) => ({ ...s, [identity]: true }));
      try {
        await admitParticipant(roomUuid, identity);
      } finally {
        setAdmitBusy((s) => ({ ...s, [identity]: false }));
      }
    },
    [roomUuid]
  );

  const handleDeny = useCallback(
    async (identity: string) => {
      if (!roomUuid) return;
      setAdmitBusy((s) => ({ ...s, [identity]: true }));
      try {
        await denyParticipant(roomUuid, identity);
      } finally {
        setAdmitBusy((s) => ({ ...s, [identity]: false }));
      }
    },
    [roomUuid]
  );

  return (
    <div className="flex flex-col border-b border-border bg-muted/40">
      <div className="flex items-center gap-2 px-3 py-2">
        {isHost && (
          <>
            <Badge variant="outline" className="gap-1">
              <span className="inline-flex h-2 w-2 rounded-full bg-emerald-500" />
              Host
            </Badge>

            {/* When auto-managed, hide the manual Start button — the backend
                kicks off egress on room_started. The Stop button stays visible
                whenever recording is live, as a host override. */}
            {(!recordingAutoManaged || recording) && (
              <Button
                size="sm"
                variant={recording ? 'destructive' : 'default'}
                disabled={recordingBusy}
                onClick={handleToggleRecording}
                className="gap-2"
              >
                {recordingBusy ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : recording ? (
                  <Circle className="h-4 w-4 fill-current" />
                ) : (
                  <Circle className="h-4 w-4" />
                )}
                {recording ? 'Stop recording' : 'Start recording'}
              </Button>
            )}

            {recordingAutoManaged && !recording && (
              <span className="text-xs text-muted-foreground italic">
                Recording will start automatically.
              </span>
            )}

            {recording && (
              <Badge variant="destructive" className="gap-1">
                <span className="inline-flex h-2 w-2 rounded-full bg-red-200 animate-pulse" />
                REC
              </Badge>
            )}

            {recordingError && (
              <span className="text-xs text-destructive">{recordingError}</span>
            )}
          </>
        )}

        <div className="ml-auto flex items-center gap-2">
          <BackgroundEffectsPicker />
          {/* Captions toggle. Visible to everyone in the room — even
              attendees benefit from captions when an organiser hasn't
              configured a transcription provider per-event, the LiveKit
              data stream simply emits nothing and the overlay stays
              hidden. The button preference persists per-user in
              localStorage so accessibility settings stick. */}
          <Button
            size="sm"
            variant={captionsEnabled ? 'default' : 'ghost'}
            className="gap-2"
            onClick={onToggleCaptions}
            aria-pressed={captionsEnabled}
          >
            <Captions className="h-4 w-4" />
            {captionsEnabled ? 'Captions on' : 'Captions'}
          </Button>
          {isHost && roomUuid && (
            <EndMeetingButton roomUuid={roomUuid} />
          )}
          <Button size="sm" variant="ghost" className="gap-2" onClick={onToggleChat}>
            <MessageSquare className="h-4 w-4" />
            {chatOpen ? 'Hide chat' : 'Chat'}
          </Button>
        </div>
      </div>

      {isHost && waitingRoomEnabled && waitingParticipants.length > 0 && (
        <div className="flex flex-col gap-1 border-t border-border bg-background/60 px-3 py-2">
          <span className="text-xs font-medium text-muted-foreground">
            Waiting room ({waitingParticipants.length})
          </span>
          <ul className="flex flex-wrap gap-2">
            {waitingParticipants.map((p) => (
              <li
                key={p.identity}
                className="flex items-center gap-2 rounded-md border border-border bg-background px-2 py-1"
              >
                <span className="text-sm">{p.name || p.identity}</span>
                <Button
                  size="sm"
                  variant="default"
                  className="h-7 gap-1"
                  disabled={admitBusy[p.identity]}
                  onClick={() => handleAdmit(p.identity)}
                >
                  {admitBusy[p.identity] ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <UserCheck className="h-3 w-3" />
                  )}
                  Admit
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  className="h-7 gap-1"
                  disabled={admitBusy[p.identity]}
                  onClick={() => handleDeny(p.identity)}
                >
                  <UserX className="h-3 w-3" />
                  Deny
                </Button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}


/**
 * Host-only "End meeting for all" button.
 *
 * Lives in the TopBar next to the chat toggle. Triggers a confirmation
 * modal because this is the load-bearing destructive action of the
 * Zoom flow — clicking it boots every participant. The backend's
 * EndMeetingView calls LiveKit `delete_room`; the empty-room webhook
 * handler does the actual cleanup (stop recording, finalize transcript,
 * mark VideoRoom ENDED). The frontend's job is to fire the API call
 * and let the LiveKit client's `onDisconnected` hook close the dialog
 * naturally as the room evaporates.
 */
function EndMeetingButton({ roomUuid }: { roomUuid: string }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleEnd = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      await endMeeting(roomUuid);
      // No need to close the dialog manually — LiveKit will fire
      // onDisconnected within ~1s as it tears the room down, which
      // unmounts the parent <Dialog> entirely.
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to end the meeting.';
      setError(message);
      setBusy(false);
    }
  }, [roomUuid]);

  return (
    <>
      <Button
        size="sm"
        variant="destructive"
        className="gap-2"
        onClick={() => setOpen(true)}
        data-testid="end-meeting-trigger"
      >
        <PhoneOff className="h-4 w-4" />
        End meeting
      </Button>
      <Dialog open={open} onOpenChange={(o) => { if (!busy) setOpen(o); }}>
        <DialogContent data-testid="end-meeting-dialog">
          <DialogHeader>
            <DialogTitle>End meeting for everyone?</DialogTitle>
            <DialogDescription>
              All participants will be disconnected. The recording will stop and be saved.
              You can start a new meeting from the lobby afterwards.
            </DialogDescription>
          </DialogHeader>
          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)} disabled={busy}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleEnd}
              disabled={busy}
              data-testid="end-meeting-confirm"
            >
              {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <PhoneOff className="mr-2 h-4 w-4" />}
              End meeting
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}


/** Parse the LiveKit participant.metadata JSON, swallowing any malformed input.
 *
 * Backend stamps `{is_host: bool}` into participant metadata at JWT
 * issuance time (see `LiveKitProvider.generate_join_token`). LiveKit
 * propagates that string verbatim to every other client in the room,
 * so we can use it to distinguish hosts from attendees on the
 * receiving side without round-tripping back to the API.
 */
function parseParticipantMetadata(metadata: string | undefined): { is_host?: boolean } {
  if (!metadata) return {};
  try {
    const parsed = JSON.parse(metadata);
    return typeof parsed === 'object' && parsed !== null ? parsed : {};
  } catch {
    return {};
  }
}


/**
 * Custom Leave button that warns the host before they leave the room
 * if they're the *only* host in it.
 *
 * Why it exists: LiveKit's prefab Leave button (`controls.leave`) just
 * disconnects the local participant, with no awareness of the host
 * lifecycle. The backend's last-host-leave handler (`tasks.py
 * _maybe_auto_end_on_last_host_leave`) ends the meeting for everyone
 * within ~1s of the host disconnecting — but the host had no warning,
 * which is jarring.
 *
 * Behaviour:
 *   - non-host attendee → unstyled Leave (just disconnect)
 *   - host with at least one OTHER host present → "Leave (meeting
 *     continues)" — disconnects them, the meeting stays up under the
 *     remaining host
 *   - host with no other host present (the common case) → confirmation
 *     modal "You're the only host. End the meeting for everyone?"
 *     - End meeting → calls `endMeeting(roomUuid)` (clean teardown via
 *       provider.delete_room → room_finished webhook → recordings
 *       finalised, transcript flushed, row marked ENDED). Then
 *       LiveKit's onDisconnected fires and the dialog unmounts.
 *     - Cancel → no-op, host stays in the meeting
 *
 * Other-host detection uses participant.metadata.is_host, which the
 * backend stamps at token-issuance time. Service participants
 * (transcription agent etc.) are filtered out via the same
 * `agent[-_]` regex used elsewhere — they don't have host privileges
 * either way, but the explicit filter is defensive.
 */
function HostAwareLeaveButton({ roomUuid }: { roomUuid: string | undefined }) {
  const { localParticipant } = useLocalParticipant();
  const participants = useParticipants();
  const room = useRoomContext();

  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const localIsHost = useMemo(
    () => !!parseParticipantMetadata(localParticipant?.metadata).is_host,
    [localParticipant?.metadata],
  );

  // "Last host" = local user is host AND no other non-service participant
  // also has is_host=true. We don't currently support co-hosts in the
  // production flow, but the predicate handles them correctly if added
  // later via the existing is_event_host server-side check.
  const isLastHost = useMemo(() => {
    if (!localIsHost) return false;
    return !participants.some((p) => {
      if (p.isLocal) return false;
      if (/^agent[-_]/i.test(p.identity ?? '')) return false;
      return !!parseParticipantMetadata(p.metadata).is_host;
    });
  }, [participants, localIsHost]);

  const disconnectQuietly = useCallback(() => {
    // Same as LiveKit's stock Leave: tears down the local connection.
    // Other participants stay; the meeting continues if anyone is left.
    void room?.disconnect();
  }, [room]);

  const handleClick = useCallback(() => {
    if (isLastHost && roomUuid) {
      setError(null);
      setOpen(true);
    } else {
      disconnectQuietly();
    }
  }, [isLastHost, roomUuid, disconnectQuietly]);

  const handleEndForEveryone = useCallback(async () => {
    if (!roomUuid) return;
    setBusy(true);
    setError(null);
    try {
      await endMeeting(roomUuid);
      // The room_finished webhook will tear LiveKit down; client's
      // onDisconnected fires and unmounts the dialog. No manual close.
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to end the meeting.';
      setError(message);
      setBusy(false);
    }
  }, [roomUuid]);

  // For non-hosts and hosts-with-co-hosts: just LiveKit's red "Leave"
  // button shape, no warning needed. We use the same `lk-disconnect-button`
  // class so it matches the prefab's appearance pixel-for-pixel.
  return (
    <>
      <Button
        size="sm"
        variant="destructive"
        className="gap-2"
        onClick={handleClick}
        data-testid="leave-meeting-trigger"
      >
        <LogOut className="h-4 w-4" />
        Leave
      </Button>
      <Dialog open={open} onOpenChange={(o) => { if (!busy) setOpen(o); }}>
        <DialogContent data-testid="leave-meeting-dialog">
          <DialogHeader>
            <DialogTitle>You're the only host</DialogTitle>
            <DialogDescription>
              If you leave, the meeting will end for everyone — the recording
              will stop and be saved. If you want to step away briefly,
              cancel and stay in the meeting; another host can take over only
              after they join.
            </DialogDescription>
          </DialogHeader>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)} disabled={busy}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleEndForEveryone}
              disabled={busy}
              data-testid="leave-meeting-confirm-end"
            >
              {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <PhoneOff className="mr-2 h-4 w-4" />}
              End meeting for everyone
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
