import { useEffect, useMemo, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, AlertCircle, Download, PlayCircle } from 'lucide-react';

import { cn } from '@/lib/utils';
import { Button } from '@/shared/ui/button';
import { Card, CardContent } from '@/shared/ui/card';
import { Skeleton } from '@/shared/ui/skeleton';
import { MediaPlayer, type MediaPlayerHandle } from '@/shared/media';
import { detectMediaSource } from '@/shared/media/lib/detectSource';
import { RecordingTranscriptAdapter } from '@/components/recording/RecordingTranscriptAdapter';
import { getVideoRecordings } from '@/api/video';
import type { VideoRecording } from '@/api/video/types';
import { getPublicEvent } from '@/api/events';
import type { Event } from '@/api/events/types';

export function EventRecordingPage() {
  const { id: eventUuid, recordingUuid } = useParams<{ id: string; recordingUuid?: string }>();
  const navigate = useNavigate();

  const [event, setEvent] = useState<Event | null>(null);
  const [recordings, setRecordings] = useState<VideoRecording[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  // Imperative handle exposed by <MediaPlayer> — used by the transcript
  // adapter to seek when a segment row is clicked. The adapter also
  // reads currentTime via local state driven by the player's onTimeUpdate
  // callback (see below).
  const playerRef = useRef<MediaPlayerHandle>(null);
  const [currentMs, setCurrentMs] = useState(0);

  useEffect(() => {
    if (!eventUuid) return;
    let cancelled = false;

    // The :id route segment may be either a UUID or a slug. `getPublicEvent`
    // accepts both, but `getVideoRecordings({event_uuid})` only accepts a
    // UUID — so we resolve the event first, then use its `.uuid` for the
    // recordings query. Hosts/admins request `manage=true` so they receive
    // unpublished + still-processing rows for review before publishing.
    (async () => {
      if (cancelled) return;
      const ev = await getPublicEvent(eventUuid).catch(() => null);
      if (cancelled) return;
      setEvent(ev);

      const realUuid = ev?.uuid ?? eventUuid;
      const isHost = !!ev?.is_current_user_host;
      const recs = await getVideoRecordings({
        event_uuid: realUuid,
        manage: isHost,
      }).catch(() => [] as VideoRecording[]);
      if (cancelled) return;
      setRecordings(recs);
      setLoading(false);
    })().catch((err) => {
      if (!cancelled) {
        setError(err instanceof Error ? err.message : 'Failed to load recording.');
        setLoading(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [eventUuid]);

  // Sort recordings by recency (most-recently-recorded first). When the URL
  // omits a specific recordingUuid we pick the first; the picker below
  // renders all of them so the user can switch.
  const sortedRecordings = useMemo(() => {
    return [...recordings].sort((a, b) => {
      const ax = a.recording_end || a.published_at || a.created_at;
      const bx = b.recording_end || b.published_at || b.created_at;
      return new Date(bx).getTime() - new Date(ax).getTime();
    });
  }, [recordings]);

  const recording = useMemo(() => {
    if (!sortedRecordings.length) return null;
    if (recordingUuid) {
      return sortedRecordings.find((r) => r.uuid === recordingUuid) ?? null;
    }
    return sortedRecordings[0];
  }, [sortedRecordings, recordingUuid]);

  const eventSlugOrUuid = event?.slug || eventUuid;
  const switchRecording = (uuid: string) => {
    navigate(`/events/${eventSlugOrUuid}/recording/${uuid}`, { replace: true });
  };

  // Pick the first available video file.
  const videoFile = useMemo(() => {
    if (!recording) return null;
    return recording.files.find((f) => f.file_type === 'video') ?? null;
  }, [recording]);

  if (loading) {
    return (
      <div className="mx-auto max-w-7xl space-y-4 p-6">
        <Skeleton className="h-10 w-2/3" />
        <Skeleton className="h-[420px] w-full" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6">
      <div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() =>
            window.history.length > 1
              ? window.history.back()
              : window.location.assign('/registrations?tab=events')
          }
        >
          <ArrowLeft className="mr-2 h-4 w-4" /> Back
        </Button>
      </div>

      <header className="space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-3xl font-semibold tracking-tight">
            {event?.title ?? 'Event recording'}
          </h1>
          {/* Host-only preview badge: appears when the active recording
              has not been published yet, so organizers know what learners
              currently see (nothing) vs. what they're previewing. */}
          {recording && !recording.is_published && (
            <span className="inline-flex items-center rounded-full border border-amber-300 bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-800 dark:border-amber-500/40 dark:bg-amber-950/30 dark:text-amber-200">
              Unpublished — preview only
            </span>
          )}
        </div>
        {recording && (
          <p className="text-sm text-muted-foreground">
            Recorded{' '}
            {recording.recording_end
              ? new Date(recording.recording_end).toLocaleString(undefined, {
                  dateStyle: 'medium',
                  timeStyle: 'short',
                })
              : 'recently'}
            {recording.duration_display && ` · ${recording.duration_display}`}
            {sortedRecordings.length > 1 && (
              <>
                {' · '}
                {sortedRecordings.findIndex((r) => r.uuid === recording.uuid) + 1} of{' '}
                {sortedRecordings.length}
              </>
            )}
          </p>
        )}
      </header>

      {/* Recording picker — only when more than one published recording.
          Each card represents an independent recording (typically: one per
          live session, or per re-record). Click switches the active
          recording via URL replace so the back button doesn't trap you on
          a stale view. */}
      {sortedRecordings.length > 1 && (
        <div className="-mx-1 flex gap-2 overflow-x-auto px-1 pb-1">
          {sortedRecordings.map((rec, idx) => {
            const isActive = rec.uuid === recording?.uuid;
            return (
              <button
                key={rec.uuid}
                type="button"
                onClick={() => switchRecording(rec.uuid)}
                className={cn(
                  'flex min-w-[200px] shrink-0 items-start gap-2 rounded-md border p-3 text-left transition-colors',
                  isActive
                    ? 'border-primary bg-primary/5'
                    : 'border-border bg-card hover:bg-muted/50',
                )}
              >
                <PlayCircle
                  className={cn(
                    'mt-0.5 h-4 w-4 shrink-0',
                    isActive ? 'text-primary' : 'text-muted-foreground',
                  )}
                />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5">
                    <div className="text-sm font-medium">
                      Recording {idx + 1}
                    </div>
                    {!rec.is_published && (
                      <span
                        className="inline-block h-1.5 w-1.5 rounded-full bg-amber-500"
                        title="Unpublished — only you can see this"
                      />
                    )}
                  </div>
                  <div className="truncate text-xs text-muted-foreground">
                    {rec.recording_end
                      ? new Date(rec.recording_end).toLocaleString(undefined, {
                          dateStyle: 'medium',
                          timeStyle: 'short',
                        })
                      : 'Date unknown'}
                  </div>
                  {rec.duration_display && (
                    <div className="text-xs text-muted-foreground">
                      {rec.duration_display}
                    </div>
                  )}
                </div>
              </button>
            );
          })}
        </div>
      )}

      {!recording ? (
        <Card>
          <CardContent className="space-y-3 p-8 text-center">
            <AlertCircle className="mx-auto h-10 w-10 text-amber-500" />
            <h2 className="text-lg font-semibold">No recording available yet</h2>
            <p className="text-sm text-muted-foreground">
              {error ??
                "If the session was recorded, it'll appear here once processing finishes and the organizer publishes it."}
            </p>
          </CardContent>
        </Card>
      ) : recording.status === 'recording' ? (
        <Card>
          <CardContent className="space-y-3 p-8 text-center">
            <AlertCircle className="mx-auto h-10 w-10 text-red-500" />
            <h2 className="text-lg font-semibold">Live recording in progress</h2>
            <p className="text-sm text-muted-foreground">
              The session is still being recorded. Check back when the event ends.
            </p>
          </CardContent>
        </Card>
      ) : recording.status === 'processing' ? (
        <Card>
          <CardContent className="space-y-3 p-8 text-center">
            <AlertCircle className="mx-auto h-10 w-10 text-amber-500" />
            <h2 className="text-lg font-semibold">Processing recording</h2>
            <p className="text-sm text-muted-foreground">
              The recording is being finalized. This usually takes a few minutes; refresh shortly.
            </p>
          </CardContent>
        </Card>
      ) : recording.status === 'error' ? (
        <Card>
          <CardContent className="space-y-3 p-8 text-center">
            <AlertCircle className="mx-auto h-10 w-10 text-destructive" />
            <h2 className="text-lg font-semibold">Recording failed</h2>
            <p className="text-sm text-muted-foreground">
              We couldn't capture this session's recording. Please contact the organizer.
            </p>
          </CardContent>
        </Card>
      ) : !videoFile ? (
        <Card>
          <CardContent className="space-y-3 p-8 text-center">
            <AlertCircle className="mx-auto h-10 w-10 text-amber-500" />
            <h2 className="text-lg font-semibold">Recording isn't ready</h2>
            <p className="text-sm text-muted-foreground">
              Status: {recording.status}. Try again in a few minutes.
            </p>
          </CardContent>
        </Card>
      ) : (
        <MediaPlayer
          ref={playerRef}
          source={detectMediaSource(videoFile.storage_url)}
          title={event?.title}
          storageKey={`recording:${recording.uuid}`}
          layout="auto"
          onTimeUpdate={(s) => setCurrentMs(Math.floor(s * 1000))}
          transcript={{
            slot: (
              <RecordingTranscriptAdapter
                recordingUuid={recording.uuid}
                currentMs={currentMs}
                onSeek={(s) => playerRef.current?.seekTo(s)}
                canEdit={!!event?.is_current_user_host}
              />
            ),
          }}
          footer={
            <a
              href={videoFile.storage_url}
              download={videoFile.file_name}
              className="inline-flex items-center gap-1.5 text-sm text-muted-foreground underline-offset-2 hover:underline"
            >
              <Download className="h-3.5 w-3.5" />
              Download {videoFile.file_name}
            </a>
          }
        />
      )}
    </div>
  );
}
