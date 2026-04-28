/**
 * RecordingTranscriptAdapter — wires the recording-specific data layer
 * (transcripts API, edit dialog, history dialog, host edit affordances)
 * around the source-agnostic <TranscriptPanel> in `@/shared/media`.
 *
 * The shared panel handles: virtualized rendering, click-to-seek,
 * "Following" toggle, search match navigation, density toggle, export
 * buttons. This adapter handles: fetching segments via react-query,
 * server-side search, segment edits + audit history.
 *
 * Why split: the player primitive lives in shared/ and must not import
 * from recording-specific APIs. The dialog UX is recording-only and
 * doesn't belong in shared/. The adapter bridges them.
 */

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { History, Loader2, Pencil } from 'lucide-react';

import { Button } from '@/shared/ui/button';
import { Textarea } from '@/shared/ui/textarea';
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
} from '@/shared/ui/dialog';
import { TranscriptPanel } from '@/shared/media';
import { formatDurationMs } from '@/shared/media';
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

interface Props {
    recordingUuid: string;
    /** Current playback time in ms — supplied by the parent <MediaPlayer>. */
    currentMs: number;
    /** Click-to-seek handler, in seconds. Wired to the player. */
    onSeek: (seconds: number) => void;
    /** True when the user can edit segments (host / staff). */
    canEdit?: boolean;
}

export function RecordingTranscriptAdapter({
    recordingUuid,
    currentMs,
    onSeek,
    canEdit = false,
}: Props) {
    const [editing, setEditing] = useState<TranscriptSegment | null>(null);
    const [historyOf, setHistoryOf] = useState<TranscriptSegment | null>(null);

    const transcriptQuery = useQuery<Transcript>({
        queryKey: ['transcript', recordingUuid],
        queryFn: () => getRecordingTranscript(recordingUuid),
        retry: false,
    });

    if (transcriptQuery.isLoading) {
        return (
            <TranscriptPanel
                transcript={{ isLoading: true }}
                currentMs={currentMs}
                onSeek={onSeek}
            />
        );
    }

    if (transcriptQuery.isError) {
        return (
            <TranscriptPanel
                transcript={{
                    errorMessage:
                        "This recording doesn't have a transcript yet — either captions weren't enabled, or the agent couldn't reach the configured STT provider.",
                }}
                currentMs={currentMs}
                onSeek={onSeek}
            />
        );
    }

    const transcript = transcriptQuery.data!;
    const segments: import('@/shared/media').TranscriptSegment[] = transcript.segments.map((s) => ({
        uuid: s.uuid,
        start_ms: s.start_ms,
        end_ms: s.end_ms,
        text: s.text,
        speaker_name: s.speaker_name,
    }));

    const showEditUi = canEdit && transcript.status !== 'streaming';

    const statusBanner = transcript.status === 'streaming' ? (
        <div className="flex items-center gap-2 border-b border-border bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
            <Loader2 className="h-3 w-3 animate-spin" />
            Transcript still being generated — segments will appear as the agent processes audio.
        </div>
    ) : transcript.status === 'error' && transcript.error_message ? (
        <div className="border-b border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
            {transcript.error_message}
        </div>
    ) : undefined;

    return (
        <>
            <TranscriptPanel
                transcript={{
                    segments,
                    statusBanner,
                    search: async (q) => {
                        const res = await searchRecordingTranscript(recordingUuid, q);
                        return { matchedIds: new Set(res.results.map((s) => s.uuid)) };
                    },
                    export: async (fmt) => {
                        await downloadTranscriptExport(recordingUuid, fmt);
                    },
                }}
                currentMs={currentMs}
                onSeek={onSeek}
                renderRowExtras={
                    showEditUi
                        ? (seg) => {
                              const original = transcript.segments.find((s) => s.uuid === seg.uuid);
                              if (!original) return null;
                              return (
                                  <div className="flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                                      <button
                                          type="button"
                                          aria-label="Edit segment"
                                          title="Edit"
                                          onClick={(e) => {
                                              e.stopPropagation();
                                              setEditing(original);
                                          }}
                                          className="rounded p-1 hover:bg-muted"
                                      >
                                          <Pencil className="h-3 w-3" />
                                      </button>
                                      <button
                                          type="button"
                                          aria-label="View edit history"
                                          title="History"
                                          onClick={(e) => {
                                              e.stopPropagation();
                                              setHistoryOf(original);
                                          }}
                                          className="rounded p-1 hover:bg-muted"
                                      >
                                          <History className="h-3 w-3" />
                                      </button>
                                  </div>
                              );
                          }
                        : undefined
                }
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
        </>
    );
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
            queryClient.invalidateQueries({ queryKey: ['transcript', recordingUuid] });
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
                        <span className="tabular-nums">{formatDurationMs(segment.start_ms)}</span>
                        {segment.speaker_name && <span>{segment.speaker_name}</span>}
                    </div>
                    <div>
                        <p className="mb-1 text-xs text-muted-foreground">Original</p>
                        <p className="rounded-md bg-muted/40 px-3 py-2 font-mono text-xs">
                            {segment.text}
                        </p>
                    </div>
                    <div>
                        <p className="mb-1 text-xs text-muted-foreground">Corrected</p>
                        <Textarea
                            value={text}
                            onChange={(e) => setText(e.target.value)}
                            rows={4}
                            autoFocus
                        />
                    </div>
                    {error && <p className="text-xs text-destructive">{error}</p>}
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
                        {mutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
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
                                    className={`rounded-md border p-3 ${isCurrent ? 'border-primary/40 bg-primary/5' : 'border-border bg-muted/30'}`}
                                >
                                    <div className="mb-1 flex items-baseline justify-between text-xs text-muted-foreground">
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
