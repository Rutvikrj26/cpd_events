// Shared lobby presentation for any live session (Event or CourseSession).
// Pure presentational — callers fetch their own data and pass the join slot
// (already-configured JoinButton) plus normalized session metadata.
//
// Per docs/design/hybrid-course-experience.md §A.

import { Link } from 'react-router-dom';
import { Calendar, MapPin, Users, AlertCircle, ArrowLeft } from 'lucide-react';
import type { ReactNode } from 'react';

import { Button } from '@/shared/ui/button';
import { Card, CardContent } from '@/shared/ui/card';
import { AddToCalendar } from '@/components/events/AddToCalendar';
import { EventCountdown } from '@/components/events/EventCountdown';

export interface LiveSessionLobbyProps {
    title: string;
    description?: string;
    startsAt: string;
    endsAt: string;
    timezone?: string;
    durationMinutes: number;
    location?: string;
    /** Used for the "Registered" tile when applicable (events). Course
        sessions can omit this. */
    registrationCount?: number;
    maxAttendees?: number;
    status: 'scheduled' | 'live' | 'completed' | 'cancelled' | 'closed' | 'draft' | 'published';
    deliveryMode?: 'online' | 'in_person' | 'hybrid';
    /**
     * True only when an actual meeting room is live right now (host has
     * clicked Start and the room is ACTIVE/SCHEDULED). When false, the
     * lobby suppresses the green "Live now" countdown pill — even if
     * `status==='live'` (which is schedule-driven and stays true for
     * the entire scheduled window). Without this we'd show two
     * conflicting signals: a green "Live now" pill alongside a
     * disabled "Meeting has ended" / "Waiting for host" join button.
     * Callers that don't poll meeting state can leave it undefined;
     * the pill falls back to status-driven behaviour.
     */
    meetingActive?: boolean;
    /** True iff the join window has opened and the session isn't past. */
    canJoinNow: boolean;
    /** True iff the session has ended. Hides the join slot, shows recording link. */
    isPast: boolean;
    /** Pre-built JoinButton (or null for in-person sessions). */
    joinSlot: ReactNode;
    backLink: { to: string; label: string };
    recordingLink?: { to: string };
    /** Optional extra cards (guest registration card, lobby banners, etc.). */
    additionalCards?: ReactNode;
}

function fmtDate(iso: string): string {
    return new Date(iso).toLocaleString(undefined, { dateStyle: 'long', timeStyle: 'short' });
}

export function LiveSessionLobby({
    title,
    description,
    startsAt,
    endsAt,
    timezone,
    durationMinutes,
    location,
    registrationCount,
    maxAttendees,
    status,
    deliveryMode,
    meetingActive,
    canJoinNow,
    isPast,
    joinSlot,
    backLink,
    recordingLink,
    additionalCards,
}: LiveSessionLobbyProps) {
    const isCancelled = status === 'cancelled';

    return (
        <div className="mx-auto max-w-3xl p-6 space-y-6">
            <div>
                <Button asChild variant="ghost" size="sm">
                    <Link to={backLink.to}>
                        <ArrowLeft className="mr-2 h-4 w-4" /> {backLink.label}
                    </Link>
                </Button>
            </div>

            <header className="space-y-2">
                <h1 className="text-3xl font-semibold tracking-tight">{title}</h1>
                {description && (
                    <p className="text-muted-foreground">{description}</p>
                )}
            </header>

            <EventCountdown
                startsAt={startsAt}
                endsAt={endsAt}
                status={status as any}
                meetingLive={meetingActive}
                className="w-full max-w-md"
            />

            {isCancelled && (
                <Card>
                    <CardContent className="p-6 text-center space-y-2">
                        <AlertCircle className="mx-auto h-8 w-8 text-rose-500" />
                        <h2 className="font-semibold">This session was cancelled</h2>
                        <p className="text-sm text-muted-foreground">
                            Your completion requirements have been updated.
                        </p>
                    </CardContent>
                </Card>
            )}

            <Card>
                <CardContent className="p-6 space-y-4">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
                        <div className="flex items-start gap-2">
                            <Calendar className="mt-0.5 h-4 w-4 text-muted-foreground" />
                            <div>
                                <div className="font-medium">When</div>
                                <div className="text-muted-foreground">
                                    {fmtDate(startsAt)}
                                    {timezone && ` (${timezone})`}
                                </div>
                                <div className="text-muted-foreground">{durationMinutes} min</div>
                            </div>
                        </div>
                        {location && (
                            <div className="flex items-start gap-2">
                                <MapPin className="mt-0.5 h-4 w-4 text-muted-foreground" />
                                <div>
                                    <div className="font-medium">
                                        {deliveryMode === 'in_person' ? 'In-person venue' : 'Where'}
                                    </div>
                                    <div className="text-muted-foreground">{location}</div>
                                </div>
                            </div>
                        )}
                        {deliveryMode === 'in_person' && !location && (
                            <div className="flex items-start gap-2">
                                <MapPin className="mt-0.5 h-4 w-4 text-muted-foreground" />
                                <div>
                                    <div className="font-medium">In person</div>
                                    <div className="text-muted-foreground">No live stream — check the session description for venue details.</div>
                                </div>
                            </div>
                        )}
                        {typeof registrationCount === 'number' && (
                            <div className="flex items-start gap-2">
                                <Users className="mt-0.5 h-4 w-4 text-muted-foreground" />
                                <div>
                                    <div className="font-medium">Registered</div>
                                    <div className="text-muted-foreground">
                                        {registrationCount}{maxAttendees ? ` / ${maxAttendees}` : ''}
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>

                    {!isCancelled && !isPast && (
                        <div className="flex flex-wrap gap-2 pt-2">
                            {joinSlot}
                            <AddToCalendar
                                title={title}
                                startsAt={startsAt}
                                endsAt={endsAt}
                                description={description}
                                location={location}
                                size="lg"
                            />
                        </div>
                    )}
                    {!canJoinNow && !isPast && !isCancelled && joinSlot && (
                        <p className="text-xs text-muted-foreground">
                            The Join button activates 15 minutes before the session starts.
                        </p>
                    )}
                </CardContent>
            </Card>

            {description && (
                <Card>
                    <CardContent className="p-6">
                        <h2 className="font-semibold mb-2">About this session</h2>
                        <p className="text-sm whitespace-pre-wrap text-muted-foreground">{description}</p>
                    </CardContent>
                </Card>
            )}

            {additionalCards}

            {isPast && recordingLink && (
                <Card>
                    <CardContent className="p-6 space-y-3">
                        <h2 className="font-semibold">After the session</h2>
                        <p className="text-sm text-muted-foreground">
                            If a recording was published, you'll find it here.
                        </p>
                        <Button asChild variant="outline" size="sm">
                            <Link to={recordingLink.to}>View recording</Link>
                        </Button>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
