/**
 * TranscriptPanel — post-event transcript viewer for the recording page.
 *
 * Renders a virtualized list of segments time-synced to a parent
 * `<video>` element. Click a segment to seek the player; the active
 * segment auto-highlights as the video plays. Search box hits the
 * GIN-backed search endpoint and scrolls matches into view.
 *
 * Why virtualize: a 2-hour session with ~1.5s avg segment length
 * produces ~4800 rows. Native rendering scrolls fine for the first
 * second, then jank-locks. `@tanstack/react-virtual` keeps DOM size
 * bounded regardless of transcript length.
 *
 * Why poll the transcript via react-query (not WebSocket):
 *   - Live captions already flow over LiveKit's data plane to the
 *     in-meeting overlay; this panel exists for POST-event playback.
 *   - The post-event viewer doesn't need realtime updates — once
 *     finalized, the transcript is immutable except for organiser
 *     edits, which are user-initiated and explicitly invalidate the
 *     query.
 */

import { forwardRef, useEffect, useMemo, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useVirtualizer } from '@tanstack/react-virtual';
import { AlertCircle, History, Loader2, Pencil, Search, X } from 'lucide-react';

import { Button } from '@/shared/ui/button';
import { Card, CardContent } from '@/shared/ui/card';
import { Input } from '@/shared/ui/input';
import { Textarea } from '@/shared/ui/textarea';
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
} from '@/shared/ui/dialog';
import {
    downloadTranscriptExport,
    editTranscriptSegment,
    getRecordingTranscript,
    getTranscriptSegmentHistory,
    searchRecordingTranscript,
} from '@/api/transcripts';
import type {
    Transcript,
    TranscriptSegment,
} from '@/api/transcripts/types';

interface TranscriptPanelProps {
    recordingUuid: string;
    /** Ref to the parent video element so segment clicks can seek it. */
    videoRef: React.RefObject<HTMLVideoElement>;
    /**
     * Whether the current user can edit segments. Backend enforces the
     * same predicate (`is_event_host`); passing it as a prop here lets
     * us hide the affordance for non-organisers without a round-trip.
     * Default false — edit UI never shown unless explicitly enabled.
     */
    canEdit?: boolean;
}

// 250ms is fast enough that the active-segment highlight feels live
// without throttling React reconciliation. Native `timeupdate` fires
// ~4×/s in most browsers; a 250ms throttle dedupes within a frame.
const TIME_SYNC_THROTTLE_MS = 250;

// react-virtual needs a height estimate. 64px matches a one-line
// segment with the speaker name above; longer segments grow naturally
// because we measure on render.
const ESTIMATED_ROW_HEIGHT = 64;

export function TranscriptPanel({ recordingUuid, videoRef, canEdit = false }: TranscriptPanelProps) {
    const [searchQ, setSearchQ] = useState('');
    const [debouncedQ, setDebouncedQ] = useState('');
    const [currentMs, setCurrentMs] = useState(0);
    // Open dialogs (edit / history) keyed by segment uuid. Two flavours
    // because they're independent — viewing history doesn't open the
    // editor and vice versa.
    const [editing, setEditing] = useState<TranscriptSegment | null>(null);
    const [historyOf, setHistoryOf] = useState<TranscriptSegment | null>(null);

    // Debounce search input so typing doesn't fire a request per keystroke.
    useEffect(() => {
        const id = window.setTimeout(() => setDebouncedQ(searchQ.trim()), 250);
        return () => window.clearTimeout(id);
    }, [searchQ]);

    // Track playback time. Throttled so we re-render at most ~4×/s.
    useEffect(() => {
        const v = videoRef.current;
        if (!v) return;
        let last = 0;
        const onTimeUpdate = () => {
            const now = performance.now();
            if (now - last < TIME_SYNC_THROTTLE_MS) return;
            last = now;
            setCurrentMs(Math.floor(v.currentTime * 1000));
        };
        v.addEventListener('timeupdate', onTimeUpdate);
        return () => v.removeEventListener('timeupdate', onTimeUpdate);
    }, [videoRef]);

    const transcriptQuery = useQuery<Transcript>({
        queryKey: ['transcript', recordingUuid],
        queryFn: () => getRecordingTranscript(recordingUuid),
        // Don't toast on 404 — recordings without transcripts are normal,
        // not an error for the user.
        retry: false,
    });

    const searchQuery = useQuery({
        queryKey: ['transcript-search', recordingUuid, debouncedQ],
        queryFn: () => searchRecordingTranscript(recordingUuid, debouncedQ),
        enabled: debouncedQ.length >= 2,
    });

    // Hoisted ABOVE the loading/error early returns so React's hook
    // order stays stable across renders (Rules of Hooks). Reads from
    // searchQuery.data — which is `undefined` until search resolves —
    // so the empty-set fallback handles the pre-data render fine.
    const isSearchActive = debouncedQ.length >= 2;
    const matchedIds = useMemo(() => {
        if (!isSearchActive || !searchQuery.data) return new Set<string>();
        return new Set(searchQuery.data.results.map((s) => s.uuid));
    }, [isSearchActive, searchQuery.data]);

    if (transcriptQuery.isLoading) {
        return (
            <Card>
                <CardContent className="p-8 flex items-center gap-2 text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Loading transcript…
                </CardContent>
            </Card>
        );
    }

    if (transcriptQuery.isError) {
        // 404 (no transcript for this recording) is a non-error from the
        // user's perspective — render a clean "no transcript yet" card.
        // Other errors (5xx) get the same shape with different copy.
        return (
            <Card>
                <CardContent className="p-6 flex items-start gap-3 text-sm">
                    <AlertCircle className="h-5 w-5 shrink-0 text-amber-500" />
                    <div>
                        <p className="font-medium">No transcript available.</p>
                        <p className="text-muted-foreground mt-1">
                            This recording doesn't have a transcript yet — either
                            the organiser hadn't enabled captions for the event,
                            or the agent couldn't reach the configured STT provider.
                        </p>
                    </div>
                </CardContent>
            </Card>
        );
    }

    const transcript = transcriptQuery.data!;
    const segments = transcript.segments;

    return (
        <Card className="flex flex-col h-full">
            <div className="flex items-center justify-between gap-2 border-b border-border p-3">
                <div className="relative flex-1">
                    <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                        value={searchQ}
                        onChange={(e) => setSearchQ(e.target.value)}
                        placeholder="Search transcript…"
                        className="pl-8 pr-8"
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
                <ExportMenu recordingUuid={recordingUuid} />
            </div>

            {transcript.status === 'streaming' && (
                <div className="px-3 py-2 text-xs text-muted-foreground bg-muted/40 border-b border-border flex items-center gap-2">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    Transcript still being generated — segments will appear as the agent processes audio.
                </div>
            )}
            {transcript.status === 'error' && transcript.error_message && (
                <div className="px-3 py-2 text-xs text-amber-700 bg-amber-50 border-b border-amber-200">
                    {transcript.error_message}
                </div>
            )}

            <SegmentList
                segments={segments}
                currentMs={currentMs}
                matchedIds={matchedIds}
                searchQuery={debouncedQ}
                canEdit={canEdit && transcript.status !== 'streaming'}
                onSeek={(ms) => {
                    const v = videoRef.current;
                    if (v) v.currentTime = ms / 1000;
                }}
                onEdit={(seg) => setEditing(seg)}
                onHistory={(seg) => setHistoryOf(seg)}
            />
            {editing && (
                <SegmentEditDialog
                    transcriptUuid={transcript.uuid}
                    recordingUuid={recordingUuid}
                    segment={editing}
                    onClose={() => setEditing(null)}
                />
            )}
            {historyOf && (
                <SegmentHistoryDialog
                    transcriptUuid={transcript.uuid}
                    segment={historyOf}
                    onClose={() => setHistoryOf(null)}
                />
            )}
        </Card>
    );
}

/* -------- Virtualized segment list ----------------------------------- */

interface SegmentListProps {
    segments: TranscriptSegment[];
    currentMs: number;
    matchedIds: Set<string>;
    searchQuery: string;
    canEdit: boolean;
    onSeek: (ms: number) => void;
    onEdit: (seg: TranscriptSegment) => void;
    onHistory: (seg: TranscriptSegment) => void;
}

function SegmentList({
    segments,
    currentMs,
    matchedIds,
    searchQuery,
    canEdit,
    onSeek,
    onEdit,
    onHistory,
}: SegmentListProps) {
    const parentRef = useRef<HTMLDivElement>(null);

    // Active segment lookup — the one whose [start_ms, end_ms] brackets
    // currentMs. Binary search rather than linear scan because for a
    // 2-hour transcript the linear path would re-traverse 4800 rows
    // every 250ms.
    const activeIndex = useMemo(() => {
        if (segments.length === 0) return -1;
        let lo = 0;
        let hi = segments.length - 1;
        while (lo <= hi) {
            const mid = (lo + hi) >> 1;
            const s = segments[mid];
            if (currentMs < s.start_ms) hi = mid - 1;
            else if (currentMs > s.end_ms) lo = mid + 1;
            else return mid;
        }
        // No exact bracket — return the segment that starts closest before.
        return Math.max(0, hi);
    }, [segments, currentMs]);

    const virtualizer = useVirtualizer({
        count: segments.length,
        getScrollElement: () => parentRef.current,
        estimateSize: () => ESTIMATED_ROW_HEIGHT,
        overscan: 8,
    });

    // Auto-scroll to the active segment as playback advances. We only
    // do this when the active segment isn't currently visible — avoids
    // hijacking the user's scroll if they've scrolled away to read.
    useEffect(() => {
        if (activeIndex < 0) return;
        const visible = virtualizer.getVirtualItems();
        const isVisible = visible.some((v) => v.index === activeIndex);
        if (!isVisible) {
            virtualizer.scrollToIndex(activeIndex, { align: 'center' });
        }
    }, [activeIndex, virtualizer]);

    if (segments.length === 0) {
        return (
            <div className="p-8 text-center text-sm text-muted-foreground">
                No segments yet.
            </div>
        );
    }

    const total = virtualizer.getTotalSize();

    return (
        <div ref={parentRef} className="flex-1 overflow-auto">
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
                            canEdit={canEdit}
                            onClick={() => onSeek(seg.start_ms)}
                            onEdit={() => onEdit(seg)}
                            onHistory={() => onHistory(seg)}
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
        </div>
    );
}

/* -------- Single segment row ---------------------------------------- */

interface SegmentRowProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'onClick'> {
    seg: TranscriptSegment;
    isActive: boolean;
    isMatch: boolean;
    searchQuery: string;
    canEdit: boolean;
    onClick: () => void;
    onEdit: () => void;
    onHistory: () => void;
}

// forwardRef so the virtualizer can measure the rendered height (segments
// aren't all the same height — long ones wrap onto multiple lines).
//
// Why a div+button mix instead of a single button: the row needs to
// contain action buttons (edit, history) that mustn't trigger the
// row's seek-on-click handler. Nested <button> is invalid HTML; we
// use a div with a primary clickable area + sibling action buttons,
// stopping propagation on the actions.
const SegmentRow = forwardRef<HTMLDivElement, SegmentRowProps>(
    function SegmentRow(
        { seg, isActive, isMatch, searchQuery, canEdit, onClick, onEdit, onHistory, style, ...rest },
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
                className={[
                    'group w-full text-left px-4 py-2 border-b border-border/50',
                    'cursor-pointer hover:bg-muted/50 transition-colors',
                    isActive ? 'bg-primary/5 border-l-2 border-l-primary' : '',
                    isMatch ? 'bg-amber-50/50' : '',
                ].join(' ')}
            >
                <div className="flex items-baseline gap-2 text-xs text-muted-foreground mb-0.5">
                    <span className="tabular-nums">{formatMs(seg.start_ms)}</span>
                    {seg.speaker_name && (
                        <span className="font-medium text-foreground/80">{seg.speaker_name}</span>
                    )}
                    {canEdit && (
                        <div className="ml-auto flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                            <button
                                type="button"
                                aria-label="Edit segment"
                                title="Edit"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    onEdit();
                                }}
                                className="p-1 rounded hover:bg-muted"
                            >
                                <Pencil className="h-3 w-3" />
                            </button>
                            <button
                                type="button"
                                aria-label="View edit history"
                                title="History"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    onHistory();
                                }}
                                className="p-1 rounded hover:bg-muted"
                            >
                                <History className="h-3 w-3" />
                            </button>
                        </div>
                    )}
                </div>
                <p className="text-sm leading-snug">
                    {searchQuery ? highlight(seg.text, searchQuery) : seg.text}
                </p>
            </div>
        );
    },
);

/* -------- Helpers --------------------------------------------------- */

function formatMs(ms: number): string {
    const s = Math.floor(ms / 1000);
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = s % 60;
    if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`;
    return `${m}:${sec.toString().padStart(2, '0')}`;
}

function highlight(text: string, q: string) {
    if (!q) return text;
    const lower = text.toLowerCase();
    const needle = q.toLowerCase();
    const parts: React.ReactNode[] = [];
    let i = 0;
    while (i < text.length) {
        const j = lower.indexOf(needle, i);
        if (j < 0) {
            parts.push(text.slice(i));
            break;
        }
        if (j > i) parts.push(text.slice(i, j));
        parts.push(
            <mark key={j} className="bg-amber-200/70 rounded px-0.5">
                {text.slice(j, j + q.length)}
            </mark>,
        );
        i = j + q.length;
    }
    return parts;
}

/* -------- Edit dialog ----------------------------------------------- */

interface SegmentEditDialogProps {
    transcriptUuid: string;
    recordingUuid: string;
    segment: TranscriptSegment;
    onClose: () => void;
}

function SegmentEditDialog({
    transcriptUuid,
    recordingUuid,
    segment,
    onClose,
}: SegmentEditDialogProps) {
    const [text, setText] = useState(segment.text);
    const [error, setError] = useState<string | null>(null);
    const queryClient = useQueryClient();

    const mutation = useMutation({
        mutationFn: (newText: string) =>
            editTranscriptSegment(transcriptUuid, segment.uuid, newText),
        onSuccess: () => {
            // Invalidate the transcript query so the panel re-renders
            // with the new segment uuid in place. Don't optimistically
            // update — the backend response is the source of truth for
            // the new segment uuid (which feeds future edits).
            queryClient.invalidateQueries({
                queryKey: ['transcript', recordingUuid],
            });
            onClose();
        },
        onError: (err: any) => {
            const status = err?.response?.status;
            if (status === 409) {
                setError(
                    'The transcript is still being generated; edits become available once it finalizes.',
                );
            } else if (status === 404) {
                setError(
                    'This segment was already edited by someone else. Refresh and try again.',
                );
            } else {
                setError('Could not save the edit. Please try again.');
            }
        },
    });

    const dirty = text.trim() !== segment.text.trim();
    const valid = text.trim().length > 0;

    return (
        <Dialog open onOpenChange={(open) => { if (!open) onClose(); }}>
            <DialogContent className="max-w-2xl">
                <DialogHeader>
                    <DialogTitle>Edit transcript segment</DialogTitle>
                </DialogHeader>
                <div className="space-y-3 text-sm">
                    <div className="flex items-baseline gap-2 text-xs text-muted-foreground">
                        <span className="tabular-nums">{formatMs(segment.start_ms)}</span>
                        {segment.speaker_name && <span>{segment.speaker_name}</span>}
                    </div>
                    <div>
                        <p className="text-xs text-muted-foreground mb-1">Original</p>
                        <p className="px-3 py-2 bg-muted/40 rounded-md font-mono text-xs">
                            {segment.text}
                        </p>
                    </div>
                    <div>
                        <p className="text-xs text-muted-foreground mb-1">Corrected</p>
                        <Textarea
                            value={text}
                            onChange={(e) => setText(e.target.value)}
                            rows={4}
                            autoFocus
                        />
                    </div>
                    {error && (
                        <p className="text-xs text-destructive">{error}</p>
                    )}
                    <p className="text-xs text-muted-foreground">
                        The original is preserved in the audit history. Timing and speaker
                        attribution are immutable for compliance.
                    </p>
                </div>
                <div className="flex justify-end gap-2 pt-2">
                    <Button variant="outline" onClick={onClose} disabled={mutation.isPending}>
                        Cancel
                    </Button>
                    <Button
                        onClick={() => mutation.mutate(text.trim())}
                        disabled={!dirty || !valid || mutation.isPending}
                    >
                        {mutation.isPending && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
                        Save
                    </Button>
                </div>
            </DialogContent>
        </Dialog>
    );
}

/* -------- History dialog -------------------------------------------- */

interface SegmentHistoryDialogProps {
    transcriptUuid: string;
    segment: TranscriptSegment;
    onClose: () => void;
}

function SegmentHistoryDialog({
    transcriptUuid,
    segment,
    onClose,
}: SegmentHistoryDialogProps) {
    const historyQuery = useQuery({
        queryKey: ['transcript-history', transcriptUuid, segment.uuid],
        queryFn: () => getTranscriptSegmentHistory(transcriptUuid, segment.uuid),
    });

    return (
        <Dialog open onOpenChange={(open) => { if (!open) onClose(); }}>
            <DialogContent className="max-w-2xl">
                <DialogHeader>
                    <DialogTitle>Edit history</DialogTitle>
                </DialogHeader>
                {historyQuery.isLoading && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Loading history…
                    </div>
                )}
                {historyQuery.data && (
                    <ol className="space-y-3 text-sm">
                        {historyQuery.data.segments.map((s, i) => {
                            const isCurrent = i === historyQuery.data.segments.length - 1;
                            return (
                                <li
                                    key={s.uuid}
                                    className={`p-3 rounded-md border ${isCurrent ? 'border-primary/40 bg-primary/5' : 'border-border bg-muted/30'}`}
                                >
                                    <div className="flex items-baseline justify-between text-xs text-muted-foreground mb-1">
                                        <span>
                                            {s.source === 'live' && 'Original (STT)'}
                                            {s.source === 'edit' && (
                                                <>Edit by {s.edited_by_name || 'organiser'}</>
                                            )}
                                            {s.source === 'batch_repair' && 'Post-event re-pass'}
                                        </span>
                                        <span>
                                            {new Date(s.edited_at || s.created_at).toLocaleString()}
                                        </span>
                                    </div>
                                    <p className="text-sm leading-snug">{s.text}</p>
                                </li>
                            );
                        })}
                    </ol>
                )}
            </DialogContent>
        </Dialog>
    );
}

/* -------- Export menu ----------------------------------------------- */

function ExportMenu({ recordingUuid }: { recordingUuid: string }) {
    const [busy, setBusy] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);

    const handleClick = async (fmt: 'vtt' | 'srt' | 'txt') => {
        setBusy(fmt);
        setError(null);
        try {
            await downloadTranscriptExport(recordingUuid, fmt);
        } catch (e) {
            const message = e instanceof Error ? e.message : 'Download failed';
            setError(message);
        } finally {
            setBusy(null);
        }
    };

    return (
        <div className="flex items-center gap-1">
            {(['vtt', 'srt', 'txt'] as const).map((fmt) => (
                <Button
                    key={fmt}
                    type="button"
                    variant="ghost"
                    size="sm"
                    disabled={busy !== null}
                    className="h-8 px-2 text-xs uppercase"
                    onClick={() => handleClick(fmt)}
                >
                    {busy === fmt ? '…' : fmt}
                </Button>
            ))}
            {error && (
                <span className="ml-2 text-xs text-destructive" role="alert">
                    {error}
                </span>
            )}
        </div>
    );
}
