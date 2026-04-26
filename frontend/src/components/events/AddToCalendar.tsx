import { Calendar } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

interface AddToCalendarProps {
  title: string;
  startsAt: string | Date;
  endsAt: string | Date;
  description?: string;
  location?: string;
  /** Optional URL to a downloadable .ics file. */
  icsUrl?: string;
  variant?: 'default' | 'outline' | 'secondary';
  size?: 'default' | 'sm' | 'lg';
  className?: string;
}

function toUtcCompact(value: string | Date): string {
  const d = typeof value === 'string' ? new Date(value) : value;
  // YYYYMMDDTHHMMSSZ (RFC 5545 UTC compact form, used by Google deep-link)
  return d.toISOString().replace(/[-:]|\.\d{3}/g, '');
}

function buildGoogleUrl(props: AddToCalendarProps): string {
  const params = new URLSearchParams({
    action: 'TEMPLATE',
    text: props.title,
    dates: `${toUtcCompact(props.startsAt)}/${toUtcCompact(props.endsAt)}`,
  });
  if (props.description) params.set('details', props.description);
  if (props.location) params.set('location', props.location);
  return `https://calendar.google.com/calendar/render?${params.toString()}`;
}

function buildOutlookUrl(props: AddToCalendarProps): string {
  const params = new URLSearchParams({
    path: '/calendar/action/compose',
    rru: 'addevent',
    subject: props.title,
    startdt: new Date(props.startsAt).toISOString(),
    enddt: new Date(props.endsAt).toISOString(),
  });
  if (props.description) params.set('body', props.description);
  if (props.location) params.set('location', props.location);
  return `https://outlook.live.com/calendar/0/deeplink/compose?${params.toString()}`;
}

function buildIcsBlob(props: AddToCalendarProps): string {
  // Lightweight ICS for client-side download when no server URL is provided.
  const lines = [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//Accredit//AddToCalendar//EN',
    'METHOD:PUBLISH',
    'BEGIN:VEVENT',
    `UID:${crypto.randomUUID()}@accredit`,
    `DTSTAMP:${toUtcCompact(new Date())}`,
    `DTSTART:${toUtcCompact(props.startsAt)}`,
    `DTEND:${toUtcCompact(props.endsAt)}`,
    `SUMMARY:${(props.title || '').replace(/[\\,;]/g, (c) => `\\${c}`).replace(/\n/g, '\\n')}`,
  ];
  if (props.description) {
    lines.push(`DESCRIPTION:${props.description.replace(/[\\,;]/g, (c) => `\\${c}`).replace(/\n/g, '\\n')}`);
  }
  if (props.location) {
    lines.push(`LOCATION:${props.location.replace(/[\\,;]/g, (c) => `\\${c}`).replace(/\n/g, '\\n')}`);
  }
  lines.push('END:VEVENT', 'END:VCALENDAR');
  return lines.join('\r\n') + '\r\n';
}

function downloadIcsFallback(props: AddToCalendarProps) {
  const blob = new Blob([buildIcsBlob(props)], { type: 'text/calendar;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${props.title.toLowerCase().replace(/[^a-z0-9]+/g, '-')}.ics`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function AddToCalendar(props: AddToCalendarProps) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant={props.variant ?? 'outline'} size={props.size ?? 'default'} className={props.className}>
          <Calendar className="mr-2 h-4 w-4" />
          Add to Calendar
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem asChild>
          <a href={buildGoogleUrl(props)} target="_blank" rel="noopener noreferrer">
            Google Calendar
          </a>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <a href={buildOutlookUrl(props)} target="_blank" rel="noopener noreferrer">
            Outlook (Office 365)
          </a>
        </DropdownMenuItem>
        {props.icsUrl ? (
          <DropdownMenuItem asChild>
            <a href={props.icsUrl} target="_blank" rel="noopener noreferrer">
              Download .ics (Apple/iCal)
            </a>
          </DropdownMenuItem>
        ) : (
          <DropdownMenuItem onClick={() => downloadIcsFallback(props)}>
            Download .ics (Apple/iCal)
          </DropdownMenuItem>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
