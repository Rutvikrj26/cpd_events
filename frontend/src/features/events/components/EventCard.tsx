import { Link } from 'react-router-dom';
import { Award, Calendar, MapPin, Users } from 'lucide-react';
import { Card, CardContent, CardDescription } from '@/shared/ui/card';
import { Badge } from '@/shared/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/shared/ui/avatar';
import type { Event } from '../types';
import { EventStatusBadge } from './EventStatusBadge';

interface EventCardProps {
    event: Event;
    /** Override default link target. Defaults to public detail page. */
    href?: string;
    /** Optionally hide the status pill (e.g. on a dashboard where every row is "published"). */
    showStatus?: boolean;
}

/**
 * EventCard — discovery-grid card. Composes the Card primitive with
 * an event-specific layout: gradient banner with date, title + meta,
 * organizer chip, status pill, attendee count.
 */
export function EventCard({
    event,
    href,
    showStatus = false,
}: EventCardProps) {
    const start = new Date(event.starts_at);
    const targetHref = href || `/events/${event.slug || event.uuid}/details`;

    return (
        <Card
            elevation="interactive"
            className="group flex flex-col overflow-hidden focus-within:ring-2 focus-within:ring-ring/60"
        >
            <Link to={targetHref} className="block">
                <div className="relative aspect-video overflow-hidden bg-gradient-to-br from-primary/15 via-primary/8 to-accent/15">
                    {(event as any).banner_image_url ? (
                        <img
                            src={(event as any).banner_image_url}
                            alt=""
                            className="h-full w-full object-cover transition-transform duration-300 ease-out group-hover:scale-[1.03]"
                            loading="lazy"
                        />
                    ) : (
                        <div className="flex h-full w-full items-center justify-center text-primary/30">
                            <Calendar className="h-16 w-16" strokeWidth={1.5} />
                        </div>
                    )}
                    {/* Date pill — top left */}
                    <div className="absolute left-3 top-3">
                        <span className="inline-flex items-center gap-1 rounded-full bg-card/90 px-2.5 py-1 text-caption font-semibold text-foreground backdrop-blur-md">
                            <Calendar className="h-3.5 w-3.5 text-primary" strokeWidth={1.75} />
                            {start.toLocaleDateString(undefined, {
                                month: 'short',
                                day: 'numeric',
                            })}
                        </span>
                    </div>
                    {showStatus && (
                        <div className="absolute right-3 top-3">
                            <EventStatusBadge status={event.status} />
                        </div>
                    )}
                </div>

                <CardContent className="flex flex-grow flex-col gap-tight p-card">
                    <h3 className="text-h3 leading-tight text-foreground transition-colors group-hover:text-primary line-clamp-2">
                        {event.title}
                    </h3>
                    {event.description && (
                        <CardDescription className="line-clamp-3">
                            {event.description}
                        </CardDescription>
                    )}

                    <div className="mt-auto flex flex-wrap items-center gap-card text-body text-muted-foreground">
                        {event.cpd_credits ? (
                            <span className="inline-flex items-center gap-1">
                                <Award className="h-4 w-4 text-warning" strokeWidth={1.75} />
                                {event.cpd_credits} CPD
                            </span>
                        ) : null}
                        {event.location ? (
                            <span className="inline-flex items-center gap-1">
                                <MapPin className="h-4 w-4" strokeWidth={1.75} />
                                {event.location}
                            </span>
                        ) : null}
                        {(event.registration_count ?? 0) > 0 ? (
                            <span className="inline-flex items-center gap-1">
                                <Users className="h-4 w-4" strokeWidth={1.75} />
                                {event.registration_count} registered
                            </span>
                        ) : null}
                    </div>
                </CardContent>
            </Link>

            {event.organization_info && (
                <div className="flex items-center justify-between gap-tight border-t bg-muted/30 px-card py-tight">
                    <div className="flex min-w-0 items-center gap-tight">
                        <Avatar className="h-7 w-7">
                            {(event.organization_info as any).logo_url ? (
                                <AvatarImage src={(event.organization_info as any).logo_url} alt="" />
                            ) : null}
                            <AvatarFallback className="text-xs">
                                {event.organization_info.name?.[0] ?? '·'}
                            </AvatarFallback>
                        </Avatar>
                        <span className="truncate text-caption font-medium text-muted-foreground">
                            {event.organization_info.name}
                        </span>
                    </div>
                    <Badge variant="secondary" className="text-2xs capitalize">
                        {event.event_type}
                    </Badge>
                </div>
            )}
        </Card>
    );
}
