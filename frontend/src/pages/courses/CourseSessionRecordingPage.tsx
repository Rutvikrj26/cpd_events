import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, AlertCircle } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { getVideoRecordings } from '@/api/video';
import type { VideoRecording } from '@/api/video/types';
import {
    getCourseBySlug, getCourseSession, getRecordingView, postRecordingView,
} from '@/api/courses';
import type { Course, CourseSession } from '@/api/courses/types';

const TRACKING_THROTTLE_MS = 15_000;

export function CourseSessionRecordingPage() {
    const { slug, sessionUuid } = useParams<{ slug: string; sessionUuid: string }>();

    const [course, setCourse] = useState<Course | null>(null);
    const [session, setSession] = useState<CourseSession | null>(null);
    const [recordings, setRecordings] = useState<VideoRecording[]>([]);
    const [resumeAt, setResumeAt] = useState<number | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);

    const videoRef = useRef<HTMLVideoElement | null>(null);
    const lastPostMs = useRef<number>(0);

    useEffect(() => {
        if (!slug || !sessionUuid) return;
        let cancelled = false;
        setLoading(true);
        setError(null);
        (async () => {
            try {
                const c = await getCourseBySlug(slug);
                if (!c) throw new Error('Course not found.');
                const [s, recs, view] = await Promise.all([
                    getCourseSession(c.uuid, sessionUuid),
                    getVideoRecordings({ course_session_uuid: sessionUuid }).catch(() => [] as VideoRecording[]),
                    getRecordingView(c.uuid, sessionUuid).catch(() => null),
                ]);
                if (cancelled) return;
                setCourse(c);
                setSession(s);
                setRecordings(recs);
                setResumeAt(view?.last_position_seconds ?? 0);
            } catch (err) {
                if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load recording.');
            } finally {
                if (!cancelled) setLoading(false);
            }
        })();
        return () => {
            cancelled = true;
        };
    }, [slug, sessionUuid]);

    // Pick the most recently published recording.
    const recording = useMemo(() => {
        if (!recordings.length) return null;
        return [...recordings].sort((a, b) => {
            const ax = a.published_at || a.created_at;
            const bx = b.published_at || b.created_at;
            return new Date(bx).getTime() - new Date(ax).getTime();
        })[0];
    }, [recordings]);

    const videoFile = useMemo(() => {
        if (!recording) return null;
        return recording.files.find((f) => f.file_type === 'video') ?? null;
    }, [recording]);

    // Seed currentTime once metadata is available.
    const handleLoadedMetadata = () => {
        if (videoRef.current && resumeAt && resumeAt > 0) {
            try {
                videoRef.current.currentTime = resumeAt;
            } catch {
                // older browsers + non-seekable streams: best-effort
            }
        }
    };

    // Throttled progress upsert. Per D3 in
    // docs/design/hybrid-course-experience.md, this never flips
    // CourseSessionAttendance.is_eligible — pure tracking.
    const handleTimeUpdate = () => {
        if (!course || !sessionUuid || !videoRef.current) return;
        const now = Date.now();
        if (now - lastPostMs.current < TRACKING_THROTTLE_MS) return;
        lastPostMs.current = now;
        const seconds = Math.floor(videoRef.current.currentTime);
        postRecordingView(course.uuid, sessionUuid, {
            watch_seconds: seconds,
            last_position_seconds: seconds,
        }).catch(() => {
            // Tracking is best-effort — never block playback on a 4xx/5xx.
        });
    };

    const handleEnded = () => {
        if (!course || !sessionUuid || !videoRef.current) return;
        const total = Math.floor(videoRef.current.duration || 0);
        postRecordingView(course.uuid, sessionUuid, {
            watch_seconds: total,
            last_position_seconds: 0,
            completed: true,
        }).catch(() => {});
    };

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
                    <Link to={course ? `/learn/${course.uuid}` : '/registrations?tab=courses'}>
                        <ArrowLeft className="mr-2 h-4 w-4" />
                        {course ? `Back to ${course.title}` : 'Back to My Learning'}
                    </Link>
                </Button>
            </div>

            <header className="space-y-2">
                <h1 className="text-3xl font-semibold tracking-tight">
                    {session?.title ?? 'Session recording'}
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
                            {error ?? 'If a recording was captured, it may still be processing or has not been published yet.'}
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
                            ref={videoRef}
                            key={videoFile.uuid}
                            src={videoFile.storage_url}
                            controls
                            preload="metadata"
                            onLoadedMetadata={handleLoadedMetadata}
                            onTimeUpdate={handleTimeUpdate}
                            onEnded={handleEnded}
                            className="w-full rounded-md"
                            style={{ maxHeight: '70vh', backgroundColor: 'black' }}
                        />
                        <div className="p-4 text-sm text-muted-foreground flex items-center justify-between flex-wrap gap-2">
                            <a href={videoFile.storage_url} download={videoFile.file_name} className="underline">
                                Download {videoFile.file_name}
                            </a>
                            <span className="text-xs">
                                Recording playback is tracked for instructor analytics. Live attendance is the only path to credit.
                            </span>
                        </div>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
