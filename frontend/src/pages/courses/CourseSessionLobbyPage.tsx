import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { AlertCircle, ArrowLeft } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { JoinButton } from '@/components/video/JoinButton';
import { LiveSessionLobby } from '@/components/live/LiveSessionLobby';
import { getCourseBySlug, getCourseSession } from '@/api/courses';
import type { Course, CourseSession } from '@/api/courses/types';
import { isWithinJoinWindow } from '@/lib/liveSession';

export function CourseSessionLobbyPage() {
    const { slug, sessionUuid } = useParams<{ slug: string; sessionUuid: string }>();
    const [course, setCourse] = useState<Course | null>(null);
    const [session, setSession] = useState<CourseSession | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!slug || !sessionUuid) return;
        let cancelled = false;
        setLoading(true);
        setError(null);
        (async () => {
            try {
                const c = await getCourseBySlug(slug);
                if (!c) throw new Error('Course not found.');
                const s = await getCourseSession(c.uuid, sessionUuid);
                if (!cancelled) {
                    setCourse(c);
                    setSession(s);
                }
            } catch (err) {
                if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load session.');
            } finally {
                if (!cancelled) setLoading(false);
            }
        })();
        return () => {
            cancelled = true;
        };
    }, [slug, sessionUuid]);

    if (loading) {
        return (
            <div className="mx-auto max-w-3xl p-6 space-y-4">
                <Skeleton className="h-10 w-2/3" />
                <Skeleton className="h-32 w-full" />
                <Skeleton className="h-48 w-full" />
            </div>
        );
    }

    if (error || !course || !session) {
        return (
            <div className="mx-auto max-w-3xl p-6">
                <Card>
                    <CardContent className="p-8 text-center space-y-3">
                        <AlertCircle className="mx-auto h-10 w-10 text-rose-500" />
                        <h1 className="text-xl font-semibold">Couldn't load this session</h1>
                        <p className="text-sm text-muted-foreground">{error ?? 'Please check the link and try again.'}</p>
                        <Button asChild variant="outline">
                            <Link to="/registrations?tab=courses">
                                <ArrowLeft className="mr-2 h-4 w-4" />
                                My Learning
                            </Link>
                        </Button>
                    </CardContent>
                </Card>
            </div>
        );
    }

    const now = new Date();
    const starts = new Date(session.starts_at);
    const ends = session.ends_at ? new Date(session.ends_at) :
        new Date(starts.getTime() + (session.duration_minutes ?? 0) * 60_000);
    const isPast = now >= ends || session.status === 'completed';
    const canJoinNow = isWithinJoinWindow(session, now);
    const isInPerson = session.delivery_mode === 'in_person';

    // In-person sessions skip the JoinButton entirely (no video stream).
    // Hybrid sessions still get the button — remote attendees join via video.
    // Hosts (course creator, staff, platform admin) can start any time, regardless of join window.
    const isHost = !!course.is_current_user_host;
    const joinSlot = !isInPerson ? (
        <JoinButton
            courseUuid={course.uuid}
            sessionUuid={session.uuid}
            role={isHost ? 'host' : 'attendee'}
            state={isHost ? (canJoinNow ? 'live' : 'pre_event') : (canJoinNow ? 'in_window' : 'pre_event')}
            size="lg"
        />
    ) : null;

    const hasRecording = !!(session as any).recording;

    return (
        <LiveSessionLobby
            title={session.title}
            description={session.description}
            startsAt={session.starts_at}
            endsAt={ends.toISOString()}
            timezone={session.timezone}
            durationMinutes={session.duration_minutes ?? 60}
            status={session.status as any}
            deliveryMode={session.delivery_mode}
            canJoinNow={canJoinNow}
            isPast={isPast}
            joinSlot={joinSlot}
            backLink={{ to: `/learn/${course.uuid}`, label: `Back to ${course.title}` }}
            recordingLink={isPast && hasRecording ? {
                to: `/courses/${course.slug}/sessions/${session.uuid}/recording`,
            } : undefined}
        />
    );
}
