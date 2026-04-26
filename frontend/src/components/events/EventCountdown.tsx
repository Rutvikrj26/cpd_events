import { useEffect, useState } from 'react';

interface EventCountdownProps {
  startsAt: string | Date;
  endsAt: string | Date;
  /** Status from the API: published / live / completed / cancelled. Refines the label. */
  status?: 'draft' | 'published' | 'live' | 'completed' | 'closed' | 'cancelled';
  className?: string;
}

interface Phase {
  label: string;
  detail: string;
  tone: 'idle' | 'soon' | 'live' | 'ended' | 'cancelled';
}

function pluralize(n: number, single: string, plural?: string): string {
  return `${n} ${n === 1 ? single : plural ?? single + 's'}`;
}

function diffParts(ms: number): { d: number; h: number; m: number; s: number } {
  const total = Math.max(0, Math.floor(ms / 1000));
  return {
    d: Math.floor(total / 86400),
    h: Math.floor((total % 86400) / 3600),
    m: Math.floor((total % 3600) / 60),
    s: total % 60,
  };
}

function describePhase(now: Date, starts: Date, ends: Date, status?: EventCountdownProps['status']): Phase {
  if (status === 'cancelled') {
    return { label: 'Cancelled', detail: 'This event has been cancelled.', tone: 'cancelled' };
  }
  if (status === 'live' || (now >= starts && now < ends)) {
    return { label: 'Live now', detail: 'Join when ready.', tone: 'live' };
  }
  if (now >= ends || status === 'completed' || status === 'closed') {
    return { label: 'Event ended', detail: 'Recording may be available below once published.', tone: 'ended' };
  }
  const ms = starts.getTime() - now.getTime();
  const { d, h, m, s } = diffParts(ms);
  if (d > 0) {
    return {
      label: `In ${pluralize(d, 'day')}, ${pluralize(h, 'hour')}`,
      detail: `Starts ${starts.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })}`,
      tone: 'idle',
    };
  }
  if (h > 0) {
    return {
      label: `In ${pluralize(h, 'hour')}, ${pluralize(m, 'min')}`,
      detail: `Starts at ${starts.toLocaleTimeString(undefined, { timeStyle: 'short' })}`,
      tone: h <= 1 ? 'soon' : 'idle',
    };
  }
  if (m > 0) {
    return {
      label: `In ${pluralize(m, 'min')}${s > 0 ? `, ${pluralize(s, 'sec')}` : ''}`,
      detail: 'Starting soon',
      tone: 'soon',
    };
  }
  return { label: `In ${pluralize(s, 'second')}`, detail: 'Starting any moment', tone: 'soon' };
}

const TONE_CLASSES: Record<Phase['tone'], string> = {
  idle: 'text-slate-700 bg-slate-100 dark:text-slate-200 dark:bg-slate-800',
  soon: 'text-amber-900 bg-amber-100 dark:text-amber-100 dark:bg-amber-900/40',
  live: 'text-emerald-900 bg-emerald-100 dark:text-emerald-100 dark:bg-emerald-900/40',
  ended: 'text-slate-600 bg-slate-50 dark:text-slate-400 dark:bg-slate-900',
  cancelled: 'text-rose-900 bg-rose-100 dark:text-rose-100 dark:bg-rose-900/40',
};

export function EventCountdown({ startsAt, endsAt, status, className }: EventCountdownProps) {
  const starts = typeof startsAt === 'string' ? new Date(startsAt) : startsAt;
  const ends = typeof endsAt === 'string' ? new Date(endsAt) : endsAt;
  const [now, setNow] = useState<Date>(() => new Date());

  useEffect(() => {
    // Tick every second when within the last hour, every 30s otherwise.
    const tick = () => setNow(new Date());
    const ms = starts.getTime() - Date.now();
    const interval = ms < 60 * 60 * 1000 && ms > -60 * 60 * 1000 ? 1000 : 30_000;
    const id = window.setInterval(tick, interval);
    return () => window.clearInterval(id);
  }, [starts]);

  const phase = describePhase(now, starts, ends, status);
  return (
    <div
      className={`inline-flex flex-col items-start rounded-md px-4 py-3 ${TONE_CLASSES[phase.tone]} ${className ?? ''}`}
    >
      <span className="text-xs font-medium uppercase tracking-wide opacity-70">
        {phase.tone === 'live' ? 'Now' : phase.tone === 'ended' ? 'Past' : phase.tone === 'cancelled' ? 'Status' : 'Starts'}
      </span>
      <span className="text-2xl font-semibold leading-tight">{phase.label}</span>
      <span className="text-sm opacity-80">{phase.detail}</span>
    </div>
  );
}
