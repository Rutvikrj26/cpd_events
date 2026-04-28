/**
 * TranscriptPanel — source-agnostic interactive transcript.
 *
 * Moved from `components/recording/TranscriptPanel.tsx` and decoupled
 * from the recording API. Caller passes in:
 *   - segments (and optional loading/error state)
 *   - currentMs from playback (drives active highlight + auto-scroll)
 *   - onSeek (called when a row is clicked)
 *   - optional search handler (server-side; falls back to local substring)
 *   - optional export handler (renders VTT/SRT/TXT buttons in the toolbar)
 *
 * UX changes vs. the original:
 *   - "Following" pill in the header — flips OFF when the user scrolls
 *     manually. Click to re-engage. Avoids the "I'm reading and it keeps
 *     jumping" annoyance.
 *   - Search has prev/next match navigation buttons.
 *   - Density toggle (compact / comfortable).
 *
 * Virtualization preserved (`@tanstack/react-virtual`) — needed for
 * 2-hour transcripts with thousands of rows.
 */

import { forwardRef, useEffect, useMemo, useRef, useState } from 'react';
import type { HTMLAttributes, ReactNode } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import {
    AlignJustify,
    AlignLeft,
    ArrowDownToLine,
    ChevronDown,
    ChevronUp,
    Loader2,
    Pin,
    PinOff,
    Search,
    X,
} from 'lucide-react';

import { cn } from '@/lib/utils';
import { Button } from '@/shared/ui/button';
import { Input } from '@/shared/ui/input';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/shared/ui/tooltip';
import { formatDurationMs } from '../lib/formatDuration';
import type { TranscriptSegment, TranscriptSource } from '../types';
import { useActiveSegmentIndex } from './useTranscriptSync';

interface TranscriptPanelProps {
    /** Source-agnostic transcript spec (segments + optional handlers). */
    transcript: TranscriptSource;
    /** Current playback time in ms — drives the active row + auto-scroll. */
    currentMs: number;
    /** Click-to-seek handler. Called with the segment's start, in seconds. */
    onSeek: (seconds: number) => void;
    /**
     * Optional row renderer override. Lets callers (recording editor)
     * inject extra affordances (edit / history) without forking the
     * whole panel.
     */
    renderRowExtras?: (seg: TranscriptSegment, isActive: boolean) => ReactNode;
    className?: string;
}

const ESTIMATED_ROW_HEIGHT_COMPACT = 56;
const ESTIMATED_ROW_HEIGHT_COMFORTABLE = 84;

// Stable empty-set sentinel — used as the "no search" matched-ids value
// so referential equality holds across renders (lets React.memo skip).
const EMPTY_ID_SET: ReadonlySet<string> = new Set();

export function TranscriptPanel({
    transcript,
    currentMs,
    onSeek,
    renderRowExtras,
    className,
}: TranscriptPanelProps) {
    const [searchQ, setSearchQ] = useState('');
    const [debouncedQ, setDebouncedQ] = useState('');
    const [searchMatchedIds, setSearchMatchedIds] = useState<Set<string>>(new Set());
    const [searching, setSearching] = useState(false);
    const [matchCursor, setMatchCursor] = useState(0);
    const [following, setFollowing] = useState(true);
    const [density, setDensity] = useState<'compact' | 'comfortable'>('compact');

    /* Debounce search input. */
    useEffect(() => {
        const id = window.setTimeout(() => setDebouncedQ(searchQ.trim()), 250);
        return () => window.clearTimeout(id);
    }, [searchQ]);

    const segments = useMemo(() => transcript.segments ?? [], [transcript.segments]);
    const isSearchActive = debouncedQ.length >= 2;
    const searchHandler = transcript.search;

    /* Run the search whenever the debounced query changes. The handler is
       async (server-backed in the recording viewer) so we must setState
       inside the effect to bridge the network response to React. We skip
       the effect entirely on empty queries — `effectiveMatchedIds` derives
       the empty case from `isSearchActive` instead of clearing state. */
    useEffect(() => {
        if (!isSearchActive) return;
        let cancelled = false;
        if (searchHandler) {
            // Bridges the loading flag for the async network search.
            // Effects are the right place for this — it's the standard
            // "kick off fetch + show spinner" pattern; the rule's
            // "you might not need an effect" guidance doesn't apply
            // because the work is genuinely external (HTTP request).
            // eslint-disable-next-line react-hooks/set-state-in-effect
            setSearching(true);
            searchHandler(debouncedQ)
                .then((res) => {
                    if (!cancelled) {
                        setSearchMatchedIds(res.matchedIds);
                        setMatchCursor(0);
                    }
                })
                .finally(() => !cancelled && setSearching(false));
        } else {
            const needle = debouncedQ.toLowerCase();
            const matched = new Set<string>();
            for (const s of segments) {
                if (s.text.toLowerCase().includes(needle)) matched.add(s.uuid);
            }
            setSearchMatchedIds(matched);
            setMatchCursor(0);
        }
        return () => {
            cancelled = true;
        };
    }, [debouncedQ, isSearchActive, searchHandler, segments]);

    /** Effective matched-ids: empty when no search; the cached result otherwise. */
    const effectiveMatchedIds = isSearchActive ? searchMatchedIds : EMPTY_ID_SET;
    const matchedSegmentIndices = useMemo(() => {
        if (!isSearchActive) return [];
        const out: number[] = [];
        segments.forEach((s, i) => {
            if (searchMatchedIds.has(s.uuid)) out.push(i);
        });
        return out;
    }, [isSearchActive, searchMatchedIds, segments]);

    /* Loading / error sentinels. */
    if (transcript.isLoading) {
        return (
            <PanelShell className={className}>
                <div className="flex items-center gap-2 p-6 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Loading transcript…
                </div>
            </PanelShell>
        );
    }

    if (transcript.errorMessage) {
        return (
            <PanelShell className={className}>
                <div className="p-6 text-sm text-muted-foreground">
                    {transcript.errorMessage}
                </div>
            </PanelShell>
        );
    }

    if (segments.length === 0) {
        return (
            <PanelShell className={className}>
                <div className="p-6 text-sm text-muted-foreground">
                    No transcript segments yet.
                </div>
            </PanelShell>
        );
    }

    return (
        <TooltipProvider delayDuration={300}>
            <PanelShell className={className}>
                <PanelToolbar
                    searchQ={searchQ}
                    setSearchQ={setSearchQ}
                    searching={searching}
                    matchCount={matchedSegmentIndices.length}
                    matchCursor={matchCursor}
                    onJumpMatch={(dir) => {
                        if (matchedSegmentIndices.length === 0) return;
                        const next =
                            (matchCursor + dir + matchedSegmentIndices.length) %
                            matchedSegmentIndices.length;
                        setMatchCursor(next);
                        const seg = segments[matchedSegmentIndices[next]];
                        onSeek(seg.start_ms / 1000);
                    }}
                    following={following}
                    onToggleFollowing={() => setFollowing((f) => !f)}
                    density={density}
                    onToggleDensity={() =>
                        setDensity((d) => (d === 'compact' ? 'comfortable' : 'compact'))
                    }
                    exportHandler={transcript.export}
                />
                {transcript.statusBanner}
                <SegmentList
                    segments={segments}
                    currentMs={currentMs}
                    matchedIds={effectiveMatchedIds}
                    searchQuery={debouncedQ}
                    following={following}
                    density={density}
                    onUserScroll={() => setFollowing(false)}
                    onSeek={(ms) => onSeek(ms / 1000)}
                    renderRowExtras={renderRowExtras}
                />
            </PanelShell>
        </TooltipProvider>
    );
}

/* -------- Shell wrapper --------------------------------------------- */

function PanelShell({
    children,
    className,
}: {
    children: ReactNode;
    className?: string;
}) {
    return (
        <div
            className={cn(
                'flex h-full flex-col overflow-hidden rounded-md border bg-card text-card-foreground',
                className,
            )}
        >
            {children}
        </div>
    );
}

/* -------- Toolbar --------------------------------------------------- */

interface ToolbarProps {
    searchQ: string;
    setSearchQ: (v: string) => void;
    searching: boolean;
    matchCount: number;
    matchCursor: number;
    onJumpMatch: (dir: 1 | -1) => void;
    following: boolean;
    onToggleFollowing: () => void;
    density: 'compact' | 'comfortable';
    onToggleDensity: () => void;
    exportHandler?: TranscriptSource['export'];
}

function PanelToolbar({
    searchQ,
    setSearchQ,
    searching,
    matchCount,
    matchCursor,
    onJumpMatch,
    following,
    onToggleFollowing,
    density,
    onToggleDensity,
    exportHandler,
}: ToolbarProps) {
    return (
        <div className="flex flex-col gap-2 border-b border-border p-2">
            <div className="flex items-center gap-1">
                <div className="relative flex-1">
                    {searching ? (
                        <Loader2 className="absolute left-2 top-2.5 h-4 w-4 animate-spin text-muted-foreground" />
                    ) : (
                        <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                    )}
                    <Input
                        value={searchQ}
                        onChange={(e) => setSearchQ(e.target.value)}
                        placeholder="Search transcript…"
                        className="h-9 pl-8 pr-8"
                        aria-label="Search transcript"
                    />
                    {searchQ && (
                        <button
                            type="button"
                            onClick={() => setSearchQ('')}
                            className="absolute right-2 top-2 rounded p-0.5 hover:bg-muted"
                            aria-label="Clear search"
                        >
                            <X className="h-4 w-4 text-muted-foreground" />
                        </button>
                    )}
                </div>
                {searchQ && (
                    <div className="flex items-center gap-0.5">
                        <Tooltip>
                            <TooltipTrigger asChild>
                                <Button
                                    type="button"
                                    variant="ghost"
                                    size="sm"
                                    className="h-9 w-7 px-0"
                                    disabled={matchCount === 0}
                                    onClick={() => onJumpMatch(-1)}
                                    aria-label="Previous match"
                                >
                                    <ChevronUp className="h-4 w-4" />
                                </Button>
                            </TooltipTrigger>
                            <TooltipContent>Previous match</TooltipContent>
                        </Tooltip>
                        <Tooltip>
                            <TooltipTrigger asChild>
                                <Button
                                    type="button"
                                    variant="ghost"
                                    size="sm"
                                    className="h-9 w-7 px-0"
                                    disabled={matchCount === 0}
                                    onClick={() => onJumpMatch(1)}
                                    aria-label="Next match"
                                >
                                    <ChevronDown className="h-4 w-4" />
                                </Button>
                            </TooltipTrigger>
                            <TooltipContent>Next match</TooltipContent>
                        </Tooltip>
                        <span className="ml-1 text-xs tabular-nums text-muted-foreground">
                            {matchCount === 0 ? '0' : `${matchCursor + 1} / ${matchCount}`}
                        </span>
                    </div>
                )}
            </div>
            <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <Tooltip>
                    <TooltipTrigger asChild>
                        <Button
                            type="button"
                            variant={following ? 'secondary' : 'ghost'}
                            size="sm"
                            className="h-7 px-2 text-xs"
                            onClick={onToggleFollowing}
                            aria-pressed={following}
                        >
                            {following ? (
                                <Pin className="mr-1 h-3 w-3" />
                            ) : (
                                <PinOff className="mr-1 h-3 w-3" />
                            )}
                            {following ? 'Following' : 'Free scroll'}
                        </Button>
                    </TooltipTrigger>
                    <TooltipContent>
                        {following
                            ? 'Auto-scrolling to current segment. Click to disable.'
                            : 'Auto-scroll paused. Click to resume following playback.'}
                    </TooltipContent>
                </Tooltip>
                <Tooltip>
                    <TooltipTrigger asChild>
                        <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            className="h-7 w-7 px-0"
                            onClick={onToggleDensity}
                            aria-label={
                                density === 'compact'
                                    ? 'Switch to comfortable density'
                                    : 'Switch to compact density'
                            }
                        >
                            {density === 'compact' ? (
                                <AlignJustify className="h-4 w-4" />
                            ) : (
                                <AlignLeft className="h-4 w-4" />
                            )}
                        </Button>
                    </TooltipTrigger>
                    <TooltipContent>
                        {density === 'compact' ? 'Comfortable spacing' : 'Compact spacing'}
                    </TooltipContent>
                </Tooltip>
                <div className="flex-1" />
                {exportHandler && <ExportMenu exportHandler={exportHandler} />}
            </div>
        </div>
    );
}

/* -------- Virtualized list ------------------------------------------ */

interface SegmentListProps {
    segments: TranscriptSegment[];
    currentMs: number;
    matchedIds: ReadonlySet<string>;
    searchQuery: string;
    following: boolean;
    density: 'compact' | 'comfortable';
    onUserScroll: () => void;
    onSeek: (ms: number) => void;
    renderRowExtras?: (seg: TranscriptSegment, isActive: boolean) => ReactNode;
}

function SegmentList({
    segments,
    currentMs,
    matchedIds,
    searchQuery,
    following,
    density,
    onUserScroll,
    onSeek,
    renderRowExtras,
}: SegmentListProps) {
    const parentRef = useRef<HTMLDivElement>(null);
    const programmaticScrollRef = useRef(false);
    const lastFollowedIndexRef = useRef(-1);
    const activeIndex = useActiveSegmentIndex(segments, currentMs);

    const estimateSize =
        density === 'compact' ? ESTIMATED_ROW_HEIGHT_COMPACT : ESTIMATED_ROW_HEIGHT_COMFORTABLE;

    const virtualizer = useVirtualizer({
        count: segments.length,
        getScrollElement: () => parentRef.current,
        estimateSize: () => estimateSize,
        overscan: 8,
    });

    /* Auto-scroll to active segment when following. Only scroll if not
       already visible — avoids fighting the user when the active segment
       is in view but they want to glance ahead. */
    useEffect(() => {
        if (!following) return;
        if (activeIndex < 0) return;
        if (activeIndex === lastFollowedIndexRef.current) return;
        const visible = virtualizer.getVirtualItems();
        const isVisible = visible.some((v) => v.index === activeIndex);
        if (!isVisible) {
            programmaticScrollRef.current = true;
            virtualizer.scrollToIndex(activeIndex, { align: 'center' });
            // Unset on the next paint so subsequent user scrolls register.
            requestAnimationFrame(() => {
                programmaticScrollRef.current = false;
            });
        }
        lastFollowedIndexRef.current = activeIndex;
    }, [activeIndex, virtualizer, following]);

    /* Detect user-initiated scroll → flip following off. */
    useEffect(() => {
        const el = parentRef.current;
        if (!el) return;
        const onScroll = () => {
            if (programmaticScrollRef.current) return;
            if (following) onUserScroll();
        };
        el.addEventListener('scroll', onScroll, { passive: true });
        return () => el.removeEventListener('scroll', onScroll);
    }, [following, onUserScroll]);

    const total = virtualizer.getTotalSize();

    return (
        <div ref={parentRef} className="relative flex-1 overflow-auto">
            <div style={{ height: total, position: 'relative' }}>
                {virtualizer.getVirtualItems().map((vi) => {
                    const seg = segments[vi.index];
                    const isActive = vi.index === activeIndex;
                    const isMatch = matchedIds.has(seg.uuid);
                    return (
                        <SegmentRow
                            key={seg.uuid}
                            seg={seg}
                            isActive={isActive}
                            isMatch={isMatch}
                            searchQuery={searchQuery}
                            density={density}
                            onClick={() => onSeek(seg.start_ms)}
                            extras={renderRowExtras?.(seg, isActive)}
                            style={{
                                position: 'absolute',
                                top: 0,
                                left: 0,
                                right: 0,
                                transform: `translateY(${vi.start}px)`,
                            }}
                            ref={virtualizer.measureElement}
                            data-index={vi.index}
                        />
                    );
                })}
            </div>
            {!following && (
                <button
                    type="button"
                    onClick={() => {
                        if (activeIndex >= 0) {
                            programmaticScrollRef.current = true;
                            virtualizer.scrollToIndex(activeIndex, { align: 'center' });
                            requestAnimationFrame(() => {
                                programmaticScrollRef.current = false;
                            });
                        }
                    }}
                    className="absolute bottom-3 right-3 flex items-center gap-1 rounded-full bg-primary px-3 py-1.5 text-xs text-primary-foreground shadow-lg hover:bg-primary/90"
                >
                    <ArrowDownToLine className="h-3 w-3" />
                    Jump to current
                </button>
            )}
        </div>
    );
}

/* -------- Single row ------------------------------------------------ */

interface SegmentRowProps extends Omit<HTMLAttributes<HTMLDivElement>, 'onClick'> {
    seg: TranscriptSegment;
    isActive: boolean;
    isMatch: boolean;
    searchQuery: string;
    density: 'compact' | 'comfortable';
    onClick: () => void;
    extras?: ReactNode;
}

const SegmentRow = forwardRef<HTMLDivElement, SegmentRowProps>(function SegmentRow(
    { seg, isActive, isMatch, searchQuery, density, onClick, extras, style, ...rest },
    ref,
) {
    return (
        <div
            ref={ref}
            role="button"
            tabIndex={0}
            onClick={onClick}
            onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onClick();
                }
            }}
            style={style}
            {...rest}
            className={cn(
                'group w-full cursor-pointer border-b border-border/50 px-3 text-left transition-colors hover:bg-muted/50',
                density === 'compact' ? 'py-1.5' : 'py-2.5',
                isActive ? 'border-l-2 border-l-primary bg-primary/5' : '',
                isMatch ? 'bg-amber-50/50 dark:bg-amber-950/20' : '',
            )}
        >
            <div className="mb-0.5 flex items-baseline gap-2 text-[11px] text-muted-foreground">
                <span className="tabular-nums">{formatDurationMs(seg.start_ms)}</span>
                {seg.speaker_name && (
                    <span className="font-medium text-foreground/80">{seg.speaker_name}</span>
                )}
                {extras && <div className="ml-auto">{extras}</div>}
            </div>
            <p
                className={cn(
                    'leading-snug',
                    density === 'compact' ? 'text-[13px]' : 'text-sm',
                )}
            >
                {searchQuery ? highlight(seg.text, searchQuery) : seg.text}
            </p>
        </div>
    );
});

function highlight(text: string, q: string) {
    if (!q) return text;
    const lower = text.toLowerCase();
    const needle = q.toLowerCase();
    const parts: ReactNode[] = [];
    let i = 0;
    while (i < text.length) {
        const j = lower.indexOf(needle, i);
        if (j < 0) {
            parts.push(text.slice(i));
            break;
        }
        if (j > i) parts.push(text.slice(i, j));
        parts.push(
            <mark key={j} className="rounded bg-amber-200/70 px-0.5 dark:bg-amber-500/40">
                {text.slice(j, j + q.length)}
            </mark>,
        );
        i = j + q.length;
    }
    return parts;
}

/* -------- Export menu ---------------------------------------------- */

function ExportMenu({
    exportHandler,
}: {
    exportHandler: (format: 'vtt' | 'srt' | 'txt') => Promise<void>;
}) {
    const [busy, setBusy] = useState<string | null>(null);
    const handleClick = async (fmt: 'vtt' | 'srt' | 'txt') => {
        setBusy(fmt);
        try {
            await exportHandler(fmt);
        } finally {
            setBusy(null);
        }
    };
    return (
        <div className="flex items-center gap-0.5">
            {(['vtt', 'srt', 'txt'] as const).map((fmt) => (
                <Button
                    key={fmt}
                    type="button"
                    variant="ghost"
                    size="sm"
                    disabled={busy !== null}
                    className="h-7 px-1.5 text-[11px] uppercase"
                    onClick={() => handleClick(fmt)}
                >
                    {busy === fmt ? '…' : fmt}
                </Button>
            ))}
        </div>
    );
}
