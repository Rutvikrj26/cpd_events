import {
  LiveKitRoom,
  RoomAudioRenderer,
  GridLayout,
  ParticipantTile,
  ControlBar,
  Chat,
  useLocalParticipant,
  useParticipants,
  useTracks,
} from '@livekit/components-react';
import '@livekit/components-styles';
import { Track } from 'livekit-client';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { AlertCircle, Circle, Loader2, MessageSquare, UserCheck, UserX, X } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { BackgroundEffectsPicker } from '@/components/video/BackgroundEffectsPicker';
import {
  admitParticipant,
  denyParticipant,
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
  const tracks = useTracks(
    [
      { source: Track.Source.Camera, withPlaceholder: true },
      { source: Track.Source.ScreenShare, withPlaceholder: false },
    ],
    { onlySubscribed: false }
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
      />

      <div className="flex flex-1 min-h-0 overflow-hidden">
        <div className="flex flex-1 min-w-0 flex-col">
          <div className="flex-1 min-h-0 overflow-hidden">
            <GridLayout tracks={tracks} className="h-full w-full">
              <ParticipantTile />
            </GridLayout>
          </div>
          <ControlBar
            controls={{ chat: false, microphone: true, camera: true, screenShare: true, leave: true }}
            className="!border-t !border-border"
          />
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
}

function TopBar({
  isHost,
  roomUuid,
  initialRecordingActive,
  recordingAutoManaged,
  waitingRoomEnabled,
  onToggleChat,
  chatOpen,
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
