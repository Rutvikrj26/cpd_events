import { useEffect, useMemo, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { ArrowLeft, AlertCircle } from 'lucide-react';

import { Button } from '@/shared/ui/button';
import { Card, CardContent } from '@/shared/ui/card';
import { Skeleton } from '@/shared/ui/skeleton';
import { getVideoRecordings } from '@/api/video';
import type { VideoRecording } from '@/api/video/types';
import { getPublicEvent } from '@/api/events';
import type { Event } from '@/api/events/types';
import { TranscriptPanel } from '@/components/recording/TranscriptPanel';

export function EventRecordingPage() {
  const { id: eventUuid, recordingUuid } = useParams<{ id: string; recordingUuid?: string }>();

  const [event, setEvent] = useState<Event | null>(null);
  const [recordings, setRecordings] = useState<VideoRecording[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  // Shared ref between the <video> element and the TranscriptPanel.
  // The panel reads currentTime via timeupdate listeners and writes
  // it back when the user clicks a segment to seek.
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    if (!eventUuid) return;
    let cancelled = false;
    setLoading(true);
    setError(null);

    // The :id route segment may be either a UUID or a slug. `getPublicEvent`
    // accepts both, but `getVideoRecordings({event_uuid})` only accepts a
    // UUID — so we resolve the event first, then use its `.uuid` for the
    // recordings query. Wrapping each fetch with a request-level `silent`
    // hint keeps the global error toast quiet for the expected "no
    // recording yet" case.
    (async () => {
      const ev = await getPublicEvent(eventUuid).catch(() => null);
      if (cancelled) return;
      setEvent(ev);

      const realUuid = ev?.uuid ?? eventUuid;
      const recs = await getVideoRecordings({ event_uuid: realUuid }).catch(
        () => [] as VideoRecording[],
      );
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

  // If the URL specifies a recordingUuid, render exactly that one. Otherwise
  // fall back to the most recently published recording.
  const recording = useMemo(() => {
    if (!recordings.length) return null;
    if (recordingUuid) {
      return recordings.find((r) => r.uuid === recordingUuid) ?? null;
    }
    return [...recordings].sort((a, b) => {
      const ax = a.published_at || a.created_at;
      const bx = b.published_at || b.created_at;
      return new Date(bx).getTime() - new Date(ax).getTime();
    })[0];
  }, [recordings, recordingUuid]);

  // Pick the first available video file.
  const videoFile = useMemo(() => {
    if (!recording) return null;
    return recording.files.find((f) => f.file_type === 'video') ?? null;
  }, [recording]);

  if (loading) {
    return (
      <div className="mx-auto max-w-4xl p-6 space-y-4">
        <Skeleton className="h-10 w-2/3" />
        <Skeleton className="h-[420px] w-full" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl p-6 space-y-6">
      <div>
        <Button variant="ghost" size="sm" onClick={() => window.history.length > 1 ? window.history.back() : window.location.assign('/my-events')}>
          <ArrowLeft className="mr-2 h-4 w-4" /> Back
        </Button>
      </div>

      <header className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">
          {event?.title ?? 'Event recording'}
        </h1>
        {recording && (
          <p className="text-sm text-muted-foreground">
            Recorded {recording.recording_end
              ? new Date(recording.recording_end).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
              : 'recently'}
            {recording.duration_display && ` · ${recording.duration_display}`}
          </p>
        )}
      </header>

      {!recording ? (
        <Card>
          <CardContent className="p-8 text-center space-y-3">
            <AlertCircle className="mx-auto h-10 w-10 text-amber-500" />
            <h2 className="text-lg font-semibold">No recording available yet</h2>
            <p className="text-sm text-muted-foreground">
              {error ?? "If the session was recorded, it'll appear here once processing finishes and the organizer publishes it."}
            </p>
          </CardContent>
        </Card>
      ) : recording.status === 'recording' ? (
        <Card>
          <CardContent className="p-8 text-center space-y-3">
            <AlertCircle className="mx-auto h-10 w-10 text-red-500" />
            <h2 className="text-lg font-semibold">Live recording in progress</h2>
            <p className="text-sm text-muted-foreground">
              The session is still being recorded. Check back when the event ends.
            </p>
          </CardContent>
        </Card>
      ) : recording.status === 'processing' ? (
        <Card>
          <CardContent className="p-8 text-center space-y-3">
            <AlertCircle className="mx-auto h-10 w-10 text-amber-500" />
            <h2 className="text-lg font-semibold">Processing recording</h2>
            <p className="text-sm text-muted-foreground">
              The recording is being finalized. This usually takes a few minutes; refresh shortly.
            </p>
          </CardContent>
        </Card>
      ) : recording.status === 'error' ? (
        <Card>
          <CardContent className="p-8 text-center space-y-3">
            <AlertCircle className="mx-auto h-10 w-10 text-destructive" />
            <h2 className="text-lg font-semibold">Recording failed</h2>
            <p className="text-sm text-muted-foreground">
              We couldn't capture this session's recording. Please contact the organizer.
            </p>
          </CardContent>
        </Card>
      ) : !videoFile ? (
        <Card>
          <CardContent className="p-8 text-center space-y-3">
            <AlertCircle className="mx-auto h-10 w-10 text-amber-500" />
            <h2 className="text-lg font-semibold">Recording isn't ready</h2>
            <p className="text-sm text-muted-foreground">
              Status: {recording.status}. Try again in a few minutes.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[2fr_1fr]">
          <Card>
            <CardContent className="p-0">
              {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
              <video
                ref={videoRef}
                key={videoFile.uuid}
                src={videoFile.storage_url}
                controls
                preload="metadata"
                className="w-full rounded-md"
                style={{ maxHeight: '70vh', backgroundColor: 'black' }}
              />
              <div className="p-4 text-sm text-muted-foreground">
                <a href={videoFile.storage_url} download={videoFile.file_name} className="underline">
                  Download {videoFile.file_name}
                </a>
              </div>
            </CardContent>
          </Card>
          {/* Transcript panel — fetches its own data via react-query;
              renders nothing meaningful when no transcript exists. The
              parent (this page) doesn't gate on transcript existence
              because the panel handles the empty/error states inline. */}
          <div className="lg:max-h-[80vh] lg:sticky lg:top-4">
            <TranscriptPanel
              recordingUuid={recording.uuid}
              videoRef={videoRef}
              // Server-computed: owner / staff / admin → can edit. The
              // backend re-checks the same predicate on PATCH; surfacing
              // the affordance via the same flag keeps both sides
              // consistent without an extra round-trip.
              canEdit={!!event?.is_current_user_host}
            />
          </div>
        </div>
      )}
    </div>
  );
}
