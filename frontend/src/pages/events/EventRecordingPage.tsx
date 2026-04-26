import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, AlertCircle } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { getVideoRecordings } from '@/api/video';
import type { VideoRecording } from '@/api/video/types';
import { getPublicEvent } from '@/api/events';
import type { Event } from '@/api/events/types';

export function EventRecordingPage() {
  const { id: eventUuid } = useParams<{ id: string }>();

  const [event, setEvent] = useState<Event | null>(null);
  const [recordings, setRecordings] = useState<VideoRecording[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!eventUuid) return;
    let cancelled = false;
    setLoading(true);
    setError(null);

    Promise.all([
      getPublicEvent(eventUuid).catch(() => null),
      getVideoRecordings({ event_uuid: eventUuid }).catch(() => [] as VideoRecording[]),
    ]).then(([ev, recs]) => {
      if (cancelled) return;
      setEvent(ev);
      setRecordings(recs);
      setLoading(false);
    }).catch((err) => {
      if (!cancelled) {
        setError(err instanceof Error ? err.message : 'Failed to load recording.');
        setLoading(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [eventUuid]);

  // Pick the most recently published recording for this event.
  const recording = useMemo(() => {
    if (!recordings.length) return null;
    return [...recordings].sort((a, b) => {
      const ax = a.published_at || a.created_at;
      const bx = b.published_at || b.created_at;
      return new Date(bx).getTime() - new Date(ax).getTime();
    })[0];
  }, [recordings]);

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
        <Button asChild variant="ghost" size="sm">
          <Link to="/my-events">
            <ArrowLeft className="mr-2 h-4 w-4" /> Back to My Events
          </Link>
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
        <Card>
          <CardContent className="p-0">
            {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
            <video
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
      )}
    </div>
  );
}
