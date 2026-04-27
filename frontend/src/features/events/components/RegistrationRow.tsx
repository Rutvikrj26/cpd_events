import { Link } from 'react-router-dom';
import { Award, ExternalLink, Video } from 'lucide-react';
import { Button } from '@/shared/ui/button';
import { Badge } from '@/shared/ui/badge';
import { Icon } from '@/shared/ui/icon';
import { CardRow, DateBlock } from '@/shared/components';
import type { Registration } from '@/api/registrations/types';

interface RegistrationRowProps {
    reg: Registration;
}

/**
 * RegistrationRow — list-item card for "My Learning" / "Up next this
 * week". Shared so the dashboard and the dedicated page render the
 * same shape.
 */
export function RegistrationRow({ reg }: RegistrationRowProps) {
    return (
        <CardRow
            leading={<DateBlock date={reg.event.starts_at} />}
            body={
                <>
                    <h3 className="truncate text-h3 leading-snug text-foreground">
                        <Link
                            to={`/events/${reg.event.slug || reg.event.uuid}/details`}
                            className="hover:text-primary focus-visible:outline-none focus-visible:underline"
                        >
                            {reg.event.title}
                        </Link>
                    </h3>
                    <div className="mt-2 flex flex-wrap items-center gap-tight text-caption text-muted-foreground">
                        <Badge variant="secondary" className="text-2xs capitalize">
                            {reg.event.event_type}
                        </Badge>
                        {reg.event.cpd_credit_value ? (
                            <span className="inline-flex items-center gap-1">
                                <Icon icon={Award} size="dense" tone="warning" />
                                {reg.event.cpd_credit_value} CPD
                            </span>
                        ) : null}
                    </div>
                </>
            }
            trailing={
                <>
                    <Button size="sm" asChild>
                        <Link to={`/events/${reg.event.uuid}/lobby`}>
                            <Video className="mr-1 h-3.5 w-3.5" /> Lobby
                        </Link>
                    </Button>
                    <Button size="sm" variant="outline" asChild>
                        <Link to={`/events/${reg.event.slug || reg.event.uuid}/details`}>
                            Details <ExternalLink className="ml-1 h-3.5 w-3.5" />
                        </Link>
                    </Button>
                </>
            }
        />
    );
}
